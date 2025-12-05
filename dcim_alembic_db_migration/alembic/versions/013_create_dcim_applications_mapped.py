"""
create dcim_applications_mapped table

Revision ID: 013_create_dcim_applications_mapped
Revises: 012_create_dcim_asset_owner
Create Date: 2025-11-20 00:00:16.000000
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

revision = "013_create_dcim_applications_mapped"
down_revision = "012_create_dcim_asset_owner"
branch_labels = None
depends_on = None

TABLE_NAME = "dcim_applications_mapped"
SCHEMA = "dcim"
SEQ_NAME = f"{TABLE_NAME}_seq"
TRG_NAME = f"{TABLE_NAME}_trg"


def _create_table() -> None:
    if not table_exists(SCHEMA, TABLE_NAME):
        op.create_table(
            TABLE_NAME,
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("name", sa.String(255), nullable=False),
            sa.Column("asset_owner_id", sa.Integer(), sa.ForeignKey("dcim.dcim_asset_owner.id"), nullable=True),
            sa.Column("description", sa.String(255), nullable=True),
            schema=SCHEMA,
        )

    if not index_exists(SCHEMA, "ix_dcim_applications_mapped_asset_owner_id"):
        op.create_index("ix_dcim_applications_mapped_asset_owner_id", TABLE_NAME, ["asset_owner_id"], schema=SCHEMA)
    if not index_exists(SCHEMA, "ix_dcim_applications_mapped_name"):
        op.create_index("ix_dcim_applications_mapped_name", TABLE_NAME, ["name"], schema=SCHEMA)


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
    op.drop_index("ix_dcim_applications_mapped_asset_owner_id", table_name=TABLE_NAME, schema=SCHEMA)
    op.drop_index("ix_dcim_applications_mapped_name", table_name=TABLE_NAME, schema=SCHEMA)
    op.drop_table(TABLE_NAME, schema=SCHEMA)
