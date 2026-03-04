"""Add media_id nullable FK to audit_checkpoint_review.

Revision ID: 015
Revises: 014
Create Date: 2026-03-02

Upgrade: ADD COLUMN media_id, ADD CONSTRAINT fk_review_media REFERENCES media_evidence(id) ON DELETE SET NULL.
Downgrade: DROP CONSTRAINT, DROP COLUMN.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "015"
down_revision: Union[str, None] = "014"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "audit_checkpoint_review",
        sa.Column("media_id", sa.String(36), nullable=True),
    )
    op.create_foreign_key(
        "fk_review_media",
        "audit_checkpoint_review",
        "media_evidence",
        ["media_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_review_media", "audit_checkpoint_review", type_="foreignkey")
    op.drop_column("audit_checkpoint_review", "media_id")
