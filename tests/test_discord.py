"""Unit tests for Discord channel."""

from __future__ import annotations

import asyncio
import contextlib
import json
from pathlib import Path as RealPath
import tempfile
import unittest
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, MagicMock, patch

from nanobot.bus.events import OutboundMessage
from nanobot.channels.discord import DiscordChannel, _split_message

# ---------------------------------------------------------------------------
# Pure function tests
# ---------------------------------------------------------------------------


class TestSplitMessage(unittest.TestCase):
    """Tests for _split_message()."""

    def test_empty_string(self) -> None:
        self.assertEqual(_split_message(""), [])

    def test_short_message_unchanged(self) -> None:
        self.assertEqual(_split_message("hello"), ["hello"])

    def test_exact_max_len(self) -> None:
        msg = "x" * 2000
        self.assertEqual(_split_message(msg), [msg])

    def test_splits_at_newline(self) -> None:
        part1 = "a" * 1990
        part2 = "b" * 100
        msg = part1 + "\n" + part2
        chunks = _split_message(msg)
        self.assertEqual(len(chunks), 2)
        self.assertEqual(chunks[0], part1)
        self.assertEqual(chunks[1], part2)

    def test_splits_at_space_when_no_newline(self) -> None:
        part1 = "a" * 1990
        part2 = "b" * 100
        msg = part1 + " " + part2
        chunks = _split_message(msg)
        self.assertEqual(len(chunks), 2)

    def test_hard_split_when_no_whitespace(self) -> None:
        msg = "x" * 4000
        chunks = _split_message(msg)
        self.assertGreater(len(chunks), 1)
        for chunk in chunks:
            self.assertLessEqual(len(chunk), 2000)

    def test_custom_max_len(self) -> None:
        chunks = _split_message("hello world", max_len=5)
        self.assertGreater(len(chunks), 1)


# ---------------------------------------------------------------------------
# Initialization tests
# ---------------------------------------------------------------------------


class TestDiscordChannelInit(unittest.TestCase):
    """Tests for DiscordChannel.__init__()."""

    def test_init_stores_config(self) -> None:
        config = MagicMock()
        bus = MagicMock()
        channel = DiscordChannel(config, bus)
        self.assertIs(channel.config, config)
        self.assertIsNone(channel._ws)
        self.assertIsNone(channel._seq)
        self.assertIsNone(channel._heartbeat_task)
        self.assertEqual(channel._typing_tasks, {})
        self.assertIsNone(channel._http)


# ---------------------------------------------------------------------------
# start() / stop() tests
# ---------------------------------------------------------------------------


class TestDiscordChannelStartStop(IsolatedAsyncioTestCase):
    """Tests for start() and stop()."""

    def setUp(self) -> None:
        self.config = MagicMock()
        self.config.token = "test-token"
        self.config.gateway_url = "wss://gateway.discord.gg"
        self.config.intents = 512
        self.bus = MagicMock()
        self.channel = DiscordChannel(self.config, self.bus)

    async def test_start_returns_early_when_no_token(self) -> None:
        self.config.token = None
        await self.channel.start()
        self.assertFalse(self.channel._running)

    async def test_stop_clears_state(self) -> None:
        mock_ws = AsyncMock()
        mock_http = AsyncMock()
        mock_task = MagicMock()
        mock_task.cancel = MagicMock()

        self.channel._running = True
        self.channel._ws = mock_ws
        self.channel._http = mock_http
        self.channel._heartbeat_task = mock_task
        self.channel._typing_tasks = {"ch1": mock_task}

        await self.channel.stop()

        self.assertFalse(self.channel._running)
        mock_ws.close.assert_awaited_once()
        mock_http.aclose.assert_awaited_once()
        mock_task.cancel.assert_called()
        self.assertIsNone(self.channel._ws)
        self.assertIsNone(self.channel._http)
        self.assertEqual(self.channel._typing_tasks, {})

    async def test_stop_when_nothing_initialized(self) -> None:
        """stop() should not raise when ws/http are None."""
        self.channel._running = True
        await self.channel.stop()
        self.assertFalse(self.channel._running)


# ---------------------------------------------------------------------------
# send() tests
# ---------------------------------------------------------------------------


