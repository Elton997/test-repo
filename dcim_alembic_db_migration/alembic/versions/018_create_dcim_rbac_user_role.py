"""
create dcim_rbac_user_role table

Revision ID: 018_create_dcim_rbac_user_role
Revises: 017_create_dcim_rbac_role
Create Date: 2025-11-20 00:00:18.000000
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

revision = "018_create_dcim_rbac_user_role"
down_revision = "017_create_dcim_rbac_role"
branch_labels = None
depends_on = None

TABLE_NAME = "dcim_rbac_user_role"
SCHEMA = "dcim"
SEQ_NAME = f"{TABLE_NAME}_seq"
TRG_NAME = f"{TABLE_NAME}_trg"


def _create_table() -> None:
    if not table_exists(SCHEMA, TABLE_NAME):
        op.create_table(
            TABLE_NAME,
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("dcim.dcim_user.id"), nullable=False),
            sa.Column("role_id", sa.Integer(), sa.ForeignKey("dcim.dcim_rbac_role.id"), nullable=False),
            sa.Column("description", sa.String(255), nullable=True),
            schema=SCHEMA,
        )

    if not index_exists(SCHEMA, "ix_dcim_rbac_user_role_user_id"):
        op.create_index("ix_dcim_rbac_user_role_user_id", TABLE_NAME, ["user_id"], schema=SCHEMA)
    if not index_exists(SCHEMA, "ix_dcim_rbac_user_role_role_id"):
        op.create_index("ix_dcim_rbac_user_role_role_id", TABLE_NAME, ["role_id"], schema=SCHEMA)


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
    op.drop_index("ix_dcim_rbac_user_role_role_id", table_name=TABLE_NAME, schema=SCHEMA)
    op.drop_index("ix_dcim_rbac_user_role_user_id", table_name=TABLE_NAME, schema=SCHEMA)
    op.drop_table(TABLE_NAME, schema=SCHEMA)
