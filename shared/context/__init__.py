"""Loads the Markdown knowledge base from `knowledge/` for the Advisor.

The Advisor reads these files into context on each conversation. Keep them
small individually; the loader lazy-loads on demand.
"""
from __future__ import annotations
from pathlib import Path
from functools import lru_cache

ROOT = Path(__file__).resolve().parents[2]
KNOWLEDGE_DIR = ROOT / "knowledge"


@lru_cache(maxsize=32)
def load(filename: str) -> str:
    """Load one knowledge file by name (e.g. '07_acreditta_context.md')."""
    path = KNOWLEDGE_DIR / filename
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def context_block() -> str:
    """The canonical Acreditta context that prepends every Advisor call."""
    return load("07_acreditta_context.md")


def list_files() -> list[str]:
    if not KNOWLEDGE_DIR.exists():
        return []
    return sorted(p.name for p in KNOWLEDGE_DIR.glob("*.md"))
