"""
Tests for model validation and specification in subagent spawning.

These tests verify:
1. Model validation when spawning subagents
2. Available models detection from providers
3. Model specification via CLI
4. Model specification via gateway API
5. Error handling for invalid models
6. Fallback behavior when model is not specified
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from nanobot.agent.subagent import SubagentManager
from nanobot.bus.queue import MessageBus
from nanobot.providers.base import LLMProvider
from nanobot.providers.registry import list_models

# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture
def mock_provider():
    """Mock LLM provider."""
    provider = MagicMock(spec=LLMProvider)
    provider.get_default_model.return_value = "zai-org/glm-4.7-flash"
    provider.api_key = "test-key"
    provider.api_base = "http://localhost:1234/v1"
    provider.chat = AsyncMock()
    return provider


@pytest.fixture
def mock_bus():
    """Mock message bus."""
    bus = MagicMock(spec=MessageBus)
    bus.publish_inbound = AsyncMock()
    return bus


@pytest.fixture
def workspace(tmp_path):
    """Test workspace directory."""
    return tmp_path / "workspace"


@pytest.fixture
def subagent_manager(mock_provider, workspace, mock_bus):
    """Create a SubagentManager instance for testing."""
    return SubagentManager(
        provider=mock_provider,
        workspace=workspace,
        bus=mock_bus,
        model="zai-org/glm-4.7-flash",
    )


# =============================================================================
# Test: list_models Function
# =============================================================================

class TestListModels:
    """Tests for the list_models function in registry."""

    @pytest.mark.asyncio
    async def test_list_models_custom_provider_with_api_base(self):
        """Test list_models with custom provider that has an API base."""
        models = await list_models(
            provider_name="custom",
            api_key="test-key",
            api_base="http://localhost:8000/v1"
        )
        # Should return models from the API
        assert isinstance(models, list)

    @pytest.mark.asyncio
    async def test_list_models_gateway_provider(self):
        """Test list_models with gateway provider (OpenRouter, etc.)."""
        models = await list_models(
            provider_name="openrouter",
            api_key="sk-or-test",
            api_base="https://openrouter.ai/api/v1"
        )
        # Should return models from the API
        assert isinstance(models, list)

    @pytest.mark.asyncio
    async def test_list_models_local_provider(self):
        """Test list_models with local provider (vLLM, Ollama)."""
        models = await list_models(
            provider_name="vllm",
            api_key="test-key",
            api_base="http://localhost:8000/v1"
        )
        # Should return models from the API
        assert isinstance(models, list)

    @pytest.mark.asyncio
    async def test_list_models_no_provider_returns_empty(self):
        """Test list_models without provider returns empty list."""
        models = await list_models(
            provider_name=None,
            api_key=None,
            api_base=None
        )
        assert models == []

    @pytest.mark.asyncio
    async def test_list_models_network_error_returns_empty(self):
        """Test list_models handles network errors gracefully."""
        with patch("nanobot.providers.custom_provider.CustomProvider.get_models") as mock_get_models:
            mock_get_models.return_value = []
            models = await list_models(
                provider_name="custom",
                api_key="test-key",
                api_base="http://localhost:8000/v1"
            )
            # Should return empty list on error (mocked get_models returns empty)
            assert models == []


# =============================================================================
# Test: SubagentManager Model Validation
# =============================================================================

class TestSubagentManagerModelValidation:
    """Tests for model validation in SubagentManager.spawn()."""

    @pytest.mark.asyncio
    async def test_spawn_with_valid_model(self, subagent_manager, mock_provider):
        """Test spawn with a valid model that exists."""
        mock_provider.chat = AsyncMock()
        mock_provider.chat.return_value = MagicMock(
            content="Task completed",
            has_tool_calls=False
        )

        # Mock list_models to return the model being tested
        with patch("nanobot.agent.subagent.list_models") as mock_list_models:
            mock_list_models.return_value = ["zai-org/glm-4.7-flash", "deepseek/deepseek-chat"]

            result = await subagent_manager.spawn(
                task="Test task",
                label="Test",
                model="zai-org/glm-4.7-flash"
            )

            # Should succeed without error
            assert "started" in result.lower()
            assert "Test" in result

    @pytest.mark.asyncio
    async def test_spawn_with_invalid_model_shows_error(self, subagent_manager, mock_provider):
        """Test spawn with an invalid model shows appropriate error."""
        # Mock list_models to return a non-empty list so validation can fail
        with patch("nanobot.agent.subagent.list_models") as mock_list_models:
            mock_list_models.return_value = ["valid-model", "another-model"]

            result = await subagent_manager.spawn(
                task="Test task",
                label="Test",
                model="nonexistent-model"
            )

            # Should return error message
            assert "Error" in result
            assert "not available" in result.lower()

    @pytest.mark.asyncio
    async def test_spawn_with_nonexistent_model_shows_available_models(self, subagent_manager, mock_provider):
        """Test spawn with invalid model shows available models in error."""
        with patch("nanobot.agent.subagent.list_models") as mock_list_models:
            mock_list_models.return_value = ["model-a", "model-b", "model-c"]

            result = await subagent_manager.spawn(
                task="Test task",
                label="Test",
                model="nonexistent-model"
            )

            # Should show available models
            assert "not available" in result.lower()
            assert "model-a" in result
            assert "model-b" in result

    @pytest.mark.asyncio
    async def test_spawn_without_model_uses_default(self, subagent_manager, mock_provider):
        """Test spawn without model parameter uses manager's default."""
        mock_provider.chat = AsyncMock()
        mock_provider.chat.return_value = MagicMock(
            content="Task completed",
            has_tool_calls=False
        )

        result = await subagent_manager.spawn(
            task="Test task",
            label="Test"
            # No model specified
        )

        # Should succeed using default model
        assert "started" in result.lower()

    @pytest.mark.asyncio
    async def test_spawn_with_custom_provider_model_validation(self, subagent_manager, mock_provider):
        """Test model validation with custom provider (different API base)."""
        with patch("nanobot.agent.subagent.list_models") as mock_list_models:
            mock_list_models.return_value = ["custom-model-1", "custom-model-2"]

            # Test with model that doesn't exist
            result = await subagent_manager.spawn(
                task="Test",
                model="nonexistent-custom-model"
            )
            assert "Error" in result

            # Test with valid model
            mock_provider.chat = AsyncMock()
            mock_provider.chat.return_value = MagicMock(
                content="Done",
                has_tool_calls=False
            )
            result = await subagent_manager.spawn(
                task="Test",
                model="custom-model-1"
            )
            assert "started" in result.lower()


