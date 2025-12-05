"""
create dcim_user table

Revision ID: 001_create_dcim_user
Revises:
Create Date: 2025-11-20 00:00:01.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from oracle_helpers import (
    table_exists,
    create_sequence_if_not_exists,
    create_trigger_for_autoincrement,
    drop_trigger_if_exists,
    drop_sequence_if_exists,
)

revision = "001_create_dcim_user"
down_revision = None
branch_labels = None
depends_on = None

TABLE_NAME = "dcim_user"
SCHEMA = "dcim"
SEQ_NAME = f"{TABLE_NAME}_seq"
TRG_NAME = f"{TABLE_NAME}_trg"


def _create_table() -> None:
    if not table_exists(SCHEMA, TABLE_NAME):
        op.create_table(
            TABLE_NAME,
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("name", sa.String(255), nullable=False, unique=True),
            sa.Column("email", sa.String(255), nullable=False, unique=True),
            sa.Column("full_name", sa.String(255)),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("last_login", sa.DateTime(), nullable=True),
            sa.Column("description", sa.String(255), nullable=True),
            schema=SCHEMA,
        )


def _create_sequence_and_trigger() -> None:
    """Create Oracle sequence and trigger for auto-increment ID."""
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
    op.drop_table(TABLE_NAME, schema=SCHEMA)