class TestDiscordChannelSend(IsolatedAsyncioTestCase):
    """Tests for send()."""

    def setUp(self) -> None:
        self.config = MagicMock()
        self.config.token = "test-token"
        self.bus = MagicMock()
        self.channel = DiscordChannel(self.config, self.bus)
        self.channel._running = True

    async def test_send_returns_early_when_no_http(self) -> None:
        self.channel._http = None
        msg = OutboundMessage(channel="discord", chat_id="123", content="hello")
        await self.channel.send(msg)  # should not raise

    async def test_send_basic_message(self) -> None:
        mock_http = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_http.post = AsyncMock(return_value=mock_response)
        self.channel._http = mock_http

        with patch.object(self.channel, "_stop_typing", new_callable=AsyncMock):
            msg = OutboundMessage(channel="discord", chat_id="123", content="hello")
            await self.channel.send(msg)

        mock_http.post.assert_called()
        call_kwargs = mock_http.post.call_args[1]
        self.assertEqual(call_kwargs["json"]["content"], "hello")

    async def test_send_with_reply_to(self) -> None:
        mock_http = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_http.post = AsyncMock(return_value=mock_response)
        self.channel._http = mock_http

        with patch.object(self.channel, "_stop_typing", new_callable=AsyncMock):
            msg = OutboundMessage(channel="discord", chat_id="123", content="hello", reply_to="456")
            await self.channel.send(msg)

        call_kwargs = mock_http.post.call_args[1]
        self.assertIn("message_reference", call_kwargs["json"])
        self.assertEqual(call_kwargs["json"]["message_reference"]["message_id"], "456")

    async def test_send_empty_content_skips(self) -> None:
        mock_http = AsyncMock()
        self.channel._http = mock_http

        with patch.object(self.channel, "_stop_typing", new_callable=AsyncMock):
            msg = OutboundMessage(channel="discord", chat_id="123", content="")
            await self.channel.send(msg)

        mock_http.post.assert_not_called()

    async def test_send_long_message_splits(self) -> None:
        mock_http = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_http.post = AsyncMock(return_value=mock_response)
        self.channel._http = mock_http

        long_content = "word " * 600  # well over 2000 chars
        with patch.object(self.channel, "_stop_typing", new_callable=AsyncMock):
            msg = OutboundMessage(channel="discord", chat_id="123", content=long_content)
            await self.channel.send(msg)

        self.assertGreater(mock_http.post.call_count, 1)

    async def test_send_rate_limit_retries(self) -> None:
        mock_http = AsyncMock()
        rate_limited = MagicMock()
        rate_limited.status_code = 429
        rate_limited.json = MagicMock(return_value={"retry_after": 0.01})

        success = MagicMock()
        success.status_code = 200
        success.raise_for_status = MagicMock()

        mock_http.post = AsyncMock(side_effect=[rate_limited, success])
        self.channel._http = mock_http

        with patch.object(self.channel, "_stop_typing", new_callable=AsyncMock):
            msg = OutboundMessage(channel="discord", chat_id="123", content="hello")
            await self.channel.send(msg)

        self.assertEqual(mock_http.post.call_count, 2)


# ---------------------------------------------------------------------------
# _handle_message_create() tests
# ---------------------------------------------------------------------------


