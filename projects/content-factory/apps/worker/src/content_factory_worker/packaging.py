from __future__ import annotations

import json
from dataclasses import dataclass
from io import BytesIO
from typing import Literal, Protocol
from zipfile import ZIP_DEFLATED, ZipFile

from sqlalchemy import select
from sqlalchemy.orm import Session

from content_factory_api.modules.domain import (
    ContentStatus,
    JobAttemptStatus,
    PublishPackageStatus,
    RenderJobStatus,
)
from content_factory_api.modules.models import (
    ContentItem,
    JobAttempt,
    PublishPackage,
    RenderJob,
    WorkflowPreset,
)
from content_factory_api.modules.schemas import WorkflowOutputBinding

ProcessingStatus = Literal["ready", "failed", "skipped_ready", "skipped_running"]


class PublishPackageError(RuntimeError):
    """Raised when a publish package cannot be assembled from render outputs."""


class PublishPackageNotFoundError(LookupError):
    """Raised when a queued package message references a missing package."""


@dataclass(frozen=True)
class PublishPackageResult:
    package_object_key: str
    manifest_payload: dict[str, object]
    byte_size: int


@dataclass(frozen=True)
class PublishPackageProcessingOutcome:
    publish_package_id: str
    status: ProcessingStatus


class PackageStorage(Protocol):
    def upload_package(self, *, object_key: str, data: bytes, content_type: str) -> None:
        """Persist package bytes to object storage."""


class PublishPackager(Protocol):
    def package(
        self,
        *,
        publish_package: PublishPackage,
        render_job: RenderJob,
        workflow_preset: WorkflowPreset,
        content_item: ContentItem,
        attempt: JobAttempt,
    ) -> PublishPackageResult:
        """Build and persist a package for one successful render attempt."""


class ZipPublishPackager:
    def __init__(
        self,
        *,
        storage: PackageStorage,
        object_key_prefix: str = "publish-packages",
    ) -> None:
        self._storage = storage
        self._object_key_prefix = object_key_prefix.strip("/") or "publish-packages"

    def package(
        self,
        *,
        publish_package: PublishPackage,
        render_job: RenderJob,
        workflow_preset: WorkflowPreset,
        content_item: ContentItem,
        attempt: JobAttempt,
    ) -> PublishPackageResult:
        manifest = build_publish_manifest(
            publish_package=publish_package,
            render_job=render_job,
            workflow_preset=workflow_preset,
            content_item=content_item,
            attempt=attempt,
        )
        manual_publish = manifest.get("manual_publish")
        hashtags: object = []
        if isinstance(manual_publish, dict):
            hashtags = manual_publish.get("hashtags", [])
        package_bytes = _zip_manifest_bundle(
            manifest=manifest,
            title=content_item.title,
            caption=content_item.script,
            hashtags=hashtags,
            provider_payload=attempt.response_payload,
        )
        object_key = (
            f"{self._object_key_prefix}/{content_item.id}/{publish_package.id}.zip"
        )
        self._storage.upload_package(
            object_key=object_key,
            data=package_bytes,
            content_type="application/zip",
        )
        return PublishPackageResult(
            package_object_key=object_key,
            manifest_payload=manifest,
            byte_size=len(package_bytes),
        )


