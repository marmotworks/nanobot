"""Track context window usage across models."""

from typing import Any

from loguru import logger


class ContextTracker:
    """Track context window usage across models with LM Studio metadata."""

    def __init__(
        self,
        provider: Any,
        warn_thresholds: list[float] | None = None
    ):
        """
        Initialize context tracker.

        Args:
            provider: Provider instance with get_models() method
            warn_thresholds: List of usage percentages to trigger warnings
        """
        self.provider = provider
        self.warn_thresholds = warn_thresholds if warn_thresholds is not None else [80.0, 90.0, 100.0]
        self.context_usage = {}  # {model_id: {"max": int, "used": int, "percent": float, "metadata": dict}}
        # Note: _load_initial_context() is async and should be awaited in async context

    async def _load_initial_context(self) -> None:
        """Load initial context from provider."""
        models = await self.provider.get_models()
        for model in models:
            # get_models() may return dicts (LM Studio) or strings (Bedrock)
            if isinstance(model, str):
                model_id = model
                max_ctx = 0
                metadata: dict = {}
            else:
                model_id = model.get("id", "")
                max_ctx = model.get("loaded_context_length") or model.get("max_context_length") or 0
                metadata = model
            if not model_id:
                continue
            self.context_usage[model_id] = {
                "max": max_ctx,
                "used": 0,
                "percent": 0.0,
                "metadata": metadata,
            }

    def add_tokens(self, model_id: str, tokens: int) -> None:
        """
        Add tokens to context usage for a model.

        Args:
            model_id: The model identifier
            tokens: Number of tokens added
        """
        if model_id not in self.context_usage:
            return

        self.context_usage[model_id]["used"] += tokens

        # Handle division by zero
        max_context = self.context_usage[model_id]["max"]
        if max_context and max_context > 0:
            self.context_usage[model_id]["percent"] = (
                self.context_usage[model_id]["used"] / max_context
            ) * 100
        else:
            self.context_usage[model_id]["percent"] = 0.0

        self._check_warnings(model_id)

    def get_usage(self, model_id: str) -> dict[str, Any]:
        """
        Get context usage for a specific model.

        Args:
            model_id: The model identifier

        Returns:
            Dict with "max", "used", "percent", and "metadata" keys
        """
        return self.context_usage.get(model_id, {"max": 0, "used": 0, "percent": 0, "metadata": {}})

    def get_all_usage(self) -> dict[str, Any]:
        """
        Get context usage for all models.

        Returns:
            Dict mapping model_id to usage info
        """
        return self.context_usage

    def _check_warnings(self, model_id: str) -> None:
        """
        Check if usage exceeds warning thresholds.

        Args:
            model_id: The model identifier
        """
        usage = self.context_usage[model_id]
        for threshold in self.warn_thresholds:
            if usage["percent"] >= threshold and usage["percent"] < threshold + 5.0:
                logger.warning("Context window usage for {} at {:.1f}% (threshold: {}%)", model_id, usage["percent"], threshold)

    def format_usage(self) -> str:
        """
        Format context usage for display.

        Returns:
            Formatted string showing usage for all models
        """
        lines = []
        for model_id, usage in self.context_usage.items():
            if usage["max"] > 0:
                lines.append(
                    f"  {model_id}: {usage['used']:>6} / {usage['max']:>6} tokens "
                    f"({usage['percent']:>5.1f}%)"
                )
        if not lines:
            return ""
        return "Context Window Usage:\n" + "\n".join(lines)

    def get_max_tokens(self, model_id: str) -> int:
        """
        Get the maximum context length for a model.

        Args:
            model_id: The model identifier

        Returns:
            Maximum context length in tokens
        """
        return self.context_usage.get(model_id, {}).get("max", 0)

    def get_used_tokens(self, model_id: str) -> int:
        """
        Get the number of tokens used for a model.

        Args:
            model_id: The model identifier

        Returns:
            Number of tokens used
        """
        return self.context_usage.get(model_id, {}).get("used", 0)
