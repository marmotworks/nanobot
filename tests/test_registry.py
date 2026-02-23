"""Unit tests for SubagentRegistry."""

import asyncio
import sqlite3
from unittest.mock import AsyncMock, MagicMock

import pytest

from nanobot.agent.registry import CapacityError, SubagentRegistry
from nanobot.agent.subagent import SubagentManager


@pytest.fixture
def registry(tmp_path: str) -> SubagentRegistry:
    """Create a registry fixture with proper setup and teardown."""
    r = SubagentRegistry(tmp_path / "test.db")
    r.open()
    yield r
    r.close()


class TestSubagentRegistryOpen:
    """Tests for SubagentRegistry.open()."""

    def test_open_creates_db_file(self, tmp_path: str) -> None:
        """Calling open() creates the .db file on disk."""
        db_path = tmp_path / "test.db"
        r = SubagentRegistry(db_path)
        r.open()
        assert db_path.exists()
        r.close()

    def test_open_creates_table(self, tmp_path: str) -> None:
        """After open(), the subagents table exists."""
        db_path = tmp_path / "test.db"
        r = SubagentRegistry(db_path)
        r.open()
        conn = sqlite3.connect(str(db_path))
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='subagents'"
        )
        assert cursor.fetchone() is not None
        conn.close()
        r.close()

    def test_close_is_idempotent(self, tmp_path: str) -> None:
        """Calling close() twice raises no exception."""
        db_path = tmp_path / "test.db"
        r = SubagentRegistry(db_path)
        r.open()
        r.close()
        r.close()


class TestSubagentRegistryTagIn:
    """Tests for SubagentRegistry.tag_in()."""

    def test_tag_in_inserts_row(self, registry: SubagentRegistry) -> None:
        """tag_in inserts a row, get_running_count() == 1."""
        registry.tag_in("abc", "test task", "user")
        assert registry.get_running_count() == 1

    def test_tag_in_status_is_pending(self, registry: SubagentRegistry) -> None:
        """tag_in creates task with status='pending'."""
        registry.tag_in("abc", "test task", "user")
        active = registry.get_all_active()
        assert len(active) == 1
        assert active[0]["status"] == "pending"

    def test_tag_in_invalid_origin_raises(self, registry: SubagentRegistry) -> None:
        """origin='invalid' raises ValueError."""
        with pytest.raises(ValueError, match="origin must be 'user' or 'cron'"):
            registry.tag_in("abc", "test task", "invalid")

    def test_tag_in_sets_spawned_at(self, registry: SubagentRegistry) -> None:
        """spawned_at is a valid ISO datetime string."""
        registry.tag_in("abc", "test task", "user")
        active = registry.get_all_active()
        assert len(active) == 1
        spawned_at = active[0]["spawned_at"]
        assert isinstance(spawned_at, str)
        assert "T" in spawned_at
        assert "+" in spawned_at or "Z" in spawned_at


class TestSubagentRegistrySetRunning:
    """Tests for SubagentRegistry.set_running()."""

    def test_set_running_updates_status(self, registry: SubagentRegistry) -> None:
        """tag_in then set_running, status == 'running'."""
        registry.tag_in("abc", "test task", "user")
        registry.set_running("abc")
        active = registry.get_all_active()
        assert active[0]["status"] == "running"

    def test_set_running_sets_started_at(self, registry: SubagentRegistry) -> None:
        """started_at is set after set_running."""
        registry.tag_in("abc", "test task", "user")
        registry.set_running("abc")
        active = registry.get_all_active()
        assert active[0]["started_at"] is not None
        assert isinstance(active[0]["started_at"], str)


