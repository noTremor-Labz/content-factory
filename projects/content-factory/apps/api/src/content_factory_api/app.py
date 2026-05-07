from typing import Annotated

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from content_factory_api import API_VERSION
from content_factory_api.config import ApiSettings, get_settings
from content_factory_api.health import router as health_router
from content_factory_api.logging import configure_observability
from content_factory_api.modules.assets import router as assets_router
from content_factory_api.modules.audit import router as audit_router
from content_factory_api.modules.auth import router as auth_router
from content_factory_api.modules.avatars import router as avatars_router
from content_factory_api.modules.brands import router as brands_router
from content_factory_api.modules.compliance import router as compliance_router
from content_factory_api.modules.content import router as content_router
from content_factory_api.modules.exports import router as exports_router
from content_factory_api.modules.render import router as render_router
from content_factory_api.modules.review import router as review_router
from content_factory_api.modules.users import router as users_router
from content_factory_api.modules.workflows import router as workflows_router


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

    if settings.cors_origin_list:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origin_list,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    @app.get("/")
    def root(
        current_settings: Annotated[ApiSettings, Depends(provide_settings)],
    ) -> dict[str, str]:
        return {
            "name": current_settings.app_name,
            "phase": "phase-1-control-plane",
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
    app.include_router(auth_router)
    app.include_router(users_router)
    app.include_router(brands_router)
    app.include_router(avatars_router)
    app.include_router(assets_router)
    app.include_router(content_router)
    app.include_router(compliance_router)
    app.include_router(workflows_router)
    app.include_router(render_router)
    app.include_router(exports_router)
    app.include_router(review_router)
    app.include_router(audit_router)
    return app
