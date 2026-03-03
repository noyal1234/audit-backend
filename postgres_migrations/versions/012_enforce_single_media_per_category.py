"""Enforce single media_evidence row per audit_checkpoint_category (hard replace).

Revision ID: 012
Revises: 011
Create Date: 2026-03-02

Cleans duplicate media rows (keeps newest by created_at per category), repairs snapshot
pointers, then adds UNIQUE(audit_checkpoint_category_id).
"""

from typing import Sequence, Union

from alembic import op

revision: str = "012"
down_revision: Union[str, None] = "011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Delete older duplicates, keep newest per category
    op.execute("""
        DELETE FROM media_evidence m
        USING media_evidence m2
        WHERE m.audit_checkpoint_category_id = m2.audit_checkpoint_category_id
          AND m.id <> m2.id
          AND m.created_at < m2.created_at;
    """)

    # 2. Repair snapshot pointers so ai_latest_media_id points to the remaining row
    op.execute("""
        UPDATE audit_checkpoint_category c
        SET ai_latest_media_id = m.id
        FROM media_evidence m
        WHERE c.id = m.audit_checkpoint_category_id;
    """)

    # 3. Add unique constraint
    op.create_unique_constraint(
        "uq_media_per_category",
        "media_evidence",
        ["audit_checkpoint_category_id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_media_per_category",
        "media_evidence",
        type_="unique",
    )