class TestDiscordHandleMessageCreate(IsolatedAsyncioTestCase):
    """Tests for _handle_message_create()."""

    def setUp(self) -> None:
        self.config = MagicMock()
        self.config.token = "test-token"
        self.bus = MagicMock()
        self.channel = DiscordChannel(self.config, self.bus)
        self.channel.is_allowed = MagicMock(return_value=True)

    def _payload(self, content: str = "hello", bot: bool = False) -> dict:
        return {
            "id": "msg1",
            "channel_id": "ch1",
            "author": {"id": "user1", "bot": bot},
            "content": content,
            "attachments": [],
            "referenced_message": None,
        }

    @patch.object(DiscordChannel, "_react_to_message", new_callable=AsyncMock)
    @patch.object(DiscordChannel, "_handle_message", new_callable=AsyncMock)
    @patch.object(DiscordChannel, "_start_typing", new_callable=AsyncMock)
    async def test_bot_messages_ignored(
        self,
        mock_typing: AsyncMock,
        mock_handle: AsyncMock,
        mock_react: AsyncMock,
    ) -> None:
        await self.channel._handle_message_create(self._payload(bot=True))
        mock_handle.assert_not_called()

    @patch.object(DiscordChannel, "_react_to_message", new_callable=AsyncMock)
    @patch.object(DiscordChannel, "_handle_message", new_callable=AsyncMock)
    @patch.object(DiscordChannel, "_start_typing", new_callable=AsyncMock)
    async def test_disallowed_sender_ignored(
        self,
        mock_typing: AsyncMock,
        mock_handle: AsyncMock,
        mock_react: AsyncMock,
    ) -> None:
        self.channel.is_allowed = MagicMock(return_value=False)
        await self.channel._handle_message_create(self._payload())
        mock_handle.assert_not_called()

    @patch.object(DiscordChannel, "_react_to_message", new_callable=AsyncMock)
    @patch.object(DiscordChannel, "_handle_message", new_callable=AsyncMock)
    @patch.object(DiscordChannel, "_start_typing", new_callable=AsyncMock)
    async def test_normal_message_dispatched(
        self,
        mock_typing: AsyncMock,
        mock_handle: AsyncMock,
        mock_react: AsyncMock,
    ) -> None:
        await self.channel._handle_message_create(self._payload("hello"))
        mock_handle.assert_awaited_once()
        call_kwargs = mock_handle.call_args[1]
        self.assertEqual(call_kwargs["content"], "hello")
        self.assertEqual(call_kwargs["chat_id"], "ch1")

    @patch.object(DiscordChannel, "_react_to_message", new_callable=AsyncMock)
    @patch.object(DiscordChannel, "_handle_message", new_callable=AsyncMock)
    @patch.object(DiscordChannel, "_start_typing", new_callable=AsyncMock)
    async def test_empty_content_becomes_placeholder(
        self,
        mock_typing: AsyncMock,
        mock_handle: AsyncMock,
        mock_react: AsyncMock,
    ) -> None:
        await self.channel._handle_message_create(self._payload(""))
        call_kwargs = mock_handle.call_args[1]
        self.assertEqual(call_kwargs["content"], "[empty message]")

    @patch.object(DiscordChannel, "_react_to_message", new_callable=AsyncMock)
    @patch.object(DiscordChannel, "_handle_message", new_callable=AsyncMock)
    @patch.object(DiscordChannel, "_start_typing", new_callable=AsyncMock)
    async def test_reply_to_extracted(
        self,
        mock_typing: AsyncMock,
        mock_handle: AsyncMock,
        mock_react: AsyncMock,
    ) -> None:
        payload = self._payload("reply")
        payload["referenced_message"] = {"id": "orig123"}
        await self.channel._handle_message_create(payload)
        call_kwargs = mock_handle.call_args[1]
        self.assertEqual(call_kwargs["metadata"]["reply_to"], "orig123")

    @patch.object(DiscordChannel, "_react_to_message", new_callable=AsyncMock)
    @patch.object(DiscordChannel, "_handle_message", new_callable=AsyncMock)
    @patch.object(DiscordChannel, "_start_typing", new_callable=AsyncMock)
    async def test_attachment_too_large_noted(
        self,
        mock_typing: AsyncMock,
        mock_handle: AsyncMock,
        mock_react: AsyncMock,
    ) -> None:
        payload = self._payload("")
        payload["attachments"] = [
            {"url": "http://x.com/f", "filename": "big.bin", "size": 30 * 1024 * 1024, "id": "a1"}
        ]
        self.channel._http = AsyncMock()
        await self.channel._handle_message_create(payload)
        call_kwargs = mock_handle.call_args[1]
        self.assertIn("too large", call_kwargs["content"])

    @patch.object(DiscordChannel, "_react_to_message", new_callable=AsyncMock)
    @patch.object(DiscordChannel, "_handle_message", new_callable=AsyncMock)
    @patch.object(DiscordChannel, "_start_typing", new_callable=AsyncMock)
    async def test_attachment_download_success(
        self,
        mock_typing: AsyncMock,
        mock_handle: AsyncMock,
        mock_react: AsyncMock,
    ) -> None:
        payload = self._payload("")
        payload["attachments"] = [
            {"url": "http://x.com/f.txt", "filename": "f.txt", "size": 100, "id": "a2"}
        ]
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.content = b"hello"
        mock_http = AsyncMock()
        mock_http.get = AsyncMock(return_value=mock_resp)
        self.channel._http = mock_http

        with tempfile.TemporaryDirectory() as tmp_dir, patch(
            "nanobot.channels.discord.Path.home", return_value=RealPath(tmp_dir)
        ):
            await self.channel._handle_message_create(payload)

        call_kwargs = mock_handle.call_args[1]
        self.assertTrue(len(call_kwargs["media"]) > 0)


# ---------------------------------------------------------------------------
# Expressive trigger tests
# ---------------------------------------------------------------------------


