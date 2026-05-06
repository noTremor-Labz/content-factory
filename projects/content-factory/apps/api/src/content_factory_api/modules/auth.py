from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from content_factory_api.config import ApiSettings, get_settings
from content_factory_api.database import get_db_session
from content_factory_api.modules.dependencies import (
    SESSION_COOKIE_NAME,
    get_current_user,
    require_roles,
)
from content_factory_api.modules.domain import UserRole, UserStatus
from content_factory_api.modules.models import Invite, User, UserSession
from content_factory_api.modules.schemas import (
    AuthSessionRead,
    BootstrapOwnerRequest,
    InviteAcceptRequest,
    InviteCreateRequest,
    InviteCreateResponse,
    LoginRequest,
    StatusResponse,
)
from content_factory_api.modules.security import (
    create_token,
    expires_in,
    hash_secret,
    hash_token,
    utcnow,
    verify_secret,
)
from content_factory_api.modules.services import commit_or_409, write_audit_log

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _set_session_cookie(
    response: Response,
    *,
    token: str,
    settings: ApiSettings,
) -> None:
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        max_age=settings.session_lifetime_hours * 60 * 60,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite="lax",
    )


def _start_session(
    db_session: Session,
    response: Response,
    *,
    user: User,
    settings: ApiSettings,
) -> UserSession:
    token = create_token()
    user_session = UserSession(
        user_id=user.id,
        token_hash=hash_token(token),
        expires_at=expires_in(hours=settings.session_lifetime_hours),
    )
    db_session.add(user_session)
    db_session.flush()
    _set_session_cookie(response, token=token, settings=settings)
    return user_session


def _session_payload(user: User, user_session: UserSession) -> AuthSessionRead:
    return AuthSessionRead.model_validate(
        {"user": user, "expires_at": user_session.expires_at}
    )


@router.post(
    "/bootstrap-owner",
    response_model=AuthSessionRead,
    status_code=status.HTTP_201_CREATED,
)
def bootstrap_owner(
    request: BootstrapOwnerRequest,
    response: Response,
    db_session: Annotated[Session, Depends(get_db_session)],
    settings: Annotated[ApiSettings, Depends(get_settings)],
) -> AuthSessionRead:
    user_count = db_session.scalar(select(func.count()).select_from(User)) or 0
    if user_count > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Owner already bootstrapped",
        )

    user = User(
        email=request.email,
        display_name=request.display_name,
        role=UserRole.OWNER.value,
        status=UserStatus.ACTIVE.value,
        password_hash=hash_secret(request.password),
    )
    db_session.add(user)
    db_session.flush()
    user_session = _start_session(db_session, response, user=user, settings=settings)
    write_audit_log(
        db_session,
        actor_user_id=user.id,
        action="auth.bootstrap_owner",
        entity_type="user",
        entity_id=user.id,
    )
    commit_or_409(db_session, "Owner could not be created")
    return _session_payload(user, user_session)


@router.post("/invites", response_model=InviteCreateResponse, status_code=status.HTTP_201_CREATED)
def create_invite(
    request: InviteCreateRequest,
    current_user: Annotated[User, Depends(require_roles(UserRole.OWNER))],
    db_session: Annotated[Session, Depends(get_db_session)],
    settings: Annotated[ApiSettings, Depends(get_settings)],
) -> InviteCreateResponse:
    existing_user = db_session.scalar(select(User).where(User.email == request.email))
    if existing_user is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User already exists")

    token = create_token()
    invite = Invite(
        email=request.email,
        role=request.role.value,
        token_hash=hash_token(token),
        expires_at=expires_in(hours=settings.invite_expiration_hours),
        created_by_user_id=current_user.id,
    )
    db_session.add(invite)
    db_session.flush()
    write_audit_log(
        db_session,
        actor_user_id=current_user.id,
        action="auth.invite_created",
        entity_type="invite",
        entity_id=invite.id,
        payload={"email": invite.email, "role": invite.role},
    )
    commit_or_409(db_session, "Invite could not be created")
    return InviteCreateResponse(
        invite_id=invite.id,
        email=invite.email,
        role=UserRole(invite.role),
        token=token,
        expires_at=invite.expires_at,
    )


