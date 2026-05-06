from collections.abc import Callable
from typing import Annotated

from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from content_factory_api.database import get_db_session
from content_factory_api.modules.domain import UserRole, UserStatus
from content_factory_api.modules.models import User, UserSession
from content_factory_api.modules.security import hash_token, utcnow

SESSION_COOKIE_NAME = "cf_session"


def get_current_user(
    db_session: Annotated[Session, Depends(get_db_session)],
    session_token: Annotated[str | None, Cookie(alias=SESSION_COOKIE_NAME)] = None,
) -> User:
    if session_token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    user_session = db_session.scalar(
        select(UserSession).where(UserSession.token_hash == hash_token(session_token))
    )
    if (
        user_session is None
        or user_session.revoked_at is not None
        or user_session.expires_at <= utcnow()
    ):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session")

    user = db_session.get(User, user_session.user_id)
    if user is None or user.status != UserStatus.ACTIVE.value:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session")

    return user


def require_roles(*allowed_roles: UserRole) -> Callable[[User], User]:
    allowed_role_values = {role.value for role in allowed_roles}

    def dependency(current_user: Annotated[User, Depends(get_current_user)]) -> User:
        if current_user.role not in allowed_role_values:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
        return current_user

    return dependency
