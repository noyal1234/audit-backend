"""Add ai_compliance_score to audit_checkpoint_category snapshot.

Revision ID: 011
Revises: 010
Create Date: 2026-03-02

Category-level snapshot of latest AI compliance score (0.0-100.0).
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "011"
down_revision: Union[str, None] = "010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "audit_checkpoint_category",
        sa.Column("ai_compliance_score", sa.Float(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("audit_checkpoint_category", "ai_compliance_score")
