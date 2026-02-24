"""Unit tests for DingTalk channel initialization and message parsing."""

import sys
import unittest
from unittest import IsolatedAsyncioTestCase, TestCase
from unittest.mock import AsyncMock, MagicMock, patch

from nanobot.channels.dingtalk import (
    DINGTALK_AVAILABLE,
    CallbackHandler,
    DingTalkChannel,
    NanobotDingTalkHandler,
)

# Import DingTalk module components before mocking to ensure proper inheritance

# Mock dingtalk_stream SDK before importing the module
mock_dingtalk_stream = MagicMock()
mock_ack_message = MagicMock()
mock_ack_message.STATUS_OK = "OK"

# CallbackHandler needs to work with super().__init__() - use a real class with MagicMock parent
class MockCallbackHandler:
    """Mock CallbackHandler that properly handles __init__."""
    def __init__(self):
        pass

mock_callback_handler = MockCallbackHandler
mock_callback_message = MagicMock()
mock_credential = MagicMock()
mock_dingtalk_client = MagicMock()
mock_chatbot_message = MagicMock()

mock_dingtalk_stream.AckMessage = mock_ack_message
mock_dingtalk_stream.CallbackHandler = mock_callback_handler
mock_dingtalk_stream.CallbackMessage = mock_callback_message
mock_dingtalk_stream.Credential = mock_credential
mock_dingtalk_stream.DingTalkStreamClient = mock_dingtalk_client
mock_dingtalk_stream.chatbot.ChatbotMessage = mock_chatbot_message

# Patch sys.modules to mock dingtalk_stream
sys.modules["dingtalk_stream"] = mock_dingtalk_stream
sys.modules["dingtalk_stream.chatbot"] = MagicMock()
sys.modules["dingtalk_stream.chatbot"].ChatbotMessage = mock_chatbot_message


class TestDingTalkChannelInitialization(TestCase):
    """Tests for DingTalkChannel initialization."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.config = MagicMock()
        self.config.client_id = "test_client_id"
        self.config.client_secret = "test_client_secret"
        self.config.allow_from = []
        self.bus = MagicMock()

    def test_channel_initialization_with_sdk(self) -> None:
        """Test channel initialization when DingTalk SDK is available."""
        self.assertTrue(DINGTALK_AVAILABLE)

        channel = DingTalkChannel(self.config, self.bus)
        self.assertEqual(channel.name, "dingtalk")
        self.assertFalse(channel.is_running)
        self.assertIsNone(channel._client)
        self.assertIsNone(channel._http)
        self.assertEqual(len(channel._background_tasks), 0)

    def test_channel_initialization_with_allow_list(self) -> None:
        """Test channel initialization with allow_from list."""
        self.config.allow_from = ["user1", "user2"]

        channel = DingTalkChannel(self.config, self.bus)
        self.assertTrue(DINGTALK_AVAILABLE)
        self.assertEqual(len(channel.config.allow_from), 2)


class TestNanobotDingTalkHandler(TestCase):
    """Tests for NanobotDingTalkHandler initialization."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.config = MagicMock()
        self.config.client_id = "test_client_id"
        self.config.client_secret = "test_client_secret"
        self.config.allow_from = []
        self.bus = MagicMock()

        self.channel = DingTalkChannel(self.config, self.bus)
        self.handler = NanobotDingTalkHandler(self.channel)

    def test_handler_initialization(self) -> None:
        """Test handler initialization."""
        self.assertEqual(self.handler.channel, self.channel)

    def test_handler_inherits_callback_handler(self) -> None:
        """Test handler inherits from CallbackHandler."""
        self.assertIsInstance(self.handler, CallbackHandler)


