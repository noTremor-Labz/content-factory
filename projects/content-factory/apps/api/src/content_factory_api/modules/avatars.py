from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from content_factory_api.database import get_db_session
from content_factory_api.modules.dependencies import get_current_user, require_roles
from content_factory_api.modules.domain import MUTATION_ROLES, IdentityPackStatus
from content_factory_api.modules.models import Avatar, Brand, IdentityPack, User
from content_factory_api.modules.schemas import (
    AvatarCreateRequest,
    AvatarListResponse,
    AvatarRead,
    IdentityPackCreateRequest,
    IdentityPackListResponse,
    IdentityPackRead,
)
from content_factory_api.modules.services import commit_or_409, get_by_id_or_404, write_audit_log

router = APIRouter(prefix="/api/avatars", tags=["avatars"])


@router.post("", response_model=AvatarRead, status_code=status.HTTP_201_CREATED)
def create_avatar(
    request: AvatarCreateRequest,
    current_user: Annotated[User, Depends(require_roles(*MUTATION_ROLES))],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> Avatar:
    get_by_id_or_404(db_session, Brand, request.brand_id, "Brand")
    avatar = Avatar(
        brand_id=request.brand_id,
        name=request.name,
        persona_notes=request.persona_notes,
        created_by_user_id=current_user.id,
    )
    db_session.add(avatar)
    db_session.flush()
    write_audit_log(
        db_session,
        actor_user_id=current_user.id,
        action="avatar.created",
        entity_type="avatar",
        entity_id=avatar.id,
    )
    commit_or_409(db_session, "Avatar could not be created")
    return avatar


@router.get("", response_model=AvatarListResponse)
def list_avatars(
    _current_user: Annotated[User, Depends(get_current_user)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> AvatarListResponse:
    avatars = list(db_session.scalars(select(Avatar).order_by(Avatar.created_at.desc())))
    return AvatarListResponse(items=[AvatarRead.model_validate(avatar) for avatar in avatars])


@router.get("/{avatar_id}/identity-packs", response_model=IdentityPackListResponse)
def list_identity_packs(
    avatar_id: str,
    _current_user: Annotated[User, Depends(get_current_user)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> IdentityPackListResponse:
    get_by_id_or_404(db_session, Avatar, avatar_id, "Avatar")
    identity_packs = list(
        db_session.scalars(
            select(IdentityPack)
            .where(IdentityPack.avatar_id == avatar_id)
            .order_by(IdentityPack.created_at.desc())
        )
    )
    return IdentityPackListResponse(
        items=[IdentityPackRead.model_validate(identity_pack) for identity_pack in identity_packs]
    )


@router.post(
    "/{avatar_id}/identity-packs",
    response_model=IdentityPackRead,
    status_code=status.HTTP_201_CREATED,
)
def create_identity_pack(
    avatar_id: str,
    request: IdentityPackCreateRequest,
    current_user: Annotated[User, Depends(require_roles(*MUTATION_ROLES))],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> IdentityPack:
    get_by_id_or_404(db_session, Avatar, avatar_id, "Avatar")
    identity_pack = IdentityPack(
        avatar_id=avatar_id,
        name=request.name,
        description=request.description,
        storage_prefix=request.storage_prefix,
        status=IdentityPackStatus.DRAFT.value,
    )
    db_session.add(identity_pack)
    db_session.flush()
    write_audit_log(
        db_session,
        actor_user_id=current_user.id,
        action="identity_pack.created",
        entity_type="identity_pack",
        entity_id=identity_pack.id,
        payload={"avatar_id": avatar_id},
    )
    commit_or_409(db_session, "Identity pack could not be created")
    return identity_pack
