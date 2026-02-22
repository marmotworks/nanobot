"""Tests for PolicyManager."""

import json
from pathlib import Path
import tempfile

from nanobot.policy_manager import PolicyManager


class TestPolicyManager:
    """Test PolicyManager functionality."""

    def setup_method(self):
        """Set up test configuration file."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = Path(self.temp_dir) / "policies.json"

    def teardown_method(self):
        """Clean up temporary directory."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_load_default_config(self):
        """Test loading default configuration."""
        pm = PolicyManager()
        assert pm.get_main_loop_model() == "zai-org/glm-4.7-flash"
        assert pm.get_max_concurrent_subagents() == 4
        assert pm.get_max_total_subagents() == 12

    def test_load_custom_config(self):
        """Test loading custom configuration."""
        custom_config = {
            "model_policies": {
                "main_loop_model": "custom-model",
                "subagent_defaults": {
                    "technical_tasks": "qwen3-coder-next",
                    "vision_tasks": "glm-4.6v-flash"
                },
                "forbidden_for_subagents": ["zai-org/glm-4.7-flash"],
                "max_concurrent_subagents": 8,
                "max_total_subagents": 24
            },
            "vision_task_instructions": {
                "glm-4.6v-flash": "Custom vision instructions"
            }
        }

        with open(self.config_path, "w") as f:
            json.dump(custom_config, f)

        pm = PolicyManager(self.config_path)
        assert pm.get_main_loop_model() == "custom-model"
        assert pm.get_max_concurrent_subagents() == 8
        assert pm.get_max_total_subagents() == 24
        assert pm.get_vision_task_instructions() == "Custom vision instructions"

    def test_get_subagent_default_technical(self):
        """Test getting default model for technical tasks."""
        pm = PolicyManager()
        assert pm.get_subagent_default("technical") == "qwen3-coder-next"

    def test_get_subagent_default_vision(self):
        """Test getting default model for vision tasks."""
        pm = PolicyManager()
        assert pm.get_subagent_default("vision") == "glm-4.6v-flash"

    def test_is_model_forbidden(self):
        """Test checking if model is forbidden for subagents."""
        pm = PolicyManager()
        assert pm.is_model_forbidden_for_subagents("zai-org/glm-4.7-flash")
        assert not pm.is_model_forbidden_for_subagents("qwen3-coder-next")
        assert not pm.is_model_forbidden_for_subagents("glm-4.6v-flash")

    def test_get_max_concurrent_by_model(self):
        """Test getting max concurrent subagents per model."""
        pm = PolicyManager()
        assert pm.get_max_concurrent_subagents("zai-org/glm-4.7-flash") == 4
        assert pm.get_max_concurrent_subagents("qwen3-coder-next") == 4
        assert pm.get_max_concurrent_subagents("glm-4.6v-flash") == 4
        assert pm.get_max_concurrent_subagents("unknown-model") == 4  # Default

    def test_get_vision_instructions(self):
        """Test getting vision task instructions."""
        pm = PolicyManager()
        instructions = pm.get_vision_task_instructions()
        assert "alignment" in instructions
        assert "spacing" in instructions
        assert "color contrast" in instructions

    def test_validate_main_model_forbidden(self):
        """Test validating that main model is forbidden for subagents."""
        pm = PolicyManager()
        is_valid, error_msg = pm.validate_model_selection("zai-org/glm-4.7-flash")
        assert not is_valid
        assert "main agent loop" in error_msg
        assert "reserved" in error_msg

    def test_validate_qwen_forbidden(self):
        """Test validating that qwen model is allowed for subagents."""
        pm = PolicyManager()
        is_valid, error_msg = pm.validate_model_selection("qwen3-coder-next")
        assert is_valid
        assert error_msg == ""

    def test_validate_glm_forbidden(self):
        """Test validating that glm model is allowed for subagents."""
        pm = PolicyManager()
        is_valid, error_msg = pm.validate_model_selection("glm-4.6v-flash")
        assert is_valid
        assert error_msg == ""

    def test_validate_vision_task_with_wrong_model(self):
        """Test validating vision task with wrong model."""
        pm = PolicyManager()
        is_valid, error_msg = pm.validate_model_selection("qwen3-coder-next", task_type="vision")
        assert not is_valid
        assert "vision" in error_msg
        assert "glm-4.6v-flash" in error_msg

    def test_validate_technical_task_with_vision_model(self):
        """Test validating technical task with vision model."""
        pm = PolicyManager()
        is_valid, error_msg = pm.validate_model_selection("glm-4.6v-flash", task_type="technical")
        assert not is_valid
        assert "technical" in error_msg
        assert "qwen3-coder-next" in error_msg

    def test_validate_vision_task_with_correct_model(self):
        """Test validating vision task with correct model."""
        pm = PolicyManager()
        is_valid, error_msg = pm.validate_model_selection("glm-4.6v-flash", task_type="vision")
        assert is_valid
        assert error_msg == ""

    def test_suggest_model_for_technical(self):
        """Test suggesting model for technical task."""
        pm = PolicyManager()
        model = pm.suggest_model_for_task("technical")
        assert model == "qwen3-coder-next"

    def test_suggest_model_for_vision(self):
        """Test suggesting model for vision task."""
        pm = PolicyManager()
        model = pm.suggest_model_for_task("vision")
        assert model == "glm-4.6v-flash"

    def test_suggest_model_for_invalid_task(self):
        """Test suggesting model for invalid task type."""
        pm = PolicyManager()
        model = pm.suggest_model_for_task("unknown")
        assert model == "qwen3-coder-next"  # Fallback to technical

    def test_get_model_info_main_model(self):
        """Test getting model info for main loop model."""
        pm = PolicyManager()
        info = pm.get_model_info("zai-org/glm-4.7-flash")
        assert info["model"] == "zai-org/glm-4.7-flash"
        assert info["is_main_loop"] is True
        assert info["is_forbidden_for_subagents"] is True
        assert info["concurrency"] == 4

    def test_get_model_info_qwen(self):
        """Test getting model info for qwen model."""
        pm = PolicyManager()
        info = pm.get_model_info("qwen3-coder-next")
        assert info["model"] == "qwen3-coder-next"
        assert info["is_main_loop"] is False
        assert info["is_forbidden_for_subagents"] is False
        assert info["concurrency"] == 4

    def test_get_model_info_glm(self):
        """Test getting model info for glm model."""
        pm = PolicyManager()
        info = pm.get_model_info("glm-4.6v-flash")
        assert info["model"] == "glm-4.6v-flash"
        assert info["is_main_loop"] is False
        assert info["is_forbidden_for_subagents"] is False
        assert info["concurrency"] == 4

    def test_get_model_info_unknown(self):
        """Test getting model info for unknown model."""
        pm = PolicyManager()
        info = pm.get_model_info("unknown-model")
        assert info["model"] == "unknown-model"
        assert info["is_main_loop"] is False
        assert info["is_forbidden_for_subagents"] is False
        assert info["concurrency"] == 4  # Default

    def test_multiple_models_all_valid(self):
        """Test validating multiple models all at once."""
        pm = PolicyManager()
        models = [
            "qwen3-coder-next",
            "glm-4.6v-flash",
            "zai-org/glm-4.7-flash"
        ]

        for model in models:
            is_valid, _ = pm.validate_model_selection(model)
            if model == "zai-org/glm-4.7-flash":
                assert not is_valid, f"Model {model} should be forbidden"
            else:
                assert is_valid, f"Model {model} should be allowed"

    def test_error_message_format(self):
        """Test that error messages are informative."""
        pm = PolicyManager()
        _, error_msg = pm.validate_model_selection("zai-org/glm-4.7-flash")
        assert len(error_msg) > 50  # Should be a substantial error message
        assert "zai-org/glm-4.7-flash" in error_msg
        assert "subagents" in error_msg
        assert "qwen3-coder-next" in error_msg  # Suggested alternative

    def test_vision_instructions_detailed(self):
        """Test that vision instructions are comprehensive."""
        pm = PolicyManager()
        instructions = pm.get_vision_task_instructions()
        required_elements = [
            "alignment",
            "spacing",
            "color contrast",
            "button states",
            "error messages",
            "visual hierarchy"
        ]

        for element in required_elements:
            assert element in instructions, f"Vision instructions should mention '{element}'"
