"""Test ContextTracker functionality."""

from unittest.mock import AsyncMock

import pytest

from nanobot.agent.context_tracker import ContextTracker
from nanobot.providers.custom_provider import CustomProvider


class TestContextTracker:
    """Test suite for ContextTracker."""

    @pytest.mark.asyncio
    async def test_initial_context_loading(self):
        """Test that context tracker loads initial context from provider."""
        # Create mock provider
        mock_provider = AsyncMock(spec=CustomProvider)
        mock_provider.get_models = AsyncMock(return_value=[
            {
                "id": "model-1",
                "max_context_length": 1000,
                "loaded_context_length": 1000,
                "metadata": {}
            },
            {
                "id": "model-2",
                "max_context_length": 2000,
                "loaded_context_length": 2000,
                "metadata": {}
            }
        ])

        # Create tracker and load context
        tracker = ContextTracker(mock_provider)
        await tracker._load_initial_context()

        # Verify initial context loaded
        assert "model-1" in tracker.context_usage
        assert "model-2" in tracker.context_usage
        assert tracker.context_usage["model-1"]["max"] == 1000
        assert tracker.context_usage["model-2"]["max"] == 2000

    @pytest.mark.asyncio
    async def test_add_tokens(self):
        """Test adding tokens to context tracker."""
        mock_provider = AsyncMock(spec=CustomProvider)
        mock_provider.get_models = AsyncMock(return_value=[
            {
                "id": "model-1",
                "max_context_length": 1000,
                "loaded_context_length": 1000,
                "metadata": {}
            }
        ])

        tracker = ContextTracker(mock_provider)
        await tracker._load_initial_context()

        # Add tokens
        tracker.add_tokens("model-1", 100)
        tracker.add_tokens("model-1", 50)

        # Verify usage
        usage = tracker.get_usage("model-1")
        assert usage["used"] == 150
        assert usage["percent"] == (150 / 1000) * 100

    @pytest.mark.asyncio
    async def test_add_tokens_to_unknown_model(self):
        """Test adding tokens to unknown model (should not crash)."""
        mock_provider = AsyncMock(spec=CustomProvider)
        mock_provider.get_models = AsyncMock(return_value=[
            {
                "id": "model-1",
                "max_context_length": 1000,
                "loaded_context_length": 1000,
                "metadata": {}
            }
        ])

        tracker = ContextTracker(mock_provider)

        # Add tokens to unknown model
        tracker.add_tokens("unknown-model", 100)

        # Should not crash, but usage should be default
        usage = tracker.get_usage("unknown-model")
        assert usage["used"] == 0
        assert usage["max"] == 0

    @pytest.mark.asyncio
    async def test_get_usage(self):
        """Test getting usage for specific model."""
        mock_provider = AsyncMock(spec=CustomProvider)
        mock_provider.get_models = AsyncMock(return_value=[
            {
                "id": "model-1",
                "max_context_length": 1000,
                "loaded_context_length": 1000,
                "metadata": {}
            }
        ])

        tracker = ContextTracker(mock_provider)
        await tracker._load_initial_context()

        # Add tokens
        tracker.add_tokens("model-1", 100)

        # Get usage
        usage = tracker.get_usage("model-1")
        assert usage["used"] == 100
        assert usage["max"] == 1000
        assert usage["percent"] == 10.0
        assert "metadata" in usage

    @pytest.mark.asyncio
    async def test_get_all_usage(self):
        """Test getting usage for all models."""
        mock_provider = AsyncMock(spec=CustomProvider)
        mock_provider.get_models = AsyncMock(return_value=[
            {
                "id": "model-1",
                "max_context_length": 1000,
                "loaded_context_length": 1000,
                "metadata": {}
            },
            {
                "id": "model-2",
                "max_context_length": 2000,
                "loaded_context_length": 2000,
                "metadata": {}
            }
        ])

        tracker = ContextTracker(mock_provider)
        await tracker._load_initial_context()

        # Add tokens
        tracker.add_tokens("model-1", 100)
        tracker.add_tokens("model-2", 200)

        # Get all usage
        all_usage = tracker.get_all_usage()
        assert len(all_usage) == 2
        assert all_usage["model-1"]["used"] == 100
        assert all_usage["model-2"]["used"] == 200

    @pytest.mark.asyncio
    async def test_format_usage(self):
        """Test formatting usage for display."""
        mock_provider = AsyncMock(spec=CustomProvider)
        mock_provider.get_models = AsyncMock(return_value=[
            {
                "id": "model-1",
                "max_context_length": 1000,
                "loaded_context_length": 1000,
                "metadata": {}
            },
            {
                "id": "model-2",
                "max_context_length": 2000,
                "loaded_context_length": 2000,
                "metadata": {}
            }
        ])

        tracker = ContextTracker(mock_provider)
        await tracker._load_initial_context()

        # Add tokens
        tracker.add_tokens("model-1", 100)
        tracker.add_tokens("model-2", 200)

        # Format usage
        output = tracker.format_usage()
        assert "Context Window Usage:" in output
        assert "model-1" in output
        assert "model-2" in output
        # Check for the formatted output with fixed-width columns
        assert "    100 /   1000 tokens ( 10.0%)" in output
        assert "    200 /   2000 tokens ( 10.0%)" in output

    @pytest.mark.asyncio
    async def test_format_usage_with_zero_max(self):
        """Test formatting usage for model with zero max context."""
        mock_provider = AsyncMock(spec=CustomProvider)
        mock_provider.get_models = AsyncMock(return_value=[
            {
                "id": "model-1",
                "max_context_length": 0,
                "loaded_context_length": 0,
                "metadata": {}
            }
        ])

        tracker = ContextTracker(mock_provider)
        await tracker._load_initial_context()

        # Format usage (should skip model with zero max)
        output = tracker.format_usage()
        assert "model-1" not in output or "0 / 0" in output

    @pytest.mark.asyncio
    async def test_get_max_tokens(self):
        """Test getting max tokens for a model."""
        mock_provider = AsyncMock(spec=CustomProvider)
        mock_provider.get_models = AsyncMock(return_value=[
            {
                "id": "model-1",
                "max_context_length": 1000,
                "loaded_context_length": 1000,
                "metadata": {}
            }
        ])

        tracker = ContextTracker(mock_provider)
        await tracker._load_initial_context()

        assert tracker.get_max_tokens("model-1") == 1000
        assert tracker.get_max_tokens("unknown-model") == 0

    @pytest.mark.asyncio
    async def test_get_used_tokens(self):
        """Test getting used tokens for a model."""
        mock_provider = AsyncMock(spec=CustomProvider)
        mock_provider.get_models = AsyncMock(return_value=[
            {
                "id": "model-1",
                "max_context_length": 1000,
                "loaded_context_length": 1000,
                "metadata": {}
            }
        ])

        tracker = ContextTracker(mock_provider)
        await tracker._load_initial_context()

        tracker.add_tokens("model-1", 100)
        tracker.add_tokens("model-1", 50)

        assert tracker.get_used_tokens("model-1") == 150
        assert tracker.get_used_tokens("unknown-model") == 0

    @pytest.mark.asyncio
    async def test_warn_thresholds(self):
        """Test that warning thresholds can be configured."""
        mock_provider = AsyncMock(spec=CustomProvider)
        mock_provider.get_models = AsyncMock(return_value=[
            {
                "id": "model-1",
                "max_context_length": 1000,
                "loaded_context_length": 1000,
                "metadata": {}
            }
        ])

        # Create tracker with custom thresholds
        tracker = ContextTracker(mock_provider, warn_thresholds=[50.0, 100.0])

        # Load initial context from provider
        await tracker._load_initial_context()

        # Add tokens to trigger warning
        tracker.add_tokens("model-1", 1000)  # 100% usage

        # Verify usage is calculated correctly
        usage = tracker.get_usage("model-1")
        assert usage["percent"] == 100.0

        # Note: Threshold checking is implemented but doesn't trigger alerts yet
        # In a full implementation, this would integrate with notification system


