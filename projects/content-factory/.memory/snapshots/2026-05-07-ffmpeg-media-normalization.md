Project Path: content-factory

Source Tree:

```txt
content-factory
└── apps
    └── worker
        ├── src
        │   └── content_factory_worker
        │       ├── config.py
        │       ├── jobs
        │       │   └── packaging.py
        │       └── packaging.py
        └── tests
            └── test_publish_package_orchestration.py

```

`apps/worker/src/content_factory_worker/config.py`:

```py
from functools import lru_cache
from typing import Literal

from pydantic import AnyHttpUrl, Field, PositiveFloat, PositiveInt, RedisDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class WorkerSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    worker_name: str = "content-factory-worker"
    app_env: Literal["development", "test", "staging", "production"] = "development"
    redis_url: RedisDsn = Field(default_factory=lambda: RedisDsn("redis://localhost:6379/0"))
    worker_concurrency: PositiveInt = 1
    comfyui_base_url: str | None = None
    comfyui_api_key: str | None = None
    comfyui_api_mode: Literal["local", "cloud"] = "local"
    comfyui_timeout_seconds: PositiveFloat = 300.0
    comfyui_poll_interval_seconds: PositiveFloat = 2.0
    comfyui_request_timeout_seconds: PositiveFloat = 30.0
    s3_endpoint: AnyHttpUrl = Field(default_factory=lambda: AnyHttpUrl("http://localhost:9000"))
    s3_region: str = "us-east-1"
    s3_bucket: str = Field(default="content-factory-assets", min_length=3)
    s3_access_key: str = Field(default="minioadmin", min_length=1)
    s3_secret_key: str = Field(default="minioadmin", min_length=1)
    s3_force_path_style: bool = True
    ffmpeg_path: str = Field(default="ffmpeg", min_length=1)
    ffmpeg_timeout_seconds: PositiveFloat = 300.0
    sentry_dsn: str | None = None

    @field_validator("comfyui_base_url", "comfyui_api_key", mode="before")
    @classmethod
    def normalize_optional_string(cls, value: object) -> object:
        if isinstance(value, str) and value.strip() == "":
            return None
        return value


@lru_cache(maxsize=1)
def get_worker_settings() -> WorkerSettings:
    return WorkerSettings()

```

`apps/worker/src/content_factory_worker/jobs/packaging.py`:

```py
from io import BytesIO
from urllib.parse import urlparse

import boto3
import dramatiq
from botocore.client import Config

from content_factory_api.database import get_sessionmaker
from content_factory_worker.config import WorkerSettings, get_worker_settings
from content_factory_worker.packaging import (
    FfmpegMediaNormalizer,
    PackageStorage,
    PublishPackageError,
    PublishPackager,
    ZipPublishPackager,
    process_publish_package,
)


class S3PackageStorage(PackageStorage):
    def __init__(self, settings: WorkerSettings) -> None:
        addressing_style = "path" if settings.s3_force_path_style else "virtual"
        self._bucket = settings.s3_bucket
        self._client = boto3.client(
            "s3",
            endpoint_url=str(settings.s3_endpoint).rstrip("/"),
            region_name=settings.s3_region,
            aws_access_key_id=settings.s3_access_key,
            aws_secret_access_key=settings.s3_secret_key,
            config=Config(signature_version="s3v4", s3={"addressing_style": addressing_style}),
        )

    def upload_package(self, *, object_key: str, data: bytes, content_type: str) -> None:
        self._client.upload_fileobj(
            BytesIO(data),
            self._bucket,
            object_key,
            ExtraArgs={"ContentType": content_type},
        )

    def download_artifact(self, artifact_reference: str) -> bytes:
        bucket, key = self._resolve_artifact_reference(artifact_reference)
        buffer = BytesIO()
        self._client.download_fileobj(bucket, key, buffer)
        return buffer.getvalue()

    def _resolve_artifact_reference(self, artifact_reference: str) -> tuple[str, str]:
        parsed = urlparse(artifact_reference)
        if parsed.scheme == "s3":
            bucket = parsed.netloc
            key = parsed.path.lstrip("/")
            if bucket != self._bucket:
                raise PublishPackageError(
                    f"Artifact bucket '{bucket}' does not match configured bucket '{self._bucket}'",
                )
            if key == "":
                raise PublishPackageError("S3 artifact reference has no object key")
            return bucket, key
        if parsed.scheme in {"http", "https"}:
            raise PublishPackageError("HTTP media artifact references are not supported")
        if parsed.scheme:
            raise PublishPackageError(
                f"Unsupported media artifact reference scheme '{parsed.scheme}'",
            )
        object_key = artifact_reference.lstrip("/")
        if object_key == "":
            raise PublishPackageError("Media artifact reference has no object key")
        return self._bucket, object_key


def build_publish_packager(settings: WorkerSettings) -> PublishPackager:
    return ZipPublishPackager(
        storage=S3PackageStorage(settings),
        media_normalizer=FfmpegMediaNormalizer(
            ffmpeg_path=settings.ffmpeg_path,
            timeout_seconds=settings.ffmpeg_timeout_seconds,
        ),
    )


@dramatiq.actor(queue_name="publish-packages", max_retries=0)
def process_publish_package_message(publish_package_id: str) -> None:
    settings = get_worker_settings()
    db_session = get_sessionmaker()()
    try:
        process_publish_package(
            publish_package_id,
            db_session=db_session,
            packager=build_publish_packager(settings),
        )
    finally:
        db_session.close()

```

