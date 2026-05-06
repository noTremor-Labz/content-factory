from collections.abc import Generator
from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from content_factory_api.config import get_settings


class Base(DeclarativeBase):
    pass


def normalize_database_url(database_url: str) -> str:
    if database_url.startswith("postgresql://"):
        return database_url.replace("postgresql://", "postgresql+psycopg://", 1)
    return database_url


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    database_url = normalize_database_url(get_settings().database_url)
    connect_args: dict[str, object] = {}
    if database_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
    return create_engine(database_url, connect_args=connect_args)


@lru_cache(maxsize=1)
def get_sessionmaker() -> sessionmaker[Session]:
    return sessionmaker(
        bind=get_engine(),
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )


def reset_database_caches() -> None:
    get_sessionmaker.cache_clear()
    get_engine.cache_clear()


def get_db_session() -> Generator[Session, None, None]:
    db_session = get_sessionmaker()()
    try:
        yield db_session
    finally:
        db_session.close()


def init_database() -> None:
    from content_factory_api.modules import models as _models

    _ = _models
    Base.metadata.create_all(bind=get_engine())
