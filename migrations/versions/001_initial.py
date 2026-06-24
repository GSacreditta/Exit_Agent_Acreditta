"""initial schema — 8 tables

Revision ID: 001_initial
Revises:
Create Date: 2026-06-14

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB


revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "articles",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("url", sa.Text(), nullable=False, unique=True),
        sa.Column("url_hash", sa.String(40), nullable=False, index=True),
        sa.Column("title", sa.Text(), nullable=False, server_default=""),
        sa.Column("snippet", sa.Text(), nullable=False, server_default=""),
        sa.Column("source", sa.Text(), nullable=False, server_default=""),
        sa.Column("article_date", sa.Text(), nullable=False, server_default=""),
        sa.Column("query", sa.Text(), nullable=False),
        sa.Column("tier", sa.Integer(), nullable=False),
        sa.Column("matched_company", sa.Text(), nullable=False, server_default=""),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "extractions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("article_id", UUID(as_uuid=True), sa.ForeignKey("articles.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("relevant", sa.Boolean(), nullable=False, server_default=sa.false(), index=True),
        sa.Column("deal_type", sa.String(32), nullable=False, server_default="none"),
        sa.Column("companies", JSONB, nullable=False, server_default="[]"),
        sa.Column("people", JSONB, nullable=False, server_default="[]"),
        sa.Column("amount", sa.Text(), nullable=True),
        sa.Column("category", sa.String(32), nullable=False, server_default="other"),
        sa.Column("why_it_matters", sa.Text(), nullable=False, server_default=""),
        sa.Column("is_urgent", sa.Boolean(), nullable=False, server_default=sa.false(), index=True),
        sa.Column("extracted_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "people",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("name_lower", sa.Text(), nullable=False, index=True),
        sa.Column("positions", JSONB, nullable=False, server_default="[]"),
        sa.Column("first_seen", sa.Date(), nullable=False, server_default=sa.func.current_date()),
        sa.Column("last_seen", sa.Date(), nullable=False, server_default=sa.func.current_date()),
        sa.Column("appearances", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("notes", sa.Text(), nullable=False, server_default=""),
        sa.UniqueConstraint("name_lower", name="uq_people_name_lower"),
    )

    op.create_table(
        "companies",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False, unique=True),
        sa.Column("tier", sa.Integer(), nullable=False, index=True),
        sa.Column("aliases", JSONB, nullable=False, server_default="[]"),
        sa.Column("notes", sa.Text(), nullable=False, server_default=""),
        sa.Column("synced_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "engagement_targets",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("person_id", UUID(as_uuid=True), sa.ForeignKey("people.id", ondelete="SET NULL"), nullable=True, index=True),
        sa.Column("company_id", UUID(as_uuid=True), sa.ForeignKey("companies.id", ondelete="SET NULL"), nullable=True, index=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="tracking", index=True),
        sa.Column("owner", sa.Text(), nullable=False, server_default=""),
        sa.Column("notes", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "engagement_actions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("target_id", UUID(as_uuid=True), sa.ForeignKey("engagement_targets.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("action_type", sa.String(32), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("details", sa.Text(), nullable=False, server_default=""),
        sa.Column("by_user", sa.Text(), nullable=False, server_default=""),
    )

    op.create_table(
        "coaching_threads",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("slack_thread_ts", sa.Text(), nullable=False, index=True),
        sa.Column("slack_channel_id", sa.Text(), nullable=False, index=True),
        sa.Column("slack_user_id", sa.Text(), nullable=False, index=True),
        sa.Column("summary", sa.Text(), nullable=False, server_default=""),
        sa.Column("messages", JSONB, nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "bot_posts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("agent", sa.String(32), nullable=False, index=True),
        sa.Column("slack_channel_id", sa.Text(), nullable=False),
        sa.Column("slack_message_ts", sa.Text(), nullable=False),
        sa.Column("payload", JSONB, nullable=False, server_default="{}"),
        sa.Column("related_extraction_id", UUID(as_uuid=True), sa.ForeignKey("extractions.id", ondelete="SET NULL"), nullable=True),
        sa.Column("related_target_id", UUID(as_uuid=True), sa.ForeignKey("engagement_targets.id", ondelete="SET NULL"), nullable=True),
        sa.Column("posted_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("bot_posts")
    op.drop_table("coaching_threads")
    op.drop_table("engagement_actions")
    op.drop_table("engagement_targets")
    op.drop_table("companies")
    op.drop_table("people")
    op.drop_table("extractions")
    op.drop_table("articles")
