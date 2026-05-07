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
