import pytest
from pydantic import ValidationError

from content_factory_api.config import get_settings


def test_api_settings_use_local_defaults() -> None:
    settings = get_settings()

    assert settings.app_name == "Content Factory API"
    assert str(settings.database_url) == "postgresql://content_factory:content_factory@localhost:5432/content_factory"
    assert str(settings.redis_url) == "redis://localhost:6379/0"
    assert "http://localhost:5173" in settings.cors_origin_list


def test_api_settings_reject_invalid_port(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("API_PORT", "0")

    with pytest.raises(ValidationError):
        get_settings()


def test_api_settings_accept_comma_separated_cors_origins(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:5173, http://localhost:4173")

    settings = get_settings()

    assert settings.cors_origin_list == ["http://localhost:5173", "http://localhost:4173"]
