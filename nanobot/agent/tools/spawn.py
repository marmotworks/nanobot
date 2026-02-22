"""Spawn tool for creating background subagents."""

from typing import Any, TYPE_CHECKING
from pathlib import Path

from loguru import logger

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
                "image_path": {
                    "type": "string",
                    "description": "Optional local file path to an image to pass to a vision-capable subagent. The image will be embedded as base64 in the subagent's first message.",
                },
            },
            "required": ["task"],
        }
    
    async def execute(self, task: str, label: str | None = None, model: str | None = None, image_path: str | None = None, **kwargs: Any) -> str:
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
        logger.info("SpawnTool.execute() called with task='{}', label='{}', model='{}'",
                    task[:50] + "..." if len(task) > 50 else task,
                    label or "None",
                    model or "None")

        # Validate model selection against policies
        if model:
            logger.info("SpawnTool: Validating model '{}' against policies", model)
            is_valid, error_msg = self._policy_manager.validate_model_selection(model)
            if not is_valid:
                logger.warning("SpawnTool: Model validation failed: {}", error_msg)
                return error_msg
            logger.info("SpawnTool: Model '{}' passed policy validation", model)

        # If no model specified, suggest appropriate default based on task type
        if not model:
            logger.info("SpawnTool: No model specified, inferring from task type")
            # Try to infer task type from task description
            task_lower = task.lower()
            if any(word in task_lower for word in ["image", "vision", "screenshot", "diagram", "analyze visual"]):
                model = self._policy_manager.get_subagent_default("vision")
                logger.info("SpawnTool: Inferred 'vision' task type, suggested model: '{}'", model)
            else:
                model = self._policy_manager.get_subagent_default("technical")
                logger.info("SpawnTool: Inferred 'technical' task type, suggested model: '{}'", model)

            # Validate the suggested model
            logger.info("SpawnTool: Validating suggested model '{}' against policies", model)
            is_valid, error_msg = self._policy_manager.validate_model_selection(model)
            if not is_valid:
                logger.warning("SpawnTool: Suggested model validation failed: {}", error_msg)
                return error_msg
            logger.info("SpawnTool: Suggested model '{}' passed policy validation", model)

            logger.info("SpawnTool: Calling manager.spawn() with model='{}'", model)
            result = await self._manager.spawn(
                task=task,
                label=label,
                origin_channel=self._origin_channel,
                origin_chat_id=self._origin_chat_id,
                model=model,
                image_path=image_path,
            )
            logger.info("SpawnTool: manager.spawn() returned: {}", result[:100] + "..." if len(result) > 100 else result)
            return result

        logger.info("SpawnTool: Calling manager.spawn() with model='{}'", model)
        result = await self._manager.spawn(
            task=task,
            label=label,
            origin_channel=self._origin_channel,
            origin_chat_id=self._origin_chat_id,
            model=model,
            image_path=image_path,
        )
        logger.info("SpawnTool: manager.spawn() returned: {}", result[:100] + "..." if len(result) > 100 else result)
        return result
