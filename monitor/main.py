"""Monitor orchestrator. Cloud Run Job entry point.

Usage:
  python -m monitor.main                  # full run
  python -m monitor.main --dry-run        # no Slack post, no DB write
  python -m monitor.main --max-queries 5  # cap queries for testing
"""
from __future__ import annotations
import argparse
import sys
import time

from .config import load_config
from .fetch import fetch_all
from .prefilter import filter_articles
from .dedupe import filter_unseen
from .enrich import enrich_articles
from .classify import classify
from .persist import save_articles_and_extractions, update_people_index
from .report import append_report
from .slack import notify


def run(dry_run: bool = False, max_queries: int | None = None, lang_override: list[str] | None = None) -> int:
    cfg = load_config()
    missing = [k for k, v in {
        "SERPAPI_KEY": cfg.serpapi_key,
        "ANTHROPIC_API_KEY": cfg.anthropic_key,
    }.items() if not v]
    if missing:
        print(f"[fatal] missing env vars: {', '.join(missing)}")
        return 2

    print("=" * 60)
    print(f"Acreditta Monitor — model={cfg.claude_model} mode={cfg.slack_mode} dry_run={dry_run}")
    print("=" * 60)

    t0 = time.time()

    # 1-3. Fetch
    articles = fetch_all(cfg, max_queries=max_queries, verbose=True, lang_override=lang_override)
    if not articles:
        return 0

    # 4. Dedupe
    articles = filter_unseen(articles, verbose=True)
    if not articles:
        return 0

    # 5. Pre-filter
    articles = filter_articles(articles, verbose=True)
    if not articles:
        return 0

    # 6. Enrich (optional)
    extracted = enrich_articles(articles, cfg, verbose=True)

    # 7. Classify (the one LLM call)
    results: list[tuple] = []
    failed = 0
    for art in articles:
        content = extracted.get(art.link)
        ext = classify(art, cfg, extracted_content=content)
        if ext is None:
            failed += 1
        results.append((art, ext))
    print(f"[classify] {len(articles)} articles · {failed} classify failures")

    if dry_run:
        # Print what would be persisted, nothing else
        relevant = [(a, e) for a, e in results if e and e.get("relevant")]
        print(f"[dry-run] would persist {len(results)} articles, {len(relevant)} relevant extractions")
        for a, e in relevant:
            print(f"  - {e.get('deal_type')}: {a.title[:80]}")
        return 0

    # 8-9. Persist articles + extractions
    persisted = save_articles_and_extractions(results, verbose=True)

    # 10. Update people index
    update_people_index(persisted)

    # 11. Markdown report (if we're on a writable FS)
    try:
        path = append_report(persisted)
        if path:
            print(f"[report] wrote {path}")
    except OSError:
        pass  # ephemeral FS, ignore

    # 12. Slack
    notify(persisted, cfg, dry_run=dry_run)
    print(f"[slack] notified ({cfg.slack_mode} mode)")

    elapsed = time.time() - t0
    print(f"[done] {elapsed:.1f}s · {len(persisted)} signals · {failed} classify failures")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--max-queries", type=int, default=None)
    parser.add_argument("--lang", nargs="+", default=None, help="Override languages, e.g. --lang pt")
    args = parser.parse_args()
    return run(dry_run=args.dry_run, max_queries=args.max_queries, lang_override=args.lang)


if __name__ == "__main__":
    sys.exit(main())
