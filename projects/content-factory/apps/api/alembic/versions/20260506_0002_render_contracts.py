"""render contracts baseline

Revision ID: 20260506_0002
Revises: 20260506_0001
Create Date: 2026-05-06
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260506_0002"
down_revision: str | None = "20260506_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "workflow_presets",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("key", sa.String(length=120), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("workflow_provider", sa.String(length=64), nullable=False),
        sa.Column("voice_provider", sa.String(length=64), nullable=False),
        sa.Column("packaging_provider", sa.String(length=64), nullable=False),
        sa.Column("workflow_definition", sa.JSON(), nullable=False),
        sa.Column("input_mapping", sa.JSON(), nullable=False),
        sa.Column("output_mapping", sa.JSON(), nullable=False),
        sa.Column("created_by_user_id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key", "version", name="uq_workflow_presets_key_version"),
    )
    op.create_index(op.f("ix_workflow_presets_key"), "workflow_presets", ["key"], unique=False)

    op.create_table(
        "render_jobs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("content_item_id", sa.String(length=36), nullable=False),
        sa.Column("workflow_preset_id", sa.String(length=36), nullable=False),
        sa.Column("workflow_preset_key", sa.String(length=120), nullable=False),
        sa.Column("workflow_preset_version", sa.Integer(), nullable=False),
        sa.Column("workflow_provider", sa.String(length=64), nullable=False),
        sa.Column("voice_provider", sa.String(length=64), nullable=False),
        sa.Column("packaging_provider", sa.String(length=64), nullable=False),
        sa.Column("input_snapshot", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("retry_budget", sa.Integer(), nullable=False),
        sa.Column("created_by_user_id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["content_item_id"], ["content_items.id"]),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["workflow_preset_id"], ["workflow_presets.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_render_jobs_content_item_id"), "render_jobs", ["content_item_id"], unique=False)
    op.create_index(
        op.f("ix_render_jobs_workflow_preset_id"),
        "render_jobs",
        ["workflow_preset_id"],
        unique=False,
    )

    op.create_table(
        "job_attempts",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("render_job_id", sa.String(length=36), nullable=False),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("provider_job_id", sa.String(length=255), nullable=True),
        sa.Column("request_payload", sa.JSON(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["render_job_id"], ["render_jobs.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("render_job_id", "attempt_number", name="uq_job_attempts_job_attempt"),
    )
    op.create_index(op.f("ix_job_attempts_render_job_id"), "job_attempts", ["render_job_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_job_attempts_render_job_id"), table_name="job_attempts")
    op.drop_table("job_attempts")
    op.drop_index(op.f("ix_render_jobs_workflow_preset_id"), table_name="render_jobs")
    op.drop_index(op.f("ix_render_jobs_content_item_id"), table_name="render_jobs")
    op.drop_table("render_jobs")
    op.drop_index(op.f("ix_workflow_presets_key"), table_name="workflow_presets")
    op.drop_table("workflow_presets")