class TestContextTrackerIntegration:
    """Integration tests with CustomProvider."""

    @pytest.mark.integration
    async def test_real_provider_integration(self):
        """Test ContextTracker with real CustomProvider."""
        # Create provider
        provider = CustomProvider(api_key="lm-studio", api_base="http://localhost:1234/v1")

        # Create tracker
        tracker = ContextTracker(provider)

        # Load initial context
        await tracker._load_initial_context()

        # Verify models loaded
        models = await provider.get_models()
        assert len(tracker.context_usage) == len(models)

        # Verify metadata included — LM Studio v0 API returns loaded_context_length
        for _model_id, usage in tracker.context_usage.items():
            assert "metadata" in usage
            assert "id" in usage["metadata"]
            assert "loaded_context_length" in usage["metadata"]
            assert usage["metadata"]["loaded_context_length"] is not None

    @pytest.mark.integration
    async def test_format_usage_with_real_provider(self):
        """Test formatting usage with real provider."""
        provider = CustomProvider(api_key="lm-studio", api_base="http://localhost:1234/v1")
        tracker = ContextTracker(provider)

        # Load initial context
        await tracker._load_initial_context()

        # Format usage
        output = tracker.format_usage()
        assert "Context Window Usage:" in output
        for model_id in tracker.context_usage:
            assert model_id in output

    @pytest.mark.integration
    async def test_add_tokens_with_real_provider(self):
        """Test adding tokens with real provider."""
        provider = CustomProvider(api_key="lm-studio", api_base="http://localhost:1234/v1")
        tracker = ContextTracker(provider)

        # Load initial context
        await tracker._load_initial_context()

        # Add tokens to a model
        tracker.add_tokens("qwen3-coder-next", 1000)

        # Verify usage
        usage = tracker.get_usage("qwen3-coder-next")
        assert usage["used"] > 0
        assert usage["percent"] > 0

    @pytest.mark.integration
    async def test_agent_loop_integration(self):
        """Test ContextTracker integration with AgentLoop."""
        # This test would require setting up a full AgentLoop
        # For now, we just verify the class can be instantiated
        provider = CustomProvider(api_key="lm-studio", api_base="http://localhost:1234/v1")
        tracker = ContextTracker(provider)

        # Verify tracker works
        await tracker._load_initial_context()
        assert len(tracker.context_usage) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
