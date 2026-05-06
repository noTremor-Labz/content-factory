from content_factory_worker.broker import configure_broker
from content_factory_worker.config import get_worker_settings
from content_factory_worker.logging import configure_observability


def bootstrap_worker() -> str:
    settings = get_worker_settings()
    configure_observability(
        worker_name=settings.worker_name,
        app_env=settings.app_env,
        sentry_dsn=settings.sentry_dsn,
    )
    configure_broker(settings)
    return settings.worker_name
