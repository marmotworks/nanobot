"""Unit tests for BedrockProvider using mocked boto3."""

from __future__ import annotations

from unittest.mock import MagicMock, patch
from urllib.error import HTTPError

import botocore.exceptions
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

    @pytest.mark.asyncio
    async def test_tool_call_args_as_string(self):
        """toolUse.input must always be a dict, even if arguments arrive as a JSON string."""
        with patch("boto3.client"):
            provider = BedrockProvider(default_model="us.anthropic.claude-sonnet-4-6")

            messages = [
                {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": "t1",
                            "type": "function",
                            "function": {
                                "name": "get_weather",
                                "arguments": '{"city": "Austin"}',  # string, not dict
                            },
                        }
                    ],
                }
            ]
            converted, _ = provider._convert_messages(messages)
            tool_use = converted[0]["content"][0]["toolUse"]
            assert isinstance(tool_use["input"], dict), "toolUse.input must be a dict"
            assert tool_use["input"] == {"city": "Austin"}

    @pytest.mark.asyncio
    async def test_tool_call_args_as_dict(self):
        """Test that tool call arguments as a dict still work correctly."""
        with patch("boto3.client"):
            provider = BedrockProvider(default_model="us.anthropic.claude-sonnet-4-6")

            messages = [
                {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": "t1",
                            "type": "function",
                            "function": {
                                "name": "get_weather",
                                "arguments": {"city": "Austin"},  # already a dict
                            },
                        }
                    ],
                }
            ]
            converted, _ = provider._convert_messages(messages)
            tool_use = converted[0]["content"][0]["toolUse"]
            assert isinstance(tool_use["input"], dict), "toolUse.input must be a dict"
            assert tool_use["input"] == {"city": "Austin"}

    @pytest.mark.asyncio
    async def test_sanitize_unpaired_tool_use_in_middle(self):
        """Test that unpaired toolUse in middle of history is stripped."""
        with patch("boto3.client"):
            provider = BedrockProvider(default_model="us.anthropic.claude-sonnet-4-6")

            # Build Bedrock-format messages:
            # 1. User message
            # 2. Assistant with toolUse (ID: "t1") - this will be stripped (no toolResult follows)
            # 3. User with plain text (NOT a toolResult) - this is the unpaired case
            # 4. Assistant with plain text - this should be preserved
            messages = [
                {"role": "user", "content": [{"text": "Hello"}]},
                {
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
                },
                {"role": "user", "content": [{"text": "Another user message"}]},
                {"role": "assistant", "content": [{"text": "Final response"}]},
            ]

            sanitized = provider._sanitize_bedrock_messages(messages)

            # Unpaired assistant+toolUse message should be stripped
            # Clean user→assistant exchange at the end should be preserved
            assert len(sanitized) == 3
            assert sanitized[0]["role"] == "user"
            assert sanitized[0]["content"][0]["text"] == "Hello"
            assert sanitized[1]["role"] == "user"
            assert sanitized[1]["content"][0]["text"] == "Another user message"
            assert sanitized[2]["role"] == "assistant"
            assert sanitized[2]["content"][0]["text"] == "Final response"

            # No toolUse blocks should remain in output
            for msg in sanitized:
                for block in msg.get("content", []):
                    assert "toolUse" not in block

    @pytest.mark.asyncio
    async def test_sanitize_multi_tool_call_valid_pair(self):
        """Multiple tool calls in one assistant message with results split across multiple user messages must NOT be stripped."""
        with patch("boto3.client"):
            provider = BedrockProvider(default_model="us.anthropic.claude-sonnet-4-6")

            messages = [
                {
                    "role": "assistant",
                    "content": [
                        {"toolUse": {"toolUseId": "t1", "name": "f1", "input": {}}},
                        {"toolUse": {"toolUseId": "t2", "name": "f2", "input": {}}},
                    ],
                },
                {
                    "role": "user",
                    "content": [{"toolResult": {"toolUseId": "t1", "content": [{"text": "r1"}]}}],
                },
                {
                    "role": "user",
                    "content": [{"toolResult": {"toolUseId": "t2", "content": [{"text": "r2"}]}}],
                },
                {"role": "assistant", "content": [{"text": "done"}]},
            ]
            result = provider._sanitize_bedrock_messages(messages)
            assert len(result) == 4, f"Expected 4 messages (valid pair), got {len(result)}: {result}"
            assert result[0]["content"][0]["toolUse"]["toolUseId"] == "t1"

    @pytest.mark.asyncio
    async def test_strip_unpaired_tool_calls(self):
        """Test that OpenAI-style unpaired toolUse/toolResult is stripped after conversion."""
        with patch("boto3.client"):
            provider = BedrockProvider(default_model="us.anthropic.claude-sonnet-4-6")

            # OpenAI-style messages with unpaired toolUse (assistant message with tool_calls
            # but no corresponding tool result follows)
            messages = [
                {"role": "user", "content": "What's the weather?"},
                {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": "t1",
                            "type": "function",
                            "function": {"name": "get_weather", "arguments": {"city": "Austin"}},
                        }
                    ],
                },
                {"role": "user", "content": "Never mind, I changed my mind."},
            ]

            converted, _ = provider._convert_messages(messages)

            # The assistant message with toolUse should be stripped because there's no toolResult
            # Only the two user messages should remain
            assert len(converted) == 2
            assert converted[0]["role"] == "user"
            assert converted[0]["content"][0]["text"] == "What's the weather?"
            assert converted[1]["role"] == "user"
            assert converted[1]["content"][0]["text"] == "Never mind, I changed my mind."

            # Verify no toolUse blocks remain
            for msg in converted:
                for block in msg.get("content", []):
                    assert "toolUse" not in block

    @pytest.mark.asyncio
    async def test_tier3_fallback_retry(self):
        """Test tier-3 fallback retry behavior with retryable errors."""

        # Retryable exceptions for Bedrock Converse API
        retryable_exceptions = [
            ("ThrottlingException", "Rate limit exceeded"),
            ("ModelStreamErrorException", "Stream error"),
        ]

        # Mock response for successful fallback
        mock_success_response = {
            "output": {"message": {"role": "assistant", "content": [{"text": "Fallback success!"}]}},
            "usage": {"inputTokens": 5, "outputTokens": 10, "totalTokens": 15},
            "stopReason": "end_turn",
        }

        for exception_name, error_msg in retryable_exceptions:
            with patch("boto3.client") as mock_boto3:
                mock_client = MagicMock()

                # First call raises retryable exception, second call succeeds
                mock_client.converse.side_effect = [
                    self._mock_bedrock_exception(exception_name, error_msg),
                    mock_success_response,
                ]
                mock_boto3.return_value = mock_client

                # Provider with fallback models
                provider = BedrockProvider(
                    region_name="us-east-1",
                    default_model="us.anthropic.claude-sonnet-4-6",
                )
                # Override fallback_models for testing
                provider.fallback_models = [
                    "us.anthropic.claude-sonnet-4-6",
                    "us.anthropic.claude-opus-4-6-v1",
                ]

                response = await provider.chat(
                    messages=[{"role": "user", "content": "Hi"}],
                    model="us.anthropic.claude-sonnet-4-6",
                )

                # Verify fallback worked
                assert response.content == "Fallback success!"
                assert mock_client.converse.call_count == 2

    @pytest.mark.asyncio
    async def test_tier3_fallback_all_models_fail(self):
        """Test that when all fallback models fail, the appropriate exception is raised."""

        with patch("boto3.client") as mock_boto3:
            mock_client = MagicMock()

            # All calls raise retryable exceptions
            mock_client.converse.side_effect = [
                self._mock_bedrock_exception("ThrottlingException", "Rate limit"),
                self._mock_bedrock_exception("ModelStreamErrorException", "Stream error"),
            ]
            mock_boto3.return_value = mock_client

            provider = BedrockProvider(
                region_name="us-east-1",
                default_model="us.anthropic.claude-sonnet-4-6",
            )
            provider.fallback_models = [
                "us.anthropic.claude-sonnet-4-6",
                "us.anthropic.claude-opus-4-6-v1",
            ]

            with pytest.raises(Exception) as exc_info:
                await provider.chat(
                    messages=[{"role": "user", "content": "Hi"}],
                    model="us.anthropic.claude-sonnet-4-6",
                )

            # Both models should have been tried
            assert mock_client.converse.call_count == 2
            # Verify the last exception is ModelStreamErrorException (check error code)
            assert isinstance(exc_info.value, botocore.exceptions.ClientError)
            assert exc_info.value.response["Error"]["Code"] == "ModelStreamErrorException"

    @pytest.mark.asyncio
    async def test_tier3_fallback_non_retryable_error(self):
        """Test that non-retryable errors fail immediately without retry."""

        with patch("boto3.client") as mock_boto3:
            mock_client = MagicMock()

            # Non-retryable exception (InvalidRequestException)
            mock_client.converse.side_effect = self._mock_bedrock_exception(
                "InvalidRequestException", "Invalid model ID"
            )
            mock_boto3.return_value = mock_client

            provider = BedrockProvider(
                region_name="us-east-1",
                default_model="us.anthropic.claude-sonnet-4-6",
            )
            provider.fallback_models = [
                "us.anthropic.claude-sonnet-4-6",
                "us.anthropic.claude-opus-4-6-v1",
            ]

            with pytest.raises(Exception) as exc_info:
                await provider.chat(
                    messages=[{"role": "user", "content": "Hi"}],
                    model="us.anthropic.claude-sonnet-4-6",
                )

            # Should fail immediately without retrying
            assert mock_client.converse.call_count == 1
            # Verify the exception is InvalidRequestException (check error code)
            assert isinstance(exc_info.value, botocore.exceptions.ClientError)
            assert exc_info.value.response["Error"]["Code"] == "InvalidRequestException"

    @staticmethod
    def _mock_bedrock_exception(exception_name: str, message: str) -> botocore.exceptions.ClientError:
        """Create a mock Bedrock exception."""

        error_response = {
            "Error": {
                "Code": exception_name,
                "Message": message,
            }
        }
        exception = botocore.exceptions.ClientError(error_response, exception_name)
        return exception
