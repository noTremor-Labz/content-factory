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
