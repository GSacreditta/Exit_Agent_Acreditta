"""The one LLM call in the Monitor pipeline."""
from __future__ import annotations
import json
from typing import Optional

from shared.llm import get_client
from shared.context import context_block
from .config import Config
from .fetch import FetchedArticle
from .schema import is_valid


_SYSTEM_PROMPT_BASE = """You are an M&A signal extractor for Acreditta's exit process.

Acreditta cares about news that could affect its sale process:
- Acquisitions, mergers, funding, exec changes, divestitures, IPOs in EdTech, credentials, LMS, skills intelligence, or corporate learning
- Especially anything involving Latin America or Spanish-speaking markets
- Deal advisors, bankers, law firms named in deals
- Decision-makers named in articles

You must respond with ONLY a single JSON object. No preamble, no markdown fences, no commentary.

Schema:
{
  "relevant": true|false,
  "deal_type": "acquisition" | "merger" | "funding" | "partnership" | "divestiture" | "exec_change" | "ipo" | "other" | "none",
  "companies": [ {"name": "...", "role": "acquirer|target|investor|advisor|partner|other"} ],
  "people": [ {"name": "...", "position": "...", "company": "...", "role_in_deal": "sponsor|dealmaker|spokesperson|advisor|other"} ],
  "amount": "string like '$50M' or null if not disclosed",
  "category": "credentials" | "LMS" | "skills" | "LATAM_edtech" | "corporate_learning" | "other",
  "why_it_matters": "one sentence tying this back to Acreditta's exit process"
}

Rules:
- If the article is not a real corporate development event (product launch, generic trend, opinion piece) set relevant=false, deal_type="none".
- Be conservative on `people`: only include names actually named in the article with their position.
- `category` reflects the SUBJECT of the deal.
- `why_it_matters` must be specific. "EdTech consolidation continues" is bad. "Third credentials acquisition in 90 days — accelerates market timing" is good.
"""


def _system_prompt() -> str:
    """Prepend the Acreditta context so the model judges relevance with the right frame."""
    ctx = context_block()
    if not ctx:
        return _SYSTEM_PROMPT_BASE
    return f"{_SYSTEM_PROMPT_BASE}\n\n---\n# Acreditta Context\n{ctx}"


def _user_prompt(article: FetchedArticle, extracted: Optional[str]) -> str:
    parts = [
        f"# Article",
        f"Title: {article.title}",
        f"Source: {article.source}",
        f"Date: {article.article_date}",
        f"URL: {article.link}",
        f"Watchlist tier: {article.tier}",
        f"Matched company: {article.matched_company or '(keyword query)'}",
        "",
        f"## Snippet",
        article.snippet or "(no snippet available)",
    ]
    if extracted:
        parts.extend(["", "## Extracted content", extracted])
    return "\n".join(parts)


def classify(
    article: FetchedArticle,
    cfg: Config,
    extracted_content: Optional[str] = None,
) -> Optional[dict]:
    client = get_client()
    user = _user_prompt(article, extracted_content)
    system = _system_prompt()

    for attempt in (1, 2):
        try:
            resp = client.messages.create(
                model=cfg.claude_model,
                max_tokens=800,
                system=system,
                messages=[{"role": "user", "content": user}],
            )
            text = "".join(b.text for b in resp.content if hasattr(b, "text")).strip()
            if text.startswith("```"):
                text = text.strip("`")
                if text.startswith("json"):
                    text = text[4:]
                text = text.strip()
            payload = json.loads(text)
            if is_valid(payload):
                return payload
        except Exception:
            if attempt == 2:
                return None
            continue
    return None
