from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from content_factory_api.database import get_db_session
from content_factory_api.modules.dependencies import get_current_user, require_roles
from content_factory_api.modules.domain import MUTATION_ROLES, ContentStatus, ReviewTaskStatus
from content_factory_api.modules.models import Avatar, Brand, ContentItem, ReviewTask, User
from content_factory_api.modules.schemas import (
    ContentItemCreateRequest,
    ContentItemListResponse,
    ContentItemRead,
    ContentPlanRequest,
    ReviewTaskRead,
)
from content_factory_api.modules.services import (
    commit_or_409,
    get_by_id_or_404,
    write_audit_log,
)

router = APIRouter(prefix="/api/content-items", tags=["content"])


@router.post("", response_model=ContentItemRead, status_code=status.HTTP_201_CREATED)
def create_content_item(
    request: ContentItemCreateRequest,
    current_user: Annotated[User, Depends(require_roles(*MUTATION_ROLES))],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> ContentItem:
    get_by_id_or_404(db_session, Brand, request.brand_id, "Brand")
    get_by_id_or_404(db_session, Avatar, request.avatar_id, "Avatar")
    content_item = ContentItem(
        brand_id=request.brand_id,
        avatar_id=request.avatar_id,
        title=request.title,
        script=request.script,
        channel=request.channel.value,
        status=ContentStatus.DRAFT.value,
        created_by_user_id=current_user.id,
    )
    db_session.add(content_item)
    db_session.flush()
    write_audit_log(
        db_session,
        actor_user_id=current_user.id,
        action="content.created",
        entity_type="content_item",
        entity_id=content_item.id,
    )
    commit_or_409(db_session, "Content item could not be created")
    return content_item


@router.get("", response_model=ContentItemListResponse)
def list_content_items(
    _current_user: Annotated[User, Depends(get_current_user)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> ContentItemListResponse:
    content_items = list(
        db_session.scalars(select(ContentItem).order_by(ContentItem.created_at.desc()))
    )
    return ContentItemListResponse(
        items=[ContentItemRead.model_validate(content_item) for content_item in content_items]
    )


@router.get("/{content_item_id}", response_model=ContentItemRead)
def get_content_item(
    content_item_id: str,
    _current_user: Annotated[User, Depends(get_current_user)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> ContentItem:
    return get_by_id_or_404(db_session, ContentItem, content_item_id, "Content item")


@router.post("/{content_item_id}/plan", response_model=ContentItemRead)
def plan_content_item(
    content_item_id: str,
    request: ContentPlanRequest,
    current_user: Annotated[User, Depends(require_roles(*MUTATION_ROLES))],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> ContentItem:
    content_item = get_by_id_or_404(db_session, ContentItem, content_item_id, "Content item")
    if content_item.status not in {ContentStatus.DRAFT.value, ContentStatus.REWORK.value}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Content item cannot be planned",
        )

    content_item.status = ContentStatus.PLANNED.value
    content_item.planned_publish_at = request.planned_publish_at
    write_audit_log(
        db_session,
        actor_user_id=current_user.id,
        action="content.planned",
        entity_type="content_item",
        entity_id=content_item.id,
    )
    db_session.commit()
    return content_item


@router.post(
    "/{content_item_id}/submit-review",
    response_model=ReviewTaskRead,
    status_code=status.HTTP_201_CREATED,
)
def submit_content_item_for_review(
    content_item_id: str,
    current_user: Annotated[User, Depends(require_roles(*MUTATION_ROLES))],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> ReviewTask:
    content_item = get_by_id_or_404(db_session, ContentItem, content_item_id, "Content item")
    if content_item.status not in {ContentStatus.PLANNED.value, ContentStatus.REWORK.value}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Content item must be planned before review",
        )

    existing_task = db_session.scalar(
        select(ReviewTask).where(
            ReviewTask.content_item_id == content_item.id,
            ReviewTask.status == ReviewTaskStatus.OPEN.value,
        )
    )
    if existing_task is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Review task already open")

    content_item.status = ContentStatus.REVIEW.value
    review_task = ReviewTask(
        content_item_id=content_item.id,
        status=ReviewTaskStatus.OPEN.value,
    )
    db_session.add(review_task)
    db_session.flush()
    write_audit_log(
        db_session,
        actor_user_id=current_user.id,
        action="content.submitted_for_review",
        entity_type="content_item",
        entity_id=content_item.id,
        payload={"review_task_id": review_task.id},
    )
    db_session.commit()
    return review_task
