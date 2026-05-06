import logging

import sentry_sdk
import structlog


def configure_observability(*, worker_name: str, app_env: str, sentry_dsn: str | None) -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.add_log_level,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
    )

    if sentry_dsn:
        sentry_sdk.init(
            dsn=sentry_dsn,
            environment=app_env,
            release="phase-1-bootstrap",
            server_name=worker_name,
            traces_sample_rate=0.0,
        )
