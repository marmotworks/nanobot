"""
Discord Connector for nanobot
Enables message receiving and sending via Discord
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import Optional

import discord
from discord.ext import commands

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DiscordConnector:
    """Discord bot connector for nanobot"""

    def __init__(self, config_path: str = "~/.nanobot/config.json"):
        self.config_path = Path(config_path).expanduser()
        self.config = self._load_config()
        self.client = commands.Bot(command_prefix="!")
        self._setup_commands()

        # Message storage
        self.messages_file = Path("memory/DISCORD_MESSAGES.md")
        self.events_file = Path("memory/DISCORD_EVENTS.md")
        self.messages_file.parent.mkdir(parents=True, exist_ok=True)

    def _load_config(self) -> dict:
        """Load Discord configuration from config.json"""
        if not self.config_path.exists():
            logger.warning(f"Config file not found at {self.config_path}")
            return {"token": "", "guild_id": "", "command_prefix": "!"}

        with open(self.config_path) as f:
            config = json.load(f)

        discord_config = config.get("channels", {}).get("discord", {})
        if not discord_config.get("token"):
            logger.error("Bot token not found in discord configuration")
            raise ValueError("Bot token is required in config.json channels.discord")

        return discord_config

    def _setup_commands(self):
        """Setup bot commands"""

        @self.client.event
        async def on_ready():
            logger.info(f"Connected to Discord as {self.client.user}")
            logger.info(f"Connected to {len(self.client.guilds)} guild(s)")

        @self.client.event
        async def on_message(message: discord.Message):
            """Handle incoming messages"""

            # Don't respond to bot's own messages
            if message.author.bot:
                return

            # Log message
            self._log_message(message)

            # Check for commands
            if message.content.startswith(self.config.get("command_prefix", "!")):
                await self._handle_command(message)

        @self.client.event
        async def on_message_delete(message: discord.Message):
            """Log message deletions"""
            self._log_event("message_deleted", {
                "channel": message.channel.name,
                "channel_id": message.channel.id,
                "author": message.author.name,
                "content": message.content,
                "timestamp": message.created_at.isoformat()
            })

        @self.client.event
        async def on_message_edit(before: discord.Message, after: discord.Message):
            """Log message edits"""
            if before.content != after.content:
                self._log_event("message_edited", {
                    "channel": after.channel.name,
                    "channel_id": after.channel.id,
                    "author": after.author.name,
                    "before": before.content,
                    "after": after.content,
                    "timestamp": after.edited_at.isoformat()
                })

    async def _handle_command(self, message: discord.Message):
        """Handle bot commands"""
        # Override in subclass or use external logic
        pass

    def _log_message(self, message: discord.Message):
        """Log a message to memory"""
        log_entry = f"""
## {message.created_at.isoformat()} - {message.author.name}

**Channel:** {message.channel.name} ({message.channel.id})
**Content:** {message.content}

---
"""
        with open(self.messages_file, "a") as f:
            f.write(log_entry)

    def _log_event(self, event_type: str, data: dict):
        """Log an event to memory"""
        log_entry = f"""
## {event_type.upper()} - {data.get('timestamp', 'N/A')}

**Details:** {data}

---
"""
        with open(self.events_file, "a") as f:
            f.write(log_entry)

    async def send_message(
        self,
        channel_id: str,
        content: str,
        embed: Optional[dict] = None
    ) -> Optional[discord.Message]:
        """Send a message to a Discord channel"""

        channel = self.client.get_channel(int(channel_id))
        if not channel:
            logger.error(f"Channel {channel_id} not found")
            return None

        try:
            if embed:
                embed_obj = discord.Embed.from_dict(embed)
                message = await channel.send(content, embed=embed_obj)
            else:
                message = await channel.send(content)

            logger.info(f"Sent message to {channel.name}: {content[:50]}...")
            return message

        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            return None

    async def start(self):
        """Start the Discord bot"""
        logger.info("Starting Discord connector...")
        await self.client.start(self.config["token"])

    async def stop(self):
        """Stop the Discord bot"""
        logger.info("Stopping Discord connector...")
        await self.client.close()


async def main():
    """Main entry point"""
    connector = DiscordConnector()
    await connector.start()


if __name__ == "__main__":
    asyncio.run(main())