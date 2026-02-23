"""Unit tests for Slack channel initialization and message handling."""
# ruff: noqa: E402

from __future__ import annotations

import sys
from unittest import IsolatedAsyncioTestCase, TestCase
from unittest.mock import AsyncMock, MagicMock, patch

# Mock slack_sdk and slack_bolt BEFORE importing SlackChannel
mock_slack_sdk = MagicMock()
mock_slack_sdk.socket_mode = MagicMock()
mock_slack_sdk.socket_mode.request = MagicMock()
mock_slack_sdk.socket_mode.response = MagicMock()
mock_slack_sdk.socket_mode.websockets = MagicMock()
mock_slack_sdk.web = MagicMock()
mock_slack_sdk.web.async_client = MagicMock()

# Create proper mock classes
mock_socket_mode_request = MagicMock()
mock_socket_mode_response = MagicMock()
mock_socket_mode_response.return_value = MagicMock()
mock_socket_mode_response.return_value.envelope_id = "env123"

mock_slack_sdk.socket_mode.request.SocketModeRequest = mock_socket_mode_request
mock_slack_sdk.socket_mode.response.SocketModeResponse = mock_socket_mode_response

sys.modules["slack_sdk"] = mock_slack_sdk
sys.modules["slack_sdk.socket_mode"] = mock_slack_sdk.socket_mode
sys.modules["slack_sdk.socket_mode.request"] = mock_slack_sdk.socket_mode.request
sys.modules["slack_sdk.socket_mode.response"] = mock_slack_sdk.socket_mode.response
sys.modules["slack_sdk.socket_mode.websockets"] = mock_slack_sdk.socket_mode.websockets
sys.modules["slack_sdk.web"] = mock_slack_sdk.web
sys.modules["slack_sdk.web.async_client"] = mock_slack_sdk.web.async_client

# Mock slackify_markdown - this is imported at module level in slack.py
mock_slackify_markdown = MagicMock()
mock_slackify_markdown.return_value = "mocked mrkdwn"
sys.modules["slackify_markdown"] = mock_slackify_markdown

from nanobot.channels.slack import SlackChannel


class TestSlackChannelInitialization(TestCase):
    """Tests for SlackChannel initialization."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.config = MagicMock()
        self.config.bot_token = "xoxb-test-token"
        self.config.app_token = "xapp-test-token"
        self.config.mode = "socket"
        self.config.group_policy = "mention"
        self.config.group_allow_from = []
        self.config.dm.enabled = True
        self.config.dm.policy = "open"
        self.config.dm.allow_from = []
        self.config.reply_in_thread = True
        self.config.react_emoji = "eyes"

        self.bus = MagicMock()

    def test_channel_initialization(self) -> None:
        """Test channel initialization with valid config."""
        channel = SlackChannel(self.config, self.bus)

        self.assertEqual(channel.name, "slack")
        self.assertFalse(channel.is_running)
        self.assertIsNone(channel._web_client)
        self.assertIsNone(channel._socket_client)
        self.assertIsNone(channel._bot_user_id)

    def test_channel_initialization_with_allow_list(self) -> None:
        """Test channel initialization with allow_from list."""
        self.config.group_policy = "allowlist"
        self.config.group_allow_from = ["C123", "C456"]
        self.config.dm.policy = "allowlist"
        self.config.dm.allow_from = ["U123", "U456"]

        channel = SlackChannel(self.config, self.bus)

        self.assertEqual(len(channel.config.group_allow_from), 2)
        self.assertEqual(len(channel.config.dm.allow_from), 2)


class TestSlackChannelIsAllowed(TestCase):
    """Tests for SlackChannel._is_allowed()."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.config = MagicMock()
        self.config.bot_token = "xoxb-test-token"
        self.config.app_token = "xapp-test-token"
        self.config.mode = "socket"
        self.config.group_policy = "mention"
        self.config.group_allow_from = []
        self.config.dm.enabled = True
        self.config.dm.policy = "open"
        self.config.dm.allow_from = []
        self.config.reply_in_thread = True
        self.config.react_emoji = "eyes"

        self.bus = MagicMock()
        self.channel = SlackChannel(self.config, self.bus)

    def test_is_allowed_dm_open_policy(self) -> None:
        """Test DM with open policy - should always return True."""
        result = self.channel._is_allowed("U123", "D123", "im")
        self.assertTrue(result)

    def test_is_allowed_dm_closed_policy_not_allowed(self) -> None:
        """Test DM with closed policy - sender not in allowlist."""
        self.config.dm.policy = "allowlist"
        self.config.dm.allow_from = ["U456", "U789"]

        result = self.channel._is_allowed("U123", "D123", "im")
        self.assertFalse(result)

    def test_is_allowed_dm_closed_policy_allowed(self) -> None:
        """Test DM with closed policy - sender in allowlist."""
        self.config.dm.policy = "allowlist"
        self.config.dm.allow_from = ["U123", "U456"]

        result = self.channel._is_allowed("U123", "D123", "im")
        self.assertTrue(result)

    def test_is_allowed_dm_disabled(self) -> None:
        """Test DM when disabled."""
        self.config.dm.enabled = False

        result = self.channel._is_allowed("U123", "D123", "im")
        self.assertFalse(result)

    def test_is_allowed_group_open_policy(self) -> None:
        """Test group channel with open policy - should always return True."""
        self.config.group_policy = "open"

        result = self.channel._is_allowed("U123", "C123", "channel")
        self.assertTrue(result)

    def test_is_allowed_group_allowlist_not_allowed(self) -> None:
        """Test group channel with allowlist policy - channel not in allowlist."""
        self.config.group_policy = "allowlist"
        self.config.group_allow_from = ["C456", "C789"]

        result = self.channel._is_allowed("U123", "C123", "channel")
        self.assertFalse(result)

    def test_is_allowed_group_allowlist_allowed(self) -> None:
        """Test group channel with allowlist policy - channel in allowlist."""
        self.config.group_policy = "allowlist"
        self.config.group_allow_from = ["C123", "C456"]

        result = self.channel._is_allowed("U123", "C123", "channel")
        self.assertTrue(result)


