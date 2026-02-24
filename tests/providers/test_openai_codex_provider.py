"""Tests for OpenAICodexProvider."""

from unittest.mock import MagicMock, patch

import pytest

from nanobot.providers.openai_codex_provider import (
    DEFAULT_ORIGINATOR,
    OpenAICodexProvider,
    _build_headers,
    _convert_messages,
    _convert_tools,
    _convert_user_message,
    _friendly_error,
    _map_finish_reason,
    _prompt_cache_key,
    _split_tool_call_id,
    _strip_model_prefix,
)


class TestStripModelPrefix:
    """Tests for _strip_model_prefix function."""

    def test_with_openai_codex_prefix(self):
        """Test stripping openai-codex/ prefix."""
        result = _strip_model_prefix("openai-codex/gpt-5.1")
        assert result == "gpt-5.1"

    def test_with_openai_codex_underscore_prefix(self):
        """Test stripping openai_codex/ prefix."""
        result = _strip_model_prefix("openai_codex/gpt-5.1")
        assert result == "gpt-5.1"

    def test_without_prefix(self):
        """Test model name without prefix remains unchanged."""
        result = _strip_model_prefix("gpt-5.1")
        assert result == "gpt-5.1"


class TestBuildHeaders:
    """Tests for _build_headers function."""

    def test_returns_correct_keys_and_values(self):
        """Test headers dict contains all expected keys and values."""
        account_id = "test-account-123"
        token = "test-token-abc"

        headers = _build_headers(account_id, token)

        assert headers["Authorization"] == f"Bearer {token}"
        assert headers["chatgpt-account-id"] == account_id
        assert headers["OpenAI-Beta"] == "responses=experimental"
        assert headers["originator"] == DEFAULT_ORIGINATOR
        assert headers["User-Agent"] == "nanobot (python)"
        assert headers["accept"] == "text/event-stream"
        assert headers["content-type"] == "application/json"


class TestConvertTools:
    """Tests for _convert_tools function."""

    def test_standard_tool_conversion(self):
        """Test conversion of standard tool with name/description/parameters."""
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "search_web",
                    "description": "Search the web for information",
                    "parameters": {
                        "type": "object",
                        "properties": {"query": {"type": "string"}},
                    },
                },
            }
        ]

        result = _convert_tools(tools)

        assert len(result) == 1
        assert result[0]["type"] == "function"
        assert result[0]["name"] == "search_web"
        assert result[0]["description"] == "Search the web for information"
        assert result[0]["parameters"] == {
            "type": "object",
            "properties": {"query": {"type": "string"}},
        }

    def test_tool_with_missing_name_is_skipped(self):
        """Test that tools without name are skipped."""
        tools = [
            {
                "type": "function",
                "function": {
                    "description": "Tool without name",
                    "parameters": {"type": "object"},
                },
            }
        ]

        result = _convert_tools(tools)

        assert len(result) == 0

    def test_empty_list_returns_empty_list(self):
        """Test empty tools list returns empty list."""
        result = _convert_tools([])
        assert result == []

    def test_nested_function_format(self):
        """Test conversion when tool has nested function structure without type."""
        tools = [
            {
                "function": {
                    "name": "get_weather",
                    "description": "Get weather info",
                    "parameters": {"type": "object"},
                }
            }
        ]

        result = _convert_tools(tools)

        # The function expects tool.get("type") == "function" to use nested function
        # Without type="function", it uses the tool directly which doesn't have a name
        # So this returns empty - the function needs type="function" for nested format
        assert len(result) == 0


