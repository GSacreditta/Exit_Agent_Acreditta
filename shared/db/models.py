"""SQLAlchemy 2.0 models for the shared exit-agents database.

Eight tables — narrow on purpose. Squishy data lives in JSONB columns so we
don't over-normalize before the agents teach us what shape it needs.
"""
from __future__ import annotations
import uuid
import datetime as dt
from typing import Optional, Any
from sqlalchemy import (
    String, Integer, Boolean, DateTime, ForeignKey, Text, Date, Index, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


def _now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


# ────────────────────────────────────────────────────────────────────────────
# Articles: raw news items fetched by Monitor
# ────────────────────────────────────────────────────────────────────────────
class Article(Base):
    __tablename__ = "articles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    url: Mapped[str] = mapped_column(Text, unique=True)
    url_hash: Mapped[str] = mapped_column(String(40), index=True)
    title: Mapped[str] = mapped_column(Text, default="")
    snippet: Mapped[str] = mapped_column(Text, default="")
    source: Mapped[str] = mapped_column(Text, default="")
    article_date: Mapped[str] = mapped_column(Text, default="")  # SerpAPI returns a human string
    query: Mapped[str] = mapped_column(Text)
    tier: Mapped[int] = mapped_column(Integer)
    matched_company: Mapped[str] = mapped_column(Text, default="")
    fetched_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_now)

    extractions: Mapped[list["Extraction"]] = relationship(
        back_populates="article", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Article {self.title[:40]!r} tier={self.tier}>"


# ────────────────────────────────────────────────────────────────────────────
# Extractions: LLM-classified deals (one per Article that produced a result)
# ────────────────────────────────────────────────────────────────────────────
class Extraction(Base):
    __tablename__ = "extractions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    article_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("articles.id", ondelete="CASCADE"), index=True)
    relevant: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    deal_type: Mapped[str] = mapped_column(String(32), default="none")
    companies: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list)
    people: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list)
    amount: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(String(32), default="other")
    why_it_matters: Mapped[str] = mapped_column(Text, default="")
    is_urgent: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    extracted_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_now)

    article: Mapped["Article"] = relationship(back_populates="extractions")


# ────────────────────────────────────────────────────────────────────────────
# People: named decision-makers across all signals
# ────────────────────────────────────────────────────────────────────────────
class Person(Base):
    __tablename__ = "people"
    __table_args__ = (UniqueConstraint("name_lower", name="uq_people_name_lower"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(Text)
    name_lower: Mapped[str] = mapped_column(Text, index=True)  # for dedupe on case
    positions: Mapped[list[str]] = mapped_column(JSONB, default=list)
    first_seen: Mapped[dt.date] = mapped_column(Date, default=lambda: _now().date())
    last_seen: Mapped[dt.date] = mapped_column(Date, default=lambda: _now().date())
    appearances: Mapped[int] = mapped_column(Integer, default=1)
    notes: Mapped[str] = mapped_column(Text, default="")


# ────────────────────────────────────────────────────────────────────────────
# Companies: buyer universe (synced from config/watchlist.yaml on deploy)
# ────────────────────────────────────────────────────────────────────────────
class Company(Base):
    __tablename__ = "companies"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(Text, unique=True)
    tier: Mapped[int] = mapped_column(Integer, index=True)
    aliases: Mapped[list[str]] = mapped_column(JSONB, default=list)
    notes: Mapped[str] = mapped_column(Text, default="")
    synced_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_now)


# ────────────────────────────────────────────────────────────────────────────
# Engagement targets: contacts under active outreach
# ────────────────────────────────────────────────────────────────────────────
class EngagementTarget(Base):
    __tablename__ = "engagement_targets"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    person_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("people.id", ondelete="SET NULL"), nullable=True, index=True
    )
    company_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("companies.id", ondelete="SET NULL"), nullable=True, index=True
    )
    status: Mapped[str] = mapped_column(String(32), default="tracking", index=True)
    # tracking | contacted | responded | engaged | dormant | closed
    owner: Mapped[str] = mapped_column(Text, default="")  # which co-founder
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)

    actions: Mapped[list["EngagementAction"]] = relationship(
        back_populates="target", cascade="all, delete-orphan", order_by="EngagementAction.occurred_at"
    )


class EngagementAction(Base):
    __tablename__ = "engagement_actions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    target_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("engagement_targets.id", ondelete="CASCADE"), index=True)
    action_type: Mapped[str] = mapped_column(String(32))
    # outreach_sent | response_received | meeting_scheduled | meeting_held | follow_up | closed | note
    occurred_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_now)
    details: Mapped[str] = mapped_column(Text, default="")
    by_user: Mapped[str] = mapped_column(Text, default="")

    target: Mapped["EngagementTarget"] = relationship(back_populates="actions")


# ────────────────────────────────────────────────────────────────────────────
# Coaching threads: Advisor conversation memory
# ────────────────────────────────────────────────────────────────────────────
class CoachingThread(Base):
    __tablename__ = "coaching_threads"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    slack_thread_ts: Mapped[str] = mapped_column(Text, index=True)
    slack_channel_id: Mapped[str] = mapped_column(Text, index=True)
    slack_user_id: Mapped[str] = mapped_column(Text, index=True)
    summary: Mapped[str] = mapped_column(Text, default="")
    messages: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)


# ────────────────────────────────────────────────────────────────────────────
# Bot posts: audit log of every bot message
# ────────────────────────────────────────────────────────────────────────────
class BotPost(Base):
    __tablename__ = "bot_posts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    agent: Mapped[str] = mapped_column(String(32), index=True)  # monitor | engagement | advisor
    slack_channel_id: Mapped[str] = mapped_column(Text)
    slack_message_ts: Mapped[str] = mapped_column(Text)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    related_extraction_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("extractions.id", ondelete="SET NULL"), nullable=True
    )
    related_target_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("engagement_targets.id", ondelete="SET NULL"), nullable=True
    )
    posted_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_now)
