import pytest
from dramatiq.brokers.stub import StubBroker
from pydantic import ValidationError

from content_factory_worker.broker import create_broker
from content_factory_worker.config import WorkerSettings, get_worker_settings


def test_worker_settings_use_local_defaults() -> None:
    settings = get_worker_settings()

    assert settings.worker_name == "content-factory-worker"
    assert str(settings.redis_url) == "redis://localhost:6379/0"
    assert settings.worker_concurrency == 1


def test_worker_settings_reject_zero_concurrency(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WORKER_CONCURRENCY", "0")

    with pytest.raises(ValidationError):
        get_worker_settings()


def test_worker_uses_stub_broker_in_test_environment() -> None:
    settings = WorkerSettings(app_env="test")

    assert isinstance(create_broker(settings), StubBroker)
