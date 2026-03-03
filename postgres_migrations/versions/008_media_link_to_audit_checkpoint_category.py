"""Re-link media_evidence to audit_checkpoint_category instead of checkpoint.

Revision ID: 008
Revises: cb5272ceaca5
Create Date: 2026-03-02
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "008"
down_revision: Union[str, None] = "cb5272ceaca5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add new FK column (nullable first so existing rows don't violate constraint)
    op.add_column(
        "media_evidence",
        sa.Column("audit_checkpoint_category_id", sa.String(36), nullable=True),
    )
    op.create_foreign_key(
        "fk_media_evidence_acc",
        "media_evidence",
        "audit_checkpoint_category",
        ["audit_checkpoint_category_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index(
        "ix_media_evidence_acc_id",
        "media_evidence",
        ["audit_checkpoint_category_id"],
    )

    # 2. Remove rows that cannot be backfilled (no safe matching strategy exists)
    #    In production, run a backfill script before this step.
    op.execute("DELETE FROM media_evidence WHERE audit_checkpoint_category_id IS NULL")

    # 3. Enforce NOT NULL now that orphan rows are removed
    op.alter_column("media_evidence", "audit_checkpoint_category_id", nullable=False)

    # 4. Drop old checkpoint_id FK and column
    op.drop_constraint("media_evidence_checkpoint_id_fkey", "media_evidence", type_="foreignkey")
    op.drop_index("ix_media_evidence_checkpoint_id", table_name="media_evidence")
    op.drop_column("media_evidence", "checkpoint_id")


def downgrade() -> None:
    op.add_column(
        "media_evidence",
        sa.Column("checkpoint_id", sa.String(36), nullable=True),
    )
    op.create_foreign_key(
        "media_evidence_checkpoint_id_fkey",
        "media_evidence",
        "checkpoint",
        ["checkpoint_id"],
        ["id"],
    )
    op.create_index("ix_media_evidence_checkpoint_id", "media_evidence", ["checkpoint_id"])

    op.drop_constraint("fk_media_evidence_acc", "media_evidence", type_="foreignkey")
    op.drop_index("ix_media_evidence_acc_id", table_name="media_evidence")
    op.drop_column("media_evidence", "audit_checkpoint_category_id")