class TestDiscordExpressiveTriggers(IsolatedAsyncioTestCase):
    """Tests for expressive reaction triggers."""

    def setUp(self) -> None:
        self.config = MagicMock()
        self.bus = MagicMock()
        self.channel = DiscordChannel(self.config, self.bus)
        self.channel.is_allowed = MagicMock(return_value=True)

    def _payload(self, content: str) -> dict:
        return {
            "id": "123456789",
            "channel_id": "987654321",
            "author": {"id": "111", "bot": False},
            "content": content,
            "attachments": [],
            "referenced_message": None,
        }

    @patch.object(DiscordChannel, "_react_to_message", new_callable=AsyncMock)
    @patch.object(DiscordChannel, "_handle_message", new_callable=AsyncMock)
    @patch.object(DiscordChannel, "_start_typing", new_callable=AsyncMock)
    async def test_expressive_trigger_thanks(
        self, mock_typing: AsyncMock, mock_handle: AsyncMock, mock_react: AsyncMock
    ) -> None:
        await self.channel._handle_message_create(self._payload("thanks for the help"))
        mock_react.assert_called_once_with("987654321", "123456789", "👀")

    @patch.object(DiscordChannel, "_react_to_message", new_callable=AsyncMock)
    @patch.object(DiscordChannel, "_handle_message", new_callable=AsyncMock)
    @patch.object(DiscordChannel, "_start_typing", new_callable=AsyncMock)
    async def test_expressive_trigger_bug(
        self, mock_typing: AsyncMock, mock_handle: AsyncMock, mock_react: AsyncMock
    ) -> None:
        await self.channel._handle_message_create(self._payload("there is a bug in the code"))
        mock_react.assert_called_once_with("987654321", "123456789", "🐛")

    @patch.object(DiscordChannel, "_react_to_message", new_callable=AsyncMock)
    @patch.object(DiscordChannel, "_handle_message", new_callable=AsyncMock)
    @patch.object(DiscordChannel, "_start_typing", new_callable=AsyncMock)
    async def test_no_trigger(
        self, mock_typing: AsyncMock, mock_handle: AsyncMock, mock_react: AsyncMock
    ) -> None:
        await self.channel._handle_message_create(self._payload("hello world"))
        mock_react.assert_not_called()

    @patch.object(DiscordChannel, "_react_to_message", new_callable=AsyncMock)
    @patch.object(DiscordChannel, "_handle_message", new_callable=AsyncMock)
    @patch.object(DiscordChannel, "_start_typing", new_callable=AsyncMock)
    async def test_first_match_only(
        self, mock_typing: AsyncMock, mock_handle: AsyncMock, mock_react: AsyncMock
    ) -> None:
        await self.channel._handle_message_create(self._payload("thanks for the bug fix"))
        mock_react.assert_called_once()
        mock_react.assert_called_once_with("987654321", "123456789", "👀")


# ---------------------------------------------------------------------------
# Interactive reaction tests
# ---------------------------------------------------------------------------


class TestDiscordInteractiveReactions(IsolatedAsyncioTestCase):
    """Tests for _handle_reaction_add()."""

    def setUp(self) -> None:
        self.config = MagicMock()
        self.bus = MagicMock()
        self.channel = DiscordChannel(self.config, self.bus)

    async def test_thumbs_up_logs_approve(self) -> None:
        payload = {
            "member": {"user": {"bot": False, "id": "111"}},
            "emoji": {"name": "👍"},
        }
        with patch("nanobot.channels.discord.logger") as mock_logger:
            await self.channel._handle_reaction_add(payload)
            mock_logger.info.assert_called_once_with(
                "Interactive reaction: {} → {}", "👍", "approve"
            )

    async def test_unknown_emoji_no_log(self) -> None:
        payload = {
            "member": {"user": {"bot": False, "id": "111"}},
            "emoji": {"name": "🎉"},
        }
        with patch("nanobot.channels.discord.logger") as mock_logger:
            await self.channel._handle_reaction_add(payload)
            mock_logger.info.assert_not_called()

    async def test_bot_reaction_ignored(self) -> None:
        payload = {
            "member": {"user": {"bot": True, "id": "222"}},
            "emoji": {"name": "👍"},
        }
        with patch("nanobot.channels.discord.logger") as mock_logger:
            await self.channel._handle_reaction_add(payload)
            mock_logger.info.assert_not_called()


# ---------------------------------------------------------------------------
# _react_to_message() tests
# ---------------------------------------------------------------------------


class TestDiscordReactToMessage(IsolatedAsyncioTestCase):
    """Tests for _react_to_message()."""

    def setUp(self) -> None:
        self.config = MagicMock()
        self.config.token = "test-token"
        self.bus = MagicMock()
        self.channel = DiscordChannel(self.config, self.bus)

    async def test_react_no_http_skips(self) -> None:
        self.channel._http = None
        await self.channel._react_to_message("ch1", "msg1", "👍")  # should not raise

    async def test_react_success(self) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 204
        mock_http = AsyncMock()
        mock_http.put = AsyncMock(return_value=mock_resp)
        self.channel._http = mock_http

        await self.channel._react_to_message("ch1", "msg1", "👍")
        mock_http.put.assert_awaited_once()

    async def test_react_non_204_warns(self) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 403
        mock_http = AsyncMock()
        mock_http.put = AsyncMock(return_value=mock_resp)
        self.channel._http = mock_http

        with patch("nanobot.channels.discord.logger") as mock_logger:
            await self.channel._react_to_message("ch1", "msg1", "👍")
            mock_logger.warning.assert_called()


# ---------------------------------------------------------------------------
# _start_typing / _stop_typing tests
# ---------------------------------------------------------------------------


