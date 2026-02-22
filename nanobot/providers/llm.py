"""LLM client interface for ReflectionEngine."""

from typing import Any


class LLMClient:
    """Minimal LLM client interface for ReflectionEngine."""

    def __init__(self, api_key: str | None = None, api_base: str | None = None):
        """Initialize the LLM client."""
        self.api_key = api_key
        self.api_base = api_base