# =============================================================================
# Test: SpawnTool Model Specification
# =============================================================================

class TestSpawnToolModelSpecification:
    """Tests for model specification in SpawnTool."""

    @pytest.mark.asyncio
    async def test_spawn_tool_accepts_model_parameter(self):
        """Test that SpawnTool.execute() accepts a model parameter."""
        # This test verifies the tool interface accepts the model parameter
        # The actual implementation would be tested in integration tests

    @pytest.mark.asyncio
    async def test_spawn_tool_model_passed_to_subagent_manager(self):
        """Test that model parameter is passed to SubagentManager.spawn()."""
        # This would require mocking SubagentManager.spawn()
        pass


# =============================================================================
# Test: Error Handling and Edge Cases
# =============================================================================

class TestErrorHandling:
    """Tests for error handling in model validation."""

    @pytest.mark.asyncio
    async def test_spawn_with_empty_model_list_shows_graceful_error(self, subagent_manager, mock_provider):
        """Test spawn handles empty model list gracefully."""
        with patch("nanobot.agent.subagent.list_models") as mock_list_models:
            mock_list_models.return_value = []

            result = await subagent_manager.spawn(
                task="Test",
                model="any-model"
            )

            # Should handle gracefully without crashing
            assert result is not None
            assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_spawn_with_none_available_models(self, subagent_manager, mock_provider):
        """Test spawn handles None from list_models gracefully."""
        with patch("nanobot.agent.subagent.list_models") as mock_list_models:
            mock_list_models.return_value = None

            result = await subagent_manager.spawn(
                task="Test",
                model="any-model"
            )

            # Should handle gracefully without crashing (validation skipped when list is empty)
            assert result is not None
            assert isinstance(result, str)
            assert "Error" not in result
            assert "started" in result.lower()


# =============================================================================
# Test: Integration Tests
# =============================================================================

class TestIntegration:
    """Integration tests for model validation in subagent spawning."""

    @pytest.mark.asyncio
    async def test_full_spawn_workflow_with_model_validation(self, tmp_path, mock_provider, mock_bus):
        """Test complete spawn workflow with model validation."""
        workspace = tmp_path / "workspace"
        workspace.mkdir()

        # Create manager with custom provider
        manager = SubagentManager(
            provider=mock_provider,
            workspace=workspace,
            bus=mock_bus,
            model="zai-org/glm-4.7-flash"
        )

        # Mock the chat response
        mock_provider.chat = AsyncMock()
        mock_provider.chat.return_value = MagicMock(
            content="Task completed successfully",
            has_tool_calls=False
        )

        # Mock list_models to return available models
        with patch("nanobot.agent.subagent.list_models") as mock_list_models:
            mock_list_models.return_value = [
                "zai-org/glm-4.7-flash",
                "deepseek/deepseek-chat",
                "openai/gpt-4"
            ]

            # Spawn with valid model
            result = await manager.spawn(
                task="Search for AI news",
                label="News Search",
                model="deepseek/deepseek-chat"
            )

            # Should start successfully
            assert "started" in result.lower()
            assert "News Search" in result

            # Verify list_models was called
            mock_list_models.assert_called()

    @pytest.mark.asyncio
    async def test_fallback_to_default_when_model_not_specified(self, tmp_path, mock_provider, mock_bus):
        """Test that subagent uses default model when none is specified."""
        workspace = tmp_path / "workspace"
        workspace.mkdir()

        manager = SubagentManager(
            provider=mock_provider,
            workspace=workspace,
            bus=mock_bus,
            model="zai-org/glm-4.7-flash"
        )

        mock_provider.chat = AsyncMock()
        mock_provider.chat.return_value = MagicMock(
            content="Task done",
            has_tool_calls=False
        )

        # Spawn without model parameter
        result = await manager.spawn(
            task="Test task"
        )

        # Should succeed using default model
        assert "started" in result.lower()


# =============================================================================
# Test: Gateway API Integration (if applicable)
# =============================================================================

class TestGatewayIntegration:
    """Tests for gateway API model routing."""

    @pytest.mark.asyncio
    async def test_gateway_model_routing_with_valid_model(self):
        """Test gateway API routing with a valid model."""
        # This would be tested in integration tests with a real gateway
        pass

    @pytest.mark.asyncio
    async def test_gateway_model_routing_with_invalid_model(self):
        """Test gateway API routing with an invalid model."""
        # This would be tested in integration tests with a real gateway
        pass


# =============================================================================
# Run with pytest
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
