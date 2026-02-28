"""Initial schema: country, zone, facility, user, staff, auth_session, category, subcategory, checkpoint, shift_config, audit, audit_checkpoint_result, media_evidence.

Revision ID: 001
Revises:
Create Date: 2025-02-27

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "country",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("code", sa.String(10), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index(op.f("ix_country_code"), "country", ["code"], unique=True)

    op.create_table(
        "zone",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("country_id", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["country_id"], ["country.id"]),
    )
    op.create_index("ix_zone_id", "zone", ["id"])
    op.create_index("ix_zone_country_id", "zone", ["country_id"])

    op.create_table(
        "facility",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("zone_id", sa.String(36), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("code", sa.String(50), nullable=True),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["zone_id"], ["zone.id"]),
    )
    op.create_index("ix_facility_id", "facility", ["id"])
    op.create_index("ix_facility_zone_id", "facility", ["zone_id"])

    op.create_table(
        "user",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("role_type", sa.String(50), nullable=False),
        sa.Column("facility_id", sa.String(36), nullable=True),
        sa.Column("zone_id", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["facility_id"], ["facility.id"]),
        sa.ForeignKeyConstraint(["zone_id"], ["zone.id"]),
    )
    op.create_index("ix_user_email", "user", ["email"], unique=True)
    op.create_index("ix_user_facility_id", "user", ["facility_id"])
    op.create_index("ix_user_zone_id", "user", ["zone_id"])

    op.create_table(
        "staff",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("facility_id", sa.String(36), nullable=False),
        sa.Column("user_id", sa.String(36), nullable=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["facility_id"], ["facility.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"]),
    )
    op.create_index("ix_staff_facility_id", "staff", ["facility_id"])
    op.create_index("ix_staff_user_id", "staff", ["user_id"])

    op.create_table(
        "auth_session",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("token_jti", sa.String(255), nullable=True),
        sa.Column("refresh_token", sa.Text(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"]),
    )
    op.create_index("ix_auth_session_user_id", "auth_session", ["user_id"])
    op.create_index("ix_auth_session_token_jti", "auth_session", ["token_jti"])

    op.create_table(
        "category",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "subcategory",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("category_id", sa.String(36), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["category_id"], ["category.id"]),
    )
    op.create_index("ix_subcategory_category_id", "subcategory", ["category_id"])

    op.create_table(
        "checkpoint",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("subcategory_id", sa.String(36), nullable=False),
        sa.Column("facility_id", sa.String(36), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("requires_photo", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["subcategory_id"], ["subcategory.id"]),
        sa.ForeignKeyConstraint(["facility_id"], ["facility.id"]),
    )
    op.create_index("ix_checkpoint_id", "checkpoint", ["id"])
    op.create_index("ix_checkpoint_subcategory_id", "checkpoint", ["subcategory_id"])
    op.create_index("ix_checkpoint_facility_id", "checkpoint", ["facility_id"])

    op.create_table(
        "shift_config",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(50), nullable=False),
        sa.Column("start_time", sa.Time(), nullable=False),
        sa.Column("end_time", sa.Time(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "audit",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("facility_id", sa.String(36), nullable=False),
        sa.Column("shift_type", sa.String(50), nullable=False),
        sa.Column("shift_date", sa.Date(), nullable=False),
        sa.Column("status_type", sa.String(50), nullable=False),
        sa.Column("created_by", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("finalized_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["facility_id"], ["facility.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["user.id"]),
    )
    op.create_index("ix_audit_id", "audit", ["id"])
    op.create_index("ix_audit_facility_id", "audit", ["facility_id"])
    op.create_index("ix_audit_shift_type", "audit", ["shift_type"])
    op.create_index("ix_audit_shift_date", "audit", ["shift_date"])
    op.create_index("ix_audit_created_at", "audit", ["created_at"])

    op.create_table(
        "audit_checkpoint_result",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("audit_id", sa.String(36), nullable=False),
        sa.Column("checkpoint_id", sa.String(36), nullable=False),
        sa.Column("compliant", sa.Boolean(), nullable=False),
        sa.Column("manual_override", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("image_path", sa.String(512), nullable=True),
        sa.Column("ai_status_type", sa.String(50), nullable=True),
        sa.Column("ai_result", sa.String(50), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["audit_id"], ["audit.id"]),
        sa.ForeignKeyConstraint(["checkpoint_id"], ["checkpoint.id"]),
    )
    op.create_index("ix_audit_checkpoint_result_audit_id", "audit_checkpoint_result", ["audit_id"])
    op.create_index("ix_audit_checkpoint_result_checkpoint_id", "audit_checkpoint_result", ["checkpoint_id"])

    op.create_table(
        "media_evidence",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("audit_id", sa.String(36), nullable=False),
        sa.Column("checkpoint_id", sa.String(36), nullable=False),
        sa.Column("file_path", sa.String(512), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["audit_id"], ["audit.id"]),
        sa.ForeignKeyConstraint(["checkpoint_id"], ["checkpoint.id"]),
    )
    op.create_index("ix_media_evidence_audit_id", "media_evidence", ["audit_id"])
    op.create_index("ix_media_evidence_checkpoint_id", "media_evidence", ["checkpoint_id"])


def downgrade() -> None:
    op.drop_table("media_evidence")
    op.drop_table("audit_checkpoint_result")
    op.drop_table("audit")
    op.drop_table("shift_config")
    op.drop_table("checkpoint")
    op.drop_table("subcategory")
    op.drop_table("category")
    op.drop_table("auth_session")
    op.drop_table("staff")
    op.drop_table("user")
    op.drop_table("facility")
    op.drop_table("zone")
    op.drop_table("country")
