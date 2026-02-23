"""
Tests for SubagentManager template selection system.

These tests verify:
1. Template content is prepended to system prompt correctly
2. Template-specific keywords appear in prompts
3. No template uses default prompt without template content
4. Unknown templates fall back gracefully to default prompt
5. SpawnTool has template parameter in its schema
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest

from nanobot.agent.subagent import SubagentManager
from nanobot.agent.tools.spawn import SpawnTool
from nanobot.bus.queue import MessageBus
from nanobot.providers.base import LLMProvider

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def mock_provider() -> LLMProvider:
    """Mock LLM provider."""
    provider = MagicMock(spec=LLMProvider)
    provider.get_default_model.return_value = "zai-org/glm-4.7-flash"
    provider.api_key = "test-key"
    provider.api_base = "http://localhost:1234/v1"
    provider.chat = MagicMock()
    return provider


@pytest.fixture
def mock_bus() -> MessageBus:
    """Mock message bus."""
    bus = MagicMock(spec=MessageBus)
    bus.publish_inbound = MagicMock()
    return bus


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    """Test workspace directory."""
    return tmp_path / "workspace"


class TestTemplateSelection:
    """Tests for SubagentManager template selection system."""

    def test_code_fixer_template_content(
        self,
        tmp_path: Path,
        mock_provider: LLMProvider,
        mock_bus: MessageBus,
    ) -> None:
        """Test that code-fixer template contains debug/fix keywords."""
        workspace_dir = tmp_path / "workspace"
        workspace_dir.mkdir()
        db_path = tmp_path / "test.db"

        manager = SubagentManager(
            provider=mock_provider,
            workspace=workspace_dir,
            bus=mock_bus,
            model="zai-org/glm-4.7-flash",
            db_path=db_path,
        )

        result = manager._build_subagent_prompt("fix this bug", template="code-fixer")

        assert "debug" in result.lower() or "fix" in result.lower()

    def test_planner_template_content(
        self,
        tmp_path: Path,
        mock_provider: LLMProvider,
        mock_bus: MessageBus,
    ) -> None:
        """Test that planner template contains plan keyword."""
        workspace_dir = tmp_path / "workspace"
        workspace_dir.mkdir()
        db_path = tmp_path / "test.db"

        manager = SubagentManager(
            provider=mock_provider,
            workspace=workspace_dir,
            bus=mock_bus,
            model="zai-org/glm-4.7-flash",
            db_path=db_path,
        )

        result = manager._build_subagent_prompt("plan this", template="planner")

        assert "plan" in result.lower()

    def test_no_template_uses_default_prompt(
        self,
        tmp_path: Path,
        mock_provider: LLMProvider,
        mock_bus: MessageBus,
    ) -> None:
        """Test that no template returns base prompt without template-specific content."""
        workspace_dir = tmp_path / "workspace"
        workspace_dir.mkdir()
        db_path = tmp_path / "test.db"

        manager = SubagentManager(
            provider=mock_provider,
            workspace=workspace_dir,
            bus=mock_bus,
            model="zai-org/glm-4.7-flash",
            db_path=db_path,
        )

        result = manager._build_subagent_prompt("do something", template=None)

        assert "debug" not in result.lower()
        assert "fix" not in result.lower()
        assert "plan" not in result.lower()
        assert "research" not in result.lower()
        assert "subagent" in result.lower()

    def test_unknown_template_falls_back_gracefully(
        self,
        tmp_path: Path,
        mock_provider: LLMProvider,
        mock_bus: MessageBus,
    ) -> None:
        """Test that unknown template returns base prompt without crashing."""
        workspace_dir = tmp_path / "workspace"
        workspace_dir.mkdir()
        db_path = tmp_path / "test.db"

        manager = SubagentManager(
            provider=mock_provider,
            workspace=workspace_dir,
            bus=mock_bus,
            model="zai-org/glm-4.7-flash",
            db_path=db_path,
        )

        result = manager._build_subagent_prompt("task", template="nonexistent")

        assert "subagent" in result.lower()
        assert "debug" not in result.lower()
        assert "fix" not in result.lower()
        assert "plan" not in result.lower()
        assert "research" not in result.lower()

    def test_spawn_tool_has_template_parameter(
        self,
        tmp_path: Path,
        mock_provider: LLMProvider,
        mock_bus: MessageBus,
    ) -> None:
        """Test that SpawnTool has template parameter in its schema."""
        workspace_dir = tmp_path / "workspace"
        workspace_dir.mkdir()
        db_path = tmp_path / "test.db"

        manager = SubagentManager(
            provider=mock_provider,
            workspace=workspace_dir,
            bus=mock_bus,
            model="zai-org/glm-4.7-flash",
            db_path=db_path,
        )

        from nanobot.policy_manager import PolicyManager

        policy_manager = PolicyManager()
        tool = SpawnTool(manager=manager, policy_manager=policy_manager)

        assert "template" in tool.parameters["properties"]
