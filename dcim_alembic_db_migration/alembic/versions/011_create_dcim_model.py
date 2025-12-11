"""
create dcim_model table

Revision ID: 011_create_dcim_model
Revises: 010_create_dcim_device_type
Create Date: 2025-11-20 00:00:12.000000
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

revision = "011_create_dcim_model"
down_revision = "010_create_dcim_device_type"
branch_labels = None
depends_on = None

TABLE_NAME = "dcim_model"
SCHEMA = "dcim"
SEQ_NAME = f"{TABLE_NAME}_seq"
TRG_NAME = f"{TABLE_NAME}_trg"


def _create_table() -> None:
    if not table_exists(SCHEMA, TABLE_NAME):
        op.create_table(
            TABLE_NAME,
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("name", sa.String(255), nullable=False, unique=True),
            sa.Column("make_id", sa.Integer(), sa.ForeignKey("dcim.dcim_make.id", ondelete="CASCADE"), nullable=False),
            sa.Column("device_type_id", sa.Integer(), sa.ForeignKey("dcim.dcim_device_type.id", ondelete="CASCADE"), nullable=False),
            sa.Column("height", sa.Integer(), nullable=False),
            sa.Column("description", sa.String(255), nullable=True),
            sa.Column("front_image_path", sa.String(512), nullable=True),
            sa.Column("rear_image_path", sa.String(512), nullable=True),
            schema=SCHEMA,
        )

    if not index_exists(SCHEMA, "ix_dcim_model_make_id"):
        op.create_index("ix_dcim_model_make_id", TABLE_NAME, ["make_id"], schema=SCHEMA)
    if not index_exists(SCHEMA, "ix_dcim_model_device_type_id"):
        op.create_index("ix_dcim_model_device_type_id", TABLE_NAME, ["device_type_id"], schema=SCHEMA)


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
    op.drop_index("ix_dcim_model_make_id", table_name=TABLE_NAME, schema=SCHEMA)
    op.drop_index("ix_dcim_model_device_type_id", table_name=TABLE_NAME, schema=SCHEMA)
    op.drop_table(TABLE_NAME, schema=SCHEMA)
