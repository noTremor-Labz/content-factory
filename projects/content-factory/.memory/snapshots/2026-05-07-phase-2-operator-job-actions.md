Project Path: content-factory

Source Tree:

```txt
content-factory
├── apps
│   ├── api
│   │   ├── src
│   │   │   └── content_factory_api
│   │   │       └── modules
│   │   │           ├── domain.py
│   │   │           ├── exports.py
│   │   │           └── render.py
│   │   └── tests
│   │       ├── test_publish_packages.py
│   │       └── test_render_contracts.py
│   ├── web
│   │   └── src
│   │       ├── app
│   │       │   ├── App.test.tsx
│   │       │   └── App.tsx
│   │       ├── features
│   │       │   ├── export
│   │       │   │   └── ExportPanel.tsx
│   │       │   └── render
│   │       │       └── RenderPanel.tsx
│   │       └── shared
│   │           └── api
│   │               └── client.ts
│   └── worker
│       ├── src
│       │   └── content_factory_worker
│       │       ├── orchestration.py
│       │       └── packaging.py
│       └── tests
│           ├── test_publish_package_orchestration.py
│           └── test_render_orchestration.py
└── packages
    └── contracts
        ├── openapi
        │   └── content-factory.openapi.json
        └── src
            └── generated
                └── api.ts

```

`apps/api/src/content_factory_api/modules/domain.py`:

```py
from enum import StrEnum


class UserRole(StrEnum):
    OWNER = "owner"
    OPERATOR = "operator"
    REVIEWER = "reviewer"
    VIEWER = "viewer"


class UserStatus(StrEnum):
    ACTIVE = "active"
    DISABLED = "disabled"


class AssetStatus(StrEnum):
    PENDING_UPLOAD = "pending_upload"
    READY = "ready"
    FAILED = "failed"


class AvatarStatus(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"


class IdentityPackStatus(StrEnum):
    DRAFT = "draft"
    READY = "ready"


class ContentChannel(StrEnum):
    INSTAGRAM_REELS = "instagram_reels"
    YOUTUBE_SHORTS = "youtube_shorts"


class WorkflowProvider(StrEnum):
    COMFYUI = "comfyui"


class VoiceProvider(StrEnum):
    NONE = "none"


class PackagingProvider(StrEnum):
    FFMPEG = "ffmpeg"


class WorkflowInputSourceType(StrEnum):
    CONTENT_ITEM = "content_item"
    BRAND = "brand"
    AVATAR = "avatar"
    IDENTITY_PACK = "identity_pack"
    LITERAL = "literal"


class OutputArtifactType(StrEnum):
    VIDEO = "video"
    COVER_IMAGE = "cover_image"
    CAPTION_TEXT = "caption_text"
    MANIFEST = "manifest"


class ContentStatus(StrEnum):
    DRAFT = "draft"
    PLANNED = "planned"
    REVIEW = "review"
    APPROVED = "approved"
    REWORK = "rework"


class ReviewTaskStatus(StrEnum):
    OPEN = "open"
    APPROVED = "approved"
    REWORK = "rework"
    CANCELLED = "cancelled"


class RenderJobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobAttemptStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class PublishPackageStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    READY = "ready"
    FAILED = "failed"
    CANCELLED = "cancelled"


MUTATION_ROLES = (UserRole.OWNER, UserRole.OPERATOR)
REVIEW_DECISION_ROLES = (UserRole.OWNER, UserRole.REVIEWER)

```

`apps/api/src/content_factory_api/modules/exports.py`:

```py
from typing import Annotated, cast

import boto3
from botocore.client import Config
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from content_factory_api.config import ApiSettings, get_settings
from content_factory_api.database import get_db_session
from content_factory_api.modules.dependencies import get_current_user, require_roles
from content_factory_api.modules.domain import (
    MUTATION_ROLES,
    ContentStatus,
    PublishPackageStatus,
    RenderJobStatus,
)
from content_factory_api.modules.models import ContentItem, PublishPackage, RenderJob, User
from content_factory_api.modules.schemas import (
    DownloadTargetRead,
    PublishPackageCreateRequest,
    PublishPackageDownloadResponse,
    PublishPackageListResponse,
    PublishPackageRead,
)
from content_factory_api.modules.security import expires_in
from content_factory_api.modules.services import (
    commit_or_409,
    get_by_id_or_404,
    write_audit_log,
)

router = APIRouter(prefix="/api/publish-packages", tags=["publish-packages"])

CANCELABLE_PACKAGE_STATUSES = {
    PublishPackageStatus.QUEUED.value,
    PublishPackageStatus.RUNNING.value,
}

RETRYABLE_PACKAGE_STATUSES = {
    PublishPackageStatus.FAILED.value,
    PublishPackageStatus.CANCELLED.value,
}

REQUEUEABLE_PACKAGE_STATUSES = {PublishPackageStatus.QUEUED.value}


@router.post("", response_model=PublishPackageRead, status_code=status.HTTP_201_CREATED)
def create_publish_package(
    request: PublishPackageCreateRequest,
    response: Response,
    current_user: Annotated[User, Depends(require_roles(*MUTATION_ROLES))],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> PublishPackage:
    render_job = get_by_id_or_404(db_session, RenderJob, request.render_job_id, "Render job")
    content_item = get_by_id_or_404(
        db_session,
        ContentItem,
        render_job.content_item_id,
        "Content item",
    )

    _validate_export_inputs(render_job=render_job, content_item=content_item)

    existing_package = db_session.scalar(
        select(PublishPackage).where(PublishPackage.render_job_id == render_job.id)
    )
    if existing_package is not None:
        response.status_code = status.HTTP_200_OK
        return existing_package

    publish_package = PublishPackage(
        render_job_id=render_job.id,
        content_item_id=content_item.id,
        status=PublishPackageStatus.QUEUED.value,
        created_by_user_id=current_user.id,
    )
    db_session.add(publish_package)
    db_session.flush()
    write_audit_log(
        db_session,
        actor_user_id=current_user.id,
        action="publish_package.created",
        entity_type="publish_package",
        entity_id=publish_package.id,
        payload={"render_job_id": render_job.id, "content_item_id": content_item.id},
    )
    commit_or_409(db_session, "Publish package could not be created")

    from content_factory_worker.queue import enqueue_publish_package

    enqueue_publish_package(publish_package.id)
    return publish_package


@router.get("", response_model=PublishPackageListResponse)
def list_publish_packages(
    _current_user: Annotated[User, Depends(get_current_user)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> PublishPackageListResponse:
    packages = list(
        db_session.scalars(select(PublishPackage).order_by(PublishPackage.created_at.desc()))
    )
    return PublishPackageListResponse(
        items=[PublishPackageRead.model_validate(package) for package in packages]
    )


@router.get("/{package_id}", response_model=PublishPackageRead)
def get_publish_package(
    package_id: str,
    _current_user: Annotated[User, Depends(get_current_user)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> PublishPackage:
    return get_by_id_or_404(db_session, PublishPackage, package_id, "Publish package")


@router.post("/{package_id}/cancel", response_model=PublishPackageRead)
def cancel_publish_package(
    package_id: str,
    current_user: Annotated[User, Depends(require_roles(*MUTATION_ROLES))],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> PublishPackage:
    publish_package = get_by_id_or_404(db_session, PublishPackage, package_id, "Publish package")
    if publish_package.status == PublishPackageStatus.CANCELLED.value:
        return publish_package
    if publish_package.status not in CANCELABLE_PACKAGE_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Publish package cannot be cancelled from its current status",
        )

    previous_status = publish_package.status
    publish_package.status = PublishPackageStatus.CANCELLED.value
    publish_package.error_message = publish_package.error_message or "Cancelled by operator"
    write_audit_log(
        db_session,
        actor_user_id=current_user.id,
        action="publish_package.cancelled",
        entity_type="publish_package",
        entity_id=publish_package.id,
        payload={"previous_status": previous_status},
    )
    commit_or_409(db_session, "Publish package could not be cancelled")
    return publish_package


@router.post("/{package_id}/retry", response_model=PublishPackageRead)
def retry_publish_package(
    package_id: str,
    current_user: Annotated[User, Depends(require_roles(*MUTATION_ROLES))],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> PublishPackage:
    publish_package = get_by_id_or_404(db_session, PublishPackage, package_id, "Publish package")
    if publish_package.status not in RETRYABLE_PACKAGE_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Publish package can only be retried after failure or cancellation",
        )

    render_job = get_by_id_or_404(
        db_session,
        RenderJob,
        publish_package.render_job_id,
        "Render job",
    )
    content_item = get_by_id_or_404(
        db_session,
        ContentItem,
        publish_package.content_item_id,
        "Content item",
    )
    _validate_export_inputs(render_job=render_job, content_item=content_item)

    previous_status = publish_package.status
    publish_package.status = PublishPackageStatus.QUEUED.value
    publish_package.package_object_key = None
    publish_package.manifest_payload = {}
    publish_package.byte_size = None
    publish_package.error_message = None
    write_audit_log(
        db_session,
        actor_user_id=current_user.id,
        action="publish_package.retried",
        entity_type="publish_package",
        entity_id=publish_package.id,
        payload={"previous_status": previous_status, "render_job_id": render_job.id},
    )
    commit_or_409(db_session, "Publish package could not be retried")

    from content_factory_worker.queue import enqueue_publish_package

    enqueue_publish_package(publish_package.id)
    return publish_package


@router.post("/{package_id}/requeue", response_model=PublishPackageRead)
def requeue_publish_package(
    package_id: str,
    current_user: Annotated[User, Depends(require_roles(*MUTATION_ROLES))],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> PublishPackage:
    publish_package = get_by_id_or_404(db_session, PublishPackage, package_id, "Publish package")
    if publish_package.status not in REQUEUEABLE_PACKAGE_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Publish package can only be requeued while queued",
        )

    write_audit_log(
        db_session,
        actor_user_id=current_user.id,
        action="publish_package.requeued",
        entity_type="publish_package",
        entity_id=publish_package.id,
        payload={"render_job_id": publish_package.render_job_id},
    )
    commit_or_409(db_session, "Publish package could not be requeued")

    from content_factory_worker.queue import enqueue_publish_package

    enqueue_publish_package(publish_package.id)
    return publish_package


@router.get("/{package_id}/download", response_model=PublishPackageDownloadResponse)
def get_publish_package_download(
    package_id: str,
    _current_user: Annotated[User, Depends(get_current_user)],
    db_session: Annotated[Session, Depends(get_db_session)],
    settings: Annotated[ApiSettings, Depends(get_settings)],
) -> PublishPackageDownloadResponse:
    publish_package = get_by_id_or_404(
        db_session,
        PublishPackage,
        package_id,
        "Publish package",
    )
    if (
        publish_package.status != PublishPackageStatus.READY.value
        or publish_package.package_object_key is None
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Publish package is not ready for download",
        )

    return PublishPackageDownloadResponse(
        package=PublishPackageRead.model_validate(publish_package),
        download=DownloadTargetRead(
            method="GET",
            url=_download_url(settings, publish_package.package_object_key),
            headers={},
            expires_at=expires_in(minutes=settings.upload_url_expiration_minutes),
        ),
    )


def _download_url(settings: ApiSettings, object_key: str) -> str:
    addressing_style = "path" if settings.s3_force_path_style else "virtual"
    s3_client = boto3.client(
        "s3",
        endpoint_url=str(settings.s3_endpoint).rstrip("/"),
        region_name=settings.s3_region,
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
        config=Config(signature_version="s3v4", s3={"addressing_style": addressing_style}),
    )
    url = s3_client.generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.s3_bucket, "Key": object_key},
        ExpiresIn=settings.upload_url_expiration_minutes * 60,
        HttpMethod="GET",
    )
    return cast(str, url)


def _validate_export_inputs(*, render_job: RenderJob, content_item: ContentItem) -> None:
    if render_job.status != RenderJobStatus.SUCCEEDED.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Render job must succeed before package export",
        )

    if content_item.status != ContentStatus.APPROVED.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Content item must be approved before package export",
        )

```

`apps/api/src/content_factory_api/modules/render.py`:

```py
from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from typing import Annotated, cast

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from content_factory_api.database import get_db_session, get_sessionmaker
from content_factory_api.modules.dependencies import get_current_user, require_roles
from content_factory_api.modules.domain import (
    MUTATION_ROLES,
    ContentStatus,
    JobAttemptStatus,
    PackagingProvider,
    RenderJobStatus,
    VoiceProvider,
    WorkflowInputSourceType,
    WorkflowProvider,
)
from content_factory_api.modules.models import (
    Avatar,
    Brand,
    ContentItem,
    IdentityPack,
    JobAttempt,
    RenderJob,
    User,
    WorkflowPreset,
)
from content_factory_api.modules.schemas import (
    JobAttemptRead,
    RenderJobCreateRequest,
    RenderJobListResponse,
    RenderJobRead,
    RenderJobStatusEvent,
    WorkflowInputBinding,
)
from content_factory_api.modules.security import utcnow
from content_factory_api.modules.services import (
    commit_or_409,
    get_by_id_or_404,
    write_audit_log,
)

router = APIRouter(prefix="/api/render-jobs", tags=["render"])

RENDERABLE_CONTENT_STATUSES = {
    ContentStatus.PLANNED.value,
    ContentStatus.REVIEW.value,
    ContentStatus.APPROVED.value,
    ContentStatus.REWORK.value,
}

TERMINAL_RENDER_JOB_STATUSES = {
    RenderJobStatus.SUCCEEDED.value,
    RenderJobStatus.FAILED.value,
    RenderJobStatus.CANCELLED.value,
}

CANCELABLE_RENDER_JOB_STATUSES = {
    RenderJobStatus.QUEUED.value,
    RenderJobStatus.RUNNING.value,
}

RETRYABLE_RENDER_JOB_STATUSES = {
    RenderJobStatus.FAILED.value,
    RenderJobStatus.CANCELLED.value,
}

REQUEUEABLE_RENDER_JOB_STATUSES = {RenderJobStatus.QUEUED.value}

CANCELABLE_ATTEMPT_STATUSES = {
    JobAttemptStatus.QUEUED.value,
    JobAttemptStatus.RUNNING.value,
}


@router.post("", response_model=RenderJobRead, status_code=status.HTTP_201_CREATED)
def create_render_job(
    request: RenderJobCreateRequest,
    current_user: Annotated[User, Depends(require_roles(*MUTATION_ROLES))],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> RenderJobRead:
    content_item = get_by_id_or_404(
        db_session,
        ContentItem,
        request.content_item_id,
        "Content item",
    )
    if content_item.status not in RENDERABLE_CONTENT_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Content item must be planned before render job creation",
        )

    workflow_preset = get_by_id_or_404(
        db_session,
        WorkflowPreset,
        request.workflow_preset_id,
        "Workflow preset",
    )
    brand = get_by_id_or_404(db_session, Brand, content_item.brand_id, "Brand")
    avatar = get_by_id_or_404(db_session, Avatar, content_item.avatar_id, "Avatar")
    identity_pack = _resolve_identity_pack(db_session, request.identity_pack_id, avatar.id)
    input_snapshot = _resolve_input_snapshot(
        workflow_preset=workflow_preset,
        content_item=content_item,
        brand=brand,
        avatar=avatar,
        identity_pack=identity_pack,
    )

    render_job = RenderJob(
        content_item_id=content_item.id,
        workflow_preset_id=workflow_preset.id,
        workflow_preset_key=workflow_preset.key,
        workflow_preset_version=workflow_preset.version,
        workflow_provider=workflow_preset.workflow_provider,
        voice_provider=workflow_preset.voice_provider,
        packaging_provider=workflow_preset.packaging_provider,
        input_snapshot=input_snapshot,
        status=RenderJobStatus.QUEUED.value,
        retry_budget=request.retry_budget,
        created_by_user_id=current_user.id,
    )
    db_session.add(render_job)
    db_session.flush()

    first_attempt = JobAttempt(
        render_job_id=render_job.id,
        attempt_number=1,
        status=JobAttemptStatus.QUEUED.value,
        request_payload={"inputs": input_snapshot},
    )
    db_session.add(first_attempt)
    db_session.flush()
    write_audit_log(
        db_session,
        actor_user_id=current_user.id,
        action="render_job.created",
        entity_type="render_job",
        entity_id=render_job.id,
        payload={
            "workflow_preset_id": workflow_preset.id,
            "workflow_preset_version": workflow_preset.version,
            "attempt_id": first_attempt.id,
        },
    )
    commit_or_409(db_session, "Render job could not be created")
    from content_factory_worker.queue import enqueue_render_job

    enqueue_render_job(render_job.id)
    return _serialize_render_job(db_session, render_job)


@router.get("", response_model=RenderJobListResponse)
def list_render_jobs(
    _current_user: Annotated[User, Depends(get_current_user)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> RenderJobListResponse:
    render_jobs = list(
        db_session.scalars(select(RenderJob).order_by(RenderJob.created_at.desc()))
    )
    return RenderJobListResponse(
        items=[_serialize_render_job(db_session, render_job) for render_job in render_jobs]
    )


@router.get("/{render_job_id}", response_model=RenderJobRead)
def get_render_job(
    render_job_id: str,
    _current_user: Annotated[User, Depends(get_current_user)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> RenderJobRead:
    render_job = get_by_id_or_404(db_session, RenderJob, render_job_id, "Render job")
    return _serialize_render_job(db_session, render_job)


@router.post("/{render_job_id}/cancel", response_model=RenderJobRead)
def cancel_render_job(
    render_job_id: str,
    current_user: Annotated[User, Depends(require_roles(*MUTATION_ROLES))],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> RenderJobRead:
    render_job = get_by_id_or_404(db_session, RenderJob, render_job_id, "Render job")
    if render_job.status == RenderJobStatus.CANCELLED.value:
        return _serialize_render_job(db_session, render_job)
    if render_job.status not in CANCELABLE_RENDER_JOB_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Render job cannot be cancelled from its current status",
        )

    previous_status = render_job.status
    cancelled_attempt_ids = _cancel_active_attempts(db_session, render_job.id)
    render_job.status = RenderJobStatus.CANCELLED.value
    write_audit_log(
        db_session,
        actor_user_id=current_user.id,
        action="render_job.cancelled",
        entity_type="render_job",
        entity_id=render_job.id,
        payload={
            "previous_status": previous_status,
            "cancelled_attempt_ids": cancelled_attempt_ids,
        },
    )
    commit_or_409(db_session, "Render job could not be cancelled")
    return _serialize_render_job(db_session, render_job)


@router.post("/{render_job_id}/retry", response_model=RenderJobRead)
def retry_render_job(
    render_job_id: str,
    current_user: Annotated[User, Depends(require_roles(*MUTATION_ROLES))],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> RenderJobRead:
    render_job = get_by_id_or_404(db_session, RenderJob, render_job_id, "Render job")
    if render_job.status not in RETRYABLE_RENDER_JOB_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Render job can only be retried after failure or cancellation",
        )

    previous_status = render_job.status
    retry_attempt = _append_queued_attempt(db_session, render_job)
    render_job.status = RenderJobStatus.QUEUED.value
    write_audit_log(
        db_session,
        actor_user_id=current_user.id,
        action="render_job.retried",
        entity_type="render_job",
        entity_id=render_job.id,
        payload={
            "previous_status": previous_status,
            "attempt_id": retry_attempt.id,
            "attempt_number": retry_attempt.attempt_number,
        },
    )
    commit_or_409(db_session, "Render job could not be retried")

    from content_factory_worker.queue import enqueue_render_job

    enqueue_render_job(render_job.id)
    return _serialize_render_job(db_session, render_job)


@router.post("/{render_job_id}/requeue", response_model=RenderJobRead)
def requeue_render_job(
    render_job_id: str,
    current_user: Annotated[User, Depends(require_roles(*MUTATION_ROLES))],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> RenderJobRead:
    render_job = get_by_id_or_404(db_session, RenderJob, render_job_id, "Render job")
    if render_job.status not in REQUEUEABLE_RENDER_JOB_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Render job can only be requeued while queued",
        )

    queued_attempt = _next_queued_attempt(db_session, render_job.id)
    created_attempt = False
    if queued_attempt is None:
        queued_attempt = _append_queued_attempt(db_session, render_job)
        created_attempt = True

    write_audit_log(
        db_session,
        actor_user_id=current_user.id,
        action="render_job.requeued",
        entity_type="render_job",
        entity_id=render_job.id,
        payload={
            "attempt_id": queued_attempt.id,
            "attempt_number": queued_attempt.attempt_number,
            "created_attempt": created_attempt,
        },
    )
    commit_or_409(db_session, "Render job could not be requeued")

    from content_factory_worker.queue import enqueue_render_job

    enqueue_render_job(render_job.id)
    return _serialize_render_job(db_session, render_job)


@router.get(
    "/{render_job_id}/events",
    response_class=StreamingResponse,
    responses={
        status.HTTP_200_OK: {
            "content": {"text/event-stream": {"schema": {"type": "string"}}},
            "description": "Server-sent render job status snapshots.",
        }
    },
)
async def stream_render_job_events(
    render_job_id: str,
    request: Request,
    _current_user: Annotated[User, Depends(get_current_user)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> StreamingResponse:
    get_by_id_or_404(db_session, RenderJob, render_job_id, "Render job")
    return StreamingResponse(
        _render_job_event_stream(render_job_id, request),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache"},
    )


def _resolve_identity_pack(
    db_session: Session,
    identity_pack_id: str | None,
    avatar_id: str,
) -> IdentityPack | None:
    if identity_pack_id is None:
        return None

    identity_pack = get_by_id_or_404(db_session, IdentityPack, identity_pack_id, "Identity pack")
    if identity_pack.avatar_id != avatar_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Identity pack does not belong to the content avatar",
        )
    return identity_pack


def _resolve_input_snapshot(
    *,
    workflow_preset: WorkflowPreset,
    content_item: ContentItem,
    brand: Brand,
    avatar: Avatar,
    identity_pack: IdentityPack | None,
) -> dict[str, object]:
    resolved: dict[str, object] = {}
    raw_input_mapping = workflow_preset.input_mapping
    for input_name, binding_payload in raw_input_mapping.items():
        if not isinstance(binding_payload, dict):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"Workflow input mapping for '{input_name}' is invalid",
            )
        binding = WorkflowInputBinding.model_validate(binding_payload)
        resolved[input_name] = _resolve_binding_value(
            input_name=input_name,
            binding=binding,
            content_item=content_item,
            brand=brand,
            avatar=avatar,
            identity_pack=identity_pack,
        )
    return resolved


def _resolve_binding_value(
    *,
    input_name: str,
    binding: WorkflowInputBinding,
    content_item: ContentItem,
    brand: Brand,
    avatar: Avatar,
    identity_pack: IdentityPack | None,
) -> object:
    if binding.source_type == WorkflowInputSourceType.LITERAL:
        return binding.value

    source_field = binding.source_field
    if source_field is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Workflow input mapping for '{input_name}' is missing source_field",
        )

    source_entity: object
    if binding.source_type == WorkflowInputSourceType.CONTENT_ITEM:
        source_entity = content_item
    elif binding.source_type == WorkflowInputSourceType.BRAND:
        source_entity = brand
    elif binding.source_type == WorkflowInputSourceType.AVATAR:
        source_entity = avatar
    else:
        if identity_pack is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Workflow preset requires identity_pack_id for render job creation",
            )
        source_entity = identity_pack

    if not hasattr(source_entity, source_field):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=(
                f"Workflow input mapping for '{input_name}' references unknown field "
                f"'{source_field}'"
            ),
        )

    return cast(object, getattr(source_entity, source_field))


def _serialize_render_job(db_session: Session, render_job: RenderJob) -> RenderJobRead:
    attempts = _attempts_for_render_job(db_session, render_job.id)
    return RenderJobRead(
        id=render_job.id,
        content_item_id=render_job.content_item_id,
        workflow_preset_id=render_job.workflow_preset_id,
        workflow_preset_key=render_job.workflow_preset_key,
        workflow_preset_version=render_job.workflow_preset_version,
        workflow_provider=WorkflowProvider(render_job.workflow_provider),
        voice_provider=VoiceProvider(render_job.voice_provider),
        packaging_provider=PackagingProvider(render_job.packaging_provider),
        input_snapshot=render_job.input_snapshot,
        status=RenderJobStatus(render_job.status),
        retry_budget=render_job.retry_budget,
        created_by_user_id=render_job.created_by_user_id,
        created_at=render_job.created_at,
        updated_at=render_job.updated_at,
        attempts=[JobAttemptRead.model_validate(attempt) for attempt in attempts],
    )


def _attempts_for_render_job(db_session: Session, render_job_id: str) -> list[JobAttempt]:
    return list(
        db_session.scalars(
            select(JobAttempt)
            .where(JobAttempt.render_job_id == render_job_id)
            .order_by(JobAttempt.attempt_number.asc())
        )
    )


def _next_queued_attempt(db_session: Session, render_job_id: str) -> JobAttempt | None:
    return db_session.scalar(
        select(JobAttempt)
        .where(
            JobAttempt.render_job_id == render_job_id,
            JobAttempt.status == JobAttemptStatus.QUEUED.value,
        )
        .order_by(JobAttempt.attempt_number.asc())
    )


def _cancel_active_attempts(db_session: Session, render_job_id: str) -> list[str]:
    now = utcnow()
    cancelled_attempt_ids: list[str] = []
    for attempt in _attempts_for_render_job(db_session, render_job_id):
        if attempt.status not in CANCELABLE_ATTEMPT_STATUSES:
            continue
        attempt.status = JobAttemptStatus.CANCELLED.value
        attempt.error_message = attempt.error_message or "Cancelled by operator"
        attempt.finished_at = attempt.finished_at or now
        cancelled_attempt_ids.append(attempt.id)
    return cancelled_attempt_ids


def _append_queued_attempt(db_session: Session, render_job: RenderJob) -> JobAttempt:
    attempts = _attempts_for_render_job(db_session, render_job.id)
    latest_attempt = attempts[-1] if attempts else None
    next_attempt_number = (latest_attempt.attempt_number + 1) if latest_attempt else 1
    request_payload = (
        latest_attempt.request_payload
        if latest_attempt is not None
        else {"inputs": render_job.input_snapshot}
    )
    attempt = JobAttempt(
        render_job_id=render_job.id,
        attempt_number=next_attempt_number,
        status=JobAttemptStatus.QUEUED.value,
        request_payload=request_payload,
    )
    db_session.add(attempt)
    db_session.flush()
    return attempt


async def _render_job_event_stream(
    render_job_id: str,
    request: Request,
    *,
    poll_interval_seconds: float = 1.0,
) -> AsyncIterator[str]:
    previous_payload: str | None = None

    while True:
        db_session = get_sessionmaker()()
        try:
            render_job = db_session.get(RenderJob, render_job_id)
            if render_job is None:
                return
            event = RenderJobStatusEvent(render_job=_serialize_render_job(db_session, render_job))
            payload = event.model_dump_json()
            terminal = render_job.status in TERMINAL_RENDER_JOB_STATUSES
        finally:
            db_session.close()

        if payload != previous_payload:
            yield f"event: render_job.snapshot\ndata: {payload}\n\n"
            previous_payload = payload

        if terminal or await request.is_disconnected():
            return

        await asyncio.sleep(poll_interval_seconds)

```

`apps/api/tests/test_publish_packages.py`:

