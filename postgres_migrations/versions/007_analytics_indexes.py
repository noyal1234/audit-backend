"""Add index on audit_checkpoint_category.is_completed for analytics queries.

Revision ID: 007
Revises: 006
Create Date: 2026-02-28
"""

from alembic import op

revision = "007"
down_revision = "006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index("ix_audit_cp_cat_is_completed", "audit_checkpoint_category", ["is_completed"])


def downgrade() -> None:
    op.drop_index("ix_audit_cp_cat_is_completed", table_name="audit_checkpoint_category")
