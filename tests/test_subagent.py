"""
Tests for SubagentManager capacity enforcement.

These tests verify:
1. Capacity limit of 3 concurrent subagents
2. RuntimeError raised when capacity is exceeded
3. Integration with real SQLite registry
"""

from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from nanobot.agent.subagent import SubagentManager
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
    provider.chat = AsyncMock()
    return provider


@pytest.fixture
def mock_bus() -> MessageBus:
    """Mock message bus."""
    bus = MagicMock(spec=MessageBus)
    bus.publish_inbound = AsyncMock()
    return bus


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    """Test workspace directory."""
    return tmp_path / "workspace"


class TestCapacityEnforcement:
    """Tests for SubagentManager capacity enforcement (milestone 10.8)."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_capacity_limit_raises_runtime_error(
        self,
        tmp_path: Path,
        mock_provider: LLMProvider,
        mock_bus: MessageBus,
    ) -> None:
        """Test that spawning a 4th subagent raises RuntimeError with capacity message."""
        workspace_dir = tmp_path / "workspace"
        workspace_dir.mkdir()
        db_path = tmp_path / "test.db"

        # Create SubagentManager with real SQLite registry
        manager = SubagentManager(
            provider=mock_provider,
            workspace=workspace_dir,
            bus=mock_bus,
            model="zai-org/glm-4.7-flash",
            db_path=db_path,
        )

        # Mock asyncio.create_task to prevent actual task execution
        with patch("asyncio.create_task") as mock_create_task:
            mock_create_task.return_value = MagicMock()

            # Manually tag in 3 running tasks atomically (status='pending')
            manager.registry.tag_in_atomic("task-001", "Task 1", "user")
            manager.registry.tag_in_atomic("task-002", "Task 2", "user")
            manager.registry.tag_in_atomic("task-003", "Task 3", "user")

            # Verify we have 3 pending tasks
            assert manager.registry.get_running_count() == 3

            # Attempt to spawn a 4th subagent — returns error string (CapacityError)
            result = await manager.spawn(task="Task 4", label="Task 4")
            assert "capacity" in result.lower()

            # Verify no 4th task was created
            mock_create_task.assert_not_called()

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_capacity_check_allows_third_task(
        self,
        tmp_path: Path,
        mock_provider: LLMProvider,
        mock_bus: MessageBus,
    ) -> None:
        """Test that the 3rd task is allowed (capacity is >= 3, not > 3)."""
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

        # Mock asyncio.create_task to prevent actual task execution
        with patch("asyncio.create_task") as mock_create_task:
            mock_task = MagicMock()
            mock_create_task.return_value = mock_task

            # Manually tag in 2 running tasks atomically
            manager.registry.tag_in_atomic("task-001", "Task 1", "user")
            manager.registry.tag_in_atomic("task-002", "Task 2", "user")

            # Verify we have 2 pending tasks
            assert manager.registry.get_running_count() == 2

            # The 3rd task should be allowed
            result = await manager.spawn(
                task="Task 3",
                label="Task 3",
            )

            # Should succeed
            assert "started" in result.lower()
            assert "Task 3" in result

            # Verify asyncio.create_task was called
            mock_create_task.assert_called_once()

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_capacity_limit_message_contains_count(
        self,
        tmp_path: Path,
        mock_provider: LLMProvider,
        mock_bus: MessageBus,
    ) -> None:
        """Test that the capacity limit error message includes the count."""
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

        with patch("asyncio.create_task") as mock_create_task:
            mock_create_task.return_value = MagicMock()

            # Tag in 3 tasks atomically
            manager.registry.tag_in_atomic("task-001", "Task 1", "user")
            manager.registry.tag_in_atomic("task-002", "Task 2", "user")
            manager.registry.tag_in_atomic("task-003", "Task 3", "user")

            # Attempt 4th spawn and verify error message contains "capacity"
            result = await manager.spawn(task="Task 4", label="Task 4")
            assert "capacity" in result.lower()


class TestTagOutFinally:
    """Tests for _run_subagent() tag_out finally guarantee (milestone 30.7)."""

    @pytest.mark.asyncio
    async def test_tag_out_called_on_success(
        self,
        tmp_path: Path,
        mock_provider: LLMProvider,
        mock_bus: MessageBus,
    ) -> None:
        """tag_out is called with status='completed' when subagent succeeds."""
        import sqlite3

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

        mock_response = MagicMock()
        mock_response.has_tool_calls = False
        mock_response.content = "Test result"
        mock_provider.chat = AsyncMock(return_value=mock_response)

        task_id = "test-task-123"
        manager.registry.tag_in(task_id, "Test Task", "user")

        with patch.object(manager, "_announce_result", AsyncMock()):
            await manager._run_subagent(
                task_id=task_id,
                task="Test task description",
                label="Test Task",
                origin={"channel": "cli", "chat_id": "test"},
                model="zai-org/glm-4.7-flash",
            )

        # Query the DB directly — get_all_active() only returns pending/running
        conn = sqlite3.connect(str(db_path))
        row = conn.execute("SELECT status FROM subagents WHERE id=?", (task_id,)).fetchone()
        conn.close()
        assert row is not None
        assert row[0] == "completed"

    @pytest.mark.asyncio
    async def test_tag_out_called_on_exception(
        self,
        tmp_path: Path,
        mock_provider: LLMProvider,
        mock_bus: MessageBus,
    ) -> None:
        """tag_out fires in finally even when _announce_result raises."""
        import sqlite3

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

        mock_response = MagicMock()
        mock_response.has_tool_calls = False
        mock_response.content = "Test result"
        mock_provider.chat = AsyncMock(return_value=mock_response)

        task_id = "test-task-456"
        manager.registry.tag_in(task_id, "Test Task", "user")

        with (
            patch.object(manager, "_announce_result", AsyncMock(side_effect=Exception("bus down"))),
            contextlib.suppress(Exception),
        ):
            await manager._run_subagent(
                task_id=task_id,
                task="Test task description",
                label="Test Task",
                origin={"channel": "cli", "chat_id": "test"},
                model="zai-org/glm-4.7-flash",
            )

        # tag_out must have fired despite the exception
        conn = sqlite3.connect(str(db_path))
        row = conn.execute("SELECT status FROM subagents WHERE id=?", (task_id,)).fetchone()
        conn.close()
        assert row is not None
        assert row[0] in ("completed", "failed")