```py
from fastapi import FastAPI
from fastapi.testclient import TestClient

from content_factory_api.database import get_sessionmaker
from content_factory_api.modules.domain import (
    ContentStatus,
    JobAttemptStatus,
    PublishPackageStatus,
    RenderJobStatus,
)
from content_factory_api.modules.models import ContentItem, JobAttempt, PublishPackage, RenderJob


def _bootstrap_owner(client: TestClient) -> None:
    response = client.post(
        "/api/auth/bootstrap-owner",
        json={
            "email": "owner@inflave.test",
            "display_name": "Owner",
            "password": "very-secure-password",
        },
    )
    assert response.status_code == 201


def _workflow_preset_payload() -> dict[str, object]:
    return {
        "key": "pilot-reels",
        "name": "Pilot Reels",
        "description": "Primary short-form render preset.",
        "workflow_provider": "comfyui",
        "voice_provider": "none",
        "packaging_provider": "ffmpeg",
        "workflow_definition": {
            "nodes": {
                "script_prompt": {
                    "class_type": "CLIPTextEncode",
                    "inputs": {"text": "render a compliant host short"},
                }
            }
        },
        "input_mapping": {
            "script_text": {"source_type": "content_item", "source_field": "script"},
        },
        "output_mapping": {
            "video_file": {"artifact_type": "video", "output_path": "outputs.video_file"},
            "cover_file": {"artifact_type": "cover_image", "output_path": "outputs.cover_file"},
        },
    }


def _seed_approved_render_job(client: TestClient) -> str:
    brand_response = client.post(
        "/api/brands",
        json={"name": "Inflave", "voice_notes": "Confident, compliant, concise."},
    )
    assert brand_response.status_code == 201
    brand_id = str(brand_response.json()["id"])

    avatar_response = client.post(
        "/api/avatars",
        json={
            "brand_id": brand_id,
            "name": "Primary Host",
            "persona_notes": "Human-like pilot avatar.",
        },
    )
    assert avatar_response.status_code == 201
    avatar_id = str(avatar_response.json()["id"])

    content_response = client.post(
        "/api/content-items",
        json={
            "brand_id": brand_id,
            "avatar_id": avatar_id,
            "title": "Pilot short",
            "script": "A careful, platform-safe short script.",
            "channel": "youtube_shorts",
        },
    )
    assert content_response.status_code == 201
    content_item_id = str(content_response.json()["id"])

    plan_response = client.post(f"/api/content-items/{content_item_id}/plan", json={})
    assert plan_response.status_code == 200
    review_response = client.post(f"/api/content-items/{content_item_id}/submit-review")
    assert review_response.status_code == 201
    approve_response = client.post(
        f"/api/review/tasks/{review_response.json()['id']}/approve",
        json={"decision_notes": "Approved for manual publishing."},
    )
    assert approve_response.status_code == 200

    preset_response = client.post("/api/workflow-presets", json=_workflow_preset_payload())
    assert preset_response.status_code == 201

    render_response = client.post(
        "/api/render-jobs",
        json={
            "content_item_id": content_item_id,
            "workflow_preset_id": str(preset_response.json()["id"]),
        },
    )
    assert render_response.status_code == 201
    render_job_id = str(render_response.json()["id"])

    db_session = get_sessionmaker()()
    try:
        render_job = db_session.get(RenderJob, render_job_id)
        assert render_job is not None
        render_job.status = RenderJobStatus.SUCCEEDED.value
        attempt = (
            db_session.query(JobAttempt)
            .filter(JobAttempt.render_job_id == render_job_id)
            .one()
        )
        attempt.status = JobAttemptStatus.SUCCEEDED.value
        attempt.response_payload = {
            "outputs": {
                "video_file": "s3://content-factory-assets/renders/video.mp4",
                "cover_file": "s3://content-factory-assets/renders/cover.jpg",
            }
        }
        db_session.commit()
    finally:
        db_session.close()

    return render_job_id


def test_create_publish_package_is_gated_and_idempotent(api_client: TestClient) -> None:
    _bootstrap_owner(api_client)
    render_job_id = _seed_approved_render_job(api_client)

    response = api_client.post("/api/publish-packages", json={"render_job_id": render_job_id})

    assert response.status_code == 201
    payload = response.json()
    assert payload["render_job_id"] == render_job_id
    assert payload["status"] == "queued"
    assert payload["package_object_key"] is None

    second_response = api_client.post(
        "/api/publish-packages",
        json={"render_job_id": render_job_id},
    )
    assert second_response.status_code == 200
    assert second_response.json()["id"] == payload["id"]

    list_response = api_client.get("/api/publish-packages")
    assert list_response.status_code == 200
    assert [item["id"] for item in list_response.json()["items"]] == [payload["id"]]


def test_publish_package_requires_approved_content_and_succeeded_render(
    api_client: TestClient,
) -> None:
    _bootstrap_owner(api_client)
    render_job_id = _seed_approved_render_job(api_client)

    db_session = get_sessionmaker()()
    try:
        render_job = db_session.get(RenderJob, render_job_id)
        assert render_job is not None
        render_job.status = RenderJobStatus.RUNNING.value
        db_session.commit()
    finally:
        db_session.close()

    running_response = api_client.post(
        "/api/publish-packages",
        json={"render_job_id": render_job_id},
    )
    assert running_response.status_code == 409
    assert "succeed" in running_response.json()["detail"]

    db_session = get_sessionmaker()()
    try:
        render_job = db_session.get(RenderJob, render_job_id)
        assert render_job is not None
        render_job.status = RenderJobStatus.SUCCEEDED.value
        content_item = db_session.get(ContentItem, render_job.content_item_id)
        assert content_item is not None
        content_item.status = ContentStatus.REWORK.value
        db_session.commit()
    finally:
        db_session.close()

    review_response = api_client.post(
        "/api/publish-packages",
        json={"render_job_id": render_job_id},
    )
    assert review_response.status_code == 409
    assert "approved" in review_response.json()["detail"]


def test_publish_package_download_requires_ready_package(api_client: TestClient) -> None:
    _bootstrap_owner(api_client)
    render_job_id = _seed_approved_render_job(api_client)
    create_response = api_client.post(
        "/api/publish-packages",
        json={"render_job_id": render_job_id},
    )
    assert create_response.status_code == 201
    package_id = str(create_response.json()["id"])

    queued_download = api_client.get(f"/api/publish-packages/{package_id}/download")
    assert queued_download.status_code == 409

    db_session = get_sessionmaker()()
    try:
        package = db_session.get(PublishPackage, package_id)
        assert package is not None
        package.status = PublishPackageStatus.READY.value
        package.package_object_key = "publish-packages/content/package.zip"
        package.byte_size = 123
        db_session.commit()
    finally:
        db_session.close()

    ready_download = api_client.get(f"/api/publish-packages/{package_id}/download")
    assert ready_download.status_code == 200
    payload = ready_download.json()
    assert payload["package"]["id"] == package_id
    assert payload["download"]["method"] == "GET"
    assert "publish-packages/content/package.zip" in payload["download"]["url"]


def test_publish_package_operator_actions_cancel_retry_and_requeue(
    api_client: TestClient,
) -> None:
    _bootstrap_owner(api_client)
    render_job_id = _seed_approved_render_job(api_client)
    create_response = api_client.post(
        "/api/publish-packages",
        json={"render_job_id": render_job_id},
    )
    assert create_response.status_code == 201
    package_id = str(create_response.json()["id"])

    requeue_response = api_client.post(f"/api/publish-packages/{package_id}/requeue")
    assert requeue_response.status_code == 200
    assert requeue_response.json()["status"] == "queued"

    cancel_response = api_client.post(f"/api/publish-packages/{package_id}/cancel")
    assert cancel_response.status_code == 200
    assert cancel_response.json()["status"] == "cancelled"

    db_session = get_sessionmaker()()
    try:
        publish_package = db_session.get(PublishPackage, package_id)
        assert publish_package is not None
        publish_package.status = PublishPackageStatus.FAILED.value
        publish_package.package_object_key = "publish-packages/stale.zip"
        publish_package.manifest_payload = {"stale": True}
        publish_package.byte_size = 10
        publish_package.error_message = "Missing output"
        db_session.commit()
    finally:
        db_session.close()

    retry_response = api_client.post(f"/api/publish-packages/{package_id}/retry")
    assert retry_response.status_code == 200
    retry_payload = retry_response.json()
    assert retry_payload["status"] == "queued"
    assert retry_payload["package_object_key"] is None
    assert retry_payload["manifest_payload"] == {}
    assert retry_payload["byte_size"] is None
    assert retry_payload["error_message"] is None

    audit_response = api_client.get("/api/audit/logs")
    actions = [entry["action"] for entry in audit_response.json()["items"]]
    assert "publish_package.requeued" in actions
    assert "publish_package.cancelled" in actions
    assert "publish_package.retried" in actions


def test_publish_package_actions_are_role_gated(
    api_app: FastAPI,
    api_client: TestClient,
) -> None:
    _bootstrap_owner(api_client)
    render_job_id = _seed_approved_render_job(api_client)
    create_response = api_client.post(
        "/api/publish-packages",
        json={"render_job_id": render_job_id},
    )
    assert create_response.status_code == 201

    invite_response = api_client.post(
        "/api/auth/invites",
        json={"email": "viewer@inflave.test", "role": "viewer"},
    )
    viewer_client = TestClient(api_app)
    accept_response = viewer_client.post(
        "/api/auth/invites/accept",
        json={
            "token": invite_response.json()["token"],
            "email": "viewer@inflave.test",
            "display_name": "Viewer",
            "password": "viewer-password",
        },
    )
    assert accept_response.status_code == 201

    response = viewer_client.post(
        f"/api/publish-packages/{create_response.json()['id']}/cancel",
    )

    assert response.status_code == 403

```

`apps/api/tests/test_render_contracts.py`:

```py
import json

from fastapi import FastAPI
from fastapi.testclient import TestClient

from content_factory_api.database import get_sessionmaker
from content_factory_api.modules.domain import JobAttemptStatus, RenderJobStatus
from content_factory_api.modules.models import JobAttempt, RenderJob


def _bootstrap_owner(client: TestClient) -> None:
    response = client.post(
        "/api/auth/bootstrap-owner",
        json={
            "email": "owner@inflave.test",
            "display_name": "Owner",
            "password": "very-secure-password",
        },
    )
    assert response.status_code == 201


def _create_brand(client: TestClient) -> str:
    response = client.post(
        "/api/brands",
        json={"name": "Inflave", "voice_notes": "Confident, compliant, concise."},
    )
    assert response.status_code == 201
    return str(response.json()["id"])


def _create_avatar(client: TestClient, brand_id: str) -> str:
    response = client.post(
        "/api/avatars",
        json={
            "brand_id": brand_id,
            "name": "Primary Host",
            "persona_notes": "Human-like pilot avatar.",
        },
    )
    assert response.status_code == 201
    return str(response.json()["id"])


def _create_identity_pack(client: TestClient, avatar_id: str) -> str:
    response = client.post(
        f"/api/avatars/{avatar_id}/identity-packs",
        json={
            "name": "Core identity",
            "description": "Pilot voice and look references.",
            "storage_prefix": "identity/core",
        },
    )
    assert response.status_code == 201
    return str(response.json()["id"])


def _create_content_item(client: TestClient, brand_id: str, avatar_id: str) -> str:
    response = client.post(
        "/api/content-items",
        json={
            "brand_id": brand_id,
            "avatar_id": avatar_id,
            "title": "Pilot short",
            "script": "A careful, platform-safe short script.",
            "channel": "youtube_shorts",
        },
    )
    assert response.status_code == 201
    return str(response.json()["id"])


def _plan_content_item(client: TestClient, content_item_id: str) -> None:
    response = client.post(f"/api/content-items/{content_item_id}/plan", json={})
    assert response.status_code == 200


def _workflow_preset_payload() -> dict[str, object]:
    return {
        "key": "pilot-reels",
        "name": "Pilot Reels",
        "description": "Primary short-form render preset.",
        "workflow_provider": "comfyui",
        "voice_provider": "none",
        "packaging_provider": "ffmpeg",
        "workflow_definition": {
            "nodes": {
                "script_prompt": {
                    "class_type": "CLIPTextEncode",
                    "inputs": {"text": "render a compliant host short"},
                }
            }
        },
        "input_mapping": {
            "script_text": {"source_type": "content_item", "source_field": "script"},
            "brand_voice_notes": {"source_type": "brand", "source_field": "voice_notes"},
            "host_name": {"source_type": "avatar", "source_field": "name"},
            "identity_pack_prefix": {
                "source_type": "identity_pack",
                "source_field": "storage_prefix",
            },
        },
        "output_mapping": {
            "video_file": {"artifact_type": "video", "output_path": "outputs.primary.video"},
            "cover_file": {"artifact_type": "cover_image", "output_path": "outputs.primary.cover"},
        },
    }


def test_workflow_preset_versions_are_incremented_and_immutable(api_client: TestClient) -> None:
    _bootstrap_owner(api_client)

    first_response = api_client.post("/api/workflow-presets", json=_workflow_preset_payload())
    assert first_response.status_code == 201
    first_payload = first_response.json()
    assert first_payload["version"] == 1

    second_payload = _workflow_preset_payload()
    second_payload["description"] = "Updated preset with a refined prompt."
    second_payload["workflow_definition"] = {
        "nodes": {
            "script_prompt": {
                "class_type": "CLIPTextEncode",
                "inputs": {"text": "render an approved and on-brand short"},
            }
        }
    }
    second_response = api_client.post("/api/workflow-presets", json=second_payload)

    assert second_response.status_code == 201
    assert second_response.json()["version"] == 2

    first_detail = api_client.get(f"/api/workflow-presets/{first_payload['id']}")
    assert first_detail.status_code == 200
    assert first_detail.json()["version"] == 1
    assert first_detail.json()["description"] == "Primary short-form render preset."
    assert (
        first_detail.json()["workflow_definition"]["nodes"]["script_prompt"]["inputs"]["text"]
        == "render a compliant host short"
    )

    list_response = api_client.get("/api/workflow-presets")
    assert list_response.status_code == 200
    versions = [
        item["version"]
        for item in list_response.json()["items"]
        if item["key"] == "pilot-reels"
    ]
    assert versions == [2, 1]


def test_workflow_preset_rejects_invalid_provider_contract(api_client: TestClient) -> None:
    _bootstrap_owner(api_client)
    invalid_payload = _workflow_preset_payload()
    invalid_payload["workflow_definition"] = {"graph": []}

    response = api_client.post("/api/workflow-presets", json=invalid_payload)

    assert response.status_code == 422
    assert "nodes" in response.json()["detail"]


def test_render_job_creation_snapshots_preset_and_seeds_first_attempt(
    api_client: TestClient,
) -> None:
    _bootstrap_owner(api_client)
    brand_id = _create_brand(api_client)
    avatar_id = _create_avatar(api_client, brand_id)
    identity_pack_id = _create_identity_pack(api_client, avatar_id)
    content_item_id = _create_content_item(api_client, brand_id, avatar_id)
    _plan_content_item(api_client, content_item_id)

    preset_response = api_client.post("/api/workflow-presets", json=_workflow_preset_payload())
    assert preset_response.status_code == 201
    preset_id = str(preset_response.json()["id"])

    render_job_response = api_client.post(
        "/api/render-jobs",
        json={
            "content_item_id": content_item_id,
            "workflow_preset_id": preset_id,
            "identity_pack_id": identity_pack_id,
            "retry_budget": 3,
        },
    )

    assert render_job_response.status_code == 201
    render_job_payload = render_job_response.json()
    assert render_job_payload["status"] == "queued"
    assert render_job_payload["workflow_preset_key"] == "pilot-reels"
    assert render_job_payload["workflow_preset_version"] == 1
    assert render_job_payload["input_snapshot"] == {
        "brand_voice_notes": "Confident, compliant, concise.",
        "host_name": "Primary Host",
        "identity_pack_prefix": "identity/core",
        "script_text": "A careful, platform-safe short script.",
    }
    assert render_job_payload["attempts"][0]["attempt_number"] == 1
    assert render_job_payload["attempts"][0]["status"] == "queued"
    assert render_job_payload["attempts"][0]["response_payload"] == {}
    assert render_job_payload["attempts"][0]["request_payload"]["inputs"] == {
        "brand_voice_notes": "Confident, compliant, concise.",
        "host_name": "Primary Host",
        "identity_pack_prefix": "identity/core",
        "script_text": "A careful, platform-safe short script.",
    }

    second_preset_payload = _workflow_preset_payload()
    second_preset_payload["description"] = "Version two."
    second_preset_response = api_client.post("/api/workflow-presets", json=second_preset_payload)
    assert second_preset_response.status_code == 201
    assert second_preset_response.json()["version"] == 2

    render_job_detail = api_client.get(f"/api/render-jobs/{render_job_payload['id']}")
    assert render_job_detail.status_code == 200
    assert render_job_detail.json()["workflow_preset_version"] == 1


def test_render_job_events_stream_terminal_snapshot(api_client: TestClient) -> None:
    _bootstrap_owner(api_client)
    brand_id = _create_brand(api_client)
    avatar_id = _create_avatar(api_client, brand_id)
    identity_pack_id = _create_identity_pack(api_client, avatar_id)
    content_item_id = _create_content_item(api_client, brand_id, avatar_id)
    _plan_content_item(api_client, content_item_id)
    preset_response = api_client.post("/api/workflow-presets", json=_workflow_preset_payload())
    assert preset_response.status_code == 201

    render_job_response = api_client.post(
        "/api/render-jobs",
        json={
            "content_item_id": content_item_id,
            "workflow_preset_id": str(preset_response.json()["id"]),
            "identity_pack_id": identity_pack_id,
        },
    )
    assert render_job_response.status_code == 201
    render_job_id = str(render_job_response.json()["id"])

    db_session = get_sessionmaker()()
    try:
        render_job = db_session.get(RenderJob, render_job_id)
        assert render_job is not None
        render_job.status = RenderJobStatus.SUCCEEDED.value
        db_session.commit()
    finally:
        db_session.close()

    with api_client.stream("GET", f"/api/render-jobs/{render_job_id}/events") as response:
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")
        stream_body = response.read().decode()

    assert "event: render_job.snapshot" in stream_body
    raw_payload = stream_body.split("data: ", 1)[1].split("\n\n", 1)[0]
    payload = json.loads(raw_payload)
    assert payload["render_job"]["id"] == render_job_id
    assert payload["render_job"]["status"] == "succeeded"


def test_render_job_operator_actions_cancel_retry_and_requeue(
    api_client: TestClient,
) -> None:
    _bootstrap_owner(api_client)
    brand_id = _create_brand(api_client)
    avatar_id = _create_avatar(api_client, brand_id)
    identity_pack_id = _create_identity_pack(api_client, avatar_id)
    content_item_id = _create_content_item(api_client, brand_id, avatar_id)
    _plan_content_item(api_client, content_item_id)
    preset_response = api_client.post("/api/workflow-presets", json=_workflow_preset_payload())
    assert preset_response.status_code == 201

    render_job_response = api_client.post(
        "/api/render-jobs",
        json={
            "content_item_id": content_item_id,
            "workflow_preset_id": str(preset_response.json()["id"]),
            "identity_pack_id": identity_pack_id,
            "retry_budget": 1,
        },
    )
    assert render_job_response.status_code == 201
    render_job_id = str(render_job_response.json()["id"])

    requeue_response = api_client.post(f"/api/render-jobs/{render_job_id}/requeue")
    assert requeue_response.status_code == 200
    assert requeue_response.json()["status"] == "queued"
    assert len(requeue_response.json()["attempts"]) == 1

    cancel_response = api_client.post(f"/api/render-jobs/{render_job_id}/cancel")
    assert cancel_response.status_code == 200
    cancel_payload = cancel_response.json()
    assert cancel_payload["status"] == "cancelled"
    assert cancel_payload["attempts"][0]["status"] == "cancelled"

    retry_response = api_client.post(f"/api/render-jobs/{render_job_id}/retry")
    assert retry_response.status_code == 200
    retry_payload = retry_response.json()
    assert retry_payload["status"] == "queued"
    assert [attempt["attempt_number"] for attempt in retry_payload["attempts"]] == [1, 2]
    assert retry_payload["attempts"][1]["status"] == "queued"

    audit_response = api_client.get("/api/audit/logs")
    actions = [entry["action"] for entry in audit_response.json()["items"]]
    assert "render_job.requeued" in actions
    assert "render_job.cancelled" in actions
    assert "render_job.retried" in actions


def test_render_job_operator_actions_are_role_gated(
    api_app: FastAPI,
    api_client: TestClient,
) -> None:
    _bootstrap_owner(api_client)
    brand_id = _create_brand(api_client)
    avatar_id = _create_avatar(api_client, brand_id)
    identity_pack_id = _create_identity_pack(api_client, avatar_id)
    content_item_id = _create_content_item(api_client, brand_id, avatar_id)
    _plan_content_item(api_client, content_item_id)
    preset_response = api_client.post("/api/workflow-presets", json=_workflow_preset_payload())
    assert preset_response.status_code == 201
    render_job_response = api_client.post(
        "/api/render-jobs",
        json={
            "content_item_id": content_item_id,
            "workflow_preset_id": str(preset_response.json()["id"]),
            "identity_pack_id": identity_pack_id,
        },
    )
    assert render_job_response.status_code == 201

    invite_response = api_client.post(
        "/api/auth/invites",
        json={"email": "reviewer@inflave.test", "role": "reviewer"},
    )
    reviewer_client = TestClient(api_app)
    accept_response = reviewer_client.post(
        "/api/auth/invites/accept",
        json={
            "token": invite_response.json()["token"],
            "email": "reviewer@inflave.test",
            "display_name": "Reviewer",
            "password": "reviewer-password",
        },
    )
    assert accept_response.status_code == 201

    response = reviewer_client.post(
        f"/api/render-jobs/{render_job_response.json()['id']}/cancel",
    )

    assert response.status_code == 403


def test_render_job_retry_rejects_succeeded_jobs(api_client: TestClient) -> None:
    _bootstrap_owner(api_client)
    brand_id = _create_brand(api_client)
    avatar_id = _create_avatar(api_client, brand_id)
    identity_pack_id = _create_identity_pack(api_client, avatar_id)
    content_item_id = _create_content_item(api_client, brand_id, avatar_id)
    _plan_content_item(api_client, content_item_id)
    preset_response = api_client.post("/api/workflow-presets", json=_workflow_preset_payload())
    assert preset_response.status_code == 201
    render_job_response = api_client.post(
        "/api/render-jobs",
        json={
            "content_item_id": content_item_id,
            "workflow_preset_id": str(preset_response.json()["id"]),
            "identity_pack_id": identity_pack_id,
        },
    )
    assert render_job_response.status_code == 201
    render_job_id = str(render_job_response.json()["id"])

    db_session = get_sessionmaker()()
    try:
        render_job = db_session.get(RenderJob, render_job_id)
        assert render_job is not None
        render_job.status = RenderJobStatus.SUCCEEDED.value
        attempt = (
            db_session.query(JobAttempt)
            .filter(JobAttempt.render_job_id == render_job_id)
            .one()
        )
        attempt.status = JobAttemptStatus.SUCCEEDED.value
        db_session.commit()
    finally:
        db_session.close()

    response = api_client.post(f"/api/render-jobs/{render_job_id}/retry")

    assert response.status_code == 409

```

`apps/web/src/app/App.test.tsx`:

