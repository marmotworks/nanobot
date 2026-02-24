"""
Example usage of the Discord connector
"""

import asyncio
from discord_connector import DiscordConnector


async def main():
    # Initialize the connector
    connector = DiscordConnector()

    # Example: Send a message to a channel
    # Replace with your actual channel ID
    channel_id = "123456789012345678"  # Example channel ID

    try:
        # Send a simple message
        message = await connector.send_message(
            channel_id=channel_id,
            content="Hello from nanobot! 🐱"
        )
        print(f"Message sent: {message}")

        # Send a message with an embed
        embed = {
            "title": "nanbot 🐱",
            "description": "A lightweight AI assistant",
            "color": 15727938,  # Blue
            "fields": [
                {
                    "name": "Version",
                    "value": "1.0.0"
                },
                {
                    "name": "Status",
                    "value": "Running"
                }
            ]
        }
        message = await connector.send_message(
            channel_id=channel_id,
            content="Check out this embed!",
            embed=embed
        )
        print(f"Embed sent: {message}")

    except Exception as e:
        print(f"Error: {e}")

    # Keep the bot running to receive messages
    # await connector.start()


if __name__ == "__main__":
    asyncio.run(main())
