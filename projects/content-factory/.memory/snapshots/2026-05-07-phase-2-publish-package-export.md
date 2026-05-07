Project Path: content-factory

Source Tree:

```txt
content-factory
├── AGENTS.md
├── CLAUDE.md
├── Makefile
├── README.md
├── alembic.ini
├── apps
│   ├── api
│   │   ├── alembic
│   │   │   ├── env.py
│   │   │   └── versions
│   │   │       ├── 20260506_0001_control_plane.py
│   │   │       ├── 20260506_0002_render_contracts.py
│   │   │       ├── 20260506_0003_render_attempt_response_payload.py
│   │   │       └── 20260507_0004_publish_packages.py
│   │   ├── src
│   │   │   ├── content_factory_api
│   │   │   │   ├── __init__.py
│   │   │   │   ├── app.py
│   │   │   │   ├── config.py
│   │   │   │   ├── database.py
│   │   │   │   ├── export_openapi.py
│   │   │   │   ├── health.py
│   │   │   │   ├── logging.py
│   │   │   │   └── modules
│   │   │   │       ├── __init__.py
│   │   │   │       ├── assets.py
│   │   │   │       ├── audit.py
│   │   │   │       ├── auth.py
│   │   │   │       ├── avatars.py
│   │   │   │       ├── brands.py
│   │   │   │       ├── content.py
│   │   │   │       ├── dependencies.py
│   │   │   │       ├── domain.py
│   │   │   │       ├── exports.py
│   │   │   │       ├── models.py
│   │   │   │       ├── render.py
│   │   │   │       ├── review.py
│   │   │   │       ├── schemas.py
│   │   │   │       ├── security.py
│   │   │   │       ├── services.py
│   │   │   │       ├── users.py
│   │   │   │       └── workflows.py
│   │   │   └── content_factory_pipeline
│   │   │       ├── __init__.py
│   │   │       └── providers.py
│   │   └── tests
│   │       ├── conftest.py
│   │       ├── test_api_config.py
│   │       ├── test_auth.py
│   │       ├── test_control_plane.py
│   │       ├── test_health.py
│   │       ├── test_migrations.py
│   │       ├── test_openapi.py
│   │       ├── test_publish_packages.py
│   │       └── test_render_contracts.py
│   ├── web
│   │   ├── e2e
│   │   │   └── cockpit.smoke.e2e.ts
│   │   ├── eslint.config.mjs
│   │   ├── index.html
│   │   ├── package.json
│   │   ├── playwright.config.ts
│   │   ├── src
│   │   │   ├── app
│   │   │   │   ├── App.css
│   │   │   │   ├── App.test.tsx
│   │   │   │   ├── App.tsx
│   │   │   │   └── routes.ts
│   │   │   ├── config
│   │   │   │   ├── env.test.ts
│   │   │   │   └── env.ts
│   │   │   ├── features
│   │   │   │   ├── audit
│   │   │   │   │   └── AuditPanel.tsx
│   │   │   │   ├── auth
│   │   │   │   │   └── AuthPanel.tsx
│   │   │   │   ├── avatars
│   │   │   │   │   └── AvatarsPanel.tsx
│   │   │   │   ├── brands-assets
│   │   │   │   │   └── BrandsAssetsPanel.tsx
│   │   │   │   ├── content
│   │   │   │   │   └── ContentPanel.tsx
│   │   │   │   ├── export
│   │   │   │   │   └── ExportPanel.tsx
│   │   │   │   ├── render
│   │   │   │   │   └── RenderPanel.tsx
│   │   │   │   └── review
│   │   │   │       └── ReviewPanel.tsx
│   │   │   ├── main.tsx
│   │   │   ├── shared
│   │   │   │   ├── api
│   │   │   │   │   ├── client.ts
│   │   │   │   │   ├── types.ts
│   │   │   │   │   └── upload.ts
│   │   │   │   └── format.ts
│   │   │   ├── test
│   │   │   │   └── setup.ts
│   │   │   └── vite-env.d.ts
│   │   ├── tsconfig.app.json
│   │   ├── tsconfig.json
│   │   ├── tsconfig.node.json
│   │   ├── vite.config.ts
│   │   └── vitest.config.ts
│   └── worker
│       ├── src
│       │   └── content_factory_worker
│       │       ├── __init__.py
│       │       ├── broker.py
│       │       ├── config.py
│       │       ├── executors
│       │       │   ├── __init__.py
│       │       │   └── comfyui.py
│       │       ├── jobs
│       │       │   ├── __init__.py
│       │       │   ├── packaging.py
│       │       │   └── render.py
│       │       ├── logging.py
│       │       ├── main.py
│       │       ├── orchestration.py
│       │       ├── packaging.py
│       │       ├── providers.py
│       │       └── queue.py
│       └── tests
│           ├── conftest.py
│           ├── test_comfyui_executor.py
│           ├── test_providers.py
│           ├── test_publish_package_orchestration.py
│           ├── test_render_orchestration.py
│           └── test_worker_config.py
├── docs
├── infra
│   └── docker-compose.yml
├── package.json
├── packages
│   └── contracts
│       ├── openapi
│       │   └── content-factory.openapi.json
│       ├── package.json
│       ├── src
│       │   ├── generated
│       │   │   └── api.ts
│       │   └── index.ts
│       └── tsconfig.json
├── pnpm-lock.yaml
├── pnpm-workspace.yaml
├── pyproject.toml
├── scripts
├── src
└── tests

```

