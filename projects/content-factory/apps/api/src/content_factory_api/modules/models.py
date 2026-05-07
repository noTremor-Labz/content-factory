from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from content_factory_api.database import Base
from content_factory_api.modules.domain import (
    AssetStatus,
    AvatarStatus,
    ContentChannel,
    ContentStatus,
    IdentityPackStatus,
    JobAttemptStatus,
    PackagingProvider,
    PublishPackageStatus,
    RenderJobStatus,
    ReviewTaskStatus,
    UserRole,
    UserStatus,
    VoiceProvider,
    WorkflowProvider,
)
from content_factory_api.modules.security import utcnow


def new_id() -> str:
    return str(uuid.uuid4())


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=utcnow,
        onupdate=utcnow,
        nullable=False,
    )


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False, default=UserRole.VIEWER.value)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default=UserStatus.ACTIVE.value)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)


class Invite(TimestampMixin, Base):
    __tablename__ = "invites"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    email: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_by_user_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("users.id"),
        nullable=True,
    )


class UserSession(Base):
    __tablename__ = "user_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id"),
        index=True,
        nullable=False,
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class Brand(TimestampMixin, Base):
    __tablename__ = "brands"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    voice_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by_user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id"),
        nullable=False,
    )


class Avatar(TimestampMixin, Base):
    __tablename__ = "avatars"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    brand_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("brands.id"),
        index=True,
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    persona_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=AvatarStatus.DRAFT.value,
    )
    created_by_user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id"),
        nullable=False,
    )


class IdentityPack(TimestampMixin, Base):
    __tablename__ = "identity_packs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    avatar_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("avatars.id"),
        index=True,
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    storage_prefix: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=IdentityPackStatus.DRAFT.value,
    )


class Asset(TimestampMixin, Base):
    __tablename__ = "assets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    brand_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("brands.id"),
        index=True,
        nullable=False,
    )
    created_by_user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id"),
        nullable=False,
    )
    object_key: Mapped[str] = mapped_column(String(700), unique=True, nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(255), nullable=False)
    byte_size: Mapped[int | None] = mapped_column(nullable=True)
    checksum_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=AssetStatus.PENDING_UPLOAD.value,
    )
    upload_expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class ContentItem(TimestampMixin, Base):
    __tablename__ = "content_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    brand_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("brands.id"),
        index=True,
        nullable=False,
    )
    avatar_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("avatars.id"),
        index=True,
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    script: Mapped[str] = mapped_column(Text, nullable=False)
    channel: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=ContentChannel.YOUTUBE_SHORTS.value,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=ContentStatus.DRAFT.value,
    )
    planned_publish_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_by_user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id"),
        nullable=False,
    )


class ReviewTask(TimestampMixin, Base):
    __tablename__ = "review_tasks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    content_item_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("content_items.id"),
        index=True,
        nullable=False,
    )
    assigned_to_user_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("users.id"),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=ReviewTaskStatus.OPEN.value,
    )
    decision_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    actor_user_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("users.id"),
        nullable=True,
    )
    action: Mapped[str] = mapped_column(String(120), index=True, nullable=False)
    entity_type: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    entity_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)


class WorkflowPreset(TimestampMixin, Base):
    __tablename__ = "workflow_presets"
    __table_args__ = (UniqueConstraint("key", "version", name="uq_workflow_presets_key_version"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    key: Mapped[str] = mapped_column(String(120), index=True, nullable=False)
    version: Mapped[int] = mapped_column(nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    workflow_provider: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default=WorkflowProvider.COMFYUI.value,
    )
    voice_provider: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default=VoiceProvider.NONE.value,
    )
    packaging_provider: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default=PackagingProvider.FFMPEG.value,
    )
    workflow_definition: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    input_mapping: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    output_mapping: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    created_by_user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id"),
        nullable=False,
    )


class RenderJob(TimestampMixin, Base):
    __tablename__ = "render_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    content_item_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("content_items.id"),
        index=True,
        nullable=False,
    )
    workflow_preset_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("workflow_presets.id"),
        index=True,
        nullable=False,
    )
    workflow_preset_key: Mapped[str] = mapped_column(String(120), nullable=False)
    workflow_preset_version: Mapped[int] = mapped_column(nullable=False)
    workflow_provider: Mapped[str] = mapped_column(String(64), nullable=False)
    voice_provider: Mapped[str] = mapped_column(String(64), nullable=False)
    packaging_provider: Mapped[str] = mapped_column(String(64), nullable=False)
    input_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=RenderJobStatus.QUEUED.value,
    )
    retry_budget: Mapped[int] = mapped_column(nullable=False, default=3)
    created_by_user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id"),
        nullable=False,
    )


class JobAttempt(TimestampMixin, Base):
    __tablename__ = "job_attempts"
    __table_args__ = (
        UniqueConstraint("render_job_id", "attempt_number", name="uq_job_attempts_job_attempt"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    render_job_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("render_jobs.id"),
        index=True,
        nullable=False,
    )
    attempt_number: Mapped[int] = mapped_column(nullable=False)
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=JobAttemptStatus.QUEUED.value,
    )
    provider_job_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    request_payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    response_payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class PublishPackage(TimestampMixin, Base):
    __tablename__ = "publish_packages"
    __table_args__ = (UniqueConstraint("render_job_id", name="uq_publish_packages_render_job"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    render_job_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("render_jobs.id"),
        index=True,
        nullable=False,
    )
    content_item_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("content_items.id"),
        index=True,
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=PublishPackageStatus.QUEUED.value,
    )
    package_object_key: Mapped[str | None] = mapped_column(String(700), nullable=True)
    manifest_payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    byte_size: Mapped[int | None] = mapped_column(nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by_user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id"),
        nullable=False,
    )
