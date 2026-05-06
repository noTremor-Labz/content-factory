from functools import lru_cache
from typing import Literal

from pydantic import Field, PositiveInt, RedisDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class WorkerSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    worker_name: str = "content-factory-worker"
    app_env: Literal["development", "test", "staging", "production"] = "development"
    redis_url: RedisDsn = Field(default_factory=lambda: RedisDsn("redis://localhost:6379/0"))
    worker_concurrency: PositiveInt = 1
    sentry_dsn: str | None = None


@lru_cache(maxsize=1)
def get_worker_settings() -> WorkerSettings:
    return WorkerSettings()
