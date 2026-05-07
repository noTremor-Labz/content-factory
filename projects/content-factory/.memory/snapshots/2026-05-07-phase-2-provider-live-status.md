Project Path: content-factory

Source Tree:

```txt
content-factory
├── apps
│   ├── api
│   │   ├── src
│   │   │   └── content_factory_api
│   │   │       └── modules
│   │   │           ├── render.py
│   │   │           └── schemas.py
│   │   └── tests
│   │       ├── test_openapi.py
│   │       └── test_render_contracts.py
│   ├── web
│   │   └── src
│   │       ├── app
│   │       │   ├── App.css
│   │       │   ├── App.test.tsx
│   │       │   ├── App.tsx
│   │       │   └── routes.ts
│   │       ├── features
│   │       │   └── render
│   │       │       └── RenderPanel.tsx
│   │       └── shared
│   │           └── api
│   │               ├── client.ts
│   │               └── types.ts
│   └── worker
│       ├── src
│       │   └── content_factory_worker
│       │       ├── config.py
│       │       ├── executors
│       │       │   ├── __init__.py
│       │       │   └── comfyui.py
│       │       ├── jobs
│       │       │   └── render.py
│       │       └── queue.py
│       └── tests
│           ├── test_comfyui_executor.py
│           └── test_worker_config.py
└── pyproject.toml

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
    attempts = list(
        db_session.scalars(
            select(JobAttempt)
            .where(JobAttempt.render_job_id == render_job.id)
            .order_by(JobAttempt.attempt_number.asc())
        )
    )
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

`apps/api/src/content_factory_api/modules/schemas.py`:

```py
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from content_factory_api.modules.domain import (
    AssetStatus,
    AvatarStatus,
    ContentChannel,
    ContentStatus,
    IdentityPackStatus,
    JobAttemptStatus,
    OutputArtifactType,
    PackagingProvider,
    RenderJobStatus,
    ReviewTaskStatus,
    UserRole,
    UserStatus,
    VoiceProvider,
    WorkflowInputSourceType,
    WorkflowProvider,
)


def normalize_email(value: str) -> str:
    normalized = value.strip().lower()
    if "@" not in normalized or normalized.startswith("@") or normalized.endswith("@"):
        raise ValueError("email must be a valid address")
    return normalized


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    display_name: str
    role: UserRole
    status: UserStatus
    created_at: datetime


class UserListResponse(BaseModel):
    items: list[UserRead]


class BootstrapOwnerRequest(BaseModel):
    email: str
    display_name: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=8, max_length=255)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        return normalize_email(value)


class LoginRequest(BaseModel):
    email: str
    password: str = Field(min_length=1, max_length=255)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        return normalize_email(value)


class InviteCreateRequest(BaseModel):
    email: str
    role: UserRole

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        return normalize_email(value)


class InviteCreateResponse(BaseModel):
    invite_id: str
    email: str
    role: UserRole
    token: str
    expires_at: datetime


class InviteAcceptRequest(BaseModel):
    token: str = Field(min_length=16)
    email: str
    display_name: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=8, max_length=255)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        return normalize_email(value)


class AuthSessionRead(BaseModel):
    user: UserRead
    expires_at: datetime


class StatusResponse(BaseModel):
    status: str


class BrandCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    voice_notes: str | None = Field(default=None, max_length=10_000)


class BrandRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    voice_notes: str | None
    created_by_user_id: str
    created_at: datetime
    updated_at: datetime


class BrandListResponse(BaseModel):
    items: list[BrandRead]


class AvatarCreateRequest(BaseModel):
    brand_id: str
    name: str = Field(min_length=1, max_length=255)
    persona_notes: str | None = Field(default=None, max_length=10_000)


class AvatarRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    brand_id: str
    name: str
    persona_notes: str | None
    status: AvatarStatus
    created_by_user_id: str
    created_at: datetime
    updated_at: datetime


class AvatarListResponse(BaseModel):
    items: list[AvatarRead]


class IdentityPackCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=10_000)
    storage_prefix: str = Field(min_length=1, max_length=500)


class IdentityPackRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    avatar_id: str
    name: str
    description: str | None
    storage_prefix: str
    status: IdentityPackStatus
    created_at: datetime
    updated_at: datetime


class IdentityPackListResponse(BaseModel):
    items: list[IdentityPackRead]


class AssetUploadInitiateRequest(BaseModel):
    brand_id: str
    filename: str = Field(min_length=1, max_length=255)
    content_type: str = Field(min_length=1, max_length=255)
    byte_size: int | None = Field(default=None, gt=0)


class AssetFinalizeRequest(BaseModel):
    byte_size: int = Field(gt=0)
    checksum_sha256: str | None = Field(default=None, min_length=64, max_length=64)


class AssetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    brand_id: str
    object_key: str
    filename: str
    content_type: str
    byte_size: int | None
    checksum_sha256: str | None
    status: AssetStatus
    upload_expires_at: datetime
    created_at: datetime
    updated_at: datetime


class UploadTargetRead(BaseModel):
    method: str
    url: str
    headers: dict[str, str]
    expires_at: datetime


class AssetUploadInitiateResponse(BaseModel):
    asset: AssetRead
    upload: UploadTargetRead


class AssetListResponse(BaseModel):
    items: list[AssetRead]


class ContentItemCreateRequest(BaseModel):
    brand_id: str
    avatar_id: str
    title: str = Field(min_length=1, max_length=255)
    script: str = Field(min_length=1, max_length=20_000)
    channel: ContentChannel


class ContentPlanRequest(BaseModel):
    planned_publish_at: datetime | None = None


class WorkflowInputBinding(BaseModel):
    source_type: WorkflowInputSourceType
    source_field: str | None = Field(default=None, min_length=1, max_length=255)
    value: Any | None = None

    @model_validator(mode="after")
    def validate_binding(self) -> "WorkflowInputBinding":
        if self.source_type == WorkflowInputSourceType.LITERAL:
            if self.source_field is not None:
                raise ValueError("Literal workflow input bindings cannot define source_field")
            if self.value is None:
                raise ValueError("Literal workflow input bindings require value")
            return self

        if self.source_field is None:
            raise ValueError("Workflow input binding requires source_field")
        if self.value is not None:
            raise ValueError("Only literal workflow input bindings may define value")
        return self


class WorkflowOutputBinding(BaseModel):
    artifact_type: OutputArtifactType
    output_path: str = Field(min_length=1, max_length=255)


class WorkflowPresetCreateRequest(BaseModel):
    key: str = Field(
        min_length=3,
        max_length=120,
        pattern=r"^[a-z0-9]+(?:[-_][a-z0-9]+)*$",
    )
    name: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=10_000)
    workflow_provider: WorkflowProvider
    voice_provider: VoiceProvider
    packaging_provider: PackagingProvider
    workflow_definition: dict[str, Any] = Field(min_length=1)
    input_mapping: dict[str, WorkflowInputBinding] = Field(min_length=1)
    output_mapping: dict[str, WorkflowOutputBinding] = Field(min_length=1)


class WorkflowPresetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    key: str
    version: int
    name: str
    description: str | None
    workflow_provider: WorkflowProvider
    voice_provider: VoiceProvider
    packaging_provider: PackagingProvider
    workflow_definition: dict[str, Any]
    input_mapping: dict[str, WorkflowInputBinding]
    output_mapping: dict[str, WorkflowOutputBinding]
    created_by_user_id: str
    created_at: datetime
    updated_at: datetime


class WorkflowPresetListResponse(BaseModel):
    items: list[WorkflowPresetRead]


class ContentItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    brand_id: str
    avatar_id: str
    title: str
    script: str
    channel: ContentChannel
    status: ContentStatus
    planned_publish_at: datetime | None
    created_by_user_id: str
    created_at: datetime
    updated_at: datetime


class ContentItemListResponse(BaseModel):
    items: list[ContentItemRead]


class JobAttemptRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    render_job_id: str
    attempt_number: int
    status: JobAttemptStatus
    provider_job_id: str | None
    request_payload: dict[str, Any]
    response_payload: dict[str, Any]
    error_message: str | None
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime
    updated_at: datetime


