"""Refactor: drop old category system, create area/sub_area/checkpoint + audit tree + reviews.

Revision ID: 013
Revises: 012
Create Date: 2026-03-02

PRE-PRODUCTION ONLY. Drops category, checkpoint_category, audit_checkpoint_category,
old audit_checkpoint; creates area, sub_area, checkpoint; creates audit_area, audit_sub_area,
audit_checkpoint (new), audit_checkpoint_review. media_evidence gains audit_checkpoint_id.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "013"
down_revision: Union[str, None] = "012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- Drop old system (order respects FKs) ---
    op.drop_constraint("uq_media_per_category", "media_evidence", type_="unique")
    op.drop_constraint("fk_media_evidence_acc", "media_evidence", type_="foreignkey")
    op.drop_index("ix_media_evidence_acc_id", table_name="media_evidence")
    op.drop_column("media_evidence", "audit_checkpoint_category_id")

    op.drop_table("audit_checkpoint_category")
    op.drop_table("audit_checkpoint")
    op.drop_table("checkpoint_category")
    op.drop_table("checkpoint")
    op.drop_table("category")

    # --- New hierarchy: facility -> area -> sub_area -> checkpoint ---
    op.create_table(
        "area",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("facility_id", sa.String(36), sa.ForeignKey("facility.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_unique_constraint("uq_area_facility_name", "area", ["facility_id", "name"])

    op.create_table(
        "sub_area",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("area_id", sa.String(36), sa.ForeignKey("area.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_unique_constraint("uq_sub_area_area_name", "sub_area", ["area_id", "name"])

    op.create_table(
        "checkpoint",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("sub_area_id", sa.String(36), sa.ForeignKey("sub_area.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("reference_image_path", sa.String(512), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_unique_constraint("uq_checkpoint_sub_area_name", "checkpoint", ["sub_area_id", "name"])

    # --- Audit snapshot tree: audit -> audit_area -> audit_sub_area -> audit_checkpoint ---
    op.create_table(
        "audit_area",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("audit_id", sa.String(36), sa.ForeignKey("audit.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("area_name", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "audit_sub_area",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("audit_area_id", sa.String(36), sa.ForeignKey("audit_area.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("sub_area_name", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "audit_checkpoint",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("audit_sub_area_id", sa.String(36), sa.ForeignKey("audit_sub_area.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("checkpoint_name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("reference_image_path", sa.String(512), nullable=False, server_default=""),
        sa.Column("is_completed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # --- Append-only reviews per checkpoint ---
    op.create_table(
        "audit_checkpoint_review",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("audit_checkpoint_id", sa.String(36), sa.ForeignKey("audit_checkpoint.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("review_type", sa.String(30), nullable=False),
        sa.Column("compliant", sa.Boolean(), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("remarks", sa.Text(), nullable=True),
        sa.Column("model_version", sa.String(255), nullable=True),
        sa.Column("created_by", sa.String(36), sa.ForeignKey("user.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # --- Link media_evidence to new audit_checkpoint ---
    op.add_column("media_evidence", sa.Column("audit_checkpoint_id", sa.String(36), nullable=True))
    op.create_foreign_key(
        "fk_media_evidence_audit_checkpoint",
        "media_evidence",
        "audit_checkpoint",
        ["audit_checkpoint_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_media_evidence_audit_checkpoint_id", "media_evidence", ["audit_checkpoint_id"])


def downgrade() -> None:
    op.drop_constraint("fk_media_evidence_audit_checkpoint", "media_evidence", type_="foreignkey")
    op.drop_index("ix_media_evidence_audit_checkpoint_id", table_name="media_evidence")
    op.drop_column("media_evidence", "audit_checkpoint_id")

    op.drop_table("audit_checkpoint_review")
    op.drop_table("audit_checkpoint")
    op.drop_table("audit_sub_area")
    op.drop_table("audit_area")
    op.drop_table("checkpoint")
    op.drop_table("sub_area")
    op.drop_table("area")

    # Recreate old tables (minimal structure for downgrade; no data)
    op.create_table(
        "category",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("facility_id", sa.String(36), sa.ForeignKey("facility.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "checkpoint",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("facility_id", sa.String(36), sa.ForeignKey("facility.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("image_url", sa.String(512), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "checkpoint_category",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("checkpoint_id", sa.String(36), sa.ForeignKey("checkpoint.id", ondelete="CASCADE"), nullable=False),
        sa.Column("category_id", sa.String(36), sa.ForeignKey("category.id", ondelete="CASCADE"), nullable=False),
    )
    op.create_table(
        "audit_checkpoint",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("audit_id", sa.String(36), sa.ForeignKey("audit.id", ondelete="CASCADE"), nullable=False),
        sa.Column("checkpoint_id", sa.String(36), sa.ForeignKey("checkpoint.id"), nullable=False),
        sa.Column("checkpoint_name", sa.String(255), nullable=False),
        sa.Column("image_url", sa.String(512), nullable=False, server_default=""),
        sa.Column("status_type", sa.String(50), nullable=False, server_default="PENDING"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "audit_checkpoint_category",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("audit_checkpoint_id", sa.String(36), sa.ForeignKey("audit_checkpoint.id", ondelete="CASCADE"), nullable=False),
        sa.Column("category_id", sa.String(36), sa.ForeignKey("category.id"), nullable=False),
        sa.Column("category_name", sa.String(255), nullable=False),
        sa.Column("is_completed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("completed_by", sa.String(36), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("remarks", sa.Text(), nullable=True),
    )
    op.add_column("media_evidence", sa.Column("audit_checkpoint_category_id", sa.String(36), nullable=True))
    op.create_foreign_key("fk_media_evidence_acc", "media_evidence", "audit_checkpoint_category", ["audit_checkpoint_category_id"], ["id"], ondelete="CASCADE")
    op.create_index("ix_media_evidence_acc_id", "media_evidence", ["audit_checkpoint_category_id"])
