"""Unit tests for nanobot/channels/mochat.py."""

from __future__ import annotations

import sys
import unittest
from unittest.mock import AsyncMock, MagicMock

# ---------------------------------------------------------------------------
# Mock socketio before importing mochat
# ---------------------------------------------------------------------------

_mock_socketio = MagicMock()
_mock_socketio.AsyncClient = MagicMock
sys.modules.setdefault("socketio", _mock_socketio)
sys.modules.setdefault("msgpack", MagicMock())

from nanobot.channels.mochat import (  # noqa: E402
    MochatBufferedEntry,
    MochatChannel,
    build_buffered_body,
    extract_mention_ids,
    normalize_mochat_content,
    parse_timestamp,
    resolve_mochat_target,
    resolve_was_mentioned,
)


def _make_config(**kwargs):
    cfg = MagicMock()
    cfg.claw_token = kwargs.get("claw_token", "test-token")
    cfg.base_url = kwargs.get("base_url", "http://localhost:3000")
    cfg.socket_url = kwargs.get("socket_url", "")
    cfg.socket_path = kwargs.get("socket_path", "/socket.io")
    cfg.socket_disable_msgpack = kwargs.get("socket_disable_msgpack", True)
    cfg.socket_reconnect_delay_ms = kwargs.get("socket_reconnect_delay_ms", 1000)
    cfg.socket_max_reconnect_delay_ms = kwargs.get("socket_max_reconnect_delay_ms", 5000)
    cfg.socket_connect_timeout_ms = kwargs.get("socket_connect_timeout_ms", 5000)
    cfg.max_retry_attempts = kwargs.get("max_retry_attempts", 3)
    cfg.watch_limit = kwargs.get("watch_limit", 20)
    cfg.watch_timeout_ms = kwargs.get("watch_timeout_ms", 30000)
    cfg.refresh_interval_ms = kwargs.get("refresh_interval_ms", 60000)
    cfg.retry_delay_ms = kwargs.get("retry_delay_ms", 1000)
    cfg.reply_delay_ms = kwargs.get("reply_delay_ms", 0)
    cfg.reply_delay_mode = kwargs.get("reply_delay_mode", "off")
    cfg.agent_user_id = kwargs.get("agent_user_id", "bot-user")
    cfg.sessions = kwargs.get("sessions", [])
    cfg.panels = kwargs.get("panels", [])
    cfg.groups = kwargs.get("groups", {})
    cfg.mention = MagicMock()
    cfg.mention.require_in_groups = kwargs.get("require_mention_in_groups", False)
    cfg.allow_from = kwargs.get("allow_from", [])
    return cfg


def _make_channel(**kwargs):
    config = _make_config(**kwargs)
    bus = MagicMock()
    channel = MochatChannel(config, bus)
    return channel


# ---------------------------------------------------------------------------
# normalize_mochat_content
# ---------------------------------------------------------------------------


class TestNormalizeMochatContent(unittest.TestCase):
    def test_string_stripped(self) -> None:
        self.assertEqual(normalize_mochat_content("  hello  "), "hello")

    def test_none_returns_empty(self) -> None:
        self.assertEqual(normalize_mochat_content(None), "")

    def test_dict_returns_json(self) -> None:
        result = normalize_mochat_content({"key": "value"})
        self.assertIn("key", result)

    def test_empty_string(self) -> None:
        self.assertEqual(normalize_mochat_content(""), "")


# ---------------------------------------------------------------------------
# resolve_mochat_target
# ---------------------------------------------------------------------------


class TestResolveMochatTarget(unittest.TestCase):
    def test_empty_string(self) -> None:
        t = resolve_mochat_target("")
        self.assertEqual(t.id, "")
        self.assertFalse(t.is_panel)

    def test_session_prefix(self) -> None:
        t = resolve_mochat_target("session_abc123")
        self.assertEqual(t.id, "session_abc123")
        self.assertFalse(t.is_panel)

    def test_panel_prefix(self) -> None:
        t = resolve_mochat_target("panel:my-panel")
        self.assertEqual(t.id, "my-panel")
        self.assertTrue(t.is_panel)

    def test_group_prefix(self) -> None:
        t = resolve_mochat_target("group:group-id")
        self.assertTrue(t.is_panel)

    def test_plain_id_is_panel(self) -> None:
        t = resolve_mochat_target("some-random-id")
        self.assertTrue(t.is_panel)

    def test_mochat_prefix_stripped(self) -> None:
        t = resolve_mochat_target("mochat:session_xyz")
        self.assertEqual(t.id, "session_xyz")


