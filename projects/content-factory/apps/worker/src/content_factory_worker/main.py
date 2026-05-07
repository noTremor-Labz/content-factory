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
    import content_factory_worker.jobs.packaging as _packaging_jobs
    import content_factory_worker.jobs.render as _render_jobs

    _ = _packaging_jobs
    _ = _render_jobs
    return settings.worker_name