```tsx
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import { App } from "./App";

interface MockUser {
  id: string;
  email: string;
  display_name: string;
  role: "owner" | "operator" | "reviewer" | "viewer";
  status: "active";
  created_at: string;
}

interface MockSession {
  user: MockUser;
  expires_at: string;
}

interface MockBrand {
  id: string;
  name: string;
  voice_notes: string | null;
  created_by_user_id: string;
  created_at: string;
  updated_at: string;
}

interface MockAvatar {
  id: string;
  brand_id: string;
  name: string;
  persona_notes: string | null;
  status: "draft" | "active";
  created_by_user_id: string;
  created_at: string;
  updated_at: string;
}

interface MockIdentityPack {
  id: string;
  avatar_id: string;
  name: string;
  description: string | null;
  storage_prefix: string;
  status: "draft" | "ready";
  created_at: string;
  updated_at: string;
}

interface MockAsset {
  id: string;
  brand_id: string;
  object_key: string;
  filename: string;
  content_type: string;
  byte_size: number | null;
  checksum_sha256: string | null;
  status: "pending_upload" | "ready" | "failed";
  upload_expires_at: string;
  created_at: string;
  updated_at: string;
}

interface MockContentItem {
  id: string;
  brand_id: string;
  avatar_id: string;
  title: string;
  script: string;
  channel: "instagram_reels" | "youtube_shorts";
  status: "draft" | "planned" | "review" | "approved" | "rework";
  planned_publish_at: string | null;
  created_by_user_id: string;
  created_at: string;
  updated_at: string;
}

interface MockReviewTask {
  id: string;
  content_item_id: string;
  assigned_to_user_id: string | null;
  status: "open" | "approved" | "rework" | "cancelled";
  decision_notes: string | null;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
}

interface MockAuditLog {
  id: string;
  actor_user_id: string | null;
  action: string;
  entity_type: string;
  entity_id: string;
  payload: Record<string, unknown>;
  created_at: string;
}

interface MockWorkflowPreset {
  id: string;
  key: string;
  version: number;
  name: string;
  description: string | null;
  workflow_provider: "comfyui";
  voice_provider: "none";
  packaging_provider: "ffmpeg";
  workflow_definition: Record<string, unknown>;
  input_mapping: Record<string, unknown>;
  output_mapping: Record<string, unknown>;
  created_by_user_id: string;
  created_at: string;
  updated_at: string;
}

interface MockJobAttempt {
  id: string;
  render_job_id: string;
  attempt_number: number;
  status: "queued" | "running" | "succeeded" | "failed" | "cancelled";
  provider_job_id: string | null;
  request_payload: Record<string, unknown>;
  response_payload: Record<string, unknown>;
  error_message: string | null;
  started_at: string | null;
  finished_at: string | null;
  created_at: string;
  updated_at: string;
}

interface MockRenderJob {
  id: string;
  content_item_id: string;
  workflow_preset_id: string;
  workflow_preset_key: string;
  workflow_preset_version: number;
  workflow_provider: "comfyui";
  voice_provider: "none";
  packaging_provider: "ffmpeg";
  input_snapshot: Record<string, unknown>;
  status: "queued" | "running" | "succeeded" | "failed" | "cancelled";
  retry_budget: number;
  created_by_user_id: string;
  created_at: string;
  updated_at: string;
  attempts: MockJobAttempt[];
}

interface MockPublishPackage {
  id: string;
  render_job_id: string;
  content_item_id: string;
  status: "queued" | "running" | "ready" | "failed" | "cancelled";
  package_object_key: string | null;
  manifest_payload: Record<string, unknown>;
  byte_size: number | null;
  error_message: string | null;
  created_by_user_id: string;
  created_at: string;
  updated_at: string;
}

interface MockApiState {
  session: MockSession | null;
  brands: MockBrand[];
  avatars: MockAvatar[];
  identityPacks: MockIdentityPack[];
  assets: MockAsset[];
  contentItems: MockContentItem[];
  reviewTasks: MockReviewTask[];
  auditLogs: MockAuditLog[];
  workflowPresets: MockWorkflowPreset[];
  renderJobs: MockRenderJob[];
  publishPackages: MockPublishPackage[];
}

type RouteHandler = (
  path: string,
  options: RequestInit | undefined,
  state: MockApiState,
) => Promise<Response> | Response;

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function noContentResponse(status = 200): Response {
  return new Response(null, { status });
}

function nowIso(minuteOffset = 0): string {
  return new Date(Date.UTC(2026, 4, 6, 12, minuteOffset)).toISOString();
}

function createOwnerSession(): MockSession {
  return {
    user: {
      id: "user-owner",
      email: "owner@inflave.test",
      display_name: "Owner",
      role: "owner",
      status: "active",
      created_at: nowIso(0),
    },
    expires_at: nowIso(240),
  };
}

function createWorkflowPreset(): MockWorkflowPreset {
  return {
    id: "workflow-preset-1",
    key: "pilot-reels",
    version: 1,
    name: "Pilot Reels",
    description: "Primary short-form render preset.",
    workflow_provider: "comfyui",
    voice_provider: "none",
    packaging_provider: "ffmpeg",
    workflow_definition: { nodes: {} },
    input_mapping: { script_text: { source_type: "content_item", source_field: "script" } },
    output_mapping: { video_file: { artifact_type: "video", output_path: "outputs.video" } },
    created_by_user_id: "user-owner",
    created_at: nowIso(0),
    updated_at: nowIso(0),
  };
}

function installMockApi(initialState: Partial<MockApiState> = {}) {
  const state: MockApiState = {
    session: initialState.session ?? null,
    brands: initialState.brands ?? [],
    avatars: initialState.avatars ?? [],
    identityPacks: initialState.identityPacks ?? [],
    assets: initialState.assets ?? [],
    contentItems: initialState.contentItems ?? [],
    reviewTasks: initialState.reviewTasks ?? [],
    auditLogs: initialState.auditLogs ?? [],
    workflowPresets: initialState.workflowPresets ?? [],
    renderJobs: initialState.renderJobs ?? [],
    publishPackages: initialState.publishPackages ?? [],
  };

  let sequence = 0;

  function nextId(prefix: string): string {
    sequence += 1;
    return `${prefix}-${sequence}`;
  }

  function recordAudit(action: string, entityType: string, entityId: string) {
    state.auditLogs.unshift({
      id: nextId("audit"),
      actor_user_id: state.session?.user.id ?? null,
      action,
      entity_type: entityType,
      entity_id: entityId,
      payload: {},
      created_at: nowIso(sequence),
    });
  }

  const fetchMock = vi.fn(async (input: string | URL | Request, options?: RequestInit) => {
    const rawUrl =
      typeof input === "string" || input instanceof URL ? input.toString() : input.url;
    const url = new URL(rawUrl, window.location.origin);
    const method =
      options?.method ??
      (typeof input === "string" || input instanceof URL ? "GET" : input.method) ??
      "GET";
    const normalizedMethod = method.toUpperCase();
    const path = `${url.pathname}${url.search}`;

    const handlers: Array<[string, RegExp, RouteHandler]> = [
      [
        "GET",
        /^\/api\/auth\/session$/,
        async () =>
          state.session ? jsonResponse(state.session) : jsonResponse({ detail: "Authentication required" }, 401),
      ],
      [
        "POST",
        /^\/api\/auth\/bootstrap-owner$/,
        async (_path, requestOptions) => {
          const body = JSON.parse(String(requestOptions?.body));
          state.session = {
            user: {
              id: "user-owner",
              email: body.email,
              display_name: body.display_name,
              role: "owner",
              status: "active",
              created_at: nowIso(0),
            },
            expires_at: nowIso(240),
          };
          recordAudit("auth.bootstrap_owner", "user", state.session.user.id);
          return jsonResponse(state.session, 201);
        },
      ],
      [
        "POST",
        /^\/api\/auth\/login$/,
        async (_path, requestOptions) => {
          const body = JSON.parse(String(requestOptions?.body));
          state.session = {
            ...createOwnerSession(),
            user: {
              ...createOwnerSession().user,
              email: body.email,
            },
          };
          recordAudit("auth.login", "user", state.session.user.id);
          return jsonResponse(state.session);
        },
      ],
      [
        "POST",
        /^\/api\/auth\/invites\/accept$/,
        async (_path, requestOptions) => {
          const body = JSON.parse(String(requestOptions?.body));
          state.session = {
            user: {
              id: "user-reviewer",
              email: body.email,
              display_name: body.display_name,
              role: "reviewer",
              status: "active",
              created_at: nowIso(1),
            },
            expires_at: nowIso(240),
          };
          recordAudit("auth.invite_accepted", "user", state.session.user.id);
          return jsonResponse(state.session, 201);
        },
      ],
      [
        "POST",
        /^\/api\/auth\/logout$/,
        async () => {
          state.session = null;
          return jsonResponse({ status: "ok" });
        },
      ],
      ["GET", /^\/api\/brands$/, async () => jsonResponse({ items: state.brands })],
      [
        "POST",
        /^\/api\/brands$/,
        async (_path, requestOptions) => {
          const body = JSON.parse(String(requestOptions?.body));
          const brand: MockBrand = {
            id: nextId("brand"),
            name: body.name,
            voice_notes: body.voice_notes || null,
            created_by_user_id: state.session?.user.id ?? "system",
            created_at: nowIso(sequence),
            updated_at: nowIso(sequence),
          };
          state.brands.unshift(brand);
          recordAudit("brand.created", "brand", brand.id);
          return jsonResponse(brand, 201);
        },
      ],
      ["GET", /^\/api\/avatars$/, async () => jsonResponse({ items: state.avatars })],
      [
        "POST",
        /^\/api\/avatars$/,
        async (_path, requestOptions) => {
          const body = JSON.parse(String(requestOptions?.body));
          const avatar: MockAvatar = {
            id: nextId("avatar"),
            brand_id: body.brand_id,
            name: body.name,
            persona_notes: body.persona_notes || null,
            status: "draft",
            created_by_user_id: state.session?.user.id ?? "system",
            created_at: nowIso(sequence),
            updated_at: nowIso(sequence),
          };
          state.avatars.unshift(avatar);
          recordAudit("avatar.created", "avatar", avatar.id);
          return jsonResponse(avatar, 201);
        },
      ],
      [
        "GET",
        /^\/api\/avatars\/[^/]+\/identity-packs$/,
        async (matchedPath) => {
          const avatarId = matchedPath.split("/")[3];
          return jsonResponse({
            items: state.identityPacks.filter((identityPack) => identityPack.avatar_id === avatarId),
          });
        },
      ],
      [
        "POST",
        /^\/api\/avatars\/[^/]+\/identity-packs$/,
        async (matchedPath, requestOptions) => {
          const avatarId = matchedPath.split("/")[3];
          const body = JSON.parse(String(requestOptions?.body));
          const identityPack: MockIdentityPack = {
            id: nextId("identity"),
            avatar_id: avatarId,
            name: body.name,
            description: body.description || null,
            storage_prefix: body.storage_prefix,
            status: "draft",
            created_at: nowIso(sequence),
            updated_at: nowIso(sequence),
          };
          state.identityPacks.unshift(identityPack);
          recordAudit("identity_pack.created", "identity_pack", identityPack.id);
          return jsonResponse(identityPack, 201);
        },
      ],
      ["GET", /^\/api\/assets$/, async () => jsonResponse({ items: state.assets })],
      [
        "POST",
        /^\/api\/assets\/uploads$/,
        async (_path, requestOptions) => {
          const body = JSON.parse(String(requestOptions?.body));
          const asset: MockAsset = {
            id: nextId("asset"),
            brand_id: body.brand_id,
            object_key: `uploads/${body.brand_id}/${body.filename}`,
            filename: body.filename,
            content_type: body.content_type,
            byte_size: body.byte_size ?? null,
            checksum_sha256: null,
            status: "pending_upload",
            upload_expires_at: nowIso(30),
            created_at: nowIso(sequence),
            updated_at: nowIso(sequence),
          };
          state.assets.unshift(asset);
          recordAudit("asset.upload_initiated", "asset", asset.id);
          return jsonResponse(
            {
              asset,
              upload: {
                method: "PUT",
                url: `http://localhost:9000/content-factory-assets/${asset.object_key}?signature=demo`,
                headers: { "Content-Type": asset.content_type },
                expires_at: asset.upload_expires_at,
              },
            },
            201,
          );
        },
      ],
      ["PUT", /^\/__storage_proxy\/content-factory-assets\/.+$/, async () => noContentResponse(200)],
      [
        "POST",
        /^\/api\/assets\/[^/]+\/finalize$/,
        async (matchedPath, requestOptions) => {
          const assetId = matchedPath.split("/")[3];
          const body = JSON.parse(String(requestOptions?.body));
          const asset = state.assets.find((item) => item.id === assetId);

          if (!asset) {
            return jsonResponse({ detail: "Asset not found" }, 404);
          }

          asset.status = "ready";
          asset.byte_size = body.byte_size;
          asset.updated_at = nowIso(sequence);
          recordAudit("asset.upload_finalized", "asset", asset.id);
          return jsonResponse(asset);
        },
      ],
      ["GET", /^\/api\/content-items$/, async () => jsonResponse({ items: state.contentItems })],
      [
        "POST",
        /^\/api\/content-items$/,
        async (_path, requestOptions) => {
          const body = JSON.parse(String(requestOptions?.body));
          const contentItem: MockContentItem = {
            id: nextId("content"),
            brand_id: body.brand_id,
            avatar_id: body.avatar_id,
            title: body.title,
            script: body.script,
            channel: body.channel,
            status: "draft",
            planned_publish_at: null,
            created_by_user_id: state.session?.user.id ?? "system",
            created_at: nowIso(sequence),
            updated_at: nowIso(sequence),
          };
          state.contentItems.unshift(contentItem);
          recordAudit("content.created", "content_item", contentItem.id);
          return jsonResponse(contentItem, 201);
        },
      ],
      [
        "POST",
        /^\/api\/content-items\/[^/]+\/plan$/,
        async (matchedPath, requestOptions) => {
          const contentItemId = matchedPath.split("/")[3];
          const body = JSON.parse(String(requestOptions?.body));
          const contentItem = state.contentItems.find((item) => item.id === contentItemId);

          if (!contentItem) {
            return jsonResponse({ detail: "Content item not found" }, 404);
          }

          contentItem.status = "planned";
          contentItem.planned_publish_at = body.planned_publish_at ?? null;
          contentItem.updated_at = nowIso(sequence);
          recordAudit("content.planned", "content_item", contentItem.id);
          return jsonResponse(contentItem);
        },
      ],
      [
        "POST",
        /^\/api\/content-items\/[^/]+\/submit-review$/,
        async (matchedPath) => {
          const contentItemId = matchedPath.split("/")[3];
          const contentItem = state.contentItems.find((item) => item.id === contentItemId);

          if (!contentItem) {
            return jsonResponse({ detail: "Content item not found" }, 404);
          }

          contentItem.status = "review";
          contentItem.updated_at = nowIso(sequence);
          const reviewTask: MockReviewTask = {
            id: nextId("review"),
            content_item_id: contentItem.id,
            assigned_to_user_id: null,
            status: "open",
            decision_notes: null,
            completed_at: null,
            created_at: nowIso(sequence),
            updated_at: nowIso(sequence),
          };
          state.reviewTasks.unshift(reviewTask);
          recordAudit("content.submitted_for_review", "content_item", contentItem.id);
          return jsonResponse(reviewTask, 201);
        },
      ],
      ["GET", /^\/api\/review\/tasks$/, async () => jsonResponse({ items: state.reviewTasks })],
      [
        "POST",
        /^\/api\/review\/tasks\/[^/]+\/approve$/,
        async (matchedPath, requestOptions) => {
          const taskId = matchedPath.split("/")[4];
          const body = JSON.parse(String(requestOptions?.body));
          const reviewTask = state.reviewTasks.find((item) => item.id === taskId);

          if (!reviewTask) {
            return jsonResponse({ detail: "Review task not found" }, 404);
          }

          const contentItem = state.contentItems.find(
            (item) => item.id === reviewTask.content_item_id,
          );
          if (!contentItem) {
            return jsonResponse({ detail: "Content item not found" }, 404);
          }

          reviewTask.status = "approved";
          reviewTask.decision_notes = body.decision_notes ?? null;
          reviewTask.completed_at = nowIso(sequence);
          reviewTask.updated_at = nowIso(sequence);
          contentItem.status = "approved";
          contentItem.updated_at = nowIso(sequence);
          recordAudit("review.approved", "review_task", reviewTask.id);
          return jsonResponse(reviewTask);
        },
      ],
      [
        "POST",
        /^\/api\/review\/tasks\/[^/]+\/request-rework$/,
        async (matchedPath, requestOptions) => {
          const taskId = matchedPath.split("/")[4];
          const body = JSON.parse(String(requestOptions?.body));
          const reviewTask = state.reviewTasks.find((item) => item.id === taskId);

          if (!reviewTask) {
            return jsonResponse({ detail: "Review task not found" }, 404);
          }

          const contentItem = state.contentItems.find(
            (item) => item.id === reviewTask.content_item_id,
          );
          if (!contentItem) {
            return jsonResponse({ detail: "Content item not found" }, 404);
          }

          reviewTask.status = "rework";
          reviewTask.decision_notes = body.decision_notes ?? null;
          reviewTask.completed_at = nowIso(sequence);
          reviewTask.updated_at = nowIso(sequence);
          contentItem.status = "rework";
          contentItem.updated_at = nowIso(sequence);
          recordAudit("review.rework_requested", "review_task", reviewTask.id);
          return jsonResponse(reviewTask);
        },
      ],
      ["GET", /^\/api\/workflow-presets$/, async () => jsonResponse({ items: state.workflowPresets })],
      ["GET", /^\/api\/render-jobs$/, async () => jsonResponse({ items: state.renderJobs })],
      ["GET", /^\/api\/publish-packages$/, async () => jsonResponse({ items: state.publishPackages })],
      [
        "GET",
        /^\/api\/render-jobs\/[^/]+$/,
        async (matchedPath) => {
          const renderJobId = matchedPath.split("/")[3];
          const renderJob = state.renderJobs.find((item) => item.id === renderJobId);

          if (!renderJob) {
            return jsonResponse({ detail: "Render job not found" }, 404);
          }

          return jsonResponse(renderJob);
        },
      ],
      [
        "POST",
        /^\/api\/render-jobs$/,
        async (_path, requestOptions) => {
          const body = JSON.parse(String(requestOptions?.body));
          const contentItem = state.contentItems.find((item) => item.id === body.content_item_id);
          const workflowPreset = state.workflowPresets.find(
            (item) => item.id === body.workflow_preset_id,
          );

          if (!contentItem || !workflowPreset) {
            return jsonResponse({ detail: "Render job could not be created" }, 404);
          }

          const renderJobId = nextId("render");
          const attempt: MockJobAttempt = {
            id: nextId("attempt"),
            render_job_id: renderJobId,
            attempt_number: 1,
            status: "queued",
            provider_job_id: null,
            request_payload: { inputs: { script_text: contentItem.script } },
            response_payload: {},
            error_message: null,
            started_at: null,
            finished_at: null,
            created_at: nowIso(sequence),
            updated_at: nowIso(sequence),
          };
          const renderJob: MockRenderJob = {
            id: renderJobId,
            content_item_id: contentItem.id,
            workflow_preset_id: workflowPreset.id,
            workflow_preset_key: workflowPreset.key,
            workflow_preset_version: workflowPreset.version,
            workflow_provider: workflowPreset.workflow_provider,
            voice_provider: workflowPreset.voice_provider,
            packaging_provider: workflowPreset.packaging_provider,
            input_snapshot: { script_text: contentItem.script },
            status: "queued",
            retry_budget: body.retry_budget ?? 3,
            created_by_user_id: state.session?.user.id ?? "system",
            created_at: nowIso(sequence),
            updated_at: nowIso(sequence),
            attempts: [attempt],
          };
          state.renderJobs.unshift(renderJob);
          recordAudit("render_job.created", "render_job", renderJob.id);
          return jsonResponse(renderJob, 201);
        },
      ],
      [
        "POST",
        /^\/api\/render-jobs\/[^/]+\/cancel$/,
        async (matchedPath) => {
          const renderJobId = matchedPath.split("/")[3];
          const renderJob = state.renderJobs.find((item) => item.id === renderJobId);
          if (!renderJob) {
            return jsonResponse({ detail: "Render job not found" }, 404);
          }
          if (!["queued", "running", "cancelled"].includes(renderJob.status)) {
            return jsonResponse({ detail: "Render job cannot be cancelled from its current status" }, 409);
          }
          renderJob.status = "cancelled";
          renderJob.updated_at = nowIso(sequence);
          renderJob.attempts.forEach((attempt) => {
            if (attempt.status === "queued" || attempt.status === "running") {
              attempt.status = "cancelled";
              attempt.error_message = attempt.error_message ?? "Cancelled by operator";
              attempt.finished_at = attempt.finished_at ?? nowIso(sequence);
              attempt.updated_at = nowIso(sequence);
            }
          });
          recordAudit("render_job.cancelled", "render_job", renderJob.id);
          return jsonResponse(renderJob);
        },
      ],
      [
        "POST",
        /^\/api\/render-jobs\/[^/]+\/retry$/,
        async (matchedPath) => {
          const renderJobId = matchedPath.split("/")[3];
          const renderJob = state.renderJobs.find((item) => item.id === renderJobId);
          if (!renderJob) {
            return jsonResponse({ detail: "Render job not found" }, 404);
          }
          if (!["failed", "cancelled"].includes(renderJob.status)) {
            return jsonResponse({ detail: "Render job can only be retried after failure or cancellation" }, 409);
          }
          const latestAttempt = [...renderJob.attempts].sort(
            (left, right) => right.attempt_number - left.attempt_number,
          )[0];
          const nextAttempt: MockJobAttempt = {
            id: nextId("attempt"),
            render_job_id: renderJob.id,
            attempt_number: latestAttempt ? latestAttempt.attempt_number + 1 : 1,
            status: "queued",
            provider_job_id: null,
            request_payload: latestAttempt?.request_payload ?? { inputs: renderJob.input_snapshot },
            response_payload: {},
            error_message: null,
            started_at: null,
            finished_at: null,
            created_at: nowIso(sequence),
            updated_at: nowIso(sequence),
          };
          renderJob.status = "queued";
          renderJob.updated_at = nowIso(sequence);
          renderJob.attempts.push(nextAttempt);
          recordAudit("render_job.retried", "render_job", renderJob.id);
          return jsonResponse(renderJob);
        },
      ],
      [
        "POST",
        /^\/api\/render-jobs\/[^/]+\/requeue$/,
        async (matchedPath) => {
          const renderJobId = matchedPath.split("/")[3];
          const renderJob = state.renderJobs.find((item) => item.id === renderJobId);
          if (!renderJob) {
            return jsonResponse({ detail: "Render job not found" }, 404);
          }
          if (renderJob.status !== "queued") {
            return jsonResponse({ detail: "Render job can only be requeued while queued" }, 409);
          }
          if (!renderJob.attempts.some((attempt) => attempt.status === "queued")) {
            const latestAttempt = [...renderJob.attempts].sort(
              (left, right) => right.attempt_number - left.attempt_number,
            )[0];
            renderJob.attempts.push({
              id: nextId("attempt"),
              render_job_id: renderJob.id,
              attempt_number: latestAttempt ? latestAttempt.attempt_number + 1 : 1,
              status: "queued",
              provider_job_id: null,
              request_payload: latestAttempt?.request_payload ?? { inputs: renderJob.input_snapshot },
              response_payload: {},
              error_message: null,
              started_at: null,
              finished_at: null,
              created_at: nowIso(sequence),
              updated_at: nowIso(sequence),
            });
          }
          recordAudit("render_job.requeued", "render_job", renderJob.id);
          return jsonResponse(renderJob);
        },
      ],
      [
        "POST",
        /^\/api\/publish-packages$/,
        async (_path, requestOptions) => {
          const body = JSON.parse(String(requestOptions?.body));
          const renderJob = state.renderJobs.find((item) => item.id === body.render_job_id);
          if (!renderJob || renderJob.status !== "succeeded") {
            return jsonResponse({ detail: "Render job must succeed before package export" }, 409);
          }

          const existingPackage = state.publishPackages.find(
            (publishPackage) => publishPackage.render_job_id === renderJob.id,
          );
          if (existingPackage) {
            return jsonResponse(existingPackage);
          }

          const publishPackage: MockPublishPackage = {
            id: nextId("package"),
            render_job_id: renderJob.id,
            content_item_id: renderJob.content_item_id,
            status: "queued",
            package_object_key: null,
            manifest_payload: {},
            byte_size: null,
            error_message: null,
            created_by_user_id: state.session?.user.id ?? "system",
            created_at: nowIso(sequence),
            updated_at: nowIso(sequence),
          };
          state.publishPackages.unshift(publishPackage);
          recordAudit("publish_package.created", "publish_package", publishPackage.id);
          return jsonResponse(publishPackage, 201);
        },
      ],
      [
        "POST",
        /^\/api\/publish-packages\/[^/]+\/cancel$/,
        async (matchedPath) => {
          const packageId = matchedPath.split("/")[3];
          const publishPackage = state.publishPackages.find((item) => item.id === packageId);
          if (!publishPackage) {
            return jsonResponse({ detail: "Publish package not found" }, 404);
          }
          if (!["queued", "running", "cancelled"].includes(publishPackage.status)) {
            return jsonResponse({ detail: "Publish package cannot be cancelled from its current status" }, 409);
          }
          publishPackage.status = "cancelled";
          publishPackage.error_message = publishPackage.error_message ?? "Cancelled by operator";
          publishPackage.updated_at = nowIso(sequence);
          recordAudit("publish_package.cancelled", "publish_package", publishPackage.id);
          return jsonResponse(publishPackage);
        },
      ],
      [
        "POST",
        /^\/api\/publish-packages\/[^/]+\/retry$/,
        async (matchedPath) => {
          const packageId = matchedPath.split("/")[3];
          const publishPackage = state.publishPackages.find((item) => item.id === packageId);
          if (!publishPackage) {
            return jsonResponse({ detail: "Publish package not found" }, 404);
          }
          if (!["failed", "cancelled"].includes(publishPackage.status)) {
            return jsonResponse({ detail: "Publish package can only be retried after failure or cancellation" }, 409);
          }
          publishPackage.status = "queued";
          publishPackage.package_object_key = null;
          publishPackage.manifest_payload = {};
          publishPackage.byte_size = null;
          publishPackage.error_message = null;
          publishPackage.updated_at = nowIso(sequence);
          recordAudit("publish_package.retried", "publish_package", publishPackage.id);
          return jsonResponse(publishPackage);
        },
      ],
      [
        "POST",
        /^\/api\/publish-packages\/[^/]+\/requeue$/,
        async (matchedPath) => {
          const packageId = matchedPath.split("/")[3];
          const publishPackage = state.publishPackages.find((item) => item.id === packageId);
          if (!publishPackage) {
            return jsonResponse({ detail: "Publish package not found" }, 404);
          }
          if (publishPackage.status !== "queued") {
            return jsonResponse({ detail: "Publish package can only be requeued while queued" }, 409);
          }
          recordAudit("publish_package.requeued", "publish_package", publishPackage.id);
          return jsonResponse(publishPackage);
        },
      ],
      [
        "GET",
        /^\/api\/publish-packages\/[^/]+\/download$/,
        async (matchedPath) => {
          const packageId = matchedPath.split("/")[3];
          const publishPackage = state.publishPackages.find((item) => item.id === packageId);
          if (!publishPackage || publishPackage.status !== "ready") {
            return jsonResponse({ detail: "Publish package is not ready for download" }, 409);
          }
          return jsonResponse({
            package: publishPackage,
            download: {
              method: "GET",
              url: `http://localhost:9000/content-factory-assets/${publishPackage.package_object_key}?signature=demo`,
              headers: {},
              expires_at: nowIso(30),
            },
          });
        },
      ],
      [
        "GET",
        /^\/api\/audit\/logs$/,
        async () => {
          if (state.session?.user.role === "reviewer" || state.session?.user.role === "viewer") {
            return jsonResponse({ detail: "Forbidden" }, 403);
          }

          return jsonResponse({ items: state.auditLogs });
        },
      ],
    ];

    const handler = handlers.find(
      ([candidateMethod, pattern]) =>
        candidateMethod === normalizedMethod && pattern.test(url.pathname),
    );

    if (!handler) {
      throw new Error(`Unhandled request: ${normalizedMethod} ${path}`);
    }

    return handler[2](url.pathname, options, state);
  });

  vi.stubGlobal("fetch", fetchMock);
  return { state, fetchMock };
}