`apps/worker/src/content_factory_worker/packaging.py`:

```py
from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path, PurePosixPath
from tempfile import TemporaryDirectory
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

ProcessingStatus = Literal[
    "ready",
    "failed",
    "skipped_ready",
    "skipped_running",
    "skipped_cancelled",
]


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
class NormalizedMedia:
    package_path: str
    data: bytes
    content_type: str
    container: str
    profile: str


@dataclass(frozen=True)
class PackageFile:
    path: str
    data: bytes


@dataclass(frozen=True)
class PublishPackageProcessingOutcome:
    publish_package_id: str
    status: ProcessingStatus


class PackageStorage(Protocol):
    def upload_package(self, *, object_key: str, data: bytes, content_type: str) -> None:
        """Persist package bytes to object storage."""

    def download_artifact(self, artifact_reference: str) -> bytes:
        """Load render output bytes referenced by a successful provider payload."""


class MediaNormalizer(Protocol):
    def normalize_video(self, *, source_reference: str, source_bytes: bytes) -> NormalizedMedia:
        """Normalize one source video into a package-ready media artifact."""


class FfmpegMediaNormalizer:
    def __init__(
        self,
        *,
        ffmpeg_path: str = "ffmpeg",
        timeout_seconds: float = 300.0,
    ) -> None:
        self._ffmpeg_path = ffmpeg_path
        self._timeout_seconds = timeout_seconds

    def normalize_video(self, *, source_reference: str, source_bytes: bytes) -> NormalizedMedia:
        with TemporaryDirectory(prefix="content-factory-ffmpeg-") as temp_dir:
            input_path = Path(temp_dir) / f"input{_source_suffix(source_reference)}"
            output_path = Path(temp_dir) / "video.mp4"
            input_path.write_bytes(source_bytes)

            command = [
                self._ffmpeg_path,
                "-y",
                "-hide_banner",
                "-loglevel",
                "error",
                "-i",
                str(input_path),
                "-map",
                "0:v:0",
                "-map",
                "0:a:0?",
                "-vf",
                (
                    "scale=1080:1920:force_original_aspect_ratio=decrease,"
                    "pad=1080:1920:(ow-iw)/2:(oh-ih)/2,setsar=1"
                ),
                "-r",
                "30",
                "-c:v",
                "libx264",
                "-profile:v",
                "high",
                "-pix_fmt",
                "yuv420p",
                "-preset",
                "veryfast",
                "-crf",
                "20",
                "-c:a",
                "aac",
                "-b:a",
                "128k",
                "-ar",
                "48000",
                "-movflags",
                "+faststart",
                str(output_path),
            ]

            try:
                completed = subprocess.run(
                    command,
                    capture_output=True,
                    check=False,
                    timeout=self._timeout_seconds,
                )
            except FileNotFoundError as exc:
                raise PublishPackageError(
                    f"FFmpeg binary '{self._ffmpeg_path}' was not found",
                ) from exc
            except subprocess.TimeoutExpired as exc:
                raise PublishPackageError(
                    f"FFmpeg normalization timed out after {self._timeout_seconds:g}s",
                ) from exc

            if completed.returncode != 0:
                stderr = completed.stderr.decode("utf-8", errors="replace").strip()
                detail = stderr or f"exit code {completed.returncode}"
                raise PublishPackageError(f"FFmpeg normalization failed: {detail}")
            if not output_path.exists():
                raise PublishPackageError("FFmpeg normalization did not produce video.mp4")

            return NormalizedMedia(
                package_path="video.mp4",
                data=output_path.read_bytes(),
                content_type="video/mp4",
                container="mp4",
                profile="short_vertical_1080p_h264_aac",
            )


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
        media_normalizer: MediaNormalizer | None = None,
        object_key_prefix: str = "publish-packages",
    ) -> None:
        self._storage = storage
        self._media_normalizer = media_normalizer or FfmpegMediaNormalizer()
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
        video_file = self._normalize_primary_video(manifest)
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
            media_files=[video_file],
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

    def _normalize_primary_video(self, manifest: dict[str, object]) -> PackageFile:
        video_artifact = _primary_video_artifact(manifest)
        source_reference = _video_artifact_reference(video_artifact)
        try:
            source_bytes = self._storage.download_artifact(source_reference)
        except PublishPackageError:
            raise
        except Exception as exc:
            raise PublishPackageError(
                f"Could not download video artifact '{source_reference}': {exc}",
            ) from exc

        normalized = self._media_normalizer.normalize_video(
            source_reference=source_reference,
            source_bytes=source_bytes,
        )
        manifest["normalized_artifacts"] = [
            _normalized_video_manifest(
                source_artifact=video_artifact,
                source_reference=source_reference,
                normalized=normalized,
            )
        ]
        return PackageFile(path=normalized.package_path, data=normalized.data)


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
    if publish_package.status == PublishPackageStatus.CANCELLED.value:
        return PublishPackageProcessingOutcome(publish_package.id, "skipped_cancelled")

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

    db_session.refresh(publish_package)
    if publish_package.status == PublishPackageStatus.CANCELLED.value:
        return PublishPackageProcessingOutcome(publish_package.id, "skipped_cancelled")

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


def _primary_video_artifact(manifest: dict[str, object]) -> dict[str, object]:
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, list):
        raise PublishPackageError("Publish manifest has no artifact list")
    for artifact in artifacts:
        if isinstance(artifact, dict) and artifact.get("artifact_type") == "video":
            return artifact
    raise PublishPackageError("Publish manifest has no video artifact to normalize")


def _video_artifact_reference(video_artifact: dict[str, object]) -> str:
    value = video_artifact.get("value")
    if not isinstance(value, str) or value.strip() == "":
        name = video_artifact.get("name")
        artifact_name = name if isinstance(name, str) else "video"
        raise PublishPackageError(f"Video artifact '{artifact_name}' does not reference media")
    return value


def _normalized_video_manifest(
    *,
    source_artifact: dict[str, object],
    source_reference: str,
    normalized: NormalizedMedia,
) -> dict[str, object]:
    return {
        "name": "video",
        "artifact_type": "video",
        "package_path": normalized.package_path,
        "content_type": normalized.content_type,
        "container": normalized.container,
        "profile": normalized.profile,
        "source": {
            "name": _artifact_string(source_artifact, "name"),
            "output_path": _artifact_string(source_artifact, "output_path"),
            "value": source_reference,
        },
    }


def _artifact_string(artifact: dict[str, object], key: str) -> str:
    value = artifact.get(key)
    return value if isinstance(value, str) else ""


def _source_suffix(source_reference: str) -> str:
    suffix = PurePosixPath(source_reference).suffix.lower()
    if suffix and len(suffix) <= 10:
        return suffix
    return ".bin"


def _zip_manifest_bundle(
    *,
    manifest: dict[str, object],
    title: str,
    caption: str,
    hashtags: object,
    provider_payload: dict[str, object],
    media_files: list[PackageFile] | None = None,
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
        for media_file in media_files or []:
            archive.writestr(media_file.path, media_file.data)
    return buffer.getvalue()


def _json_bytes(payload: dict[str, object]) -> bytes:
    return json.dumps(payload, indent=2, sort_keys=True).encode("utf-8")

```

