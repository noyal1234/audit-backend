"""Facility-scoped categories and checkpoints with many-to-many join table.

Removes the subcategory table and subcategory_id from checkpoint.
Adds facility_id to category. Creates checkpoint_category join table.
Restructures checkpoint: drops subcategory_id/description/requires_photo/active,
adds image_url.

Revision ID: 005
Revises: 004
Create Date: 2026-02-28
"""

from alembic import op
import sqlalchemy as sa

revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint(
        "checkpoint_subcategory_id_fkey", "checkpoint", type_="foreignkey"
    )

    op.drop_column("checkpoint", "subcategory_id")
    op.drop_column("checkpoint", "description")
    op.drop_column("checkpoint", "requires_photo")
    op.drop_column("checkpoint", "active")
    op.add_column(
        "checkpoint",
        sa.Column("image_url", sa.String(512), nullable=False, server_default=""),
    )
    op.create_unique_constraint("uq_checkpoint_facility_name", "checkpoint", ["facility_id", "name"])

    op.add_column(
        "category",
        sa.Column("facility_id", sa.String(36), sa.ForeignKey("facility.id", ondelete="CASCADE"), nullable=True),
    )
    op.execute("UPDATE category SET facility_id = '' WHERE facility_id IS NULL")
    op.alter_column("category", "facility_id", nullable=False)
    op.drop_column("category", "updated_at")
    op.create_unique_constraint("uq_category_facility_name", "category", ["facility_id", "name"])

    op.create_table(
        "checkpoint_category",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "checkpoint_id",
            sa.String(36),
            sa.ForeignKey("checkpoint.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "category_id",
            sa.String(36),
            sa.ForeignKey("category.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.UniqueConstraint("checkpoint_id", "category_id", name="uq_checkpoint_category"),
    )
    op.create_index("ix_checkpoint_category_checkpoint_id", "checkpoint_category", ["checkpoint_id"])
    op.create_index("ix_checkpoint_category_category_id", "checkpoint_category", ["category_id"])

    op.drop_table("subcategory")


def downgrade() -> None:
    op.create_table(
        "subcategory",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("category_id", sa.String(36), sa.ForeignKey("category.id"), nullable=False, index=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.drop_table("checkpoint_category")

    op.drop_constraint("uq_category_facility_name", "category", type_="unique")
    op.add_column("category", sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()))
    op.drop_column("category", "facility_id")

    op.drop_constraint("uq_checkpoint_facility_name", "checkpoint", type_="unique")
    op.drop_column("checkpoint", "image_url")
    op.add_column("checkpoint", sa.Column("active", sa.Boolean, nullable=False, server_default=sa.text("true")))
    op.add_column("checkpoint", sa.Column("requires_photo", sa.Boolean, nullable=False, server_default=sa.text("false")))
    op.add_column("checkpoint", sa.Column("description", sa.Text, nullable=True))
    op.add_column(
        "checkpoint",
        sa.Column("subcategory_id", sa.String(36), sa.ForeignKey("subcategory.id"), nullable=True, index=True),
    )