@router.post("/invites/accept", response_model=AuthSessionRead, status_code=status.HTTP_201_CREATED)
def accept_invite(
    request: InviteAcceptRequest,
    response: Response,
    db_session: Annotated[Session, Depends(get_db_session)],
    settings: Annotated[ApiSettings, Depends(get_settings)],
) -> AuthSessionRead:
    invite = db_session.scalar(select(Invite).where(Invite.token_hash == hash_token(request.token)))
    if (
        invite is None
        or invite.accepted_at is not None
        or invite.expires_at <= utcnow()
        or invite.email != request.email
    ):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invite is invalid")

    existing_user = db_session.scalar(select(User).where(User.email == request.email))
    if existing_user is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User already exists")

    user = User(
        email=request.email,
        display_name=request.display_name,
        role=invite.role,
        status=UserStatus.ACTIVE.value,
        password_hash=hash_secret(request.password),
    )
    invite.accepted_at = utcnow()
    db_session.add(user)
    db_session.flush()
    user_session = _start_session(db_session, response, user=user, settings=settings)
    write_audit_log(
        db_session,
        actor_user_id=user.id,
        action="auth.invite_accepted",
        entity_type="user",
        entity_id=user.id,
        payload={"invite_id": invite.id, "role": user.role},
    )
    commit_or_409(db_session, "Invite could not be accepted")
    return _session_payload(user, user_session)


@router.post("/login", response_model=AuthSessionRead)
def login(
    request: LoginRequest,
    response: Response,
    db_session: Annotated[Session, Depends(get_db_session)],
    settings: Annotated[ApiSettings, Depends(get_settings)],
) -> AuthSessionRead:
    user = db_session.scalar(select(User).where(User.email == request.email))
    if (
        user is None
        or user.status != UserStatus.ACTIVE.value
        or not verify_secret(request.password, user.password_hash)
    ):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    user_session = _start_session(db_session, response, user=user, settings=settings)
    write_audit_log(
        db_session,
        actor_user_id=user.id,
        action="auth.login",
        entity_type="user",
        entity_id=user.id,
    )
    commit_or_409(db_session, "Session could not be created")
    return _session_payload(user, user_session)


@router.post("/logout", response_model=StatusResponse)
def logout(
    response: Response,
    current_user: Annotated[User, Depends(get_current_user)],
    db_session: Annotated[Session, Depends(get_db_session)],
    session_token: Annotated[str | None, Cookie(alias=SESSION_COOKIE_NAME)] = None,
) -> StatusResponse:
    if session_token is not None:
        user_session = db_session.scalar(
            select(UserSession).where(UserSession.token_hash == hash_token(session_token))
        )
        if user_session is not None:
            user_session.revoked_at = utcnow()
    write_audit_log(
        db_session,
        actor_user_id=current_user.id,
        action="auth.logout",
        entity_type="user",
        entity_id=current_user.id,
    )
    response.delete_cookie(key=SESSION_COOKIE_NAME)
    db_session.commit()
    return StatusResponse(status="ok")


@router.get("/session", response_model=AuthSessionRead)
def get_session(
    current_user: Annotated[User, Depends(get_current_user)],
    db_session: Annotated[Session, Depends(get_db_session)],
    session_token: Annotated[str | None, Cookie(alias=SESSION_COOKIE_NAME)] = None,
) -> AuthSessionRead:
    if session_token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )
    user_session = db_session.scalar(
        select(UserSession).where(UserSession.token_hash == hash_token(session_token))
    )
    if user_session is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session")
    return _session_payload(current_user, user_session)