`apps/api/alembic/versions/20260507_0004_publish_packages.py`:

```py
"""add publish packages

Revision ID: 20260507_0004
Revises: 20260506_0003
Create Date: 2026-05-07
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260507_0004"
down_revision: str | None = "20260506_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "publish_packages",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("render_job_id", sa.String(length=36), nullable=False),
        sa.Column("content_item_id", sa.String(length=36), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("package_object_key", sa.String(length=700), nullable=True),
        sa.Column("manifest_payload", sa.JSON(), nullable=False),
        sa.Column("byte_size", sa.Integer(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_by_user_id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["content_item_id"], ["content_items.id"]),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["render_job_id"], ["render_jobs.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("render_job_id", name="uq_publish_packages_render_job"),
    )
    op.create_index(
        op.f("ix_publish_packages_content_item_id"),
        "publish_packages",
        ["content_item_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_publish_packages_render_job_id"),
        "publish_packages",
        ["render_job_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_publish_packages_render_job_id"), table_name="publish_packages")
    op.drop_index(op.f("ix_publish_packages_content_item_id"), table_name="publish_packages")
    op.drop_table("publish_packages")

```

`apps/api/src/content_factory_api/app.py`:

```py
from typing import Annotated

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from content_factory_api import API_VERSION
from content_factory_api.config import ApiSettings, get_settings
from content_factory_api.health import router as health_router
from content_factory_api.logging import configure_observability
from content_factory_api.modules.assets import router as assets_router
from content_factory_api.modules.audit import router as audit_router
from content_factory_api.modules.auth import router as auth_router
from content_factory_api.modules.avatars import router as avatars_router
from content_factory_api.modules.brands import router as brands_router
from content_factory_api.modules.content import router as content_router
from content_factory_api.modules.exports import router as exports_router
from content_factory_api.modules.render import router as render_router
from content_factory_api.modules.review import router as review_router
from content_factory_api.modules.users import router as users_router
from content_factory_api.modules.workflows import router as workflows_router


def provide_settings() -> ApiSettings:
    return get_settings()


def create_app() -> FastAPI:
    settings = get_settings()
    configure_observability(
        service_name=settings.app_name,
        app_env=settings.app_env,
        sentry_dsn=settings.sentry_dsn,
    )

    app = FastAPI(
        title=settings.app_name,
        version=API_VERSION,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    if settings.cors_origin_list:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origin_list,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    @app.get("/")
    def root(
        current_settings: Annotated[ApiSettings, Depends(provide_settings)],
    ) -> dict[str, str]:
        return {
            "name": current_settings.app_name,
            "phase": "phase-1-control-plane",
            "status": "ready",
            "version": API_VERSION,
        }

    @app.get("/api/meta")
    def meta(
        current_settings: Annotated[ApiSettings, Depends(provide_settings)],
    ) -> dict[str, str]:
        return {
            "environment": current_settings.app_env,
            "service": current_settings.app_name,
            "version": API_VERSION,
        }

    app.include_router(health_router)
    app.include_router(auth_router)
    app.include_router(users_router)
    app.include_router(brands_router)
    app.include_router(avatars_router)
    app.include_router(assets_router)
    app.include_router(content_router)
    app.include_router(workflows_router)
    app.include_router(render_router)
    app.include_router(exports_router)
    app.include_router(review_router)
    app.include_router(audit_router)
    return app

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

```

`apps/api/src/content_factory_api/modules/models.py`:

```py
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
    PublishPackageStatus,
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


class PublishPackageCreateRequest(BaseModel):
    render_job_id: str


class PublishPackageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    render_job_id: str
    content_item_id: str
    status: PublishPackageStatus
    package_object_key: str | None
    manifest_payload: dict[str, Any]
    byte_size: int | None
    error_message: str | None
    created_by_user_id: str
    created_at: datetime
    updated_at: datetime


class PublishPackageListResponse(BaseModel):
    items: list[PublishPackageRead]


class DownloadTargetRead(BaseModel):
    method: str
    url: str
    headers: dict[str, str]
    expires_at: datetime


class PublishPackageDownloadResponse(BaseModel):
    package: PublishPackageRead
    download: DownloadTargetRead


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

`apps/api/tests/test_publish_packages.py`:

```py
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
  status: "queued" | "running" | "ready" | "failed";
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
              onGetDownload={async (packageId) => {
                const response = await apiClient.getPublishPackageDownload(packageId);
                return response.download.url;
              }}
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

`apps/web/src/app/routes.ts`:

```ts
export const cockpitRoutes = [
  { id: "overview", label: "Overview" },
  { id: "brands-assets", label: "Brands & Assets" },
  { id: "avatars", label: "Avatars" },
  { id: "content", label: "Content" },
  { id: "review", label: "Review" },
  { id: "render", label: "Render" },
  { id: "export", label: "Export" },
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
  onGetDownload: (packageId: string) => Promise<string>;
}

const activePackageStatuses = new Set(["queued", "running", "ready"]);

export function ExportPanel({
  contentItems,
  publishPackages,
  renderJobs,
  canMutate,
  busy,
  onCreatePackage,
  onGetDownload,
}: ExportPanelProps) {
  const [selectedRenderJobId, setSelectedRenderJobId] = useState("");
  const [downloadUrls, setDownloadUrls] = useState<Record<string, string>>({});
  const [downloadError, setDownloadError] = useState<string | null>(null);
  const activePackageRenderJobIds = new Set(
    publishPackages
      .filter((publishPackage) => activePackageStatuses.has(publishPackage.status))
      .map((publishPackage) => publishPackage.render_job_id),
  );
  const eligibleRenderJobs = renderJobs.filter((renderJob) => {
    const contentItem = contentItems.find((item) => item.id === renderJob.content_item_id);
    return (
      renderJob.status === "succeeded" &&
      contentItem?.status === "approved" &&
      !activePackageRenderJobIds.has(renderJob.id)
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
  renderJobEventsUrl(renderJobId: string) {
    return resolveApiUrl(`/api/render-jobs/${renderJobId}/events`);
  },
  listPublishPackages() {
    return getList<PublishPackage>("/api/publish-packages");
  },
  createPublishPackage(payload: PublishPackageCreateRequest) {
    return postJson<PublishPackageCreateRequest, PublishPackage>("/api/publish-packages", payload);
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
export type PublishPackage = components["schemas"]["PublishPackageRead"];
export type InviteRole = components["schemas"]["InviteCreateRequest"]["role"];
export type Invite = components["schemas"]["InviteCreateResponse"];
export type InviteCreateResponse = components["schemas"]["InviteCreateResponse"];
export type UploadTarget = components["schemas"]["UploadTargetRead"];
export type AssetUploadInitiateResponse = components["schemas"]["AssetUploadInitiateResponse"];
export type PublishPackageDownloadResponse = components["schemas"]["PublishPackageDownloadResponse"];

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
export type PublishPackageCreateRequest = components["schemas"]["PublishPackageCreateRequest"];

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
  publishPackages: PublishPackage[];
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
  publishPackages: [],
};

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

import boto3
import dramatiq
from botocore.client import Config

from content_factory_api.database import get_sessionmaker
from content_factory_worker.config import WorkerSettings, get_worker_settings
from content_factory_worker.packaging import (
    PackageStorage,
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


def build_publish_packager(settings: WorkerSettings) -> PublishPackager:
    return ZipPublishPackager(storage=S3PackageStorage(settings))


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

`apps/worker/src/content_factory_worker/main.py`:

```py
from content_factory_worker.broker import configure_broker
from content_factory_worker.config import get_worker_settings
from content_factory_worker.logging import configure_observability


def bootstrap_worker() -> str:
    settings = get_worker_settings()
    configure_observability(
        worker_name=settings.worker_name,
        app_env=settings.app_env,
        sentry_dsn=settings.sentry_dsn,
    )
    configure_broker(settings)
    import content_factory_worker.jobs.packaging as _packaging_jobs
    import content_factory_worker.jobs.render as _render_jobs

    _ = _packaging_jobs
    _ = _render_jobs
    return settings.worker_name

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


def enqueue_publish_package(publish_package_id: str) -> Message[Any]:
    broker = configure_broker(get_worker_settings())
    from content_factory_worker.jobs.packaging import process_publish_package_message

    process_publish_package_message.broker = broker
    broker.declare_actor(process_publish_package_message)
    return process_publish_package_message.send(publish_package_id)

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