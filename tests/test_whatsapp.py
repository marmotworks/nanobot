"""Unit tests for WhatsApp channel using Node.js bridge."""

from __future__ import annotations

import asyncio
import contextlib
import json
import unittest
from unittest import IsolatedAsyncioTestCase, TestCase
from unittest.mock import AsyncMock, MagicMock, patch

from nanobot.bus.events import OutboundMessage
from nanobot.channels.whatsapp import WhatsAppChannel


class TestWhatsAppChannelInitialization(TestCase):
    """Tests for WhatsAppChannel initialization."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.config = MagicMock()
        self.config.bridge_url = "ws://localhost:3001"
        self.config.bridge_token = ""
        self.config.allow_from = []
        self.bus = MagicMock()

    def test_channel_initialization(self) -> None:
        """Test channel initialization with default config."""
        channel = WhatsAppChannel(self.config, self.bus)

        self.assertEqual(channel.name, "whatsapp")
        self.assertEqual(channel.config.bridge_url, "ws://localhost:3001")
        self.assertEqual(channel.config.bridge_token, "")
        self.assertEqual(len(channel.config.allow_from), 0)
        self.assertIsNone(channel._ws)
        self.assertFalse(channel._connected)
        self.assertFalse(channel.is_running)

    def test_channel_initialization_with_token(self) -> None:
        """Test channel initialization with auth token."""
        self.config.bridge_token = "test_token_123"

        channel = WhatsAppChannel(self.config, self.bus)

        self.assertEqual(channel.config.bridge_token, "test_token_123")

    def test_channel_initialization_with_allow_list(self) -> None:
        """Test channel initialization with allow_from list."""
        self.config.allow_from = ["1234567890", "0987654321"]

        channel = WhatsAppChannel(self.config, self.bus)

        self.assertEqual(len(channel.config.allow_from), 2)


class TestWhatsAppChannelIsAllowed(TestCase):
    """Tests for WhatsAppChannel.is_allowed()."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.config = MagicMock()
        self.config.bridge_url = "ws://localhost:3001"
        self.config.bridge_token = ""
        self.config.allow_from = []
        self.bus = MagicMock()

    def test_is_allowed_no_allow_list(self) -> None:
        """Test is_allowed returns True when no allow list is configured."""
        channel = WhatsAppChannel(self.config, self.bus)

        self.assertTrue(channel.is_allowed("1234567890"))

    def test_is_allowed_in_allow_list(self) -> None:
        """Test is_allowed returns True when sender is in allow list."""
        self.config.allow_from = ["1234567890", "0987654321"]
        channel = WhatsAppChannel(self.config, self.bus)

        self.assertTrue(channel.is_allowed("1234567890"))

    def test_is_allowed_not_in_allow_list(self) -> None:
        """Test is_allowed returns False when sender is not in allow list."""
        self.config.allow_from = ["1234567890", "0987654321"]
        channel = WhatsAppChannel(self.config, self.bus)

        self.assertFalse(channel.is_allowed("1111111111"))

    def test_is_allowed_with_lid_format(self) -> None:
        """Test is_allowed handles LID format (jid) with pipe separator."""
        # The pipe-split logic checks each part against the allow list.
        # "abc|def" → parts ["abc", "def"]; allow list must contain one of those parts.
        self.config.allow_from = ["1234567890"]
        channel = WhatsAppChannel(self.config, self.bus)

        # LID format: "1234567890|4567891234" → part "1234567890" matches allow list
        self.assertTrue(channel.is_allowed("1234567890|4567891234"))


