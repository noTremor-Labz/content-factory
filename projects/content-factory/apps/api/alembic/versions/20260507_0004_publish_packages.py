"""add publish packages

Revision ID: 20260507_0004
Revises: 20260506_0003
Create Date: 2026-05-07
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260507_0004"
down_revision: str | None = "20260506_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "publish_packages",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("render_job_id", sa.String(length=36), nullable=False),
        sa.Column("content_item_id", sa.String(length=36), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("package_object_key", sa.String(length=700), nullable=True),
        sa.Column("manifest_payload", sa.JSON(), nullable=False),
        sa.Column("byte_size", sa.Integer(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_by_user_id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["content_item_id"], ["content_items.id"]),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["render_job_id"], ["render_jobs.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("render_job_id", name="uq_publish_packages_render_job"),
    )
    op.create_index(
        op.f("ix_publish_packages_content_item_id"),
        "publish_packages",
        ["content_item_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_publish_packages_render_job_id"),
        "publish_packages",
        ["render_job_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_publish_packages_render_job_id"), table_name="publish_packages")
    op.drop_index(op.f("ix_publish_packages_content_item_id"), table_name="publish_packages")
    op.drop_table("publish_packages")
