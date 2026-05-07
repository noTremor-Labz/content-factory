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
