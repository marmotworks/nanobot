"""Discord react tool — add emoji reactions to messages."""
from __future__ import annotations

from typing import Any
import urllib.parse

import httpx
from loguru import logger

from nanobot.agent.tools.base import Tool

DISCORD_API_BASE = "https://discord.com/api/v10"


class DiscordReactTool(Tool):
    """Tool to add an emoji reaction to a Discord message."""

    def __init__(self, token: str) -> None:
        self._token = token

    @property
    def name(self) -> str:
        return "discord_react"

    @property
    def description(self) -> str:
        return "Add an emoji reaction to a Discord message."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "channel_id": {
                    "type": "string",
                    "description": "The Discord channel ID containing the message",
                },
                "message_id": {
                    "type": "string",
                    "description": "The Discord message ID to react to",
                },
                "emoji": {
                    "type": "string",
                    "description": "The emoji to react with (e.g. '👍', '✅')",
                },
            },
            "required": ["channel_id", "message_id", "emoji"],
        }

    async def execute(self, channel_id: str, message_id: str, emoji: str, **kwargs: Any) -> str:
        encoded = urllib.parse.quote(emoji)
        url = f"{DISCORD_API_BASE}/channels/{channel_id}/messages/{message_id}/reactions/{encoded}/@me"
        headers = {"Authorization": f"Bot {self._token}"}
        async with httpx.AsyncClient() as client:
            resp = await client.put(url, headers=headers)
        if resp.status_code in (200, 204):
            logger.info("Reacted to message {} with {}", message_id, emoji)
            return f"Reacted with {emoji}"
        logger.warning("Failed to react: {} {}", resp.status_code, resp.text)
        return f"Failed to react: {resp.status_code} {resp.text}"
