"""
create dcim_rbac_role_sub_menu_access table

Revision ID: 021_create_dcim_rbac_role_sub_menu_access
Revises: 020_create_dcim_sub_menu
Create Date: 2025-11-20 00:00:21.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from oracle_helpers import table_exists, index_exists

revision = "021_create_dcim_rbac_role_sub_menu_access"
down_revision = "020_create_dcim_sub_menu"
branch_labels = None
depends_on = None

TABLE_NAME = "dcim_rbac_role_sub_menu_access"
SCHEMA = "dcim"
# Note: This table uses composite primary key (role_id, sub_menu_id), no auto-increment


def _create_table() -> None:
    if not table_exists(SCHEMA, TABLE_NAME):
        op.create_table(
            TABLE_NAME,
            sa.Column("role_id", sa.Integer(), sa.ForeignKey("dcim.dcim_rbac_role.id"), nullable=False, primary_key=True),
            sa.Column("sub_menu_id", sa.Integer(), sa.ForeignKey("dcim.dcim_sub_menu.id"), nullable=False, primary_key=True),
            sa.Column("can_view", sa.Boolean(), nullable=False, server_default=sa.text("1")),
            sa.Column("description", sa.String(255), nullable=True),
            schema=SCHEMA,
        )

    if not index_exists(SCHEMA, "ix_dcim_rbac_access_role_id"):
        op.create_index("ix_dcim_rbac_access_role_id", TABLE_NAME, ["role_id"], schema=SCHEMA)
    if not index_exists(SCHEMA, "ix_dcim_rbac_access_sub_menu_id"):
        op.create_index("ix_dcim_rbac_access_sub_menu_id", TABLE_NAME, ["sub_menu_id"], schema=SCHEMA)


def _update_table() -> None:
    pass


def upgrade() -> None:
    _create_table()
    _update_table()


def downgrade() -> None:
    op.drop_index("ix_dcim_rbac_access_sub_menu_id", table_name=TABLE_NAME, schema=SCHEMA)
    op.drop_index("ix_dcim_rbac_access_role_id", table_name=TABLE_NAME, schema=SCHEMA)
    op.drop_table(TABLE_NAME, schema=SCHEMA)

