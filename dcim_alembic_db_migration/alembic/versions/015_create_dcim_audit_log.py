"""
create dcim_audit_log table

Revision ID: 015_create_dcim_audit_log
Revises: 014_create_dcim_device
Create Date: 2025-11-20 00:00:13.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from oracle_helpers import (
    table_exists,
    index_exists,
    create_sequence_if_not_exists,
    create_trigger_for_autoincrement,
    drop_trigger_if_exists,
    drop_sequence_if_exists,
)

revision = "015_create_dcim_audit_log"
down_revision = "014_create_dcim_device"
branch_labels = None
depends_on = None

TABLE_NAME = "dcim_audit_log"
SCHEMA = "dcim"
SEQ_NAME = f"{TABLE_NAME}_seq"
TRG_NAME = f"{TABLE_NAME}_trg"


def _create_table() -> None:
    if not table_exists(SCHEMA, TABLE_NAME):
        op.create_table(
            TABLE_NAME,
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("time", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("dcim.dcim_user.id"), nullable=True),
            sa.Column("action", sa.String(255), nullable=False),
            sa.Column("type", sa.String(255), nullable=False),
            sa.Column("object_id", sa.Integer(), nullable=True),
            sa.Column("message", sa.Text(), nullable=True),
            sa.Column("description", sa.String(255), nullable=True),
            schema=SCHEMA,
        )

    if not index_exists(SCHEMA, "ix_dcim_audit_log_user_id"):
        op.create_index("ix_dcim_audit_log_user_id", TABLE_NAME, ["user_id"], schema=SCHEMA)
    if not index_exists(SCHEMA, "ix_dcim_audit_log_type"):
        op.create_index("ix_dcim_audit_log_type", TABLE_NAME, ["type"], schema=SCHEMA)


def _create_sequence_and_trigger() -> None:
    create_sequence_if_not_exists(SCHEMA, SEQ_NAME)
    create_trigger_for_autoincrement(SCHEMA, TABLE_NAME, TRG_NAME, SEQ_NAME)


def _update_table() -> None:
    pass


def upgrade() -> None:
    _create_table()
    _create_sequence_and_trigger()
    _update_table()


def downgrade() -> None:
    drop_trigger_if_exists(SCHEMA, TRG_NAME)
    drop_sequence_if_exists(SCHEMA, SEQ_NAME)
    op.drop_index("ix_dcim_audit_log_type", table_name=TABLE_NAME, schema=SCHEMA)
    op.drop_index("ix_dcim_audit_log_user_id", table_name=TABLE_NAME, schema=SCHEMA)
    op.drop_table(TABLE_NAME, schema=SCHEMA)