class TestConvertMessages:
    """Tests for _convert_messages function."""

    def test_system_message_extracts_to_system_prompt(self):
        """Test system message extracts content to system_prompt."""
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello"},
        ]

        system_prompt, input_items = _convert_messages(messages)

        assert system_prompt == "You are a helpful assistant."
        assert len(input_items) == 1
        assert input_items[0]["role"] == "user"

    def test_user_text_message_conversion(self):
        """Test user text message converts to input_items."""
        messages = [{"role": "user", "content": "Hello, world!"}]

        system_prompt, input_items = _convert_messages(messages)

        assert system_prompt == ""
        assert len(input_items) == 1
        assert input_items[0]["role"] == "user"
        assert input_items[0]["content"][0]["type"] == "input_text"
        assert input_items[0]["content"][0]["text"] == "Hello, world!"

    def test_assistant_text_message_conversion(self):
        """Test assistant message with text converts correctly."""
        messages = [{"role": "assistant", "content": "Hi there!"}]

        _, input_items = _convert_messages(messages)

        assert len(input_items) == 1
        assert input_items[0]["type"] == "message"
        assert input_items[0]["role"] == "assistant"
        assert input_items[0]["content"][0]["type"] == "output_text"
        assert input_items[0]["content"][0]["text"] == "Hi there!"
        assert input_items[0]["status"] == "completed"

    def test_assistant_message_with_tool_calls(self):
        """Test assistant message with tool_calls creates function_call items."""
        messages = [
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "call_123|fc_456",
                        "function": {
                            "name": "search_web",
                            "arguments": '{"query": "test"}',
                        },
                    }
                ],
            }
        ]

        _, input_items = _convert_messages(messages)

        assert len(input_items) == 1
        assert input_items[0]["type"] == "function_call"
        assert input_items[0]["name"] == "search_web"
        assert input_items[0]["arguments"] == '{"query": "test"}'

    def test_tool_result_message_conversion(self):
        """Test tool result message creates function_call_output item."""
        messages = [
            {
                "role": "tool",
                "tool_call_id": "call_123",
                "content": '{"result": "data"}',
            }
        ]

        _, input_items = _convert_messages(messages)

        assert len(input_items) == 1
        assert input_items[0]["type"] == "function_call_output"
        assert input_items[0]["output"] == '{"result": "data"}'


class TestConvertUserMessage:
    """Tests for _convert_user_message function."""

    def test_string_content_conversion(self):
        """Test string content converts to input_text format."""
        result = _convert_user_message("Hello")

        assert result["role"] == "user"
        assert result["content"][0]["type"] == "input_text"
        assert result["content"][0]["text"] == "Hello"

    def test_list_with_text_item_conversion(self):
        """Test list with text item converts correctly."""
        content = [{"type": "text", "text": "Hello"}]
        result = _convert_user_message(content)

        assert result["role"] == "user"
        assert result["content"][0]["type"] == "input_text"
        assert result["content"][0]["text"] == "Hello"

    def test_list_with_image_url_conversion(self):
        """Test list with image_url item converts to input_image."""
        content = [
            {
                "type": "image_url",
                "image_url": {"url": "https://example.com/image.jpg"},
            }
        ]
        result = _convert_user_message(content)

        assert result["role"] == "user"
        assert result["content"][0]["type"] == "input_image"
        assert result["content"][0]["image_url"] == "https://example.com/image.jpg"

    def test_empty_content_returns_empty_text(self):
        """Test empty/None content returns user message with empty text."""
        result = _convert_user_message(None)

        assert result["role"] == "user"
        assert result["content"][0]["type"] == "input_text"
        assert result["content"][0]["text"] == ""


class TestSplitToolCallId:
    """Tests for _split_tool_call_id function."""

    def test_split_with_pipe_separator(self):
        """Test splitting call_123|fc_456."""
        call_id, item_id = _split_tool_call_id("call_123|fc_456")

        assert call_id == "call_123"
        assert item_id == "fc_456"

    def test_split_without_pipe_separator(self):
        """Test splitting call_123 returns item_id as None."""
        call_id, item_id = _split_tool_call_id("call_123")

        assert call_id == "call_123"
        assert item_id is None

    def test_none_input_returns_default(self):
        """Test None input returns ('call_0', None)."""
        call_id, item_id = _split_tool_call_id(None)

        assert call_id == "call_0"
        assert item_id is None


class TestPromptCacheKey:
    """Tests for _prompt_cache_key function."""

    def test_same_messages_produce_same_key(self):
        """Test identical messages produce same SHA256 key."""
        messages = [{"role": "user", "content": "test"}]

        key1 = _prompt_cache_key(messages)
        key2 = _prompt_cache_key(messages)

        assert key1 == key2

    def test_different_messages_produce_different_keys(self):
        """Test different messages produce different SHA256 keys."""
        messages1 = [{"role": "user", "content": "test1"}]
        messages2 = [{"role": "user", "content": "test2"}]

        key1 = _prompt_cache_key(messages1)
        key2 = _prompt_cache_key(messages2)

        assert key1 != key2

    def test_returns_sha256_hex_digest(self):
        """Test returns 64-character hex string."""
        messages = [{"role": "user", "content": "test"}]

        key = _prompt_cache_key(messages)

        assert len(key) == 64
        assert all(c in "0123456789abcdef" for c in key)


