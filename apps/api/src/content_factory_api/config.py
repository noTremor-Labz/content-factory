from functools import lru_cache
from typing import Literal

from pydantic import AnyHttpUrl, Field, PositiveInt, PostgresDsn, RedisDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class ApiSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Content Factory API"
    app_env: Literal["development", "test", "staging", "production"] = "development"
    api_host: str = "0.0.0.0"
    api_port: PositiveInt = 8000
    database_url: PostgresDsn = Field(
        default_factory=lambda: PostgresDsn(
            "postgresql://content_factory:content_factory@localhost:5432/content_factory"
        )
    )
    redis_url: RedisDsn = Field(default_factory=lambda: RedisDsn("redis://localhost:6379/0"))
    s3_endpoint: AnyHttpUrl = Field(default_factory=lambda: AnyHttpUrl("http://localhost:9000"))
    s3_region: str = "us-east-1"
    s3_bucket: str = Field(default="content-factory-assets", min_length=3)
    s3_access_key: str = Field(default="minioadmin", min_length=1)
    s3_secret_key: str = Field(default="minioadmin", min_length=1)
    s3_force_path_style: bool = True
    sentry_dsn: str | None = None


@lru_cache(maxsize=1)
def get_settings() -> ApiSettings:
    return ApiSettings()