def process_publish_package(
    publish_package_id: str,
    *,
    db_session: Session,
    packager: PublishPackager,
) -> PublishPackageProcessingOutcome:
    publish_package = db_session.get(PublishPackage, publish_package_id)
    if publish_package is None:
        raise PublishPackageNotFoundError(f"Publish package '{publish_package_id}' not found")

    if publish_package.status == PublishPackageStatus.READY.value:
        return PublishPackageProcessingOutcome(publish_package.id, "skipped_ready")
    if publish_package.status == PublishPackageStatus.RUNNING.value:
        return PublishPackageProcessingOutcome(publish_package.id, "skipped_running")

    try:
        render_job = _get_render_job(db_session, publish_package.render_job_id)
        content_item = _get_content_item(db_session, publish_package.content_item_id)
        workflow_preset = _get_workflow_preset(db_session, render_job.workflow_preset_id)
        attempt = _latest_successful_attempt(db_session, render_job.id)
        _validate_package_inputs(render_job=render_job, content_item=content_item, attempt=attempt)
        assert attempt is not None
    except PublishPackageError as exc:
        return _fail_package(db_session, publish_package, str(exc))

    publish_package.status = PublishPackageStatus.RUNNING.value
    publish_package.error_message = None
    db_session.commit()

    try:
        result = packager.package(
            publish_package=publish_package,
            render_job=render_job,
            workflow_preset=workflow_preset,
            content_item=content_item,
            attempt=attempt,
        )
    except PublishPackageError as exc:
        return _fail_package(db_session, publish_package, str(exc))
    except Exception as exc:
        return _fail_package(db_session, publish_package, f"{exc.__class__.__name__}: {exc}")

    publish_package.status = PublishPackageStatus.READY.value
    publish_package.package_object_key = result.package_object_key
    publish_package.manifest_payload = result.manifest_payload
    publish_package.byte_size = result.byte_size
    publish_package.error_message = None
    db_session.commit()
    return PublishPackageProcessingOutcome(publish_package.id, "ready")


def build_publish_manifest(
    *,
    publish_package: PublishPackage,
    render_job: RenderJob,
    workflow_preset: WorkflowPreset,
    content_item: ContentItem,
    attempt: JobAttempt,
) -> dict[str, object]:
    artifacts = _resolve_artifacts(workflow_preset.output_mapping, attempt.response_payload)
    hashtags = _hashtags_from_payload(attempt.response_payload)
    planned_publish_at = (
        content_item.planned_publish_at.isoformat() if content_item.planned_publish_at else None
    )
    return {
        "schema_version": 1,
        "package_id": publish_package.id,
        "render_job_id": render_job.id,
        "content_item": {
            "id": content_item.id,
            "title": content_item.title,
            "script": content_item.script,
            "channel": content_item.channel,
            "planned_publish_at": planned_publish_at,
        },
        "workflow": {
            "preset_id": workflow_preset.id,
            "key": workflow_preset.key,
            "version": workflow_preset.version,
            "workflow_provider": render_job.workflow_provider,
            "voice_provider": render_job.voice_provider,
            "packaging_provider": render_job.packaging_provider,
        },
        "artifacts": artifacts,
        "manual_publish": {
            "title": content_item.title,
            "caption": content_item.script,
            "hashtags": hashtags,
        },
        "audit": {
            "created_by_user_id": publish_package.created_by_user_id,
            "render_attempt_id": attempt.id,
            "render_provider_job_id": attempt.provider_job_id,
        },
    }


def _get_render_job(db_session: Session, render_job_id: str) -> RenderJob:
    render_job = db_session.get(RenderJob, render_job_id)
    if render_job is None:
        raise PublishPackageError(f"Render job '{render_job_id}' not found")
    return render_job


def _get_content_item(db_session: Session, content_item_id: str) -> ContentItem:
    content_item = db_session.get(ContentItem, content_item_id)
    if content_item is None:
        raise PublishPackageError(f"Content item '{content_item_id}' not found")
    return content_item


def _get_workflow_preset(db_session: Session, workflow_preset_id: str) -> WorkflowPreset:
    workflow_preset = db_session.get(WorkflowPreset, workflow_preset_id)
    if workflow_preset is None:
        raise PublishPackageError(f"Workflow preset '{workflow_preset_id}' not found")
    return workflow_preset


def _latest_successful_attempt(db_session: Session, render_job_id: str) -> JobAttempt | None:
    return db_session.scalar(
        select(JobAttempt)
        .where(
            JobAttempt.render_job_id == render_job_id,
            JobAttempt.status == JobAttemptStatus.SUCCEEDED.value,
        )
        .order_by(JobAttempt.attempt_number.desc())
    )


