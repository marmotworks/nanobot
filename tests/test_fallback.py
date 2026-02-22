"""Unit tests for _chat_with_fallback method in AgentLoop."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from nanobot.agent.loop import AgentLoop
from nanobot.bus.queue import MessageBus
from nanobot.providers.base import LLMResponse


class TestChatWithFallback:
    """Test suite for _chat_with_fallback method."""

    @pytest.mark.asyncio
    async def test_primary_success_no_fallback(self):
        """Primary provider returns a normal response, fallback is never called."""
        mock_bus = MagicMock(spec=MessageBus)
        mock_provider = AsyncMock()
        mock_provider.chat.return_value = LLMResponse(
            content="Hello from primary provider",
            finish_reason="stop",
        )
        mock_provider.get_default_model.return_value = "gpt-4"

        with patch("nanobot.agent.loop.PolicyManager"), \
             patch("nanobot.agent.loop.ContextBuilder"), \
             patch("nanobot.agent.loop.ContextTracker"), \
             patch("nanobot.agent.loop.ToolRegistry"), \
             patch("nanobot.agent.loop.SubagentManager"), \
             patch("nanobot.agent.loop.SessionManager"), \
             patch("nanobot.agent.loop.MessageTool"), \
             patch("nanobot.agent.loop.SpawnTool"), \
             patch("nanobot.agent.loop.ExecTool"), \
             patch("nanobot.agent.loop.WebSearchTool"), \
             patch("nanobot.agent.loop.WebFetchTool"), \
             patch("nanobot.agent.loop.ReadFileTool"), \
             patch("nanobot.agent.loop.WriteFileTool"), \
             patch("nanobot.agent.loop.EditFileTool"), \
             patch("nanobot.agent.loop.ListDirTool"), \
             patch("nanobot.agent.loop.CronTool"), \
             patch("nanobot.agent.loop.ContextTracker") as mock_tracker_cls:

            mock_tracker = MagicMock()
            mock_tracker_cls.return_value = mock_tracker
            mock_tracker.context_usage = {}
            mock_tracker.add_tokens = MagicMock()

            agent = AgentLoop(
                bus=mock_bus,
                provider=mock_provider,
                workspace=MagicMock(),
                model="gpt-4",
            )

            messages = [{"role": "user", "content": "test"}]
            tools = []
            model = "gpt-4"
            temperature = 0.7
            max_tokens = 4096

            result = await agent._chat_with_fallback(messages, tools, model, temperature, max_tokens)

            assert result.content == "Hello from primary provider"
            assert result.finish_reason == "stop"
            mock_provider.chat.assert_called_once()
            assert mock_provider.chat.call_count == 1

    @pytest.mark.asyncio
    async def test_non_fallback_error_no_fallback_triggered(self):
        """Primary returns error with content NOT matching fallback keywords."""
        mock_bus = MagicMock(spec=MessageBus)
        mock_provider = AsyncMock()
        mock_provider.chat.return_value = LLMResponse(
            content="Error calling LLM: something went wrong",
            finish_reason="error",
        )
        mock_provider.get_default_model.return_value = "gpt-4"

        with patch("nanobot.agent.loop.PolicyManager"), \
             patch("nanobot.agent.loop.ContextBuilder"), \
             patch("nanobot.agent.loop.ContextTracker"), \
             patch("nanobot.agent.loop.ToolRegistry"), \
             patch("nanobot.agent.loop.SubagentManager"), \
             patch("nanobot.agent.loop.SessionManager"), \
             patch("nanobot.agent.loop.MessageTool"), \
             patch("nanobot.agent.loop.SpawnTool"), \
             patch("nanobot.agent.loop.ExecTool"), \
             patch("nanobot.agent.loop.WebSearchTool"), \
             patch("nanobot.agent.loop.WebFetchTool"), \
             patch("nanobot.agent.loop.ReadFileTool"), \
             patch("nanobot.agent.loop.WriteFileTool"), \
             patch("nanobot.agent.loop.EditFileTool"), \
             patch("nanobot.agent.loop.ListDirTool"), \
             patch("nanobot.agent.loop.CronTool"), \
             patch("nanobot.agent.loop.ContextTracker") as mock_tracker_cls:

            mock_tracker = MagicMock()
            mock_tracker_cls.return_value = mock_tracker
            mock_tracker.context_usage = {}
            mock_tracker.add_tokens = MagicMock()

            agent = AgentLoop(
                bus=mock_bus,
                provider=mock_provider,
                workspace=MagicMock(),
                model="gpt-4",
            )

            messages = [{"role": "user", "content": "test"}]
            tools = []
            model = "gpt-4"
            temperature = 0.7
            max_tokens = 4096

            result = await agent._chat_with_fallback(messages, tools, model, temperature, max_tokens)

            assert result.content == "Error calling LLM: something went wrong"
            assert result.finish_reason == "error"
            mock_provider.chat.assert_called_once()
            assert mock_provider.chat.call_count == 1

    @pytest.mark.asyncio
    async def test_rate_limit_triggers_fallback(self):
        """Primary returns error with 'rate_limit' in content, fallback is triggered."""
        mock_bus = MagicMock(spec=MessageBus)
        mock_provider = AsyncMock()
        mock_provider.chat.return_value = LLMResponse(
            content="Error calling LLM: rate_limit exceeded",
            finish_reason="error",
        )
        mock_provider.get_default_model.return_value = "gpt-4"

        with patch("nanobot.agent.loop.PolicyManager"), \
             patch("nanobot.agent.loop.ContextBuilder"), \
             patch("nanobot.agent.loop.ContextTracker"), \
             patch("nanobot.agent.loop.ToolRegistry"), \
             patch("nanobot.agent.loop.SubagentManager"), \
             patch("nanobot.agent.loop.SessionManager"), \
             patch("nanobot.agent.loop.MessageTool"), \
             patch("nanobot.agent.loop.SpawnTool"), \
             patch("nanobot.agent.loop.ExecTool"), \
             patch("nanobot.agent.loop.WebSearchTool"), \
             patch("nanobot.agent.loop.WebFetchTool"), \
             patch("nanobot.agent.loop.ReadFileTool"), \
             patch("nanobot.agent.loop.WriteFileTool"), \
             patch("nanobot.agent.loop.EditFileTool"), \
             patch("nanobot.agent.loop.ListDirTool"), \
             patch("nanobot.agent.loop.CronTool"), \
             patch("nanobot.agent.loop.ContextTracker") as mock_tracker_cls:

            mock_tracker = MagicMock()
            mock_tracker_cls.return_value = mock_tracker
            mock_tracker.context_usage = {}
            mock_tracker.add_tokens = MagicMock()

            agent = AgentLoop(
                bus=mock_bus,
                provider=mock_provider,
                workspace=MagicMock(),
                model="gpt-4",
            )

            messages = [{"role": "user", "content": "test"}]
            tools = []
            model = "gpt-4"
            temperature = 0.7
            max_tokens = 4096

            mock_fallback = AsyncMock()
            mock_fallback.chat.return_value = LLMResponse(
                content="Hello from fallback",
                finish_reason="stop",
            )

            with patch("nanobot.providers.custom_provider.CustomProvider", return_value=mock_fallback) as mock_custom_provider:
                result = await agent._chat_with_fallback(messages, tools, model, temperature, max_tokens)

                assert result.content == "Hello from fallback"
                assert result.finish_reason == "stop"
                mock_provider.chat.assert_called_once()
                mock_custom_provider.assert_called_once()
                mock_fallback.chat.assert_called_once()
                _, kwargs = mock_custom_provider.call_args
                assert kwargs["api_key"] == "lm-studio"
                assert kwargs["api_base"] == "http://localhost:1234/v1"
                assert kwargs["default_model"] == "zai-org/glm-4.7-flash"

    @pytest.mark.asyncio
    async def test_overloaded_triggers_fallback(self):
        """Primary returns error with 'overloaded' in content, fallback is triggered."""
        mock_bus = MagicMock(spec=MessageBus)
        mock_provider = AsyncMock()
        mock_provider.chat.return_value = LLMResponse(
            content="Error calling LLM: provider is overloaded",
            finish_reason="error",
        )
        mock_provider.get_default_model.return_value = "gpt-4"

        with patch("nanobot.agent.loop.PolicyManager"), \
             patch("nanobot.agent.loop.ContextBuilder"), \
             patch("nanobot.agent.loop.ContextTracker"), \
             patch("nanobot.agent.loop.ToolRegistry"), \
             patch("nanobot.agent.loop.SubagentManager"), \
             patch("nanobot.agent.loop.SessionManager"), \
             patch("nanobot.agent.loop.MessageTool"), \
             patch("nanobot.agent.loop.SpawnTool"), \
             patch("nanobot.agent.loop.ExecTool"), \
             patch("nanobot.agent.loop.WebSearchTool"), \
             patch("nanobot.agent.loop.WebFetchTool"), \
             patch("nanobot.agent.loop.ReadFileTool"), \
             patch("nanobot.agent.loop.WriteFileTool"), \
             patch("nanobot.agent.loop.EditFileTool"), \
             patch("nanobot.agent.loop.ListDirTool"), \
             patch("nanobot.agent.loop.CronTool"), \
             patch("nanobot.agent.loop.ContextTracker") as mock_tracker_cls:

            mock_tracker = MagicMock()
            mock_tracker_cls.return_value = mock_tracker
            mock_tracker.context_usage = {}
            mock_tracker.add_tokens = MagicMock()

            agent = AgentLoop(
                bus=mock_bus,
                provider=mock_provider,
                workspace=MagicMock(),
                model="gpt-4",
            )

            messages = [{"role": "user", "content": "test"}]
            tools = []
            model = "gpt-4"
            temperature = 0.7
            max_tokens = 4096

            mock_fallback = AsyncMock()
            mock_fallback.chat.return_value = LLMResponse(
                content="Hello from fallback",
                finish_reason="stop",
            )

            with patch("nanobot.providers.custom_provider.CustomProvider", return_value=mock_fallback) as mock_custom_provider:
                result = await agent._chat_with_fallback(messages, tools, model, temperature, max_tokens)

                assert result.content == "Hello from fallback"
                assert result.finish_reason == "stop"
                mock_provider.chat.assert_called_once()
                mock_custom_provider.assert_called_once()
                mock_fallback.chat.assert_called_once()

    @pytest.mark.asyncio
    async def test_authentication_error_triggers_fallback(self):
        """Primary returns error with 'AuthenticationError' in content, fallback is triggered."""
        mock_bus = MagicMock(spec=MessageBus)
        mock_provider = AsyncMock()
        mock_provider.chat.return_value = LLMResponse(
            content="Error calling LLM: AuthenticationError: invalid API key",
            finish_reason="error",
        )
        mock_provider.get_default_model.return_value = "gpt-4"

        with patch("nanobot.agent.loop.PolicyManager"), \
             patch("nanobot.agent.loop.ContextBuilder"), \
             patch("nanobot.agent.loop.ContextTracker"), \
             patch("nanobot.agent.loop.ToolRegistry"), \
             patch("nanobot.agent.loop.SubagentManager"), \
             patch("nanobot.agent.loop.SessionManager"), \
             patch("nanobot.agent.loop.MessageTool"), \
             patch("nanobot.agent.loop.SpawnTool"), \
             patch("nanobot.agent.loop.ExecTool"), \
             patch("nanobot.agent.loop.WebSearchTool"), \
             patch("nanobot.agent.loop.WebFetchTool"), \
             patch("nanobot.agent.loop.ReadFileTool"), \
             patch("nanobot.agent.loop.WriteFileTool"), \
             patch("nanobot.agent.loop.EditFileTool"), \
             patch("nanobot.agent.loop.ListDirTool"), \
             patch("nanobot.agent.loop.CronTool"), \
             patch("nanobot.agent.loop.ContextTracker") as mock_tracker_cls:

            mock_tracker = MagicMock()
            mock_tracker_cls.return_value = mock_tracker
            mock_tracker.context_usage = {}
            mock_tracker.add_tokens = MagicMock()

            agent = AgentLoop(
                bus=mock_bus,
                provider=mock_provider,
                workspace=MagicMock(),
                model="gpt-4",
            )

            messages = [{"role": "user", "content": "test"}]
            tools = []
            model = "gpt-4"
            temperature = 0.7
            max_tokens = 4096

            mock_fallback = AsyncMock()
            mock_fallback.chat.return_value = LLMResponse(
                content="Hello from fallback",
                finish_reason="stop",
            )

            with patch("nanobot.providers.custom_provider.CustomProvider", return_value=mock_fallback) as mock_custom_provider:
                result = await agent._chat_with_fallback(messages, tools, model, temperature, max_tokens)

                assert result.content == "Hello from fallback"
                assert result.finish_reason == "stop"
                mock_provider.chat.assert_called_once()
                mock_custom_provider.assert_called_once()
                mock_fallback.chat.assert_called_once()

    @pytest.mark.asyncio
    async def test_fallback_also_fails(self):
        """Primary triggers fallback, fallback raises Exception, returns failure response."""
        mock_bus = MagicMock(spec=MessageBus)
        mock_provider = AsyncMock()
        mock_provider.chat.return_value = LLMResponse(
            content="Error calling LLM: rate_limit exceeded",
            finish_reason="error",
        )
        mock_provider.get_default_model.return_value = "gpt-4"

        with patch("nanobot.agent.loop.PolicyManager"), \
             patch("nanobot.agent.loop.ContextBuilder"), \
             patch("nanobot.agent.loop.ContextTracker"), \
             patch("nanobot.agent.loop.ToolRegistry"), \
             patch("nanobot.agent.loop.SubagentManager"), \
             patch("nanobot.agent.loop.SessionManager"), \
             patch("nanobot.agent.loop.MessageTool"), \
             patch("nanobot.agent.loop.SpawnTool"), \
             patch("nanobot.agent.loop.ExecTool"), \
             patch("nanobot.agent.loop.WebSearchTool"), \
             patch("nanobot.agent.loop.WebFetchTool"), \
             patch("nanobot.agent.loop.ReadFileTool"), \
             patch("nanobot.agent.loop.WriteFileTool"), \
             patch("nanobot.agent.loop.EditFileTool"), \
             patch("nanobot.agent.loop.ListDirTool"), \
             patch("nanobot.agent.loop.CronTool"), \
             patch("nanobot.agent.loop.ContextTracker") as mock_tracker_cls:

            mock_tracker = MagicMock()
            mock_tracker_cls.return_value = mock_tracker
            mock_tracker.context_usage = {}
            mock_tracker.add_tokens = MagicMock()

            agent = AgentLoop(
                bus=mock_bus,
                provider=mock_provider,
                workspace=MagicMock(),
                model="gpt-4",
            )

            messages = [{"role": "user", "content": "test"}]
            tools = []
            model = "gpt-4"
            temperature = 0.7
            max_tokens = 4096

            mock_fallback = AsyncMock()
            mock_fallback.chat.side_effect = Exception("Fallback provider connection failed")

            with patch("nanobot.providers.custom_provider.CustomProvider", return_value=mock_fallback):
                result = await agent._chat_with_fallback(messages, tools, model, temperature, max_tokens)

                assert "Both primary and fallback providers failed:" in result.content
                assert result.finish_reason == "error"
                mock_provider.chat.assert_called_once()
                mock_fallback.chat.assert_called_once()