class TestNanobotDingTalkHandlerProcess(IsolatedAsyncioTestCase):
    """Tests for NanobotDingTalkHandler.process() message processing."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.config = MagicMock()
        self.config.client_id = "test_client_id"
        self.config.client_secret = "test_client_secret"
        self.config.allow_from = []
        self.bus = MagicMock()

        self.channel = DingTalkChannel(self.config, self.bus)
        self.handler = NanobotDingTalkHandler(self.channel)

        # Setup mock message data
        self.mock_message = MagicMock()
        self.mock_message.data = {
            "text": {"content": "Hello world"},
            "senderId": "user123",
            "senderNick": "TestUser",
        }

        # Setup ChatbotMessage mock
        self.mock_chatbot_msg = MagicMock()
        self.mock_chatbot_msg.text = MagicMock()
        self.mock_chatbot_msg.text.content = "Hello world"
        self.mock_chatbot_msg.sender_staff_id = "user123"
        self.mock_chatbot_msg.sender_id = None
        self.mock_chatbot_msg.sender_nick = "TestUser"
        self.mock_chatbot_msg.message_type = "text"

    async def test_process_with_valid_text_message(self) -> None:
        """Test processing a valid text message."""
        mock_chatbot_message = MagicMock()
        mock_chatbot_message.from_dict.return_value = self.mock_chatbot_msg

        with patch("nanobot.channels.dingtalk.ChatbotMessage", mock_chatbot_message):
            self.channel._on_message = AsyncMock(return_value=None)

            result = await self.handler.process(self.mock_message)

            # Verify results
            self.assertEqual(result, ("OK", "OK"))
            self.channel._on_message.assert_called_once_with(
                "Hello world", "user123", "TestUser"
            )

    async def test_process_with_empty_content(self) -> None:
        """Test processing a message with empty content."""
        self.mock_message.data = {"text": {"content": ""}}

        self.mock_chatbot_msg.text.content = ""
        self.mock_chatbot_msg.sender_staff_id = None
        self.mock_chatbot_msg.sender_id = None
        self.mock_chatbot_msg.sender_nick = None
        self.mock_chatbot_msg.message_type = "text"

        mock_chatbot_message = MagicMock()
        mock_chatbot_message.from_dict.return_value = self.mock_chatbot_msg

        with patch("nanobot.channels.dingtalk.ChatbotMessage", mock_chatbot_message):
            self.channel._on_message = AsyncMock(return_value=None)

            result = await self.handler.process(self.mock_message)

            self.assertEqual(result, ("OK", "OK"))
            self.channel._on_message.assert_not_called()

    async def test_process_with_fallback_text_extraction(self) -> None:
        """Test fallback text extraction from raw message data."""
        self.mock_message.data = {
            "text": {"content": "Fallback content"},
        }

        self.mock_chatbot_msg.text = None
        self.mock_chatbot_msg.sender_staff_id = "user456"
        self.mock_chatbot_msg.sender_id = None
        self.mock_chatbot_msg.sender_nick = "FallbackUser"
        self.mock_chatbot_msg.message_type = "unknown"

        mock_chatbot_message = MagicMock()
        mock_chatbot_message.from_dict.return_value = self.mock_chatbot_msg

        with patch("nanobot.channels.dingtalk.ChatbotMessage", mock_chatbot_message):
            self.channel._on_message = AsyncMock(return_value=None)

            result = await self.handler.process(self.mock_message)

            self.assertEqual(result, ("OK", "OK"))
            self.channel._on_message.assert_called_once_with(
                "Fallback content", "user456", "FallbackUser"
            )

    async def test_process_with_exception(self) -> None:
        """Test processing handles exceptions gracefully."""
        self.mock_message.data = {"text": {"content": "Test"}}

        mock_chatbot_message = MagicMock()
        mock_chatbot_message.from_dict.side_effect = Exception("Test error")

        with patch("nanobot.channels.dingtalk.ChatbotMessage", mock_chatbot_message):
            self.channel._on_message = AsyncMock(return_value=None)

            result = await self.handler.process(self.mock_message)

            # Should still return OK to avoid retry loop
            self.assertEqual(result, ("OK", "Error"))


class TestDingTalkGetAccessToken(IsolatedAsyncioTestCase):
    """Tests for DingTalkChannel._get_access_token()."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.config = MagicMock()
        self.config.client_id = "test_client_id"
        self.config.client_secret = "test_client_secret"
        self.config.allow_from = []
        self.bus = MagicMock()

        self.channel = DingTalkChannel(self.config, self.bus)

    async def test_get_access_token_success(self) -> None:
        """Test successful access token retrieval."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "accessToken": "test_token_123",
            "expireIn": 7200,
        }
        mock_response.raise_for_status = MagicMock()

        mock_http_client = MagicMock()
        mock_http_client.post = AsyncMock(return_value=mock_response)
        self.channel._http = mock_http_client

        token = await self.channel._get_access_token()

        self.assertEqual(token, "test_token_123")
        self.assertEqual(self.channel._access_token, "test_token_123")
        self.assertGreater(self.channel._token_expiry, 0)

    async def test_get_access_token_cached(self) -> None:
        """Test cached access token is returned without HTTP call."""
        self.channel._access_token = "cached_token"
        self.channel._token_expiry = 9999999999  # Far future

        mock_http_client = MagicMock()
        mock_http_client.post = AsyncMock(return_value=MagicMock())
        self.channel._http = mock_http_client

        token = await self.channel._get_access_token()

        self.assertEqual(token, "cached_token")
        mock_http_client.post.assert_not_called()

    async def test_get_access_token_http_error(self) -> None:
        """Test HTTP error handling in token retrieval."""
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = Exception("HTTP Error")

        mock_http_client = MagicMock()
        mock_http_client.post = AsyncMock(return_value=mock_response)
        self.channel._http = mock_http_client

        token = await self.channel._get_access_token()

        self.assertIsNone(token)

    async def test_get_access_token_no_http_client(self) -> None:
        """Test token retrieval when HTTP client is not initialized."""
        self.channel._http = None
        token = await self.channel._get_access_token()
        self.assertIsNone(token)


class TestDingTalkSendMessage(IsolatedAsyncioTestCase):
    """Tests for DingTalkChannel.send()."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.config = MagicMock()
        self.config.client_id = "test_client_id"
        self.config.client_secret = "test_client_secret"
        self.config.allow_from = []
        self.bus = MagicMock()

        self.channel = DingTalkChannel(self.config, self.bus)

    async def test_send_with_success(self) -> None:
        """Test successful message sending."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = ""

        mock_http_client = MagicMock()
        mock_http_client.post = AsyncMock(return_value=mock_response)
        self.channel._http = mock_http_client

        # Mock token retrieval
        with patch.object(self.channel, "_get_access_token", new_callable=AsyncMock) as mock_token:
            mock_token.return_value = "test_token"
            from nanobot.bus.events import OutboundMessage

            msg = OutboundMessage(
                channel="dingtalk",
                chat_id="user123",
                content="Hello test",
            )
            await self.channel.send(msg)

        mock_http_client.post.assert_called_once()

    async def test_send_with_token_failure(self) -> None:
        """Test message sending when token retrieval fails."""
        mock_http_client = MagicMock()
        mock_http_client.post = AsyncMock(return_value=MagicMock())
        self.channel._http = mock_http_client

        with patch.object(self.channel, "_get_access_token", new_callable=AsyncMock) as mock_token:
            mock_token.return_value = None
            from nanobot.bus.events import OutboundMessage

            msg = OutboundMessage(
                channel="dingtalk",
                chat_id="user123",
                content="Hello test",
            )
            await self.channel.send(msg)

        mock_http_client.post.assert_not_called()

    async def test_send_with_http_error(self) -> None:
        """Test message sending when HTTP request fails."""
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Bad Request"

        mock_http_client = MagicMock()
        mock_http_client.post = AsyncMock(return_value=mock_response)
        self.channel._http = mock_http_client

        with patch.object(self.channel, "_get_access_token", new_callable=AsyncMock) as mock_token:
            mock_token.return_value = "test_token"
            from nanobot.bus.events import OutboundMessage

            msg = OutboundMessage(
                channel="dingtalk",
                chat_id="user123",
                content="Hello test",
            )
            await self.channel.send(msg)

        mock_http_client.post.assert_called_once()


class TestDingTalkOnMessage(IsolatedAsyncioTestCase):
    """Tests for DingTalkChannel._on_message()."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.config = MagicMock()
        self.config.client_id = "test_client_id"
        self.config.client_secret = "test_client_secret"
        self.config.allow_from = []
        self.bus = MagicMock()

        self.channel = DingTalkChannel(self.config, self.bus)

    async def test_on_message_publishes_to_bus(self) -> None:
        """Test that _on_message publishes to the message bus."""
        self.channel._handle_message = AsyncMock(return_value=None)

        await self.channel._on_message("Hello world", "user123", "TestUser")

        self.channel._handle_message.assert_called_once_with(
            sender_id="user123",
            chat_id="user123",
            content="Hello world",
            metadata={
                "sender_name": "TestUser",
                "platform": "dingtalk",
            },
        )

    async def test_on_message_with_allow_list(self) -> None:
        """Test _on_message respects allow_from configuration."""
        self.config.allow_from = ["allowed_user"]
        self.channel = DingTalkChannel(self.config, self.bus)
        self.channel._handle_message = AsyncMock(return_value=None)

        # Sender not in allow list
        await self.channel._on_message("Hello world", "unauthorized_user", "TestUser")

        # The _handle_message should still be called, but the base class will check permissions
        self.channel._handle_message.assert_called_once()


if __name__ == "__main__":
    unittest.main()
