"""Unit tests for BedrockProvider using mocked boto3."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from nanobot.providers.bedrock_provider import BedrockProvider


class TestBedrockProvider:
    """Test BedrockProvider with mocked boto3 client."""

    @pytest.mark.asyncio
    async def test_get_default_model(self):
        """Test get_default_model returns the configured default model."""
        with patch("boto3.client"):
            provider = BedrockProvider(default_model="us.anthropic.claude-sonnet-4-6")
            assert provider.get_default_model() == "us.anthropic.claude-sonnet-4-6"

    @pytest.mark.asyncio
    async def test_get_models(self):
        """Test get_models returns a list containing expected models."""
        with patch("boto3.client"):
            provider = BedrockProvider(default_model="us.anthropic.claude-sonnet-4-6")
            models = await provider.get_models()
            assert "us.anthropic.claude-sonnet-4-6" in models

    @pytest.mark.asyncio
    async def test_chat_basic(self):
        """Test chat method with basic text response."""
        mock_response = {
            "output": {"message": {"role": "assistant", "content": [{"text": "Hello!"}]}},
            "usage": {"inputTokens": 10, "outputTokens": 5, "totalTokens": 15},
            "stopReason": "end_turn",
        }

        with patch("boto3.client") as mock_boto3:
            mock_client = MagicMock()
            mock_client.converse.return_value = mock_response
            mock_boto3.return_value = mock_client

            provider = BedrockProvider(default_model="us.anthropic.claude-sonnet-4-6")
            response = await provider.chat(
                messages=[{"role": "user", "content": "Hi"}],
                model="us.anthropic.claude-sonnet-4-6",
            )

            assert response.content == "Hello!"
            assert response.usage["total_tokens"] == 15

    @pytest.mark.asyncio
    async def test_chat_with_tool_call(self):
        """Test chat method with tool use response."""
        mock_response = {
            "output": {
                "message": {
                    "role": "assistant",
                    "content": [
                        {
                            "toolUse": {
                                "toolUseId": "t1",
                                "name": "get_weather",
                                "input": {"city": "Austin"},
                            }
                        }
                    ],
                }
            },
            "usage": {"inputTokens": 20, "outputTokens": 10, "totalTokens": 30},
            "stopReason": "tool_use",
        }

        with patch("boto3.client") as mock_boto3:
            mock_client = MagicMock()
            mock_client.converse.return_value = mock_response
            mock_boto3.return_value = mock_client

            provider = BedrockProvider(default_model="us.anthropic.claude-sonnet-4-6")
            response = await provider.chat(
                messages=[{"role": "user", "content": "What's the weather?"}],
                model="us.anthropic.claude-sonnet-4-6",
            )

            assert response.tool_calls[0].name == "get_weather"
            assert response.tool_calls[0].arguments == {"city": "Austin"}

    @pytest.mark.asyncio
    async def test_message_conversion_system(self):
        """Test that system messages are extracted correctly."""
        with patch("boto3.client"):
            provider = BedrockProvider(default_model="us.anthropic.claude-sonnet-4-6")

            messages = [
                {"role": "system", "content": "Be helpful"},
                {"role": "user", "content": "Hi"},
            ]

            bedrock_messages, system_prompts = provider._convert_messages(messages)

            assert len(bedrock_messages) == 1
            assert bedrock_messages[0]["role"] == "user"

            assert len(system_prompts) == 1
            assert system_prompts[0] == {"text": "Be helpful"}

    @pytest.mark.asyncio
    async def test_message_conversion_tool_result(self):
        """Test tool result message conversion."""
        with patch("boto3.client"):
            provider = BedrockProvider(default_model="us.anthropic.claude-sonnet-4-6")

            messages = [
                {"role": "tool", "tool_call_id": "t1", "content": "sunny"},
            ]

            bedrock_messages, system_prompts = provider._convert_messages(messages)

            assert len(bedrock_messages) == 1
            assert bedrock_messages[0]["role"] == "user"
            assert "toolResult" in bedrock_messages[0]["content"][0]
            assert bedrock_messages[0]["content"][0]["toolResult"]["toolUseId"] == "t1"
            assert system_prompts == []
