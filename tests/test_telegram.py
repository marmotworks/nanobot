"""Unit tests for telegram.py channel implementation."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from nanobot.channels.telegram import (
    TelegramChannel,
    _markdown_to_telegram_html,
    _split_message,
)
from nanobot.config.schema import TelegramConfig


class TestMarkdownToTelegramHtml:
    """Tests for _markdown_to_telegram_html function."""

    def test_empty_string(self) -> None:
        """Test empty string input."""
        assert _markdown_to_telegram_html("") == ""

    def test_plain_text(self) -> None:
        """Test plain text without markdown."""
        text = "Hello world"
        assert _markdown_to_telegram_html(text) == "Hello world"

    def test_bold_text(self) -> None:
        """Test bold markdown syntax."""
        text = "**bold text**"
        assert _markdown_to_telegram_html(text) == "<b>bold text</b>"
        text = "__bold text__"
        assert _markdown_to_telegram_html(text) == "<b>bold text</b>"

    def test_italic_text(self) -> None:
        """Test italic markdown syntax."""
        text = "_italic text_"
        assert _markdown_to_telegram_html(text) == "<i>italic text</i>"

    def test_strikethrough_text(self) -> None:
        """Test strikethrough markdown syntax."""
        text = "~~strikethrough text~~"
        assert _markdown_to_telegram_html(text) == "<s>strikethrough text</s>"

    def test_inline_code(self) -> None:
        """Test inline code syntax."""
        text = "`code`"
        assert _markdown_to_telegram_html(text) == "<code>code</code>"

    def test_code_block(self) -> None:
        """Test code block syntax."""
        text = "```\nprint('hello')\n```"
        expected = "<pre><code>print('hello')\n</code></pre>"
        assert _markdown_to_telegram_html(text) == expected

    def test_links(self) -> None:
        """Test link syntax."""
        text = "[text](https://example.com)"
        expected = '<a href="https://example.com">text</a>'
        assert _markdown_to_telegram_html(text) == expected

    def test_headers(self) -> None:
        """Test header syntax."""
        text = "# Title\n## Subtitle"
        result = _markdown_to_telegram_html(text)
        assert result == "Title\nSubtitle"

    def test_blockquotes(self) -> None:
        """Test blockquote syntax."""
        text = "> quoted text"
        assert _markdown_to_telegram_html(text) == "quoted text"

    def test_bullet_lists(self) -> None:
        """Test bullet list syntax."""
        text = "- item 1\n* item 2"
        result = _markdown_to_telegram_html(text)
        assert result == "• item 1\n• item 2"

    def test_html_escaping(self) -> None:
        """Test that HTML special characters are escaped."""
        text = "a & b < c > d"
        assert _markdown_to_telegram_html(text) == "a &amp; b &lt; c &gt; d"

    def test_nested_formatting(self) -> None:
        """Test nested bold and italic."""
        text = "**bold and _italic_**"
        result = _markdown_to_telegram_html(text)
        assert "<b>bold and <i>italic</i></b>" in result

    def test_code_with_special_chars(self) -> None:
        """Test that code content is properly escaped."""
        text = "`a & b < c`"
        result = _markdown_to_telegram_html(text)
        assert result == "<code>a &amp; b &lt; c</code>"


class TestSplitMessage:
    """Tests for _split_message function."""

    def test_short_message_no_split(self) -> None:
        """Test short message that doesn't need splitting."""
        content = "short message"
        result = _split_message(content, max_len=4000)
        assert result == ["short message"]

    def test_exact_length_no_split(self) -> None:
        """Test message at exact max length."""
        content = "a" * 100
        result = _split_message(content, max_len=100)
        assert result == ["a" * 100]

    def test_long_message_splits_at_newline(self) -> None:
        """Test long message splits at newline."""
        content = "line1\nline2\nline3\nline4"
        result = _split_message(content, max_len=10)
        assert len(result) == 4
        assert result[0] == "line1"
        assert result[1] == "line2"
        assert result[2] == "line3"
        assert result[3] == "line4"

    def test_long_message_no_newline_splits_at_space(self) -> None:
        """Test long message without newline splits at space."""
        content = "word1 word2 word3 word4"
        result = _split_message(content, max_len=15)
        assert len(result) == 2
        assert result[0] == "word1 word2"
        assert result[1] == "word3 word4"

    def test_very_long_no_newline_no_space(self) -> None:
        """Test very long text with no newline or space."""
        content = "a" * 150
        result = _split_message(content, max_len=50)
        assert len(result) == 3
        assert result[0] == "a" * 50
        assert result[1] == "a" * 50
        assert result[2] == "a" * 50

    def test_trailing_whitespace_handling(self) -> None:
        """Test that trailing whitespace is preserved after split."""
        content = "word1 word2  word3"
        result = _split_message(content, max_len=10)
        assert result[0] == "word1"
        assert result[1] == "word2 "
        assert result[2] == "word3"

    def test_empty_content(self) -> None:
        """Test empty content."""
        result = _split_message("", max_len=4000)
        assert result == [""]


