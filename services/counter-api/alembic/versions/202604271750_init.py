"""init schema

Revision ID: 202604271750
Revises:
Create Date: 2026-04-27 17:50:00
"""

from alembic import op
import sqlalchemy as sa

revision = "202604271750"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "counters",
        sa.Column("key", sa.String(length=255), primary_key=True),
        sa.Column("value", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "idempotency_records",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("request_key", sa.String(length=255), nullable=False),
        sa.Column("counter_key", sa.String(length=255), nullable=False),
        sa.Column("response_value", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("request_key", name="uq_idempotency_request_key"),
    )
    op.create_index("ix_idempotency_records_counter_key", "idempotency_records", ["counter_key"])


def downgrade() -> None:
    op.drop_index("ix_idempotency_records_counter_key", table_name="idempotency_records")
    op.drop_table("idempotency_records")
    op.drop_table("counters")