class TestDiscordTyping(IsolatedAsyncioTestCase):
    """Tests for _start_typing() and _stop_typing()."""

    def setUp(self) -> None:
        self.config = MagicMock()
        self.config.token = "test-token"
        self.bus = MagicMock()
        self.channel = DiscordChannel(self.config, self.bus)
        self.channel._running = True

    async def test_stop_typing_cancels_task(self) -> None:
        mock_task = MagicMock()
        self.channel._typing_tasks["ch1"] = mock_task
        await self.channel._stop_typing("ch1")
        mock_task.cancel.assert_called_once()
        self.assertNotIn("ch1", self.channel._typing_tasks)

    async def test_stop_typing_noop_when_no_task(self) -> None:
        await self.channel._stop_typing("nonexistent")  # should not raise

    async def test_start_typing_creates_task(self) -> None:
        mock_http = AsyncMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 204
        mock_http.post = AsyncMock(return_value=mock_resp)
        self.channel._http = mock_http

        await self.channel._start_typing("ch1")
        self.assertIn("ch1", self.channel._typing_tasks)

        # Clean up
        self.channel._running = False
        await self.channel._stop_typing("ch1")

    async def test_start_typing_replaces_existing(self) -> None:
        old_task = MagicMock()
        self.channel._typing_tasks["ch1"] = old_task

        mock_http = AsyncMock()
        mock_http.post = AsyncMock(return_value=MagicMock(status_code=204))
        self.channel._http = mock_http

        await self.channel._start_typing("ch1")
        old_task.cancel.assert_called_once()

        self.channel._running = False
        await self.channel._stop_typing("ch1")


# ---------------------------------------------------------------------------
# start() / gateway_loop() tests
# ---------------------------------------------------------------------------


class TestDiscordStartGateway(IsolatedAsyncioTestCase):
    """Tests for start() and _gateway_loop()."""

    def setUp(self) -> None:
        self.config = MagicMock()
        self.config.token = "test-token"
        self.config.gateway_url = "wss://gateway.discord.gg"
        self.config.intents = 512
        self.bus = MagicMock()
        self.channel = DiscordChannel(self.config, self.bus)

    async def test_start_connects_to_gateway(self) -> None:
        mock_ws = AsyncMock()
        mock_ws.__aenter__ = AsyncMock(return_value=mock_ws)
        mock_ws.__aexit__ = AsyncMock(return_value=None)
        mock_ws.__aiter__ = MagicMock(return_value=iter([]))  # Empty iterator

        mock_http = AsyncMock()
        mock_http.post = AsyncMock(return_value=MagicMock(status_code=200))

        async def fake_gateway_loop() -> None:
            self.channel._running = False

        with patch("nanobot.channels.discord.websockets.connect") as mock_connect, \
             patch.object(self.channel, "_gateway_loop", side_effect=fake_gateway_loop) as mock_gateway_loop, \
             patch.object(self.channel, "_stop_typing", new_callable=AsyncMock):
            mock_connect.return_value = mock_ws
            self.channel._http = mock_http

            await self.channel.start()

            mock_connect.assert_called_once_with(self.config.gateway_url)
            mock_gateway_loop.assert_called_once()

    async def test_start_reconnects_on_error(self) -> None:
        mock_ws = AsyncMock()
        mock_ws.__aenter__ = AsyncMock(return_value=mock_ws)
        mock_ws.__aexit__ = AsyncMock(return_value=None)
        mock_ws.__aiter__ = MagicMock(return_value=iter([]))

        mock_http = AsyncMock()
        call_count = 0

        # First call raises; second call sets _running=False so loop exits
        async def fake_gateway_loop() -> None:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("Simulated gateway error")
            self.channel._running = False

        async def fake_sleep(_seconds: float) -> None:
            pass  # instant sleep so test doesn't block

        with patch("nanobot.channels.discord.websockets.connect") as mock_connect, \
             patch.object(self.channel, "_gateway_loop", side_effect=fake_gateway_loop) as mock_gateway_loop, \
             patch.object(self.channel, "_stop_typing", new_callable=AsyncMock), \
             patch("nanobot.channels.discord.asyncio.sleep", side_effect=fake_sleep) as mock_sleep:
            mock_connect.return_value = mock_ws
            self.channel._http = mock_http

            await self.channel.start()

            # Should have attempted reconnect (sleep called) and retried gateway_loop
            mock_sleep.assert_called()
            self.assertGreaterEqual(mock_gateway_loop.call_count, 2)


# ---------------------------------------------------------------------------
# _gateway_loop() op code tests
# ---------------------------------------------------------------------------