class RenderJobCreateRequest(BaseModel):
    content_item_id: str
    workflow_preset_id: str
    identity_pack_id: str | None = None
    retry_budget: int = Field(default=3, ge=1, le=5)


class RenderJobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    content_item_id: str
    workflow_preset_id: str
    workflow_preset_key: str
    workflow_preset_version: int
    workflow_provider: WorkflowProvider
    voice_provider: VoiceProvider
    packaging_provider: PackagingProvider
    input_snapshot: dict[str, Any]
    status: RenderJobStatus
    retry_budget: int
    created_by_user_id: str
    created_at: datetime
    updated_at: datetime
    attempts: list[JobAttemptRead]


class RenderJobListResponse(BaseModel):
    items: list[RenderJobRead]


class RenderJobStatusEvent(BaseModel):
    event: Literal["render_job.snapshot"] = "render_job.snapshot"
    render_job: RenderJobRead


class ReviewTaskRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    content_item_id: str
    assigned_to_user_id: str | None
    status: ReviewTaskStatus
    decision_notes: str | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class ReviewTaskListResponse(BaseModel):
    items: list[ReviewTaskRead]


class ReviewDecisionRequest(BaseModel):
    decision_notes: str | None = Field(default=None, max_length=10_000)


class AuditLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    actor_user_id: str | None
    action: str
    entity_type: str
    entity_id: str
    payload: dict[str, Any]
    created_at: datetime


class AuditLogListResponse(BaseModel):
    items: list[AuditLogRead]

```

`apps/api/tests/test_openapi.py`:

```py
import json
from pathlib import Path

from content_factory_api.export_openapi import export_openapi_schema


def test_export_openapi_schema_includes_health_routes(tmp_path: Path) -> None:
    output_path = export_openapi_schema(tmp_path / "openapi.json")
    schema = json.loads(output_path.read_text(encoding="utf-8"))

    assert output_path.exists()
    assert "/health/live" in schema["paths"]
    assert "/health/ready" in schema["paths"]
    assert "/api/auth/login" in schema["paths"]
    assert "/api/workflow-presets" in schema["paths"]
    assert "/api/render-jobs" in schema["paths"]
    assert "/api/render-jobs/{render_job_id}/events" in schema["paths"]
    assert "/api/content-items/{content_item_id}/submit-review" in schema["paths"]
    assert "/api/review/tasks/{task_id}/approve" in schema["paths"]

```

`apps/api/tests/test_render_contracts.py`:

```py
import json

from fastapi.testclient import TestClient

from content_factory_api.database import get_sessionmaker
from content_factory_api.modules.domain import RenderJobStatus
from content_factory_api.modules.models import RenderJob


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

```

`apps/web/src/app/App.css`:

```css
:root {
  color: #1f2933;
  background:
    radial-gradient(circle at top left, rgba(255, 205, 148, 0.42), transparent 32%),
    radial-gradient(circle at top right, rgba(120, 193, 255, 0.24), transparent 28%),
    linear-gradient(180deg, #fff8ef 0%, #f4f0ea 44%, #e7edf2 100%);
  font-family: "Avenir Next", "IBM Plex Sans", "Segoe UI", sans-serif;
  line-height: 1.5;
  font-weight: 400;

  --text-primary: #1f2933;
  --text-secondary: #52606d;
  --text-muted: #7b8794;
  --surface: rgba(255, 255, 255, 0.84);
  --surface-strong: rgba(255, 255, 255, 0.93);
  --border: rgba(31, 41, 51, 0.11);
  --shadow: 0 24px 60px rgba(15, 23, 42, 0.11);
  --accent: #b54708;
  --accent-deep: #7c2d12;
  --accent-soft: #fef3c7;
  --success: #166534;
  --success-soft: #dcfce7;
  --danger: #991b1b;
  --danger-soft: #fee2e2;
  --info: #0f4c81;
  --info-soft: #dbeafe;
}

* {
  box-sizing: border-box;
}

body {
  margin: 0;
  min-width: 320px;
}

button,
input,
select,
textarea {
  font: inherit;
}

button {
  cursor: pointer;
}

input,
select,
textarea {
  width: 100%;
  border: 1px solid rgba(82, 96, 109, 0.18);
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.9);
  color: var(--text-primary);
  padding: 0.85rem 1rem;
}