class TestSlackChannelShouldRespondInChannel(TestCase):
    """Tests for SlackChannel._should_respond_in_channel()."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.config = MagicMock()
        self.config.bot_token = "xoxb-test-token"
        self.config.app_token = "xapp-test-token"
        self.config.mode = "socket"
        self.config.group_policy = "mention"
        self.config.group_allow_from = []
        self.config.dm.enabled = True
        self.config.dm.policy = "open"
        self.config.dm.allow_from = []
        self.config.reply_in_thread = True
        self.config.react_emoji = "eyes"

        self.bus = MagicMock()
        self.channel = SlackChannel(self.config, self.bus)
        self.channel._bot_user_id = "U123"

    def test_should_respond_open_policy(self) -> None:
        """Test with open policy - should always return True."""
        self.config.group_policy = "open"

        result = self.channel._should_respond_in_channel("message", "hello", "C123")
        self.assertTrue(result)

    def test_should_respond_mention_policy_app_mention(self) -> None:
        """Test with mention policy - app_mention type."""
        self.config.group_policy = "mention"

        result = self.channel._should_respond_in_channel("app_mention", "hello", "C123")
        self.assertTrue(result)

    def test_should_respond_mention_policy_message_with_mention(self) -> None:
        """Test with mention policy - message type with bot mention."""
        self.config.group_policy = "mention"
        self.channel._bot_user_id = "U123"

        result = self.channel._should_respond_in_channel(
            "message",
            "<@U123> hello",
            "C123",
        )
        self.assertTrue(result)

    def test_should_respond_mention_policy_message_without_mention(self) -> None:
        """Test with mention policy - message type without bot mention."""
        self.config.group_policy = "mention"

        result = self.channel._should_respond_in_channel("message", "hello", "C123")
        self.assertFalse(result)

    def test_should_respond_mention_policy_no_bot_user_id(self) -> None:
        """Test with mention policy - no bot user ID set."""
        self.config.group_policy = "mention"
        self.channel._bot_user_id = None

        result = self.channel._should_respond_in_channel("message", "<@U123> hello", "C123")
        self.assertFalse(result)

    def test_should_respond_allowlist_policy_channel_allowed(self) -> None:
        """Test with allowlist policy - channel in allowlist."""
        self.config.group_policy = "allowlist"
        self.config.group_allow_from = ["C123", "C456"]

        result = self.channel._should_respond_in_channel("message", "hello", "C123")
        self.assertTrue(result)

    def test_should_respond_allowlist_policy_channel_not_allowed(self) -> None:
        """Test with allowlist policy - channel not in allowlist."""
        self.config.group_policy = "allowlist"
        self.config.group_allow_from = ["C456", "C789"]

        result = self.channel._should_respond_in_channel("message", "hello", "C123")
        self.assertFalse(result)


class TestSlackChannelStripBotMention(TestCase):
    """Tests for SlackChannel._strip_bot_mention()."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.config = MagicMock()
        self.config.bot_token = "xoxb-test-token"
        self.config.app_token = "xapp-test-token"
        self.config.mode = "socket"
        self.config.group_policy = "mention"
        self.config.group_allow_from = []
        self.config.dm.enabled = True
        self.config.dm.policy = "open"
        self.config.dm.allow_from = []
        self.config.reply_in_thread = True
        self.config.react_emoji = "eyes"

        self.bus = MagicMock()
        self.channel = SlackChannel(self.config, self.bus)
        self.channel._bot_user_id = "U123"

    def test_strip_bot_mention_basic(self) -> None:
        """Test basic bot mention stripping."""
        text = "<@U123> hello"
        result = self.channel._strip_bot_mention(text)
        self.assertEqual(result, "hello")

    def test_strip_bot_mention_with_trailing_space(self) -> None:
        """Test bot mention stripping with trailing space."""
        text = "<@U123> hello"
        result = self.channel._strip_bot_mention(text)
        self.assertEqual(result, "hello")

    def test_strip_bot_mention_with_multiple_spaces(self) -> None:
        """Test bot mention stripping with multiple spaces."""
        text = "<@U123>   hello world"
        result = self.channel._strip_bot_mention(text)
        self.assertEqual(result, "hello world")

    def test_strip_bot_mention_no_mention(self) -> None:
        """Test text without bot mention - should return unchanged."""
        text = "hello world"
        result = self.channel._strip_bot_mention(text)
        self.assertEqual(result, "hello world")

    def test_strip_bot_mention_empty_text(self) -> None:
        """Test empty text - should return empty."""
        result = self.channel._strip_bot_mention("")
        self.assertEqual(result, "")

    def test_strip_bot_mention_no_bot_user_id(self) -> None:
        """Test when bot user ID is not set."""
        self.channel._bot_user_id = None
        text = "<@U123> hello"
        result = self.channel._strip_bot_mention(text)
        self.assertEqual(result, "<@U123> hello")

    def test_strip_bot_mention_multiple_mentions(self) -> None:
        """Test text with multiple bot mentions."""
        text = "<@U123> hello <@U123> world"
        result = self.channel._strip_bot_mention(text)
        self.assertEqual(result, "hello world")