# ---------------------------------------------------------------------------
# extract_mention_ids
# ---------------------------------------------------------------------------


class TestExtractMentionIds(unittest.TestCase):
    def test_string_list(self) -> None:
        self.assertEqual(extract_mention_ids(["user1", "user2"]), ["user1", "user2"])

    def test_dict_list(self) -> None:
        result = extract_mention_ids([{"id": "user1"}, {"userId": "user2"}])
        self.assertIn("user1", result)
        self.assertIn("user2", result)

    def test_not_list(self) -> None:
        self.assertEqual(extract_mention_ids("not-a-list"), [])

    def test_empty(self) -> None:
        self.assertEqual(extract_mention_ids([]), [])


# ---------------------------------------------------------------------------
# resolve_was_mentioned
# ---------------------------------------------------------------------------


class TestResolveWasMentioned(unittest.TestCase):
    def test_meta_mentioned_true(self) -> None:
        payload = {"meta": {"mentioned": True}}
        self.assertTrue(resolve_was_mentioned(payload, "bot-user"))

    def test_meta_was_mentioned_true(self) -> None:
        payload = {"meta": {"wasMentioned": True}}
        self.assertTrue(resolve_was_mentioned(payload, "bot-user"))

    def test_mention_in_ids(self) -> None:
        payload = {"meta": {"mentions": ["bot-user"]}}
        self.assertTrue(resolve_was_mentioned(payload, "bot-user"))

    def test_at_mention_in_content(self) -> None:
        payload = {"content": "<@bot-user> hello"}
        self.assertTrue(resolve_was_mentioned(payload, "bot-user"))

    def test_not_mentioned(self) -> None:
        payload = {"content": "hello world"}
        self.assertFalse(resolve_was_mentioned(payload, "bot-user"))

    def test_empty_agent_id(self) -> None:
        payload = {"content": "<@bot-user> hello"}
        self.assertFalse(resolve_was_mentioned(payload, ""))


# ---------------------------------------------------------------------------
# build_buffered_body
# ---------------------------------------------------------------------------


class TestBuildBufferedBody(unittest.TestCase):
    def test_single_entry(self) -> None:
        entries = [MochatBufferedEntry(raw_body="hello", author="user1")]
        self.assertEqual(build_buffered_body(entries, False), "hello")

    def test_multiple_entries_no_group(self) -> None:
        entries = [
            MochatBufferedEntry(raw_body="hello", author="user1"),
            MochatBufferedEntry(raw_body="world", author="user1"),
        ]
        result = build_buffered_body(entries, False)
        self.assertIn("hello", result)
        self.assertIn("world", result)

    def test_multiple_entries_group(self) -> None:
        entries = [
            MochatBufferedEntry(raw_body="hello", author="user1", sender_name="Alice"),
            MochatBufferedEntry(raw_body="world", author="user2", sender_name="Bob"),
        ]
        result = build_buffered_body(entries, True)
        self.assertIn("Alice: hello", result)
        self.assertIn("Bob: world", result)

    def test_empty_entries(self) -> None:
        self.assertEqual(build_buffered_body([], False), "")


# ---------------------------------------------------------------------------
# parse_timestamp
# ---------------------------------------------------------------------------


class TestParseTimestamp(unittest.TestCase):
    def test_valid_iso(self) -> None:
        result = parse_timestamp("2024-01-01T12:00:00Z")
        self.assertIsNotNone(result)
        self.assertIsInstance(result, int)

    def test_invalid(self) -> None:
        self.assertIsNone(parse_timestamp("not-a-date"))

    def test_none(self) -> None:
        self.assertIsNone(parse_timestamp(None))

    def test_empty_string(self) -> None:
        self.assertIsNone(parse_timestamp(""))


# ---------------------------------------------------------------------------
# MochatChannel init
# ---------------------------------------------------------------------------


