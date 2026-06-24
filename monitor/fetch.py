"""SerpAPI Google News fetcher."""
from __future__ import annotations
import hashlib
from dataclasses import dataclass
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


def _build_queries(cfg: Config) -> list[tuple[str, int, str]]:
    out: list[tuple[str, int, str]] = []
    for c in cfg.tier_1 + cfg.tier_2:
        for variant in cfg.query_variants:
            out.append((variant.format(name=c.name), c.tier, c.name))
    for kw in cfg.tier_3_keywords:
        out.append((kw, 3, ""))
    return out


def _serpapi_call(query: str, cfg: Config, lang: str) -> list[dict]:
    params = {
        "engine": "google_news",
        "q": query,
        "api_key": cfg.serpapi_key,
        "hl": lang,
        "gl": "co" if lang == "es" else "us",
        "num": cfg.serpapi_num,
        "tbs": "qdr:d" if cfg.lookback_hours <= 24 else "qdr:w",
    }
    return GoogleSearch(params).get_dict().get("news_results", []) or []


def fetch_all(cfg: Config, max_queries: int | None = None, verbose: bool = False) -> list[FetchedArticle]:
    queries = _build_queries(cfg)
    if max_queries:
        queries = queries[:max_queries]
    if verbose:
        print(f"[fetch] {len(queries)} queries × {len(cfg.languages)} languages")

    articles: list[FetchedArticle] = []
    for q, tier, company in queries:
        for lang in cfg.languages:
            try:
                results = _serpapi_call(q, cfg, lang)
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
