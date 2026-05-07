from typing import Annotated, cast

import boto3
from botocore.client import Config
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from content_factory_api.config import ApiSettings, get_settings
from content_factory_api.database import get_db_session
from content_factory_api.modules.dependencies import get_current_user, require_roles
from content_factory_api.modules.domain import (
    MUTATION_ROLES,
    ContentStatus,
    PublishPackageStatus,
    RenderJobStatus,
)
from content_factory_api.modules.models import ContentItem, PublishPackage, RenderJob, User
from content_factory_api.modules.schemas import (
    DownloadTargetRead,
    PublishPackageCreateRequest,
    PublishPackageDownloadResponse,
    PublishPackageListResponse,
    PublishPackageRead,
)
from content_factory_api.modules.security import expires_in
from content_factory_api.modules.services import (
    commit_or_409,
    get_by_id_or_404,
    write_audit_log,
)

router = APIRouter(prefix="/api/publish-packages", tags=["publish-packages"])


@router.post("", response_model=PublishPackageRead, status_code=status.HTTP_201_CREATED)
def create_publish_package(
    request: PublishPackageCreateRequest,
    response: Response,
    current_user: Annotated[User, Depends(require_roles(*MUTATION_ROLES))],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> PublishPackage:
    render_job = get_by_id_or_404(db_session, RenderJob, request.render_job_id, "Render job")
    content_item = get_by_id_or_404(
        db_session,
        ContentItem,
        render_job.content_item_id,
        "Content item",
    )

    if render_job.status != RenderJobStatus.SUCCEEDED.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Render job must succeed before package export",
        )

    if content_item.status != ContentStatus.APPROVED.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Content item must be approved before package export",
        )

    existing_package = db_session.scalar(
        select(PublishPackage).where(PublishPackage.render_job_id == render_job.id)
    )
    if existing_package is not None:
        response.status_code = status.HTTP_200_OK
        return existing_package

    publish_package = PublishPackage(
        render_job_id=render_job.id,
        content_item_id=content_item.id,
        status=PublishPackageStatus.QUEUED.value,
        created_by_user_id=current_user.id,
    )
    db_session.add(publish_package)
    db_session.flush()
    write_audit_log(
        db_session,
        actor_user_id=current_user.id,
        action="publish_package.created",
        entity_type="publish_package",
        entity_id=publish_package.id,
        payload={"render_job_id": render_job.id, "content_item_id": content_item.id},
    )
    commit_or_409(db_session, "Publish package could not be created")

    from content_factory_worker.queue import enqueue_publish_package

    enqueue_publish_package(publish_package.id)
    return publish_package


@router.get("", response_model=PublishPackageListResponse)
def list_publish_packages(
    _current_user: Annotated[User, Depends(get_current_user)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> PublishPackageListResponse:
    packages = list(
        db_session.scalars(select(PublishPackage).order_by(PublishPackage.created_at.desc()))
    )
    return PublishPackageListResponse(
        items=[PublishPackageRead.model_validate(package) for package in packages]
    )


@router.get("/{package_id}", response_model=PublishPackageRead)
def get_publish_package(
    package_id: str,
    _current_user: Annotated[User, Depends(get_current_user)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> PublishPackage:
    return get_by_id_or_404(db_session, PublishPackage, package_id, "Publish package")


@router.get("/{package_id}/download", response_model=PublishPackageDownloadResponse)
def get_publish_package_download(
    package_id: str,
    _current_user: Annotated[User, Depends(get_current_user)],
    db_session: Annotated[Session, Depends(get_db_session)],
    settings: Annotated[ApiSettings, Depends(get_settings)],
) -> PublishPackageDownloadResponse:
    publish_package = get_by_id_or_404(
        db_session,
        PublishPackage,
        package_id,
        "Publish package",
    )
    if (
        publish_package.status != PublishPackageStatus.READY.value
        or publish_package.package_object_key is None
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Publish package is not ready for download",
        )

    return PublishPackageDownloadResponse(
        package=PublishPackageRead.model_validate(publish_package),
        download=DownloadTargetRead(
            method="GET",
            url=_download_url(settings, publish_package.package_object_key),
            headers={},
            expires_at=expires_in(minutes=settings.upload_url_expiration_minutes),
        ),
    )


def _download_url(settings: ApiSettings, object_key: str) -> str:
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
        "get_object",
        Params={"Bucket": settings.s3_bucket, "Key": object_key},
        ExpiresIn=settings.upload_url_expiration_minutes * 60,
        HttpMethod="GET",
    )
    return cast(str, url)
