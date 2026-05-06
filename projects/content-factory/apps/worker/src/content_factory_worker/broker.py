import dramatiq
from dramatiq.brokers.redis import RedisBroker
from dramatiq.brokers.stub import StubBroker

from content_factory_worker.config import WorkerSettings


def create_broker(settings: WorkerSettings) -> RedisBroker | StubBroker:
    if settings.app_env == "test":
        return StubBroker()

    return RedisBroker(url=str(settings.redis_url))  # type: ignore[no-untyped-call]


def configure_broker(settings: WorkerSettings) -> RedisBroker | StubBroker:
    broker = create_broker(settings)
    dramatiq.set_broker(broker)
    return broker
