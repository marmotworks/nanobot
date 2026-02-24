# Discord Connector

A Discord bot connector for nanobot that enables message receiving and sending via Discord.

## Quick Start

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Create a Discord bot at https://discord.com/developers/applications
3. Create config file:
```bash
cp example_config.json config/discord.json
# Edit config/discord.json with your token
```

4. Run the connector:
```bash
python discord_connector.py
```

## Features

- Receive messages from Discord channels
- Send messages to Discord channels
- Log all messages and events to memory
- Support for commands and reactions
- Automatic message editing/deletion logging

## Configuration

Edit `config/discord.json`:

```json
{
  "token": "your_bot_token",
  "command_prefix": "!"
}
```

## Usage

### Sending Messages

```python
from discord_connector import DiscordConnector

connector = DiscordConnector()
await connector.send_message(
    channel_id="1234567890",
    content="Hello from nanobot!"
)
```

### Receiving Messages

All incoming messages are logged to `memory/DISCORD_MESSAGES.md`

## Commands

Default command prefix: `!`

Available commands can be added by extending the `_handle_command` method in `DiscordConnector`.

## Troubleshooting

- Make sure your bot has the correct permissions
- Check that the token is valid
- Verify the bot is invited to the correct server

## Creating a Private Discord Bot

Follow these steps to create and configure a private Discord bot for use with nanobot.

### Step 1: Create a Developer Application

1. Go to the [Discord Developer Portal](https://discord.com/developers/applications)
2. Click on **"New Application"** at the top right
3. Give your application a name (e.g., "nanobot-discord")
4. Click **"Create"**

### Step 2: Create a Bot User

1. In your application, click on the **"Bot"** tab on the left sidebar
2. Click **"Add Bot"**
3. Click **"Yes, do it!"** to confirm
4. **Important:** Toggle **"Public Bot"** to OFF (unchecked) to make your bot private
   - This ensures only you can add the bot to servers
   - If left ON, anyone with your bot URL can add it

### Step 3: Enable Required Privileged Intents

For the bot to function properly, you need to enable specific intents:

1. In the **Bot** tab, scroll down to the **Privileged Gateway Intents** section
2. Enable these intents:
   - **MESSAGE CONTENT INTENT**: Required to read message content
   - **SERVER MEMBERS INTENT** (optional): Required to see member information
   - **PRESENCE INTENT** (optional): Required to see member presence

3. Click **"Save Changes"**

### Step 4: Get Your Bot Token

1. On the **Bot** tab, click **"Reset Token"** (only if you haven't saved it yet)
2. Click **"Copy"** to copy your bot token
3. **Important:** Store this token securely! Never share it publicly
   - You can regenerate the token later if needed
   - The token is required to authenticate with Discord

### Step 5: Invite Your Bot to a Server

1. Go to the **OAuth2** tab on the left sidebar
2. Select **"URL Generator"** from the sidebar
3. Under **Scopes**, check these boxes:
   - **bot** (required)
   - **applications.commands** (optional, for slash commands)

4. Under **Bot Permissions**, select the permissions your bot needs:
   - **Read Messages/View Channels**: ✓
   - **Send Messages**: ✓
   - **Embed Links**: ✓
   - **Attach Files**: ✓
   - **Read Message History**: ✓
   - **Mention Everyone**: ✓
   - **Connect**: ✓ (if your bot joins voice channels)
   - **Speak**: ✓ (if your bot joins voice channels)

5. Copy the generated URL
6. Paste it into your browser to invite the bot to your server

### Step 6: Configure nanobot

1. Create the config file:
```bash
cp config/discord.json.example config/discord.json
```

2. Edit `config/discord.json` with your bot token:
```json
{
  "token": "your_bot_token_here"
}
```

3. Run the connector:
```bash
python discord_connector.py
```

## Bot Authorization Flow

The Discord bot uses a special OAuth2 flow optimized for bots:

**Authorization URL:**
```
https://discord.com/oauth2/authorize?client_id=YOUR_CLIENT_ID&scope=bot&permissions=PERMISSIONS
```

**Key Parameters:**
- `client_id`: Your application's client ID (from the OAuth2 tab)
- `scope=bot`: Indicates this is a bot authorization
- `permissions`: Bitwise integer representing required permissions

**Permissions Integer:**
You can calculate the permissions integer using Discord's permission calculator:
- https://discord.com/developers/applications/oauth2/url-generator

Common permission integers:
- `1`: Administrator
- `8`: Manage Messages
- `272424608`: Send Messages, Read Message History, Embed Links, Attach Files
- `3221225472`: Administrator

## Security Best Practices

1. **Keep your token secret**: Never commit tokens to version control
2. **Use environment variables**: Consider storing sensitive data in environment variables
3. **Monitor token usage**: Regularly check your bot's activity in the Developer Portal
4. **Rotate tokens**: Regenerate tokens periodically if you suspect exposure
5. **Use private bots**: Keep "Public Bot" disabled unless necessary

## Troubleshooting

### Bot Won't Join Server
- Verify the bot token is correct
- Ensure the bot has the necessary permissions
- Check that the bot hasn't hit the guild limit (unverified bots: 100 servers)

### Bot Can't Read Messages
- Ensure MESSAGE CONTENT INTENT is enabled in the Developer Portal
- Verify the bot has the "Read Messages" permission

### Bot Can't Send Messages
- Verify the bot has the "Send Messages" permission
- Check if the bot has been kicked from the server
- Ensure the bot is not muted in the channel

### Token Errors
- Regenerate the token if it's been compromised
- Ensure the token hasn't expired (tokens don't expire, but can be revoked)
- Check for typos in the token

## Advanced Configuration

### Custom Prefix
Edit the `command_prefix` in your config file:
```json
{
  "token": "your_bot_token",
  "command_prefix": ">>"
}
```

### Channel Whitelisting
Add channels the bot should monitor:
```json
{
  "token": "your_bot_token",
  "whitelisted_channels": ["1234567890", "9876543210"]
}
```

### Logging Configuration
Adjust logging levels and destinations in the connector code.

## Additional Resources

- [Discord OAuth2 Documentation](https://docs.discord.com/developers/topics/oauth2)
- [Discord Bot Permissions](https://discord.com/developers/applications/oauth2/url-generator)
- [Gateway Intents](https://discord.com/developers/docs/topics/gateway#gateway-intents)
- [Developer Portal](https://discord.com/developers/applications)