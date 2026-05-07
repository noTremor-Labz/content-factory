import json

import httpx
import pytest

from content_factory_api.modules.domain import (
    JobAttemptStatus,
    PackagingProvider,
    RenderJobStatus,
    VoiceProvider,
    WorkflowProvider,
)
from content_factory_api.modules.models import JobAttempt, RenderJob, WorkflowPreset
from content_factory_worker.config import WorkerSettings
from content_factory_worker.executors.comfyui import ComfyUiRenderExecutor
from content_factory_worker.jobs.render import UnconfiguredRenderExecutor, build_render_executor
from content_factory_worker.orchestration import RenderExecutionError


def test_comfyui_executor_submits_local_prompt_and_returns_history_payload() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path == "/prompt":
            return httpx.Response(200, json={"prompt_id": "prompt-123", "number": 1})
        if request.url.path == "/history/prompt-123":
            return httpx.Response(
                200,
                json={
                    "prompt-123": {
                        "status": {"completed": True, "status_str": "success"},
                        "outputs": {"9": {"videos": [{"filename": "pilot.mp4"}]}},
                    }
                },
            )
        return httpx.Response(404, json={"detail": "not found"})

    executor = ComfyUiRenderExecutor(
        base_url="http://comfy.local",
        api_mode="local",
        client=httpx.Client(transport=httpx.MockTransport(handler)),
        sleeper=lambda _seconds: None,
    )

    result = executor.execute(
        render_job=_render_job(),
        workflow_preset=_workflow_preset(),
        attempt=_attempt(),
    )

    assert result.provider_job_id == "prompt-123"
    assert result.response_payload["provider"] == "comfyui"
    assert result.response_payload["prompt_response"] == {"prompt_id": "prompt-123", "number": 1}
    assert (
        result.response_payload["history"]["prompt-123"]["outputs"]["9"]["videos"][0]["filename"]
        == "pilot.mp4"
    )
    submit_body = json.loads(requests[0].content)
    assert requests[0].url.path == "/prompt"
    assert (
        submit_body["prompt"]["script_prompt"]["inputs"]["text"]
        == "render a compliant host short"
    )
    assert submit_body["extra_data"]["content_factory"]["render_job_id"] == "render-job-1"
    assert submit_body["extra_data"]["content_factory"]["inputs"] == {"script_text": "Pilot script"}


def test_comfyui_executor_maps_cloud_failed_status_to_render_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/prompt":
            return httpx.Response(200, json={"prompt_id": "prompt-123"})
        if request.url.path == "/api/job/prompt-123/status":
            return httpx.Response(
                200,
                json={"status": "failed", "error": {"message": "Model missing"}},
            )
        return httpx.Response(404)

    executor = ComfyUiRenderExecutor(
        base_url="https://cloud.comfy.org",
        api_key="secret",
        api_mode="cloud",
        client=httpx.Client(transport=httpx.MockTransport(handler)),
        sleeper=lambda _seconds: None,
    )

    with pytest.raises(RenderExecutionError, match="Model missing"):
        executor.execute(
            render_job=_render_job(),
            workflow_preset=_workflow_preset(),
            attempt=_attempt(),
        )


def test_comfyui_executor_times_out_waiting_for_terminal_status() -> None:
    now = 100.0

    def monotonic() -> float:
        return now

    def sleeper(seconds: float) -> None:
        nonlocal now
        now += seconds

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/prompt":
            return httpx.Response(200, json={"prompt_id": "prompt-123"})
        if request.url.path == "/history/prompt-123":
            return httpx.Response(200, json={})
        return httpx.Response(404)

    executor = ComfyUiRenderExecutor(
        base_url="http://comfy.local",
        api_mode="local",
        timeout_seconds=2,
        poll_interval_seconds=1,
        client=httpx.Client(transport=httpx.MockTransport(handler)),
        monotonic=monotonic,
        sleeper=sleeper,
    )

    with pytest.raises(RenderExecutionError, match="timed out"):
        executor.execute(
            render_job=_render_job(),
            workflow_preset=_workflow_preset(),
            attempt=_attempt(),
        )


def test_render_executor_factory_uses_unconfigured_executor_without_base_url() -> None:
    executor = build_render_executor(WorkerSettings(app_env="test", comfyui_base_url=None))

    assert isinstance(executor, UnconfiguredRenderExecutor)


def test_render_executor_factory_uses_comfyui_executor_when_configured() -> None:
    executor = build_render_executor(
        WorkerSettings(app_env="test", comfyui_base_url="http://comfy.local")
    )

    assert isinstance(executor, ComfyUiRenderExecutor)


def _workflow_preset() -> WorkflowPreset:
    return WorkflowPreset(
        id="workflow-preset-1",
        key="pilot-reels",
        version=1,
        name="Pilot Reels",
        workflow_provider=WorkflowProvider.COMFYUI.value,
        voice_provider=VoiceProvider.NONE.value,
        packaging_provider=PackagingProvider.FFMPEG.value,
        workflow_definition={
            "nodes": {
                "script_prompt": {
                    "class_type": "CLIPTextEncode",
                    "inputs": {"text": "render a compliant host short"},
                }
            }
        },
        input_mapping={"script_text": {"source_type": "content_item", "source_field": "script"}},
        output_mapping={"video_file": {"artifact_type": "video", "output_path": "outputs.video"}},
        created_by_user_id="user-1",
    )


def _render_job() -> RenderJob:
    return RenderJob(
        id="render-job-1",
        content_item_id="content-1",
        workflow_preset_id="workflow-preset-1",
        workflow_preset_key="pilot-reels",
        workflow_preset_version=1,
        workflow_provider=WorkflowProvider.COMFYUI.value,
        voice_provider=VoiceProvider.NONE.value,
        packaging_provider=PackagingProvider.FFMPEG.value,
        input_snapshot={"script_text": "Pilot script"},
        status=RenderJobStatus.RUNNING.value,
        retry_budget=3,
        created_by_user_id="user-1",
    )


def _attempt() -> JobAttempt:
    return JobAttempt(
        id="attempt-1",
        render_job_id="render-job-1",
        attempt_number=1,
        status=JobAttemptStatus.RUNNING.value,
        request_payload={"inputs": {"script_text": "Pilot script"}},
    )