def _validate_package_inputs(
    *,
    render_job: RenderJob,
    content_item: ContentItem,
    attempt: JobAttempt | None,
) -> None:
    if render_job.status != RenderJobStatus.SUCCEEDED.value:
        raise PublishPackageError("Render job must be succeeded before packaging")
    if content_item.status != ContentStatus.APPROVED.value:
        raise PublishPackageError("Content item must be approved before packaging")
    if attempt is None:
        raise PublishPackageError("Render job has no successful attempt to package")


def _fail_package(
    db_session: Session,
    publish_package: PublishPackage,
    error_message: str,
) -> PublishPackageProcessingOutcome:
    publish_package.status = PublishPackageStatus.FAILED.value
    publish_package.error_message = error_message
    db_session.commit()
    return PublishPackageProcessingOutcome(publish_package.id, "failed")


def _resolve_artifacts(
    output_mapping: dict[str, object],
    response_payload: dict[str, object],
) -> list[dict[str, object]]:
    outputs = _extract_outputs(response_payload)
    artifacts: list[dict[str, object]] = []
    for output_name, raw_binding in output_mapping.items():
        if not isinstance(raw_binding, dict):
            raise PublishPackageError(f"Output mapping for '{output_name}' is invalid")
        binding = WorkflowOutputBinding.model_validate(raw_binding)
        artifact_value = _resolve_artifact_value(
            response_payload=response_payload,
            outputs=outputs,
            output_name=output_name,
            output_path=binding.output_path,
        )
        if artifact_value is None:
            raise PublishPackageError(
                f"Render output '{output_name}' was not found at '{binding.output_path}'",
            )
        artifacts.append(
            {
                "name": output_name,
                "artifact_type": binding.artifact_type.value,
                "output_path": binding.output_path,
                "value": artifact_value,
            }
        )
    return artifacts


def _resolve_artifact_value(
    *,
    response_payload: dict[str, object],
    outputs: dict[str, object],
    output_name: str,
    output_path: str,
) -> object | None:
    candidates = [
        _resolve_dotted_path(response_payload, output_path),
        _resolve_dotted_path(outputs, output_path.removeprefix("outputs.")),
        outputs.get(output_name),
    ]
    for candidate in candidates:
        if candidate is not None:
            return candidate
    return None


def _extract_outputs(response_payload: dict[str, object]) -> dict[str, object]:
    outputs = response_payload.get("outputs")
    if isinstance(outputs, dict):
        return outputs

    history = response_payload.get("history")
    nested_outputs = _find_first_outputs(history)
    if nested_outputs is not None:
        return nested_outputs

    return {}


def _find_first_outputs(value: object) -> dict[str, object] | None:
    if isinstance(value, dict):
        outputs = value.get("outputs")
        if isinstance(outputs, dict):
            return outputs
        for nested_value in value.values():
            nested_outputs = _find_first_outputs(nested_value)
            if nested_outputs is not None:
                return nested_outputs
    if isinstance(value, list):
        for nested_value in value:
            nested_outputs = _find_first_outputs(nested_value)
            if nested_outputs is not None:
                return nested_outputs
    return None


def _resolve_dotted_path(payload: dict[str, object], dotted_path: str) -> object | None:
    current: object = payload
    for part in dotted_path.split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def _hashtags_from_payload(response_payload: dict[str, object]) -> list[str]:
    raw_hashtags = response_payload.get("hashtags")
    if not isinstance(raw_hashtags, list):
        return []
    return [value for value in raw_hashtags if isinstance(value, str)]


def _zip_manifest_bundle(
    *,
    manifest: dict[str, object],
    title: str,
    caption: str,
    hashtags: object,
    provider_payload: dict[str, object],
) -> bytes:
    if not isinstance(hashtags, list):
        hashtags = []
    buffer = BytesIO()
    with ZipFile(buffer, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr("manifest.json", _json_bytes(manifest))
        archive.writestr("title.txt", title)
        archive.writestr("caption.txt", caption)
        archive.writestr("hashtags.txt", "\n".join(str(tag) for tag in hashtags))
        archive.writestr("provider-output.json", _json_bytes(provider_payload))
    return buffer.getvalue()


def _json_bytes(payload: dict[str, object]) -> bytes:
    return json.dumps(payload, indent=2, sort_keys=True).encode("utf-8")
