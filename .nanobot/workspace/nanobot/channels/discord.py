"""
Discord Channel Module for nanobot
Enables emoji reaction handling and message interaction
"""

from typing import Dict

# Expressive Triggers: Maps content patterns to emoji reactions
EXPRESSIVE_TRIGGERS: Dict[str, str] = {
    "thanks": "👀",
    "appreciate": "👀",
    "thx": "👀",
    "?": "🤔",
    "bug": "🐛",
    "error": "🐛",
    "issue": "🐛",
    "broken": "🐛",
    "```": "💻",
    "✅": "✅",
}

# Interactive Actions: Maps emoji reactions to bot actions
INTERACTIVE_ACTIONS: Dict[str, str] = {
    "thumbs_up": "approve",
    "thumbs_down": "reject",
    "x": "cancel",
    "repeat": "retry",
    "stop": "halt",
}


class DiscordChannel:
    """Discord channel handler with emoji registry support"""

    def __init__(self):
        """Initialize the Discord channel with emoji registry"""
        self.emoji_registry: dict[str, dict] = {
            "EXPRESSIVE_TRIGGERS": EXPRESSIVE_TRIGGERS,
            "INTERACTIVE_ACTIONS": INTERACTIVE_ACTIONS,
        }

    def get_expressive_trigger(self, content: str) -> str:
        """Get the appropriate emoji for a given message content"""
        content_lower = content.lower()

        # Check each keyword in EXPRESSIVE_TRIGGERS
        for keyword, emoji in EXPRESSIVE_TRIGGERS.items():
            if keyword in content_lower:
                return emoji

        # Default: 👀 on receipt
        return "👀"

    def get_action_for_emoji(self, emoji: str) -> str:
        """Get the action for a given emoji"""
        return INTERACTIVE_ACTIONS.get(emoji, "unknown")

    def get_all_expressive_triggers(self) -> Dict[str, str]:
        """Return the expressive triggers dictionary"""
        return EXPRESSIVE_TRIGGERS

    def get_all_interactive_actions(self) -> Dict[str, str]:
        """Return the interactive actions dictionary"""
        return INTERACTIVE_ACTIONS

    async def on_raw_reaction_add(self, payload: dict) -> None:
        """Handle MESSAGE_REACTION_ADD gateway events
        
        Args:
            payload: Discord gateway event payload containing:
                - emoji: reaction emoji info
                - user_id: user who added the reaction
                - message_id: ID of the reacted message
                - channel_id: channel where reaction was added
                - guild_id: guild where reaction was added (optional)
        """
        # Check if the reacted message is from the bot itself
        # For now, we assume all reactions on bot messages should trigger actions
        # In a real implementation, we'd check payload.message_id against bot's messages
        
        # Look up the emoji in emoji_registry to find the mapped action
        emoji_name = payload.get("emoji", {}).get("name", "")
        action = self.get_action_for_emoji(emoji_name)
        
        # Trigger the appropriate action
        if action != "unknown":
            # In a real implementation, this would trigger the actual action
            # (e.g., call a method to approve/reject/etc.)
            pass