class TestMochatChannelInit(unittest.TestCase):
    def test_init_stores_config(self) -> None:
        channel = _make_channel()
        self.assertEqual(channel.config.claw_token, "test-token")
        self.assertIsNone(channel._http)
        self.assertIsNone(channel._socket)
        self.assertFalse(channel._ws_connected)
        self.assertFalse(channel._ws_ready)

    def test_init_empty_sets(self) -> None:
        channel = _make_channel()
        self.assertIsInstance(channel._session_set, set)
        self.assertIsInstance(channel._panel_set, set)
        self.assertIsInstance(channel._seen_set, dict)

    def test_seed_targets_from_config(self) -> None:
        channel = _make_channel(sessions=["session_abc"], panels=["panel-1"])
        channel._seed_targets_from_config()
        self.assertIn("session_abc", channel._session_set)
        self.assertIn("panel-1", channel._panel_set)


# ---------------------------------------------------------------------------
# MochatChannel._normalize_id_list
# ---------------------------------------------------------------------------


class TestNormalizeIdList(unittest.TestCase):
    def test_basic(self) -> None:
        ids, wildcard = MochatChannel._normalize_id_list(["a", "b", "a"])
        self.assertEqual(sorted(ids), ["a", "b"])
        self.assertFalse(wildcard)

    def test_wildcard(self) -> None:
        ids, wildcard = MochatChannel._normalize_id_list(["a", "*"])
        self.assertTrue(wildcard)
        self.assertNotIn("*", ids)

    def test_empty(self) -> None:
        ids, wildcard = MochatChannel._normalize_id_list([])
        self.assertEqual(ids, [])
        self.assertFalse(wildcard)


# ---------------------------------------------------------------------------
# MochatChannel._remember_message_id
# ---------------------------------------------------------------------------


class TestRememberMessageId(unittest.TestCase):
    def test_first_time_not_seen(self) -> None:
        channel = _make_channel()
        self.assertFalse(channel._remember_message_id("key", "msg-1"))

    def test_second_time_is_seen(self) -> None:
        channel = _make_channel()
        channel._remember_message_id("key", "msg-1")
        self.assertTrue(channel._remember_message_id("key", "msg-1"))

    def test_different_keys_independent(self) -> None:
        channel = _make_channel()
        channel._remember_message_id("key1", "msg-1")
        self.assertFalse(channel._remember_message_id("key2", "msg-1"))


# ---------------------------------------------------------------------------
# MochatChannel.send
# ---------------------------------------------------------------------------


class TestMochatChannelSend(unittest.IsolatedAsyncioTestCase):
    async def test_send_no_token(self) -> None:
        channel = _make_channel(claw_token="")
        msg = MagicMock()
        msg.content = "hello"
        msg.media = []
        msg.chat_id = "session_abc"
        msg.reply_to = None
        msg.metadata = {}
        # Should return early without error
        await channel.send(msg)

    async def test_send_empty_content(self) -> None:
        channel = _make_channel()
        msg = MagicMock()
        msg.content = "   "
        msg.media = []
        msg.chat_id = "session_abc"
        msg.reply_to = None
        msg.metadata = {}
        channel._api_send = AsyncMock()
        await channel.send(msg)
        channel._api_send.assert_not_called()

    async def test_send_session(self) -> None:
        channel = _make_channel()
        msg = MagicMock()
        msg.content = "hello"
        msg.media = []
        msg.chat_id = "session_abc"
        msg.reply_to = None
        msg.metadata = {}
        channel._api_send = AsyncMock(return_value={})
        await channel.send(msg)
        channel._api_send.assert_called_once()
        args = channel._api_send.call_args[0]
        self.assertIn("sessions", args[0])

    async def test_send_panel(self) -> None:
        channel = _make_channel()
        channel._panel_set.add("panel-1")
        msg = MagicMock()
        msg.content = "hello"
        msg.media = []
        msg.chat_id = "panel-1"
        msg.reply_to = None
        msg.metadata = {}
        channel._api_send = AsyncMock(return_value={})
        await channel.send(msg)
        channel._api_send.assert_called_once()
        args = channel._api_send.call_args[0]
        self.assertIn("panels", args[0])

    async def test_send_empty_target(self) -> None:
        channel = _make_channel()
        msg = MagicMock()
        msg.content = "hello"
        msg.media = []
        msg.chat_id = ""
        msg.reply_to = None
        msg.metadata = {}
        channel._api_send = AsyncMock()
        await channel.send(msg)
        channel._api_send.assert_not_called()


# ---------------------------------------------------------------------------
# MochatChannel._process_inbound_event
# ---------------------------------------------------------------------------


