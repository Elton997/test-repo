"""
create dcim_sub_menu table

Revision ID: 020_create_dcim_sub_menu
Revises: 019_create_dcim_menu
Create Date: 2025-11-20 00:00:20.000000
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

revision = "020_create_dcim_sub_menu"
down_revision = "019_create_dcim_menu"
branch_labels = None
depends_on = None

TABLE_NAME = "dcim_sub_menu"
SCHEMA = "dcim"
SEQ_NAME = f"{TABLE_NAME}_seq"
TRG_NAME = f"{TABLE_NAME}_trg"


def _create_table() -> None:
    if not table_exists(SCHEMA, TABLE_NAME):
        op.create_table(
            TABLE_NAME,
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("menu_id", sa.Integer(), sa.ForeignKey("dcim.dcim_menu.id"), nullable=False),
            sa.Column("display_name", sa.String(255), nullable=False),
            sa.Column("page_url", sa.String(255), nullable=False),
            sa.Column("icon", sa.String(255), nullable=True),
            sa.Column("code", sa.String(255), nullable=False, unique=True),
            sa.Column("sort_order", sa.Integer(), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
            sa.Column("description", sa.String(255), nullable=True),
            schema=SCHEMA,
        )

    if not index_exists(SCHEMA, "ix_dcim_sub_menu_menu_id"):
        op.create_index("ix_dcim_sub_menu_menu_id", TABLE_NAME, ["menu_id"], schema=SCHEMA)
    if not index_exists(SCHEMA, "ix_dcim_sub_menu_sort_order"):
        op.create_index("ix_dcim_sub_menu_sort_order", TABLE_NAME, ["sort_order"], schema=SCHEMA)


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
    op.drop_index("ix_dcim_sub_menu_sort_order", table_name=TABLE_NAME, schema=SCHEMA)
    op.drop_index("ix_dcim_sub_menu_menu_id", table_name=TABLE_NAME, schema=SCHEMA)
    op.drop_table(TABLE_NAME, schema=SCHEMA)

