"""Unit tests for _chat_with_fallback config-driven fallback behavior."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from nanobot.agent.loop import AgentLoop
from nanobot.bus.queue import MessageBus
from nanobot.config.schema import Config, FallbackConfig, FallbackTierConfig
from nanobot.providers.base import LLMResponse


class TestChatWithFallbackConfig:
    """Test suite for _chat_with_fallback config-driven fallback behavior."""

    @pytest.mark.asyncio
    async def test_tier2_uses_config_model(self):
        """When config.fallback.tier2 has custom values, verify _chat_with_fallback uses them."""
        mock_bus = MagicMock(spec=MessageBus)
        mock_provider = AsyncMock()
        mock_provider.chat.return_value = LLMResponse(
            content="Error calling LLM: rate_limit exceeded",
            finish_reason="error",
        )
        mock_provider.get_default_model.return_value = "gpt-4"

        custom_tier2_model = "custom-model"
        custom_tier2_api_base = "http://custom:1234/v1"

        mock_fallback = AsyncMock()
        mock_fallback.chat.return_value = LLMResponse(
            content="Hello from custom fallback",
            finish_reason="stop",
        )

        with (
            patch("nanobot.agent.loop.PolicyManager"),
            patch("nanobot.agent.loop.ContextBuilder"),
            patch("nanobot.agent.loop.ContextTracker"),
            patch("nanobot.agent.loop.ToolRegistry"),
            patch("nanobot.agent.loop.SubagentManager"),
            patch("nanobot.agent.loop.SessionManager"),
            patch("nanobot.agent.loop.MessageTool"),
            patch("nanobot.agent.loop.SpawnTool"),
            patch("nanobot.agent.loop.ExecTool"),
            patch("nanobot.agent.loop.WebSearchTool"),
            patch("nanobot.agent.loop.WebFetchTool"),
            patch("nanobot.agent.loop.ReadFileTool"),
            patch("nanobot.agent.loop.WriteFileTool"),
            patch("nanobot.agent.loop.EditFileTool"),
            patch("nanobot.agent.loop.ListDirTool"),
            patch("nanobot.agent.loop.CronTool"),
            patch("nanobot.agent.loop.ContextTracker") as mock_tracker_cls,
        ):
            mock_tracker = MagicMock()
            mock_tracker_cls.return_value = mock_tracker
            mock_tracker.context_usage = {}
            mock_tracker.add_tokens = MagicMock()

            custom_fallback_config = Config(
                fallback=FallbackConfig(
                    tier2=FallbackTierConfig(
                        provider="custom",
                        model=custom_tier2_model,
                        api_base=custom_tier2_api_base,
                    ),
                    tier3=None,
                )
            )

            agent = AgentLoop(
                bus=mock_bus,
                provider=mock_provider,
                workspace=MagicMock(),
                model="gpt-4",
                config=custom_fallback_config,
            )

            messages = [{"role": "user", "content": "test"}]
            tools = []
            model = "gpt-4"
            temperature = 0.7
            max_tokens = 4096

            with patch(
                "nanobot.providers.custom_provider.CustomProvider", return_value=mock_fallback
            ) as mock_custom_provider:
                result = await agent._chat_with_fallback(
                    messages, tools, model, temperature, max_tokens
                )

                assert result.content == "Hello from custom fallback"
                assert result.finish_reason == "stop"
                mock_provider.chat.assert_called_once()

                mock_fallback.chat.assert_called_once()
                call_args = mock_fallback.chat.call_args
                assert call_args[1]["model"] == custom_tier2_model

                mock_custom_provider.assert_called_once()
                _, kwargs = mock_custom_provider.call_args
                assert kwargs["api_key"] == "lm-studio"
                assert kwargs["api_base"] == custom_tier2_api_base
                assert kwargs["default_model"] == custom_tier2_model

    @pytest.mark.asyncio
    async def test_tier2_uses_hardcoded_defaults_when_config_none(self):
        """When config.fallback is None, verify _chat_with_fallback uses hardcoded defaults."""
        mock_bus = MagicMock(spec=MessageBus)
        mock_provider = AsyncMock()
        mock_provider.chat.return_value = LLMResponse(
            content="Error calling LLM: rate_limit exceeded",
            finish_reason="error",
        )
        mock_provider.get_default_model.return_value = "gpt-4"

        mock_fallback = AsyncMock()
        mock_fallback.chat.return_value = LLMResponse(
            content="Hello from fallback",
            finish_reason="stop",
        )

        with (
            patch("nanobot.agent.loop.PolicyManager"),
            patch("nanobot.agent.loop.ContextBuilder"),
            patch("nanobot.agent.loop.ContextTracker"),
            patch("nanobot.agent.loop.ToolRegistry"),
            patch("nanobot.agent.loop.SubagentManager"),
            patch("nanobot.agent.loop.SessionManager"),
            patch("nanobot.agent.loop.MessageTool"),
            patch("nanobot.agent.loop.SpawnTool"),
            patch("nanobot.agent.loop.ExecTool"),
            patch("nanobot.agent.loop.WebSearchTool"),
            patch("nanobot.agent.loop.WebFetchTool"),
            patch("nanobot.agent.loop.ReadFileTool"),
            patch("nanobot.agent.loop.WriteFileTool"),
            patch("nanobot.agent.loop.EditFileTool"),
            patch("nanobot.agent.loop.ListDirTool"),
            patch("nanobot.agent.loop.CronTool"),
            patch("nanobot.agent.loop.ContextTracker") as mock_tracker_cls,
        ):
            mock_tracker = MagicMock()
            mock_tracker_cls.return_value = mock_tracker
            mock_tracker.context_usage = {}
            mock_tracker.add_tokens = MagicMock()

            agent = AgentLoop(
                bus=mock_bus,
                provider=mock_provider,
                workspace=MagicMock(),
                model="gpt-4",
                config=None,
            )

            messages = [{"role": "user", "content": "test"}]
            tools = []
            model = "gpt-4"
            temperature = 0.7
            max_tokens = 4096

            with patch(
                "nanobot.providers.custom_provider.CustomProvider", return_value=mock_fallback
            ) as mock_custom_provider:
                result = await agent._chat_with_fallback(
                    messages, tools, model, temperature, max_tokens
                )

                assert result.content == "Hello from fallback"
                assert result.finish_reason == "stop"
                mock_provider.chat.assert_called_once()
                mock_custom_provider.assert_called_once()
                _, kwargs = mock_custom_provider.call_args
                assert kwargs["api_key"] == "lm-studio"
                assert kwargs["api_base"] == "http://localhost:1234/v1"
                assert kwargs["default_model"] == "zai-org/glm-4.7-flash"

    @pytest.mark.asyncio
    async def test_tier3_uses_config_model(self):
        """When config.fallback.tier3 has custom values, verify _chat_with_fallback uses them."""
        mock_bus = MagicMock(spec=MessageBus)
        mock_provider = AsyncMock()
        mock_provider.chat.return_value = LLMResponse(
            content="Error calling LLM: rate_limit exceeded",
            finish_reason="error",
        )
        mock_provider.get_default_model.return_value = "gpt-4"

        custom_tier3_model = "custom-bedrock-model"
        custom_tier3_region = "eu-west-1"

        mock_fallback_tier2 = AsyncMock()
        mock_fallback_tier2.chat.side_effect = Exception("Tier2 failed")

        mock_bedrock_fallback = AsyncMock()
        mock_bedrock_fallback.chat.return_value = LLMResponse(
            content="Hello from custom Bedrock",
            finish_reason="stop",
        )

        with (
            patch("nanobot.agent.loop.PolicyManager"),
            patch("nanobot.agent.loop.ContextBuilder"),
            patch("nanobot.agent.loop.ContextTracker"),
            patch("nanobot.agent.loop.ToolRegistry"),
            patch("nanobot.agent.loop.SubagentManager"),
            patch("nanobot.agent.loop.SessionManager"),
            patch("nanobot.agent.loop.MessageTool"),
            patch("nanobot.agent.loop.SpawnTool"),
            patch("nanobot.agent.loop.ExecTool"),
            patch("nanobot.agent.loop.WebSearchTool"),
            patch("nanobot.agent.loop.WebFetchTool"),
            patch("nanobot.agent.loop.ReadFileTool"),
            patch("nanobot.agent.loop.WriteFileTool"),
            patch("nanobot.agent.loop.EditFileTool"),
            patch("nanobot.agent.loop.ListDirTool"),
            patch("nanobot.agent.loop.CronTool"),
            patch("nanobot.agent.loop.ContextTracker") as mock_tracker_cls,
        ):
            mock_tracker = MagicMock()
            mock_tracker_cls.return_value = mock_tracker
            mock_tracker.context_usage = {}
            mock_tracker.add_tokens = MagicMock()

            custom_fallback_config = Config(
                fallback=FallbackConfig(
                    tier2=FallbackTierConfig(
                        provider="custom",
                        model="zai-org/glm-4.7-flash",
                        api_base="http://localhost:1234/v1",
                    ),
                    tier3=FallbackTierConfig(
                        provider="bedrock",
                        model=custom_tier3_model,
                        region=custom_tier3_region,
                    ),
                )
            )

            agent = AgentLoop(
                bus=mock_bus,
                provider=mock_provider,
                workspace=MagicMock(),
                model="gpt-4",
                config=custom_fallback_config,
            )

            messages = [{"role": "user", "content": "test"}]
            tools = []
            model = "gpt-4"
            temperature = 0.7
            max_tokens = 4096

            with (
                patch(
                    "nanobot.providers.custom_provider.CustomProvider",
                    return_value=mock_fallback_tier2,
                ),
                patch(
                    "nanobot.providers.bedrock_provider.BedrockProvider",
                    return_value=mock_bedrock_fallback,
                ) as mock_bedrock_provider,
            ):
                result = await agent._chat_with_fallback(
                    messages, tools, model, temperature, max_tokens
                )

                assert result.content == "Hello from custom Bedrock"
                assert result.finish_reason == "stop"
                mock_provider.chat.assert_called_once()
                mock_fallback_tier2.chat.assert_called_once()
                mock_bedrock_fallback.chat.assert_called_once()

                mock_bedrock_provider.assert_called_once()
                _, kwargs = mock_bedrock_provider.call_args
                assert kwargs["region_name"] == custom_tier3_region
                assert kwargs["default_model"] == custom_tier3_model

    @pytest.mark.asyncio
    async def test_tier3_uses_hardcoded_defaults_when_config_none(self):
        """When config.fallback is None and tier2 fails, verify hardcoded tier3 defaults."""
        mock_bus = MagicMock(spec=MessageBus)
        mock_provider = AsyncMock()
        mock_provider.chat.return_value = LLMResponse(
            content="Error calling LLM: rate_limit exceeded",
            finish_reason="error",
        )
        mock_provider.get_default_model.return_value = "gpt-4"

        mock_fallback_tier2 = AsyncMock()
        mock_fallback_tier2.chat.side_effect = Exception("Tier2 failed")

        mock_bedrock_fallback = AsyncMock()
        mock_bedrock_fallback.chat.return_value = LLMResponse(
            content="Hello from AWS Bedrock (tier 3)",
            finish_reason="stop",
        )

        with (
            patch("nanobot.agent.loop.PolicyManager"),
            patch("nanobot.agent.loop.ContextBuilder"),
            patch("nanobot.agent.loop.ContextTracker"),
            patch("nanobot.agent.loop.ToolRegistry"),
            patch("nanobot.agent.loop.SubagentManager"),
            patch("nanobot.agent.loop.SessionManager"),
            patch("nanobot.agent.loop.MessageTool"),
            patch("nanobot.agent.loop.SpawnTool"),
            patch("nanobot.agent.loop.ExecTool"),
            patch("nanobot.agent.loop.WebSearchTool"),
            patch("nanobot.agent.loop.WebFetchTool"),
            patch("nanobot.agent.loop.ReadFileTool"),
            patch("nanobot.agent.loop.WriteFileTool"),
            patch("nanobot.agent.loop.EditFileTool"),
            patch("nanobot.agent.loop.ListDirTool"),
            patch("nanobot.agent.loop.CronTool"),
            patch("nanobot.agent.loop.ContextTracker") as mock_tracker_cls,
        ):
            mock_tracker = MagicMock()
            mock_tracker_cls.return_value = mock_tracker
            mock_tracker.context_usage = {}
            mock_tracker.add_tokens = MagicMock()

            agent = AgentLoop(
                bus=mock_bus,
                provider=mock_provider,
                workspace=MagicMock(),
                model="gpt-4",
                config=None,
            )

            messages = [{"role": "user", "content": "test"}]
            tools = []
            model = "gpt-4"
            temperature = 0.7
            max_tokens = 4096

            with (
                patch(
                    "nanobot.providers.custom_provider.CustomProvider",
                    return_value=mock_fallback_tier2,
                ),
                patch(
                    "nanobot.providers.bedrock_provider.BedrockProvider",
                    return_value=mock_bedrock_fallback,
                ) as mock_bedrock_provider,
            ):
                result = await agent._chat_with_fallback(
                    messages, tools, model, temperature, max_tokens
                )

                assert result.content == "Hello from AWS Bedrock (tier 3)"
                assert result.finish_reason == "stop"
                mock_provider.chat.assert_called_once()
                mock_fallback_tier2.chat.assert_called_once()
                mock_bedrock_fallback.chat.assert_called_once()

                mock_bedrock_provider.assert_called_once()
                _, kwargs = mock_bedrock_provider.call_args
                assert kwargs["region_name"] == "us-east-1"
                assert kwargs["default_model"] == "us.anthropic.claude-sonnet-4-6"
