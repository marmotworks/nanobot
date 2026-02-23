"""Unit tests for Discord channel expressive reaction triggers."""

import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from nanobot.channels.discord import DiscordChannel


class TestDiscordExpressiveTriggers(unittest.TestCase):
    """Tests for expressive reaction triggers in DiscordChannel."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.config = MagicMock()
        self.bus = MagicMock()
        self.channel = DiscordChannel(self.config, self.bus)

    async def _create_payload(self, content: str) -> dict[str, str | list | None]:
        """Create a synthetic Discord message payload."""
        return {
            "id": "123456789",
            "channel_id": "987654321",
            "author": {"id": "111", "username": "testuser", "bot": False},
            "content": content,
            "attachments": [],
            "referenced_message": None,
        }

    @patch.object(DiscordChannel, "_react_to_message", new_callable=AsyncMock)
    @patch.object(DiscordChannel, "_handle_message", new_callable=AsyncMock)
    @patch.object(DiscordChannel, "_start_typing", new_callable=AsyncMock)
    async def test_expressive_trigger_thanks(
        self,
        mock_start_typing: AsyncMock,
        mock_handle_message: AsyncMock,
        mock_react_to_message: AsyncMock,
    ) -> None:
        """When a message contains 'thanks', _react_to_message is called with the 👀 emoji."""
        payload = await self._create_payload("thanks for the help")
        await self.channel._handle_message_create(payload)

        mock_react_to_message.assert_called_once_with("987654321", "123456789", "👀")

    @patch.object(DiscordChannel, "_react_to_message", new_callable=AsyncMock)
    @patch.object(DiscordChannel, "_handle_message", new_callable=AsyncMock)
    @patch.object(DiscordChannel, "_start_typing", new_callable=AsyncMock)
    async def test_expressive_trigger_bug(
        self,
        mock_start_typing: AsyncMock,
        mock_handle_message: AsyncMock,
        mock_react_to_message: AsyncMock,
    ) -> None:
        """When a message contains 'bug', _react_to_message is called with the 🐛 emoji."""
        payload = await self._create_payload("there is a bug in the code")
        await self.channel._handle_message_create(payload)

        mock_react_to_message.assert_called_once_with("987654321", "123456789", "🐛")

    @patch.object(DiscordChannel, "_react_to_message", new_callable=AsyncMock)
    @patch.object(DiscordChannel, "_handle_message", new_callable=AsyncMock)
    @patch.object(DiscordChannel, "_start_typing", new_callable=AsyncMock)
    async def test_expressive_no_trigger(
        self,
        mock_start_typing: AsyncMock,
        mock_handle_message: AsyncMock,
        mock_react_to_message: AsyncMock,
    ) -> None:
        """When a message contains no trigger keywords, _react_to_message is NOT called."""
        payload = await self._create_payload("hello world")
        await self.channel._handle_message_create(payload)

        mock_react_to_message.assert_not_called()

    @patch.object(DiscordChannel, "_react_to_message", new_callable=AsyncMock)
    @patch.object(DiscordChannel, "_handle_message", new_callable=AsyncMock)
    @patch.object(DiscordChannel, "_start_typing", new_callable=AsyncMock)
    async def test_expressive_first_match_only(
        self,
        mock_start_typing: AsyncMock,
        mock_handle_message: AsyncMock,
        mock_react_to_message: AsyncMock,
    ) -> None:
        """When a message contains multiple trigger keywords, only the first matching trigger fires."""
        payload = await self._create_payload("thanks for the bug fix")
        await self.channel._handle_message_create(payload)

        mock_react_to_message.assert_called_once()
        mock_react_to_message.assert_called_once_with("987654321", "123456789", "👀")


class TestDiscordInteractiveReactions(unittest.IsolatedAsyncioTestCase):
    """Tests for interactive reaction handling in DiscordChannel._handle_reaction_add()."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.config = MagicMock()
        self.bus = MagicMock()
        self.channel = DiscordChannel(self.config, self.bus)

    async def test_interactive_reaction_thumbs_up(self) -> None:
        """When a 👍 emoji reaction is added by a non-bot user, logger.info is called with 'approve'."""
        payload = {
            "member": {"user": {"bot": False, "id": "111"}},
            "emoji": {"name": "👍", "id": None},
            "user_id": "111",
            "channel_id": "987654321",
            "message_id": "123456789",
        }

        with patch("nanobot.channels.discord.logger") as mock_logger:
            await self.channel._handle_reaction_add(payload)
            mock_logger.info.assert_called_once_with("Interactive reaction: {} → {}", "👍", "approve")

    async def test_interactive_reaction_unknown_emoji(self) -> None:
        """When a reaction with an unknown emoji is added, logger.info is NOT called."""
        payload = {
            "member": {"user": {"bot": False, "id": "111"}},
            "emoji": {"name": "🎉", "id": None},
            "user_id": "111",
            "channel_id": "987654321",
            "message_id": "123456789",
        }

        with patch("nanobot.channels.discord.logger") as mock_logger:
            await self.channel._handle_reaction_add(payload)
            mock_logger.info.assert_not_called()

    async def test_interactive_reaction_bot_ignored(self) -> None:
        """When a bot adds a 👍 reaction, logger.info is NOT called."""
        payload = {
            "member": {"user": {"bot": True, "id": "222"}},
            "emoji": {"name": "👍", "id": None},
            "user_id": "222",
            "channel_id": "987654321",
            "message_id": "123456789",
        }

        with patch("nanobot.channels.discord.logger") as mock_logger:
            await self.channel._handle_reaction_add(payload)
            mock_logger.info.assert_not_called()


if __name__ == "__main__":
    unittest.main()