class TestDiscordGatewayLoop(IsolatedAsyncioTestCase):
    """Tests for _gateway_loop() with different op codes."""

    def setUp(self) -> None:
        self.config = MagicMock()
        self.config.token = "test-token"
        self.bus = MagicMock()
        self.channel = DiscordChannel(self.config, self.bus)
        self.channel._running = True

    def _make_mock_ws(self, messages: list) -> AsyncMock:
        """Create a mock websocket that yields the given messages via async for."""
        mock_ws = AsyncMock()

        async def async_gen():
            for msg in messages:
                yield msg

        mock_ws.__aiter__ = lambda self: async_gen()
        return mock_ws

    async def test_gateway_loop_op10_hello(self) -> None:
        hello_data = {"op": 10, "d": {"heartbeat_interval": 45000}}
        mock_ws = self._make_mock_ws([json.dumps(hello_data).encode()])
        self.channel._ws = mock_ws

        with patch.object(self.channel, "_start_heartbeat", new_callable=AsyncMock) as mock_heartbeat, \
             patch.object(self.channel, "_identify", new_callable=AsyncMock) as mock_identify:
            await self.channel._gateway_loop()

            mock_heartbeat.assert_awaited_once_with(45.0)
            mock_identify.assert_awaited_once()

    async def test_gateway_loop_op0_ready_event(self) -> None:
        ready_data = {"op": 0, "t": "READY", "s": 1, "d": {}}
        mock_ws = self._make_mock_ws([json.dumps(ready_data).encode()])
        self.channel._ws = mock_ws

        with patch.object(self.channel, "_start_heartbeat", new_callable=AsyncMock), \
             patch.object(self.channel, "_identify", new_callable=AsyncMock):
            await self.channel._gateway_loop()  # should not raise

    async def test_gateway_loop_op0_message_create(self) -> None:
        msg_data = {"op": 0, "t": "MESSAGE_CREATE", "s": 2, "d": {"id": "1", "channel_id": "ch1"}}
        mock_ws = self._make_mock_ws([json.dumps(msg_data).encode()])
        self.channel._ws = mock_ws

        with patch.object(self.channel, "_start_heartbeat", new_callable=AsyncMock), \
             patch.object(self.channel, "_identify", new_callable=AsyncMock), \
             patch.object(self.channel, "_handle_message_create", new_callable=AsyncMock) as mock_handle:
            await self.channel._gateway_loop()

            mock_handle.assert_awaited_once_with(msg_data["d"])

    async def test_gateway_loop_op0_reaction_add(self) -> None:
        reaction_data = {
            "op": 0,
            "t": "MESSAGE_REACTION_ADD",
            "s": 3,
            "d": {"emoji": {"name": "👍"}},
        }
        mock_ws = self._make_mock_ws([json.dumps(reaction_data).encode()])
        self.channel._ws = mock_ws

        with patch.object(self.channel, "_start_heartbeat", new_callable=AsyncMock), \
             patch.object(self.channel, "_identify", new_callable=AsyncMock), \
             patch.object(self.channel, "_handle_reaction_add", new_callable=AsyncMock) as mock_handle:
            await self.channel._gateway_loop()

            mock_handle.assert_awaited_once_with(reaction_data["d"])

    async def test_gateway_loop_op7_reconnect(self) -> None:
        reconnect_data = {"op": 7, "s": 4, "d": None}
        mock_ws = self._make_mock_ws([json.dumps(reconnect_data).encode()])
        self.channel._ws = mock_ws

        with patch.object(self.channel, "_start_heartbeat", new_callable=AsyncMock), \
             patch.object(self.channel, "_identify", new_callable=AsyncMock):
            await self.channel._gateway_loop()  # should break out of loop cleanly

    async def test_gateway_loop_op9_invalid_session(self) -> None:
        invalid_data = {"op": 9, "s": 5, "d": None}
        mock_ws = self._make_mock_ws([json.dumps(invalid_data).encode()])
        self.channel._ws = mock_ws

        with patch.object(self.channel, "_start_heartbeat", new_callable=AsyncMock), \
             patch.object(self.channel, "_identify", new_callable=AsyncMock):
            await self.channel._gateway_loop()  # should break out of loop cleanly

    async def test_gateway_loop_invalid_json(self) -> None:
        mock_ws = self._make_mock_ws([b"not json"])
        self.channel._ws = mock_ws

        with patch.object(self.channel, "_start_heartbeat", new_callable=AsyncMock), \
             patch.object(self.channel, "_identify", new_callable=AsyncMock):
            await self.channel._gateway_loop()  # should log warning and continue


# ---------------------------------------------------------------------------
# _identify() tests
# ---------------------------------------------------------------------------


class TestDiscordIdentify(IsolatedAsyncioTestCase):
    """Tests for _identify()."""

    def setUp(self) -> None:
        self.config = MagicMock()
        self.config.token = "test-token"
        self.config.intents = 512
        self.bus = MagicMock()
        self.channel = DiscordChannel(self.config, self.bus)
        self.channel._running = True

    async def test_identify_no_ws_returns(self) -> None:
        self.channel._ws = None
        await self.channel._identify()  # should not raise

    async def test_identify_sends_payload(self) -> None:
        mock_ws = AsyncMock()
        self.channel._ws = mock_ws

        await self.channel._identify()

        mock_ws.send.assert_awaited_once()
        sent_data = json.loads(mock_ws.send.call_args[0][0])
        self.assertEqual(sent_data["op"], 2)
        self.assertEqual(sent_data["d"]["token"], "test-token")
        self.assertEqual(sent_data["d"]["intents"], 512)


