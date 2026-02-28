"""Add dealer contact columns to facility (dealership).

Revision ID: 002
Revises: 001
Create Date: 2025-02-27

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("facility", sa.Column("dealer_name", sa.String(255), nullable=True))
    op.add_column("facility", sa.Column("dealer_phone", sa.String(50), nullable=True))
    op.add_column("facility", sa.Column("dealer_email", sa.String(255), nullable=True))
    op.add_column("facility", sa.Column("dealer_designation", sa.String(100), nullable=True))
    op.create_index(op.f("ix_facility_dealer_email"), "facility", ["dealer_email"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_facility_dealer_email"), table_name="facility")
    op.drop_column("facility", "dealer_designation")
    op.drop_column("facility", "dealer_email")
    op.drop_column("facility", "dealer_phone")
    op.drop_column("facility", "dealer_name")
