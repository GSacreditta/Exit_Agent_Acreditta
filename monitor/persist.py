"""Persist Monitor results to Postgres."""
from __future__ import annotations
import datetime as dt
from sqlalchemy import select

from shared.db import get_session, Article, Extraction, Person
from .fetch import FetchedArticle


def save_articles_and_extractions(
    results: list[tuple[FetchedArticle, dict | None]],
    verbose: bool = False,
) -> list[tuple[Extraction, Article]]:
    """
    For each (fetched, extraction_dict) tuple:
      - Insert Article (skip if exists by url_hash)
      - Insert Extraction linked to it
    Returns the persisted (Extraction, Article) pairs that are marked relevant.
    """
    persisted: list[tuple[Extraction, Article]] = []

    with get_session() as s:
        for fetched, ext in results:
            # Insert or fetch existing Article
            existing = s.execute(
                select(Article).where(Article.url_hash == fetched.url_hash)
            ).scalar_one_or_none()
            if existing:
                article = existing
            else:
                article = Article(
                    url=fetched.link,
                    url_hash=fetched.url_hash,
                    title=fetched.title,
                    snippet=fetched.snippet,
                    source=fetched.source,
                    article_date=fetched.article_date,
                    query=fetched.query,
                    tier=fetched.tier,
                    matched_company=fetched.matched_company,
                )
                s.add(article)
                s.flush()  # need article.id

            if ext is None:
                continue  # classification failed; article still marked seen

            urgent = _is_urgent(ext, article.tier)
            extraction = Extraction(
                article_id=article.id,
                relevant=bool(ext.get("relevant")),
                deal_type=ext.get("deal_type", "none"),
                companies=ext.get("companies", []),
                people=ext.get("people", []),
                amount=ext.get("amount"),
                category=ext.get("category", "other"),
                why_it_matters=ext.get("why_it_matters", ""),
                is_urgent=urgent,
            )
            s.add(extraction)
            s.flush()

            if extraction.relevant:
                persisted.append((extraction, article))

    if verbose:
        print(f"[persist] saved {len(results)} articles, {len(persisted)} relevant extractions")
    return persisted


def _is_urgent(ext: dict, tier: int) -> bool:
    if tier == 1:
        if ext.get("deal_type") in ("acquisition", "merger", "divestiture", "ipo"):
            return True
        if ext.get("category") in ("credentials", "LATAM_edtech"):
            return True
    if ext.get("deal_type") == "acquisition" and ext.get("category") == "credentials":
        return True
    return False


def update_people_index(extractions: list[tuple[Extraction, Article]]) -> None:
    """Upsert named decision-makers into the `people` table."""
    if not extractions:
        return
    today = dt.date.today()
    with get_session() as s:
        for ext, _ in extractions:
            for p in (ext.people or []):
                name = (p.get("name") or "").strip()
                if not name:
                    continue
                name_lower = name.lower()
                position = f"{p.get('position', '?')} @ {p.get('company', '?')}"

                existing = s.execute(
                    select(Person).where(Person.name_lower == name_lower)
                ).scalar_one_or_none()

                if existing:
                    positions = list(existing.positions or [])
                    if position not in positions:
                        positions.append(position)
                    existing.positions = positions
                    existing.last_seen = today
                    existing.appearances = (existing.appearances or 0) + 1
                else:
                    s.add(Person(
                        name=name,
                        name_lower=name_lower,
                        positions=[position],
                        first_seen=today,
                        last_seen=today,
                        appearances=1,
                    ))
