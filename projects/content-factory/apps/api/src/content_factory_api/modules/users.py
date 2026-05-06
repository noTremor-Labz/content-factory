from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from content_factory_api.database import get_db_session
from content_factory_api.modules.dependencies import get_current_user, require_roles
from content_factory_api.modules.domain import UserRole
from content_factory_api.modules.models import User
from content_factory_api.modules.schemas import UserListResponse, UserRead

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("/me", response_model=UserRead)
def get_me(current_user: Annotated[User, Depends(get_current_user)]) -> User:
    return current_user


@router.get("", response_model=UserListResponse)
def list_users(
    _current_user: Annotated[User, Depends(require_roles(UserRole.OWNER, UserRole.OPERATOR))],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> UserListResponse:
    users = list(db_session.scalars(select(User).order_by(User.created_at.desc())))
    return UserListResponse(items=[UserRead.model_validate(user) for user in users])
