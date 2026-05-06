import pytest
from fastapi.testclient import TestClient

from content_factory_api.app import create_app
from content_factory_api.config import get_settings


@pytest.fixture(autouse=True)
def reset_api_settings_cache() -> None:
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def api_client() -> TestClient:
    return TestClient(create_app())
