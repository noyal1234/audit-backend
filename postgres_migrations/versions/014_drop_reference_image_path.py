"""Drop reference_image_path from checkpoint and audit_checkpoint.

Revision ID: 014
Revises: 013
Create Date: 2026-03-02

Upgrade: DROP COLUMN reference_image_path from checkpoint and audit_checkpoint (if exists).
Downgrade: Add column back as TEXT NULL.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "014"
down_revision: Union[str, None] = "013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE checkpoint DROP COLUMN IF EXISTS reference_image_path")
    op.execute("ALTER TABLE audit_checkpoint DROP COLUMN IF EXISTS reference_image_path")


def downgrade() -> None:
    op.add_column("checkpoint", sa.Column("reference_image_path", sa.Text(), nullable=True))
    op.add_column("audit_checkpoint", sa.Column("reference_image_path", sa.Text(), nullable=True))
