from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from starlette import status

from content_factory_api.database import get_db_session
from content_factory_api.modules.compliance import validate_compliance_for_review_approval
from content_factory_api.modules.dependencies import get_current_user, require_roles
from content_factory_api.modules.domain import (
    REVIEW_DECISION_ROLES,
    ContentStatus,
    ReviewTaskStatus,
)
from content_factory_api.modules.models import ContentItem, ReviewTask, User
from content_factory_api.modules.schemas import (
    ReviewDecisionRequest,
    ReviewTaskListResponse,
    ReviewTaskRead,
)
from content_factory_api.modules.security import utcnow
from content_factory_api.modules.services import get_by_id_or_404, write_audit_log

router = APIRouter(prefix="/api/review/tasks", tags=["review"])


@router.get("", response_model=ReviewTaskListResponse)
def list_review_tasks(
    _current_user: Annotated[User, Depends(get_current_user)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> ReviewTaskListResponse:
    tasks = list(
        db_session.scalars(select(ReviewTask).order_by(ReviewTask.created_at.desc()))
    )
    return ReviewTaskListResponse(items=[ReviewTaskRead.model_validate(task) for task in tasks])


@router.post("/{task_id}/approve", response_model=ReviewTaskRead)
def approve_review_task(
    task_id: str,
    request: ReviewDecisionRequest,
    current_user: Annotated[User, Depends(require_roles(*REVIEW_DECISION_ROLES))],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> ReviewTask:
    task = _get_open_review_task(db_session, task_id)
    content_item = get_by_id_or_404(db_session, ContentItem, task.content_item_id, "Content item")
    compliance_check = validate_compliance_for_review_approval(
        db_session,
        content_item=content_item,
        compliance_override_reason=request.compliance_override_reason,
    )
    content_item.status = ContentStatus.APPROVED.value
    task.status = ReviewTaskStatus.APPROVED.value
    task.decision_notes = request.decision_notes
    task.compliance_check_id = compliance_check.id
    task.compliance_override_reason = (
        request.compliance_override_reason.strip()
        if request.compliance_override_reason is not None
        else None
    )
    task.completed_at = utcnow()
    if task.compliance_override_reason is not None:
        write_audit_log(
            db_session,
            actor_user_id=current_user.id,
            action="review.compliance_override",
            entity_type="review_task",
            entity_id=task.id,
            payload={
                "content_item_id": content_item.id,
                "compliance_check_id": compliance_check.id,
                "reason": task.compliance_override_reason,
            },
        )
    write_audit_log(
        db_session,
        actor_user_id=current_user.id,
        action="review.approved",
        entity_type="review_task",
        entity_id=task.id,
        payload={
            "content_item_id": content_item.id,
            "compliance_check_id": compliance_check.id,
            "compliance_status": compliance_check.status,
            "compliance_override": task.compliance_override_reason is not None,
        },
    )
    db_session.commit()
    return task


@router.post("/{task_id}/request-rework", response_model=ReviewTaskRead)
def request_rework(
    task_id: str,
    request: ReviewDecisionRequest,
    current_user: Annotated[User, Depends(require_roles(*REVIEW_DECISION_ROLES))],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> ReviewTask:
    task = _get_open_review_task(db_session, task_id)
    content_item = get_by_id_or_404(db_session, ContentItem, task.content_item_id, "Content item")
    content_item.status = ContentStatus.REWORK.value
    task.status = ReviewTaskStatus.REWORK.value
    task.decision_notes = request.decision_notes
    task.completed_at = utcnow()
    write_audit_log(
        db_session,
        actor_user_id=current_user.id,
        action="review.rework_requested",
        entity_type="review_task",
        entity_id=task.id,
        payload={"content_item_id": content_item.id},
    )
    db_session.commit()
    return task


def _get_open_review_task(db_session: Session, task_id: str) -> ReviewTask:
    task = get_by_id_or_404(db_session, ReviewTask, task_id, "Review task")
    content_item = get_by_id_or_404(db_session, ContentItem, task.content_item_id, "Content item")
    if (
        task.status != ReviewTaskStatus.OPEN.value
        or content_item.status != ContentStatus.REVIEW.value
    ):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Review task is not open")
    return task