class TestWhatsAppSendMessage(IsolatedAsyncioTestCase):
    """Tests for WhatsAppChannel.send()."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.config = MagicMock()
        self.config.bridge_url = "ws://localhost:3001"
        self.config.bridge_token = ""
        self.config.allow_from = []
        self.bus = MagicMock()

    async def test_send_not_connected(self) -> None:
        """Test send logs warning when bridge not connected."""
        channel = WhatsAppChannel(self.config, self.bus)
        channel._connected = False
        channel._ws = None

        msg = OutboundMessage(
            channel="whatsapp",
            chat_id="1234567890",
            content="Hello test",
        )

        with patch("nanobot.channels.whatsapp.logger") as mock_logger:
            await channel.send(msg)

        mock_logger.warning.assert_called_once_with("WhatsApp bridge not connected")

    async def test_send_success(self) -> None:
        """Test successful message sending through bridge."""
        channel = WhatsAppChannel(self.config, self.bus)
        channel._connected = True
        channel._ws = MagicMock()
        channel._ws.send = AsyncMock()

        msg = OutboundMessage(
            channel="whatsapp",
            chat_id="1234567890",
            content="Hello test",
        )

        await channel.send(msg)

        expected_payload = json.dumps({
            "type": "send",
            "to": "1234567890",
            "text": "Hello test",
        }, ensure_ascii=False)

        channel._ws.send.assert_called_once_with(expected_payload)

    async def test_send_with_error(self) -> None:
        """Test send handles WebSocket errors gracefully."""
        channel = WhatsAppChannel(self.config, self.bus)
        channel._connected = True
        channel._ws = MagicMock()
        channel._ws.send = AsyncMock(side_effect=Exception("WebSocket error"))

        msg = OutboundMessage(
            channel="whatsapp",
            chat_id="1234567890",
            content="Hello test",
        )

        with patch("nanobot.channels.whatsapp.logger") as mock_logger:
            await channel.send(msg)

        mock_logger.error.assert_called_once()


class TestWhatsAppHandleBridgeMessage(IsolatedAsyncioTestCase):
    """Tests for WhatsAppChannel._handle_bridge_message()."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.config = MagicMock()
        self.config.bridge_url = "ws://localhost:3001"
        self.config.bridge_token = ""
        self.config.allow_from = []
        self.bus = MagicMock()

    async def test_handle_message_incoming_text(self) -> None:
        """Test handling an incoming text message from WhatsApp."""
        channel = WhatsAppChannel(self.config, self.bus)
        channel._handle_message = AsyncMock(return_value=None)

        raw_message = json.dumps({
            "type": "message",
            "pn": "1234567890",
            "sender": "1234567890@s.whatsapp.net",
            "content": "Hello world",
            "id": "message_id_123",
            "timestamp": 1234567890,
            "isGroup": False,
        })

        await channel._handle_bridge_message(raw_message)

        channel._handle_message.assert_called_once_with(
            sender_id="1234567890",
            chat_id="1234567890@s.whatsapp.net",
            content="Hello world",
            metadata={
                "message_id": "message_id_123",
                "timestamp": 1234567890,
                "is_group": False,
            },
        )

    async def test_handle_message_voice_message(self) -> None:
        """Test handling a voice message with transcription placeholder."""
        channel = WhatsAppChannel(self.config, self.bus)
        channel._handle_message = AsyncMock(return_value=None)

        raw_message = json.dumps({
            "type": "message",
            "pn": "1234567890",
            "sender": "1234567890@s.whatsapp.net",
            "content": "[Voice Message]",
            "id": "message_id_456",
            "timestamp": 1234567890,
            "isGroup": False,
        })

        await channel._handle_bridge_message(raw_message)

        channel._handle_message.assert_called_once_with(
            sender_id="1234567890",
            chat_id="1234567890@s.whatsapp.net",
            content="[Voice Message: Transcription not available for WhatsApp yet]",
            metadata={
                "message_id": "message_id_456",
                "timestamp": 1234567890,
                "is_group": False,
            },
        )

    async def test_handle_message_status_connected(self) -> None:
        """Test handling a status update when connected."""
        channel = WhatsAppChannel(self.config, self.bus)

        raw_message = json.dumps({
            "type": "status",
            "status": "connected",
        })

        await channel._handle_bridge_message(raw_message)

        self.assertTrue(channel._connected)

    async def test_handle_message_status_disconnected(self) -> None:
        """Test handling a status update when disconnected."""
        channel = WhatsAppChannel(self.config, self.bus)
        channel._connected = True

        raw_message = json.dumps({
            "type": "status",
            "status": "disconnected",
        })

        await channel._handle_bridge_message(raw_message)

        self.assertFalse(channel._connected)

    async def test_handle_message_qr(self) -> None:
        """Test handling a QR code message."""
        channel = WhatsAppChannel(self.config, self.bus)

        raw_message = json.dumps({
            "type": "qr",
        })

        with patch("nanobot.channels.whatsapp.logger") as mock_logger:
            await channel._handle_bridge_message(raw_message)

        mock_logger.info.assert_called_once_with("Scan QR code in the bridge terminal to connect WhatsApp")

    async def test_handle_message_error(self) -> None:
        """Test handling an error message from bridge."""
        channel = WhatsAppChannel(self.config, self.bus)

        raw_message = json.dumps({
            "type": "error",
            "error": "Connection failed",
        })

        with patch("nanobot.channels.whatsapp.logger") as mock_logger:
            await channel._handle_bridge_message(raw_message)

        mock_logger.error.assert_called_once_with("WhatsApp bridge error: {}", "Connection failed")

    async def test_handle_message_invalid_json(self) -> None:
        """Test handling an invalid JSON message."""
        channel = WhatsAppChannel(self.config, self.bus)

        with patch("nanobot.channels.whatsapp.logger") as mock_logger:
            await channel._handle_bridge_message("invalid json {")

        mock_logger.warning.assert_called_once()


