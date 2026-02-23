"""Model Policy Manager - Enforces operational rules for model selection."""

import json
from pathlib import Path


class PolicyManager:
    """Manages model usage policies and validates model selection."""

    def __init__(self, config_path: Path | None = None):
        """Initialize policy manager with configuration."""
        if config_path is None:
            config_path = Path(__file__).parent / "config" / "policies.json"

        self.config = self._load_config(config_path)
        self.vision_instructions = self.config["vision_task_instructions"]

    def _load_config(self, config_path: Path) -> dict:
        """Load policy configuration from JSON file."""
        default_config = {
            "model_policies": {
                "main_loop_model": "zai-org/glm-4.7-flash",
                "subagent_defaults": {
                    "technical_tasks": "qwen3-coder-next",
                    "vision_tasks": "glm-4.6v-flash"
                },
                "forbidden_for_subagents": ["zai-org/glm-4.7-flash"],
                "max_concurrent_subagents": 4,
                "max_total_subagents": 12,
                "concurrency_by_model": {
                    "zai-org/glm-4.7-flash": 4,
                    "qwen3-coder-next": 4,
                    "glm-4.6v-flash": 4
                }
            },
            "vision_task_instructions": {
                "glm-4.6v-flash": "Provide detailed, accurate analysis. Pay special attention to: alignment, spacing, color contrast, button states, error messages, and visual hierarchy. Describe visual elements clearly and specifically."
            }
        }
        try:
            with open(config_path) as f:
                return json.load(f)
        except FileNotFoundError:
            return default_config

    def get_main_loop_model(self) -> str:
        """Get the configured main loop model."""
        return self.config["model_policies"]["main_loop_model"]

    def get_subagent_default(self, task_type: str) -> str:
        """Get default model for a task type."""
        # Map task_type to config key
        key_map = {
            "technical": "technical_tasks",
            "vision": "vision_tasks"
        }
        config_key = key_map.get(task_type, task_type)

        # Fallback to technical if unknown task type
        if config_key not in self.config["model_policies"]["subagent_defaults"]:
            config_key = "technical_tasks"

        return self.config["model_policies"]["subagent_defaults"][config_key]

    def is_model_forbidden_for_subagents(self, model: str) -> bool:
        """Check if a model is forbidden for subagents."""
        forbidden = self.config["model_policies"]["forbidden_for_subagents"]
        return model in forbidden

    def get_max_concurrent_subagents(self, model: str | None = None) -> int:
        """Get max concurrent subagents for a model."""
        if model:
            return self.config["model_policies"]["concurrency_by_model"].get(
                model, self.config["model_policies"]["max_concurrent_subagents"]
            )
        return self.config["model_policies"]["max_concurrent_subagents"]

    def get_max_total_subagents(self) -> int:
        """Get maximum total concurrent subagents."""
        return self.config["model_policies"]["max_total_subagents"]

    def get_vision_task_instructions(self) -> str:
        """Get instructions for vision tasks."""
        return self.vision_instructions.get("glm-4.6v-flash", "")

    def validate_model_selection(self, model: str, task_type: str | None = None) -> tuple[bool, str]:
        """
        Validate that a model selection is allowed.

        Args:
            model: Model name to validate
            task_type: Type of task (technical, vision, etc.)

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check if model is forbidden for subagents
        if self.is_model_forbidden_for_subagents(model):
            main_model = self.get_main_loop_model()
            return False, (
                f"Model '{model}' is reserved for the main agent loop and cannot be used for subagents. "
                f"Use '{main_model}' for the main agent, or choose a subagent model like 'qwen3-coder-next'."
            )

        # Check if model is appropriate for task type
        if task_type == "vision" and model != "glm-4.6v-flash":
            return False, (
                f"vision tasks require the 'glm-4.6v-flash' model. "
                f"Current selection: '{model}'."
            )

        if task_type == "technical" and model == "glm-4.6v-flash":
            return False, (
                f"technical tasks should use 'qwen3-coder-next' model. "
                f"Current selection: '{model}' (vision model)."
            )

        return True, ""

    def suggest_model_for_task(self, task_type: str) -> str:
        """Suggest an appropriate model for a task type."""
        return self.get_subagent_default(task_type)

    def get_model_info(self, model: str) -> dict:
        """Get information about a model."""
        info = {
            "model": model,
            "concurrency": self.get_max_concurrent_subagents(model),
            "is_main_loop": model == self.get_main_loop_model(),
            "is_forbidden_for_subagents": self.is_model_forbidden_for_subagents(model),
        }
        return info
