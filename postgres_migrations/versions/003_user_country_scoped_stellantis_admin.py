"""User: add country_id, remove zone_id. STELLANTIS_ADMIN becomes country-scoped.

Revision ID: 003
Revises: 002
Create Date: 2025-02-27

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("user", sa.Column("country_id", sa.String(36), nullable=True))
    op.create_foreign_key("fk_user_country_id", "user", "country", ["country_id"], ["id"])
    op.create_index("ix_user_country_id", "user", ["country_id"], unique=False)
    op.drop_index("ix_user_zone_id", table_name="user")
    op.drop_constraint("user_zone_id_fkey", "user", type_="foreignkey")
    op.drop_column("user", "zone_id")


def downgrade() -> None:
    op.add_column("user", sa.Column("zone_id", sa.String(36), nullable=True))
    op.create_foreign_key("user_zone_id_fkey", "user", "zone", ["zone_id"], ["id"])
    op.create_index("ix_user_zone_id", "user", ["zone_id"], unique=False)
    op.drop_index("ix_user_country_id", table_name="user")
    op.drop_constraint("fk_user_country_id", "user", type_="foreignkey")
    op.drop_column("user", "country_id")
