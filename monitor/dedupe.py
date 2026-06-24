"""Dedupe against the `articles` table. Replaces the old seen.json."""
from __future__ import annotations
from sqlalchemy import select

from shared.db import get_session, Article
from .fetch import FetchedArticle


def filter_unseen(articles: list[FetchedArticle], verbose: bool = False) -> list[FetchedArticle]:
    if not articles:
        return []
    hashes = [a.url_hash for a in articles]
    with get_session() as s:
        rows = s.execute(select(Article.url_hash).where(Article.url_hash.in_(hashes))).all()
        seen = {r[0] for r in rows}
    fresh = [a for a in articles if a.url_hash not in seen]
    if verbose:
        print(f"[dedupe] {len(articles)} → {len(fresh)} new")
    return fresh
