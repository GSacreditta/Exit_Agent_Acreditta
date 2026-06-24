"""Monitor Slack notification — uses shared.slack.SlackPoster (bot token API)."""
from __future__ import annotations
from shared.slack import poster_from_env
from shared.db import Article, Extraction
from .config import Config


def _emoji(urgent: bool) -> str:
    return "🚨" if urgent else "🔔"


def _format_line(ext: Extraction, art: Article) -> str:
    companies = ", ".join(c["name"] for c in (ext.companies or [])) or "?"
    amount = ext.amount or ""
    amount_str = f" ({amount})" if amount else ""
    head = f"{_emoji(ext.is_urgent)} *{ext.deal_type.title()}* — {companies}{amount_str}"
    body = f"_{ext.why_it_matters}_"
    link = f"<{art.url}|{art.title[:100]}>"
    return f"{head}\n{body}\n{link}"


def notify(persisted: list[tuple[Extraction, Article]], cfg: Config, dry_run: bool = False) -> None:
    if not persisted:
        return
    if dry_run:
        print("\n[slack dry-run]")
        for ext, art in persisted:
            print(_format_line(ext, art))
            print()
        return

    poster = poster_from_env(agent="monitor")
    if cfg.slack_mode == "per_item":
        for ext, art in persisted:
            poster.post(_format_line(ext, art), related_extraction_id=ext.id)
        return

    # digest mode
    n_urgent = sum(1 for ext, _ in persisted if ext.is_urgent)
    header = f"*Acreditta M&A Watch — {len(persisted)} señales hoy ({n_urgent} urgentes)*"
    lines = [_format_line(ext, art) for ext, art in persisted]
    text = header + "\n\n" + "\n\n".join(lines)
    poster.post(text)
