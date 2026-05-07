"""add compliance gate

Revision ID: 20260507_0005
Revises: 20260507_0004
Create Date: 2026-05-07
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260507_0005"
down_revision: str | None = "20260507_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "compliance_rules",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("key", sa.String(length=120), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("severity", sa.String(length=32), nullable=False),
        sa.Column("reason_code", sa.String(length=120), nullable=False),
        sa.Column("pattern", sa.Text(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key"),
    )
    op.create_index(op.f("ix_compliance_rules_key"), "compliance_rules", ["key"], unique=True)

    op.create_table(
        "compliance_checks",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("content_item_id", sa.String(length=36), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("risk_score", sa.Integer(), nullable=False),
        sa.Column("flags", sa.JSON(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("evaluated_by_user_id", sa.String(length=36), nullable=True),
        sa.Column("evaluated_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["content_item_id"], ["content_items.id"]),
        sa.ForeignKeyConstraint(["evaluated_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_compliance_checks_content_item_id"),
        "compliance_checks",
        ["content_item_id"],
        unique=False,
    )

    with op.batch_alter_table("review_tasks") as batch_op:
        batch_op.add_column(sa.Column("compliance_check_id", sa.String(length=36), nullable=True))
        batch_op.add_column(sa.Column("compliance_override_reason", sa.Text(), nullable=True))
        batch_op.create_foreign_key(
            "fk_review_tasks_compliance_check_id_compliance_checks",
            "compliance_checks",
            ["compliance_check_id"],
            ["id"],
        )


def downgrade() -> None:
    with op.batch_alter_table("review_tasks") as batch_op:
        batch_op.drop_constraint(
            "fk_review_tasks_compliance_check_id_compliance_checks",
            type_="foreignkey",
        )
        batch_op.drop_column("compliance_override_reason")
        batch_op.drop_column("compliance_check_id")
    op.drop_index(op.f("ix_compliance_checks_content_item_id"), table_name="compliance_checks")
    op.drop_table("compliance_checks")
    op.drop_index(op.f("ix_compliance_rules_key"), table_name="compliance_rules")
    op.drop_table("compliance_rules")