class TestTelegramChannelGetMediaType:
    """Tests for TelegramChannel._get_media_type static method."""

    def test_photo_jpg(self) -> None:
        """Test jpg extension."""
        assert TelegramChannel._get_media_type("image.jpg") == "photo"

    def test_photo_jpeg(self) -> None:
        """Test jpeg extension."""
        assert TelegramChannel._get_media_type("image.jpeg") == "photo"

    def test_photo_png(self) -> None:
        """Test png extension."""
        assert TelegramChannel._get_media_type("image.png") == "photo"

    def test_photo_gif(self) -> None:
        """Test gif extension."""
        assert TelegramChannel._get_media_type("image.gif") == "photo"

    def test_photo_webp(self) -> None:
        """Test webp extension."""
        assert TelegramChannel._get_media_type("image.webp") == "photo"

    def test_voice_ogg(self) -> None:
        """Test ogg extension."""
        assert TelegramChannel._get_media_type("audio.ogg") == "voice"

    def test_audio_mp3(self) -> None:
        """Test mp3 extension."""
        assert TelegramChannel._get_media_type("audio.mp3") == "audio"

    def test_audio_m4a(self) -> None:
        """Test m4a extension."""
        assert TelegramChannel._get_media_type("audio.m4a") == "audio"

    def test_audio_wav(self) -> None:
        """Test wav extension."""
        assert TelegramChannel._get_media_type("audio.wav") == "audio"

    def test_audio_aac(self) -> None:
        """Test aac extension."""
        assert TelegramChannel._get_media_type("audio.aac") == "audio"

    def test_unknown_document(self) -> None:
        """Test unknown extension returns document."""
        assert TelegramChannel._get_media_type("file.xyz") == "document"

    def test_no_extension_document(self) -> None:
        """Test file without extension returns document."""
        assert TelegramChannel._get_media_type("file") == "document"

    def test_case_insensitive(self) -> None:
        """Test extension matching is case insensitive."""
        assert TelegramChannel._get_media_type("image.JPG") == "photo"
        assert TelegramChannel._get_media_type("image.PNg") == "photo"


class TestTelegramChannelGetExtension:
    """Tests for TelegramChannel._get_extension instance method."""

    def test_image_jpeg(self) -> None:
        """Test image/jpeg mime type."""
        channel = TelegramChannel(MagicMock(), MagicMock())
        result = channel._get_extension("image", "image/jpeg")
        assert result == ".jpg"

    def test_image_png(self) -> None:
        """Test image/png mime type."""
        channel = TelegramChannel(MagicMock(), MagicMock())
        result = channel._get_extension("image", "image/png")
        assert result == ".png"

    def test_image_gif(self) -> None:
        """Test image/gif mime type."""
        channel = TelegramChannel(MagicMock(), MagicMock())
        result = channel._get_extension("image", "image/gif")
        assert result == ".gif"

    def test_audio_ogg(self) -> None:
        """Test audio/ogg mime type."""
        channel = TelegramChannel(MagicMock(), MagicMock())
        result = channel._get_extension("voice", "audio/ogg")
        assert result == ".ogg"

    def test_audio_mpeg(self) -> None:
        """Test audio/mpeg mime type."""
        channel = TelegramChannel(MagicMock(), MagicMock())
        result = channel._get_extension("audio", "audio/mpeg")
        assert result == ".mp3"

    def test_audio_mp4(self) -> None:
        """Test audio/mp4 mime type."""
        channel = TelegramChannel(MagicMock(), MagicMock())
        result = channel._get_extension("audio", "audio/mp4")
        assert result == ".m4a"

    def test_fallback_to_media_type(self) -> None:
        """Test fallback to media type when no mime type."""
        channel = TelegramChannel(MagicMock(), MagicMock())
        assert channel._get_extension("image", None) == ".jpg"
        assert channel._get_extension("voice", None) == ".ogg"
        assert channel._get_extension("audio", None) == ".mp3"
        assert channel._get_extension("file", None) == ""

    def test_fallback_unknown_media_type(self) -> None:
        """Test fallback for unknown media type."""
        channel = TelegramChannel(MagicMock(), MagicMock())
        result = channel._get_extension("unknown", None)
        assert result == ""


