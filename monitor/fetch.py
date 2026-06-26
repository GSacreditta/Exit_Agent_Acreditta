"""SerpAPI Google News fetcher."""
from __future__ import annotations
import hashlib
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from serpapi import GoogleSearch

from .config import Config


@dataclass
class FetchedArticle:
    query: str
    title: str
    link: str
    snippet: str
    source: str
    article_date: str
    tier: int
    matched_company: str

    @property
    def url_hash(self) -> str:
        return hashlib.sha1(self.link.encode("utf-8")).hexdigest()


_GL_MAP = {"es": "co", "pt": "br", "en": "us"}


def _variant_for_lang(cfg: Config, lang: str) -> str:
    return {"en": cfg.query_variant_en, "es": cfg.query_variant_es, "pt": cfg.query_variant_pt}[lang]


def _after_date(lookback_hours: int) -> str:
    """Google News `after:YYYY-MM-DD` date filter."""
    dt = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)
    return f"after:{dt.strftime('%Y-%m-%d')}"


def _build_queries(cfg: Config, languages: list[str]) -> list[tuple[str, int, str, str]]:
    """Returns (query, tier, company, lang) tuples — one per company per language."""
    out: list[tuple[str, int, str, str]] = []
    for c in cfg.tier_1 + cfg.tier_2:
        for lang in languages:
            q = _variant_for_lang(cfg, lang).format(name=c.name)
            out.append((q, c.tier, c.name, lang))
    for kw in cfg.tier_3_keywords:
        for lang in languages:
            out.append((kw, 3, "", lang))
    return out


def _serpapi_call(query: str, cfg: Config, lang: str, lookback_hours: int) -> list[dict]:
    q_with_date = f"{query} {_after_date(lookback_hours)}"
    params = {
        "engine": "google_news",
        "q": q_with_date,
        "api_key": cfg.serpapi_key,
        "hl": lang,
        "gl": _GL_MAP.get(lang, "us"),
        "num": cfg.serpapi_num,
    }
    return GoogleSearch(params).get_dict().get("news_results", []) or []


def fetch_all(
    cfg: Config,
    max_queries: int | None = None,
    verbose: bool = False,
    lang_override: list[str] | None = None,
) -> list[FetchedArticle]:
    languages = lang_override or cfg.languages
    lookback = cfg.lookback_hours_pt if languages == ["pt"] else cfg.lookback_hours
    queries = _build_queries(cfg, languages)
    if max_queries:
        queries = queries[:max_queries]
    if verbose:
        print(f"[fetch] {len(queries)} queries · langs={languages} · lookback={lookback}h")

    articles: list[FetchedArticle] = []
    for q, tier, company, lang in queries:
        try:
            results = _serpapi_call(q, cfg, lang, lookback)
        except Exception as e:
            if verbose:
                print(f"[fetch] error on '{q}' ({lang}): {e}")
            continue
        for r in results:
            link = r.get("link") or r.get("url") or ""
            if not link:
                continue
            src = r.get("source", "")
            if isinstance(src, dict):
                src = src.get("name", "")
            articles.append(FetchedArticle(
                query=q,
                title=(r.get("title") or "").strip(),
                link=link,
                snippet=(r.get("snippet") or "").strip(),
                source=str(src),
                article_date=r.get("date", ""),
                tier=tier,
                matched_company=company,
            ))
    if verbose:
        print(f"[fetch] {len(articles)} raw results")
    return articles