`apps/worker/tests/test_publish_package_orchestration.py`:

```py
import io
import json
from collections.abc import Generator
from pathlib import Path
from zipfile import ZipFile

import pytest
from sqlalchemy.orm import Session

from content_factory_api.config import get_settings
from content_factory_api.database import get_sessionmaker, init_database, reset_database_caches
from content_factory_api.modules.domain import (
    ContentChannel,
    ContentStatus,
    JobAttemptStatus,
    PackagingProvider,
    PublishPackageStatus,
    RenderJobStatus,
    UserRole,
    UserStatus,
    VoiceProvider,
    WorkflowProvider,
)
from content_factory_api.modules.models import (
    Avatar,
    Brand,
    ContentItem,
    JobAttempt,
    PublishPackage,
    RenderJob,
    User,
    WorkflowPreset,
)
from content_factory_worker.packaging import (
    FfmpegMediaNormalizer,
    MediaNormalizer,
    NormalizedMedia,
    PackageStorage,
    PublishPackageError,
    ZipPublishPackager,
    process_publish_package,
)


@pytest.fixture
def db_session(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Generator[Session, None, None]:
    db_path = tmp_path / "publish-package.db"
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
    get_settings.cache_clear()
    reset_database_caches()
    init_database()
    session = get_sessionmaker()()
    try:
        yield session
    finally:
        session.close()
        get_settings.cache_clear()
        reset_database_caches()


class MemoryPackageStorage(PackageStorage):
    def __init__(self, artifacts: dict[str, bytes] | None = None) -> None:
        self.objects: dict[str, bytes] = {}
        self.artifacts = artifacts or {}
        self.downloaded_artifacts: list[str] = []

    def upload_package(self, *, object_key: str, data: bytes, content_type: str) -> None:
        assert content_type == "application/zip"
        self.objects[object_key] = data

    def download_artifact(self, artifact_reference: str) -> bytes:
        self.downloaded_artifacts.append(artifact_reference)
        return self.artifacts[artifact_reference]


class FakeMediaNormalizer(MediaNormalizer):
    def __init__(self, output: bytes = b"normalized mp4 bytes") -> None:
        self.output = output
        self.sources: list[tuple[str, bytes]] = []

    def normalize_video(self, *, source_reference: str, source_bytes: bytes) -> NormalizedMedia:
        self.sources.append((source_reference, source_bytes))
        return NormalizedMedia(
            package_path="video.mp4",
            data=self.output,
            content_type="video/mp4",
            container="mp4",
            profile="test-profile",
        )


class FailingMediaNormalizer(MediaNormalizer):
    def normalize_video(self, *, source_reference: str, source_bytes: bytes) -> NormalizedMedia:
        raise PublishPackageError(f"Could not normalize {source_reference}")


def test_process_publish_package_builds_manifest_zip(db_session: Session) -> None:
    video_reference = "s3://content-factory-assets/renders/video.mp4"
    publish_package = _seed_publish_package(
        db_session,
        response_payload={
            "outputs": {
                "video_file": video_reference,
                "cover_file": "s3://content-factory-assets/renders/cover.jpg",
            },
            "hashtags": ["#inflave"],
        },
    )
    storage = MemoryPackageStorage(artifacts={video_reference: b"raw render video"})
    normalizer = FakeMediaNormalizer()

    outcome = process_publish_package(
        publish_package.id,
        db_session=db_session,
        packager=ZipPublishPackager(storage=storage, media_normalizer=normalizer),
    )

    db_session.refresh(publish_package)
    assert outcome.status == "ready"
    assert publish_package.status == PublishPackageStatus.READY.value
    assert publish_package.package_object_key in storage.objects
    assert publish_package.byte_size is not None and publish_package.byte_size > 0
    assert publish_package.manifest_payload["manual_publish"]["title"] == "Pilot short"
    assert publish_package.manifest_payload["artifacts"][0]["name"] == "video_file"

    archive = ZipFile(io.BytesIO(storage.objects[publish_package.package_object_key or ""]))
    assert sorted(archive.namelist()) == [
        "caption.txt",
        "hashtags.txt",
        "manifest.json",
        "provider-output.json",
        "title.txt",
        "video.mp4",
    ]
    assert archive.read("video.mp4") == b"normalized mp4 bytes"
    manifest = json.loads(archive.read("manifest.json").decode("utf-8"))
    assert manifest["render_job_id"] == publish_package.render_job_id
    assert manifest["manual_publish"]["hashtags"] == ["#inflave"]
    assert manifest["normalized_artifacts"] == [
        {
            "name": "video",
            "artifact_type": "video",
            "package_path": "video.mp4",
            "content_type": "video/mp4",
            "container": "mp4",
            "profile": "test-profile",
            "source": {
                "name": "video_file",
                "output_path": "outputs.video_file",
                "value": video_reference,
            },
        }
    ]
    assert storage.downloaded_artifacts == [video_reference]
    assert normalizer.sources == [(video_reference, b"raw render video")]


def test_process_publish_package_marks_missing_outputs_failed(db_session: Session) -> None:
    publish_package = _seed_publish_package(db_session, response_payload={"outputs": {}})

    outcome = process_publish_package(
        publish_package.id,
        db_session=db_session,
        packager=ZipPublishPackager(
            storage=MemoryPackageStorage(),
            media_normalizer=FakeMediaNormalizer(),
        ),
    )

    db_session.refresh(publish_package)
    assert outcome.status == "failed"
    assert publish_package.status == PublishPackageStatus.FAILED.value
    assert publish_package.error_message is not None
    assert "video_file" in publish_package.error_message


def test_process_publish_package_marks_normalization_failure_failed(db_session: Session) -> None:
    video_reference = "s3://content-factory-assets/renders/video.mp4"
    publish_package = _seed_publish_package(
        db_session,
        response_payload={
            "outputs": {
                "video_file": video_reference,
                "cover_file": "s3://content-factory-assets/renders/cover.jpg",
            }
        },
    )

    outcome = process_publish_package(
        publish_package.id,
        db_session=db_session,
        packager=ZipPublishPackager(
            storage=MemoryPackageStorage(artifacts={video_reference: b"raw render video"}),
            media_normalizer=FailingMediaNormalizer(),
        ),
    )

    db_session.refresh(publish_package)
    assert outcome.status == "failed"
    assert publish_package.status == PublishPackageStatus.FAILED.value
    assert publish_package.error_message == f"Could not normalize {video_reference}"


def test_cancelled_publish_package_is_not_processed(db_session: Session) -> None:
    publish_package = _seed_publish_package(
        db_session,
        response_payload={
            "outputs": {
                "video_file": "s3://content-factory-assets/renders/video.mp4",
                "cover_file": "s3://content-factory-assets/renders/cover.jpg",
            }
        },
    )
    publish_package.status = PublishPackageStatus.CANCELLED.value
    db_session.commit()
    storage = MemoryPackageStorage()

    outcome = process_publish_package(
        publish_package.id,
        db_session=db_session,
        packager=ZipPublishPackager(storage=storage, media_normalizer=FakeMediaNormalizer()),
    )

    db_session.refresh(publish_package)
    assert outcome.status == "skipped_cancelled"
    assert publish_package.status == PublishPackageStatus.CANCELLED.value
    assert storage.objects == {}


def test_ffmpeg_media_normalizer_reports_missing_binary() -> None:
    normalizer = FfmpegMediaNormalizer(
        ffmpeg_path="/definitely/missing/content-factory-ffmpeg",
        timeout_seconds=1.0,
    )

    with pytest.raises(PublishPackageError, match="FFmpeg binary"):
        normalizer.normalize_video(
            source_reference="s3://content-factory-assets/renders/video.mp4",
            source_bytes=b"raw render video",
        )


def _seed_publish_package(
    db_session: Session,
    *,
    response_payload: dict[str, object],
) -> PublishPackage:
    user = User(
        email="owner@inflave.test",
        display_name="Owner",
        role=UserRole.OWNER.value,
        status=UserStatus.ACTIVE.value,
        password_hash="hash",
    )
    db_session.add(user)
    db_session.flush()

    brand = Brand(
        name="Inflave",
        voice_notes="Confident, compliant, concise.",
        created_by_user_id=user.id,
    )
    db_session.add(brand)
    db_session.flush()

    avatar = Avatar(
        brand_id=brand.id,
        name="Primary Host",
        persona_notes="Human-like pilot avatar.",
        created_by_user_id=user.id,
    )
    db_session.add(avatar)
    db_session.flush()

    content_item = ContentItem(
        brand_id=brand.id,
        avatar_id=avatar.id,
        title="Pilot short",
        script="A careful, platform-safe short script.",
        channel=ContentChannel.YOUTUBE_SHORTS.value,
        status=ContentStatus.APPROVED.value,
        created_by_user_id=user.id,
    )
    db_session.add(content_item)
    db_session.flush()

    workflow_preset = WorkflowPreset(
        key="pilot-reels",
        version=1,
        name="Pilot Reels",
        workflow_provider=WorkflowProvider.COMFYUI.value,
        voice_provider=VoiceProvider.NONE.value,
        packaging_provider=PackagingProvider.FFMPEG.value,
        workflow_definition={"nodes": {"script_prompt": {"class_type": "CLIPTextEncode"}}},
        input_mapping={"script_text": {"source_type": "content_item", "source_field": "script"}},
        output_mapping={
            "video_file": {"artifact_type": "video", "output_path": "outputs.video_file"},
            "cover_file": {"artifact_type": "cover_image", "output_path": "outputs.cover_file"},
        },
        created_by_user_id=user.id,
    )
    db_session.add(workflow_preset)
    db_session.flush()

    render_job = RenderJob(
        content_item_id=content_item.id,
        workflow_preset_id=workflow_preset.id,
        workflow_preset_key=workflow_preset.key,
        workflow_preset_version=workflow_preset.version,
        workflow_provider=workflow_preset.workflow_provider,
        voice_provider=workflow_preset.voice_provider,
        packaging_provider=workflow_preset.packaging_provider,
        input_snapshot={"script_text": content_item.script},
        status=RenderJobStatus.SUCCEEDED.value,
        retry_budget=1,
        created_by_user_id=user.id,
    )
    db_session.add(render_job)
    db_session.flush()

    attempt = JobAttempt(
        render_job_id=render_job.id,
        attempt_number=1,
        status=JobAttemptStatus.SUCCEEDED.value,
        provider_job_id="comfyui-1",
        request_payload={"inputs": render_job.input_snapshot},
        response_payload=response_payload,
    )
    db_session.add(attempt)
    db_session.flush()

    publish_package = PublishPackage(
        render_job_id=render_job.id,
        content_item_id=content_item.id,
        status=PublishPackageStatus.QUEUED.value,
        created_by_user_id=user.id,
    )
    db_session.add(publish_package)
    db_session.commit()
    return publish_package

```