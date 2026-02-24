# Discord Connector

Enables nanobot to receive and send messages via Discord.

## Overview

The Discord connector enables nanobot to:
- Receive messages from Discord channels
- Send messages to Discord channels
- Handle message reactions and commands
- Work with Discord bot tokens for authentication

## Setup

### 1. Create a Discord Bot

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Click "New Application" → give it a name
3. Go to "Bot" tab → click "Add Bot"
4. Copy your **Bot Token** (keep this secret!)
5. Go to "OAuth2" → "URL Generator"
6. Select scopes: `bot`
7. Select permissions: `Read Messages/View Channels`, `Send Messages`, `Embed Links`
8. Generate the URL and invite the bot to your server

### 2. Configure the Connector

Edit `/Users/mhall/.nanobot/config.json`:

```json
{
  "channels": {
    "discord": {
      "enabled": true,
      "token": "YOUR_BOT_TOKEN_HERE",
      "allowFrom": [],
      "gatewayUrl": "wss://gateway.discord.gg/?v=10&encoding=json",
      "intents": 37377
    }
  }
}
```

### 3. Run the Connector

```bash
python -m nanobot.workspace.skills.discord.discord_connector
```

Or integrate it into your main bot loop.

## Usage

### Sending Messages

```python
from nanobot.workspace.skills.discord.discord_connector import DiscordConnector

connector = DiscordConnector()
await connector.send_message(channel_id="1234567890", content="Hello from nanobot!")
```

### Receiving Messages

Messages are automatically received and logged to:
- Discord messages → `/Users/mhall/.nanobot/workspace/memory/DISCORD_MESSAGES.md`
- Discord events → `/Users/mhall/.nanobot/workspace/memory/DISCORD_EVENTS.md`

### Custom Commands

Define custom commands in your bot logic to respond to Discord messages. For example:

```python
if message.content.startswith("!hello"):
    await connector.send_message(message.channel.id, "Hello there!")
```

## Integration with Message Tool

The `message` tool can target Discord channels:

```python
message(
    content="Hello from Discord!",
    channel="discord",
    chat_id="YOUR_DISCORD_CHANNEL_ID"
)
```

## Permissions Required

- `Read Messages/View Channels` - to receive messages
- `Send Messages` - to send messages
- `Embed Links` - to send rich messages

## Error Handling

- Invalid token → Check your bot token in config.json
- Permission denied → Verify bot has required permissions
- Channel not found → Check channel ID is correct

## Troubleshooting

### Bot doesn't join server
- Verify bot token is correct
- Check bot is not blocked in server settings
- Verify bot has required permissions

### Messages not sending
- Check bot has Send Messages permission
- Verify channel ID is valid
- Check if bot is in the channel

## Dependencies

- `discord.py` - Python Discord API wrapper

Install with:
```bash
pip install discord.py
```