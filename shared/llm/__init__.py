"""Single Anthropic client factory. Agents share the same instance.

The wrapper exists so:
- Future logging / cost tracking / retries land in one place.
- Tests can swap the client easily.
"""
from __future__ import annotations
import os
from functools import lru_cache
from anthropic import Anthropic


@lru_cache(maxsize=1)
def get_client() -> Anthropic:
    key = os.getenv("ANTHROPIC_API_KEY")
    if not key:
        raise RuntimeError("ANTHROPIC_API_KEY not set")
    return Anthropic(api_key=key)
