import re
from typing import Annotated, cast

import boto3
from botocore.client import Config
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from content_factory_api.config import ApiSettings, get_settings
from content_factory_api.database import get_db_session
from content_factory_api.modules.dependencies import get_current_user, require_roles
from content_factory_api.modules.domain import MUTATION_ROLES, AssetStatus
from content_factory_api.modules.models import Asset, Brand, User, new_id
from content_factory_api.modules.schemas import (
    AssetFinalizeRequest,
    AssetListResponse,
    AssetRead,
    AssetUploadInitiateRequest,
    AssetUploadInitiateResponse,
    UploadTargetRead,
)
from content_factory_api.modules.security import expires_in
from content_factory_api.modules.services import (
    commit_or_409,
    get_by_id_or_404,
    write_audit_log,
)

router = APIRouter(prefix="/api/assets", tags=["assets"])


def _safe_filename(filename: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "-", filename).strip("-") or "asset"


def _upload_url(settings: ApiSettings, asset: Asset) -> str:
    addressing_style = "path" if settings.s3_force_path_style else "virtual"
    s3_client = boto3.client(
        "s3",
        endpoint_url=str(settings.s3_endpoint).rstrip("/"),
        region_name=settings.s3_region,
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
        config=Config(signature_version="s3v4", s3={"addressing_style": addressing_style}),
    )
    url = s3_client.generate_presigned_url(
        "put_object",
        Params={
            "Bucket": settings.s3_bucket,
            "Key": asset.object_key,
            "ContentType": asset.content_type,
        },
        ExpiresIn=settings.upload_url_expiration_minutes * 60,
        HttpMethod="PUT",
    )
    return cast(str, url)


@router.post(
    "/uploads",
    response_model=AssetUploadInitiateResponse,
    status_code=status.HTTP_201_CREATED,
)
def initiate_upload(
    request: AssetUploadInitiateRequest,
    current_user: Annotated[User, Depends(require_roles(*MUTATION_ROLES))],
    db_session: Annotated[Session, Depends(get_db_session)],
    settings: Annotated[ApiSettings, Depends(get_settings)],
) -> AssetUploadInitiateResponse:
    get_by_id_or_404(db_session, Brand, request.brand_id, "Brand")
    upload_expires_at = expires_in(minutes=settings.upload_url_expiration_minutes)
    filename = _safe_filename(request.filename)
    asset_id = new_id()
    asset = Asset(
        id=asset_id,
        brand_id=request.brand_id,
        created_by_user_id=current_user.id,
        object_key=f"uploads/{request.brand_id}/{asset_id}-{filename}",
        filename=request.filename,
        content_type=request.content_type,
        byte_size=request.byte_size,
        status=AssetStatus.PENDING_UPLOAD.value,
        upload_expires_at=upload_expires_at,
    )
    db_session.add(asset)
    db_session.flush()
    write_audit_log(
        db_session,
        actor_user_id=current_user.id,
        action="asset.upload_initiated",
        entity_type="asset",
        entity_id=asset.id,
        payload={"filename": asset.filename, "content_type": asset.content_type},
    )
    commit_or_409(db_session, "Asset upload could not be initiated")
    return AssetUploadInitiateResponse(
        asset=AssetRead.model_validate(asset),
        upload=UploadTargetRead(
            method="PUT",
            url=_upload_url(settings, asset),
            headers={"Content-Type": asset.content_type},
            expires_at=asset.upload_expires_at,
        ),
    )


@router.post("/{asset_id}/finalize", response_model=AssetRead)
def finalize_upload(
    asset_id: str,
    request: AssetFinalizeRequest,
    current_user: Annotated[User, Depends(require_roles(*MUTATION_ROLES))],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> Asset:
    asset = get_by_id_or_404(db_session, Asset, asset_id, "Asset")
    if asset.status != AssetStatus.PENDING_UPLOAD.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Asset is not pending upload",
        )

    asset.byte_size = request.byte_size
    asset.checksum_sha256 = request.checksum_sha256
    asset.status = AssetStatus.READY.value
    write_audit_log(
        db_session,
        actor_user_id=current_user.id,
        action="asset.upload_finalized",
        entity_type="asset",
        entity_id=asset.id,
        payload={"byte_size": request.byte_size},
    )
    db_session.commit()
    return asset


@router.get("", response_model=AssetListResponse)
def list_assets(
    _current_user: Annotated[User, Depends(get_current_user)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> AssetListResponse:
    assets = list(
        db_session.scalars(select(Asset).order_by(Asset.created_at.desc()))
    )
    return AssetListResponse(items=[AssetRead.model_validate(asset) for asset in assets])
