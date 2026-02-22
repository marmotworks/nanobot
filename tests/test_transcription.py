"""Tests for GroqTranscriptionProvider."""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from nanobot.providers.transcription import GroqTranscriptionProvider


class TestGroqTranscriptionProvider:
    """Tests for the GroqTranscriptionProvider class."""

    @pytest.mark.asyncio
    async def test_success(self, tmp_path: pytest.TempPathFactory) -> None:
        """Test successful transcription with mocked httpx client."""
        # Create a temporary file for testing
        temp_file = tmp_path / "test_audio.mp3"
        temp_file.write_text("dummy audio content")

        # Mock the async context manager and post response
        mock_client = AsyncMock()
        mock_response = Mock()
        mock_response.json.return_value = {"text": "hello world"}
        mock_response.raise_for_status.return_value = None
        mock_client.post.return_value = mock_response

        # Mock httpx.AsyncClient as async context manager
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch(
            "nanobot.providers.transcription.httpx.AsyncClient",
            return_value=mock_client,
        ):
            provider = GroqTranscriptionProvider(api_key="test-key")
            result = await provider.transcribe(str(temp_file))

        assert result == "hello world"

    @pytest.mark.asyncio
    async def test_missing_api_key(self) -> None:
        """Test transcribe returns empty string when no API key is set."""
        with patch("os.environ.get", return_value=None):
            provider = GroqTranscriptionProvider(api_key=None)
            result = await provider.transcribe("any/path")

        assert result == ""

    @pytest.mark.asyncio
    async def test_missing_file(self) -> None:
        """Test transcribe returns empty string when file does not exist."""
        provider = GroqTranscriptionProvider(api_key="test-key")
        result = await provider.transcribe("/nonexistent/path/audio.mp3")

        assert result == ""

    @pytest.mark.asyncio
    async def test_api_error(self, tmp_path: pytest.TempPathFactory) -> None:
        """Test transcribe returns empty string on API error."""
        # Create a temporary file for testing
        temp_file = tmp_path / "test_audio.mp3"
        temp_file.write_text("dummy audio content")

        # Mock the async context manager and post to raise an exception
        mock_client = AsyncMock()
        mock_client.post.side_effect = Exception("network error")
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch(
            "nanobot.providers.transcription.httpx.AsyncClient",
            return_value=mock_client,
        ):
            provider = GroqTranscriptionProvider(api_key="test-key")
            result = await provider.transcribe(str(temp_file))

        assert result == ""

    @pytest.mark.asyncio
    async def test_returns_empty_when_text_key_missing(
        self,
        tmp_path: pytest.TempPathFactory,
    ) -> None:
        """Test transcribe returns empty string when response has no text key."""
        # Create a temporary file for testing
        temp_file = tmp_path / "test_audio.mp3"
        temp_file.write_text("dummy audio content")

        # Mock the async context manager and post response with empty JSON
        mock_client = AsyncMock()
        mock_response = Mock()
        mock_response.json.return_value = {}
        mock_response.raise_for_status.return_value = None
        mock_client.post.return_value = mock_response

        # Mock httpx.AsyncClient as async context manager
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch(
            "nanobot.providers.transcription.httpx.AsyncClient",
            return_value=mock_client,
        ):
            provider = GroqTranscriptionProvider(api_key="test-key")
            result = await provider.transcribe(str(temp_file))

        assert result == ""
