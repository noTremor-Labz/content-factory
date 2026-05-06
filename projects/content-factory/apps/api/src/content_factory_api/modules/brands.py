from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from content_factory_api.database import get_db_session
from content_factory_api.modules.dependencies import get_current_user, require_roles
from content_factory_api.modules.domain import MUTATION_ROLES
from content_factory_api.modules.models import Brand, User
from content_factory_api.modules.schemas import BrandCreateRequest, BrandListResponse, BrandRead
from content_factory_api.modules.services import commit_or_409, get_by_id_or_404, write_audit_log

router = APIRouter(prefix="/api/brands", tags=["brands"])


@router.post("", response_model=BrandRead, status_code=status.HTTP_201_CREATED)
def create_brand(
    request: BrandCreateRequest,
    current_user: Annotated[User, Depends(require_roles(*MUTATION_ROLES))],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> Brand:
    brand = Brand(
        name=request.name,
        voice_notes=request.voice_notes,
        created_by_user_id=current_user.id,
    )
    db_session.add(brand)
    db_session.flush()
    write_audit_log(
        db_session,
        actor_user_id=current_user.id,
        action="brand.created",
        entity_type="brand",
        entity_id=brand.id,
    )
    commit_or_409(db_session, "Brand could not be created")
    return brand


@router.get("", response_model=BrandListResponse)
def list_brands(
    _current_user: Annotated[User, Depends(get_current_user)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> BrandListResponse:
    brands = list(db_session.scalars(select(Brand).order_by(Brand.created_at.desc())))
    return BrandListResponse(items=[BrandRead.model_validate(brand) for brand in brands])


@router.get("/{brand_id}", response_model=BrandRead)
def get_brand(
    brand_id: str,
    _current_user: Annotated[User, Depends(get_current_user)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> Brand:
    return get_by_id_or_404(db_session, Brand, brand_id, "Brand")
