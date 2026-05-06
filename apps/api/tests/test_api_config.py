import pytest
from pydantic import ValidationError

from content_factory_api.config import get_settings


def test_api_settings_use_local_defaults() -> None:
    settings = get_settings()

    assert settings.app_name == "Content Factory API"
    assert str(settings.database_url) == "postgresql://content_factory:content_factory@localhost:5432/content_factory"
    assert str(settings.redis_url) == "redis://localhost:6379/0"


def test_api_settings_reject_invalid_port(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("API_PORT", "0")

    with pytest.raises(ValidationError):
        get_settings()
