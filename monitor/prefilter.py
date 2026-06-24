"""Multilingual M&A pre-filter regex. ES + EN + PT."""
from __future__ import annotations
import re
from .fetch import FetchedArticle

KEYWORDS = [
    # English
    r"\bacqui(?:re|red|res|sition)\b",
    r"\bmerg(?:e|ed|er|ing)\b",
    r"\bbuy(?:s|out|ing)?\b",
    r"\bsold to\b",
    r"\btakeover\b",
    r"\bfunding round\b",
    r"\bseries [A-G]\b",
    r"\bseed round\b",
    r"\braised \$\d",
    r"\bstrategic (?:investor|partnership|investment)\b",
    r"\bappointed\s+(?:as\s+)?(?:CEO|CFO|COO|President|VP|SVP|EVP|Director)\b",
    r"\bsteps down\b",
    r"\bIPO\b",
    r"\bgo[- ]private\b",
    r"\bdivest(?:s|ed|iture|ment)?\b",
    # Spanish
    r"\badquir(?:e|ió|ido|ida|iere)\b",
    r"\badquisición\b",
    r"\bcompra (?:a|el|la|de)\b",
    r"\bfusi(?:ón|ona|onan)\b",
    r"\bse fusiona\b",
    r"\branda? de inversión\b",
    r"\binversión estratégica\b",
    r"\blevantó \$\d",
    r"\brecaudó \$\d",
    r"\bdesigna(?:do|da)?\s+(?:como|nuevo)\s+(?:CEO|director|presidente|VP)\b",
    r"\bnombrad[oa]\s+(?:CEO|director|presidente)\b",
    r"\bsalida a bolsa\b",
    r"\boferta pública\b",
    # Portuguese
    r"\badquiri(?:u|do|da|ção)\b",
    r"\bfus(?:ão|ões|iona)\b",
    r"\bcompra (?:a|o|do|da)\b",
    r"\brodada de investimento\b",
    r"\bcaptou R?\$",
    r"\bnomead[oa]\s+(?:como\s+)?(?:CEO|diretor|presidente)\b",
    r"\babertura de capital\b",
]

_RX = re.compile("|".join(KEYWORDS), re.IGNORECASE)


def is_relevant(article: FetchedArticle) -> bool:
    return bool(_RX.search(f"{article.title}  {article.snippet}"))


def filter_articles(articles: list[FetchedArticle], verbose: bool = False) -> list[FetchedArticle]:
    kept = [a for a in articles if is_relevant(a)]
    if verbose:
        print(f"[prefilter] {len(articles)} → {len(kept)} after M&A keyword filter")
    return kept