textarea {
  resize: vertical;
}

input:focus,
select:focus,
textarea:focus,
button:focus-visible {
  outline: 2px solid rgba(181, 71, 8, 0.22);
  outline-offset: 2px;
}

#root {
  min-height: 100vh;
}

.shell {
  min-height: 100vh;
  padding: 1.5rem;
}

.surface {
  border: 1px solid var(--border);
  border-radius: 28px;
  background: var(--surface);
  box-shadow: var(--shadow);
  backdrop-filter: blur(18px);
}

.hero,
.summary-grid,
.workspace-grid,
.auth-layout,
.loading-card {
  margin: 0 auto;
  max-width: 1240px;
}

.hero {
  display: grid;
  gap: 1.5rem;
  padding: 1.75rem;
}

.hero h1,
.auth-hero h1,
.loading-card h1 {
  margin: 0;
  font-family: "Iowan Old Style", "Palatino Linotype", "Book Antiqua", serif;
  font-size: clamp(2.7rem, 6vw, 5rem);
  line-height: 0.93;
  letter-spacing: -0.04em;
}

.eyebrow {
  margin: 0 0 0.85rem;
  color: var(--accent);
  font-size: 0.78rem;
  font-weight: 700;
  letter-spacing: 0.18em;
  text-transform: uppercase;
}

.lede,
.panel-copy,
.meta-copy,
.session-card p,
.list-card p,
.empty-state {
  color: var(--text-secondary);
}

.lede {
  margin: 1rem 0 0;
  max-width: 42rem;
  font-size: 1.05rem;
}

.hero-side {
  display: grid;
  gap: 1rem;
}

.session-card {
  border: 1px solid rgba(31, 41, 51, 0.08);
  border-radius: 24px;
  background: var(--surface-strong);
  padding: 1.1rem 1.2rem;
}

.session-card strong {
  display: block;
  margin-top: 0.2rem;
  font-size: 1.1rem;
}