# ---------------------------------------------------------------------------
# _start_heartbeat() tests
# ---------------------------------------------------------------------------


class TestDiscordHeartbeat(IsolatedAsyncioTestCase):
    """Tests for _start_heartbeat()."""

    def setUp(self) -> None:
        self.config = MagicMock()
        self.config.token = "test-token"
        self.bus = MagicMock()
        self.channel = DiscordChannel(self.config, self.bus)
        self.channel._running = True

    async def test_heartbeat_replaces_existing_task(self) -> None:
        old_task = MagicMock()
        self.channel._heartbeat_task = old_task

        mock_ws = MagicMock()
        self.channel._ws = mock_ws

        await self.channel._start_heartbeat(45.0)

        old_task.cancel.assert_called_once()
        self.assertIsNotNone(self.channel._heartbeat_task)

    async def test_heartbeat_creates_loop(self) -> None:
        mock_ws = MagicMock()
        mock_ws.send = AsyncMock()
        self.channel._ws = mock_ws
        self.channel._running = True

        await self.channel._start_heartbeat(0.01)

        task = self.channel._heartbeat_task
        self.assertIsNotNone(task)

        # Give it time to run a few iterations
        await asyncio.sleep(0.02)

        # Clean up
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task


# ---------------------------------------------------------------------------
# _react_to_message() emoji encoding tests
# ---------------------------------------------------------------------------


class TestDiscordReactEmojiEncoding(IsolatedAsyncioTestCase):
    """Tests for _react_to_message() emoji URL encoding."""

    def setUp(self) -> None:
        self.config = MagicMock()
        self.config.token = "test-token"
        self.bus = MagicMock()
        self.channel = DiscordChannel(self.config, self.bus)
        self.channel._running = True

    async def test_react_uses_url_encoded_emoji(self) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 204
        mock_http = AsyncMock()
        mock_http.put = AsyncMock(return_value=mock_resp)
        self.channel._http = mock_http

        # Test with emoji containing special chars (e.g., multibyte)
        await self.channel._react_to_message("ch1", "msg1", "👨‍💻")

        call_args = mock_http.put.call_args
        url = call_args[0][0]
        # The emoji should be URL encoded in the path
        self.assertIn("reactions/", url)
        self.assertIn("@me", url)


# ---------------------------------------------------------------------------
# _send_payload() error handling tests
# ---------------------------------------------------------------------------


class TestDiscordSendPayloadErrors(IsolatedAsyncioTestCase):
    """Tests for _send_payload() error handling after max retries."""

    def setUp(self) -> None:
        self.config = MagicMock()
        self.config.token = "test-token"
        self.bus = MagicMock()
        self.channel = DiscordChannel(self.config, self.bus)
        self.channel._running = True

    async def test_send_payload_fails_after_3_retries(self) -> None:
        mock_http = AsyncMock()
        error_response = MagicMock()
        error_response.status_code = 500
        error_response.raise_for_status = MagicMock(side_effect=Exception("Server error"))

        mock_http.post = AsyncMock(return_value=error_response)
        self.channel._http = mock_http

        url = "https://example.com/api"
        headers = {"Authorization": "Bot test"}

        with patch("nanobot.channels.discord.logger") as mock_logger:
            result = await self.channel._send_payload(url, headers, {"content": "test"})

            self.assertFalse(result)
            # Should have logged error after 3 attempts
            mock_logger.error.assert_called_once()

    async def test_send_payload_exception_on_retry(self) -> None:
        mock_http = AsyncMock()
        mock_http.post = AsyncMock(side_effect=[Exception("conn error"), Exception("conn error"), Exception("conn error")])
        self.channel._http = mock_http

        url = "https://example.com/api"
        headers = {"Authorization": "Bot test"}

        with patch("nanobot.channels.discord.logger") as mock_logger:
            result = await self.channel._send_payload(url, headers, {"content": "test"})

            self.assertFalse(result)
            mock_logger.error.assert_called_once()


# ---------------------------------------------------------------------------
# _handle_message_create() attachment tests
# ---------------------------------------------------------------------------


