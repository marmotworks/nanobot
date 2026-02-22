"""
Test CustomProvider's enhanced get_models() method to verify context_length extraction.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from nanobot.providers.custom_provider import CustomProvider


class TestCustomProviderContextLength:
    """Test that CustomProvider.get_models() returns model metadata including context_length."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_get_models_returns_dict_with_context_length(self):
        """Test that get_models() returns a list of dicts with id and a context length field.

        Hits localhost:1234 — requires LM Studio running. Marked as integration test.
        Accepts both v0 API format (max_context_length) and OpenAI fallback format (context_length).
        """
        provider = CustomProvider(
            api_key="lm-studio", api_base="http://localhost:1234/v1", default_model="test-model"
        )

        models = await provider.get_models()

        # Verify return type
        assert isinstance(models, list), f"Expected list, got {type(models)}"
        assert len(models) > 0, "Expected at least one model"

        # Verify each model is a dict with an id
        for model in models:
            assert isinstance(model, dict), f"Expected dict, got {type(model)}"
            assert "id" in model, "Missing 'id' field"
            # Accept either v0 API key or OpenAI fallback key
            has_ctx = "max_context_length" in model or "context_length" in model
            assert has_ctx, f"Missing context length field in model: {model.keys()}"

        print(f"✓ get_models() successfully returned {len(models)} models with context_length")

    @pytest.mark.asyncio
    async def test_get_models_handles_api_failure(self):
        """Test that get_models() handles API failures gracefully."""
        provider = CustomProvider(
            api_key="invalid-key",
            api_base="http://localhost:9999/v1",  # Invalid endpoint
            default_model="fallback-model",
        )

        # Should not raise an exception, should return fallback
        models = await provider.get_models()

        # Should return a list with fallback model info
        assert isinstance(models, list), f"Expected list, got {type(models)}"
        assert len(models) == 1, f"Expected 1 model, got {len(models)}"
        assert models[0]["id"] == "fallback-model"
        assert models[0]["context_length"] is None

        print("✓ get_models() handles API failures gracefully")

    @pytest.mark.asyncio
    async def test_get_models_empty_response(self):
        """Test that get_models() handles empty v0 API response and falls back to OpenAI API."""

        provider = CustomProvider(
            api_key="test-key", api_base="http://localhost:1234/v1", default_model="default-model"
        )

        # Mock empty v0 API response at the class level
        with patch(
            "nanobot.providers.custom_provider.CustomProvider._query_lm_studio_v0_api",
            new=AsyncMock(return_value=[]),
        ):
            # Mock OpenAI-compatible API response with predictable model data
            mock_models_response = MagicMock()
            mock_models_response.data = [
                MagicMock(id="model-1", context_length=8192),
                MagicMock(id="model-2", context_length=4096),
                MagicMock(id="model-3", context_length=16384),
            ]

            with patch.object(
                provider._client.models, "list", new=AsyncMock(return_value=mock_models_response)
            ):
                models = await provider.get_models()

        assert isinstance(models, list)
        # Should use OpenAI-compatible format with context_length field
        assert len(models) == 3, f"Expected 3 models, got {len(models)}"
        assert models[0]["id"] == "model-1"
        assert models[0]["context_length"] == 8192
        assert models[1]["id"] == "model-2"
        assert models[1]["context_length"] == 4096
        assert models[2]["id"] == "model-3"
        assert models[2]["context_length"] == 16384

        print("✓ get_models() handles empty v0 API and falls back to OpenAI API")

    @pytest.mark.asyncio
    async def test_get_models_single_model(self):
        """Test that get_models() works with a single model."""
        from unittest.mock import AsyncMock

        provider = CustomProvider(
            api_key="test-key", api_base="http://localhost:1234/v1", default_model="single-model"
        )

        # Mock single model response from v0 API
        provider._query_lm_studio_v0_api = AsyncMock(
            return_value=[
                {
                    "id": "single-model",
                    "object": "model",
                    "type": "llm",
                    "publisher": "test",
                    "arch": "test",
                    "state": "loaded",
                    "max_context_length": 8192,
                    "loaded_context_length": 8192,
                    "capabilities": [],
                    "loaded": True,
                }
            ]
        )

        models = await provider.get_models()

        assert len(models) == 1
        assert models[0]["id"] == "single-model"
        assert models[0]["max_context_length"] == 8192

        print("✓ get_models() works with single model")

        # Note: In practice, LM Studio v0 API returns 3 models, so this test is for fallback scenarios
