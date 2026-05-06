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


MUTATION_ROLES = (UserRole.OWNER, UserRole.OPERATOR)
REVIEW_DECISION_ROLES = (UserRole.OWNER, UserRole.REVIEWER)