class TestDiscordHandleAttachmentErrors(IsolatedAsyncioTestCase):
    """Tests for _handle_message_create() attachment error paths."""

    def setUp(self) -> None:
        self.config = MagicMock()
        self.config.token = "test-token"
        self.bus = MagicMock()
        self.channel = DiscordChannel(self.config, self.bus)
        self.channel.is_allowed = MagicMock(return_value=True)

    @patch.object(DiscordChannel, "_react_to_message", new_callable=AsyncMock)
    @patch.object(DiscordChannel, "_handle_message", new_callable=AsyncMock)
    @patch.object(DiscordChannel, "_start_typing", new_callable=AsyncMock)
    async def test_attachment_download_failure_noted(
        self,
        mock_typing: AsyncMock,
        mock_handle: AsyncMock,
        mock_react: AsyncMock,
    ) -> None:
        payload = {
            "id": "msg1",
            "channel_id": "ch1",
            "author": {"id": "user1", "bot": False},
            "content": "test",
            "attachments": [
                {"url": "http://x.com/f.txt", "filename": "f.txt", "size": 100, "id": "a3"}
            ],
            "referenced_message": None,
        }
        mock_http = AsyncMock()
        mock_http.get = AsyncMock(side_effect=Exception("Download failed"))
        self.channel._http = mock_http

        await self.channel._handle_message_create(payload)

        call_kwargs = mock_handle.call_args[1]
        self.assertIn("download failed", call_kwargs["content"])

    @patch.object(DiscordChannel, "_react_to_message", new_callable=AsyncMock)
    @patch.object(DiscordChannel, "_handle_message", new_callable=AsyncMock)
    @patch.object(DiscordChannel, "_start_typing", new_callable=AsyncMock)
    async def test_attachment_no_url_skipped(
        self,
        mock_typing: AsyncMock,
        mock_handle: AsyncMock,
        mock_react: AsyncMock,
    ) -> None:
        payload = {
            "id": "msg1",
            "channel_id": "ch1",
            "author": {"id": "user1", "bot": False},
            "content": "test",
            "attachments": [
                {"filename": "f.txt", "size": 100, "id": "a4"}
            ],
            "referenced_message": None,
        }
        mock_http = AsyncMock()
        self.channel._http = mock_http

        await self.channel._handle_message_create(payload)

        call_kwargs = mock_handle.call_args[1]
        # Should not have attachment in content since no URL
        self.assertNotIn("attachment:", call_kwargs["content"])


# ---------------------------------------------------------------------------
# _handle_message_create() edge cases
# ---------------------------------------------------------------------------


class TestDiscordHandleMessageEdgeCases(IsolatedAsyncioTestCase):
    """Tests for _handle_message_create() edge cases."""

    def setUp(self) -> None:
        self.config = MagicMock()
        self.config.token = "test-token"
        self.bus = MagicMock()
        self.channel = DiscordChannel(self.config, self.bus)
        self.channel.is_allowed = MagicMock(return_value=True)

    @patch.object(DiscordChannel, "_react_to_message", new_callable=AsyncMock)
    @patch.object(DiscordChannel, "_handle_message", new_callable=AsyncMock)
    @patch.object(DiscordChannel, "_start_typing", new_callable=AsyncMock)
    async def test_missing_author_id_skipped(
        self,
        mock_typing: AsyncMock,
        mock_handle: AsyncMock,
        mock_react: AsyncMock,
    ) -> None:
        payload = {
            "id": "msg1",
            "channel_id": "ch1",
            "author": {},  # No id
            "content": "test",
            "attachments": [],
            "referenced_message": None,
        }
        await self.channel._handle_message_create(payload)
        mock_handle.assert_not_called()

    @patch.object(DiscordChannel, "_react_to_message", new_callable=AsyncMock)
    @patch.object(DiscordChannel, "_handle_message", new_callable=AsyncMock)
    @patch.object(DiscordChannel, "_start_typing", new_callable=AsyncMock)
    async def test_missing_channel_id_skipped(
        self,
        mock_typing: AsyncMock,
        mock_handle: AsyncMock,
        mock_react: AsyncMock,
    ) -> None:
        payload = {
            "id": "msg1",
            "author": {"id": "user1", "bot": False},
            "content": "test",
            "attachments": [],
            "referenced_message": None,
        }
        await self.channel._handle_message_create(payload)
        mock_handle.assert_not_called()

    @patch.object(DiscordChannel, "_react_to_message", new_callable=AsyncMock)
    @patch.object(DiscordChannel, "_handle_message", new_callable=AsyncMock)
    @patch.object(DiscordChannel, "_start_typing", new_callable=AsyncMock)
    async def test_empty_content_parts_becomes_placeholder(
        self,
        mock_typing: AsyncMock,
        mock_handle: AsyncMock,
        mock_react: AsyncMock,
    ) -> None:
        payload = {
            "id": "msg1",
            "channel_id": "ch1",
            "author": {"id": "user1", "bot": False},
            "content": "",
            "attachments": [],
            "referenced_message": None,
        }
        await self.channel._handle_message_create(payload)
        call_kwargs = mock_handle.call_args[1]
        self.assertEqual(call_kwargs["content"], "[empty message]")


if __name__ == "__main__":
    unittest.main()
