"""Category-level AI snapshot: audit_checkpoint_category holds latest AI state.

Revision ID: 009
Revises: 008
Create Date: 2026-03-02

Adds ai_latest_media_id, ai_status, ai_compliant, ai_summary to audit_checkpoint_category.
Evidence stays in media_evidence; category holds the snapshot for UI/reload.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "009"
down_revision: Union[str, None] = "008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "audit_checkpoint_category",
        sa.Column("ai_latest_media_id", sa.String(36), nullable=True),
    )
    op.add_column(
        "audit_checkpoint_category",
        sa.Column("ai_status", sa.String(20), nullable=True),
    )
    op.add_column(
        "audit_checkpoint_category",
        sa.Column("ai_compliant", sa.Boolean(), nullable=True),
    )
    op.add_column(
        "audit_checkpoint_category",
        sa.Column("ai_summary", sa.Text(), nullable=True),
    )
    op.create_foreign_key(
        "fk_audit_checkpoint_category_ai_latest_media",
        "audit_checkpoint_category",
        "media_evidence",
        ["ai_latest_media_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_audit_checkpoint_category_ai_latest_media",
        "audit_checkpoint_category",
        type_="foreignkey",
    )
    op.drop_column("audit_checkpoint_category", "ai_summary")
    op.drop_column("audit_checkpoint_category", "ai_compliant")
    op.drop_column("audit_checkpoint_category", "ai_status")
    op.drop_column("audit_checkpoint_category", "ai_latest_media_id")
