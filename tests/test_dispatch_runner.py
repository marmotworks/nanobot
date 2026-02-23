"""Unit tests for dispatch_runner.py."""

from __future__ import annotations

from pathlib import Path  # noqa: TC003  -- used at runtime, not type-check-only
from unittest.mock import patch

import nanobot.agent.dispatch_runner as dr


class TestFindReadyMilestoneNoneWhenEmpty:
    """Tests for find_ready_milestone() with empty BACKLOG.md."""

    def test_empty_backlog_returns_none(self, tmp_path: Path) -> None:
        """Empty BACKLOG.md → returns None."""
        backlog_path = tmp_path / "BACKLOG.md"
        backlog_path.write_text("", encoding="utf-8")

        with (
            patch.object(dr, "BACKLOG_PATH", backlog_path),
            patch.object(dr, "REGISTRY_DB", tmp_path / "test.db"),
            patch.object(dr, "LOCK_FILE", tmp_path / ".backlog.lock"),
        ):
            result = dr.find_ready_milestone()

        assert result is None


class TestFindReadyMilestoneFindsFirstReady:
    """Tests for find_ready_milestone() finding ready milestones."""

    def test_finds_first_ready_milestone(self, tmp_path: Path) -> None:
        """BACKLOG with one [ ] milestone, no blockers → returns DispatchResult."""
        backlog_path = tmp_path / "BACKLOG.md"
        backlog_path.write_text(
            "- [ ] 31.1 Implement unit tests\nCriterion: Tests pass\nFile: tests/test_dispatch_runner.py\nBlocker: none\n",
            encoding="utf-8",
        )

        with (
            patch.object(dr, "BACKLOG_PATH", backlog_path),
            patch.object(dr, "REGISTRY_DB", tmp_path / "test.db"),
            patch.object(dr, "LOCK_FILE", tmp_path / ".backlog.lock"),
        ):
            result = dr.find_ready_milestone()

        assert result is not None
        assert result.milestone_num == "31.1"
        assert result.label == "31.1"
        assert "Implement unit tests" in result.task_brief
        assert result.dispatched is False


class TestFindReadyMilestoneSkipsBlocked:
    """Tests for find_ready_milestone() skipping blocked milestones."""

    def test_skips_blocked_milestone(self, tmp_path: Path) -> None:
        """BACKLOG with [ ] milestone that has unmet blocker → returns None."""
        backlog_path = tmp_path / "BACKLOG.md"
        backlog_path.write_text(
            "- [ ] 31.1 Implement unit tests\nCriterion: Tests pass\nFile: tests/test_dispatch_runner.py\nBlocker: 30.1\n",
            encoding="utf-8",
        )

        with (
            patch.object(dr, "BACKLOG_PATH", backlog_path),
            patch.object(dr, "REGISTRY_DB", tmp_path / "test.db"),
            patch.object(dr, "LOCK_FILE", tmp_path / ".backlog.lock"),
        ):
            result = dr.find_ready_milestone()

        assert result is None


class TestFindReadyMilestoneSkipsInProgress:
    """Tests for find_ready_milestone() skipping in-progress milestones."""

    def test_skips_in_progress_milestone(self, tmp_path: Path) -> None:
        """BACKLOG with [~] milestone → returns None."""
        backlog_path = tmp_path / "BACKLOG.md"
        backlog_path.write_text(
            "- [~] 31.1 Implement unit tests\nCriterion: Tests pass\nFile: tests/test_dispatch_runner.py\nBlocker: none\n",
            encoding="utf-8",
        )

        with (
            patch.object(dr, "BACKLOG_PATH", backlog_path),
            patch.object(dr, "REGISTRY_DB", tmp_path / "test.db"),
            patch.object(dr, "LOCK_FILE", tmp_path / ".backlog.lock"),
        ):
            result = dr.find_ready_milestone()

        assert result is None


class TestFindReadyMilestoneWritesTilde:
    """Tests for find_ready_milestone() writing [~] marker."""

    def test_writes_tilde_after_call(self, tmp_path: Path) -> None:
        """After calling find_ready_milestone(), BACKLOG.md has [~] where [ ] was."""
        backlog_path = tmp_path / "BACKLOG.md"
        backlog_path.write_text(
            "- [ ] 31.1 Implement unit tests\nCriterion: Tests pass\nFile: tests/test_dispatch_runner.py\nBlocker: none\n",
            encoding="utf-8",
        )

        with (
            patch.object(dr, "BACKLOG_PATH", backlog_path),
            patch.object(dr, "REGISTRY_DB", tmp_path / "test.db"),
            patch.object(dr, "LOCK_FILE", tmp_path / ".backlog.lock"),
        ):
            dr.find_ready_milestone()

        content = backlog_path.read_text(encoding="utf-8")
        assert "- [~] 31.1" in content
        assert "- [ ] 31.1" not in content


class TestGetRunningCountEmptyDb:
    """Tests for get_running_count() with empty database."""

    def test_empty_db_returns_zero(self, tmp_path: Path) -> None:
        """Fresh DB → returns 0."""
        db_path = tmp_path / "test.db"

        with (
            patch.object(dr, "BACKLOG_PATH", tmp_path / "BACKLOG.md"),
            patch.object(dr, "REGISTRY_DB", db_path),
            patch.object(dr, "LOCK_FILE", tmp_path / ".backlog.lock"),
        ):
            result = dr.get_running_count()

        assert result == 0


class TestGetRunningCountWithRunning:
    """Tests for get_running_count() with running entries."""

    def test_returns_count_of_running(self, tmp_path: Path) -> None:
        """DB with 2 running entries → returns 2."""
        db_path = tmp_path / "test.db"
        conn = dr.sqlite3.connect(str(db_path))
        conn.execute(
            """
            CREATE TABLE subagents (
                id TEXT PRIMARY KEY,
                label TEXT NOT NULL,
                origin TEXT NOT NULL,
                status TEXT NOT NULL,
                spawned_at TEXT NOT NULL,
                started_at TEXT,
                completed_at TEXT,
                retry_count INTEGER DEFAULT 0,
                stack_frame TEXT,
                result_summary TEXT
            )
            """
        )
        conn.execute(
            "INSERT INTO subagents (id, label, origin, status, spawned_at) VALUES (?, ?, ?, ?, ?)",
            ("task1", "task 1", "user", "pending", "2026-01-01T00:00:00+00:00"),
        )
        conn.execute(
            "INSERT INTO subagents (id, label, origin, status, spawned_at) VALUES (?, ?, ?, ?, ?)",
            ("task2", "task 2", "user", "running", "2026-01-01T00:00:00+00:00"),
        )
        conn.commit()
        conn.close()

        with (
            patch.object(dr, "BACKLOG_PATH", tmp_path / "BACKLOG.md"),
            patch.object(dr, "REGISTRY_DB", db_path),
            patch.object(dr, "LOCK_FILE", tmp_path / ".backlog.lock"),
        ):
            result = dr.get_running_count()

        assert result == 2
