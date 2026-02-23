"""Unit tests for qq.py channel implementation."""

from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from nanobot.channels.qq import QQChannel, _make_bot_class


class TestMakeBotClass(unittest.TestCase):
    """Tests for _make_bot_class function."""

    def test_returns_class_with_right_methods(self) -> None:
        """Test _make_bot_class returns a class with the right methods."""
        channel = MagicMock()
        channel._on_message = AsyncMock()

        bot_class = _make_bot_class(channel)

        assert hasattr(bot_class, "__bases__")
        assert len(bot_class.__bases__) > 0

        # Verify the class has the required async methods without instantiating
        # (instantiation requires event loop from botpy)
        assert hasattr(bot_class, "on_ready")
        assert hasattr(bot_class, "on_c2c_message_create")
        assert hasattr(bot_class, "on_direct_message_create")


class TestQQChannelInit(unittest.TestCase):
    """Tests for QQChannel.__init__ method."""

    def test_initialization(self) -> None:
        """Test channel initialization."""
        config = MagicMock()
        config.app_id = "test_app_id"
        config.secret = "test_secret"
        config.allow_from = []
        bus = MagicMock()

        with patch("nanobot.channels.qq.QQ_AVAILABLE", True):
            channel = QQChannel(config, bus)

        assert channel.config == config
        assert channel.bus == bus
        assert channel._client is None
        assert len(channel._processed_ids) == 0
        assert channel._running is False


class TestQQChannelStart(unittest.IsolatedAsyncioTestCase):
    """Tests for QQChannel.start method."""

    async def test_returns_early_if_qq_not_available(self) -> None:
        """Test start returns early if QQ_AVAILABLE=False."""
        config = MagicMock()
        config.app_id = "test_app_id"
        config.secret = "test_secret"
        bus = MagicMock()

        with patch("nanobot.channels.qq.QQ_AVAILABLE", False), patch(
            "nanobot.channels.qq._make_bot_class"
        ) as mock_make_bot, patch("nanobot.channels.qq.logger") as mock_logger:
            channel = QQChannel(config, bus)
            await channel.start()
            mock_logger.error.assert_called_once()
            mock_make_bot.assert_not_called()

    async def test_returns_early_if_config_missing(self) -> None:
        """Test start returns early if app_id or secret missing."""
        config = MagicMock()
        config.app_id = ""
        config.secret = "test_secret"
        bus = MagicMock()

        with patch("nanobot.channels.qq.QQ_AVAILABLE", True), patch(
            "nanobot.channels.qq.logger"
        ) as mock_logger:
            channel = QQChannel(config, bus)
            await channel.start()
            mock_logger.error.assert_called_once()

    async def test_start_sets_running_and_creates_client(self) -> None:
        """Test start sets _running=True and creates client."""
        config = MagicMock()
        config.app_id = "test_app_id"
        config.secret = "test_secret"
        bus = MagicMock()

        with patch("nanobot.channels.qq.QQ_AVAILABLE", True), patch(
            "nanobot.channels.qq._make_bot_class"
        ) as mock_make_bot, patch("nanobot.channels.qq.QQChannel._run_bot"):
            mock_bot_class = MagicMock()
            mock_make_bot.return_value = mock_bot_class
            mock_client = MagicMock()
            mock_bot_class.return_value = mock_client

            channel = QQChannel(config, bus)
            await channel.start()
            assert channel._running is True
            mock_make_bot.assert_called_once()
            mock_bot_class.assert_called_once()
            assert channel._client is mock_client


class TestQQChannelStop(unittest.IsolatedAsyncioTestCase):
    """Tests for QQChannel.stop method."""

    async def test_stop_sets_running_false(self) -> None:
        """Test stop sets _running=False."""
        config = MagicMock()
        bus = MagicMock()

        channel = QQChannel(config, bus)
        channel._running = True
        await channel.stop()
        assert channel._running is False

    async def test_stop_calls_client_close(self) -> None:
        """Test stop calls _client.close()."""
        config = MagicMock()
        bus = MagicMock()

        channel = QQChannel(config, bus)
        channel._running = True
        channel._client = MagicMock()
        channel._client.close = AsyncMock()
        await channel.stop()
        channel._client.close.assert_called_once()

    async def test_stop_handles_no_client(self) -> None:
        """Test stop handles when _client is None."""
        config = MagicMock()
        bus = MagicMock()

        channel = QQChannel(config, bus)
        channel._running = True
        channel._client = None
        await channel.stop()
        assert channel._running is False