class TestSlackChannelToMrkdwn(TestCase):
    """Tests for SlackChannel._to_mrkdwn()."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.config = MagicMock()
        self.config.bot_token = "xoxb-test-token"
        self.config.app_token = "xapp-test-token"
        self.config.mode = "socket"
        self.config.group_policy = "mention"
        self.config.group_allow_from = []
        self.config.dm.enabled = True
        self.config.dm.policy = "open"
        self.config.dm.allow_from = []
        self.config.reply_in_thread = True
        self.config.react_emoji = "eyes"

        self.bus = MagicMock()

    def test_to_mrkdwn_empty_text(self) -> None:
        """Test empty text - should return empty string."""
        result = SlackChannel._to_mrkdwn("")
        self.assertEqual(result, "")

    def test_to_mrkdwn_with_slackify_markdown(self) -> None:
        """Test text conversion using slackify_markdown."""
        text = "**bold** and *italic*"

        with patch("nanobot.channels.slack.slackify_markdown") as mock_slackify:
            mock_slackify.return_value = "mocked mrkdwn"
            result = SlackChannel._to_mrkdwn(text)
            mock_slackify.assert_called_once_with(text)
            self.assertEqual(result, "mocked mrkdwn")

    def test_to_mrkdwn_with_table_conversion(self) -> None:
        """Test table conversion in markdown."""
        text = """
