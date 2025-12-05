"""
create dcim_user_location_access table

Revision ID: 022_create_dcim_user_location_access
Revises: 021_create_dcim_rbac_role_sub_menu_access
Create Date: 2025-12-04 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

from oracle_helpers import table_exists, index_exists


revision = "022_create_dcim_user_location_access"
down_revision = "021_create_dcim_rbac_role_sub_menu_access"
branch_labels = None
depends_on = None

TABLE_NAME = "dcim_user_location_access"
SCHEMA = "dcim"


def _create_table() -> None:
    if not table_exists(SCHEMA, TABLE_NAME):
        op.create_table(
            TABLE_NAME,
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("dcim.dcim_user.id"), nullable=False),
            sa.Column("location_id", sa.Integer(), sa.ForeignKey("dcim.dcim_location.id"), nullable=False),
            schema=SCHEMA,
        )
        op.create_unique_constraint(
            "uq_dcim_user_loc_access_user_location",
            TABLE_NAME,
            ["user_id", "location_id"],
            schema=SCHEMA,
        )

    if not index_exists(SCHEMA, "ix_dcim_user_loc_access_user_id"):
        op.create_index(
            "ix_dcim_user_loc_access_user_id",
            TABLE_NAME,
            ["user_id"],
            schema=SCHEMA,
        )

    if not index_exists(SCHEMA, "ix_dcim_user_loc_access_location_id"):
        op.create_index(
            "ix_dcim_user_loc_access_location_id",
            TABLE_NAME,
            ["location_id"],
            schema=SCHEMA,
        )



def upgrade() -> None:
    _create_table()


def downgrade() -> None:
    op.drop_constraint(
        "uq_dcim_user_loc_access_user_location",
        TABLE_NAME,
        schema=SCHEMA,
        type_="unique",
    )
    op.drop_index("ix_dcim_user_loc_access_location_id", table_name=TABLE_NAME, schema=SCHEMA)
    op.drop_index("ix_dcim_user_loc_access_user_id", table_name=TABLE_NAME, schema=SCHEMA)
    op.drop_table(TABLE_NAME, schema=SCHEMA)