class TestProcessInboundEvent(unittest.IsolatedAsyncioTestCase):
    async def test_skips_own_message(self) -> None:
        channel = _make_channel(agent_user_id="bot-user")
        channel._handle_message = AsyncMock()
        event = {
            "type": "message.add",
            "timestamp": "2024-01-01T00:00:00Z",
            "payload": {
                "author": "bot-user",
                "messageId": "msg-1",
                "content": "hello",
            },
        }
        await channel._process_inbound_event("session_abc", event, "session")
        channel._handle_message.assert_not_called()

    async def test_skips_duplicate_message(self) -> None:
        channel = _make_channel(agent_user_id="bot-user")
        channel._handle_message = AsyncMock()
        channel._remember_message_id("session:session_abc", "msg-1")
        event = {
            "type": "message.add",
            "timestamp": "2024-01-01T00:00:00Z",
            "payload": {
                "author": "other-user",
                "messageId": "msg-1",
                "content": "hello",
            },
        }
        await channel._process_inbound_event("session_abc", event, "session")
        channel._handle_message.assert_not_called()

    async def test_dispatches_valid_message(self) -> None:
        channel = _make_channel(agent_user_id="bot-user")
        channel._handle_message = AsyncMock()
        event = {
            "type": "message.add",
            "timestamp": "2024-01-01T00:00:00Z",
            "payload": {
                "author": "other-user",
                "messageId": "msg-unique-1",
                "content": "hello",
            },
        }
        await channel._process_inbound_event("session_abc", event, "session")
        channel._handle_message.assert_called_once()

    async def test_skips_missing_payload(self) -> None:
        channel = _make_channel()
        channel._handle_message = AsyncMock()
        event = {"type": "message.add"}
        await channel._process_inbound_event("session_abc", event, "session")
        channel._handle_message.assert_not_called()


# ---------------------------------------------------------------------------
# MochatChannel._dispatch_entries
# ---------------------------------------------------------------------------


class TestDispatchEntries(unittest.IsolatedAsyncioTestCase):
    async def test_dispatch_single_entry(self) -> None:
        channel = _make_channel()
        channel._handle_message = AsyncMock()
        entries = [
            MochatBufferedEntry(raw_body="hello", author="user1", message_id="m1", group_id="")
        ]
        await channel._dispatch_entries("session_abc", "session", entries, False)
        channel._handle_message.assert_called_once()
        kwargs = channel._handle_message.call_args[1]
        self.assertEqual(kwargs["content"], "hello")
        self.assertEqual(kwargs["sender_id"], "user1")

    async def test_dispatch_empty_entries(self) -> None:
        channel = _make_channel()
        channel._handle_message = AsyncMock()
        await channel._dispatch_entries("session_abc", "session", [], False)
        channel._handle_message.assert_not_called()

    async def test_dispatch_empty_body_uses_placeholder(self) -> None:
        channel = _make_channel()
        channel._handle_message = AsyncMock()
        entries = [MochatBufferedEntry(raw_body="", author="user1", message_id="m1")]
        await channel._dispatch_entries("session_abc", "session", entries, False)
        kwargs = channel._handle_message.call_args[1]
        self.assertEqual(kwargs["content"], "[empty message]")


# ---------------------------------------------------------------------------
# MochatChannel.stop
# ---------------------------------------------------------------------------


class TestMochatChannelStop(unittest.IsolatedAsyncioTestCase):
    async def test_stop_sets_running_false(self) -> None:
        channel = _make_channel()
        channel._running = True
        channel._http = AsyncMock()
        channel._http.aclose = AsyncMock()
        await channel.stop()
        self.assertFalse(channel._running)

    async def test_stop_closes_http(self) -> None:
        channel = _make_channel()
        channel._running = True
        mock_http = AsyncMock()
        mock_http.aclose = AsyncMock()
        channel._http = mock_http
        await channel.stop()
        mock_http.aclose.assert_called_once()

    async def test_stop_disconnects_socket(self) -> None:
        channel = _make_channel()
        channel._running = True
        mock_socket = AsyncMock()
        mock_socket.disconnect = AsyncMock()
        channel._socket = mock_socket
        channel._http = AsyncMock()
        channel._http.aclose = AsyncMock()
        await channel.stop()
        mock_socket.disconnect.assert_called_once()
        self.assertIsNone(channel._socket)


if __name__ == "__main__":
    unittest.main()
