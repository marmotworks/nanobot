"""Tests for CustomProvider."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from nanobot.providers.custom_provider import CustomProvider


def make_mock_openai_response(content="Hello!", tool_calls=None, finish_reason="stop", usage=None, reasoning_content=None):
    """Create a mock OpenAI response object."""
    message = MagicMock()
    message.content = content
    message.tool_calls = tool_calls
    message.reasoning_content = reasoning_content

    choice = MagicMock()
    choice.message = message
    choice.finish_reason = finish_reason

    response = MagicMock()
    response.choices = [choice]

    if usage:
        response.usage = usage
    else:
        usage_obj = MagicMock()
        usage_obj.prompt_tokens = 10
        usage_obj.completion_tokens = 5
        usage_obj.total_tokens = 15
        response.usage = usage_obj

    return response


def make_mock_tool_call(id="tc-1", name="search_web", arguments='{"query": "test"}'):
    """Create a mock tool call object."""
    tool_call = MagicMock()
    tool_call.id = id
    tool_call.function.name = name
    tool_call.function.arguments = arguments
    return tool_call


def make_mock_model(id="test-model", context_length=None):
    """Create a mock model object."""
    model = MagicMock()
    model.id = id
    if context_length is not None:
        model.context_length = context_length
    return model


class TestCustomProviderInit:
    """Tests for __init__ method."""

    def test_defaults(self):
        """Test default initialization."""
        with patch("nanobot.providers.custom_provider.AsyncOpenAI") as mock_async_openai:
            mock_client = MagicMock()
            mock_async_openai.return_value = mock_client

            provider = CustomProvider()

            assert provider.default_model == "default"
            assert provider.api_key == "no-key"
            assert provider.api_base == "http://localhost:8000/v1"
            mock_async_openai.assert_called_once_with(api_key="no-key", base_url="http://localhost:8000/v1")

    def test_custom_parameters(self):
        """Test initialization with custom parameters."""
        with patch("nanobot.providers.custom_provider.AsyncOpenAI") as mock_async_openai:
            mock_client = MagicMock()
            mock_async_openai.return_value = mock_client

            provider = CustomProvider(
                api_key="test-key",
                api_base="http://localhost:1234/v1",
                default_model="my-model"
            )

            assert provider.default_model == "my-model"
            assert provider.api_key == "test-key"
            assert provider.api_base == "http://localhost:1234/v1"
            mock_async_openai.assert_called_once_with(api_key="test-key", base_url="http://localhost:1234/v1")


class TestCustomProviderChat:
    """Tests for chat method."""

    @pytest.fixture
    def provider(self):
        with patch("nanobot.providers.custom_provider.AsyncOpenAI") as mock_async_openai:
            mock_client = MagicMock()
            mock_async_openai.return_value = mock_client
            return CustomProvider(api_key="test", api_base="http://localhost:1234/v1", default_model="my-model")

    @pytest.mark.asyncio
    async def test_chat_happy_path(self, provider):
        """Test chat() happy path with basic response."""
        mock_response = make_mock_openai_response(content="Hello!")
        provider._client.chat.completions.create = AsyncMock(return_value=mock_response)

        result = await provider.chat([{"role": "user", "content": "hi"}])

        assert result.content == "Hello!"
        assert result.finish_reason == "stop"
        assert result.usage == {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}

    @pytest.mark.asyncio
    async def test_chat_with_custom_model(self, provider):
        """Test chat() with custom model parameter."""
        mock_response = make_mock_openai_response(content="Response")
        provider._client.chat.completions.create = AsyncMock(return_value=mock_response)

        await provider.chat([{"role": "user", "content": "hi"}], model="custom-model")

        call_kwargs = provider._client.chat.completions.create.call_args.kwargs
        assert call_kwargs["model"] == "custom-model"

    @pytest.mark.asyncio
    async def test_chat_uses_default_model_when_none_provided(self, provider):
        """Test chat() uses provider default model when model is None."""
        mock_response = make_mock_openai_response(content="Response")
        provider._client.chat.completions.create = AsyncMock(return_value=mock_response)

        await provider.chat([{"role": "user", "content": "hi"}])

        call_kwargs = provider._client.chat.completions.create.call_args.kwargs
        assert call_kwargs["model"] == "my-model"

    @pytest.mark.asyncio
    async def test_chat_with_tools(self, provider):
        """Test chat() with tools parameter."""
        mock_response = make_mock_openai_response(content="Response")
        provider._client.chat.completions.create = AsyncMock(return_value=mock_response)

        tools = [{"type": "function", "function": {"name": "test_tool"}}]
        await provider.chat([{"role": "user", "content": "hi"}], tools=tools)

        call_kwargs = provider._client.chat.completions.create.call_args.kwargs
        assert call_kwargs["tools"] == tools
        assert call_kwargs["tool_choice"] == "auto"

    @pytest.mark.asyncio
    async def test_chat_with_max_tokens(self, provider):
        """Test chat() max_tokens parameter."""
        mock_response = make_mock_openai_response(content="Response")
        provider._client.chat.completions.create = AsyncMock(return_value=mock_response)

        await provider.chat([{"role": "user", "content": "hi"}], max_tokens=100)

        call_kwargs = provider._client.chat.completions.create.call_args.kwargs
        assert call_kwargs["max_tokens"] == 100

    @pytest.mark.asyncio
    async def test_chat_with_temperature(self, provider):
        """Test chat() temperature parameter."""
        mock_response = make_mock_openai_response(content="Response")
        provider._client.chat.completions.create = AsyncMock(return_value=mock_response)

        await provider.chat([{"role": "user", "content": "hi"}], temperature=0.5)

        call_kwargs = provider._client.chat.completions.create.call_args.kwargs
        assert call_kwargs["temperature"] == 0.5

    @pytest.mark.asyncio
    async def test_chat_clamps_max_tokens_to_min(self, provider):
        """Test chat() clamps max_tokens=-1 to 1."""
        mock_response = make_mock_openai_response(content="Response")
        provider._client.chat.completions.create = AsyncMock(return_value=mock_response)

        await provider.chat([{"role": "user", "content": "hi"}], max_tokens=-1)

        call_kwargs = provider._client.chat.completions.create.call_args.kwargs
        assert call_kwargs["max_tokens"] == 1

    @pytest.mark.asyncio
    async def test_chat_with_tool_calls(self, provider):
        """Test chat() with tool calls in response."""
        mock_tool_call = make_mock_tool_call()
        mock_response = make_mock_openai_response(content=None, tool_calls=[mock_tool_call])
        provider._client.chat.completions.create = AsyncMock(return_value=mock_response)

        result = await provider.chat([{"role": "user", "content": "hi"}])

        assert result.content is None
        assert len(result.tool_calls) == 1
        assert result.tool_calls[0].id == "tc-1"
        assert result.tool_calls[0].name == "search_web"
        assert result.tool_calls[0].arguments == {"query": "test"}

    @pytest.mark.asyncio
    async def test_chat_with_reasoning_content(self, provider):
        """Test chat() with reasoning content in response."""
        mock_response = make_mock_openai_response(content="Response", reasoning_content="Reasoning here")
        provider._client.chat.completions.create = AsyncMock(return_value=mock_response)

        result = await provider.chat([{"role": "user", "content": "hi"}])

        assert result.reasoning_content == "Reasoning here"

    @pytest.mark.asyncio
    async def test_chat_with_usage_custom(self, provider):
        """Test chat() with custom usage values."""
        usage = MagicMock()
        usage.prompt_tokens = 100
        usage.completion_tokens = 50
        usage.total_tokens = 150
        mock_response = make_mock_openai_response(content="Response", usage=usage)
        provider._client.chat.completions.create = AsyncMock(return_value=mock_response)

        result = await provider.chat([{"role": "user", "content": "hi"}])

        assert result.usage == {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150}

    @pytest.mark.asyncio
    async def test_chat_error_handling(self, provider):
        """Test chat() exception returns LLMResponse with error."""
        provider._client.chat.completions.create = AsyncMock(side_effect=Exception("API timeout"))

        result = await provider.chat([{"role": "user", "content": "hi"}])

        assert result.content == "Error"
        assert result.finish_reason == "error"
        assert result.tool_calls == []
        assert result.usage == {}

    @pytest.mark.asyncio
    async def test_chat_http_error_handling(self, provider):
        """Test chat() HTTP error returns LLMResponse with error."""
        provider._client.chat.completions.create = AsyncMock(side_effect=ConnectionError("Network error"))

        result = await provider.chat([{"role": "user", "content": "hi"}])

        assert result.content == "Error"
        assert result.finish_reason == "error"


class TestCustomProviderParse:
    """Tests for _parse method."""

    @pytest.fixture
    def provider(self):
        with patch("nanobot.providers.custom_provider.AsyncOpenAI"):
            return CustomProvider()

    def test_parse_basic_response(self, provider):
        """Test _parse with basic response."""
        mock_response = make_mock_openai_response(content="Hello!")
        result = provider._parse(mock_response)

        assert result.content == "Hello!"
        assert result.finish_reason == "stop"
        assert result.usage == {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}

    def test_parse_with_tool_calls(self, provider):
        """Test _parse with tool calls."""
        mock_tool_call = make_mock_tool_call()
        mock_response = make_mock_openai_response(content=None, tool_calls=[mock_tool_call])
        result = provider._parse(mock_response)

        assert len(result.tool_calls) == 1
        assert result.tool_calls[0].id == "tc-1"
        assert result.tool_calls[0].name == "search_web"

    def test_parse_with_json_arguments(self, provider):
        """Test _parse with JSON string arguments."""
        mock_tool_call = make_mock_tool_call(arguments='{"key": "value"}')
        mock_response = make_mock_openai_response(content=None, tool_calls=[mock_tool_call])
        result = provider._parse(mock_response)

        assert result.tool_calls[0].arguments == {"key": "value"}

    def test_parse_with_none_arguments(self, provider):
        """Test _parse with None arguments."""
        mock_tool_call = make_mock_tool_call(arguments=None)
        mock_response = make_mock_openai_response(content=None, tool_calls=[mock_tool_call])
        result = provider._parse(mock_response)

        assert result.tool_calls[0].arguments is None

    def test_parse_with_finish_reason_none(self, provider):
        """Test _parse with None finish_reason defaults to 'stop'."""
        message = MagicMock()
        message.content = "Hello"
        message.tool_calls = None
        message.reasoning_content = None

        choice = MagicMock()
        choice.message = message
        choice.finish_reason = None

        response = MagicMock()
        response.choices = [choice]

        usage = MagicMock()
        usage.prompt_tokens = 10
        usage.completion_tokens = 5
        usage.total_tokens = 15
        response.usage = usage

        result = provider._parse(response)

        assert result.finish_reason == "stop"

    def test_parse_with_reasoning_content(self, provider):
        """Test _parse with reasoning content."""
        mock_response = make_mock_openai_response(content="Response", reasoning_content="Thinking...")
        result = provider._parse(mock_response)

        assert result.reasoning_content == "Thinking..."

    def test_parse_with_usage_none(self, provider):
        """Test _parse with None usage."""
        message = MagicMock()
        message.content = "Hello"
        message.tool_calls = None
        message.reasoning_content = None

        choice = MagicMock()
        choice.message = message
        choice.finish_reason = "stop"

        response = MagicMock()
        response.choices = [choice]
        response.usage = None

        result = provider._parse(response)

        assert result.usage == {}


class TestCustomProviderGetDefaultModel:
    """Tests for get_default_model method."""

    def test_get_default_model(self):
        """Test returns the default model string."""
        provider = CustomProvider(default_model="my-model")
        result = provider.get_default_model()

        assert result == "my-model"


class TestCustomProviderQueryLmStudioV0Api:
    """Tests for _query_lm_studio_v0_api method."""

    @pytest.fixture
    def provider(self):
        with patch("nanobot.providers.custom_provider.AsyncOpenAI"):
            return CustomProvider(api_key="test-key", api_base="http://localhost:1234/v1")

    @pytest.mark.asyncio
    async def test_query_lm_studio_v0_api_happy_path(self, provider):
        """Test _query_lm_studio_v0_api with successful response."""
        mock_data = {
            "data": [
                {
                    "id": "model-1",
                    "object": "model",
                    "type": "chat",
                    "publisher": "test-publisher",
                    "arch": "transformer",
                    "state": "loaded",
                    "max_context_length": 4096,
                    "loaded_context_length": 4096,
                    "capabilities": ["chat", "tools"],
                    "loaded": True
                }
            ]
        }

        mock_response = MagicMock()
        mock_response.json.return_value = mock_data
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        with patch("nanobot.providers.custom_provider.httpx.AsyncClient") as mock_async_client:
            mock_async_client.return_value.__aenter__.return_value = mock_client

            result = await provider._query_lm_studio_v0_api()

            assert len(result) == 1
            assert result[0]["id"] == "model-1"
            assert result[0]["type"] == "chat"
            assert result[0]["max_context_length"] == 4096

    @pytest.mark.asyncio
    async def test_query_lm_studio_v0_api_empty_data(self, provider):
        """Test _query_lm_studio_v0_api with empty data."""
        mock_data = {"data": []}

        mock_response = MagicMock()
        mock_response.json.return_value = mock_data
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        with patch("nanobot.providers.custom_provider.httpx.AsyncClient") as mock_async_client:
            mock_async_client.return_value.__aenter__.return_value = mock_client

            result = await provider._query_lm_studio_v0_api()

            assert result == []

    @pytest.mark.asyncio
    async def test_query_lm_studio_v0_api_missing_data_key(self, provider):
        """Test _query_lm_studio_v0_api with missing data key."""
        mock_data = {}

        mock_response = MagicMock()
        mock_response.json.return_value = mock_data
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        with patch("nanobot.providers.custom_provider.httpx.AsyncClient") as mock_async_client:
            mock_async_client.return_value.__aenter__.return_value = mock_client

            result = await provider._query_lm_studio_v0_api()

            assert result == []

    @pytest.mark.asyncio
    async def test_query_lm_studio_v0_api_http_error(self, provider):
        """Test _query_lm_studio_v0_api with HTTP error."""
        mock_client = MagicMock()
        mock_client.get = AsyncMock(side_effect=Exception("HTTP Error 404"))

        with patch("nanobot.providers.custom_provider.httpx.AsyncClient") as mock_async_client:
            mock_async_client.return_value.__aenter__.return_value = mock_client

            result = await provider._query_lm_studio_v0_api()

            assert result == []

    @pytest.mark.asyncio
    async def test_query_lm_studio_v0_api_url_construction(self, provider):
        """Test _query_lm_studio_v0_api constructs correct v0 API URL."""
        mock_data = {"data": []}
        mock_response = MagicMock()
        mock_response.json.return_value = mock_data
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        with patch("nanobot.providers.custom_provider.httpx.AsyncClient") as mock_async_client:
            mock_async_client.return_value.__aenter__.return_value = mock_client

            await provider._query_lm_studio_v0_api()

            # Verify URL is constructed from scheme + host only (v0 API at root)
            call_args = mock_client.get.call_args
            assert call_args[0][0] == "http://localhost:1234/api/v0/models"

    @pytest.mark.asyncio
    async def test_query_lm_studio_v0_api_url_with_trailing_slash(self, provider):
        """Test _query_lm_studio_v0_api handles trailing slash in api_base."""
        mock_data = {"data": []}
        mock_response = MagicMock()
        mock_response.json.return_value = mock_data
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        provider_with_slash = CustomProvider(api_key="test-key", api_base="http://localhost:1234/v1/")
        with patch("nanobot.providers.custom_provider.httpx.AsyncClient") as mock_async_client:
            mock_async_client.return_value.__aenter__.return_value = mock_client

            await provider_with_slash._query_lm_studio_v0_api()

            # Verify trailing slash is stripped
            call_args = mock_client.get.call_args
            assert call_args[0][0] == "http://localhost:1234/api/v0/models"

    @pytest.mark.asyncio
    async def test_query_lm_studio_v0_api_with_headers(self, provider):
        """Test _query_lm_studio_v0_api includes Authorization header."""
        mock_data = {"data": []}
        mock_response = MagicMock()
        mock_response.json.return_value = mock_data
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        with patch("nanobot.providers.custom_provider.httpx.AsyncClient") as mock_async_client:
            mock_async_client.return_value.__aenter__.return_value = mock_client

            await provider._query_lm_studio_v0_api()

            # Verify Authorization header is included
            call_kwargs = mock_client.get.call_args.kwargs
            assert call_kwargs["headers"]["Authorization"] == "Bearer test-key"


class TestCustomProviderGetModels:
    """Tests for get_models method."""

    @pytest.fixture
    def provider(self):
        with patch("nanobot.providers.custom_provider.AsyncOpenAI") as mock_async_openai:
            mock_client = MagicMock()
            mock_async_openai.return_value = mock_client
            return CustomProvider(api_key="test-key", api_base="http://localhost:1234/v1", default_model="default-model")

    @pytest.mark.asyncio
    async def test_get_models_returns_lm_studio_v0_models(self, provider):
        """Test get_models returns LM Studio v0 models when available."""
        v0_models = [
            {"id": "model-1", "max_context_length": 4096}
        ]
        provider._query_lm_studio_v0_api = AsyncMock(return_value=v0_models)

        result = await provider.get_models()

        assert result == v0_models
        provider._query_lm_studio_v0_api.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_get_models_fallback_to_openai_models(self, provider):
        """Test get_models falls back to OpenAI API when v0 API returns empty."""
        provider._query_lm_studio_v0_api = AsyncMock(return_value=[])

        mock_model = make_mock_model(id="gpt-4", context_length=8192)
        mock_models_response = MagicMock()
        mock_models_response.data = [mock_model]

        provider._client.models.list = AsyncMock(return_value=mock_models_response)

        result = await provider.get_models()

        assert len(result) == 1
        assert result[0]["id"] == "gpt-4"
        assert result[0]["context_length"] == 8192
        provider._query_lm_studio_v0_api.assert_awaited_once()
        provider._client.models.list.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_get_models_fallback_to_default_model(self, provider):
        """Test get_models falls back to default model when both APIs fail."""
        provider._query_lm_studio_v0_api = AsyncMock(return_value=[])
        provider._client.models.list = AsyncMock(side_effect=Exception("API Error"))

        result = await provider.get_models()

        assert len(result) == 1
        assert result[0]["id"] == "default-model"
        assert result[0]["context_length"] is None

    @pytest.mark.asyncio
    async def test_get_models_no_context_length_when_none(self, provider):
        """Test get_models handles models without context_length attribute."""
        provider._query_lm_studio_v0_api = AsyncMock(return_value=[])

        mock_model = MagicMock()
        mock_model.id = "gpt-3.5"
        # Don't set context_length to simulate missing attribute
        del mock_model.context_length  # Remove if it exists from MagicMock default

        mock_models_response = MagicMock()
        mock_models_response.data = [mock_model]

        provider._client.models.list = AsyncMock(return_value=mock_models_response)

        result = await provider.get_models()

        assert result[0]["context_length"] is None

    @pytest.mark.asyncio
    async def test_get_models_multiple_models(self, provider):
        """Test get_models with multiple models from OpenAI API."""
        provider._query_lm_studio_v0_api = AsyncMock(return_value=[])

        mock_model1 = make_mock_model(id="gpt-4", context_length=8192)
        mock_model2 = make_mock_model(id="gpt-3.5", context_length=16384)
        mock_models_response = MagicMock()
        mock_models_response.data = [mock_model1, mock_model2]

        provider._client.models.list = AsyncMock(return_value=mock_models_response)

        result = await provider.get_models()

        assert len(result) == 2
        assert result[0]["id"] == "gpt-4"
        assert result[1]["id"] == "gpt-3.5"