beforeEach(() => {
  window.location.hash = "";
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("App", () => {
  test("shows the auth gate and bootstraps the first owner", async () => {
    installMockApi();

    render(<App />);

    expect(await screen.findByRole("heading", { name: /content factory control plane/i })).toBeVisible();

    fireEvent.click(screen.getByRole("tab", { name: /bootstrap owner/i }));
    fireEvent.click(screen.getByRole("button", { name: /create first owner/i }));

    expect(await screen.findByText(/owner bootstrapped and signed in/i)).toBeVisible();
    expect(await screen.findByRole("heading", { name: /operator command posture/i })).toBeVisible();
    expect(
      (await screen.findAllByText(/create the first brand to open the intake and drafting loop/i))
        .length,
    ).toBeGreaterThan(0);
  });

  test("runs the pilot cockpit flow from brand creation to render queue", async () => {
    installMockApi({ session: createOwnerSession(), workflowPresets: [createWorkflowPreset()] });
    window.location.hash = "#brands-assets";

    render(<App />);

    expect(await screen.findByRole("heading", { name: /control voice and guardrails/i })).toBeVisible();

    fireEvent.change(screen.getByLabelText(/brand name/i), { target: { value: "Inflave" } });
    fireEvent.change(screen.getByLabelText(/voice notes/i), {
      target: { value: "Confident, compliant, concise." },
    });
    fireEvent.click(screen.getByRole("button", { name: /create brand/i }));

    expect(await screen.findByText(/brand created\./i)).toBeVisible();
    expect(await screen.findByRole("heading", { name: /^Inflave$/i })).toBeVisible();

    const file = new File(["pilot-reference"], "script-reference.png", { type: "image/png" });
    fireEvent.change(screen.getByLabelText(/upload file/i), { target: { files: [file] } });
    fireEvent.click(screen.getByRole("button", { name: /upload asset/i }));

    expect(await screen.findByText(/asset uploaded and finalized\./i)).toBeVisible();
    expect(await screen.findByText(/script-reference\.png/i)).toBeVisible();
    expect(await screen.findByText(/^ready$/i)).toBeVisible();

    fireEvent.click(screen.getByRole("button", { name: /avatars/i }));
    expect(await screen.findByRole("heading", { name: /anchor the pilot persona/i })).toBeVisible();

    fireEvent.change(screen.getByLabelText(/avatar name/i), { target: { value: "Primary Host" } });
    fireEvent.change(screen.getByLabelText(/persona notes/i), {
      target: { value: "Human-like pilot avatar." },
    });
    fireEvent.click(screen.getByRole("button", { name: /create avatar/i }));

    expect(await screen.findByText(/avatar created\./i)).toBeVisible();
    await waitFor(() => {
      expect(screen.getAllByText("Primary Host").length).toBeGreaterThan(0);
    });

    fireEvent.change(screen.getByLabelText(/identity pack name/i), {
      target: { value: "Core identity" },
    });
    fireEvent.change(screen.getByLabelText(/^description$/i), {
      target: { value: "Pilot voice and look references." },
    });
    fireEvent.change(screen.getByLabelText(/storage prefix/i), {
      target: { value: "identity/core" },
    });
    fireEvent.click(screen.getByRole("button", { name: /create identity pack/i }));

    expect(await screen.findByText(/identity pack created\./i)).toBeVisible();
    await waitFor(() => {
      expect(screen.getAllByText("Core identity").length).toBeGreaterThan(0);
    });

    fireEvent.click(screen.getByRole("button", { name: /content/i }));
    expect(await screen.findByRole("heading", { name: /turn scripts into reviewable items/i })).toBeVisible();

    fireEvent.change(screen.getByLabelText(/content title/i), { target: { value: "Pilot short" } });
    fireEvent.change(screen.getByLabelText(/^script$/i), {
      target: { value: "A careful, platform-safe short script." },
    });
    fireEvent.click(screen.getByRole("button", { name: /create content item/i }));

    expect(await screen.findByText(/content item created\./i)).toBeVisible();
    expect(await screen.findByRole("heading", { name: /^Pilot short$/i })).toBeVisible();

    fireEvent.click(screen.getByRole("button", { name: /^plan$/i }));
    expect(await screen.findByText(/content item planned\./i)).toBeVisible();
    expect(await screen.findByText(/^planned$/i)).toBeVisible();

    fireEvent.click(screen.getByRole("button", { name: /send to review/i }));
    expect(await screen.findByText(/content item submitted for review\./i)).toBeVisible();

    fireEvent.click(screen.getByRole("button", { name: /^review$/i }));
    expect(await screen.findByRole("heading", { name: /human approvals stay in the loop/i })).toBeVisible();

    fireEvent.change(screen.getByLabelText(/decision notes/i), {
      target: { value: "Approved for manual publishing." },
    });
    fireEvent.click(screen.getByRole("button", { name: /^approve$/i }));

    expect(await screen.findByText(/review task approved\./i)).toBeVisible();
    expect(await screen.findByText(/approved for manual publishing\./i)).toBeVisible();
    expect(await screen.findByText(/^approved$/i)).toBeVisible();

    fireEvent.click(screen.getByRole("button", { name: /^audit$/i }));
    expect(await screen.findByRole("heading", { name: /recent control-plane actions/i })).toBeVisible();
    await waitFor(() => {
      expect(screen.getByText(/review\.approved/i)).toBeVisible();
    });

    fireEvent.click(screen.getByRole("button", { name: /^render$/i }));
    expect(await screen.findByRole("heading", { name: /render queue/i })).toBeVisible();
    fireEvent.click(screen.getByRole("button", { name: /create render job/i }));

    expect(await screen.findByText(/render job created\./i)).toBeVisible();
    expect((await screen.findAllByText(/pilot-reels v1/i)).length).toBeGreaterThan(0);
    expect((await screen.findAllByText(/^queued$/i)).length).toBeGreaterThan(0);
  });

  test("runs render job operator actions", async () => {
    const contentItem: MockContentItem = {
      id: "content-planned",
      brand_id: "brand-1",
      avatar_id: "avatar-1",
      title: "Pilot short",
      script: "A careful, platform-safe short script.",
      channel: "youtube_shorts",
      status: "planned",
      planned_publish_at: null,
      created_by_user_id: "user-owner",
      created_at: nowIso(0),
      updated_at: nowIso(0),
    };
    const workflowPreset = createWorkflowPreset();
    const renderJob: MockRenderJob = {
      id: "render-queued",
      content_item_id: contentItem.id,
      workflow_preset_id: workflowPreset.id,
      workflow_preset_key: workflowPreset.key,
      workflow_preset_version: workflowPreset.version,
      workflow_provider: workflowPreset.workflow_provider,
      voice_provider: workflowPreset.voice_provider,
      packaging_provider: workflowPreset.packaging_provider,
      input_snapshot: { script_text: contentItem.script },
      status: "queued",
      retry_budget: 1,
      created_by_user_id: "user-owner",
      created_at: nowIso(1),
      updated_at: nowIso(2),
      attempts: [
        {
          id: "attempt-1",
          render_job_id: "render-queued",
          attempt_number: 1,
          status: "queued",
          provider_job_id: null,
          request_payload: { inputs: { script_text: contentItem.script } },
          response_payload: {},
          error_message: null,
          started_at: null,
          finished_at: null,
          created_at: nowIso(1),
          updated_at: nowIso(2),
        },
      ],
    };
    installMockApi({
      session: createOwnerSession(),
      contentItems: [contentItem],
      workflowPresets: [workflowPreset],
      renderJobs: [renderJob],
    });
    window.location.hash = "#render";

    render(<App />);

    expect(await screen.findByRole("heading", { name: /render queue/i })).toBeVisible();
    fireEvent.click(screen.getByRole("button", { name: /requeue job/i }));
    expect(await screen.findByText(/render job requeued\./i)).toBeVisible();

    fireEvent.click(screen.getByRole("button", { name: /cancel job/i }));
    expect(await screen.findByText(/render job cancelled\./i)).toBeVisible();
    expect((await screen.findAllByText(/^cancelled$/i)).length).toBeGreaterThan(0);

    fireEvent.click(screen.getByRole("button", { name: /retry job/i }));
    expect(await screen.findByText(/render job retried\./i)).toBeVisible();
    expect((await screen.findAllByText(/^queued$/i)).length).toBeGreaterThan(0);
  });

  test("prepares a publish package from a succeeded approved render", async () => {
    const contentItem: MockContentItem = {
      id: "content-approved",
      brand_id: "brand-1",
      avatar_id: "avatar-1",
      title: "Pilot short",
      script: "A careful, platform-safe short script.",
      channel: "youtube_shorts",
      status: "approved",
      planned_publish_at: null,
      created_by_user_id: "user-owner",
      created_at: nowIso(0),
      updated_at: nowIso(0),
    };
    const workflowPreset = createWorkflowPreset();
    const renderJob: MockRenderJob = {
      id: "render-succeeded",
      content_item_id: contentItem.id,
      workflow_preset_id: workflowPreset.id,
      workflow_preset_key: workflowPreset.key,
      workflow_preset_version: workflowPreset.version,
      workflow_provider: workflowPreset.workflow_provider,
      voice_provider: workflowPreset.voice_provider,
      packaging_provider: workflowPreset.packaging_provider,
      input_snapshot: { script_text: contentItem.script },
      status: "succeeded",
      retry_budget: 3,
      created_by_user_id: "user-owner",
      created_at: nowIso(1),
      updated_at: nowIso(2),
      attempts: [
        {
          id: "attempt-1",
          render_job_id: "render-succeeded",
          attempt_number: 1,
          status: "succeeded",
          provider_job_id: "comfyui-1",
          request_payload: { inputs: { script_text: contentItem.script } },
          response_payload: {
            outputs: { video_file: "s3://content-factory-assets/renders/video.mp4" },
          },
          error_message: null,
          started_at: nowIso(1),
          finished_at: nowIso(2),
          created_at: nowIso(1),
          updated_at: nowIso(2),
        },
      ],
    };
    installMockApi({
      session: createOwnerSession(),
      contentItems: [contentItem],
      workflowPresets: [workflowPreset],
      renderJobs: [renderJob],
    });
    window.location.hash = "#export";

    render(<App />);

    expect(await screen.findByRole("heading", { name: /publish packages/i })).toBeVisible();
    expect((await screen.findAllByText(/pilot-reels v1/i)).length).toBeGreaterThan(0);
    fireEvent.click(screen.getByRole("button", { name: /create package/i }));

    expect(await screen.findByText(/publish package queued\./i)).toBeVisible();
    expect(
      await screen.findByText(/no succeeded approved renders waiting for package export/i),
    ).toBeVisible();
    expect((await screen.findAllByText(/^queued$/i)).length).toBeGreaterThan(0);

    fireEvent.click(screen.getByRole("button", { name: /requeue package/i }));
    expect(await screen.findByText(/publish package requeued\./i)).toBeVisible();

    fireEvent.click(screen.getByRole("button", { name: /cancel package/i }));
    expect(await screen.findByText(/publish package cancelled\./i)).toBeVisible();
    expect((await screen.findAllByText(/^cancelled$/i)).length).toBeGreaterThan(0);

    fireEvent.click(screen.getByRole("button", { name: /retry package/i }));
    expect(await screen.findByText(/publish package retried\./i)).toBeVisible();
    expect((await screen.findAllByText(/^queued$/i)).length).toBeGreaterThan(0);
  });
});

```

`apps/web/src/app/App.tsx`:

```tsx
import "./App.css";

import { startTransition, useCallback, useEffect, useState } from "react";

import { AuthPanel } from "../features/auth/AuthPanel";
import { AuditPanel } from "../features/audit/AuditPanel";
import { AvatarsPanel } from "../features/avatars/AvatarsPanel";
import { BrandsAssetsPanel } from "../features/brands-assets/BrandsAssetsPanel";
import { ContentPanel } from "../features/content/ContentPanel";
import { ExportPanel } from "../features/export/ExportPanel";
import { RenderPanel } from "../features/render/RenderPanel";
import { ReviewPanel } from "../features/review/ReviewPanel";
import { webEnv } from "../config/env";
import { apiClient, describeApiBase, isApiError } from "../shared/api/client";
import {
  emptyCockpitData,
  type AuthSession,
  type CockpitData,
  type RenderJob,
  type UserRole,
} from "../shared/api/types";
import { formatDateTime } from "../shared/format";
import { cockpitRoutes, normalizeCockpitRoute, toCockpitHash, type CockpitRouteId } from "./routes";

type SessionState =
  | { kind: "loading" }
  | { kind: "anonymous" }
  | { kind: "authenticated"; session: AuthSession };

interface RenderJobStatusEvent {
  event: "render_job.snapshot";
  render_job: RenderJob;
}

function canMutateRole(role: UserRole): boolean {
  return role === "owner" || role === "operator";
}

function canReviewRole(role: UserRole): boolean {
  return role === "owner" || role === "reviewer";
}

function canViewAuditRole(role: UserRole): boolean {
  return role === "owner" || role === "operator";
}

function messageFromError(error: unknown): string {
  if (isApiError(error)) {
    return error.detail;
  }

  if (error instanceof Error && error.message.trim().length > 0) {
    return error.message;
  }

  return "Unexpected error";
}

function readHashRoute(): CockpitRouteId {
  if (typeof window === "undefined") {
    return "overview";
  }

  return normalizeCockpitRoute(window.location.hash.replace(/^#/, ""));
}

function countByStatus<TItem extends { status: string }>(items: TItem[], status: string): number {
  return items.filter((item) => item.status === status).length;
}

function nextStepForData(data: CockpitData): string {
  if (data.brands.length === 0) {
    return "Create the first brand to open the intake and drafting loop.";
  }

  if (data.avatars.length === 0) {
    return "Add the pilot avatar so drafts can be attached to a concrete host persona.";
  }

  if (data.contentItems.length === 0) {
    return "Draft the first short-form content item and push it into review.";
  }

  if (countByStatus(data.reviewTasks, "open") > 0) {
    return "Review queue has open decisions waiting for a human approver.";
  }

  if (countByStatus(data.contentItems, "approved") > 0 && data.renderJobs.length === 0) {
    return "Approved content is ready for its first render job.";
  }

  if (
    data.renderJobs.some((renderJob) => renderJob.status === "succeeded") &&
    data.publishPackages.length === 0
  ) {
    return "Succeeded renders are ready for export packaging.";
  }

  return "Cockpit is ready for the next operator pass.";
}

export function App() {
  const [route, setRoute] = useState<CockpitRouteId>(readHashRoute);
  const [sessionState, setSessionState] = useState<SessionState>({ kind: "loading" });
  const [cockpitData, setCockpitData] = useState<CockpitData>(emptyCockpitData);
  const [busyLabel, setBusyLabel] = useState<string | null>(null);
  const [screenError, setScreenError] = useState<string | null>(null);
  const [flashMessage, setFlashMessage] = useState<string | null>(null);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [liveRenderJobId, setLiveRenderJobId] = useState<string | null>(null);

  const refreshCockpit = useCallback(async (role: UserRole) => {
    const [
      brandsResponse,
      avatarsResponse,
      assetsResponse,
      contentResponse,
      reviewResponse,
      workflowPresetsResponse,
      renderJobsResponse,
      publishPackagesResponse,
    ] =
      await Promise.all([
        apiClient.listBrands(),
        apiClient.listAvatars(),
        apiClient.listAssets(),
        apiClient.listContentItems(),
        apiClient.listReviewTasks(),
        apiClient.listWorkflowPresets(),
        apiClient.listRenderJobs(),
        apiClient.listPublishPackages(),
      ]);

    const identityPackLists = await Promise.all(
      avatarsResponse.items.map((avatar) => apiClient.listIdentityPacks(avatar.id)),
    );

    let auditLogs = emptyCockpitData.auditLogs;
    if (canViewAuditRole(role)) {
      try {
        auditLogs = (await apiClient.listAuditLogs()).items;
      } catch (error) {
        if (!isApiError(error) || error.status !== 403) {
          throw error;
        }
      }
    }

    startTransition(() => {
      setCockpitData({
        brands: brandsResponse.items,
        avatars: avatarsResponse.items,
        identityPacks: identityPackLists.flatMap((response) => response.items),
        assets: assetsResponse.items,
        contentItems: contentResponse.items,
        reviewTasks: reviewResponse.items,
        auditLogs,
        workflowPresets: workflowPresetsResponse.items,
        renderJobs: renderJobsResponse.items,
        publishPackages: publishPackagesResponse.items,
      });
    });
  }, []);

  const loadSession = useCallback(async () => {
    setScreenError(null);
    setFlashMessage(null);
    setIsRefreshing(true);

    try {
      const session = await apiClient.getSession();
      startTransition(() => {
        setSessionState({ kind: "authenticated", session });
      });
      await refreshCockpit(session.user.role);
    } catch (error) {
      if (isApiError(error) && error.status === 401) {
        startTransition(() => {
          setSessionState({ kind: "anonymous" });
          setCockpitData(emptyCockpitData);
        });
      } else {
        startTransition(() => {
          setSessionState({ kind: "anonymous" });
          setCockpitData(emptyCockpitData);
        });
        setScreenError(messageFromError(error));
      }
    } finally {
      setIsRefreshing(false);
    }
  }, [refreshCockpit]);

  useEffect(() => {
    let cancelled = false;
    void Promise.resolve().then(() => {
      if (!cancelled) {
        void loadSession();
      }
    });
    return () => {
      cancelled = true;
    };
  }, [loadSession]);

  useEffect(() => {
    const syncRoute = () => {
      setRoute(readHashRoute());
    };

    syncRoute();
    window.addEventListener("hashchange", syncRoute);
    return () => window.removeEventListener("hashchange", syncRoute);
  }, []);

  useEffect(() => {
    if (
      sessionState.kind !== "authenticated" ||
      liveRenderJobId === null ||
      typeof EventSource === "undefined"
    ) {
      return;
    }

    const source = new EventSource(apiClient.renderJobEventsUrl(liveRenderJobId), {
      withCredentials: true,
    });
    const handleSnapshot = (event: MessageEvent<string>) => {
      const payload = JSON.parse(event.data) as RenderJobStatusEvent;
      setCockpitData((current) => ({
        ...current,
        renderJobs: [
          payload.render_job,
          ...current.renderJobs.filter((renderJob) => renderJob.id !== payload.render_job.id),
        ],
      }));

      if (["succeeded", "failed", "cancelled"].includes(payload.render_job.status)) {
        source.close();
      }
    };

    source.addEventListener("render_job.snapshot", handleSnapshot as EventListener);
    source.onerror = () => source.close();
    return () => source.close();
  }, [liveRenderJobId, sessionState.kind]);

  async function completeAuthentication(session: AuthSession, successMessage: string) {
    setScreenError(null);
    setFlashMessage(successMessage);
    setIsRefreshing(true);
    startTransition(() => {
      setSessionState({ kind: "authenticated", session });
    });

    try {
      await refreshCockpit(session.user.role);
    } catch (error) {
      setScreenError(messageFromError(error));
    } finally {
      setIsRefreshing(false);
    }
  }

  async function runSessionAction(
    label: string,
    action: () => Promise<AuthSession>,
    successMessage: string,
  ) {
    setBusyLabel(label);
    setScreenError(null);
    setFlashMessage(null);

    try {
      const session = await action();
      await completeAuthentication(session, successMessage);
    } catch (error) {
      setScreenError(messageFromError(error));
    } finally {
      setBusyLabel(null);
    }
  }

  async function runCockpitMutation(
    label: string,
    action: () => Promise<unknown>,
    successMessage: string,
  ) {
    if (sessionState.kind !== "authenticated") {
      return;
    }

    setBusyLabel(label);
    setScreenError(null);
    setFlashMessage(null);

    try {
      await action();
      setIsRefreshing(true);
      await refreshCockpit(sessionState.session.user.role);
      setFlashMessage(successMessage);
    } catch (error) {
      setScreenError(messageFromError(error));
    } finally {
      setBusyLabel(null);
      setIsRefreshing(false);
    }
  }

  if (sessionState.kind === "loading") {
    return (
      <main className="loading-shell">
        <div className="surface loading-card">
          <p className="eyebrow">Phase 1 cockpit</p>
          <h1>Loading session</h1>
          <p className="panel-copy">Checking the current operator cookie and restoring the cockpit.</p>
        </div>
      </main>
    );
  }

  if (sessionState.kind === "anonymous") {
    return (
      <main className="shell">
        <AuthPanel
          appName={webEnv.VITE_APP_NAME}
          apiBaseLabel={describeApiBase()}
          busy={busyLabel !== null}
          error={screenError}
          onLogin={(payload) =>
            runSessionAction("login", () => apiClient.login(payload), "Session opened.")
          }
          onBootstrapOwner={(payload) =>
            runSessionAction(
              "bootstrap owner",
              () => apiClient.bootstrapOwner(payload),
              "Owner bootstrapped and signed in.",
            )
          }
          onAcceptInvite={(payload) =>
            runSessionAction(
              "accept invite",
              () => apiClient.acceptInvite(payload),
              "Invite accepted and session opened.",
            )
          }
        />
      </main>
    );
  }

  const { session } = sessionState;
  const canMutate = canMutateRole(session.user.role);
  const canReview = canReviewRole(session.user.role);
  const canViewAudit = canViewAuditRole(session.user.role);
  const readyAssets = countByStatus(cockpitData.assets, "ready");
  const openReviewTasks = countByStatus(cockpitData.reviewTasks, "open");

  return (
    <main className="shell cockpit-shell">
      <section className="hero surface">
        <div>
          <p className="eyebrow">Protected control plane</p>
          <h1>{webEnv.VITE_APP_NAME}</h1>
          <p className="lede">{nextStepForData(cockpitData)}</p>
        </div>

        <div className="hero-side">
          <article className="session-card">
            <span className="meta-label">Signed in as</span>
            <strong>{session.user.display_name}</strong>
            <p>
              {session.user.email} · {session.user.role}
            </p>
            <p>Session expires {formatDateTime(session.expires_at)}</p>
            <button
              className="ghost-button"
              disabled={busyLabel !== null}
              type="button"
              onClick={async () => {
                setBusyLabel("logout");
                setScreenError(null);
                setFlashMessage(null);

                try {
                  await apiClient.logout();
                  startTransition(() => {
                    setSessionState({ kind: "anonymous" });
                    setCockpitData(emptyCockpitData);
                  });
                } catch (error) {
                  setScreenError(messageFromError(error));
                } finally {
                  setBusyLabel(null);
                }
              }}
            >
              Sign out
            </button>
          </article>

          <article className="session-card">
            <span className="meta-label">Integration target</span>
            <strong>{describeApiBase()}</strong>
            <p>Role gates: mutate {canMutate ? "enabled" : "disabled"} · review {canReview ? "enabled" : "disabled"}</p>
          </article>
        </div>
      </section>

      <section className="summary-grid">
        <article className="metric-card surface">
          <span className="metric-label">Brands</span>
          <strong>{cockpitData.brands.length}</strong>
          <p>Voice context ready for drafting and review.</p>
        </article>
        <article className="metric-card surface">
          <span className="metric-label">Ready assets</span>
          <strong>{readyAssets}</strong>
          <p>Source material finalized after signed uploads.</p>
        </article>
        <article className="metric-card surface">
          <span className="metric-label">Open review</span>
          <strong>{openReviewTasks}</strong>
          <p>Human decisions waiting in the approval queue.</p>
        </article>
        <article className="metric-card surface">
          <span className="metric-label">Drafts in system</span>
          <strong>{cockpitData.contentItems.length}</strong>
                  <p>Content items across lifecycle states. Render jobs: {cockpitData.renderJobs.length}.</p>
        </article>
      </section>

      {screenError ? (
        <p className="banner error" role="alert">
          {screenError}
        </p>
      ) : null}
      {flashMessage ? (
        <p className="banner success" role="status">
          {flashMessage}
        </p>
      ) : null}
      {isRefreshing ? (
        <p className="banner info" role="status">
          Syncing cockpit data...
        </p>
      ) : null}

      <div className="workspace-grid">
        <nav className="surface nav-card" aria-label="Cockpit navigation">
          {cockpitRoutes.map((navigationItem) => (
            <button
              key={navigationItem.id}
              className={navigationItem.id === route ? "nav-link active" : "nav-link"}
              type="button"
              onClick={() => {
                window.location.hash = toCockpitHash(navigationItem.id);
              }}
            >
              {navigationItem.label}
            </button>
          ))}
        </nav>

        <section className="workspace-panel">
          {route === "overview" ? (
            <section className="surface panel-stack">
              <div className="panel-header">
                <div>
                  <p className="eyebrow">Overview</p>
                  <h2>Operator command posture</h2>
                </div>
                <span className="count-pill">Phase 1 slice</span>
              </div>
              <p className="panel-copy">
                This cockpit deliberately stays narrow: bootstrap session, collect assets,
                connect avatars, move drafts through review, and preserve an audit trail.
              </p>
              <div className="list-stack">
                <article className="list-card">
                  <div className="list-card-header">
                    <h3>Current operator role</h3>
                    <span className="status-badge neutral">{session.user.role}</span>
                  </div>
                  <p>Signed in as {session.user.display_name}. Permissions are derived from the backend RBAC contract.</p>
                </article>
                <article className="list-card">
                  <div className="list-card-header">
                    <h3>Immediate next step</h3>
                    <span className="status-badge neutral">guided</span>
                  </div>
                  <p>{nextStepForData(cockpitData)}</p>
                </article>
                <article className="list-card">
                  <div className="list-card-header">
                    <h3>Review pressure</h3>
                    <span className="status-badge neutral">{openReviewTasks} open</span>
                  </div>
                  <p>Approved items move toward manual publishing, while rework loops stay visible to operators.</p>
                </article>
              </div>
            </section>
          ) : null}

          {route === "brands-assets" ? (
            <BrandsAssetsPanel
              assets={cockpitData.assets}
              brands={cockpitData.brands}
              busy={busyLabel !== null}
              canMutate={canMutate}
              onCreateBrand={(payload) =>
                runCockpitMutation("create brand", () => apiClient.createBrand(payload), "Brand created.")
              }
              onUploadAsset={(brandId, file) =>
                runCockpitMutation(
                  "upload asset",
                  () =>
                    apiClient.uploadAsset(file, {
                      brand_id: brandId,
                      filename: file.name,
                      content_type: file.type || "application/octet-stream",
                      byte_size: file.size,
                    }),
                  "Asset uploaded and finalized.",
                )
              }
            />
          ) : null}

          {route === "avatars" ? (
            <AvatarsPanel
              avatars={cockpitData.avatars}
              brands={cockpitData.brands}
              busy={busyLabel !== null}
              canMutate={canMutate}
              identityPacks={cockpitData.identityPacks}
              onCreateAvatar={(payload) =>
                runCockpitMutation("create avatar", () => apiClient.createAvatar(payload), "Avatar created.")
              }
              onCreateIdentityPack={(avatarId, payload) =>
                runCockpitMutation(
                  "create identity pack",
                  () => apiClient.createIdentityPack(avatarId, payload),
                  "Identity pack created.",
                )
              }
            />
          ) : null}

          {route === "content" ? (
            <ContentPanel
              avatars={cockpitData.avatars}
              brands={cockpitData.brands}
              busy={busyLabel !== null}
              canMutate={canMutate}
              contentItems={cockpitData.contentItems}
              onCreateContent={(payload) =>
                runCockpitMutation(
                  "create content",
                  () => apiClient.createContentItem(payload),
                  "Content item created.",
                )
              }
              onPlanContent={(contentItemId, plannedPublishAt) =>
                runCockpitMutation(
                  "plan content",
                  () => apiClient.planContentItem(contentItemId, { planned_publish_at: plannedPublishAt }),
                  "Content item planned.",
                )
              }
              onSubmitReview={(contentItemId) =>
                runCockpitMutation(
                  "submit review",
                  () => apiClient.submitContentForReview(contentItemId),
                  "Content item submitted for review.",
                )
              }
            />
          ) : null}

          {route === "review" ? (
            <ReviewPanel
              busy={busyLabel !== null}
              canReview={canReview}
              contentItems={cockpitData.contentItems}
              onApprove={(taskId, decisionNotes) =>
                runCockpitMutation(
                  "approve review",
                  () => apiClient.approveReviewTask(taskId, { decision_notes: decisionNotes }),
                  "Review task approved.",
                )
              }
              onRequestRework={(taskId, decisionNotes) =>
                runCockpitMutation(
                  "request rework",
                  () => apiClient.requestReviewRework(taskId, { decision_notes: decisionNotes }),
                  "Rework requested.",
                )
              }
              reviewTasks={cockpitData.reviewTasks}
            />
          ) : null}

          {route === "render" ? (
            <RenderPanel
              busy={busyLabel !== null}
              canMutate={canMutate}
              contentItems={cockpitData.contentItems}
              identityPacks={cockpitData.identityPacks}
              onCreateRenderJob={(payload) =>
                runCockpitMutation(
                  "create render job",
                  () => apiClient.createRenderJob(payload),
                  "Render job created.",
                )
              }
              onCancelRenderJob={(renderJobId) =>
                runCockpitMutation(
                  "cancel render job",
                  () => apiClient.cancelRenderJob(renderJobId),
                  "Render job cancelled.",
                )
              }
              onRetryRenderJob={(renderJobId) =>
                runCockpitMutation(
                  "retry render job",
                  () => apiClient.retryRenderJob(renderJobId),
                  "Render job retried.",
                )
              }
              onRequeueRenderJob={(renderJobId) =>
                runCockpitMutation(
                  "requeue render job",
                  () => apiClient.requeueRenderJob(renderJobId),
                  "Render job requeued.",
                )
              }
              onSelectRenderJob={setLiveRenderJobId}
              renderJobs={cockpitData.renderJobs}
              workflowPresets={cockpitData.workflowPresets}
            />
          ) : null}

          {route === "export" ? (
            <ExportPanel
              busy={busyLabel !== null}
              canMutate={canMutate}
              contentItems={cockpitData.contentItems}
              onCreatePackage={(renderJobId) =>
                runCockpitMutation(
                  "create publish package",
                  () => apiClient.createPublishPackage({ render_job_id: renderJobId }),
                  "Publish package queued.",
                )
              }
              onCancelPackage={(packageId) =>
                runCockpitMutation(
                  "cancel publish package",
                  () => apiClient.cancelPublishPackage(packageId),
                  "Publish package cancelled.",
                )
              }
              onGetDownload={async (packageId) => {
                const response = await apiClient.getPublishPackageDownload(packageId);
                return response.download.url;
              }}
              onRetryPackage={(packageId) =>
                runCockpitMutation(
                  "retry publish package",
                  () => apiClient.retryPublishPackage(packageId),
                  "Publish package retried.",
                )
              }
              onRequeuePackage={(packageId) =>
                runCockpitMutation(
                  "requeue publish package",
                  () => apiClient.requeuePublishPackage(packageId),
                  "Publish package requeued.",
                )
              }
              publishPackages={cockpitData.publishPackages}
              renderJobs={cockpitData.renderJobs}
            />
          ) : null}

          {route === "audit" ? (
            <AuditPanel auditLogs={cockpitData.auditLogs} canView={canViewAudit} />
          ) : null}
        </section>
      </div>
    </main>
  );
}

```

`apps/web/src/features/export/ExportPanel.tsx`:

```tsx
import { useState } from "react";

import type { ContentItem, PublishPackage, RenderJob } from "../../shared/api/types";
import { formatDateTime, formatStatus } from "../../shared/format";

interface ExportPanelProps {
  contentItems: ContentItem[];
  publishPackages: PublishPackage[];
  renderJobs: RenderJob[];
  canMutate: boolean;
  busy: boolean;
  onCreatePackage: (renderJobId: string) => Promise<void>;
  onCancelPackage: (packageId: string) => Promise<void>;
  onGetDownload: (packageId: string) => Promise<string>;
  onRetryPackage: (packageId: string) => Promise<void>;
  onRequeuePackage: (packageId: string) => Promise<void>;
}

const cancelablePackageStatuses = new Set(["queued", "running"]);
const retryablePackageStatuses = new Set(["failed", "cancelled"]);
const requeueablePackageStatuses = new Set(["queued"]);

export function ExportPanel({
  contentItems,
  publishPackages,
  renderJobs,
  canMutate,
  busy,
  onCreatePackage,
  onCancelPackage,
  onGetDownload,
  onRetryPackage,
  onRequeuePackage,
}: ExportPanelProps) {
  const [selectedRenderJobId, setSelectedRenderJobId] = useState("");
  const [downloadUrls, setDownloadUrls] = useState<Record<string, string>>({});
  const [downloadError, setDownloadError] = useState<string | null>(null);
  const packagedRenderJobIds = new Set(
    publishPackages.map((publishPackage) => publishPackage.render_job_id),
  );
  const eligibleRenderJobs = renderJobs.filter((renderJob) => {
    const contentItem = contentItems.find((item) => item.id === renderJob.content_item_id);
    return (
      renderJob.status === "succeeded" &&
      contentItem?.status === "approved" &&
      !packagedRenderJobIds.has(renderJob.id)
    );
  });
  const renderJobId = selectedRenderJobId || eligibleRenderJobs[0]?.id || "";

  return (
    <div className="panel-grid two-up">
      <section className="surface panel-stack">
        <div className="panel-header">
          <div>
            <p className="eyebrow">Export</p>
            <h2>Publish packages</h2>
          </div>
          <span className="count-pill">{publishPackages.length} packages</span>
        </div>

        {canMutate ? (
          <form
            className="stack-form"
            onSubmit={async (event) => {
              event.preventDefault();
              if (!renderJobId) {
                return;
              }
              await onCreatePackage(renderJobId);
            }}
          >
            <label>
              <span>Render job</span>
              <select
                value={renderJobId}
                onChange={(event) => setSelectedRenderJobId(event.target.value)}
              >
                <option value="">Select render job</option>
                {eligibleRenderJobs.map((renderJob) => (
                  <option key={renderJob.id} value={renderJob.id}>
                    {renderJob.workflow_preset_key} v{renderJob.workflow_preset_version} ·{" "}
                    {contentItems.find((item) => item.id === renderJob.content_item_id)?.title ??
                      "Content item"}
                  </option>
                ))}
              </select>
            </label>
            <button className="primary-button" disabled={busy || !renderJobId} type="submit">
              Create package
            </button>
          </form>
        ) : null}

        <div className="list-stack">
          {eligibleRenderJobs.length === 0 ? (
            <p className="empty-state">No succeeded approved renders waiting for package export.</p>
          ) : (
            eligibleRenderJobs.map((renderJob) => (
              <article className="list-card" key={renderJob.id}>
                <div className="list-card-header">
                  <div>
                    <h3>{renderJob.workflow_preset_key} v{renderJob.workflow_preset_version}</h3>
                    <p className="meta-copy">
                      {contentItems.find((item) => item.id === renderJob.content_item_id)?.title ??
                        renderJob.content_item_id}
                    </p>
                  </div>
                  <span className="status-badge">{formatStatus(renderJob.status)}</span>
                </div>
                <p className="meta-copy">Updated {formatDateTime(renderJob.updated_at)}</p>
              </article>
            ))
          )}
        </div>
      </section>

      <section className="surface panel-stack">
        <div className="panel-header">
          <div>
            <p className="eyebrow">Packages</p>
            <h2>Manual publish bundle</h2>
          </div>
        </div>

        {downloadError ? <p className="banner error">{downloadError}</p> : null}

        <div className="list-stack">
          {publishPackages.length === 0 ? (
            <p className="empty-state">No publish packages yet.</p>
          ) : (
            publishPackages.map((publishPackage) => {
              const contentItem = contentItems.find(
                (item) => item.id === publishPackage.content_item_id,
              );
              const downloadUrl = downloadUrls[publishPackage.id];
              return (
                <article className="list-card" key={publishPackage.id}>
                  <div className="list-card-header">
                    <div>
                      <h3>{contentItem?.title ?? publishPackage.content_item_id}</h3>
                      <p className="meta-copy">
                        {publishPackage.package_object_key ?? "Package object pending"}
                      </p>
                    </div>
                    <span className="status-badge">{formatStatus(publishPackage.status)}</span>
                  </div>
                  <p className="meta-copy">
                    {publishPackage.byte_size ?? 0} bytes · Updated{" "}
                    {formatDateTime(publishPackage.updated_at)}
                  </p>
                  {publishPackage.error_message ? (
                    <p className="banner error">{publishPackage.error_message}</p>
                  ) : null}
                  {publishPackage.status === "ready" ? (
                    <div className="inline-action-row">
                      <button
                        className="secondary-button"
                        disabled={busy}
                        type="button"
                        onClick={async () => {
                          setDownloadError(null);
                          try {
                            const url = await onGetDownload(publishPackage.id);
                            setDownloadUrls((current) => ({
                              ...current,
                              [publishPackage.id]: url,
                            }));
                          } catch (error) {
                            setDownloadError(error instanceof Error ? error.message : "Download failed");
                          }
                        }}
                      >
                        Get download
                      </button>
                      {downloadUrl ? (
                        <a className="secondary-button" href={downloadUrl}>
                          Open package
                        </a>
                      ) : null}
                    </div>
                  ) : null}
                  {canMutate ? (
                    <div className="inline-action-row">
                      {requeueablePackageStatuses.has(publishPackage.status) ? (
                        <button
                          className="secondary-button"
                          disabled={busy}
                          type="button"
                          onClick={() => onRequeuePackage(publishPackage.id)}
                        >
                          Requeue package
                        </button>
                      ) : null}
                      {cancelablePackageStatuses.has(publishPackage.status) ? (
                        <button
                          className="secondary-button"
                          disabled={busy}
                          type="button"
                          onClick={() => onCancelPackage(publishPackage.id)}
                        >
                          Cancel package
                        </button>
                      ) : null}
                      {retryablePackageStatuses.has(publishPackage.status) ? (
                        <button
                          className="secondary-button"
                          disabled={busy}
                          type="button"
                          onClick={() => onRetryPackage(publishPackage.id)}
                        >
                          Retry package
                        </button>
                      ) : null}
                    </div>
                  ) : null}
                </article>
              );
            })
          )}
        </div>
      </section>
    </div>
  );
}

```

`apps/web/src/features/render/RenderPanel.tsx`:

```tsx
import { useEffect, useState } from "react";

import { formatDateTime, formatStatus } from "../../shared/format";
import type {
  ContentItem,
  IdentityPack,
  RenderJob,
  RenderJobCreateRequest,
  WorkflowPreset,
} from "../../shared/api/types";

interface RenderPanelProps {
  contentItems: ContentItem[];
  identityPacks: IdentityPack[];
  renderJobs: RenderJob[];
  workflowPresets: WorkflowPreset[];
  canMutate: boolean;
  busy: boolean;
  onCreateRenderJob: (payload: RenderJobCreateRequest) => Promise<void>;
  onCancelRenderJob: (renderJobId: string) => Promise<void>;
  onRetryRenderJob: (renderJobId: string) => Promise<void>;
  onRequeueRenderJob: (renderJobId: string) => Promise<void>;
  onSelectRenderJob: (renderJobId: string | null) => void;
}

const renderableStatuses = new Set(["planned", "review", "approved", "rework"]);
const cancelableRenderStatuses = new Set(["queued", "running"]);
const retryableRenderStatuses = new Set(["failed", "cancelled"]);
const requeueableRenderStatuses = new Set(["queued"]);

export function RenderPanel({
  contentItems,
  identityPacks,
  renderJobs,
  workflowPresets,
  canMutate,
  busy,
  onCreateRenderJob,
  onCancelRenderJob,
  onRetryRenderJob,
  onRequeueRenderJob,
  onSelectRenderJob,
}: RenderPanelProps) {
  const [selectedJobId, setSelectedJobId] = useState(renderJobs[0]?.id ?? "");
  const [formState, setFormState] = useState({
    contentItemId: "",
    workflowPresetId: "",
    identityPackId: "",
    retryBudget: 3,
  });
  const renderableContentItems = contentItems.filter((item) => renderableStatuses.has(item.status));
  const contentItemId = formState.contentItemId || renderableContentItems[0]?.id || "";
  const workflowPresetId = formState.workflowPresetId || workflowPresets[0]?.id || "";
  const selectedJob = renderJobs.find((renderJob) => renderJob.id === selectedJobId) ?? renderJobs[0] ?? null;
  const selectedContentItem = selectedJob
    ? contentItems.find((item) => item.id === selectedJob.content_item_id)
    : null;

  useEffect(() => {
    onSelectRenderJob(selectedJob?.id ?? null);
  }, [onSelectRenderJob, selectedJob?.id]);

  return (
    <div className="panel-grid two-up">
      <section className="surface panel-stack">
        <div className="panel-header">
          <div>
            <p className="eyebrow">Render queue</p>
            <h2>Render queue</h2>
          </div>
          <span className="count-pill">{renderJobs.length} jobs</span>
        </div>

        {canMutate ? (
          <form
            className="stack-form"
            onSubmit={async (event) => {
              event.preventDefault();
              await onCreateRenderJob({
                content_item_id: contentItemId,
                workflow_preset_id: workflowPresetId,
                identity_pack_id: formState.identityPackId || null,
                retry_budget: formState.retryBudget,
              });
            }}
          >
            <label>
              <span>Content item</span>
              <select
                value={contentItemId}
                onChange={(event) =>
                  setFormState((current) => ({ ...current, contentItemId: event.target.value }))
                }
              >
                <option value="">Select content item</option>
                {renderableContentItems.map((contentItem) => (
                  <option key={contentItem.id} value={contentItem.id}>
                    {contentItem.title} · {formatStatus(contentItem.status)}
                  </option>
                ))}
              </select>
            </label>
            <label>
              <span>Workflow preset</span>
              <select
                value={workflowPresetId}
                onChange={(event) =>
                  setFormState((current) => ({ ...current, workflowPresetId: event.target.value }))
                }
              >
                <option value="">Select workflow preset</option>
                {workflowPresets.map((workflowPreset) => (
                  <option key={workflowPreset.id} value={workflowPreset.id}>
                    {workflowPreset.key} v{workflowPreset.version}
                  </option>
                ))}
              </select>
            </label>
            <label>
              <span>Identity pack</span>
              <select
                value={formState.identityPackId}
                onChange={(event) =>
                  setFormState((current) => ({ ...current, identityPackId: event.target.value }))
                }
              >
                <option value="">No identity pack</option>
                {identityPacks.map((identityPack) => (
                  <option key={identityPack.id} value={identityPack.id}>
                    {identityPack.name}
                  </option>
                ))}
              </select>
            </label>
            <label>
              <span>Retry budget</span>
              <input
                min={1}
                max={5}
                type="number"
                value={formState.retryBudget}
                onChange={(event) =>
                  setFormState((current) => ({
                    ...current,
                    retryBudget: Number(event.target.value),
                  }))
                }
              />
            </label>
            <button
              className="primary-button"
              disabled={busy || !contentItemId || !workflowPresetId}
              type="submit"
            >
              Create render job
            </button>
          </form>
        ) : null}

        <div className="list-stack">
          {renderJobs.length === 0 ? (
            <p className="empty-state">No render jobs yet.</p>
          ) : (
            renderJobs.map((renderJob) => (
              <article className="list-card" key={renderJob.id}>
                <div className="list-card-header">
                  <div>
                    <h3>{renderJob.workflow_preset_key} v{renderJob.workflow_preset_version}</h3>
                    <p className="meta-copy">
                      {contentItems.find((item) => item.id === renderJob.content_item_id)?.title ?? "Content item"}
                    </p>
                  </div>
                  <span className="status-badge">{formatStatus(renderJob.status)}</span>
                </div>
                <p className="meta-copy">
                  {renderJob.attempts.length} attempts · Updated {formatDateTime(renderJob.updated_at)}
                </p>
                <button
                  className="secondary-button"
                  type="button"
                  onClick={() => setSelectedJobId(renderJob.id)}
                >
                  View job
                </button>
                {canMutate ? (
                  <div className="inline-action-row">
                    {requeueableRenderStatuses.has(renderJob.status) ? (
                      <button
                        className="secondary-button"
                        disabled={busy}
                        type="button"
                        onClick={() => onRequeueRenderJob(renderJob.id)}
                      >
                        Requeue job
                      </button>
                    ) : null}
                    {cancelableRenderStatuses.has(renderJob.status) ? (
                      <button
                        className="secondary-button"
                        disabled={busy}
                        type="button"
                        onClick={() => onCancelRenderJob(renderJob.id)}
                      >
                        Cancel job
                      </button>
                    ) : null}
                    {retryableRenderStatuses.has(renderJob.status) ? (
                      <button
                        className="secondary-button"
                        disabled={busy}
                        type="button"
                        onClick={() => onRetryRenderJob(renderJob.id)}
                      >
                        Retry job
                      </button>
                    ) : null}
                  </div>
                ) : null}
              </article>
            ))
          )}
        </div>
      </section>

      <section className="surface panel-stack">
        <div className="panel-header">
          <div>
            <p className="eyebrow">Job detail</p>
            <h2>{selectedJob ? selectedJob.workflow_preset_key : "No job selected"}</h2>
          </div>
          {selectedJob ? <span className="status-badge">{formatStatus(selectedJob.status)}</span> : null}
        </div>

        {selectedJob ? (
          <>
            <dl className="meta-list">
              <div>
                <dt>Content</dt>
                <dd>{selectedContentItem?.title ?? selectedJob.content_item_id}</dd>
              </div>
              <div>
                <dt>Provider</dt>
                <dd>{selectedJob.workflow_provider}</dd>
              </div>
              <div>
                <dt>Created</dt>
                <dd>{formatDateTime(selectedJob.created_at)}</dd>
              </div>
            </dl>

            <div className="list-stack">
              {selectedJob.attempts.map((attempt) => (
                <article className="list-card" key={attempt.id}>
                  <div className="list-card-header">
                    <h3>Attempt {attempt.attempt_number}</h3>
                    <span className="status-badge">{formatStatus(attempt.status)}</span>
                  </div>
                  <p className="meta-copy">
                    Provider job {attempt.provider_job_id ?? "not assigned"} · Started{" "}
                    {formatDateTime(attempt.started_at)} · Finished {formatDateTime(attempt.finished_at)}
                  </p>
                  {attempt.error_message ? <p className="banner error">{attempt.error_message}</p> : null}
                  <pre className="json-preview">
                    {JSON.stringify(attempt.response_payload, null, 2)}
                  </pre>
                </article>
              ))}
            </div>
          </>
        ) : (
          <p className="empty-state">Select a render job from the queue.</p>
        )}
      </section>
    </div>
  );
}

```

`apps/web/src/shared/api/client.ts`:

```ts
import { webEnv } from "../../config/env";
import { resolveUploadUrl } from "./upload";
import type {
  AssetFinalizeRequest,
  Asset,
  AssetUploadInitiateRequest,
  AssetUploadInitiateResponse,
  AuditLog,
  AuthSession,
  Avatar,
  AvatarCreateRequest,
  BootstrapOwnerRequest,
  Brand,
  BrandCreateRequest,
  ContentItem,
  ContentItemCreateRequest,
  ContentPlanRequest,
  IdentityPack,
  IdentityPackCreateRequest,
  InviteAcceptRequest,
  LoginRequest,
  Invite,
  InviteCreateRequest,
  RenderJob,
  RenderJobCreateRequest,
  PublishPackage,
  PublishPackageCreateRequest,
  PublishPackageDownloadResponse,
  ReviewDecisionRequest,
  ReviewTask,
  User,
  WorkflowPreset,
} from "./types";

export class ApiError extends Error {
  status: number;

  detail: string;

  constructor(status: number, detail: string) {
    super(detail);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

function isAbsoluteUrl(value: string): boolean {
  return /^https?:\/\//i.test(value);
}

function resolveApiUrl(path: string): string {
  if (isAbsoluteUrl(path)) {
    return path;
  }

  const normalizedPath = path.startsWith("/") ? path : `/${path}`;

  if (isAbsoluteUrl(webEnv.VITE_API_BASE_URL)) {
    return new URL(normalizedPath, `${webEnv.VITE_API_BASE_URL.replace(/\/+$/, "")}/`).toString();
  }

  if (webEnv.VITE_API_BASE_URL === "/") {
    return normalizedPath;
  }

  return `${webEnv.VITE_API_BASE_URL.replace(/\/+$/, "")}${normalizedPath}`;
}

async function readResponseBody(response: Response): Promise<unknown> {
  const contentType = response.headers.get("content-type");

  if (contentType?.includes("application/json")) {
    return response.json();
  }

  return response.text();
}

function errorDetailFromBody(body: unknown): string {
  if (typeof body === "string" && body.trim().length > 0) {
    return body;
  }

  if (
    body &&
    typeof body === "object" &&
    "detail" in body &&
    typeof body.detail === "string" &&
    body.detail.trim().length > 0
  ) {
    return body.detail;
  }

  if (body && typeof body === "object" && "detail" in body && Array.isArray(body.detail)) {
    return body.detail
      .map((item) => {
        if (item && typeof item === "object" && "msg" in item && typeof item.msg === "string") {
          return item.msg;
        }

        return "Validation error";
      })
      .join("; ");
  }

  return "Request failed";
}

async function requestJson<TResponse>(path: string, init?: RequestInit): Promise<TResponse> {
  const response = await fetch(resolveApiUrl(path), {
    credentials: "include",
    ...init,
    headers: {
      Accept: "application/json",
      ...(init?.body ? { "Content-Type": "application/json" } : {}),
      ...(init?.headers ?? {}),
    },
  });
  const body = await readResponseBody(response);

  if (!response.ok) {
    throw new ApiError(response.status, errorDetailFromBody(body));
  }

  return body as TResponse;
}

function postJson<TRequest, TResponse>(path: string, body: TRequest): Promise<TResponse> {
  return requestJson<TResponse>(path, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

function getList<TItem>(path: string): Promise<{ items: TItem[] }> {
  return requestJson<{ items: TItem[] }>(path);
}

export function describeApiBase(): string {
  return webEnv.VITE_API_BASE_URL === "/" ? "Same-origin proxy (/api)" : webEnv.VITE_API_BASE_URL;
}

export function isApiError(error: unknown): error is ApiError {
  return error instanceof ApiError;
}

export const apiClient = {
  getSession() {
    return requestJson<AuthSession>("/api/auth/session");
  },
  login(payload: LoginRequest) {
    return postJson<LoginRequest, AuthSession>("/api/auth/login", payload);
  },
  bootstrapOwner(payload: BootstrapOwnerRequest) {
    return postJson<BootstrapOwnerRequest, AuthSession>("/api/auth/bootstrap-owner", payload);
  },
  acceptInvite(payload: InviteAcceptRequest) {
    return postJson<InviteAcceptRequest, AuthSession>("/api/auth/invites/accept", payload);
  },
  logout() {
    return requestJson<{ status: string }>("/api/auth/logout", { method: "POST" });
  },
  createInvite(payload: InviteCreateRequest) {
    return postJson<InviteCreateRequest, Invite>("/api/auth/invites", payload);
  },
  listUsers() {
    return getList<User>("/api/users");
  },
  listBrands() {
    return getList<Brand>("/api/brands");
  },
  createBrand(payload: BrandCreateRequest) {
    return postJson<BrandCreateRequest, Brand>("/api/brands", payload);
  },
  listAvatars() {
    return getList<Avatar>("/api/avatars");
  },
  createAvatar(payload: AvatarCreateRequest) {
    return postJson<AvatarCreateRequest, Avatar>("/api/avatars", payload);
  },
  listIdentityPacks(avatarId: string) {
    return getList<IdentityPack>(`/api/avatars/${avatarId}/identity-packs`);
  },
  createIdentityPack(avatarId: string, payload: IdentityPackCreateRequest) {
    return postJson<IdentityPackCreateRequest, IdentityPack>(
      `/api/avatars/${avatarId}/identity-packs`,
      payload,
    );
  },
  listAssets() {
    return getList<Asset>("/api/assets");
  },
  initiateUpload(payload: AssetUploadInitiateRequest) {
    return postJson<AssetUploadInitiateRequest, AssetUploadInitiateResponse>("/api/assets/uploads", payload);
  },
  finalizeUpload(assetId: string, payload: AssetFinalizeRequest) {
    return postJson<AssetFinalizeRequest, Asset>(`/api/assets/${assetId}/finalize`, payload);
  },
  listContentItems() {
    return getList<ContentItem>("/api/content-items");
  },
  createContentItem(payload: ContentItemCreateRequest) {
    return postJson<ContentItemCreateRequest, ContentItem>("/api/content-items", payload);
  },
  planContentItem(contentItemId: string, payload: ContentPlanRequest) {
    return postJson<ContentPlanRequest, ContentItem>(`/api/content-items/${contentItemId}/plan`, payload);
  },
  submitContentForReview(contentItemId: string) {
    return requestJson<ReviewTask>(`/api/content-items/${contentItemId}/submit-review`, { method: "POST" });
  },
  submitContentItemForReview(contentItemId: string) {
    return requestJson<ReviewTask>(`/api/content-items/${contentItemId}/submit-review`, { method: "POST" });
  },
  listReviewTasks() {
    return getList<ReviewTask>("/api/review/tasks");
  },
  listWorkflowPresets() {
    return getList<WorkflowPreset>("/api/workflow-presets");
  },
  listRenderJobs() {
    return getList<RenderJob>("/api/render-jobs");
  },
  getRenderJob(renderJobId: string) {
    return requestJson<RenderJob>(`/api/render-jobs/${renderJobId}`);
  },
  createRenderJob(payload: RenderJobCreateRequest) {
    return postJson<RenderJobCreateRequest, RenderJob>("/api/render-jobs", payload);
  },
  cancelRenderJob(renderJobId: string) {
    return requestJson<RenderJob>(`/api/render-jobs/${renderJobId}/cancel`, { method: "POST" });
  },
  retryRenderJob(renderJobId: string) {
    return requestJson<RenderJob>(`/api/render-jobs/${renderJobId}/retry`, { method: "POST" });
  },
  requeueRenderJob(renderJobId: string) {
    return requestJson<RenderJob>(`/api/render-jobs/${renderJobId}/requeue`, { method: "POST" });
  },
  renderJobEventsUrl(renderJobId: string) {
    return resolveApiUrl(`/api/render-jobs/${renderJobId}/events`);
  },
  listPublishPackages() {
    return getList<PublishPackage>("/api/publish-packages");
  },
  createPublishPackage(payload: PublishPackageCreateRequest) {
    return postJson<PublishPackageCreateRequest, PublishPackage>("/api/publish-packages", payload);
  },
  cancelPublishPackage(packageId: string) {
    return requestJson<PublishPackage>(`/api/publish-packages/${packageId}/cancel`, { method: "POST" });
  },
  retryPublishPackage(packageId: string) {
    return requestJson<PublishPackage>(`/api/publish-packages/${packageId}/retry`, { method: "POST" });
  },
  requeuePublishPackage(packageId: string) {
    return requestJson<PublishPackage>(`/api/publish-packages/${packageId}/requeue`, { method: "POST" });
  },
  getPublishPackageDownload(packageId: string) {
    return requestJson<PublishPackageDownloadResponse>(`/api/publish-packages/${packageId}/download`);
  },
  approveReviewTask(taskId: string, payload: ReviewDecisionRequest) {
    return postJson<ReviewDecisionRequest, ReviewTask>(`/api/review/tasks/${taskId}/approve`, payload);
  },
  requestReviewRework(taskId: string, payload: ReviewDecisionRequest) {
    return postJson<ReviewDecisionRequest, ReviewTask>(
      `/api/review/tasks/${taskId}/request-rework`,
      payload,
    );
  },
  requestRework(taskId: string, payload: ReviewDecisionRequest) {
    return postJson<ReviewDecisionRequest, ReviewTask>(
      `/api/review/tasks/${taskId}/request-rework`,
      payload,
    );
  },
  listAuditLogs(limit = 100) {
    return getList<AuditLog>(`/api/audit/logs?limit=${limit}`);
  },
  async uploadAsset(file: File, payload: AssetUploadInitiateRequest): Promise<Asset> {
    const initiated = await postJson<AssetUploadInitiateRequest, AssetUploadInitiateResponse>(
      "/api/assets/uploads",
      payload,
    );

    const uploadResponse = await fetch(resolveUploadUrl(initiated.upload.url), {
      method: initiated.upload.method,
      headers: initiated.upload.headers,
      body: file,
    });

    if (!uploadResponse.ok) {
      throw new ApiError(uploadResponse.status, "Asset upload could not be completed");
    }

    return postJson<AssetFinalizeRequest, Asset>(`/api/assets/${initiated.asset.id}/finalize`, {
      byte_size: file.size || initiated.asset.byte_size || 1,
      checksum_sha256: null,
    });
  },
};

```

`apps/worker/src/content_factory_worker/orchestration.py`:

```py
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from content_factory_api.modules.domain import JobAttemptStatus, RenderJobStatus
from content_factory_api.modules.models import JobAttempt, RenderJob, WorkflowPreset
from content_factory_api.modules.security import utcnow

TERMINAL_RENDER_JOB_STATUSES = {
    RenderJobStatus.SUCCEEDED.value,
    RenderJobStatus.FAILED.value,
    RenderJobStatus.CANCELLED.value,
}

ProcessingStatus = Literal[
    "succeeded",
    "failed",
    "retry_queued",
    "cancelled",
    "skipped_terminal",
    "skipped_no_attempt",
]


class RenderExecutionError(RuntimeError):
    """Raised by a render executor when a provider attempt fails."""


class RenderJobNotFoundError(LookupError):
    """Raised when a queued worker message references a missing render job."""


class RenderJobStateError(RuntimeError):
    """Raised when a render job cannot be processed because its state is invalid."""


@dataclass(frozen=True)
class RenderExecutionResult:
    provider_job_id: str | None = None
    response_payload: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class RenderJobProcessingOutcome:
    render_job_id: str
    attempt_id: str | None
    status: ProcessingStatus


class RenderExecutor(Protocol):
    def execute(
        self,
        *,
        render_job: RenderJob,
        workflow_preset: WorkflowPreset,
        attempt: JobAttempt,
    ) -> RenderExecutionResult:
        """Run a single render attempt against the configured provider."""


def process_render_job(
    render_job_id: str,
    *,
    db_session: Session,
    executor: RenderExecutor,
) -> RenderJobProcessingOutcome:
    render_job = db_session.get(RenderJob, render_job_id)
    if render_job is None:
        raise RenderJobNotFoundError(f"Render job '{render_job_id}' not found")

    if render_job.status in TERMINAL_RENDER_JOB_STATUSES:
        return RenderJobProcessingOutcome(
            render_job_id=render_job.id,
            attempt_id=None,
            status="skipped_terminal",
        )

    workflow_preset = db_session.get(WorkflowPreset, render_job.workflow_preset_id)
    if workflow_preset is None:
        raise RenderJobStateError(
            f"Workflow preset '{render_job.workflow_preset_id}' not found",
        )

    attempts = _attempts_for_job(db_session, render_job.id)
    attempt = _next_queued_attempt(attempts)
    if attempt is None:
        return RenderJobProcessingOutcome(
            render_job_id=render_job.id,
            attempt_id=None,
            status="skipped_no_attempt",
        )

    _mark_attempt_running(render_job, attempt)
    db_session.commit()

    try:
        result = executor.execute(
            render_job=render_job,
            workflow_preset=workflow_preset,
            attempt=attempt,
        )
    except RenderExecutionError as exc:
        if _job_or_attempt_cancelled(db_session, render_job, attempt):
            return _mark_operator_cancelled(db_session, render_job=render_job, attempt=attempt)
        return _fail_attempt(
            db_session,
            render_job=render_job,
            attempt=attempt,
            attempts=attempts,
            error_message=str(exc),
        )
    except Exception as exc:
        if _job_or_attempt_cancelled(db_session, render_job, attempt):
            return _mark_operator_cancelled(db_session, render_job=render_job, attempt=attempt)
        return _fail_attempt(
            db_session,
            render_job=render_job,
            attempt=attempt,
            attempts=attempts,
            error_message=f"{exc.__class__.__name__}: {exc}",
        )

    if _job_or_attempt_cancelled(db_session, render_job, attempt):
        return _mark_operator_cancelled(db_session, render_job=render_job, attempt=attempt)

    attempt.status = JobAttemptStatus.SUCCEEDED.value
    attempt.provider_job_id = result.provider_job_id
    attempt.response_payload = result.response_payload
    attempt.finished_at = utcnow()
    render_job.status = RenderJobStatus.SUCCEEDED.value
    db_session.commit()
    return RenderJobProcessingOutcome(
        render_job_id=render_job.id,
        attempt_id=attempt.id,
        status="succeeded",
    )


def _attempts_for_job(db_session: Session, render_job_id: str) -> list[JobAttempt]:
    return list(
        db_session.scalars(
            select(JobAttempt)
            .where(JobAttempt.render_job_id == render_job_id)
            .order_by(JobAttempt.attempt_number.asc())
        )
    )


def _next_queued_attempt(attempts: list[JobAttempt]) -> JobAttempt | None:
    for attempt in attempts:
        if attempt.status == JobAttemptStatus.QUEUED.value:
            return attempt
    return None


def _mark_attempt_running(render_job: RenderJob, attempt: JobAttempt) -> None:
    now = utcnow()
    render_job.status = RenderJobStatus.RUNNING.value
    attempt.status = JobAttemptStatus.RUNNING.value
    attempt.started_at = now


def _fail_attempt(
    db_session: Session,
    *,
    render_job: RenderJob,
    attempt: JobAttempt,
    attempts: list[JobAttempt],
    error_message: str,
) -> RenderJobProcessingOutcome:
    attempt.status = JobAttemptStatus.FAILED.value
    attempt.error_message = error_message
    attempt.finished_at = utcnow()

    if attempt.attempt_number < render_job.retry_budget:
        next_attempt_number = (
            max(existing_attempt.attempt_number for existing_attempt in attempts) + 1
        )
        next_attempt = JobAttempt(
            render_job_id=render_job.id,
            attempt_number=next_attempt_number,
            status=JobAttemptStatus.QUEUED.value,
            request_payload=attempt.request_payload,
        )
        db_session.add(next_attempt)
        render_job.status = RenderJobStatus.QUEUED.value
        db_session.commit()
        return RenderJobProcessingOutcome(
            render_job_id=render_job.id,
            attempt_id=next_attempt.id,
            status="retry_queued",
        )

    render_job.status = RenderJobStatus.FAILED.value
    db_session.commit()
    return RenderJobProcessingOutcome(
        render_job_id=render_job.id,
        attempt_id=attempt.id,
        status="failed",
    )


def _job_or_attempt_cancelled(
    db_session: Session,
    render_job: RenderJob,
    attempt: JobAttempt,
) -> bool:
    db_session.refresh(render_job)
    db_session.refresh(attempt)
    return (
        render_job.status == RenderJobStatus.CANCELLED.value
        or attempt.status == JobAttemptStatus.CANCELLED.value
    )


def _mark_operator_cancelled(
    db_session: Session,
    *,
    render_job: RenderJob,
    attempt: JobAttempt,
) -> RenderJobProcessingOutcome:
    now = utcnow()
    render_job.status = RenderJobStatus.CANCELLED.value
    attempt.status = JobAttemptStatus.CANCELLED.value
    attempt.finished_at = attempt.finished_at or now
    attempt.error_message = attempt.error_message or "Cancelled by operator"
    db_session.commit()
    return RenderJobProcessingOutcome(
        render_job_id=render_job.id,
        attempt_id=attempt.id,
        status="cancelled",
    )

```

`apps/worker/src/content_factory_worker/packaging.py`:

```py
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
    PackageStorage,
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
    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}

    def upload_package(self, *, object_key: str, data: bytes, content_type: str) -> None:
        assert content_type == "application/zip"
        self.objects[object_key] = data


def test_process_publish_package_builds_manifest_zip(db_session: Session) -> None:
    publish_package = _seed_publish_package(
        db_session,
        response_payload={
            "outputs": {
                "video_file": "s3://content-factory-assets/renders/video.mp4",
                "cover_file": "s3://content-factory-assets/renders/cover.jpg",
            },
            "hashtags": ["#inflave"],
        },
    )
    storage = MemoryPackageStorage()

    outcome = process_publish_package(
        publish_package.id,
        db_session=db_session,
        packager=ZipPublishPackager(storage=storage),
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
    ]
    manifest = json.loads(archive.read("manifest.json").decode("utf-8"))
    assert manifest["render_job_id"] == publish_package.render_job_id
    assert manifest["manual_publish"]["hashtags"] == ["#inflave"]


def test_process_publish_package_marks_missing_outputs_failed(db_session: Session) -> None:
    publish_package = _seed_publish_package(db_session, response_payload={"outputs": {}})

    outcome = process_publish_package(
        publish_package.id,
        db_session=db_session,
        packager=ZipPublishPackager(storage=MemoryPackageStorage()),
    )

    db_session.refresh(publish_package)
    assert outcome.status == "failed"
    assert publish_package.status == PublishPackageStatus.FAILED.value
    assert publish_package.error_message is not None
    assert "video_file" in publish_package.error_message


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
        packager=ZipPublishPackager(storage=storage),
    )

    db_session.refresh(publish_package)
    assert outcome.status == "skipped_cancelled"
    assert publish_package.status == PublishPackageStatus.CANCELLED.value
    assert storage.objects == {}


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

`apps/worker/tests/test_render_orchestration.py`:

```py
from collections.abc import Generator
from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from content_factory_api.config import get_settings
from content_factory_api.database import get_sessionmaker, init_database, reset_database_caches
from content_factory_api.modules.domain import (
    ContentChannel,
    ContentStatus,
    JobAttemptStatus,
    PackagingProvider,
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
    RenderJob,
    User,
    WorkflowPreset,
)
from content_factory_worker.orchestration import (
    RenderExecutionError,
    RenderExecutionResult,
    process_render_job,
)


@pytest.fixture
def db_session(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Generator[Session, None, None]:
    db_path = tmp_path / "worker-orchestration.db"
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


class SuccessfulExecutor:
    def __init__(self) -> None:
        self.calls = 0

    def execute(
        self,
        *,
        render_job: RenderJob,
        workflow_preset: WorkflowPreset,
        attempt: JobAttempt,
    ) -> RenderExecutionResult:
        self.calls += 1
        return RenderExecutionResult(
            provider_job_id=f"comfyui-{attempt.id}",
            response_payload={
                "workflow_key": workflow_preset.key,
                "outputs": {"video_file": f"renders/{render_job.id}/video.mp4"},
            },
        )


class FailingExecutor:
    def __init__(self) -> None:
        self.calls = 0

    def execute(
        self,
        *,
        render_job: RenderJob,
        workflow_preset: WorkflowPreset,
        attempt: JobAttempt,
    ) -> RenderExecutionResult:
        self.calls += 1
        raise RenderExecutionError("ComfyUI request timed out")


class CancellingExecutor:
    def __init__(self) -> None:
        self.calls = 0

    def execute(
        self,
        *,
        render_job: RenderJob,
        workflow_preset: WorkflowPreset,
        attempt: JobAttempt,
    ) -> RenderExecutionResult:
        self.calls += 1
        cancel_session = get_sessionmaker()()
        try:
            cancelled_job = cancel_session.get(RenderJob, render_job.id)
            cancelled_attempt = cancel_session.get(JobAttempt, attempt.id)
            assert cancelled_job is not None
            assert cancelled_attempt is not None
            cancelled_job.status = RenderJobStatus.CANCELLED.value
            cancelled_attempt.status = JobAttemptStatus.CANCELLED.value
            cancel_session.commit()
        finally:
            cancel_session.close()
        return RenderExecutionResult(
            provider_job_id="comfyui-cancelled",
            response_payload={"outputs": {"video_file": "renders/cancelled.mp4"}},
        )


def test_process_render_job_marks_attempt_succeeded(db_session: Session) -> None:
    render_job, attempt = _seed_render_job(db_session, retry_budget=2)
    executor = SuccessfulExecutor()

    outcome = process_render_job(render_job.id, db_session=db_session, executor=executor)

    db_session.refresh(render_job)
    db_session.refresh(attempt)
    assert outcome.status == "succeeded"
    assert executor.calls == 1
    assert render_job.status == RenderJobStatus.SUCCEEDED.value
    assert attempt.status == JobAttemptStatus.SUCCEEDED.value
    assert attempt.provider_job_id == f"comfyui-{attempt.id}"
    assert attempt.response_payload["outputs"]["video_file"] == f"renders/{render_job.id}/video.mp4"
    assert attempt.started_at is not None
    assert attempt.finished_at is not None


def test_failed_attempt_queues_retry_until_budget_is_exhausted(db_session: Session) -> None:
    render_job, first_attempt = _seed_render_job(db_session, retry_budget=2)
    executor = FailingExecutor()

    outcome = process_render_job(render_job.id, db_session=db_session, executor=executor)

    attempts = _attempts_for_job(db_session, render_job.id)
    db_session.refresh(render_job)
    db_session.refresh(first_attempt)
    assert outcome.status == "retry_queued"
    assert executor.calls == 1
    assert render_job.status == RenderJobStatus.QUEUED.value
    assert first_attempt.status == JobAttemptStatus.FAILED.value
    assert first_attempt.error_message == "ComfyUI request timed out"
    assert len(attempts) == 2
    assert attempts[1].attempt_number == 2
    assert attempts[1].status == JobAttemptStatus.QUEUED.value
    assert attempts[1].request_payload == first_attempt.request_payload


def test_failed_attempt_marks_job_failed_when_retry_budget_is_exhausted(
    db_session: Session,
) -> None:
    render_job, first_attempt = _seed_render_job(db_session, retry_budget=1)
    executor = FailingExecutor()

    outcome = process_render_job(render_job.id, db_session=db_session, executor=executor)

    attempts = _attempts_for_job(db_session, render_job.id)
    db_session.refresh(render_job)
    db_session.refresh(first_attempt)
    assert outcome.status == "failed"
    assert render_job.status == RenderJobStatus.FAILED.value
    assert first_attempt.status == JobAttemptStatus.FAILED.value
    assert len(attempts) == 1


def test_terminal_render_job_is_not_processed_again(db_session: Session) -> None:
    render_job, attempt = _seed_render_job(db_session, retry_budget=2)
    render_job.status = RenderJobStatus.SUCCEEDED.value
    attempt.status = JobAttemptStatus.SUCCEEDED.value
    db_session.commit()
    executor = FailingExecutor()

    outcome = process_render_job(render_job.id, db_session=db_session, executor=executor)

    assert outcome.status == "skipped_terminal"
    assert executor.calls == 0


def test_operator_cancelled_render_job_is_not_overwritten_after_execution(
    db_session: Session,
) -> None:
    render_job, attempt = _seed_render_job(db_session, retry_budget=2)
    executor = CancellingExecutor()

    outcome = process_render_job(render_job.id, db_session=db_session, executor=executor)

    db_session.refresh(render_job)
    db_session.refresh(attempt)
    assert outcome.status == "cancelled"
    assert executor.calls == 1
    assert render_job.status == RenderJobStatus.CANCELLED.value
    assert attempt.status == JobAttemptStatus.CANCELLED.value
    assert attempt.provider_job_id is None


def _seed_render_job(db_session: Session, *, retry_budget: int) -> tuple[RenderJob, JobAttempt]:
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
        status=ContentStatus.PLANNED.value,
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
            "video_file": {"artifact_type": "video", "output_path": "outputs.primary.video"},
        },
        created_by_user_id=user.id,
    )
    db_session.add(workflow_preset)
    db_session.flush()

    input_snapshot = {"script_text": content_item.script}
    render_job = RenderJob(
        content_item_id=content_item.id,
        workflow_preset_id=workflow_preset.id,
        workflow_preset_key=workflow_preset.key,
        workflow_preset_version=workflow_preset.version,
        workflow_provider=workflow_preset.workflow_provider,
        voice_provider=workflow_preset.voice_provider,
        packaging_provider=workflow_preset.packaging_provider,
        input_snapshot=input_snapshot,
        status=RenderJobStatus.QUEUED.value,
        retry_budget=retry_budget,
        created_by_user_id=user.id,
    )
    db_session.add(render_job)
    db_session.flush()

    attempt = JobAttempt(
        render_job_id=render_job.id,
        attempt_number=1,
        status=JobAttemptStatus.QUEUED.value,
        request_payload={"inputs": input_snapshot},
    )
    db_session.add(attempt)
    db_session.commit()
    return render_job, attempt


def _attempts_for_job(db_session: Session, render_job_id: str) -> list[JobAttempt]:
    return sorted(
        db_session.query(JobAttempt)
        .filter(JobAttempt.render_job_id == render_job_id)
        .all(),
        key=lambda attempt: attempt.attempt_number,
    )

```

`packages/contracts/openapi/content-factory.openapi.json`:

```json
{
  "openapi": "3.1.0",
  "info": {
    "title": "Content Factory API",
    "version": "0.1.0"
  },
  "paths": {
    "/": {
      "get": {
        "summary": "Root",
        "operationId": "root__get",
        "responses": {
          "200": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {
                  "additionalProperties": {
                    "type": "string"
                  },
                  "type": "object",
                  "title": "Response Root  Get"
                }
              }
            }
          }
        }
      }
    },
    "/api/meta": {
      "get": {
        "summary": "Meta",
        "operationId": "meta_api_meta_get",
        "responses": {
          "200": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {
                  "additionalProperties": {
                    "type": "string"
                  },
                  "type": "object",
                  "title": "Response Meta Api Meta Get"
                }
              }
            }
          }
        }
      }
    },
    "/health/live": {
      "get": {
        "tags": [
          "health"
        ],
        "summary": "Live",
        "operationId": "live_health_live_get",
        "responses": {
          "200": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {
                  "additionalProperties": {
                    "type": "string"
                  },
                  "type": "object",
                  "title": "Response Live Health Live Get"
                }
              }
            }
          }
        }
      }
    },
    "/health/ready": {
      "get": {
        "tags": [
          "health"
        ],
        "summary": "Ready",
        "operationId": "ready_health_ready_get",
        "responses": {
          "200": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {
                  "additionalProperties": true,
                  "type": "object",
                  "title": "Response Ready Health Ready Get"
                }
              }
            }
          }
        }
      }
    },
    "/api/auth/bootstrap-owner": {
      "post": {
        "tags": [
          "auth"
        ],
        "summary": "Bootstrap Owner",
        "operationId": "bootstrap_owner_api_auth_bootstrap_owner_post",
        "requestBody": {
          "content": {
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/BootstrapOwnerRequest"
              }
            }
          },
          "required": true
        },
        "responses": {
          "201": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/AuthSessionRead"
                }
              }
            }
          },
          "422": {
            "description": "Validation Error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            }
          }
        }
      }
    },
    "/api/auth/invites": {
      "post": {
        "tags": [
          "auth"
        ],
        "summary": "Create Invite",
        "operationId": "create_invite_api_auth_invites_post",
        "parameters": [
          {
            "name": "cf_session",
            "in": "cookie",
            "required": false,
            "schema": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "title": "Cf Session"
            }
          }
        ],
        "requestBody": {
          "required": true,
          "content": {
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/InviteCreateRequest"
              }
            }
          }
        },
        "responses": {
          "201": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/InviteCreateResponse"
                }
              }
            }
          },
          "422": {
            "description": "Validation Error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            }
          }
        }
      }
    },
    "/api/auth/invites/accept": {
      "post": {
        "tags": [
          "auth"
        ],
        "summary": "Accept Invite",
        "operationId": "accept_invite_api_auth_invites_accept_post",
        "requestBody": {
          "content": {
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/InviteAcceptRequest"
              }
            }
          },
          "required": true
        },
        "responses": {
          "201": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/AuthSessionRead"
                }
              }
            }
          },
          "422": {
            "description": "Validation Error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            }
          }
        }
      }
    },
    "/api/auth/login": {
      "post": {
        "tags": [
          "auth"
        ],
        "summary": "Login",
        "operationId": "login_api_auth_login_post",
        "requestBody": {
          "content": {
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/LoginRequest"
              }
            }
          },
          "required": true
        },
        "responses": {
          "200": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/AuthSessionRead"
                }
              }
            }
          },
          "422": {
            "description": "Validation Error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            }
          }
        }
      }
    },
    "/api/auth/logout": {
      "post": {
        "tags": [
          "auth"
        ],
        "summary": "Logout",
        "operationId": "logout_api_auth_logout_post",
        "parameters": [
          {
            "name": "cf_session",
            "in": "cookie",
            "required": false,
            "schema": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "title": "Cf Session"
            }
          }
        ],
        "responses": {
          "200": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/StatusResponse"
                }
              }
            }
          },
          "422": {
            "description": "Validation Error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            }
          }
        }
      }
    },
    "/api/auth/session": {
      "get": {
        "tags": [
          "auth"
        ],
        "summary": "Get Session",
        "operationId": "get_session_api_auth_session_get",
        "parameters": [
          {
            "name": "cf_session",
            "in": "cookie",
            "required": false,
            "schema": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "title": "Cf Session"
            }
          }
        ],
        "responses": {
          "200": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/AuthSessionRead"
                }
              }
            }
          },
          "422": {
            "description": "Validation Error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            }
          }
        }
      }
    },
    "/api/users/me": {
      "get": {
        "tags": [
          "users"
        ],
        "summary": "Get Me",
        "operationId": "get_me_api_users_me_get",
        "parameters": [
          {
            "name": "cf_session",
            "in": "cookie",
            "required": false,
            "schema": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "title": "Cf Session"
            }
          }
        ],
        "responses": {
          "200": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/UserRead"
                }
              }
            }
          },
          "422": {
            "description": "Validation Error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            }
          }
        }
      }
    },
    "/api/users": {
      "get": {
        "tags": [
          "users"
        ],
        "summary": "List Users",
        "operationId": "list_users_api_users_get",
        "parameters": [
          {
            "name": "cf_session",
            "in": "cookie",
            "required": false,
            "schema": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "title": "Cf Session"
            }
          }
        ],
        "responses": {
          "200": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/UserListResponse"
                }
              }
            }
          },
          "422": {
            "description": "Validation Error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            }
          }
        }
      }
    },
    "/api/brands": {
      "post": {
        "tags": [
          "brands"
        ],
        "summary": "Create Brand",
        "operationId": "create_brand_api_brands_post",
        "parameters": [
          {
            "name": "cf_session",
            "in": "cookie",
            "required": false,
            "schema": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "title": "Cf Session"
            }
          }
        ],
        "requestBody": {
          "required": true,
          "content": {
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/BrandCreateRequest"
              }
            }
          }
        },
        "responses": {
          "201": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/BrandRead"
                }
              }
            }
          },
          "422": {
            "description": "Validation Error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            }
          }
        }
      },
      "get": {
        "tags": [
          "brands"
        ],
        "summary": "List Brands",
        "operationId": "list_brands_api_brands_get",
        "parameters": [
          {
            "name": "cf_session",
            "in": "cookie",
            "required": false,
            "schema": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "title": "Cf Session"
            }
          }
        ],
        "responses": {
          "200": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/BrandListResponse"
                }
              }
            }
          },
          "422": {
            "description": "Validation Error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            }
          }
        }
      }
    },
    "/api/brands/{brand_id}": {
      "get": {
        "tags": [
          "brands"
        ],
        "summary": "Get Brand",
        "operationId": "get_brand_api_brands__brand_id__get",
        "parameters": [
          {
            "name": "brand_id",
            "in": "path",
            "required": true,
            "schema": {
              "type": "string",
              "title": "Brand Id"
            }
          },
          {
            "name": "cf_session",
            "in": "cookie",
            "required": false,
            "schema": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "title": "Cf Session"
            }
          }
        ],
        "responses": {
          "200": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/BrandRead"
                }
              }
            }
          },
          "422": {
            "description": "Validation Error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            }
          }
        }
      }
    },
    "/api/avatars": {
      "post": {
        "tags": [
          "avatars"
        ],
        "summary": "Create Avatar",
        "operationId": "create_avatar_api_avatars_post",
        "parameters": [
          {
            "name": "cf_session",
            "in": "cookie",
            "required": false,
            "schema": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "title": "Cf Session"
            }
          }
        ],
        "requestBody": {
          "required": true,
          "content": {
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/AvatarCreateRequest"
              }
            }
          }
        },
        "responses": {
          "201": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/AvatarRead"
                }
              }
            }
          },
          "422": {
            "description": "Validation Error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            }
          }
        }
      },
      "get": {
        "tags": [
          "avatars"
        ],
        "summary": "List Avatars",
        "operationId": "list_avatars_api_avatars_get",
        "parameters": [
          {
            "name": "cf_session",
            "in": "cookie",
            "required": false,
            "schema": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "title": "Cf Session"
            }
          }
        ],
        "responses": {
          "200": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/AvatarListResponse"
                }
              }
            }
          },
          "422": {
            "description": "Validation Error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            }
          }
        }
      }
    },
    "/api/avatars/{avatar_id}/identity-packs": {
      "get": {
        "tags": [
          "avatars"
        ],
        "summary": "List Identity Packs",
        "operationId": "list_identity_packs_api_avatars__avatar_id__identity_packs_get",
        "parameters": [
          {
            "name": "avatar_id",
            "in": "path",
            "required": true,
            "schema": {
              "type": "string",
              "title": "Avatar Id"
            }
          },
          {
            "name": "cf_session",
            "in": "cookie",
            "required": false,
            "schema": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "title": "Cf Session"
            }
          }
        ],
        "responses": {
          "200": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/IdentityPackListResponse"
                }
              }
            }
          },
          "422": {
            "description": "Validation Error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            }
          }
        }
      },
      "post": {
        "tags": [
          "avatars"
        ],
        "summary": "Create Identity Pack",
        "operationId": "create_identity_pack_api_avatars__avatar_id__identity_packs_post",
        "parameters": [
          {
            "name": "avatar_id",
            "in": "path",
            "required": true,
            "schema": {
              "type": "string",
              "title": "Avatar Id"
            }
          },
          {
            "name": "cf_session",
            "in": "cookie",
            "required": false,
            "schema": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "title": "Cf Session"
            }
          }
        ],
        "requestBody": {
          "required": true,
          "content": {
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/IdentityPackCreateRequest"
              }
            }
          }
        },
        "responses": {
          "201": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/IdentityPackRead"
                }
              }
            }
          },
          "422": {
            "description": "Validation Error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            }
          }
        }
      }
    },
    "/api/assets/uploads": {
      "post": {
        "tags": [
          "assets"
        ],
        "summary": "Initiate Upload",
        "operationId": "initiate_upload_api_assets_uploads_post",
        "parameters": [
          {
            "name": "cf_session",
            "in": "cookie",
            "required": false,
            "schema": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "title": "Cf Session"
            }
          }
        ],
        "requestBody": {
          "required": true,
          "content": {
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/AssetUploadInitiateRequest"
              }
            }
          }
        },
        "responses": {
          "201": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/AssetUploadInitiateResponse"
                }
              }
            }
          },
          "422": {
            "description": "Validation Error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            }
          }
        }
      }
    },
    "/api/assets/{asset_id}/finalize": {
      "post": {
        "tags": [
          "assets"
        ],
        "summary": "Finalize Upload",
        "operationId": "finalize_upload_api_assets__asset_id__finalize_post",
        "parameters": [
          {
            "name": "asset_id",
            "in": "path",
            "required": true,
            "schema": {
              "type": "string",
              "title": "Asset Id"
            }
          },
          {
            "name": "cf_session",
            "in": "cookie",
            "required": false,
            "schema": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "title": "Cf Session"
            }
          }
        ],
        "requestBody": {
          "required": true,
          "content": {
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/AssetFinalizeRequest"
              }
            }
          }
        },
        "responses": {
          "200": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/AssetRead"
                }
              }
            }
          },
          "422": {
            "description": "Validation Error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            }
          }
        }
      }
    },
    "/api/assets": {
      "get": {
        "tags": [
          "assets"
        ],
        "summary": "List Assets",
        "operationId": "list_assets_api_assets_get",
        "parameters": [
          {
            "name": "cf_session",
            "in": "cookie",
            "required": false,
            "schema": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "title": "Cf Session"
            }
          }
        ],
        "responses": {
          "200": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/AssetListResponse"
                }
              }
            }
          },
          "422": {
            "description": "Validation Error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            }
          }
        }
      }
    },
    "/api/content-items": {
      "post": {
        "tags": [
          "content"
        ],
        "summary": "Create Content Item",
        "operationId": "create_content_item_api_content_items_post",
        "parameters": [
          {
            "name": "cf_session",
            "in": "cookie",
            "required": false,
            "schema": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "title": "Cf Session"
            }
          }
        ],
        "requestBody": {
          "required": true,
          "content": {
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/ContentItemCreateRequest"
              }
            }
          }
        },
        "responses": {
          "201": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/ContentItemRead"
                }
              }
            }
          },
          "422": {
            "description": "Validation Error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            }
          }
        }
      },
      "get": {
        "tags": [
          "content"
        ],
        "summary": "List Content Items",
        "operationId": "list_content_items_api_content_items_get",
        "parameters": [
          {
            "name": "cf_session",
            "in": "cookie",
            "required": false,
            "schema": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "title": "Cf Session"
            }
          }
        ],
        "responses": {
          "200": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/ContentItemListResponse"
                }
              }
            }
          },
          "422": {
            "description": "Validation Error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            }
          }
        }
      }
    },
    "/api/content-items/{content_item_id}": {
      "get": {
        "tags": [
          "content"
        ],
        "summary": "Get Content Item",
        "operationId": "get_content_item_api_content_items__content_item_id__get",
        "parameters": [
          {
            "name": "content_item_id",
            "in": "path",
            "required": true,
            "schema": {
              "type": "string",
              "title": "Content Item Id"
            }
          },
          {
            "name": "cf_session",
            "in": "cookie",
            "required": false,
            "schema": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "title": "Cf Session"
            }
          }
        ],
        "responses": {
          "200": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/ContentItemRead"
                }
              }
            }
          },
          "422": {
            "description": "Validation Error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            }
          }
        }
      }
    },
    "/api/content-items/{content_item_id}/plan": {
      "post": {
        "tags": [
          "content"
        ],
        "summary": "Plan Content Item",
        "operationId": "plan_content_item_api_content_items__content_item_id__plan_post",
        "parameters": [
          {
            "name": "content_item_id",
            "in": "path",
            "required": true,
            "schema": {
              "type": "string",
              "title": "Content Item Id"
            }
          },
          {
            "name": "cf_session",
            "in": "cookie",
            "required": false,
            "schema": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "title": "Cf Session"
            }
          }
        ],
        "requestBody": {
          "required": true,
          "content": {
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/ContentPlanRequest"
              }
            }
          }
        },
        "responses": {
          "200": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/ContentItemRead"
                }
              }
            }
          },
          "422": {
            "description": "Validation Error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            }
          }
        }
      }
    },
    "/api/content-items/{content_item_id}/submit-review": {
      "post": {
        "tags": [
          "content"
        ],
        "summary": "Submit Content Item For Review",
        "operationId": "submit_content_item_for_review_api_content_items__content_item_id__submit_review_post",
        "parameters": [
          {
            "name": "content_item_id",
            "in": "path",
            "required": true,
            "schema": {
              "type": "string",
              "title": "Content Item Id"
            }
          },
          {
            "name": "cf_session",
            "in": "cookie",
            "required": false,
            "schema": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "title": "Cf Session"
            }
          }
        ],
        "responses": {
          "201": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/ReviewTaskRead"
                }
              }
            }
          },
          "422": {
            "description": "Validation Error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            }
          }
        }
      }
    },
    "/api/workflow-presets": {
      "post": {
        "tags": [
          "workflows"
        ],
        "summary": "Create Workflow Preset",
        "operationId": "create_workflow_preset_api_workflow_presets_post",
        "parameters": [
          {
            "name": "cf_session",
            "in": "cookie",
            "required": false,
            "schema": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "title": "Cf Session"
            }
          }
        ],
        "requestBody": {
          "required": true,
          "content": {
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/WorkflowPresetCreateRequest"
              }
            }
          }
        },
        "responses": {
          "201": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/WorkflowPresetRead"
                }
              }
            }
          },
          "422": {
            "description": "Validation Error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            }
          }
        }
      },
      "get": {
        "tags": [
          "workflows"
        ],
        "summary": "List Workflow Presets",
        "operationId": "list_workflow_presets_api_workflow_presets_get",
        "parameters": [
          {
            "name": "cf_session",
            "in": "cookie",
            "required": false,
            "schema": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "title": "Cf Session"
            }
          }
        ],
        "responses": {
          "200": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/WorkflowPresetListResponse"
                }
              }
            }
          },
          "422": {
            "description": "Validation Error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            }
          }
        }
      }
    },
    "/api/workflow-presets/{workflow_preset_id}": {
      "get": {
        "tags": [
          "workflows"
        ],
        "summary": "Get Workflow Preset",
        "operationId": "get_workflow_preset_api_workflow_presets__workflow_preset_id__get",
        "parameters": [
          {
            "name": "workflow_preset_id",
            "in": "path",
            "required": true,
            "schema": {
              "type": "string",
              "title": "Workflow Preset Id"
            }
          },
          {
            "name": "cf_session",
            "in": "cookie",
            "required": false,
            "schema": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "title": "Cf Session"
            }
          }
        ],
        "responses": {
          "200": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/WorkflowPresetRead"
                }
              }
            }
          },
          "422": {
            "description": "Validation Error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            }
          }
        }
      }
    },
    "/api/render-jobs": {
      "post": {
        "tags": [
          "render"
        ],
        "summary": "Create Render Job",
        "operationId": "create_render_job_api_render_jobs_post",
        "parameters": [
          {
            "name": "cf_session",
            "in": "cookie",
            "required": false,
            "schema": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "title": "Cf Session"
            }
          }
        ],
        "requestBody": {
          "required": true,
          "content": {
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/RenderJobCreateRequest"
              }
            }
          }
        },
        "responses": {
          "201": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/RenderJobRead"
                }
              }
            }
          },
          "422": {
            "description": "Validation Error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            }
          }
        }
      },
      "get": {
        "tags": [
          "render"
        ],
        "summary": "List Render Jobs",
        "operationId": "list_render_jobs_api_render_jobs_get",
        "parameters": [
          {
            "name": "cf_session",
            "in": "cookie",
            "required": false,
            "schema": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "title": "Cf Session"
            }
          }
        ],
        "responses": {
          "200": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/RenderJobListResponse"
                }
              }
            }
          },
          "422": {
            "description": "Validation Error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            }
          }
        }
      }
    },
    "/api/render-jobs/{render_job_id}": {
      "get": {
        "tags": [
          "render"
        ],
        "summary": "Get Render Job",
        "operationId": "get_render_job_api_render_jobs__render_job_id__get",
        "parameters": [
          {
            "name": "render_job_id",
            "in": "path",
            "required": true,
            "schema": {
              "type": "string",
              "title": "Render Job Id"
            }
          },
          {
            "name": "cf_session",
            "in": "cookie",
            "required": false,
            "schema": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "title": "Cf Session"
            }
          }
        ],
        "responses": {
          "200": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/RenderJobRead"
                }
              }
            }
          },
          "422": {
            "description": "Validation Error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            }
          }
        }
      }
    },
    "/api/render-jobs/{render_job_id}/cancel": {
      "post": {
        "tags": [
          "render"
        ],
        "summary": "Cancel Render Job",
        "operationId": "cancel_render_job_api_render_jobs__render_job_id__cancel_post",
        "parameters": [
          {
            "name": "render_job_id",
            "in": "path",
            "required": true,
            "schema": {
              "type": "string",
              "title": "Render Job Id"
            }
          },
          {
            "name": "cf_session",
            "in": "cookie",
            "required": false,
            "schema": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "title": "Cf Session"
            }
          }
        ],
        "responses": {
          "200": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/RenderJobRead"
                }
              }
            }
          },
          "422": {
            "description": "Validation Error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            }
          }
        }
      }
    },
    "/api/render-jobs/{render_job_id}/retry": {
      "post": {
        "tags": [
          "render"
        ],
        "summary": "Retry Render Job",
        "operationId": "retry_render_job_api_render_jobs__render_job_id__retry_post",
        "parameters": [
          {
            "name": "render_job_id",
            "in": "path",
            "required": true,
            "schema": {
              "type": "string",
              "title": "Render Job Id"
            }
          },
          {
            "name": "cf_session",
            "in": "cookie",
            "required": false,
            "schema": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "title": "Cf Session"
            }
          }
        ],
        "responses": {
          "200": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/RenderJobRead"
                }
              }
            }
          },
          "422": {
            "description": "Validation Error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            }
          }
        }
      }
    },
    "/api/render-jobs/{render_job_id}/requeue": {
      "post": {
        "tags": [
          "render"
        ],
        "summary": "Requeue Render Job",
        "operationId": "requeue_render_job_api_render_jobs__render_job_id__requeue_post",
        "parameters": [
          {
            "name": "render_job_id",
            "in": "path",
            "required": true,
            "schema": {
              "type": "string",
              "title": "Render Job Id"
            }
          },
          {
            "name": "cf_session",
            "in": "cookie",
            "required": false,
            "schema": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "title": "Cf Session"
            }
          }
        ],
        "responses": {
          "200": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/RenderJobRead"
                }
              }
            }
          },
          "422": {
            "description": "Validation Error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            }
          }
        }
      }
    },
    "/api/render-jobs/{render_job_id}/events": {
      "get": {
        "tags": [
          "render"
        ],
        "summary": "Stream Render Job Events",
        "operationId": "stream_render_job_events_api_render_jobs__render_job_id__events_get",
        "parameters": [
          {
            "name": "render_job_id",
            "in": "path",
            "required": true,
            "schema": {
              "type": "string",
              "title": "Render Job Id"
            }
          },
          {
            "name": "cf_session",
            "in": "cookie",
            "required": false,
            "schema": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "title": "Cf Session"
            }
          }
        ],
        "responses": {
          "200": {
            "description": "Server-sent render job status snapshots.",
            "content": {
              "text/event-stream": {
                "schema": {
                  "type": "string"
                }
              }
            }
          },
          "422": {
            "description": "Validation Error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            }
          }
        }
      }
    },
    "/api/publish-packages": {
      "post": {
        "tags": [
          "publish-packages"
        ],
        "summary": "Create Publish Package",
        "operationId": "create_publish_package_api_publish_packages_post",
        "parameters": [
          {
            "name": "cf_session",
            "in": "cookie",
            "required": false,
            "schema": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "title": "Cf Session"
            }
          }
        ],
        "requestBody": {
          "required": true,
          "content": {
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/PublishPackageCreateRequest"
              }
            }
          }
        },
        "responses": {
          "201": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/PublishPackageRead"
                }
              }
            }
          },
          "422": {
            "description": "Validation Error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            }
          }
        }
      },
      "get": {
        "tags": [
          "publish-packages"
        ],
        "summary": "List Publish Packages",
        "operationId": "list_publish_packages_api_publish_packages_get",
        "parameters": [
          {
            "name": "cf_session",
            "in": "cookie",
            "required": false,
            "schema": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "title": "Cf Session"
            }
          }
        ],
        "responses": {
          "200": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/PublishPackageListResponse"
                }
              }
            }
          },
          "422": {
            "description": "Validation Error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            }
          }
        }
      }
    },
    "/api/publish-packages/{package_id}": {
      "get": {
        "tags": [
          "publish-packages"
        ],
        "summary": "Get Publish Package",
        "operationId": "get_publish_package_api_publish_packages__package_id__get",
        "parameters": [
          {
            "name": "package_id",
            "in": "path",
            "required": true,
            "schema": {
              "type": "string",
              "title": "Package Id"
            }
          },
          {
            "name": "cf_session",
            "in": "cookie",
            "required": false,
            "schema": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "title": "Cf Session"
            }
          }
        ],
        "responses": {
          "200": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/PublishPackageRead"
                }
              }
            }
          },
          "422": {
            "description": "Validation Error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            }
          }
        }
      }
    },
    "/api/publish-packages/{package_id}/cancel": {
      "post": {
        "tags": [
          "publish-packages"
        ],
        "summary": "Cancel Publish Package",
        "operationId": "cancel_publish_package_api_publish_packages__package_id__cancel_post",
        "parameters": [
          {
            "name": "package_id",
            "in": "path",
            "required": true,
            "schema": {
              "type": "string",
              "title": "Package Id"
            }
          },
          {
            "name": "cf_session",
            "in": "cookie",
            "required": false,
            "schema": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "title": "Cf Session"
            }
          }
        ],
        "responses": {
          "200": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/PublishPackageRead"
                }
              }
            }
          },
          "422": {
            "description": "Validation Error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            }
          }
        }
      }
    },
    "/api/publish-packages/{package_id}/retry": {
      "post": {
        "tags": [
          "publish-packages"
        ],
        "summary": "Retry Publish Package",
        "operationId": "retry_publish_package_api_publish_packages__package_id__retry_post",
        "parameters": [
          {
            "name": "package_id",
            "in": "path",
            "required": true,
            "schema": {
              "type": "string",
              "title": "Package Id"
            }
          },
          {
            "name": "cf_session",
            "in": "cookie",
            "required": false,
            "schema": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "title": "Cf Session"
            }
          }
        ],
        "responses": {
          "200": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/PublishPackageRead"
                }
              }
            }
          },
          "422": {
            "description": "Validation Error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            }
          }
        }
      }
    },
    "/api/publish-packages/{package_id}/requeue": {
      "post": {
        "tags": [
          "publish-packages"
        ],
        "summary": "Requeue Publish Package",
        "operationId": "requeue_publish_package_api_publish_packages__package_id__requeue_post",
        "parameters": [
          {
            "name": "package_id",
            "in": "path",
            "required": true,
            "schema": {
              "type": "string",
              "title": "Package Id"
            }
          },
          {
            "name": "cf_session",
            "in": "cookie",
            "required": false,
            "schema": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "title": "Cf Session"
            }
          }
        ],
        "responses": {
          "200": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/PublishPackageRead"
                }
              }
            }
          },
          "422": {
            "description": "Validation Error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            }
          }
        }
      }
    },
    "/api/publish-packages/{package_id}/download": {
      "get": {
        "tags": [
          "publish-packages"
        ],
        "summary": "Get Publish Package Download",
        "operationId": "get_publish_package_download_api_publish_packages__package_id__download_get",
        "parameters": [
          {
            "name": "package_id",
            "in": "path",
            "required": true,
            "schema": {
              "type": "string",
              "title": "Package Id"
            }
          },
          {
            "name": "cf_session",
            "in": "cookie",
            "required": false,
            "schema": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "title": "Cf Session"
            }
          }
        ],
        "responses": {
          "200": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/PublishPackageDownloadResponse"
                }
              }
            }
          },
          "422": {
            "description": "Validation Error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            }
          }
        }
      }
    },
    "/api/review/tasks": {
      "get": {
        "tags": [
          "review"
        ],
        "summary": "List Review Tasks",
        "operationId": "list_review_tasks_api_review_tasks_get",
        "parameters": [
          {
            "name": "cf_session",
            "in": "cookie",
            "required": false,
            "schema": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "title": "Cf Session"
            }
          }
        ],
        "responses": {
          "200": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/ReviewTaskListResponse"
                }
              }
            }
          },
          "422": {
            "description": "Validation Error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            }
          }
        }
      }
    },
    "/api/review/tasks/{task_id}/approve": {
      "post": {
        "tags": [
          "review"
        ],
        "summary": "Approve Review Task",
        "operationId": "approve_review_task_api_review_tasks__task_id__approve_post",
        "parameters": [
          {
            "name": "task_id",
            "in": "path",
            "required": true,
            "schema": {
              "type": "string",
              "title": "Task Id"
            }
          },
          {
            "name": "cf_session",
            "in": "cookie",
            "required": false,
            "schema": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "title": "Cf Session"
            }
          }
        ],
        "requestBody": {
          "required": true,
          "content": {
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/ReviewDecisionRequest"
              }
            }
          }
        },
        "responses": {
          "200": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/ReviewTaskRead"
                }
              }
            }
          },
          "422": {
            "description": "Validation Error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            }
          }
        }
      }
    },
    "/api/review/tasks/{task_id}/request-rework": {
      "post": {
        "tags": [
          "review"
        ],
        "summary": "Request Rework",
        "operationId": "request_rework_api_review_tasks__task_id__request_rework_post",
        "parameters": [
          {
            "name": "task_id",
            "in": "path",
            "required": true,
            "schema": {
              "type": "string",
              "title": "Task Id"
            }
          },
          {
            "name": "cf_session",
            "in": "cookie",
            "required": false,
            "schema": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "title": "Cf Session"
            }
          }
        ],
        "requestBody": {
          "required": true,
          "content": {
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/ReviewDecisionRequest"
              }
            }
          }
        },
        "responses": {
          "200": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/ReviewTaskRead"
                }
              }
            }
          },
          "422": {
            "description": "Validation Error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            }
          }
        }
      }
    },
    "/api/audit/logs": {
      "get": {
        "tags": [
          "audit"
        ],
        "summary": "List Audit Logs",
        "operationId": "list_audit_logs_api_audit_logs_get",
        "parameters": [
          {
            "name": "limit",
            "in": "query",
            "required": false,
            "schema": {
              "type": "integer",
              "maximum": 200,
              "minimum": 1,
              "default": 100,
              "title": "Limit"
            }
          },
          {
            "name": "cf_session",
            "in": "cookie",
            "required": false,
            "schema": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "title": "Cf Session"
            }
          }
        ],
        "responses": {
          "200": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/AuditLogListResponse"
                }
              }
            }
          },
          "422": {
            "description": "Validation Error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            }
          }
        }
      }
    }
  },
  "components": {
    "schemas": {
      "AssetFinalizeRequest": {
        "properties": {
          "byte_size": {
            "type": "integer",
            "exclusiveMinimum": 0.0,
            "title": "Byte Size"
          },
          "checksum_sha256": {
            "anyOf": [
              {
                "type": "string",
                "maxLength": 64,
                "minLength": 64
              },
              {
                "type": "null"
              }
            ],
            "title": "Checksum Sha256"
          }
        },
        "type": "object",
        "required": [
          "byte_size"
        ],
        "title": "AssetFinalizeRequest"
      },
      "AssetListResponse": {
        "properties": {
          "items": {
            "items": {
              "$ref": "#/components/schemas/AssetRead"
            },
            "type": "array",
            "title": "Items"
          }
        },
        "type": "object",
        "required": [
          "items"
        ],
        "title": "AssetListResponse"
      },
      "AssetRead": {
        "properties": {
          "id": {
            "type": "string",
            "title": "Id"
          },
          "brand_id": {
            "type": "string",
            "title": "Brand Id"
          },
          "object_key": {
            "type": "string",
            "title": "Object Key"
          },
          "filename": {
            "type": "string",
            "title": "Filename"
          },
          "content_type": {
            "type": "string",
            "title": "Content Type"
          },
          "byte_size": {
            "anyOf": [
              {
                "type": "integer"
              },
              {
                "type": "null"
              }
            ],
            "title": "Byte Size"
          },
          "checksum_sha256": {
            "anyOf": [
              {
                "type": "string"
              },
              {
                "type": "null"
              }
            ],
            "title": "Checksum Sha256"
          },
          "status": {
            "$ref": "#/components/schemas/AssetStatus"
          },
          "upload_expires_at": {
            "type": "string",
            "format": "date-time",
            "title": "Upload Expires At"
          },
          "created_at": {
            "type": "string",
            "format": "date-time",
            "title": "Created At"
          },
          "updated_at": {
            "type": "string",
            "format": "date-time",
            "title": "Updated At"
          }
        },
        "type": "object",
        "required": [
          "id",
          "brand_id",
          "object_key",
          "filename",
          "content_type",
          "byte_size",
          "checksum_sha256",
          "status",
          "upload_expires_at",
          "created_at",
          "updated_at"
        ],
        "title": "AssetRead"
      },
      "AssetStatus": {
        "type": "string",
        "enum": [
          "pending_upload",
          "ready",
          "failed"
        ],
        "title": "AssetStatus"
      },
      "AssetUploadInitiateRequest": {
        "properties": {
          "brand_id": {
            "type": "string",
            "title": "Brand Id"
          },
          "filename": {
            "type": "string",
            "maxLength": 255,
            "minLength": 1,
            "title": "Filename"
          },
          "content_type": {
            "type": "string",
            "maxLength": 255,
            "minLength": 1,
            "title": "Content Type"
          },
          "byte_size": {
            "anyOf": [
              {
                "type": "integer",
                "exclusiveMinimum": 0.0
              },
              {
                "type": "null"
              }
            ],
            "title": "Byte Size"
          }
        },
        "type": "object",
        "required": [
          "brand_id",
          "filename",
          "content_type"
        ],
        "title": "AssetUploadInitiateRequest"
      },
      "AssetUploadInitiateResponse": {
        "properties": {
          "asset": {
            "$ref": "#/components/schemas/AssetRead"
          },
          "upload": {
            "$ref": "#/components/schemas/UploadTargetRead"
          }
        },
        "type": "object",
        "required": [
          "asset",
          "upload"
        ],
        "title": "AssetUploadInitiateResponse"
      },
      "AuditLogListResponse": {
        "properties": {
          "items": {
            "items": {
              "$ref": "#/components/schemas/AuditLogRead"
            },
            "type": "array",
            "title": "Items"
          }
        },
        "type": "object",
        "required": [
          "items"
        ],
        "title": "AuditLogListResponse"
      },
      "AuditLogRead": {
        "properties": {
          "id": {
            "type": "string",
            "title": "Id"
          },
          "actor_user_id": {
            "anyOf": [
              {
                "type": "string"
              },
              {
                "type": "null"
              }
            ],
            "title": "Actor User Id"
          },
          "action": {
            "type": "string",
            "title": "Action"
          },
          "entity_type": {
            "type": "string",
            "title": "Entity Type"
          },
          "entity_id": {
            "type": "string",
            "title": "Entity Id"
          },
          "payload": {
            "additionalProperties": true,
            "type": "object",
            "title": "Payload"
          },
          "created_at": {
            "type": "string",
            "format": "date-time",
            "title": "Created At"
          }
        },
        "type": "object",
        "required": [
          "id",
          "actor_user_id",
          "action",
          "entity_type",
          "entity_id",
          "payload",
          "created_at"
        ],
        "title": "AuditLogRead"
      },
      "AuthSessionRead": {
        "properties": {
          "user": {
            "$ref": "#/components/schemas/UserRead"
          },
          "expires_at": {
            "type": "string",
            "format": "date-time",
            "title": "Expires At"
          }
        },
        "type": "object",
        "required": [
          "user",
          "expires_at"
        ],
        "title": "AuthSessionRead"
      },
      "AvatarCreateRequest": {
        "properties": {
          "brand_id": {
            "type": "string",
            "title": "Brand Id"
          },
          "name": {
            "type": "string",
            "maxLength": 255,
            "minLength": 1,
            "title": "Name"
          },
          "persona_notes": {
            "anyOf": [
              {
                "type": "string",
                "maxLength": 10000
              },
              {
                "type": "null"
              }
            ],
            "title": "Persona Notes"
          }
        },
        "type": "object",
        "required": [
          "brand_id",
          "name"
        ],
        "title": "AvatarCreateRequest"
      },
      "AvatarListResponse": {
        "properties": {
          "items": {
            "items": {
              "$ref": "#/components/schemas/AvatarRead"
            },
            "type": "array",
            "title": "Items"
          }
        },
        "type": "object",
        "required": [
          "items"
        ],
        "title": "AvatarListResponse"
      },
      "AvatarRead": {
        "properties": {
          "id": {
            "type": "string",
            "title": "Id"
          },
          "brand_id": {
            "type": "string",
            "title": "Brand Id"
          },
          "name": {
            "type": "string",
            "title": "Name"
          },
          "persona_notes": {
            "anyOf": [
              {
                "type": "string"
              },
              {
                "type": "null"
              }
            ],
            "title": "Persona Notes"
          },
          "status": {
            "$ref": "#/components/schemas/AvatarStatus"
          },
          "created_by_user_id": {
            "type": "string",
            "title": "Created By User Id"
          },
          "created_at": {
            "type": "string",
            "format": "date-time",
            "title": "Created At"
          },
          "updated_at": {
            "type": "string",
            "format": "date-time",
            "title": "Updated At"
          }
        },
        "type": "object",
        "required": [
          "id",
          "brand_id",
          "name",
          "persona_notes",
          "status",
          "created_by_user_id",
          "created_at",
          "updated_at"
        ],
        "title": "AvatarRead"
      },
      "AvatarStatus": {
        "type": "string",
        "enum": [
          "draft",
          "active"
        ],
        "title": "AvatarStatus"
      },
      "BootstrapOwnerRequest": {
        "properties": {
          "email": {
            "type": "string",
            "title": "Email"
          },
          "display_name": {
            "type": "string",
            "maxLength": 255,
            "minLength": 1,
            "title": "Display Name"
          },
          "password": {
            "type": "string",
            "maxLength": 255,
            "minLength": 8,
            "title": "Password"
          }
        },
        "type": "object",
        "required": [
          "email",
          "display_name",
          "password"
        ],
        "title": "BootstrapOwnerRequest"
      },
      "BrandCreateRequest": {
        "properties": {
          "name": {
            "type": "string",
            "maxLength": 255,
            "minLength": 1,
            "title": "Name"
          },
          "voice_notes": {
            "anyOf": [
              {
                "type": "string",
                "maxLength": 10000
              },
              {
                "type": "null"
              }
            ],
            "title": "Voice Notes"
          }
        },
        "type": "object",
        "required": [
          "name"
        ],
        "title": "BrandCreateRequest"
      },
      "BrandListResponse": {
        "properties": {
          "items": {
            "items": {
              "$ref": "#/components/schemas/BrandRead"
            },
            "type": "array",
            "title": "Items"
          }
        },
        "type": "object",
        "required": [
          "items"
        ],
        "title": "BrandListResponse"
      },
      "BrandRead": {
        "properties": {
          "id": {
            "type": "string",
            "title": "Id"
          },
          "name": {
            "type": "string",
            "title": "Name"
          },
          "voice_notes": {
            "anyOf": [
              {
                "type": "string"
              },
              {
                "type": "null"
              }
            ],
            "title": "Voice Notes"
          },
          "created_by_user_id": {
            "type": "string",
            "title": "Created By User Id"
          },
          "created_at": {
            "type": "string",
            "format": "date-time",
            "title": "Created At"
          },
          "updated_at": {
            "type": "string",
            "format": "date-time",
            "title": "Updated At"
          }
        },
        "type": "object",
        "required": [
          "id",
          "name",
          "voice_notes",
          "created_by_user_id",
          "created_at",
          "updated_at"
        ],
        "title": "BrandRead"
      },
      "ContentChannel": {
        "type": "string",
        "enum": [
          "instagram_reels",
          "youtube_shorts"
        ],
        "title": "ContentChannel"
      },
      "ContentItemCreateRequest": {
        "properties": {
          "brand_id": {
            "type": "string",
            "title": "Brand Id"
          },
          "avatar_id": {
            "type": "string",
            "title": "Avatar Id"
          },
          "title": {
            "type": "string",
            "maxLength": 255,
            "minLength": 1,
            "title": "Title"
          },
          "script": {
            "type": "string",
            "maxLength": 20000,
            "minLength": 1,
            "title": "Script"
          },
          "channel": {
            "$ref": "#/components/schemas/ContentChannel"
          }
        },
        "type": "object",
        "required": [
          "brand_id",
          "avatar_id",
          "title",
          "script",
          "channel"
        ],
        "title": "ContentItemCreateRequest"
      },
      "ContentItemListResponse": {
        "properties": {
          "items": {
            "items": {
              "$ref": "#/components/schemas/ContentItemRead"
            },
            "type": "array",
            "title": "Items"
          }
        },
        "type": "object",
        "required": [
          "items"
        ],
        "title": "ContentItemListResponse"
      },
      "ContentItemRead": {
        "properties": {
          "id": {
            "type": "string",
            "title": "Id"
          },
          "brand_id": {
            "type": "string",
            "title": "Brand Id"
          },
          "avatar_id": {
            "type": "string",
            "title": "Avatar Id"
          },
          "title": {
            "type": "string",
            "title": "Title"
          },
          "script": {
            "type": "string",
            "title": "Script"
          },
          "channel": {
            "$ref": "#/components/schemas/ContentChannel"
          },
          "status": {
            "$ref": "#/components/schemas/ContentStatus"
          },
          "planned_publish_at": {
            "anyOf": [
              {
                "type": "string",
                "format": "date-time"
              },
              {
                "type": "null"
              }
            ],
            "title": "Planned Publish At"
          },
          "created_by_user_id": {
            "type": "string",
            "title": "Created By User Id"
          },
          "created_at": {
            "type": "string",
            "format": "date-time",
            "title": "Created At"
          },
          "updated_at": {
            "type": "string",
            "format": "date-time",
            "title": "Updated At"
          }
        },
        "type": "object",
        "required": [
          "id",
          "brand_id",
          "avatar_id",
          "title",
          "script",
          "channel",
          "status",
          "planned_publish_at",
          "created_by_user_id",
          "created_at",
          "updated_at"
        ],
        "title": "ContentItemRead"
      },
      "ContentPlanRequest": {
        "properties": {
          "planned_publish_at": {
            "anyOf": [
              {
                "type": "string",
                "format": "date-time"
              },
              {
                "type": "null"
              }
            ],
            "title": "Planned Publish At"
          }
        },
        "type": "object",
        "title": "ContentPlanRequest"
      },
      "ContentStatus": {
        "type": "string",
        "enum": [
          "draft",
          "planned",
          "review",
          "approved",
          "rework"
        ],
        "title": "ContentStatus"
      },
      "DownloadTargetRead": {
        "properties": {
          "method": {
            "type": "string",
            "title": "Method"
          },
          "url": {
            "type": "string",
            "title": "Url"
          },
          "headers": {
            "additionalProperties": {
              "type": "string"
            },
            "type": "object",
            "title": "Headers"
          },
          "expires_at": {
            "type": "string",
            "format": "date-time",
            "title": "Expires At"
          }
        },
        "type": "object",
        "required": [
          "method",
          "url",
          "headers",
          "expires_at"
        ],
        "title": "DownloadTargetRead"
      },
      "HTTPValidationError": {
        "properties": {
          "detail": {
            "items": {
              "$ref": "#/components/schemas/ValidationError"
            },
            "type": "array",
            "title": "Detail"
          }
        },
        "type": "object",
        "title": "HTTPValidationError"
      },
      "IdentityPackCreateRequest": {
        "properties": {
          "name": {
            "type": "string",
            "maxLength": 255,
            "minLength": 1,
            "title": "Name"
          },
          "description": {
            "anyOf": [
              {
                "type": "string",
                "maxLength": 10000
              },
              {
                "type": "null"
              }
            ],
            "title": "Description"
          },
          "storage_prefix": {
            "type": "string",
            "maxLength": 500,
            "minLength": 1,
            "title": "Storage Prefix"
          }
        },
        "type": "object",
        "required": [
          "name",
          "storage_prefix"
        ],
        "title": "IdentityPackCreateRequest"
      },
      "IdentityPackListResponse": {
        "properties": {
          "items": {
            "items": {
              "$ref": "#/components/schemas/IdentityPackRead"
            },
            "type": "array",
            "title": "Items"
          }
        },
        "type": "object",
        "required": [
          "items"
        ],
        "title": "IdentityPackListResponse"
      },
      "IdentityPackRead": {
        "properties": {
          "id": {
            "type": "string",
            "title": "Id"
          },
          "avatar_id": {
            "type": "string",
            "title": "Avatar Id"
          },
          "name": {
            "type": "string",
            "title": "Name"
          },
          "description": {
            "anyOf": [
              {
                "type": "string"
              },
              {
                "type": "null"
              }
            ],
            "title": "Description"
          },
          "storage_prefix": {
            "type": "string",
            "title": "Storage Prefix"
          },
          "status": {
            "$ref": "#/components/schemas/IdentityPackStatus"
          },
          "created_at": {
            "type": "string",
            "format": "date-time",
            "title": "Created At"
          },
          "updated_at": {
            "type": "string",
            "format": "date-time",
            "title": "Updated At"
          }
        },
        "type": "object",
        "required": [
          "id",
          "avatar_id",
          "name",
          "description",
          "storage_prefix",
          "status",
          "created_at",
          "updated_at"
        ],
        "title": "IdentityPackRead"
      },
      "IdentityPackStatus": {
        "type": "string",
        "enum": [
          "draft",
          "ready"
        ],
        "title": "IdentityPackStatus"
      },
      "InviteAcceptRequest": {
        "properties": {
          "token": {
            "type": "string",
            "minLength": 16,
            "title": "Token"
          },
          "email": {
            "type": "string",
            "title": "Email"
          },
          "display_name": {
            "type": "string",
            "maxLength": 255,
            "minLength": 1,
            "title": "Display Name"
          },
          "password": {
            "type": "string",
            "maxLength": 255,
            "minLength": 8,
            "title": "Password"
          }
        },
        "type": "object",
        "required": [
          "token",
          "email",
          "display_name",
          "password"
        ],
        "title": "InviteAcceptRequest"
      },
      "InviteCreateRequest": {
        "properties": {
          "email": {
            "type": "string",
            "title": "Email"
          },
          "role": {
            "$ref": "#/components/schemas/UserRole"
          }
        },
        "type": "object",
        "required": [
          "email",
          "role"
        ],
        "title": "InviteCreateRequest"
      },
      "InviteCreateResponse": {
        "properties": {
          "invite_id": {
            "type": "string",
            "title": "Invite Id"
          },
          "email": {
            "type": "string",
            "title": "Email"
          },
          "role": {
            "$ref": "#/components/schemas/UserRole"
          },
          "token": {
            "type": "string",
            "title": "Token"
          },
          "expires_at": {
            "type": "string",
            "format": "date-time",
            "title": "Expires At"
          }
        },
        "type": "object",
        "required": [
          "invite_id",
          "email",
          "role",
          "token",
          "expires_at"
        ],
        "title": "InviteCreateResponse"
      },
      "JobAttemptRead": {
        "properties": {
          "id": {
            "type": "string",
            "title": "Id"
          },
          "render_job_id": {
            "type": "string",
            "title": "Render Job Id"
          },
          "attempt_number": {
            "type": "integer",
            "title": "Attempt Number"
          },
          "status": {
            "$ref": "#/components/schemas/JobAttemptStatus"
          },
          "provider_job_id": {
            "anyOf": [
              {
                "type": "string"
              },
              {
                "type": "null"
              }
            ],
            "title": "Provider Job Id"
          },
          "request_payload": {
            "additionalProperties": true,
            "type": "object",
            "title": "Request Payload"
          },
          "response_payload": {
            "additionalProperties": true,
            "type": "object",
            "title": "Response Payload"
          },
          "error_message": {
            "anyOf": [
              {
                "type": "string"
              },
              {
                "type": "null"
              }
            ],
            "title": "Error Message"
          },
          "started_at": {
            "anyOf": [
              {
                "type": "string",
                "format": "date-time"
              },
              {
                "type": "null"
              }
            ],
            "title": "Started At"
          },
          "finished_at": {
            "anyOf": [
              {
                "type": "string",
                "format": "date-time"
              },
              {
                "type": "null"
              }
            ],
            "title": "Finished At"
          },
          "created_at": {
            "type": "string",
            "format": "date-time",
            "title": "Created At"
          },
          "updated_at": {
            "type": "string",
            "format": "date-time",
            "title": "Updated At"
          }
        },
        "type": "object",
        "required": [
          "id",
          "render_job_id",
          "attempt_number",
          "status",
          "provider_job_id",
          "request_payload",
          "response_payload",
          "error_message",
          "started_at",
          "finished_at",
          "created_at",
          "updated_at"
        ],
        "title": "JobAttemptRead"
      },
      "JobAttemptStatus": {
        "type": "string",
        "enum": [
          "queued",
          "running",
          "succeeded",
          "failed",
          "cancelled"
        ],
        "title": "JobAttemptStatus"
      },
      "LoginRequest": {
        "properties": {
          "email": {
            "type": "string",
            "title": "Email"
          },
          "password": {
            "type": "string",
            "maxLength": 255,
            "minLength": 1,
            "title": "Password"
          }
        },
        "type": "object",
        "required": [
          "email",
          "password"
        ],
        "title": "LoginRequest"
      },
      "OutputArtifactType": {
        "type": "string",
        "enum": [
          "video",
          "cover_image",
          "caption_text",
          "manifest"
        ],
        "title": "OutputArtifactType"
      },
      "PackagingProvider": {
        "type": "string",
        "enum": [
          "ffmpeg"
        ],
        "title": "PackagingProvider"
      },
      "PublishPackageCreateRequest": {
        "properties": {
          "render_job_id": {
            "type": "string",
            "title": "Render Job Id"
          }
        },
        "type": "object",
        "required": [
          "render_job_id"
        ],
        "title": "PublishPackageCreateRequest"
      },
      "PublishPackageDownloadResponse": {
        "properties": {
          "package": {
            "$ref": "#/components/schemas/PublishPackageRead"
          },
          "download": {
            "$ref": "#/components/schemas/DownloadTargetRead"
          }
        },
        "type": "object",
        "required": [
          "package",
          "download"
        ],
        "title": "PublishPackageDownloadResponse"
      },
      "PublishPackageListResponse": {
        "properties": {
          "items": {
            "items": {
              "$ref": "#/components/schemas/PublishPackageRead"
            },
            "type": "array",
            "title": "Items"
          }
        },
        "type": "object",
        "required": [
          "items"
        ],
        "title": "PublishPackageListResponse"
      },
      "PublishPackageRead": {
        "properties": {
          "id": {
            "type": "string",
            "title": "Id"
          },
          "render_job_id": {
            "type": "string",
            "title": "Render Job Id"
          },
          "content_item_id": {
            "type": "string",
            "title": "Content Item Id"
          },
          "status": {
            "$ref": "#/components/schemas/PublishPackageStatus"
          },
          "package_object_key": {
            "anyOf": [
              {
                "type": "string"
              },
              {
                "type": "null"
              }
            ],
            "title": "Package Object Key"
          },
          "manifest_payload": {
            "additionalProperties": true,
            "type": "object",
            "title": "Manifest Payload"
          },
          "byte_size": {
            "anyOf": [
              {
                "type": "integer"
              },
              {
                "type": "null"
              }
            ],
            "title": "Byte Size"
          },
          "error_message": {
            "anyOf": [
              {
                "type": "string"
              },
              {
                "type": "null"
              }
            ],
            "title": "Error Message"
          },
          "created_by_user_id": {
            "type": "string",
            "title": "Created By User Id"
          },
          "created_at": {
            "type": "string",
            "format": "date-time",
            "title": "Created At"
          },
          "updated_at": {
            "type": "string",
            "format": "date-time",
            "title": "Updated At"
          }
        },
        "type": "object",
        "required": [
          "id",
          "render_job_id",
          "content_item_id",
          "status",
          "package_object_key",
          "manifest_payload",
          "byte_size",
          "error_message",
          "created_by_user_id",
          "created_at",
          "updated_at"
        ],
        "title": "PublishPackageRead"
      },
      "PublishPackageStatus": {
        "type": "string",
        "enum": [
          "queued",
          "running",
          "ready",
          "failed",
          "cancelled"
        ],
        "title": "PublishPackageStatus"
      },
      "RenderJobCreateRequest": {
        "properties": {
          "content_item_id": {
            "type": "string",
            "title": "Content Item Id"
          },
          "workflow_preset_id": {
            "type": "string",
            "title": "Workflow Preset Id"
          },
          "identity_pack_id": {
            "anyOf": [
              {
                "type": "string"
              },
              {
                "type": "null"
              }
            ],
            "title": "Identity Pack Id"
          },
          "retry_budget": {
            "type": "integer",
            "maximum": 5.0,
            "minimum": 1.0,
            "title": "Retry Budget",
            "default": 3
          }
        },
        "type": "object",
        "required": [
          "content_item_id",
          "workflow_preset_id"
        ],
        "title": "RenderJobCreateRequest"
      },
      "RenderJobListResponse": {
        "properties": {
          "items": {
            "items": {
              "$ref": "#/components/schemas/RenderJobRead"
            },
            "type": "array",
            "title": "Items"
          }
        },
        "type": "object",
        "required": [
          "items"
        ],
        "title": "RenderJobListResponse"
      },
      "RenderJobRead": {
        "properties": {
          "id": {
            "type": "string",
            "title": "Id"
          },
          "content_item_id": {
            "type": "string",
            "title": "Content Item Id"
          },
          "workflow_preset_id": {
            "type": "string",
            "title": "Workflow Preset Id"
          },
          "workflow_preset_key": {
            "type": "string",
            "title": "Workflow Preset Key"
          },
          "workflow_preset_version": {
            "type": "integer",
            "title": "Workflow Preset Version"
          },
          "workflow_provider": {
            "$ref": "#/components/schemas/WorkflowProvider"
          },
          "voice_provider": {
            "$ref": "#/components/schemas/VoiceProvider"
          },
          "packaging_provider": {
            "$ref": "#/components/schemas/PackagingProvider"
          },
          "input_snapshot": {
            "additionalProperties": true,
            "type": "object",
            "title": "Input Snapshot"
          },
          "status": {
            "$ref": "#/components/schemas/RenderJobStatus"
          },
          "retry_budget": {
            "type": "integer",
            "title": "Retry Budget"
          },
          "created_by_user_id": {
            "type": "string",
            "title": "Created By User Id"
          },
          "created_at": {
            "type": "string",
            "format": "date-time",
            "title": "Created At"
          },
          "updated_at": {
            "type": "string",
            "format": "date-time",
            "title": "Updated At"
          },
          "attempts": {
            "items": {
              "$ref": "#/components/schemas/JobAttemptRead"
            },
            "type": "array",
            "title": "Attempts"
          }
        },
        "type": "object",
        "required": [
          "id",
          "content_item_id",
          "workflow_preset_id",
          "workflow_preset_key",
          "workflow_preset_version",
          "workflow_provider",
          "voice_provider",
          "packaging_provider",
          "input_snapshot",
          "status",
          "retry_budget",
          "created_by_user_id",
          "created_at",
          "updated_at",
          "attempts"
        ],
        "title": "RenderJobRead"
      },
      "RenderJobStatus": {
        "type": "string",
        "enum": [
          "queued",
          "running",
          "succeeded",
          "failed",
          "cancelled"
        ],
        "title": "RenderJobStatus"
      },
      "ReviewDecisionRequest": {
        "properties": {
          "decision_notes": {
            "anyOf": [
              {
                "type": "string",
                "maxLength": 10000
              },
              {
                "type": "null"
              }
            ],
            "title": "Decision Notes"
          }
        },
        "type": "object",
        "title": "ReviewDecisionRequest"
      },
      "ReviewTaskListResponse": {
        "properties": {
          "items": {
            "items": {
              "$ref": "#/components/schemas/ReviewTaskRead"
            },
            "type": "array",
            "title": "Items"
          }
        },
        "type": "object",
        "required": [
          "items"
        ],
        "title": "ReviewTaskListResponse"
      },
      "ReviewTaskRead": {
        "properties": {
          "id": {
            "type": "string",
            "title": "Id"
          },
          "content_item_id": {
            "type": "string",
            "title": "Content Item Id"
          },
          "assigned_to_user_id": {
            "anyOf": [
              {
                "type": "string"
              },
              {
                "type": "null"
              }
            ],
            "title": "Assigned To User Id"
          },
          "status": {
            "$ref": "#/components/schemas/ReviewTaskStatus"
          },
          "decision_notes": {
            "anyOf": [
              {
                "type": "string"
              },
              {
                "type": "null"
              }
            ],
            "title": "Decision Notes"
          },
          "completed_at": {
            "anyOf": [
              {
                "type": "string",
                "format": "date-time"
              },
              {
                "type": "null"
              }
            ],
            "title": "Completed At"
          },
          "created_at": {
            "type": "string",
            "format": "date-time",
            "title": "Created At"
          },
          "updated_at": {
            "type": "string",
            "format": "date-time",
            "title": "Updated At"
          }
        },
        "type": "object",
        "required": [
          "id",
          "content_item_id",
          "assigned_to_user_id",
          "status",
          "decision_notes",
          "completed_at",
          "created_at",
          "updated_at"
        ],
        "title": "ReviewTaskRead"
      },
      "ReviewTaskStatus": {
        "type": "string",
        "enum": [
          "open",
          "approved",
          "rework",
          "cancelled"
        ],
        "title": "ReviewTaskStatus"
      },
      "StatusResponse": {
        "properties": {
          "status": {
            "type": "string",
            "title": "Status"
          }
        },
        "type": "object",
        "required": [
          "status"
        ],
        "title": "StatusResponse"
      },
      "UploadTargetRead": {
        "properties": {
          "method": {
            "type": "string",
            "title": "Method"
          },
          "url": {
            "type": "string",
            "title": "Url"
          },
          "headers": {
            "additionalProperties": {
              "type": "string"
            },
            "type": "object",
            "title": "Headers"
          },
          "expires_at": {
            "type": "string",
            "format": "date-time",
            "title": "Expires At"
          }
        },
        "type": "object",
        "required": [
          "method",
          "url",
          "headers",
          "expires_at"
        ],
        "title": "UploadTargetRead"
      },
      "UserListResponse": {
        "properties": {
          "items": {
            "items": {
              "$ref": "#/components/schemas/UserRead"
            },
            "type": "array",
            "title": "Items"
          }
        },
        "type": "object",
        "required": [
          "items"
        ],
        "title": "UserListResponse"
      },
      "UserRead": {
        "properties": {
          "id": {
            "type": "string",
            "title": "Id"
          },
          "email": {
            "type": "string",
            "title": "Email"
          },
          "display_name": {
            "type": "string",
            "title": "Display Name"
          },
          "role": {
            "$ref": "#/components/schemas/UserRole"
          },
          "status": {
            "$ref": "#/components/schemas/UserStatus"
          },
          "created_at": {
            "type": "string",
            "format": "date-time",
            "title": "Created At"
          }
        },
        "type": "object",
        "required": [
          "id",
          "email",
          "display_name",
          "role",
          "status",
          "created_at"
        ],
        "title": "UserRead"
      },
      "UserRole": {
        "type": "string",
        "enum": [
          "owner",
          "operator",
          "reviewer",
          "viewer"
        ],
        "title": "UserRole"
      },
      "UserStatus": {
        "type": "string",
        "enum": [
          "active",
          "disabled"
        ],
        "title": "UserStatus"
      },
      "ValidationError": {
        "properties": {
          "loc": {
            "items": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "integer"
                }
              ]
            },
            "type": "array",
            "title": "Location"
          },
          "msg": {
            "type": "string",
            "title": "Message"
          },
          "type": {
            "type": "string",
            "title": "Error Type"
          },
          "input": {
            "title": "Input"
          },
          "ctx": {
            "type": "object",
            "title": "Context"
          }
        },
        "type": "object",
        "required": [
          "loc",
          "msg",
          "type"
        ],
        "title": "ValidationError"
      },
      "VoiceProvider": {
        "type": "string",
        "enum": [
          "none"
        ],
        "title": "VoiceProvider"
      },
      "WorkflowInputBinding": {
        "properties": {
          "source_type": {
            "$ref": "#/components/schemas/WorkflowInputSourceType"
          },
          "source_field": {
            "anyOf": [
              {
                "type": "string",
                "maxLength": 255,
                "minLength": 1
              },
              {
                "type": "null"
              }
            ],
            "title": "Source Field"
          },
          "value": {
            "anyOf": [
              {},
              {
                "type": "null"
              }
            ],
            "title": "Value"
          }
        },
        "type": "object",
        "required": [
          "source_type"
        ],
        "title": "WorkflowInputBinding"
      },
      "WorkflowInputSourceType": {
        "type": "string",
        "enum": [
          "content_item",
          "brand",
          "avatar",
          "identity_pack",
          "literal"
        ],
        "title": "WorkflowInputSourceType"
      },
      "WorkflowOutputBinding": {
        "properties": {
          "artifact_type": {
            "$ref": "#/components/schemas/OutputArtifactType"
          },
          "output_path": {
            "type": "string",
            "maxLength": 255,
            "minLength": 1,
            "title": "Output Path"
          }
        },
        "type": "object",
        "required": [
          "artifact_type",
          "output_path"
        ],
        "title": "WorkflowOutputBinding"
      },
      "WorkflowPresetCreateRequest": {
        "properties": {
          "key": {
            "type": "string",
            "maxLength": 120,
            "minLength": 3,
            "pattern": "^[a-z0-9]+(?:[-_][a-z0-9]+)*$",
            "title": "Key"
          },
          "name": {
            "type": "string",
            "maxLength": 255,
            "minLength": 1,
            "title": "Name"
          },
          "description": {
            "anyOf": [
              {
                "type": "string",
                "maxLength": 10000
              },
              {
                "type": "null"
              }
            ],
            "title": "Description"
          },
          "workflow_provider": {
            "$ref": "#/components/schemas/WorkflowProvider"
          },
          "voice_provider": {
            "$ref": "#/components/schemas/VoiceProvider"
          },
          "packaging_provider": {
            "$ref": "#/components/schemas/PackagingProvider"
          },
          "workflow_definition": {
            "additionalProperties": true,
            "type": "object",
            "minProperties": 1,
            "title": "Workflow Definition"
          },
          "input_mapping": {
            "additionalProperties": {
              "$ref": "#/components/schemas/WorkflowInputBinding"
            },
            "type": "object",
            "minProperties": 1,
            "title": "Input Mapping"
          },
          "output_mapping": {
            "additionalProperties": {
              "$ref": "#/components/schemas/WorkflowOutputBinding"
            },
            "type": "object",
            "minProperties": 1,
            "title": "Output Mapping"
          }
        },
        "type": "object",
        "required": [
          "key",
          "name",
          "workflow_provider",
          "voice_provider",
          "packaging_provider",
          "workflow_definition",
          "input_mapping",
          "output_mapping"
        ],
        "title": "WorkflowPresetCreateRequest"
      },
      "WorkflowPresetListResponse": {
        "properties": {
          "items": {
            "items": {
              "$ref": "#/components/schemas/WorkflowPresetRead"
            },
            "type": "array",
            "title": "Items"
          }
        },
        "type": "object",
        "required": [
          "items"
        ],
        "title": "WorkflowPresetListResponse"
      },
      "WorkflowPresetRead": {
        "properties": {
          "id": {
            "type": "string",
            "title": "Id"
          },
          "key": {
            "type": "string",
            "title": "Key"
          },
          "version": {
            "type": "integer",
            "title": "Version"
          },
          "name": {
            "type": "string",
            "title": "Name"
          },
          "description": {
            "anyOf": [
              {
                "type": "string"
              },
              {
                "type": "null"
              }
            ],
            "title": "Description"
          },
          "workflow_provider": {
            "$ref": "#/components/schemas/WorkflowProvider"
          },
          "voice_provider": {
            "$ref": "#/components/schemas/VoiceProvider"
          },
          "packaging_provider": {
            "$ref": "#/components/schemas/PackagingProvider"
          },
          "workflow_definition": {
            "additionalProperties": true,
            "type": "object",
            "title": "Workflow Definition"
          },
          "input_mapping": {
            "additionalProperties": {
              "$ref": "#/components/schemas/WorkflowInputBinding"
            },
            "type": "object",
            "title": "Input Mapping"
          },
          "output_mapping": {
            "additionalProperties": {
              "$ref": "#/components/schemas/WorkflowOutputBinding"
            },
            "type": "object",
            "title": "Output Mapping"
          },
          "created_by_user_id": {
            "type": "string",
            "title": "Created By User Id"
          },
          "created_at": {
            "type": "string",
            "format": "date-time",
            "title": "Created At"
          },
          "updated_at": {
            "type": "string",
            "format": "date-time",
            "title": "Updated At"
          }
        },
        "type": "object",
        "required": [
          "id",
          "key",
          "version",
          "name",
          "description",
          "workflow_provider",
          "voice_provider",
          "packaging_provider",
          "workflow_definition",
          "input_mapping",
          "output_mapping",
          "created_by_user_id",
          "created_at",
          "updated_at"
        ],
        "title": "WorkflowPresetRead"
      },
      "WorkflowProvider": {
        "type": "string",
        "enum": [
          "comfyui"
        ],
        "title": "WorkflowProvider"
      }
    }
  }
}
```

`packages/contracts/src/generated/api.ts`:

```ts
/**
 * This file was auto-generated by openapi-typescript.
 * Do not make direct changes to the file.
 */

export interface paths {
    "/": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Root */
        get: operations["root__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/meta": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Meta */
        get: operations["meta_api_meta_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/health/live": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Live */
        get: operations["live_health_live_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/health/ready": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Ready */
        get: operations["ready_health_ready_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/auth/bootstrap-owner": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Bootstrap Owner */
        post: operations["bootstrap_owner_api_auth_bootstrap_owner_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/auth/invites": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Create Invite */
        post: operations["create_invite_api_auth_invites_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/auth/invites/accept": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Accept Invite */
        post: operations["accept_invite_api_auth_invites_accept_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/auth/login": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Login */
        post: operations["login_api_auth_login_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/auth/logout": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Logout */
        post: operations["logout_api_auth_logout_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/auth/session": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Session */
        get: operations["get_session_api_auth_session_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/users/me": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Me */
        get: operations["get_me_api_users_me_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/users": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Users */
        get: operations["list_users_api_users_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/brands": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Brands */
        get: operations["list_brands_api_brands_get"];
        put?: never;
        /** Create Brand */
        post: operations["create_brand_api_brands_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/brands/{brand_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Brand */
        get: operations["get_brand_api_brands__brand_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/avatars": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Avatars */
        get: operations["list_avatars_api_avatars_get"];
        put?: never;
        /** Create Avatar */
        post: operations["create_avatar_api_avatars_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/avatars/{avatar_id}/identity-packs": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Identity Packs */
        get: operations["list_identity_packs_api_avatars__avatar_id__identity_packs_get"];
        put?: never;
        /** Create Identity Pack */
        post: operations["create_identity_pack_api_avatars__avatar_id__identity_packs_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/assets/uploads": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Initiate Upload */
        post: operations["initiate_upload_api_assets_uploads_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/assets/{asset_id}/finalize": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Finalize Upload */
        post: operations["finalize_upload_api_assets__asset_id__finalize_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/assets": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Assets */
        get: operations["list_assets_api_assets_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/content-items": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Content Items */
        get: operations["list_content_items_api_content_items_get"];
        put?: never;
        /** Create Content Item */
        post: operations["create_content_item_api_content_items_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/content-items/{content_item_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Content Item */
        get: operations["get_content_item_api_content_items__content_item_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/content-items/{content_item_id}/plan": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Plan Content Item */
        post: operations["plan_content_item_api_content_items__content_item_id__plan_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/content-items/{content_item_id}/submit-review": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Submit Content Item For Review */
        post: operations["submit_content_item_for_review_api_content_items__content_item_id__submit_review_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/workflow-presets": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Workflow Presets */
        get: operations["list_workflow_presets_api_workflow_presets_get"];
        put?: never;
        /** Create Workflow Preset */
        post: operations["create_workflow_preset_api_workflow_presets_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/workflow-presets/{workflow_preset_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Workflow Preset */
        get: operations["get_workflow_preset_api_workflow_presets__workflow_preset_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/render-jobs": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Render Jobs */
        get: operations["list_render_jobs_api_render_jobs_get"];
        put?: never;
        /** Create Render Job */
        post: operations["create_render_job_api_render_jobs_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/render-jobs/{render_job_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Render Job */
        get: operations["get_render_job_api_render_jobs__render_job_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/render-jobs/{render_job_id}/cancel": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Cancel Render Job */
        post: operations["cancel_render_job_api_render_jobs__render_job_id__cancel_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/render-jobs/{render_job_id}/retry": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Retry Render Job */
        post: operations["retry_render_job_api_render_jobs__render_job_id__retry_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/render-jobs/{render_job_id}/requeue": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Requeue Render Job */
        post: operations["requeue_render_job_api_render_jobs__render_job_id__requeue_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/render-jobs/{render_job_id}/events": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Stream Render Job Events */
        get: operations["stream_render_job_events_api_render_jobs__render_job_id__events_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/publish-packages": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Publish Packages */
        get: operations["list_publish_packages_api_publish_packages_get"];
        put?: never;
        /** Create Publish Package */
        post: operations["create_publish_package_api_publish_packages_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/publish-packages/{package_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Publish Package */
        get: operations["get_publish_package_api_publish_packages__package_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/publish-packages/{package_id}/cancel": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Cancel Publish Package */
        post: operations["cancel_publish_package_api_publish_packages__package_id__cancel_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/publish-packages/{package_id}/retry": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Retry Publish Package */
        post: operations["retry_publish_package_api_publish_packages__package_id__retry_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/publish-packages/{package_id}/requeue": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Requeue Publish Package */
        post: operations["requeue_publish_package_api_publish_packages__package_id__requeue_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/publish-packages/{package_id}/download": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Publish Package Download */
        get: operations["get_publish_package_download_api_publish_packages__package_id__download_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/review/tasks": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Review Tasks */
        get: operations["list_review_tasks_api_review_tasks_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/review/tasks/{task_id}/approve": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Approve Review Task */
        post: operations["approve_review_task_api_review_tasks__task_id__approve_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/review/tasks/{task_id}/request-rework": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Request Rework */
        post: operations["request_rework_api_review_tasks__task_id__request_rework_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/audit/logs": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Audit Logs */
        get: operations["list_audit_logs_api_audit_logs_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
}
export type webhooks = Record<string, never>;
export interface components {
    schemas: {
        /** AssetFinalizeRequest */
        AssetFinalizeRequest: {
            /** Byte Size */
            byte_size: number;
            /** Checksum Sha256 */
            checksum_sha256?: string | null;
        };
        /** AssetListResponse */
        AssetListResponse: {
            /** Items */
            items: components["schemas"]["AssetRead"][];
        };
        /** AssetRead */
        AssetRead: {
            /** Id */
            id: string;
            /** Brand Id */
            brand_id: string;
            /** Object Key */
            object_key: string;
            /** Filename */
            filename: string;
            /** Content Type */
            content_type: string;
            /** Byte Size */
            byte_size: number | null;
            /** Checksum Sha256 */
            checksum_sha256: string | null;
            status: components["schemas"]["AssetStatus"];
            /**
             * Upload Expires At
             * Format: date-time
             */
            upload_expires_at: string;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /**
             * Updated At
             * Format: date-time
             */
            updated_at: string;
        };
        /**
         * AssetStatus
         * @enum {string}
         */
        AssetStatus: "pending_upload" | "ready" | "failed";
        /** AssetUploadInitiateRequest */
        AssetUploadInitiateRequest: {
            /** Brand Id */
            brand_id: string;
            /** Filename */
            filename: string;
            /** Content Type */
            content_type: string;
            /** Byte Size */
            byte_size?: number | null;
        };
        /** AssetUploadInitiateResponse */
        AssetUploadInitiateResponse: {
            asset: components["schemas"]["AssetRead"];
            upload: components["schemas"]["UploadTargetRead"];
        };
        /** AuditLogListResponse */
        AuditLogListResponse: {
            /** Items */
            items: components["schemas"]["AuditLogRead"][];
        };
        /** AuditLogRead */
        AuditLogRead: {
            /** Id */
            id: string;
            /** Actor User Id */
            actor_user_id: string | null;
            /** Action */
            action: string;
            /** Entity Type */
            entity_type: string;
            /** Entity Id */
            entity_id: string;
            /** Payload */
            payload: {
                [key: string]: unknown;
            };
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
        };
        /** AuthSessionRead */
        AuthSessionRead: {
            user: components["schemas"]["UserRead"];
            /**
             * Expires At
             * Format: date-time
             */
            expires_at: string;
        };
        /** AvatarCreateRequest */
        AvatarCreateRequest: {
            /** Brand Id */
            brand_id: string;
            /** Name */
            name: string;
            /** Persona Notes */
            persona_notes?: string | null;
        };
        /** AvatarListResponse */
        AvatarListResponse: {
            /** Items */
            items: components["schemas"]["AvatarRead"][];
        };
        /** AvatarRead */
        AvatarRead: {
            /** Id */
            id: string;
            /** Brand Id */
            brand_id: string;
            /** Name */
            name: string;
            /** Persona Notes */
            persona_notes: string | null;
            status: components["schemas"]["AvatarStatus"];
            /** Created By User Id */
            created_by_user_id: string;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /**
             * Updated At
             * Format: date-time
             */
            updated_at: string;
        };
        /**
         * AvatarStatus
         * @enum {string}
         */
        AvatarStatus: "draft" | "active";
        /** BootstrapOwnerRequest */
        BootstrapOwnerRequest: {
            /** Email */
            email: string;
            /** Display Name */
            display_name: string;
            /** Password */
            password: string;
        };
        /** BrandCreateRequest */
        BrandCreateRequest: {
            /** Name */
            name: string;
            /** Voice Notes */
            voice_notes?: string | null;
        };
        /** BrandListResponse */
        BrandListResponse: {
            /** Items */
            items: components["schemas"]["BrandRead"][];
        };
        /** BrandRead */
        BrandRead: {
            /** Id */
            id: string;
            /** Name */
            name: string;
            /** Voice Notes */
            voice_notes: string | null;
            /** Created By User Id */
            created_by_user_id: string;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /**
             * Updated At
             * Format: date-time
             */
            updated_at: string;
        };
        /**
         * ContentChannel
         * @enum {string}
         */
        ContentChannel: "instagram_reels" | "youtube_shorts";
        /** ContentItemCreateRequest */
        ContentItemCreateRequest: {
            /** Brand Id */
            brand_id: string;
            /** Avatar Id */
            avatar_id: string;
            /** Title */
            title: string;
            /** Script */
            script: string;
            channel: components["schemas"]["ContentChannel"];
        };
        /** ContentItemListResponse */
        ContentItemListResponse: {
            /** Items */
            items: components["schemas"]["ContentItemRead"][];
        };
        /** ContentItemRead */
        ContentItemRead: {
            /** Id */
            id: string;
            /** Brand Id */
            brand_id: string;
            /** Avatar Id */
            avatar_id: string;
            /** Title */
            title: string;
            /** Script */
            script: string;
            channel: components["schemas"]["ContentChannel"];
            status: components["schemas"]["ContentStatus"];
            /** Planned Publish At */
            planned_publish_at: string | null;
            /** Created By User Id */
            created_by_user_id: string;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /**
             * Updated At
             * Format: date-time
             */
            updated_at: string;
        };
        /** ContentPlanRequest */
        ContentPlanRequest: {
            /** Planned Publish At */
            planned_publish_at?: string | null;
        };
        /**
         * ContentStatus
         * @enum {string}
         */
        ContentStatus: "draft" | "planned" | "review" | "approved" | "rework";
        /** DownloadTargetRead */
        DownloadTargetRead: {
            /** Method */
            method: string;
            /** Url */
            url: string;
            /** Headers */
            headers: {
                [key: string]: string;
            };
            /**
             * Expires At
             * Format: date-time
             */
            expires_at: string;
        };
        /** HTTPValidationError */
        HTTPValidationError: {
            /** Detail */
            detail?: components["schemas"]["ValidationError"][];
        };
        /** IdentityPackCreateRequest */
        IdentityPackCreateRequest: {
            /** Name */
            name: string;
            /** Description */
            description?: string | null;
            /** Storage Prefix */
            storage_prefix: string;
        };
        /** IdentityPackListResponse */
        IdentityPackListResponse: {
            /** Items */
            items: components["schemas"]["IdentityPackRead"][];
        };
        /** IdentityPackRead */
        IdentityPackRead: {
            /** Id */
            id: string;
            /** Avatar Id */
            avatar_id: string;
            /** Name */
            name: string;
            /** Description */
            description: string | null;
            /** Storage Prefix */
            storage_prefix: string;
            status: components["schemas"]["IdentityPackStatus"];
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /**
             * Updated At
             * Format: date-time
             */
            updated_at: string;
        };
        /**
         * IdentityPackStatus
         * @enum {string}
         */
        IdentityPackStatus: "draft" | "ready";
        /** InviteAcceptRequest */
        InviteAcceptRequest: {
            /** Token */
            token: string;
            /** Email */
            email: string;
            /** Display Name */
            display_name: string;
            /** Password */
            password: string;
        };
        /** InviteCreateRequest */
        InviteCreateRequest: {
            /** Email */
            email: string;
            role: components["schemas"]["UserRole"];
        };
        /** InviteCreateResponse */
        InviteCreateResponse: {
            /** Invite Id */
            invite_id: string;
            /** Email */
            email: string;
            role: components["schemas"]["UserRole"];
            /** Token */
            token: string;
            /**
             * Expires At
             * Format: date-time
             */
            expires_at: string;
        };
        /** JobAttemptRead */
        JobAttemptRead: {
            /** Id */
            id: string;
            /** Render Job Id */
            render_job_id: string;
            /** Attempt Number */
            attempt_number: number;
            status: components["schemas"]["JobAttemptStatus"];
            /** Provider Job Id */
            provider_job_id: string | null;
            /** Request Payload */
            request_payload: {
                [key: string]: unknown;
            };
            /** Response Payload */
            response_payload: {
                [key: string]: unknown;
            };
            /** Error Message */
            error_message: string | null;
            /** Started At */
            started_at: string | null;
            /** Finished At */
            finished_at: string | null;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /**
             * Updated At
             * Format: date-time
             */
            updated_at: string;
        };
        /**
         * JobAttemptStatus
         * @enum {string}
         */
        JobAttemptStatus: "queued" | "running" | "succeeded" | "failed" | "cancelled";
        /** LoginRequest */
        LoginRequest: {
            /** Email */
            email: string;
            /** Password */
            password: string;
        };
        /**
         * OutputArtifactType
         * @enum {string}
         */
        OutputArtifactType: "video" | "cover_image" | "caption_text" | "manifest";
        /**
         * PackagingProvider
         * @enum {string}
         */
        PackagingProvider: "ffmpeg";
        /** PublishPackageCreateRequest */
        PublishPackageCreateRequest: {
            /** Render Job Id */
            render_job_id: string;
        };
        /** PublishPackageDownloadResponse */
        PublishPackageDownloadResponse: {
            package: components["schemas"]["PublishPackageRead"];
            download: components["schemas"]["DownloadTargetRead"];
        };
        /** PublishPackageListResponse */
        PublishPackageListResponse: {
            /** Items */
            items: components["schemas"]["PublishPackageRead"][];
        };
        /** PublishPackageRead */
        PublishPackageRead: {
            /** Id */
            id: string;
            /** Render Job Id */
            render_job_id: string;
            /** Content Item Id */
            content_item_id: string;
            status: components["schemas"]["PublishPackageStatus"];
            /** Package Object Key */
            package_object_key: string | null;
            /** Manifest Payload */
            manifest_payload: {
                [key: string]: unknown;
            };
            /** Byte Size */
            byte_size: number | null;
            /** Error Message */
            error_message: string | null;
            /** Created By User Id */
            created_by_user_id: string;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /**
             * Updated At
             * Format: date-time
             */
            updated_at: string;
        };
        /**
         * PublishPackageStatus
         * @enum {string}
         */
        PublishPackageStatus: "queued" | "running" | "ready" | "failed" | "cancelled";
        /** RenderJobCreateRequest */
        RenderJobCreateRequest: {
            /** Content Item Id */
            content_item_id: string;
            /** Workflow Preset Id */
            workflow_preset_id: string;
            /** Identity Pack Id */
            identity_pack_id?: string | null;
            /**
             * Retry Budget
             * @default 3
             */
            retry_budget: number;
        };
        /** RenderJobListResponse */
        RenderJobListResponse: {
            /** Items */
            items: components["schemas"]["RenderJobRead"][];
        };
        /** RenderJobRead */
        RenderJobRead: {
            /** Id */
            id: string;
            /** Content Item Id */
            content_item_id: string;
            /** Workflow Preset Id */
            workflow_preset_id: string;
            /** Workflow Preset Key */
            workflow_preset_key: string;
            /** Workflow Preset Version */
            workflow_preset_version: number;
            workflow_provider: components["schemas"]["WorkflowProvider"];
            voice_provider: components["schemas"]["VoiceProvider"];
            packaging_provider: components["schemas"]["PackagingProvider"];
            /** Input Snapshot */
            input_snapshot: {
                [key: string]: unknown;
            };
            status: components["schemas"]["RenderJobStatus"];
            /** Retry Budget */
            retry_budget: number;
            /** Created By User Id */
            created_by_user_id: string;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /**
             * Updated At
             * Format: date-time
             */
            updated_at: string;
            /** Attempts */
            attempts: components["schemas"]["JobAttemptRead"][];
        };
        /**
         * RenderJobStatus
         * @enum {string}
         */
        RenderJobStatus: "queued" | "running" | "succeeded" | "failed" | "cancelled";
        /** ReviewDecisionRequest */
        ReviewDecisionRequest: {
            /** Decision Notes */
            decision_notes?: string | null;
        };
        /** ReviewTaskListResponse */
        ReviewTaskListResponse: {
            /** Items */
            items: components["schemas"]["ReviewTaskRead"][];
        };
        /** ReviewTaskRead */
        ReviewTaskRead: {
            /** Id */
            id: string;
            /** Content Item Id */
            content_item_id: string;
            /** Assigned To User Id */
            assigned_to_user_id: string | null;
            status: components["schemas"]["ReviewTaskStatus"];
            /** Decision Notes */
            decision_notes: string | null;
            /** Completed At */
            completed_at: string | null;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /**
             * Updated At
             * Format: date-time
             */
            updated_at: string;
        };
        /**
         * ReviewTaskStatus
         * @enum {string}
         */
        ReviewTaskStatus: "open" | "approved" | "rework" | "cancelled";
        /** StatusResponse */
        StatusResponse: {
            /** Status */
            status: string;
        };
        /** UploadTargetRead */
        UploadTargetRead: {
            /** Method */
            method: string;
            /** Url */
            url: string;
            /** Headers */
            headers: {
                [key: string]: string;
            };
            /**
             * Expires At
             * Format: date-time
             */
            expires_at: string;
        };
        /** UserListResponse */
        UserListResponse: {
            /** Items */
            items: components["schemas"]["UserRead"][];
        };
        /** UserRead */
        UserRead: {
            /** Id */
            id: string;
            /** Email */
            email: string;
            /** Display Name */
            display_name: string;
            role: components["schemas"]["UserRole"];
            status: components["schemas"]["UserStatus"];
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
        };
        /**
         * UserRole
         * @enum {string}
         */
        UserRole: "owner" | "operator" | "reviewer" | "viewer";
        /**
         * UserStatus
         * @enum {string}
         */
        UserStatus: "active" | "disabled";
        /** ValidationError */
        ValidationError: {
            /** Location */
            loc: (string | number)[];
            /** Message */
            msg: string;
            /** Error Type */
            type: string;
            /** Input */
            input?: unknown;
            /** Context */
            ctx?: Record<string, never>;
        };
        /**
         * VoiceProvider
         * @enum {string}
         */
        VoiceProvider: "none";
        /** WorkflowInputBinding */
        WorkflowInputBinding: {
            source_type: components["schemas"]["WorkflowInputSourceType"];
            /** Source Field */
            source_field?: string | null;
            /** Value */
            value?: unknown | null;
        };
        /**
         * WorkflowInputSourceType
         * @enum {string}
         */
        WorkflowInputSourceType: "content_item" | "brand" | "avatar" | "identity_pack" | "literal";
        /** WorkflowOutputBinding */
        WorkflowOutputBinding: {
            artifact_type: components["schemas"]["OutputArtifactType"];
            /** Output Path */
            output_path: string;
        };
        /** WorkflowPresetCreateRequest */
        WorkflowPresetCreateRequest: {
            /** Key */
            key: string;
            /** Name */
            name: string;
            /** Description */
            description?: string | null;
            workflow_provider: components["schemas"]["WorkflowProvider"];
            voice_provider: components["schemas"]["VoiceProvider"];
            packaging_provider: components["schemas"]["PackagingProvider"];
            /** Workflow Definition */
            workflow_definition: {
                [key: string]: unknown;
            };
            /** Input Mapping */
            input_mapping: {
                [key: string]: components["schemas"]["WorkflowInputBinding"];
            };
            /** Output Mapping */
            output_mapping: {
                [key: string]: components["schemas"]["WorkflowOutputBinding"];
            };
        };
        /** WorkflowPresetListResponse */
        WorkflowPresetListResponse: {
            /** Items */
            items: components["schemas"]["WorkflowPresetRead"][];
        };
        /** WorkflowPresetRead */
        WorkflowPresetRead: {
            /** Id */
            id: string;
            /** Key */
            key: string;
            /** Version */
            version: number;
            /** Name */
            name: string;
            /** Description */
            description: string | null;
            workflow_provider: components["schemas"]["WorkflowProvider"];
            voice_provider: components["schemas"]["VoiceProvider"];
            packaging_provider: components["schemas"]["PackagingProvider"];
            /** Workflow Definition */
            workflow_definition: {
                [key: string]: unknown;
            };
            /** Input Mapping */
            input_mapping: {
                [key: string]: components["schemas"]["WorkflowInputBinding"];
            };
            /** Output Mapping */
            output_mapping: {
                [key: string]: components["schemas"]["WorkflowOutputBinding"];
            };
            /** Created By User Id */
            created_by_user_id: string;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /**
             * Updated At
             * Format: date-time
             */
            updated_at: string;
        };
        /**
         * WorkflowProvider
         * @enum {string}
         */
        WorkflowProvider: "comfyui";
    };
    responses: never;
    parameters: never;
    requestBodies: never;
    headers: never;
    pathItems: never;
}
export type $defs = Record<string, never>;
export interface operations {
    root__get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": {
                        [key: string]: string;
                    };
                };
            };
        };
    };
    meta_api_meta_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": {
                        [key: string]: string;
                    };
                };
            };
        };
    };
    live_health_live_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": {
                        [key: string]: string;
                    };
                };
            };
        };
    };
    ready_health_ready_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": {
                        [key: string]: unknown;
                    };
                };
            };
        };
    };
    bootstrap_owner_api_auth_bootstrap_owner_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["BootstrapOwnerRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AuthSessionRead"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    create_invite_api_auth_invites_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: {
                cf_session?: string | null;
            };
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["InviteCreateRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["InviteCreateResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    accept_invite_api_auth_invites_accept_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["InviteAcceptRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AuthSessionRead"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    login_api_auth_login_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["LoginRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AuthSessionRead"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    logout_api_auth_logout_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: {
                cf_session?: string | null;
            };
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["StatusResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    get_session_api_auth_session_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: {
                cf_session?: string | null;
            };
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AuthSessionRead"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    get_me_api_users_me_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: {
                cf_session?: string | null;
            };
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["UserRead"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_users_api_users_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: {
                cf_session?: string | null;
            };
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["UserListResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_brands_api_brands_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: {
                cf_session?: string | null;
            };
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["BrandListResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    create_brand_api_brands_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: {
                cf_session?: string | null;
            };
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["BrandCreateRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["BrandRead"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    get_brand_api_brands__brand_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                brand_id: string;
            };
            cookie?: {
                cf_session?: string | null;
            };
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["BrandRead"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_avatars_api_avatars_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: {
                cf_session?: string | null;
            };
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AvatarListResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    create_avatar_api_avatars_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: {
                cf_session?: string | null;
            };
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["AvatarCreateRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AvatarRead"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_identity_packs_api_avatars__avatar_id__identity_packs_get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                avatar_id: string;
            };
            cookie?: {
                cf_session?: string | null;
            };
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["IdentityPackListResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    create_identity_pack_api_avatars__avatar_id__identity_packs_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                avatar_id: string;
            };
            cookie?: {
                cf_session?: string | null;
            };
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["IdentityPackCreateRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["IdentityPackRead"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    initiate_upload_api_assets_uploads_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: {
                cf_session?: string | null;
            };
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["AssetUploadInitiateRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AssetUploadInitiateResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    finalize_upload_api_assets__asset_id__finalize_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                asset_id: string;
            };
            cookie?: {
                cf_session?: string | null;
            };
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["AssetFinalizeRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AssetRead"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_assets_api_assets_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: {
                cf_session?: string | null;
            };
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AssetListResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_content_items_api_content_items_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: {
                cf_session?: string | null;
            };
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ContentItemListResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    create_content_item_api_content_items_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: {
                cf_session?: string | null;
            };
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ContentItemCreateRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ContentItemRead"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    get_content_item_api_content_items__content_item_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                content_item_id: string;
            };
            cookie?: {
                cf_session?: string | null;
            };
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ContentItemRead"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    plan_content_item_api_content_items__content_item_id__plan_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                content_item_id: string;
            };
            cookie?: {
                cf_session?: string | null;
            };
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ContentPlanRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ContentItemRead"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    submit_content_item_for_review_api_content_items__content_item_id__submit_review_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                content_item_id: string;
            };
            cookie?: {
                cf_session?: string | null;
            };
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ReviewTaskRead"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_workflow_presets_api_workflow_presets_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: {
                cf_session?: string | null;
            };
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["WorkflowPresetListResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    create_workflow_preset_api_workflow_presets_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: {
                cf_session?: string | null;
            };
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["WorkflowPresetCreateRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["WorkflowPresetRead"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    get_workflow_preset_api_workflow_presets__workflow_preset_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                workflow_preset_id: string;
            };
            cookie?: {
                cf_session?: string | null;
            };
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["WorkflowPresetRead"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_render_jobs_api_render_jobs_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: {
                cf_session?: string | null;
            };
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["RenderJobListResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    create_render_job_api_render_jobs_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: {
                cf_session?: string | null;
            };
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["RenderJobCreateRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["RenderJobRead"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    get_render_job_api_render_jobs__render_job_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                render_job_id: string;
            };
            cookie?: {
                cf_session?: string | null;
            };
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["RenderJobRead"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    cancel_render_job_api_render_jobs__render_job_id__cancel_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                render_job_id: string;
            };
            cookie?: {
                cf_session?: string | null;
            };
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["RenderJobRead"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    retry_render_job_api_render_jobs__render_job_id__retry_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                render_job_id: string;
            };
            cookie?: {
                cf_session?: string | null;
            };
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["RenderJobRead"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    requeue_render_job_api_render_jobs__render_job_id__requeue_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                render_job_id: string;
            };
            cookie?: {
                cf_session?: string | null;
            };
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["RenderJobRead"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    stream_render_job_events_api_render_jobs__render_job_id__events_get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                render_job_id: string;
            };
            cookie?: {
                cf_session?: string | null;
            };
        };
        requestBody?: never;
        responses: {
            /** @description Server-sent render job status snapshots. */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "text/event-stream": string;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_publish_packages_api_publish_packages_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: {
                cf_session?: string | null;
            };
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PublishPackageListResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    create_publish_package_api_publish_packages_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: {
                cf_session?: string | null;
            };
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["PublishPackageCreateRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PublishPackageRead"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    get_publish_package_api_publish_packages__package_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                package_id: string;
            };
            cookie?: {
                cf_session?: string | null;
            };
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PublishPackageRead"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    cancel_publish_package_api_publish_packages__package_id__cancel_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                package_id: string;
            };
            cookie?: {
                cf_session?: string | null;
            };
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PublishPackageRead"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    retry_publish_package_api_publish_packages__package_id__retry_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                package_id: string;
            };
            cookie?: {
                cf_session?: string | null;
            };
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PublishPackageRead"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    requeue_publish_package_api_publish_packages__package_id__requeue_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                package_id: string;
            };
            cookie?: {
                cf_session?: string | null;
            };
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PublishPackageRead"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    get_publish_package_download_api_publish_packages__package_id__download_get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                package_id: string;
            };
            cookie?: {
                cf_session?: string | null;
            };
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PublishPackageDownloadResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_review_tasks_api_review_tasks_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: {
                cf_session?: string | null;
            };
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ReviewTaskListResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    approve_review_task_api_review_tasks__task_id__approve_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                task_id: string;
            };
            cookie?: {
                cf_session?: string | null;
            };
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ReviewDecisionRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ReviewTaskRead"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    request_rework_api_review_tasks__task_id__request_rework_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                task_id: string;
            };
            cookie?: {
                cf_session?: string | null;
            };
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ReviewDecisionRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ReviewTaskRead"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_audit_logs_api_audit_logs_get: {
        parameters: {
            query?: {
                limit?: number;
            };
            header?: never;
            path?: never;
            cookie?: {
                cf_session?: string | null;
            };
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AuditLogListResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
}

```