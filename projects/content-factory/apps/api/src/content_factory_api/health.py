from typing import Annotated

from fastapi import APIRouter, Depends

from content_factory_api import API_VERSION
from content_factory_api.config import ApiSettings, get_settings

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/live")
def live(settings: Annotated[ApiSettings, Depends(get_settings)]) -> dict[str, str]:
    return {
        "service": settings.app_name,
        "status": "ok",
        "version": API_VERSION,
    }


@router.get("/ready")
def ready(settings: Annotated[ApiSettings, Depends(get_settings)]) -> dict[str, object]:
    return {
        "service": settings.app_name,
        "status": "ready",
        "checks": {
            "config": "ok",
            "database_url": str(settings.database_url),
            "redis_url": str(settings.redis_url),
            "object_storage_bucket": settings.s3_bucket,
        },
    }
