from __future__ import annotations

from collections.abc import Callable
from copy import deepcopy
from time import monotonic as default_monotonic
from time import sleep as default_sleep
from typing import Any, Literal

import httpx

from content_factory_api.modules.models import JobAttempt, RenderJob, WorkflowPreset
from content_factory_worker.orchestration import RenderExecutionError, RenderExecutionResult

ComfyUiApiMode = Literal["local", "cloud"]


class ComfyUiRenderExecutor:
    def __init__(
        self,
        *,
        base_url: str,
        api_key: str | None = None,
        api_mode: ComfyUiApiMode = "local",
        timeout_seconds: float = 300.0,
        poll_interval_seconds: float = 2.0,
        request_timeout_seconds: float = 30.0,
        client: httpx.Client | None = None,
        sleeper: Callable[[float], None] = default_sleep,
        monotonic: Callable[[], float] = default_monotonic,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_mode = api_mode
        self._timeout_seconds = timeout_seconds
        self._poll_interval_seconds = poll_interval_seconds
        self._sleeper = sleeper
        self._monotonic = monotonic
        self._client = client or httpx.Client(timeout=request_timeout_seconds)
        self._headers = {"X-API-Key": api_key} if api_key else {}

    def execute(
        self,
        *,
        render_job: RenderJob,
        workflow_preset: WorkflowPreset,
        attempt: JobAttempt,
    ) -> RenderExecutionResult:
        prompt_response = self._post_prompt(
            render_job=render_job,
            workflow_preset=workflow_preset,
            attempt=attempt,
        )
        prompt_id = _extract_prompt_id(prompt_response)
        terminal_payload = self._wait_for_terminal_payload(prompt_id)

        return RenderExecutionResult(
            provider_job_id=prompt_id,
            response_payload={
                "provider": "comfyui",
                "api_mode": self._api_mode,
                "prompt_response": prompt_response,
                **terminal_payload,
            },
        )

    def _post_prompt(
        self,
        *,
        render_job: RenderJob,
        workflow_preset: WorkflowPreset,
        attempt: JobAttempt,
    ) -> dict[str, Any]:
        prompt = _workflow_prompt(workflow_preset.workflow_definition)
        payload = {
            "prompt": prompt,
            "client_id": render_job.id,
            "extra_data": {
                "content_factory": {
                    "render_job_id": render_job.id,
                    "attempt_id": attempt.id,
                    "workflow_preset_id": workflow_preset.id,
                    "inputs": render_job.input_snapshot,
                }
            },
        }
        return self._request_json("POST", self._prompt_path, json=payload)

    def _wait_for_terminal_payload(self, prompt_id: str) -> dict[str, Any]:
        deadline = self._monotonic() + self._timeout_seconds
        while self._monotonic() <= deadline:
            if self._api_mode == "cloud":
                status_payload = self._request_json(
                    "GET",
                    f"/api/job/{prompt_id}/status",
                )
                status_value = status_payload.get("status")
                if status_value == "completed":
                    history_payload = self._try_get_json(f"/api/history_v2/{prompt_id}")
                    payload: dict[str, Any] = {"status": status_payload}
                    if history_payload is not None:
                        payload["history"] = history_payload
                    return payload
                if status_value in {"failed", "cancelled"}:
                    raise RenderExecutionError(_error_message("ComfyUI job failed", status_payload))
            else:
                history_payload = self._request_json("GET", f"/history/{prompt_id}")
                history_entry = _history_entry(history_payload, prompt_id)
                if history_entry is not None and _is_local_history_success(history_entry):
                    return {"history": history_payload}
                if history_entry is not None and _is_local_history_failure(history_entry):
                    raise RenderExecutionError(_error_message("ComfyUI job failed", history_entry))

            self._sleeper(self._poll_interval_seconds)

        raise RenderExecutionError("ComfyUI render timed out")

    @property
    def _prompt_path(self) -> str:
        return "/api/prompt" if self._api_mode == "cloud" else "/prompt"

    def _try_get_json(self, path: str) -> dict[str, Any] | None:
        try:
            return self._request_json("GET", path)
        except RenderExecutionError:
            return None

    def _request_json(
        self,
        method: Literal["GET", "POST"],
        path: str,
        *,
        json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        try:
            response = self._client.request(
                method,
                f"{self._base_url}{path}",
                headers=self._headers,
                json=json,
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            detail = _response_error_detail(exc.response)
            raise RenderExecutionError(detail) from exc
        except httpx.HTTPError as exc:
            raise RenderExecutionError(f"ComfyUI request failed: {exc}") from exc

        payload = response.json()
        if not isinstance(payload, dict):
            raise RenderExecutionError("ComfyUI returned a non-object response")
        return payload


def _workflow_prompt(workflow_definition: dict[str, Any]) -> dict[str, Any]:
    copied_definition = deepcopy(workflow_definition)
    nodes = copied_definition.get("nodes")
    if isinstance(nodes, dict):
        return nodes
    return copied_definition


def _extract_prompt_id(payload: dict[str, Any]) -> str:
    prompt_id = payload.get("prompt_id")
    if not isinstance(prompt_id, str) or prompt_id.strip() == "":
        raise RenderExecutionError("ComfyUI did not return a prompt_id")
    return prompt_id


def _history_entry(payload: dict[str, Any], prompt_id: str) -> dict[str, Any] | None:
    raw_entry = payload.get(prompt_id)
    return raw_entry if isinstance(raw_entry, dict) else None


def _is_local_history_success(history_entry: dict[str, Any]) -> bool:
    status = history_entry.get("status")
    if isinstance(status, dict):
        if status.get("status_str") == "success":
            return True
        if status.get("completed") is True and status.get("status_str") not in {"error", "failed"}:
            return True
    return "outputs" in history_entry


def _is_local_history_failure(history_entry: dict[str, Any]) -> bool:
    status = history_entry.get("status")
    if not isinstance(status, dict):
        return False
    return status.get("status_str") in {"error", "failed"} or status.get("completed") is False


def _error_message(default_message: str, payload: dict[str, Any]) -> str:
    error = payload.get("error")
    if isinstance(error, dict):
        message = error.get("message") or error.get("exception_message")
        if isinstance(message, str) and message.strip():
            return message

    exception_message = payload.get("exception_message")
    if isinstance(exception_message, str) and exception_message.strip():
        return exception_message

    return default_message


def _response_error_detail(response: httpx.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        payload = None

    if isinstance(payload, dict):
        detail = payload.get("detail") or payload.get("error")
        if isinstance(detail, str) and detail.strip():
            return detail
        if isinstance(detail, dict):
            message = detail.get("message")
            if isinstance(message, str) and message.strip():
                return message

    return f"ComfyUI request failed with status {response.status_code}"