class TestTelegramChannelInit:
    """Tests for TelegramChannel.__init__ method."""

    def test_initialization(self) -> None:
        """Test channel initialization."""
        config = TelegramConfig(
            token="test_token",
            chat_id=12345,
            reply_to_message=False,
            proxy=None,
        )
        bus = MagicMock()
        channel = TelegramChannel(config, bus, groq_api_key="test_key")

        assert channel.config == config
        assert channel.groq_api_key == "test_key"
        assert channel._app is None
        assert channel._chat_ids == {}
        assert channel._typing_tasks == {}


class TestTelegramChannelSend:
    """Tests for TelegramChannel.send method."""

    @pytest.mark.asyncio
    async def test_send_without_app(self) -> None:
        """Test send when bot is not running."""
        config = TelegramConfig(
            token="test_token",
            chat_id=12345,
            reply_to_message=False,
            proxy=None,
        )
        bus = MagicMock()
        channel = TelegramChannel(config, bus)
        channel._app = None

        msg = MagicMock()
        msg.chat_id = "12345"
        msg.content = "test message"
        msg.media = None

        with patch("nanobot.channels.telegram.logger") as mock_logger:
            await channel.send(msg)
            mock_logger.warning.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_with_invalid_chat_id(self) -> None:
        """Test send with invalid chat_id."""
        config = TelegramConfig(
            token="test_token",
            chat_id=12345,
            reply_to_message=False,
            proxy=None,
        )
        bus = MagicMock()
        channel = TelegramChannel(config, bus)

        mock_app = MagicMock()
        mock_app.bot = MagicMock()
        channel._app = mock_app

        msg = MagicMock()
        msg.chat_id = "invalid"
        msg.content = "test message"
        msg.media = None

        with patch("nanobot.channels.telegram.logger") as mock_logger:
            await channel.send(msg)
            mock_logger.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_text_message(self) -> None:
        """Test sending text message."""
        config = TelegramConfig(
            token="test_token",
            chat_id=12345,
            reply_to_message=False,
            proxy=None,
        )
        bus = MagicMock()
        channel = TelegramChannel(config, bus)

        mock_app = MagicMock()
        mock_app.bot = MagicMock()
        mock_app.bot.send_message = AsyncMock()
        channel._app = mock_app

        msg = MagicMock()
        msg.chat_id = "12345"
        msg.content = "test message"
        msg.media = None
        msg.metadata = {}

        await channel.send(msg)
        mock_app.bot.send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_with_media(self) -> None:
        """Test sending message with media."""
        config = TelegramConfig(
            token="test_token",
            chat_id=12345,
            reply_to_message=False,
            proxy=None,
        )
        bus = MagicMock()
        channel = TelegramChannel(config, bus)

        mock_app = MagicMock()
        mock_app.bot = MagicMock()
        mock_app.bot.send_photo = AsyncMock()
        mock_app.bot.send_message = AsyncMock()
        channel._app = mock_app

        msg = MagicMock()
        msg.chat_id = "12345"
        msg.content = "test message"
        msg.media = ["/path/to/image.jpg"]
        msg.metadata = {}

        with patch("builtins.open", MagicMock()):
            await channel.send(msg)

    @pytest.mark.asyncio
    async def test_send_stops_typing(self) -> None:
        """Test that send stops typing indicator."""
        config = TelegramConfig(
            token="test_token",
            chat_id=12345,
            reply_to_message=False,
            proxy=None,
        )
        bus = MagicMock()
        channel = TelegramChannel(config, bus)

        mock_task = MagicMock()
        channel._typing_tasks["12345"] = mock_task

        mock_app = MagicMock()
        mock_app.bot = MagicMock()
        mock_app.bot.send_message = AsyncMock()
        channel._app = mock_app

        msg = MagicMock()
        msg.chat_id = "12345"
        msg.content = "test message"
        msg.media = None
        msg.metadata = {}

        await channel.send(msg)
        assert "12345" not in channel._typing_tasks


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
