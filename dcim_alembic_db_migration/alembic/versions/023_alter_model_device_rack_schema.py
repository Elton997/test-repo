"""
Alter schema: add image paths to model, remove from device, remove width from rack

Revision ID: 023_alter_model_device_rack_schema
Revises: 022_create_dcim_user_location_access
Create Date: 2025-12-11 00:00:00.000000

Changes:
- Add front_image_path and rear_image_path columns to dcim_model table
- Remove front_image_path and rear_image_path columns from dcim_device table
- Remove width column from dcim_rack table
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from oracle_helpers import (
    add_column_if_not_exists,
    drop_column_if_exists,
)

revision = "023_alter_model_device_rack_schema"
down_revision = "022_create_dcim_user_location_access"
branch_labels = None
depends_on = None

SCHEMA = "dcim"


def upgrade() -> None:
    # Add front_image_path and rear_image_path to dcim_model (if not exists)
    add_column_if_not_exists(
        SCHEMA,
        "dcim_model",
        sa.Column("front_image_path", sa.String(512), nullable=True),
    )
    add_column_if_not_exists(
        SCHEMA,
        "dcim_model",
        sa.Column("rear_image_path", sa.String(512), nullable=True),
    )

    # Remove front_image_path and rear_image_path from dcim_device (if exists)
    drop_column_if_exists(SCHEMA, "dcim_device", "front_image_path")
    drop_column_if_exists(SCHEMA, "dcim_device", "rear_image_path")

    # Remove width from dcim_rack (if exists)
    drop_column_if_exists(SCHEMA, "dcim_rack", "width")


def downgrade() -> None:
    # Re-add width to dcim_rack
    add_column_if_not_exists(
        SCHEMA,
        "dcim_rack",
        sa.Column("width", sa.Integer(), nullable=True),
    )

    # Re-add front_image_path and rear_image_path to dcim_device
    add_column_if_not_exists(
        SCHEMA,
        "dcim_device",
        sa.Column("front_image_path", sa.String(512), nullable=True),
    )
    add_column_if_not_exists(
        SCHEMA,
        "dcim_device",
        sa.Column("rear_image_path", sa.String(512), nullable=True),
    )

    # Remove front_image_path and rear_image_path from dcim_model
    drop_column_if_exists(SCHEMA, "dcim_model", "front_image_path")
    drop_column_if_exists(SCHEMA, "dcim_model", "rear_image_path")

