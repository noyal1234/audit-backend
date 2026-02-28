"""Unified auth: user.is_active, facility.user_id, staff drop email.

Revision ID: 004
Revises: 003
Create Date: 2025-02-27

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("user", sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()))
    op.add_column("facility", sa.Column("user_id", sa.String(36), nullable=True))
    op.create_foreign_key("fk_facility_user_id", "facility", "user", ["user_id"], ["id"])
    op.create_index("ix_facility_user_id", "facility", ["user_id"], unique=False)
    op.drop_column("staff", "email")


def downgrade() -> None:
    op.add_column("staff", sa.Column("email", sa.String(255), nullable=True))
    op.drop_index("ix_facility_user_id", table_name="facility")
    op.drop_constraint("fk_facility_user_id", "facility", type_="foreignkey")
    op.drop_column("facility", "user_id")
    op.drop_column("user", "is_active")