class TestMapFinishReason:
    """Tests for _map_finish_reason function."""

    def test_completed_maps_to_stop(self):
        """Test 'completed' status maps to 'stop'."""
        assert _map_finish_reason("completed") == "stop"

    def test_incomplete_maps_to_length(self):
        """Test 'incomplete' status maps to 'length'."""
        assert _map_finish_reason("incomplete") == "length"

    def test_failed_maps_to_error(self):
        """Test 'failed' status maps to 'error'."""
        assert _map_finish_reason("failed") == "error"

    def test_none_maps_to_stop(self):
        """Test None status maps to 'stop'."""
        assert _map_finish_reason(None) == "stop"


class TestFriendlyError:
    """Tests for _friendly_error function."""

    def test_429_returns_quota_message(self):
        """Test 429 status returns quota exceeded message."""
        result = _friendly_error(429, "Rate limit exceeded")

        assert "ChatGPT usage quota exceeded" in result
        assert "rate limit triggered" in result

    def test_500_returns_http_message(self):
        """Test 500 status returns HTTP message."""
        result = _friendly_error(500, "Internal Server Error")

        assert result == "HTTP 500: Internal Server Error"


class TestOpenAICodexProviderChat:
    """Tests for OpenAICodexProvider.chat method."""

    @pytest.mark.asyncio
    async def test_chat_happy_path(self):
        """Test chat() happy path returns LLMResponse with content."""
        provider = OpenAICodexProvider()

        mock_token = MagicMock()
        mock_token.account_id = "test-account"
        mock_token.access = "test-token"

        mock_response = ("Hello, world!", [], "stop")

        with patch("nanobot.providers.openai_codex_provider.get_codex_token") as mock_get_token, patch(
            "nanobot.providers.openai_codex_provider._request_codex"
        ) as mock_request:
            mock_get_token.return_value = mock_token
            mock_request.return_value = mock_response

            response = await provider.chat([{"role": "user", "content": "Hi"}])

        assert response.content == "Hello, world!"
        assert response.finish_reason == "stop"
        assert response.tool_calls == []

        # Verify headers and body (passed as positional args: url, headers, body)
        call_args = mock_request.call_args.args
        assert call_args[1]["Authorization"] == "Bearer test-token"
        assert call_args[2]["model"] == "gpt-5.1-codex"
        assert call_args[2]["stream"] is True

    @pytest.mark.asyncio
    async def test_chat_with_custom_model(self):
        """Test chat() with custom model strips prefix."""
        provider = OpenAICodexProvider()

        mock_token = MagicMock()
        mock_token.account_id = "test-account"
        mock_token.access = "test-token"

        mock_response = ("Response", [], "stop")

        with patch("nanobot.providers.openai_codex_provider.get_codex_token") as mock_get_token, patch(
            "nanobot.providers.openai_codex_provider._request_codex"
        ) as mock_request:
            mock_get_token.return_value = mock_token
            mock_request.return_value = mock_response

            await provider.chat(
                [{"role": "user", "content": "Hi"}],
                model="openai-codex/gpt-4",
            )

        call_args = mock_request.call_args.args
        assert call_args[2]["model"] == "gpt-4"

    @pytest.mark.asyncio
    async def test_chat_with_tools(self):
        """Test chat() with tools passes converted tools to request."""
        provider = OpenAICodexProvider()

        mock_token = MagicMock()
        mock_token.account_id = "test-account"
        mock_token.access = "test-token"

        mock_response = ("Response", [], "stop")

        tools = [
            {
                "type": "function",
                "function": {
                    "name": "search_web",
                    "description": "Search web",
                    "parameters": {"type": "object"},
                },
            }
        ]

        with patch("nanobot.providers.openai_codex_provider.get_codex_token") as mock_get_token, patch(
            "nanobot.providers.openai_codex_provider._request_codex"
        ) as mock_request:
            mock_get_token.return_value = mock_token
            mock_request.return_value = mock_response

            await provider.chat([{"role": "user", "content": "Search"}], tools=tools)

        call_args = mock_request.call_args.args
        assert len(call_args[2]["tools"]) == 1
        assert call_args[2]["tools"][0]["name"] == "search_web"

    @pytest.mark.asyncio
    async def test_chat_exception_handling(self):
        """Test chat() exception returns LLMResponse with error."""
        provider = OpenAICodexProvider()

        mock_token = MagicMock()
        mock_token.account_id = "test-account"
        mock_token.access = "test-token"

        with patch("nanobot.providers.openai_codex_provider.get_codex_token") as mock_get_token, patch(
            "nanobot.providers.openai_codex_provider._request_codex"
        ) as mock_request:
            mock_get_token.return_value = mock_token
            mock_request.side_effect = Exception("API timeout")

            response = await provider.chat([{"role": "user", "content": "Test"}])

        assert "Error calling Codex:" in response.content
        assert response.finish_reason == "error"

    @pytest.mark.asyncio
    async def test_chat_ssl_retry_with_verify_false(self):
        """Test chat() retries with verify=False on SSL error."""
        provider = OpenAICodexProvider()

        mock_token = MagicMock()
        mock_token.account_id = "test-account"
        mock_token.access = "test-token"

        # First call raises SSL error, second succeeds
        with patch("nanobot.providers.openai_codex_provider.get_codex_token") as mock_get_token, patch(
            "nanobot.providers.openai_codex_provider._request_codex"
        ) as mock_request:
            mock_get_token.return_value = mock_token
            mock_request.side_effect = [
                Exception("CERTIFICATE_VERIFY_FAILED"),
                ("Response", [], "stop"),
            ]

            response = await provider.chat([{"role": "user", "content": "Test"}])

        assert response.content == "Response"
        assert mock_request.call_count == 2

    @pytest.mark.asyncio
    async def test_chat_with_tool_calls_in_response(self):
        """Test chat() with tool calls in response."""
        provider = OpenAICodexProvider()

        mock_token = MagicMock()
        mock_token.account_id = "test-account"
        mock_token.access = "test-token"

        mock_tool_call = MagicMock()
        mock_tool_call.id = "call_123|fc_456"
        mock_tool_call.name = "search_web"
        mock_tool_call.arguments = {"query": "test"}

        mock_response = ("Response", [mock_tool_call], "stop")

        with patch("nanobot.providers.openai_codex_provider.get_codex_token") as mock_get_token, patch(
            "nanobot.providers.openai_codex_provider._request_codex"
        ) as mock_request:
            mock_get_token.return_value = mock_token
            mock_request.return_value = mock_response

            response = await provider.chat([{"role": "user", "content": "Search"}])

        assert response.content == "Response"
        assert len(response.tool_calls) == 1
        assert response.tool_calls[0].name == "search_web"

    @pytest.mark.asyncio
    async def test_chat_uses_default_model_when_none_provided(self):
        """Test chat() uses provider default model when model is None."""
        provider = OpenAICodexProvider(default_model="openai-codex/gpt-5.1-codex")

        mock_token = MagicMock()
        mock_token.account_id = "test-account"
        mock_token.access = "test-token"

        mock_response = ("Response", [], "stop")

        with patch("nanobot.providers.openai_codex_provider.get_codex_token") as mock_get_token, patch(
            "nanobot.providers.openai_codex_provider._request_codex"
        ) as mock_request:
            mock_get_token.return_value = mock_token
            mock_request.return_value = mock_response

            await provider.chat([{"role": "user", "content": "Test"}])

        call_args = mock_request.call_args.args
        assert call_args[2]["model"] == "gpt-5.1-codex"


class TestOpenAICodexProviderGetDefaultModel:
    """Tests for OpenAICodexProvider.get_default_model method."""

    def test_get_default_model(self):
        """Test returns the default model string."""
        provider = OpenAICodexProvider(default_model="openai-codex/gpt-5.1-codex")
        result = provider.get_default_model()

        assert result == "openai-codex/gpt-5.1-codex"
