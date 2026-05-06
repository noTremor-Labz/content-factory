from typing import Annotated

from fastapi import Depends, FastAPI

from content_factory_api import API_VERSION
from content_factory_api.config import ApiSettings, get_settings
from content_factory_api.health import router as health_router
from content_factory_api.logging import configure_observability


def provide_settings() -> ApiSettings:
    return get_settings()


def create_app() -> FastAPI:
    settings = get_settings()
    configure_observability(
        service_name=settings.app_name,
        app_env=settings.app_env,
        sentry_dsn=settings.sentry_dsn,
    )

    app = FastAPI(
        title=settings.app_name,
        version=API_VERSION,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    @app.get("/")
    def root(
        current_settings: Annotated[ApiSettings, Depends(provide_settings)],
    ) -> dict[str, str]:
        return {
            "name": current_settings.app_name,
            "phase": "phase-1-bootstrap",
            "status": "ready",
            "version": API_VERSION,
        }

    @app.get("/api/meta")
    def meta(
        current_settings: Annotated[ApiSettings, Depends(provide_settings)],
    ) -> dict[str, str]:
        return {
            "environment": current_settings.app_env,
            "service": current_settings.app_name,
            "version": API_VERSION,
        }

    app.include_router(health_router)
    return app
