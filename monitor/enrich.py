"""Parallel Extract API enrichment for articles that survive the prefilter."""
from __future__ import annotations
from .config import Config
from .fetch import FetchedArticle

try:
    from parallel import Parallel
    _SDK = True
except ImportError:
    _SDK = False


def enrich_articles(
    articles: list[FetchedArticle], cfg: Config, verbose: bool = False
) -> dict[str, str]:
    if not cfg.use_parallel_extract or not articles:
        return {}
    if not _SDK:
        if verbose:
            print("[enrich] parallel-web SDK not installed, skipping")
        return {}
    if not cfg.parallel_key:
        if verbose:
            print("[enrich] PARALLEL_API_KEY missing, skipping")
        return {}

    client = Parallel(api_key=cfg.parallel_key)
    out: dict[str, str] = {}
    CHUNK = 10
    urls = [a.link for a in articles]
    for i in range(0, len(urls), CHUNK):
        batch = urls[i:i + CHUNK]
        try:
            resp = client.beta.extract(
                urls=batch,
                objective=(
                    "Identify mergers, acquisitions, funding rounds, divestitures, "
                    "executive changes, or strategic partnerships. Extract company "
                    "names, deal amounts, and named individuals with their roles."
                ),
                excerpts=True,
                full_content=False,
            )
        except Exception as e:
            if verbose:
                print(f"[enrich] Parallel error: {e}")
            continue

        for r in getattr(resp, "results", []) or []:
            url = getattr(r, "url", None) or (r.get("url") if isinstance(r, dict) else None)
            if not url:
                continue
            excerpts = getattr(r, "excerpts", None) or (r.get("excerpts") if isinstance(r, dict) else None) or []
            text = "\n\n".join(excerpts) if excerpts else ""
            if text:
                out[url] = text[:6000]

    if verbose:
        print(f"[enrich] extracted content for {len(out)}/{len(urls)} URLs")
    return out
