from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from content_factory_api.app import create_app
from content_factory_api.config import get_settings
from content_factory_api.database import init_database, reset_database_caches


@pytest.fixture(autouse=True)
def reset_api_settings_cache() -> None:
    get_settings.cache_clear()
    reset_database_caches()
    yield
    get_settings.cache_clear()
    reset_database_caches()


@pytest.fixture
def api_app(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> FastAPI:
    db_path = tmp_path / "content_factory_test.db"
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
    get_settings.cache_clear()
    reset_database_caches()
    init_database()
    return create_app()


@pytest.fixture
def api_client(api_app: FastAPI) -> TestClient:
    return TestClient(api_app)
