"""
create dcim_rack table

Revision ID: 008_create_dcim_rack
Revises: 007_create_dcim_datacenter
Create Date: 2025-11-20 00:00:08.000000
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

revision = "008_create_dcim_rack"
down_revision = "007_create_dcim_datacenter"
branch_labels = None
depends_on = None

TABLE_NAME = "dcim_rack"
SCHEMA = "dcim"
SEQ_NAME = f"{TABLE_NAME}_seq"
TRG_NAME = f"{TABLE_NAME}_trg"


def _create_table() -> None:
    if not table_exists(SCHEMA, TABLE_NAME):
        op.create_table(
            TABLE_NAME,
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("name", sa.String(255), nullable=False, unique=True),
            sa.Column("building_id", sa.Integer(), sa.ForeignKey("dcim.dcim_building.id"), nullable=False),
            sa.Column("location_id", sa.Integer(), sa.ForeignKey("dcim.dcim_location.id"), nullable=False),
            sa.Column("wing_id", sa.Integer(), sa.ForeignKey("dcim.dcim_wing.id"), nullable=False),
            sa.Column("floor_id", sa.Integer(), sa.ForeignKey("dcim.dcim_floor.id"), nullable=False),
            sa.Column("datacenter_id", sa.Integer(), sa.ForeignKey("dcim.dcim_datacenter.id"), nullable=False),
            sa.Column("status", sa.String(255), nullable=False, server_default=sa.text("'active'")),
            sa.Column("width", sa.Integer(), nullable=True),
            sa.Column("height", sa.Integer(), nullable=True),
            sa.Column("space_used", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("space_available", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("last_updated", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("description", sa.String(255), nullable=True),
            schema=SCHEMA,
        )

    if not index_exists(SCHEMA, "ix_dcim_rack_building_id"):
        op.create_index("ix_dcim_rack_building_id", TABLE_NAME, ["building_id"], schema=SCHEMA)
    if not index_exists(SCHEMA, "ix_dcim_rack_location_id"):
        op.create_index("ix_dcim_rack_location_id", TABLE_NAME, ["location_id"], schema=SCHEMA)
    if not index_exists(SCHEMA, "ix_dcim_rack_wing_id"):
        op.create_index("ix_dcim_rack_wing_id", TABLE_NAME, ["wing_id"], schema=SCHEMA)
    if not index_exists(SCHEMA, "ix_dcim_rack_floor_id"):
        op.create_index("ix_dcim_rack_floor_id", TABLE_NAME, ["floor_id"], schema=SCHEMA)
    if not index_exists(SCHEMA, "ix_dcim_rack_datacenter_id"):
        op.create_index("ix_dcim_rack_datacenter_id", TABLE_NAME, ["datacenter_id"], schema=SCHEMA)


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
    op.drop_index("ix_dcim_rack_location_id", table_name=TABLE_NAME, schema=SCHEMA)
    op.drop_index("ix_dcim_rack_building_id", table_name=TABLE_NAME, schema=SCHEMA)
    op.drop_index("ix_dcim_rack_wing_id", table_name=TABLE_NAME, schema=SCHEMA)
    op.drop_index("ix_dcim_rack_floor_id", table_name=TABLE_NAME, schema=SCHEMA)
    op.drop_index("ix_dcim_rack_datacenter_id", table_name=TABLE_NAME, schema=SCHEMA)
    op.drop_table(TABLE_NAME, schema=SCHEMA)
