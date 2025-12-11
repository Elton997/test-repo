"""
create dcim_device table

Revision ID: 014_create_dcim_device
Revises: 013_create_dcim_applications_mapped
Create Date: 2025-11-20 00:00:09.000000
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

revision = "014_create_dcim_device"
down_revision = "013_create_dcim_applications_mapped"
branch_labels = None
depends_on = None

TABLE_NAME = "dcim_device"
SCHEMA = "dcim"
SEQ_NAME = f"{TABLE_NAME}_seq"
TRG_NAME = f"{TABLE_NAME}_trg"


def _create_table() -> None:
    if not table_exists(SCHEMA, TABLE_NAME):
        op.create_table(
            TABLE_NAME,
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("name", sa.String(255), nullable=False, unique=True),
            sa.Column("serial_no", sa.String(255), nullable=True),
            sa.Column("position", sa.Integer(), nullable=True),
            sa.Column("face_front", sa.Boolean(), nullable=False, server_default=sa.text("0")),
            sa.Column("face_rear", sa.Boolean(), nullable=False, server_default=sa.text("0")),
            sa.Column("status", sa.String(255), nullable=False, server_default=sa.text("'active'")),
            sa.Column("devicetype_id", sa.Integer(), nullable=True),
            sa.Column("building_id", sa.Integer(), sa.ForeignKey("dcim.dcim_building.id"), nullable=False),
            sa.Column("location_id", sa.Integer(), sa.ForeignKey("dcim.dcim_location.id"), nullable=False),
            sa.Column("rack_id", sa.Integer(), sa.ForeignKey("dcim.dcim_rack.id"), nullable=True),
            sa.Column("dc_id", sa.Integer(), sa.ForeignKey("dcim.dcim_datacenter.id"), nullable=True),
            sa.Column("wings_id", sa.Integer(), sa.ForeignKey("dcim.dcim_wing.id"), nullable=True),
            sa.Column("floor_id", sa.Integer(), sa.ForeignKey("dcim.dcim_floor.id"), nullable=True),
            sa.Column("make_id", sa.Integer(), sa.ForeignKey("dcim.dcim_make.id"), nullable=True),
            sa.Column("ip", sa.String(255), nullable=True),
            sa.Column("po_number", sa.String(255), nullable=True),
            sa.Column("asset_user", sa.String(255), nullable=False, server_default=sa.text("'instock'")),
            sa.Column("applications_mapped_id", sa.Integer(), sa.ForeignKey("dcim.dcim_applications_mapped.id"), nullable=True),
            sa.Column("warranty_start_date", sa.Date(), nullable=True),
            sa.Column("warranty_end_date", sa.Date(), nullable=True),
            sa.Column("amc_start_date", sa.Date(), nullable=True),
            sa.Column("amc_end_date", sa.Date(), nullable=True),
            sa.Column("space_required", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("last_updated", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("description", sa.String(255), nullable=True),
            schema=SCHEMA,
        )

    if not index_exists(SCHEMA, "ix_dcim_device_serial_no"):
        op.create_index("ix_dcim_device_serial_no", TABLE_NAME, ["serial_no"], schema=SCHEMA)
    if not index_exists(SCHEMA, "ix_dcim_device_building_id"):
        op.create_index("ix_dcim_device_building_id", TABLE_NAME, ["building_id"], schema=SCHEMA)
    if not index_exists(SCHEMA, "ix_dcim_device_location_id"):
        op.create_index("ix_dcim_device_location_id", TABLE_NAME, ["location_id"], schema=SCHEMA)
    if not index_exists(SCHEMA, "ix_dcim_device_rack_id"):
        op.create_index("ix_dcim_device_rack_id", TABLE_NAME, ["rack_id"], schema=SCHEMA)
    if not index_exists(SCHEMA, "ix_dcim_device_dc_id"):
        op.create_index("ix_dcim_device_dc_id", TABLE_NAME, ["dc_id"], schema=SCHEMA)
    if not index_exists(SCHEMA, "ix_dcim_device_wings_id"):
        op.create_index("ix_dcim_device_wings_id", TABLE_NAME, ["wings_id"], schema=SCHEMA)
    if not index_exists(SCHEMA, "ix_dcim_device_floor_id"):
        op.create_index("ix_dcim_device_floor_id", TABLE_NAME, ["floor_id"], schema=SCHEMA)
    if not index_exists(SCHEMA, "ix_dcim_device_make_id"):
        op.create_index("ix_dcim_device_make_id", TABLE_NAME, ["make_id"], schema=SCHEMA)
    if not index_exists(SCHEMA, "ix_dcim_device_applications_mapped_id"):
        op.create_index("ix_dcim_device_applications_mapped_id", TABLE_NAME, ["applications_mapped_id"], schema=SCHEMA)


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
    op.drop_index("ix_dcim_device_floor_id", table_name=TABLE_NAME, schema=SCHEMA)
    op.drop_index("ix_dcim_device_wings_id", table_name=TABLE_NAME, schema=SCHEMA)
    op.drop_index("ix_dcim_device_dc_id", table_name=TABLE_NAME, schema=SCHEMA)
    op.drop_index("ix_dcim_device_rack_id", table_name=TABLE_NAME, schema=SCHEMA)
    op.drop_index("ix_dcim_device_location_id", table_name=TABLE_NAME, schema=SCHEMA)
    op.drop_index("ix_dcim_device_building_id", table_name=TABLE_NAME, schema=SCHEMA)
    op.drop_index("ix_dcim_device_serial_no", table_name=TABLE_NAME, schema=SCHEMA)
    op.drop_index("ix_dcim_device_make_id", table_name=TABLE_NAME, schema=SCHEMA)
    op.drop_index("ix_dcim_device_applications_mapped_id", table_name=TABLE_NAME, schema=SCHEMA)
    op.drop_table(TABLE_NAME, schema=SCHEMA)
