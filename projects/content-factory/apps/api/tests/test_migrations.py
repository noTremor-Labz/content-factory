from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect


def test_alembic_upgrade_head_creates_control_plane_tables(tmp_path: Path) -> None:
    db_path = tmp_path / "migration-smoke.db"
    database_url = f"sqlite:///{db_path}"
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", database_url)

    command.upgrade(config, "head")

    engine = create_engine(database_url)
    table_names = set(inspect(engine).get_table_names())

    assert {
        "users",
        "invites",
        "user_sessions",
        "brands",
        "avatars",
        "identity_packs",
        "assets",
        "content_items",
        "review_tasks",
        "audit_logs",
        "workflow_presets",
        "render_jobs",
        "job_attempts",
        "publish_packages",
    }.issubset(table_names)
