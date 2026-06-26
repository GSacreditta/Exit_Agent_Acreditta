"""Monitor's local config: env + watchlist.yaml."""
from __future__ import annotations
import os
from dataclasses import dataclass, field
from pathlib import Path
import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]


@dataclass
class Company:
    name: str
    aliases: list[str] = field(default_factory=list)
    tier: int = 1

    @property
    def all_names(self) -> list[str]:
        return [self.name] + self.aliases


@dataclass
class Config:
    # secrets / env
    serpapi_key: str
    parallel_key: str
    anthropic_key: str
    claude_model: str
    use_parallel_extract: bool
    slack_mode: str
    serpapi_num: int
    lookback_hours: int
    # watchlist
    tier_1: list[Company]
    tier_2: list[Company]
    tier_3_keywords: list[str]
    query_variant_en: str
    query_variant_es: str
    query_variant_pt: str
    languages: list[str]
    languages_pt: list[str]
    lookback_hours_pt: int


def load_config() -> Config:
    load_dotenv(ROOT / ".env")
    with open(ROOT / "config" / "watchlist.yaml") as f:
        wl = yaml.safe_load(f)

    tier_1 = [Company(c["name"], c.get("aliases", []), tier=1) for c in wl["tier_1_buyers"]]
    tier_2 = [Company(c["name"], c.get("aliases", []), tier=2) for c in wl["tier_2_latam_edtech"]]

    return Config(
        serpapi_key=os.getenv("SERPAPI_KEY", ""),
        parallel_key=os.getenv("PARALLEL_API_KEY", ""),
        anthropic_key=os.getenv("ANTHROPIC_API_KEY", ""),
        claude_model=os.getenv("CLAUDE_MODEL", "claude-haiku-4-5"),
        use_parallel_extract=os.getenv("USE_PARALLEL_EXTRACT", "true").lower() == "true",
        slack_mode=os.getenv("SLACK_MODE", "digest"),
        serpapi_num=int(os.getenv("SERPAPI_NUM", "10")),
        lookback_hours=int(os.getenv("LOOKBACK_HOURS", wl["settings"]["lookback_hours"])),
        tier_1=tier_1,
        tier_2=tier_2,
        tier_3_keywords=wl["tier_3_category_keywords"],
        query_variant_en=wl["settings"]["query_variants_en"],
        query_variant_es=wl["settings"]["query_variants_es"],
        query_variant_pt=wl["settings"]["query_variants_pt"],
        languages=wl["settings"]["languages"],
        languages_pt=wl["settings"].get("languages_pt", ["pt"]),
        lookback_hours_pt=int(wl["settings"].get("lookback_hours_pt", 360)),
    )