class TestSubagentRegistryTagOut:
    """Tests for SubagentRegistry.tag_out()."""

    def test_tag_out_completed(self, registry: SubagentRegistry) -> None:
        """tag_in → set_running → tag_out('completed'), get_running_count() == 0."""
        registry.tag_in("abc", "test task", "user")
        registry.set_running("abc")
        registry.tag_out("abc", "completed", "success")
        assert registry.get_running_count() == 0

    def test_tag_out_truncates_summary(self, registry: SubagentRegistry) -> None:
        """result_summary of 300 chars is stored as 200 chars."""
        long_summary = "x" * 300
        registry.tag_in("abc", "test task", "user")
        registry.tag_out("abc", "completed", long_summary)
        conn = sqlite3.connect(str(registry.db_path))
        row = conn.execute("SELECT result_summary FROM subagents WHERE id=?", ("abc",)).fetchone()
        assert row[0] is not None
        assert len(row[0]) == 200
        conn.close()

    def test_tag_out_failed(self, registry: SubagentRegistry) -> None:
        """status='failed', get_running_count() == 0."""
        registry.tag_in("abc", "test task", "user")
        registry.tag_out("abc", "failed", "error")
        assert registry.get_running_count() == 0


class TestSubagentRegistryMarkLost:
    """Tests for SubagentRegistry.mark_lost()."""

    def test_mark_lost_sets_status(self, registry: SubagentRegistry) -> None:
        """tag_in → mark_lost, status='lost', get_running_count() == 0."""
        registry.tag_in("abc", "test task", "user")
        registry.mark_lost("abc")
        assert registry.get_running_count() == 0

    def test_mark_lost_stores_stack_frame(self, registry: SubagentRegistry) -> None:
        """stack_frame stored correctly."""
        registry.tag_in("abc", "test task", "user")
        registry.mark_lost("abc", "stack frame content")
        conn = sqlite3.connect(str(registry.db_path))
        row = conn.execute("SELECT stack_frame FROM subagents WHERE id=?", ("abc",)).fetchone()
        assert row[0] == "stack frame content"
        conn.close()


class TestSubagentRegistryMarkRequeue:
    """Tests for SubagentRegistry.mark_requeue()."""

    def test_mark_requeue_sets_status(self, registry: SubagentRegistry) -> None:
        """status='cancelled_requeue' after mark_requeue."""
        registry.tag_in("abc", "test task", "user")
        registry.mark_requeue("abc")
        conn = sqlite3.connect(str(registry.db_path))
        row = conn.execute("SELECT status FROM subagents WHERE id=?", ("abc",)).fetchone()
        assert row[0] == "cancelled_requeue"
        conn.close()

    def test_mark_requeue_increments_retry_count(self, registry: SubagentRegistry) -> None:
        """retry_count goes from 0 → 1 → 2."""
        registry.tag_in("abc", "test task", "user")
        assert registry.get_retry_count("abc") == 0
        registry.mark_requeue("abc")
        assert registry.get_retry_count("abc") == 1
        registry.mark_requeue("abc")
        assert registry.get_retry_count("abc") == 2


class TestSubagentRegistryRecoverOnStartup:
    """Tests for SubagentRegistry.recover_on_startup()."""

    def test_recover_marks_pending_as_lost(self, registry: SubagentRegistry) -> None:
        """tag_in (pending) → recover_on_startup() → status='lost'."""
        registry.tag_in("abc", "test task", "user")
        registry.recover_on_startup()
        conn = sqlite3.connect(str(registry.db_path))
        row = conn.execute("SELECT status FROM subagents WHERE id=?", ("abc",)).fetchone()
        assert row[0] == "lost"
        conn.close()

    def test_recover_marks_running_as_lost(self, registry: SubagentRegistry) -> None:
        """tag_in → set_running → recover_on_startup() → status='lost'."""
        registry.tag_in("abc", "test task", "user")
        registry.set_running("abc")
        registry.recover_on_startup()
        conn = sqlite3.connect(str(registry.db_path))
        row = conn.execute("SELECT status FROM subagents WHERE id=?", ("abc",)).fetchone()
        assert row[0] == "lost"
        conn.close()

    def test_recover_returns_count(self, registry: SubagentRegistry) -> None:
        """2 active tasks → recover returns 2."""
        registry.tag_in("abc", "test task", "user")
        registry.tag_in("def", "test task", "user")
        count = registry.recover_on_startup()
        assert count == 2

    def test_recover_ignores_completed(self, registry: SubagentRegistry) -> None:
        """Completed task not affected by recover."""
        registry.tag_in("abc", "test task", "user")
        registry.tag_out("abc", "completed", "success")
        count = registry.recover_on_startup()
        assert count == 0


