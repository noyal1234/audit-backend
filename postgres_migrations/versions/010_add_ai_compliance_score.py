"""Add ai_compliance_score to media_evidence.

Revision ID: 010
Revises: 009
Create Date: 2026-03-02

Stores AI compliance score (0.0-100.0) per media row.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "010"
down_revision: Union[str, None] = "009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "media_evidence",
        sa.Column("ai_compliance_score", sa.Float(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("media_evidence", "ai_compliance_score")
