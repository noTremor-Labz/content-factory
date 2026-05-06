import pytest

from content_factory_worker.config import get_worker_settings


@pytest.fixture(autouse=True)
def reset_worker_settings_cache() -> None:
    get_worker_settings.cache_clear()
    yield
    get_worker_settings.cache_clear()
