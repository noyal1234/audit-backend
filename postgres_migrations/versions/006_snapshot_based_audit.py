"""Snapshot-based shift audit with audit_checkpoint and audit_checkpoint_category.

Drops old audit_checkpoint_result table.
Adds unique constraint on audit(facility_id, shift_type, shift_date).
Creates audit_checkpoint (snapshot of checkpoint at audit time).
Creates audit_checkpoint_category (tracks category-level completion).

Revision ID: 006
Revises: 005
Create Date: 2026-02-28
"""

from alembic import op
import sqlalchemy as sa

revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_table("audit_checkpoint_result")

    op.create_unique_constraint(
        "uq_audit_facility_shift", "audit", ["facility_id", "shift_type", "shift_date"]
    )
    op.create_index("ix_audit_facility_shift_date", "audit", ["facility_id", "shift_type", "shift_date"])

    op.create_table(
        "audit_checkpoint",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("audit_id", sa.String(36), sa.ForeignKey("audit.id", ondelete="CASCADE"), nullable=False),
        sa.Column("checkpoint_id", sa.String(36), sa.ForeignKey("checkpoint.id"), nullable=False),
        sa.Column("checkpoint_name", sa.String(255), nullable=False),
        sa.Column("image_url", sa.String(512), nullable=False, server_default=""),
        sa.Column("status_type", sa.String(50), nullable=False, server_default="PENDING"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("audit_id", "checkpoint_id", name="uq_audit_checkpoint"),
    )
    op.create_index("ix_audit_checkpoint_audit_id", "audit_checkpoint", ["audit_id"])

    op.create_table(
        "audit_checkpoint_category",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "audit_checkpoint_id",
            sa.String(36),
            sa.ForeignKey("audit_checkpoint.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("category_id", sa.String(36), sa.ForeignKey("category.id"), nullable=False),
        sa.Column("category_name", sa.String(255), nullable=False),
        sa.Column("is_completed", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("completed_by", sa.String(36), sa.ForeignKey("user.id"), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("remarks", sa.Text, nullable=True),
        sa.UniqueConstraint("audit_checkpoint_id", "category_id", name="uq_audit_checkpoint_category"),
    )
    op.create_index("ix_audit_cp_cat_acp_id", "audit_checkpoint_category", ["audit_checkpoint_id"])


def downgrade() -> None:
    op.drop_table("audit_checkpoint_category")
    op.drop_table("audit_checkpoint")

    op.drop_index("ix_audit_facility_shift_date", table_name="audit")
    op.drop_constraint("uq_audit_facility_shift", "audit", type_="unique")

    op.create_table(
        "audit_checkpoint_result",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("audit_id", sa.String(36), sa.ForeignKey("audit.id"), nullable=False, index=True),
        sa.Column("checkpoint_id", sa.String(36), sa.ForeignKey("checkpoint.id"), nullable=False, index=True),
        sa.Column("compliant", sa.Boolean, nullable=False),
        sa.Column("manual_override", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("image_path", sa.String(512), nullable=True),
        sa.Column("ai_status_type", sa.String(50), nullable=True),
        sa.Column("ai_result", sa.String(50), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
