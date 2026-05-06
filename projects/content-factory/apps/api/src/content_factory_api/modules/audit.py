from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from content_factory_api.database import get_db_session
from content_factory_api.modules.dependencies import require_roles
from content_factory_api.modules.domain import UserRole
from content_factory_api.modules.models import AuditLog, User
from content_factory_api.modules.schemas import AuditLogListResponse, AuditLogRead

router = APIRouter(prefix="/api/audit/logs", tags=["audit"])


@router.get("", response_model=AuditLogListResponse)
def list_audit_logs(
    _current_user: Annotated[User, Depends(require_roles(UserRole.OWNER, UserRole.OPERATOR))],
    db_session: Annotated[Session, Depends(get_db_session)],
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
) -> AuditLogListResponse:
    logs = list(
        db_session.scalars(select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit))
    )
    return AuditLogListResponse(items=[AuditLogRead.model_validate(log) for log in logs])