class TestQQChannelSend(unittest.IsolatedAsyncioTestCase):
    """Tests for QQChannel.send method."""

    async def test_send_handles_no_client(self) -> None:
        """Test send handles when client is not initialized."""
        config = MagicMock()
        bus = MagicMock()

        channel = QQChannel(config, bus)
        channel._client = None

        msg = MagicMock()
        msg.chat_id = "test_chat_id"
        msg.content = "test message"

        with patch("nanobot.channels.qq.logger") as mock_logger:
            await channel.send(msg)
            mock_logger.warning.assert_called_once()

    async def test_send_calls_post_c2c_message(self) -> None:
        """Test send calls _client.api.post_c2c_message()."""
        config = MagicMock()
        bus = MagicMock()

        channel = QQChannel(config, bus)
        channel._client = MagicMock()
        channel._client.api = MagicMock()
        channel._client.api.post_c2c_message = AsyncMock()

        msg = MagicMock()
        msg.chat_id = "test_chat_id"
        msg.content = "test message"

        await channel.send(msg)
        channel._client.api.post_c2c_message.assert_called_once()
        call_kwargs = channel._client.api.post_c2c_message.call_args.kwargs
        assert call_kwargs["openid"] == "test_chat_id"
        assert call_kwargs["content"] == "test message"

    async def test_send_handles_exception(self) -> None:
        """Test send handles exception from post_c2c_message."""
        config = MagicMock()
        bus = MagicMock()

        channel = QQChannel(config, bus)
        channel._client = MagicMock()
        channel._client.api = MagicMock()
        channel._client.api.post_c2c_message = AsyncMock(side_effect=Exception("API error"))

        msg = MagicMock()
        msg.chat_id = "test_chat_id"
        msg.content = "test message"

        with patch("nanobot.channels.qq.logger") as mock_logger:
            await channel.send(msg)
            mock_logger.error.assert_called_once()


class TestQQChannelOnMessage(unittest.IsolatedAsyncioTestCase):
    """Tests for QQChannel._on_message method."""

    async def test_on_message_deduplication(self) -> None:
        """Test _on_message deduplication by message ID."""
        config = MagicMock()
        config.allow_from = []
        bus = MagicMock()

        channel = QQChannel(config, bus)

        message1 = MagicMock()
        message1.id = "msg_123"
        message1.author = MagicMock()
        message1.author.id = "user_456"
        message1.content = "Hello"

        message2 = MagicMock()
        message2.id = "msg_123"
        message2.author = MagicMock()
        message2.author.id = "user_456"
        message2.content = "Hello again"

        await channel._on_message(message1)
        await channel._on_message(message2)
        assert len(channel._processed_ids) == 1

    async def test_on_message_content_extraction(self) -> None:
        """Test _on_message extracts content correctly."""
        config = MagicMock()
        config.allow_from = []
        bus = MagicMock()

        channel = QQChannel(config, bus)
        channel._handle_message = AsyncMock()

        message = MagicMock()
        message.id = "msg_123"
        message.author = MagicMock()
        message.author.id = "user_456"
        message.content = "  Hello World  "

        await channel._on_message(message)
        channel._handle_message.assert_called_once()
        call_kwargs = channel._handle_message.call_args.kwargs
        assert call_kwargs["content"] == "Hello World"

    async def test_on_message_user_id_extraction(self) -> None:
        """Test _on_message extracts user_id from author."""
        config = MagicMock()
        config.allow_from = []
        bus = MagicMock()

        channel = QQChannel(config, bus)
        channel._handle_message = AsyncMock()

        message = MagicMock()
        message.id = "msg_123"
        message.author = MagicMock()
        message.author.id = "user_456"
        message.author.user_openid = "user_openid_789"
        message.content = "Hello"

        await channel._on_message(message)
        channel._handle_message.assert_called_once()
        call_kwargs = channel._handle_message.call_args.kwargs
        assert call_kwargs["sender_id"] == "user_456"
        assert call_kwargs["chat_id"] == "user_456"

    async def test_on_message_empty_content_returns_early(self) -> None:
        """Test _on_message returns early if content is empty."""
        config = MagicMock()
        config.allow_from = []
        bus = MagicMock()

        channel = QQChannel(config, bus)
        channel._handle_message = AsyncMock()

        message = MagicMock()
        message.id = "msg_123"
        message.author = MagicMock()
        message.author.id = "user_456"
        message.content = ""

        await channel._on_message(message)
        channel._handle_message.assert_not_called()

    async def test_on_message_handles_exception(self) -> None:
        """Test _on_message handles exception gracefully."""
        config = MagicMock()
        config.allow_from = []
        bus = MagicMock()

        channel = QQChannel(config, bus)

        message = MagicMock()
        message.id = "msg_123"
        message.author = MagicMock()
        message.author.id = "user_456"
        message.content = "Hello"

        with patch("nanobot.channels.qq.logger") as mock_logger, patch.object(
            channel, "_handle_message", side_effect=Exception("Error")
        ):
            await channel._on_message(message)
            mock_logger.exception.assert_called_once()

    async def test_on_message_calls_handle_message_with_metadata(self) -> None:
        """Test _on_message calls _handle_message with message_id in metadata."""
        config = MagicMock()
        config.allow_from = []
        bus = MagicMock()

        channel = QQChannel(config, bus)
        channel._handle_message = AsyncMock()

        message = MagicMock()
        message.id = "msg_123"
        message.author = MagicMock()
        message.author.id = "user_456"
        message.content = "Hello"

        await channel._on_message(message)
        channel._handle_message.assert_called_once()
        call_kwargs = channel._handle_message.call_args.kwargs
        assert call_kwargs["metadata"]["message_id"] == "msg_123"


if __name__ == "__main__":
    unittest.main()