class TestSubagentRegistryGetRetryCount:
    """Tests for SubagentRegistry.get_retry_count()."""

    def test_get_retry_count_default(self, registry: SubagentRegistry) -> None:
        """New task has retry_count=0."""
        registry.tag_in("abc", "test task", "user")
        assert registry.get_retry_count("abc") == 0

    def test_get_retry_count_after_requeue(self, registry: SubagentRegistry) -> None:
        """After mark_requeue, retry_count=1."""
        registry.tag_in("abc", "test task", "user")
        registry.mark_requeue("abc")
        assert registry.get_retry_count("abc") == 1

    def test_get_retry_count_not_found(self, registry: SubagentRegistry) -> None:
        """Unknown task_id returns 0."""
        assert registry.get_retry_count("nonexistent") == 0


class TestTagInAtomic:
    """Tests for SubagentRegistry.tag_in_atomic() (milestone 30.6)."""

    def test_tag_in_atomic_success(self, registry: SubagentRegistry) -> None:
        """tag_in_atomic succeeds and registry has 1 running entry."""
        registry.tag_in_atomic("id1", "label1", "user")
        assert registry.get_running_count() == 1

    def test_tag_in_atomic_capacity_enforcement(self, registry: SubagentRegistry) -> None:
        """Filling 3 slots with tag_in_atomic, 4th raises CapacityError."""
        registry.tag_in_atomic("task1", "task 1", "user")
        registry.tag_in_atomic("task2", "task 2", "user")
        registry.tag_in_atomic("task3", "task 3", "user")
        assert registry.get_running_count() == 3
        with pytest.raises(CapacityError):
            registry.tag_in_atomic("task4", "task 4", "user")

    def test_tag_in_atomic_after_tag_out(self, registry: SubagentRegistry) -> None:
        """Fill 3 slots, tag_out one, 4th tag_in_atomic succeeds."""
        registry.tag_in_atomic("task1", "task 1", "user")
        registry.tag_in_atomic("task2", "task 2", "user")
        registry.tag_in_atomic("task3", "task 3", "user")
        assert registry.get_running_count() == 3
        registry.tag_out("task2", "completed", "done")
        registry.tag_in_atomic("task4", "task 4", "user")
        assert registry.get_running_count() == 3

    def test_capacity_error_is_importable(self) -> None:
        """CapacityError is importable and is a subclass of Exception."""
        from nanobot.agent.registry import CapacityError
        assert issubclass(CapacityError, Exception)


@pytest.mark.integration
async def test_capacity_enforcement(tmp_path) -> None:
    """Spawning a 4th subagent when 3 are running returns a capacity error string."""
    # Create mocks for provider and bus
    provider = MagicMock()
    provider.get_default_model.return_value = "test-model"
    bus = AsyncMock()

    # Create SubagentManager
    manager = SubagentManager(
        provider=provider,
        workspace=tmp_path,
        bus=bus,
        db_path=tmp_path / "subagents.db",
    )

    # Patch _run_subagent to be an AsyncMock that sleeps forever
    async def sleep_forever(*args, **kwargs):
        await asyncio.sleep(3600)

    manager._run_subagent = AsyncMock(side_effect=sleep_forever)

    # Manually tag in 3 tasks atomically to simulate capacity being full
    manager.registry.tag_in_atomic("task1", "test task 1", "user")
    manager.registry.tag_in_atomic("task2", "test task 2", "user")
    manager.registry.tag_in_atomic("task3", "test task 3", "user")

    # Verify we have 3 running tasks
    assert manager.registry.get_running_count() == 3

    # Spawn a 4th time - should return error string containing "capacity"
    result = await manager.spawn("test task 4")
    assert "capacity" in result.lower()
