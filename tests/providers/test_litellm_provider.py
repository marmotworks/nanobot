"""Tests for LiteLLMProvider."""

from unittest.mock import MagicMock, patch

import pytest

from nanobot.providers.litellm_provider import LiteLLMProvider


def make_mock_response(content="Hello!", tool_calls=None):
    """Create a mock LiteLLM response."""
    # Create message object with proper attributes
    message = MagicMock()
    message.content = content
    message.tool_calls = tool_calls
    message.reasoning_content = None

    choice = MagicMock()
    choice.finish_reason = "stop"
    choice.message = message

    response = MagicMock()
    response.choices = [choice]

    # Create usage object with proper attributes
    usage = MagicMock()
    usage.prompt_tokens = 10
    usage.completion_tokens = 20
    usage.total_tokens = 30
    response.usage = usage

    return response


class TestLiteLLMProviderChat:
    """Tests for the chat method."""

    @pytest.mark.asyncio
    async def test_chat_happy_path(self):
        """Test chat() happy path with mocked litellm.acompletion."""
        provider = LiteLLMProvider(api_key="test-key")
        mock_response = make_mock_response(content="Hello, world!")

        with patch("nanobot.providers.litellm_provider.acompletion") as mock_acompletion:
            mock_acompletion.return_value = mock_response
            response = await provider.chat([{"role": "user", "content": "Hi"}])

        assert response.content == "Hello, world!"
        assert response.finish_reason == "stop"

    @pytest.mark.asyncio
    async def test_chat_with_tool_calls(self):
        """Test chat() with tool calls in response."""
        provider = LiteLLMProvider(api_key="test-key")

        # Create mock tool call
        mock_tool_call = MagicMock()
        mock_tool_call.id = "tool-call-1"
        mock_tool_call.function.name = "search_web"
        mock_tool_call.function.arguments = '{"query": "test"}'

        mock_response = make_mock_response(content=None, tool_calls=[mock_tool_call])

        with patch("nanobot.providers.litellm_provider.acompletion") as mock_acompletion:
            mock_acompletion.return_value = mock_response
            response = await provider.chat([{"role": "user", "content": "Search for test"}])

        assert response.content is None
        assert len(response.tool_calls) == 1
        assert response.tool_calls[0].id == "tool-call-1"
        assert response.tool_calls[0].name == "search_web"
        assert response.tool_calls[0].arguments == {"query": "test"}

    @pytest.mark.asyncio
    async def test_chat_error_handling(self):
        """Test chat() error handling when acompletion raises exception."""
        provider = LiteLLMProvider(api_key="test-key")

        with patch("nanobot.providers.litellm_provider.acompletion") as mock_acompletion:
            mock_acompletion.side_effect = Exception("API timeout")
            response = await provider.chat([{"role": "user", "content": "Test"}])

        assert response.content.startswith("Error calling LLM:")
        assert response.finish_reason == "error"


class TestLiteLLMProviderResolveModel:
    """Tests for _resolve_model method."""

    def test_resolve_model_gateway_mode(self):
        """Test _resolve_model with gateway mode - model gets prefixed."""
        provider = LiteLLMProvider(
            api_key="test-key",
            api_base="https://openrouter.ai/api/v1",
            provider_name="openrouter",
        )
        # Gateway mode should prefix the model
        result = provider._resolve_model("claude-3-5-sonnet")
        assert result == "openrouter/claude-3-5-sonnet"

    def test_resolve_model_standard_mode(self):
        """Test _resolve_model in standard mode - model passthrough."""
        provider = LiteLLMProvider(api_key="test-key")
        # In standard mode with no gateway, model should be passed through as-is
        # for providers that don't need prefixing (like Anthropic)
        result = provider._resolve_model("claude-3-5-sonnet")
        assert result == "claude-3-5-sonnet"


class TestLiteLLMProviderSanitizeMessages:
    """Tests for _sanitize_messages static method."""

    def test_sanitize_messages_strips_non_standard_keys(self):
        """Test that non-standard keys are stripped."""
        messages = [
            {"role": "user", "content": "Hello", "extra_key": "should be removed"},
        ]
        result = LiteLLMProvider._sanitize_messages(messages)
        assert result[0] == {"role": "user", "content": "Hello"}

    def test_sanitize_messages_assistant_content_none(self):
        """Test that assistant messages get content=None added."""
        messages = [
            {"role": "assistant", "tool_calls": [{"id": "tc1", "function": {"name": "test"}}]},
        ]
        result = LiteLLMProvider._sanitize_messages(messages)
        assert result[0]["content"] is None

    def test_sanitize_messages_preserves_standard_keys(self):
        """Test that standard keys are preserved."""
        messages = [
            {
                "role": "user",
                "content": "Hello",
                "tool_calls": [],
                "tool_call_id": "tc1",
                "name": "test",
            },
        ]
        result = LiteLLMProvider._sanitize_messages(messages)
        assert result[0] == {
            "role": "user",
            "content": "Hello",
            "tool_calls": [],
            "tool_call_id": "tc1",
            "name": "test",
        }


class TestLiteLLMProviderParseResponse:
    """Tests for _parse_response method."""

    def test_parse_response_usage_tracking(self):
        """Test that usage stats are extracted from response."""
        provider = LiteLLMProvider(api_key="test-key")

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Hello"
        mock_response.choices[0].message.tool_calls = None
        mock_response.choices[0].finish_reason = "stop"
        mock_response.usage.prompt_tokens = 10
        mock_response.usage.completion_tokens = 20
        mock_response.usage.total_tokens = 30

        result = provider._parse_response(mock_response)

        assert result.usage == {
            "prompt_tokens": 10,
            "completion_tokens": 20,
            "total_tokens": 30,
        }


class TestLiteLLMProviderSupportsCacheControl:
    """Tests for _supports_cache_control method."""

    def test_supports_cache_control_no_gateway_no_spec(self):
        """Test returns False when no gateway and no spec."""
        provider = LiteLLMProvider(api_key="test-key")
        result = provider._supports_cache_control("unknown-model")
        assert result is False


class TestLiteLLMProviderDefaultModel:
    """Tests for get_default_model method."""

    def test_get_default_model(self):
        """Test returns the default model string."""
        provider = LiteLLMProvider(api_key="test-key")
        result = provider.get_default_model()
        assert result == "anthropic/claude-opus-4-5"


class TestLiteLLMProviderMaxTokens:
    """Tests for max_tokens clamping in chat method."""

    @pytest.mark.asyncio
    async def test_max_tokens_clamping(self):
        """Test that max_tokens=-1 is clamped to 1."""
        provider = LiteLLMProvider(api_key="test-key")
        mock_response = make_mock_response(content="Hello!")

        with patch("nanobot.providers.litellm_provider.acompletion") as mock_acompletion:
            mock_acompletion.return_value = mock_response
            await provider.chat([{"role": "user", "content": "Test"}], max_tokens=-1)

            # Verify that max_tokens=1 was passed to acompletion
            call_kwargs = mock_acompletion.call_args.kwargs
            assert call_kwargs["max_tokens"] == 1
