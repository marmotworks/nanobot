"""Discord message tool implementation."""
import os
import sys
from pathlib import Path

# Read configuration from environment or default
WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")
CHANNEL_ID = os.environ.get("DISCORD_CHANNEL_ID")

def send_message(channel_id: str, message: str):
    """Send a message to a Discord channel."""
    import requests
    
    webhook_url = WEBHOOK_URL or os.environ.get("DISCORD_WEBHOOK_URL")
    if not webhook_url:
        print("ERROR: DISCORD_WEBHOOK_URL not set", file=sys.stderr)
        sys.exit(1)
    
    payload = {
        "content": message,
        "channel_id": channel_id
    }
    
    response = requests.post(webhook_url, json=payload)
    if response.status_code == 204:
        print("Message sent successfully")
    else:
        print(f"ERROR: Failed to send message: {response.status_code} {response.text}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python message.py <channel_id> <message>", file=sys.stderr)
        sys.exit(1)
    
    channel_id = sys.argv[1]
    message = sys.argv[2]
    send_message(channel_id, message)
