from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from content_factory_api.database import Base
from content_factory_api.modules.models import AuditLog


def get_by_id_or_404[ModelT: Base](
    db_session: Session,
    model: type[ModelT],
    entity_id: str,
    entity_name: str,
) -> ModelT:
    entity = db_session.get(model, entity_id)
    if entity is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{entity_name} not found",
        )
    return entity


def commit_or_409(db_session: Session, detail: str) -> None:
    try:
        db_session.commit()
    except IntegrityError as exc:
        db_session.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail) from exc


def write_audit_log(
    db_session: Session,
    *,
    actor_user_id: str | None,
    action: str,
    entity_type: str,
    entity_id: str,
    payload: dict[str, object] | None = None,
) -> AuditLog:
    audit_log = AuditLog(
        actor_user_id=actor_user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        payload=payload or {},
    )
    db_session.add(audit_log)
    return audit_log
