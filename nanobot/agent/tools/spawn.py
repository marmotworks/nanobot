"""Spawn tool for creating background subagents."""

from typing import Any, TYPE_CHECKING
from pathlib import Path

from nanobot.agent.tools.base import Tool
from nanobot.policy_manager import PolicyManager

if TYPE_CHECKING:
    from nanobot.agent.subagent import SubagentManager


class SpawnTool(Tool):
    """
    Tool to spawn a subagent for background task execution.

    The subagent runs asynchronously and announces its result back
    to the main agent when complete.

    Enforces model usage policies:
    - zai-org/glm-4.7-flash: Main agent loop only
    - qwen3-coder-next: Technical tasks
    - glm-4.6v-flash: Vision tasks only
    """

    def __init__(self, manager: "SubagentManager", policy_manager: PolicyManager):
        self._manager = manager
        self._policy_manager = policy_manager
        self._origin_channel = "cli"
        self._origin_chat_id = "direct"
    
    def set_context(self, channel: str, chat_id: str) -> None:
        """Set the origin context for subagent announcements."""
        self._origin_channel = channel
        self._origin_chat_id = chat_id
    
    @property
    def name(self) -> str:
        return "spawn"
    
    @property
    def description(self) -> str:
        return (
            "Spawn a subagent to handle a task in the background. "
            "Use this for complex or time-consuming tasks that can run independently. "
            "The subagent will complete the task and report back when done."
        )
    
    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "task": {
                    "type": "string",
                    "description": "The task for the subagent to complete",
                },
                "label": {
                    "type": "string",
                    "description": "Optional short label for the task (for display)",
                },
                "model": {
                    "type": "string",
                    "description": "Optional model to use for this subagent (e.g., 'deepseek/deepseek-chat'). If not specified, uses the main agent's model.",
                },
            },
            "required": ["task"],
        }
    
    async def execute(self, task: str, label: str | None = None, model: str | None = None, **kwargs: Any) -> str:
        """Spawn a subagent to execute the given task.

        Args:
            task: The task for the subagent to complete.
            label: Optional short label for the task (for display).
            model: Optional model to use for this subagent.
                   If not specified, uses the main agent's model.
                   If model is None, will suggest the appropriate default.

        Returns:
            Result from subagent or error message if validation fails.
        """
        # Validate model selection against policies
        if model:
            is_valid, error_msg = self._policy_manager.validate_model_selection(model)
            if not is_valid:
                return error_msg

        # If no model specified, suggest appropriate default based on task type
        if not model:
            # Try to infer task type from task description
            task_lower = task.lower()
            if any(word in task_lower for word in ["image", "vision", "screenshot", "diagram", "analyze visual"]):
                model = self._policy_manager.get_subagent_default("vision")
            else:
                model = self._policy_manager.get_subagent_default("technical")

            # Validate the suggested model
            is_valid, error_msg = self._policy_manager.validate_model_selection(model)
            if not is_valid:
                return error_msg

            return await self._manager.spawn(
                task=task,
                label=label,
                origin_channel=self._origin_channel,
                origin_chat_id=self._origin_chat_id,
                model=model,
            )

        return await self._manager.spawn(
            task=task,
            label=label,
            origin_channel=self._origin_channel,
            origin_chat_id=self._origin_chat_id,
            model=model,
        )