| Header 1 | Header 2 |
|----------|----------|
| Cell 1   | Cell 2   |
"""

        with patch("nanobot.channels.slack.slackify_markdown") as mock_slackify:
            mock_slackify.return_value = "mocked mrkdwn"
            result = SlackChannel._to_mrkdwn(text)
            self.assertEqual(result, "mocked mrkdwn")

    def test_to_mrkdwn_preserves_non_table_content(self) -> None:
        """Test that non-table content is passed to slackify_markdown."""
        text = "Hello **world**"

        # The module already imported slackify_markdown, so we need to patch it at the module level
        with patch("nanobot.channels.slack.slackify_markdown") as mock_slackify:
            mock_slackify.return_value = "Hello :bold:world:"
            result = SlackChannel._to_mrkdwn(text)
            mock_slackify.assert_called_once_with(text)
            self.assertEqual(result, "Hello :bold:world:")


class TestSlackChannelConvertTable(TestCase):
    """Tests for SlackChannel._convert_table()."""

    def test_convert_table_basic(self) -> None:
        """Test basic table conversion."""
        table = "| Header 1 | Header 2 |\n|----------|----------|\n| Cell 1   | Cell 2   |"
        match = MagicMock()
        match.group.return_value = table

        result = SlackChannel._convert_table(match)
        expected = "**Header 1**: Cell 1 · **Header 2**: Cell 2"
        self.assertEqual(result, expected)

    def test_convert_table_minimal(self) -> None:
        """Test table with minimal content."""
        table = "| A | B |\n|---|---|\n| 1 | 2 |"
        match = MagicMock()
        match.group.return_value = table

        result = SlackChannel._convert_table(match)
        expected = "**A**: 1 · **B**: 2"
        self.assertEqual(result, expected)

    def test_convert_table_single_row(self) -> None:
        """Test table with single data row."""
        table = "| Name | Value |\n|------|-------|\n| Test | 123   |"
        match = MagicMock()
        match.group.return_value = table

        result = SlackChannel._convert_table(match)
        expected = "**Name**: Test · **Value**: 123"
        self.assertEqual(result, expected)

    def test_convert_table_insufficient_rows(self) -> None:
        """Test table with insufficient rows."""
        table = "| Header 1 |"
        match = MagicMock()
        match.group.return_value = table

        result = SlackChannel._convert_table(match)
        self.assertEqual(result, table)

    def test_convert_table_missing_cells(self) -> None:
        """Test table with missing cells."""
        table = "| A | B | C |\n|---|---|---|\n| 1 |     | 3 |"
        match = MagicMock()
        match.group.return_value = table

        result = SlackChannel._convert_table(match)
        expected = "**A**: 1 · **C**: 3"
        self.assertEqual(result, expected)


class TestSlackChannelOnSocketRequest(IsolatedAsyncioTestCase):
    """Tests for SlackChannel._on_socket_request()."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.config = MagicMock()
        self.config.bot_token = "xoxb-test-token"
        self.config.app_token = "xapp-test-token"
        self.config.mode = "socket"
        self.config.group_policy = "mention"
        self.config.group_allow_from = []
        self.config.dm.enabled = True
        self.config.dm.policy = "open"
        self.config.dm.allow_from = []
        self.config.reply_in_thread = True
        self.config.react_emoji = "eyes"

        self.bus = MagicMock()
        self.channel = SlackChannel(self.config, self.bus)
        self.channel._bot_user_id = "U123"
        self.channel._handle_message = AsyncMock(return_value=None)

        # Mock clients
        self.mock_socket_client = AsyncMock()
        self.mock_web_client = AsyncMock()
        self.channel._socket_client = self.mock_socket_client
        self.channel._web_client = self.mock_web_client

        # Set up mock response object
        self.mock_response = MagicMock()
        self.mock_response.envelope_id = "env123"
        self.mock_socket_client.send_socket_mode_response = AsyncMock()

    async def test_on_socket_request_non_events_api(self) -> None:
        """Test request with non-events_api type - should return early."""
        req = MagicMock()
        req.type = "slash_commands"
        req.envelope_id = "env123"

        await self.channel._on_socket_request(self.mock_socket_client, req)

        self.mock_socket_client.send_socket_mode_response.assert_not_called()
        self.channel._handle_message.assert_not_called()

    async def test_on_socket_request_events_api_message(self) -> None:
        """Test events_api message event."""
        req = MagicMock()
        req.type = "events_api"
        req.envelope_id = "env123"
        req.payload = {
            "event": {
                "type": "message",
                "user": "U456",
                "channel": "C123",
                "channel_type": "channel",
                "text": "hello",
                "ts": "1234567890.123456",
            }
        }

        self.channel._is_allowed = MagicMock(return_value=True)
        self.channel._should_respond_in_channel = MagicMock(return_value=True)

        await self.channel._on_socket_request(self.mock_socket_client, req)

        # Verify response sent
        self.mock_socket_client.send_socket_mode_response.assert_called_once()

        # Verify message handling
        self.channel._handle_message.assert_called_once()
        call_kwargs = self.channel._handle_message.call_args[1]
        self.assertEqual(call_kwargs["content"], "hello")
        self.assertEqual(call_kwargs["sender_id"], "U456")
        self.assertEqual(call_kwargs["chat_id"], "C123")

    async def test_on_socket_request_events_api_app_mention(self) -> None:
        """Test events_api app_mention event."""
        req = MagicMock()
        req.type = "events_api"
        req.envelope_id = "env123"
        req.payload = {
            "event": {
                "type": "app_mention",
                "user": "U456",
                "channel": "C123",
                "channel_type": "channel",
                "text": "<@U123> hello",
                "ts": "1234567890.123456",
            }
        }

        self.channel._is_allowed = MagicMock(return_value=True)
        self.channel._should_respond_in_channel = MagicMock(return_value=True)

        await self.channel._on_socket_request(self.mock_socket_client, req)

        # Verify message handling with stripped content
        self.channel._handle_message.assert_called_once()
        call_kwargs = self.channel._handle_message.call_args[1]
        self.assertEqual(call_kwargs["content"], "hello")

    async def test_on_socket_request_message_with_bot_mention_skip(self) -> None:
        """Test that message events with bot mention are skipped (prefer app_mention)."""
        req = MagicMock()
        req.type = "events_api"
        req.envelope_id = "env123"
        req.payload = {
            "event": {
                "type": "message",
                "user": "U456",
                "channel": "C123",
                "channel_type": "channel",
                "text": "<@U123> hello",
                "ts": "1234567890.123456",
            }
        }

        # This should be skipped since app_mention would handle it
        self.channel._is_allowed = MagicMock(return_value=True)
        self.channel._should_respond_in_channel = MagicMock(return_value=True)

        await self.channel._on_socket_request(self.mock_socket_client, req)

        # Message event with bot mention should be skipped
        self.channel._handle_message.assert_not_called()

    async def test_on_socket_request_bot_message_skipped(self) -> None:
        """Test that bot/system messages are skipped."""
        req = MagicMock()
        req.type = "events_api"
        req.envelope_id = "env123"
        req.payload = {
            "event": {
                "type": "message",
                "user": "U123",  # Same as bot user ID
                "channel": "C123",
                "channel_type": "channel",
                "text": "hello",
                "ts": "1234567890.123456",
            }
        }

        await self.channel._on_socket_request(self.mock_socket_client, req)

        self.channel._handle_message.assert_not_called()

    async def test_on_socket_request_message_subtype_skipped(self) -> None:
        """Test that messages with subtype are skipped."""
        req = MagicMock()
        req.type = "events_api"
        req.envelope_id = "env123"
        req.payload = {
            "event": {
                "type": "message",
                "user": "U456",
                "channel": "C123",
                "channel_type": "channel",
                "text": "hello",
                "subtype": "bot_message",
                "ts": "1234567890.123456",
            }
        }

        await self.channel._on_socket_request(self.mock_socket_client, req)

        self.channel._handle_message.assert_not_called()

    async def test_on_socket_request_missing_sender_or_channel(self) -> None:
        """Test event with missing sender or channel - should return early."""
        req = MagicMock()
        req.type = "events_api"
        req.envelope_id = "env123"
        req.payload = {
            "event": {
                "type": "message",
                "text": "hello",
            }
        }

        await self.channel._on_socket_request(self.mock_socket_client, req)

        # The function should still send response for events_api type
        # but not call _handle_message
        self.mock_socket_client.send_socket_mode_response.assert_called_once()
        self.channel._handle_message.assert_not_called()

    async def test_on_socket_request_not_allowed_sender(self) -> None:
        """Test event from non-allowed sender."""
        req = MagicMock()
        req.type = "events_api"
        req.envelope_id = "env123"
        req.payload = {
            "event": {
                "type": "message",
                "user": "U456",
                "channel": "C123",
                "channel_type": "channel",
                "text": "hello",
                "ts": "1234567890.123456",
            }
        }

        self.channel._is_allowed = MagicMock(return_value=False)

        await self.channel._on_socket_request(self.mock_socket_client, req)

        self.channel._handle_message.assert_not_called()

    async def test_on_socket_request_not_respond_in_channel(self) -> None:
        """Test event where bot should not respond in channel."""
        req = MagicMock()
        req.type = "events_api"
        req.envelope_id = "env123"
        req.payload = {
            "event": {
                "type": "message",
                "user": "U456",
                "channel": "C123",
                "channel_type": "channel",
                "text": "hello",
                "ts": "1234567890.123456",
            }
        }

        self.channel._is_allowed = MagicMock(return_value=True)
        self.channel._should_respond_in_channel = MagicMock(return_value=False)

        await self.channel._on_socket_request(self.mock_socket_client, req)

        self.channel._handle_message.assert_not_called()

    async def test_on_socket_request_adds_reaction(self) -> None:
        """Test that reaction is added to triggering message."""
        req = MagicMock()
        req.type = "events_api"
        req.envelope_id = "env123"
        req.payload = {
            "event": {
                "type": "message",
                "user": "U456",
                "channel": "C123",
                "channel_type": "channel",
                "text": "hello",
                "ts": "1234567890.123456",
            }
        }

        self.channel._is_allowed = MagicMock(return_value=True)
        self.channel._should_respond_in_channel = MagicMock(return_value=True)

        await self.channel._on_socket_request(self.mock_socket_client, req)

        # Verify reaction was added
        self.mock_web_client.reactions_add.assert_called_once()
        call_kwargs = self.mock_web_client.reactions_add.call_args[1]
        self.assertEqual(call_kwargs["channel"], "C123")
        self.assertEqual(call_kwargs["name"], "eyes")
        self.assertEqual(call_kwargs["timestamp"], "1234567890.123456")

    async def test_on_socket_request_dm_channel(self) -> None:
        """Test event in DM channel."""
        req = MagicMock()
        req.type = "events_api"
        req.envelope_id = "env123"
        req.payload = {
            "event": {
                "type": "message",
                "user": "U456",
                "channel": "D123",
                "channel_type": "im",
                "text": "hello",
                "ts": "1234567890.123456",
            }
        }

        self.channel._is_allowed = MagicMock(return_value=True)

        await self.channel._on_socket_request(self.mock_socket_client, req)

        self.channel._handle_message.assert_called_once()
        call_kwargs = self.channel._handle_message.call_args[1]
        self.assertEqual(call_kwargs["content"], "hello")
        self.assertEqual(call_kwargs["chat_id"], "D123")


