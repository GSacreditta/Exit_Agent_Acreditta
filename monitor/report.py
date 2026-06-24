"""Optional Markdown report — humans like a chronological log.

In Phase 1 this writes to local disk only when running locally (the Cloud Run
filesystem is ephemeral). For long-term archival across runs, the DB is the
source of truth; this is a nicety for the team to read.
"""
from __future__ import annotations
import datetime as dt
from pathlib import Path
from shared.db import Article, Extraction

REPORTS = Path("data/reports")


def _format_entry(ext: Extraction, art: Article) -> str:
    companies = ", ".join(f"{c['name']} ({c['role']})" for c in (ext.companies or [])) or "—"
    people = ext.people or []
    if people:
        people_str = "\n".join(
            f"  - **{p.get('name', '?')}** — {p.get('position', '?')} @ {p.get('company', '?')}"
            f" ({p.get('role_in_deal', 'other')})"
            for p in people
        )
    else:
        people_str = "  - _(none named)_"
    tag = "🚨 **URGENTE**" if ext.is_urgent else "🔔"
    return (
        f"\n### {tag} {art.title}\n\n"
        f"- **Fecha:** {art.article_date or 'n/a'}\n"
        f"- **Fuente:** {art.source or 'n/a'}\n"
        f"- **Tipo de deal:** {ext.deal_type}\n"
        f"- **Categoría:** {ext.category}\n"
        f"- **Monto:** {ext.amount or '—'}\n"
        f"- **Tier:** {art.tier}\n"
        f"- **Empresas:** {companies}\n"
        f"- **Personas:**\n{people_str}\n"
        f"- **Why it matters:** {ext.why_it_matters}\n"
        f"- **Link:** {art.url}\n"
    )


def append_report(persisted: list[tuple[Extraction, Article]]) -> Path | None:
    if not persisted:
        return None
    REPORTS.mkdir(parents=True, exist_ok=True)
    today = dt.date.today()
    path = REPORTS / f"MA_Watch_{today:%Y-%m}.md"
    if not path.exists():
        path.write_text(
            f"# Acreditta M&A Watch — {today:%B %Y}\n\n"
            f"_Daily monitor — generated automatically. DB is source of truth._\n"
        )
    block = [f"\n---\n## {today:%Y-%m-%d}\n"]
    for ext, art in persisted:
        block.append(_format_entry(ext, art))
    with open(path, "a") as f:
        f.write("".join(block))
    return path
