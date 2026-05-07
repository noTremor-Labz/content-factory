from functools import lru_cache
from typing import Literal

from pydantic import AnyHttpUrl, Field, PositiveFloat, PositiveInt, RedisDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class WorkerSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    worker_name: str = "content-factory-worker"
    app_env: Literal["development", "test", "staging", "production"] = "development"
    redis_url: RedisDsn = Field(default_factory=lambda: RedisDsn("redis://localhost:6379/0"))
    worker_concurrency: PositiveInt = 1
    comfyui_base_url: str | None = None
    comfyui_api_key: str | None = None
    comfyui_api_mode: Literal["local", "cloud"] = "local"
    comfyui_timeout_seconds: PositiveFloat = 300.0
    comfyui_poll_interval_seconds: PositiveFloat = 2.0
    comfyui_request_timeout_seconds: PositiveFloat = 30.0
    s3_endpoint: AnyHttpUrl = Field(default_factory=lambda: AnyHttpUrl("http://localhost:9000"))
    s3_region: str = "us-east-1"
    s3_bucket: str = Field(default="content-factory-assets", min_length=3)
    s3_access_key: str = Field(default="minioadmin", min_length=1)
    s3_secret_key: str = Field(default="minioadmin", min_length=1)
    s3_force_path_style: bool = True
    ffmpeg_path: str = Field(default="ffmpeg", min_length=1)
    ffmpeg_timeout_seconds: PositiveFloat = 300.0
    sentry_dsn: str | None = None

    @field_validator("comfyui_base_url", "comfyui_api_key", mode="before")
    @classmethod
    def normalize_optional_string(cls, value: object) -> object:
        if isinstance(value, str) and value.strip() == "":
            return None
        return value


@lru_cache(maxsize=1)
def get_worker_settings() -> WorkerSettings:
    return WorkerSettings()