.meta-label {
  display: block;
  color: var(--text-muted);
  font-size: 0.78rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.summary-grid,
.panel-grid,
.workspace-grid,
.auth-layout {
  display: grid;
  gap: 1rem;
}

.summary-grid {
  margin-top: 1rem;
}

.metric-card,
.nav-card,
.panel-stack,
.auth-card,
.auth-hero,
.loading-card {
  padding: 1.25rem;
}

.metric-card strong {
  display: block;
  margin-top: 0.5rem;
  font-size: 2.4rem;
  line-height: 1;
}

.metric-label {
  color: var(--text-muted);
  font-size: 0.8rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.banner {
  margin: 1rem auto 0;
  max-width: 1240px;
  border-radius: 18px;
  padding: 0.95rem 1rem;
  font-weight: 600;
}

.banner.error {
  background: var(--danger-soft);
  color: var(--danger);
}

.banner.success {
  background: var(--success-soft);
  color: var(--success);
}

.banner.info {
  background: var(--info-soft);
  color: var(--info);
}

.workspace-grid {
  margin-top: 1rem;
}

.nav-card {
  display: flex;
  gap: 0.65rem;
  overflow-x: auto;
}

.nav-link,
.tab,
.ghost-button,
.secondary-button,
.primary-button {
  border: 0;
  border-radius: 999px;
  padding: 0.8rem 1.05rem;
  transition:
    transform 140ms ease,
    background-color 140ms ease,
    color 140ms ease;
}

.nav-link,
.tab,
.ghost-button,
.secondary-button {
  background: rgba(255, 255, 255, 0.76);
  color: var(--text-primary);
}

.nav-link.active,
.tab.active,
.primary-button {
  background: linear-gradient(135deg, #b54708 0%, #7c2d12 100%);
  color: #fff9f2;
}

.nav-link:hover,
.tab:hover,
.ghost-button:hover,
.secondary-button:hover,
.primary-button:hover {
  transform: translateY(-1px);
}

.workspace-panel {
  min-width: 0;
}

.panel-stack {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.panel-header,
.list-card-header,
.meta-list,
.tab-row,
.inline-action-row,
.tag-row {
  display: flex;
  gap: 0.75rem;
}

.panel-header,
.list-card-header {
  align-items: flex-start;
  justify-content: space-between;
}

.panel-header h2,
.auth-card h2,
.list-card h3 {
  margin: 0;
}

.count-pill,
.status-badge,
.tag {
  border-radius: 999px;
  padding: 0.35rem 0.7rem;
  font-size: 0.78rem;
  font-weight: 700;
  text-transform: uppercase;
}

.count-pill {
  background: rgba(181, 71, 8, 0.12);
  color: var(--accent-deep);
}

.status-badge,
.tag {
  background: rgba(15, 76, 129, 0.11);
  color: var(--info);
}

.status-badge.neutral {
  background: rgba(82, 96, 109, 0.14);
  color: var(--text-secondary);
}

.stack-form {
  display: grid;
  gap: 0.9rem;
}

.stack-form label,
.compact-field {
  display: grid;
  gap: 0.45rem;
}

.stack-form label span,
.compact-field span,
.meta-list dt {
  color: var(--text-muted);
  font-size: 0.82rem;
  font-weight: 700;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}

.list-stack {
  display: grid;
  gap: 0.85rem;
}

.list-card {
  border: 1px solid rgba(31, 41, 51, 0.08);
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.92);
  padding: 1rem 1.05rem;
}

.list-card h3 {
  margin: 0;
  font-size: 1.02rem;
}

.list-card p,
.session-card p,
.panel-copy,
.empty-state {
  margin: 0;
}

.json-preview {
  max-height: 220px;
  overflow: auto;
  border: 1px solid rgba(82, 96, 109, 0.14);
  border-radius: 18px;
  background: rgba(31, 41, 51, 0.04);
  color: var(--text-primary);
  font-size: 0.82rem;
  margin: 0.85rem 0 0;
  padding: 0.85rem;
  white-space: pre-wrap;
}

.empty-state {
  border: 1px dashed rgba(82, 96, 109, 0.22);
  border-radius: 22px;
  padding: 1rem;
}

.meta-list {
  flex-wrap: wrap;
  margin: 1.4rem 0 0;
  padding: 0;
}

.meta-list div {
  min-width: 210px;
}

.meta-list dd {
  margin: 0.25rem 0 0;
  color: var(--text-primary);
  font-weight: 700;
}

.auth-layout {
  align-items: start;
}

.auth-card {
  min-width: 0;
}

.tab-row {
  flex-wrap: wrap;
}

.loading-shell {
  min-height: 100vh;
  display: grid;
  place-items: center;
  padding: 1.5rem;
}

.loading-card {
  max-width: 720px;
}

.two-up {
  grid-template-columns: minmax(0, 1fr);
}

@media (min-width: 820px) {
  .shell {
    padding: 2rem;
  }

  .hero {
    grid-template-columns: minmax(0, 1.7fr) minmax(280px, 0.9fr);
    padding: 2rem;
  }

  .summary-grid {
    grid-template-columns: repeat(4, minmax(0, 1fr));
  }

  .workspace-grid {
    grid-template-columns: 240px minmax(0, 1fr);
    align-items: start;
  }

  .nav-card {
    position: sticky;
    top: 1.5rem;
    flex-direction: column;
  }

  .auth-layout {
    grid-template-columns: minmax(0, 1.2fr) minmax(360px, 0.9fr);
  }

  .two-up {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

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
    ] =
      await Promise.all([
        apiClient.listBrands(),
        apiClient.listAvatars(),
        apiClient.listAssets(),
        apiClient.listContentItems(),
        apiClient.listReviewTasks(),
        apiClient.listWorkflowPresets(),
        apiClient.listRenderJobs(),
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
              onSelectRenderJob={setLiveRenderJobId}
              renderJobs={cockpitData.renderJobs}
              workflowPresets={cockpitData.workflowPresets}
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

`apps/web/src/app/routes.ts`:

```ts
export const cockpitRoutes = [
  { id: "overview", label: "Overview" },
  { id: "brands-assets", label: "Brands & Assets" },
  { id: "avatars", label: "Avatars" },
  { id: "content", label: "Content" },
  { id: "review", label: "Review" },
  { id: "render", label: "Render" },
  { id: "audit", label: "Audit" },
] as const;

export type CockpitRouteId = (typeof cockpitRoutes)[number]["id"];

const cockpitRouteIds = new Set<CockpitRouteId>(cockpitRoutes.map((route) => route.id));

export function normalizeCockpitRoute(value: string | null | undefined): CockpitRouteId {
  if (value && cockpitRouteIds.has(value as CockpitRouteId)) {
    return value as CockpitRouteId;
  }

  return "overview";
}

export function toCockpitHash(route: CockpitRouteId): string {
  return `#${route}`;
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
  onSelectRenderJob: (renderJobId: string | null) => void;
}

const renderableStatuses = new Set(["planned", "review", "approved", "rework"]);

export function RenderPanel({
  contentItems,
  identityPacks,
  renderJobs,
  workflowPresets,
  canMutate,
  busy,
  onCreateRenderJob,
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
  renderJobEventsUrl(renderJobId: string) {
    return resolveApiUrl(`/api/render-jobs/${renderJobId}/events`);
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

`apps/web/src/shared/api/types.ts`:

```ts
import type { components } from "@content-factory/contracts";

export type User = components["schemas"]["UserRead"];
export type UserRole = User["role"];
export type AuthSession = components["schemas"]["AuthSessionRead"];
export type Brand = components["schemas"]["BrandRead"];
export type Avatar = components["schemas"]["AvatarRead"];
export type IdentityPack = components["schemas"]["IdentityPackRead"];
export type Asset = components["schemas"]["AssetRead"];
export type ReviewTask = components["schemas"]["ReviewTaskRead"];
export type ContentItem = components["schemas"]["ContentItemRead"];
export type ContentChannel = components["schemas"]["ContentChannel"];
export type AuditLog = components["schemas"]["AuditLogRead"];
export type WorkflowPreset = components["schemas"]["WorkflowPresetRead"];
export type RenderJob = components["schemas"]["RenderJobRead"];
export type InviteRole = components["schemas"]["InviteCreateRequest"]["role"];
export type Invite = components["schemas"]["InviteCreateResponse"];
export type InviteCreateResponse = components["schemas"]["InviteCreateResponse"];
export type UploadTarget = components["schemas"]["UploadTargetRead"];
export type AssetUploadInitiateResponse = components["schemas"]["AssetUploadInitiateResponse"];

export type BootstrapOwnerRequest = components["schemas"]["BootstrapOwnerRequest"];
export type LoginRequest = components["schemas"]["LoginRequest"];
export type InviteAcceptRequest = components["schemas"]["InviteAcceptRequest"];
export type InviteCreateRequest = components["schemas"]["InviteCreateRequest"];
export type BrandCreateRequest = components["schemas"]["BrandCreateRequest"];
export type AvatarCreateRequest = components["schemas"]["AvatarCreateRequest"];
export type IdentityPackCreateRequest = components["schemas"]["IdentityPackCreateRequest"];
export type AssetUploadInitiateRequest = components["schemas"]["AssetUploadInitiateRequest"];
export type AssetFinalizeRequest = components["schemas"]["AssetFinalizeRequest"];
export type ContentItemCreateRequest = components["schemas"]["ContentItemCreateRequest"];
export type ContentPlanRequest = components["schemas"]["ContentPlanRequest"];
export type ReviewDecisionRequest = components["schemas"]["ReviewDecisionRequest"];
export type RenderJobCreateRequest = components["schemas"]["RenderJobCreateRequest"];

export interface CockpitData {
  brands: Brand[];
  avatars: Avatar[];
  identityPacks: IdentityPack[];
  assets: Asset[];
  contentItems: ContentItem[];
  reviewTasks: ReviewTask[];
  auditLogs: AuditLog[];
  workflowPresets: WorkflowPreset[];
  renderJobs: RenderJob[];
}

export const emptyCockpitData: CockpitData = {
  brands: [],
  avatars: [],
  identityPacks: [],
  assets: [],
  contentItems: [],
  reviewTasks: [],
  auditLogs: [],
  workflowPresets: [],
  renderJobs: [],
};

```

`apps/worker/src/content_factory_worker/config.py`:

```py
from functools import lru_cache
from typing import Literal

from pydantic import Field, PositiveFloat, PositiveInt, RedisDsn, field_validator
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

`apps/worker/src/content_factory_worker/executors/__init__.py`:

```py
"""Render provider executors."""

```

`apps/worker/src/content_factory_worker/executors/comfyui.py`:

```py
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

```

`apps/worker/src/content_factory_worker/jobs/render.py`:

```py
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

```

`apps/worker/src/content_factory_worker/queue.py`:

```py
from typing import Any

from dramatiq.message import Message

from content_factory_worker.broker import configure_broker
from content_factory_worker.config import get_worker_settings


def enqueue_render_job(render_job_id: str) -> Message[Any]:
    broker = configure_broker(get_worker_settings())
    from content_factory_worker.jobs.render import process_render_job_message

    process_render_job_message.broker = broker
    broker.declare_actor(process_render_job_message)
    return process_render_job_message.send(render_job_id)

```

`apps/worker/tests/test_comfyui_executor.py`:

```py
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

```

`apps/worker/tests/test_worker_config.py`:

```py
import pytest
from dramatiq.brokers.stub import StubBroker
from pydantic import ValidationError

from content_factory_worker.broker import create_broker
from content_factory_worker.config import WorkerSettings, get_worker_settings


def test_worker_settings_use_local_defaults() -> None:
    settings = get_worker_settings()

    assert settings.worker_name == "content-factory-worker"
    assert str(settings.redis_url) == "redis://localhost:6379/0"
    assert settings.worker_concurrency == 1
    assert settings.comfyui_base_url is None
    assert settings.comfyui_api_mode == "local"


def test_worker_settings_reject_zero_concurrency(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WORKER_CONCURRENCY", "0")

    with pytest.raises(ValidationError):
        get_worker_settings()


def test_worker_settings_normalize_blank_comfyui_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("COMFYUI_BASE_URL", "  ")

    settings = get_worker_settings()

    assert settings.comfyui_base_url is None


def test_worker_uses_stub_broker_in_test_environment() -> None:
    settings = WorkerSettings(app_env="test")

    assert isinstance(create_broker(settings), StubBroker)

```

`pyproject.toml`:

```toml
[build-system]
requires = ["setuptools>=69", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "content-factory-services"
version = "0.1.0"
description = "Phase 1 bootstrap for the Content Factory control plane."
requires-python = ">=3.12"
dependencies = [
  "alembic",
  "boto3",
  "dramatiq[redis]",
  "fastapi",
  "httpx",
  "pydantic-settings",
  "redis",
  "sentry-sdk",
  "sqlalchemy",
  "psycopg[binary]",
  "structlog",
  "uvicorn[standard]",
]

[project.optional-dependencies]
dev = [
  "mypy",
  "pytest",
  "pytest-asyncio",
  "ruff",
]

[tool.setuptools.packages.find]
where = ["apps/api/src", "apps/worker/src"]
include = ["content_factory_api*", "content_factory_pipeline*", "content_factory_worker*"]

[tool.pytest.ini_options]
addopts = "-ra"
testpaths = ["apps/api/tests", "apps/worker/tests"]
pythonpath = ["apps/api/src", "apps/worker/src"]

[tool.ruff]
target-version = "py312"
line-length = 100
src = ["apps/api/src", "apps/api/tests", "apps/worker/src", "apps/worker/tests"]

[tool.ruff.lint]
select = ["B", "E", "F", "I", "UP"]

[tool.mypy]
python_version = "3.12"
strict = true
ignore_missing_imports = true
mypy_path = ["apps/api/src", "apps/worker/src"]

```