class TestWhatsAppStartStop(IsolatedAsyncioTestCase):
    """Tests for WhatsAppChannel.start() and stop()."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.config = MagicMock()
        self.config.bridge_url = "ws://localhost:3001"
        self.config.bridge_token = ""
        self.config.allow_from = []
        self.bus = MagicMock()

    async def test_stop_sets_flags(self) -> None:
        """Test that stop() sets running and connected flags to False."""
        channel = WhatsAppChannel(self.config, self.bus)
        channel._running = True
        channel._connected = True
        channel._ws = MagicMock()
        channel._ws.close = AsyncMock()

        await channel.stop()

        self.assertFalse(channel._running)
        self.assertFalse(channel._connected)
        self.assertIsNone(channel._ws)

    async def test_start_with_token(self) -> None:
        """Test start() sends auth token when configured."""
        self.config.bridge_token = "test_token_123"

        channel = WhatsAppChannel(self.config, self.bus)

        # Create a mock WebSocket that returns an empty async iterator immediately
        # This ensures the async-for loop exits without hanging
        mock_ws = MagicMock()
        mock_ws.__aenter__ = AsyncMock(return_value=mock_ws)
        mock_ws.__aexit__ = AsyncMock(return_value=None)
        mock_ws.send = AsyncMock()
        # Make async-for loop exit immediately by returning empty iterator
        mock_ws.__aiter__ = MagicMock(return_value=iter([]))

        with patch("websockets.connect", return_value=mock_ws), \
             patch("nanobot.channels.whatsapp.logger"):
            # Run start in a task and cancel it after a short delay
            task = asyncio.create_task(channel.start())
            await asyncio.sleep(0.01)
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task

        # Verify auth token was sent
        mock_ws.send.assert_called_once()
        call_args = mock_ws.send.call_args[0][0]
        payload = json.loads(call_args)
        self.assertEqual(payload["type"], "auth")
        self.assertEqual(payload["token"], "test_token_123")


class TestWhatsAppStartStopIsolated(IsolatedAsyncioTestCase):
    """Additional async tests for WhatsAppChannel.start() and stop()."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.config = MagicMock()
        self.config.bridge_url = "ws://localhost:3001"
        self.config.bridge_token = ""
        self.config.allow_from = []
        self.bus = MagicMock()

    async def test_start_sets_running_flag(self) -> None:
        """Test that start() sets _running to True before entering the loop."""
        channel = WhatsAppChannel(self.config, self.bus)

        # Create a mock WebSocket that returns an empty async iterator immediately
        mock_ws = MagicMock()
        mock_ws.__aenter__ = AsyncMock(return_value=mock_ws)
        mock_ws.__aexit__ = AsyncMock(return_value=None)
        # Make async-for loop exit immediately by returning empty iterator
        mock_ws.__aiter__ = MagicMock(return_value=iter([]))

        with patch("websockets.connect", return_value=mock_ws), \
             patch("nanobot.channels.whatsapp.logger"):
            task = asyncio.create_task(channel.start())
            await asyncio.sleep(0.05)
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task

        # _running is set True at the top of start(); only stop() resets it
        self.assertTrue(channel._running)


if __name__ == "__main__":
    unittest.main()