class TestSlackChannelSendMessage(IsolatedAsyncioTestCase):
    """Tests for SlackChannel.send()."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.config = MagicMock()
        self.config.bot_token = "xoxb-test-token"
        self.config.app_token = "xapp-test-token"
        self.config.mode = "socket"
        self.config.group_policy = "mention"
        self.config.group_allow_from = []
        self.config.dm.enabled = True
        self.config.dm.policy = "open"
        self.config.dm.allow_from = []
        self.config.reply_in_thread = True
        self.config.react_emoji = "eyes"

        self.bus = MagicMock()
        self.channel = SlackChannel(self.config, self.bus)
        self.channel._bot_user_id = "U123"

        # Mock web client
        self.mock_web_client = MagicMock()
        self.channel._web_client = self.mock_web_client

        # Import after mocks are set up
        from nanobot.bus.events import OutboundMessage
        self.msg = OutboundMessage(
            channel="slack",
            chat_id="C123",
            content="Hello **world**",
        )

    async def test_send_message_basic(self) -> None:
        """Test basic message sending."""
        self.mock_web_client.chat_postMessage = AsyncMock()

        with patch("nanobot.channels.slack.slackify_markdown") as mock_slackify:
            mock_slackify.return_value = "mocked mrkdwn"
            await self.channel.send(self.msg)

            self.mock_web_client.chat_postMessage.assert_called_once()
            call_kwargs = self.mock_web_client.chat_postMessage.call_args[1]
            self.assertEqual(call_kwargs["channel"], "C123")
            self.assertEqual(call_kwargs["text"], "mocked mrkdwn")

    async def test_send_message_with_thread(self) -> None:
        """Test message sending in thread."""
        self.msg.metadata = {
            "slack": {
                "thread_ts": "1234567890.123456",
                "channel_type": "channel",
            }
        }

        self.mock_web_client.chat_postMessage = AsyncMock()

        await self.channel.send(self.msg)

        self.mock_web_client.chat_postMessage.assert_called_once()
        call_kwargs = self.mock_web_client.chat_postMessage.call_args[1]
        self.assertEqual(call_kwargs["thread_ts"], "1234567890.123456")

    async def test_send_message_with_media(self) -> None:
        """Test message sending with media file."""
        self.msg.media = ["/path/to/image.png"]

        self.mock_web_client.chat_postMessage = AsyncMock()
        self.mock_web_client.files_upload_v2 = AsyncMock()

        await self.channel.send(self.msg)

        self.mock_web_client.files_upload_v2.assert_called_once()
        call_kwargs = self.mock_web_client.files_upload_v2.call_args[1]
        self.assertEqual(call_kwargs["channel"], "C123")
        self.assertEqual(call_kwargs["file"], "/path/to/image.png")

    async def test_send_message_no_web_client(self) -> None:
        """Test sending message when web client is not initialized."""
        self.channel._web_client = None

        await self.channel.send(self.msg)

        self.mock_web_client.chat_postMessage.assert_not_called()

    async def test_send_message_file_upload_error(self) -> None:
        """Test file upload error handling."""
        self.msg.media = ["/path/to/image.png"]

        self.mock_web_client.chat_postMessage = AsyncMock()
        self.mock_web_client.files_upload_v2 = AsyncMock(side_effect=Exception("Upload failed"))

        await self.channel.send(self.msg)

        self.mock_web_client.files_upload_v2.assert_called_once()

    async def test_send_message_chat_post_error(self) -> None:
        """Test chat_postMessage error handling."""
        self.mock_web_client.chat_postMessage = AsyncMock(side_effect=Exception("Send failed"))

        await self.channel.send(self.msg)

        self.mock_web_client.chat_postMessage.assert_called_once()


class TestSlackChannelStartStop(IsolatedAsyncioTestCase):
    """Tests for SlackChannel.start() and stop()."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.config = MagicMock()
        self.config.bot_token = "xoxb-test-token"
        self.config.app_token = "xapp-test-token"
        self.config.mode = "socket"
        self.config.group_policy = "mention"
        self.config.group_allow_from = []
        self.config.dm.enabled = True
        self.config.dm.policy = "open"
        self.config.dm.allow_from = []
        self.config.reply_in_thread = True
        self.config.react_emoji = "eyes"

        self.bus = MagicMock()
        self.channel = SlackChannel(self.config, self.bus)

    async def test_start_missing_tokens(self) -> None:
        """Test start when bot/app token is missing."""
        self.config.bot_token = ""
        self.config.app_token = ""

        await self.channel.start()

        self.assertFalse(self.channel.is_running)

    async def test_start_invalid_mode(self) -> None:
        """Test start with unsupported mode."""
        self.config.mode = "webhook"

        await self.channel.start()

        self.assertFalse(self.channel.is_running)

    async def test_start_success(self) -> None:
        """Test successful start of Socket Mode client."""
        self.config.bot_token = "xoxb-test-token"
        self.config.app_token = "xapp-test-token"
        self.config.mode = "socket"

        mock_web_client = MagicMock()
        mock_web_client.auth_test = AsyncMock(
            return_value={"user_id": "U123", "bot_id": "B123"},
        )

        mock_socket_client = MagicMock()
        mock_socket_client.connect = AsyncMock()
        mock_socket_client.close = AsyncMock()
        mock_socket_client.socket_mode_request_listeners = []

        # Patch AsyncWebClient and SocketModeClient to avoid real connections
        with patch("nanobot.channels.slack.AsyncWebClient", return_value=mock_web_client), patch("nanobot.channels.slack.SocketModeClient", return_value=mock_socket_client):
                # Patch asyncio.sleep to break out of the loop after one iteration
                async def stop_loop(*args, **kwargs) -> None:
                    self.channel._running = False

                with patch("asyncio.sleep", new=stop_loop):
                    await self.channel.start()

                    # Verify the channel was properly initialized during start
                    # Note: _running becomes False after the loop exits, but other state remains
                    self.assertEqual(self.channel._bot_user_id, "U123")
                    self.assertEqual(len(mock_socket_client.socket_mode_request_listeners), 1)

    async def test_stop_success(self) -> None:
        """Test successful stop of Socket Mode client."""
        mock_socket_client = MagicMock()
        mock_socket_client.close = AsyncMock()
        self.channel._socket_client = mock_socket_client
        self.channel._running = True

        await self.channel.stop()

        self.assertFalse(self.channel.is_running)
        self.assertIsNone(self.channel._socket_client)


if __name__ == "__main__":
    import unittest
    unittest.main()
