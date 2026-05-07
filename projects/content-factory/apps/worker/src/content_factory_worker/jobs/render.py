import dramatiq

from content_factory_api.database import get_sessionmaker
from content_factory_api.modules.models import JobAttempt, RenderJob, WorkflowPreset
from content_factory_worker.config import WorkerSettings, get_worker_settings
from content_factory_worker.executors.comfyui import ComfyUiRenderExecutor
from content_factory_worker.orchestration import (
    RenderExecutionError,
    RenderExecutionResult,
    RenderExecutor,
    process_render_job,
)


class UnconfiguredRenderExecutor:
    def execute(
        self,
        *,
        render_job: RenderJob,
        workflow_preset: WorkflowPreset,
        attempt: JobAttempt,
    ) -> RenderExecutionResult:
        _ = (render_job, workflow_preset, attempt)
        raise RenderExecutionError("No render execution provider is configured")


def build_render_executor(settings: WorkerSettings) -> RenderExecutor:
    if settings.comfyui_base_url is None:
        return UnconfiguredRenderExecutor()

    return ComfyUiRenderExecutor(
        base_url=settings.comfyui_base_url,
        api_key=settings.comfyui_api_key,
        api_mode=settings.comfyui_api_mode,
        timeout_seconds=settings.comfyui_timeout_seconds,
        poll_interval_seconds=settings.comfyui_poll_interval_seconds,
        request_timeout_seconds=settings.comfyui_request_timeout_seconds,
    )


@dramatiq.actor(queue_name="render-jobs", max_retries=0)
def process_render_job_message(render_job_id: str) -> None:
    settings = get_worker_settings()
    db_session = get_sessionmaker()()
    try:
        process_render_job(
            render_job_id,
            db_session=db_session,
            executor=build_render_executor(settings),
        )
    finally:
        db_session.close()
