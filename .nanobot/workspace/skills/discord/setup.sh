#!/bin/bash

# Discord Connector Setup Script

echo "🔧 Discord Connector Setup"
echo "=========================="
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed"
    exit 1
fi

echo "✅ Python 3 is installed"

# Install dependencies
echo ""
echo "📦 Installing dependencies..."
pip3 install -r requirements.txt

if [ $? -eq 0 ]; then
    echo "✅ Dependencies installed successfully"
else
    echo "❌ Failed to install dependencies"
    exit 1
fi

# Check if config file exists
if [ ! -f "config/discord.json" ]; then
    echo ""
    echo "⚠️  Config file not found"
    echo "📝 Please copy example_config.json to config/discord.json"
    echo "   and add your bot token and guild ID"
    echo ""
    echo "Get a bot token at: https://discord.com/developers/applications"
else
    echo "✅ Config file found"
fi

echo ""
echo "🎉 Setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit config/discord.json with your bot token and guild ID"
echo "2. Invite your bot to your Discord server"
echo "3. Run: python discord_connector.py"
