"""Unit tests for review_backlog.py functions."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
from unittest.mock import patch

_SCRIPT = Path(__file__).parent.parent / "nanobot/skills/task-tracker/scripts/review_backlog.py"
_spec = importlib.util.spec_from_file_location("review_backlog", _SCRIPT)
rb = importlib.util.module_from_spec(_spec)  # type: ignore[arg-type]
sys.modules["review_backlog"] = rb
_spec.loader.exec_module(rb)  # type: ignore[union-attr]


class TestGetCompletedLabels:
    """Tests for get_completed_labels() function."""

    def test_returns_completed_labels_when_db_has_entries(self, tmp_path: Path) -> None:
        """DB with completed entries → returns set of their labels."""
        db_path = tmp_path / "test.db"
        conn = rb.sqlite3.connect(str(db_path))
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
            """INSERT INTO subagents (id, label, origin, status, spawned_at, completed_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            ("task-1", "1.1", "user", "completed", "2024-01-01T00:00:00Z", "2024-01-01T01:00:00Z"),
        )
        conn.execute(
            """INSERT INTO subagents (id, label, origin, status, spawned_at, completed_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            ("task-2", "1.2", "user", "completed", "2024-01-01T00:00:00Z", "2024-01-01T01:00:00Z"),
        )
        conn.execute(
            """INSERT INTO subagents (id, label, origin, status, spawned_at)
               VALUES (?, ?, ?, ?, ?)""",
            ("task-3", "1.3", "user", "running", "2024-01-01T00:00:00Z"),
        )
        conn.commit()
        conn.close()

        result = rb.get_completed_labels(db_path)

        assert result == {"1.1", "1.2"}

    def test_returns_empty_set_when_db_is_empty(self, tmp_path: Path) -> None:
        """DB with no completed entries → returns empty set."""
        db_path = tmp_path / "test.db"
        conn = rb.sqlite3.connect(str(db_path))
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
            """INSERT INTO subagents (id, label, origin, status, spawned_at)
               VALUES (?, ?, ?, ?, ?)""",
            ("task-1", "1.1", "user", "running", "2024-01-01T00:00:00Z"),
        )
        conn.execute(
            """INSERT INTO subagents (id, label, origin, status, spawned_at)
               VALUES (?, ?, ?, ?, ?)""",
            ("task-2", "1.2", "user", "failed", "2024-01-01T00:00:00Z"),
        )
        conn.commit()
        conn.close()

        result = rb.get_completed_labels(db_path)

        assert result == set()

    def test_returns_empty_set_when_db_does_not_exist(self, tmp_path: Path) -> None:
        """Non-existent DB → returns empty set."""
        db_path = tmp_path / "nonexistent.db"

        result = rb.get_completed_labels(db_path)

        assert result == set()

    def test_ignores_null_labels(self, tmp_path: Path) -> None:
        """Rows with NULL label are ignored."""
        db_path = tmp_path / "test.db"
        conn = rb.sqlite3.connect(str(db_path))
        conn.execute(
            """
            CREATE TABLE subagents (
                id TEXT PRIMARY KEY,
                label TEXT,
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
            """INSERT INTO subagents (id, label, origin, status, spawned_at, completed_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            ("task-1", "1.1", "user", "completed", "2024-01-01T00:00:00Z", "2024-01-01T01:00:00Z"),
        )
        conn.execute(
            """INSERT INTO subagents (id, label, origin, status, spawned_at, completed_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            ("task-2", None, "user", "completed", "2024-01-01T00:00:00Z", "2024-01-01T01:00:00Z"),
        )
        conn.commit()
        conn.close()

        result = rb.get_completed_labels(db_path)

        assert result == {"1.1"}

    def test_ignores_empty_string_labels(self, tmp_path: Path) -> None:
        """Rows with empty string label are ignored."""
        db_path = tmp_path / "test.db"
        conn = rb.sqlite3.connect(str(db_path))
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
            """INSERT INTO subagents (id, label, origin, status, spawned_at, completed_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            ("task-1", "1.1", "user", "completed", "2024-01-01T00:00:00Z", "2024-01-01T01:00:00Z"),
        )
        conn.execute(
            """INSERT INTO subagents (id, label, origin, status, spawned_at, completed_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            ("task-2", "", "user", "completed", "2024-01-01T00:00:00Z", "2024-01-01T01:00:00Z"),
        )
        conn.commit()
        conn.close()

        result = rb.get_completed_labels(db_path)

        assert result == {"1.1"}


class TestGetFailedLabels:
    """Tests for get_failed_labels() function."""

    def test_returns_failed_labels_when_db_has_entries(self, tmp_path: Path) -> None:
        """DB with failed entries → returns set of their labels."""
        db_path = tmp_path / "test.db"
        conn = rb.sqlite3.connect(str(db_path))
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
            """INSERT INTO subagents (id, label, origin, status, spawned_at, completed_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            ("task-1", "1.1", "user", "failed", "2024-01-01T00:00:00Z", "2024-01-01T01:00:00Z"),
        )
        conn.execute(
            """INSERT INTO subagents (id, label, origin, status, spawned_at, completed_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            ("task-2", "1.2", "user", "failed", "2024-01-01T00:00:00Z", "2024-01-01T01:00:00Z"),
        )
        conn.execute(
            """INSERT INTO subagents (id, label, origin, status, spawned_at)
               VALUES (?, ?, ?, ?, ?)""",
            ("task-3", "1.3", "user", "running", "2024-01-01T00:00:00Z"),
        )
        conn.commit()
        conn.close()

        result = rb.get_failed_labels(db_path)

        assert result == {"1.1", "1.2"}

    def test_returns_lost_labels_as_failed(self, tmp_path: Path) -> None:
        """DB with lost entries → included in failed labels."""
        db_path = tmp_path / "test.db"
        conn = rb.sqlite3.connect(str(db_path))
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
            """INSERT INTO subagents (id, label, origin, status, spawned_at, completed_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            ("task-1", "1.1", "user", "lost", "2024-01-01T00:00:00Z", "2024-01-01T01:00:00Z"),
        )
        conn.execute(
            """INSERT INTO subagents (id, label, origin, status, spawned_at, completed_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            ("task-2", "1.2", "user", "lost", "2024-01-01T00:00:00Z", "2024-01-01T01:00:00Z"),
        )
        conn.commit()
        conn.close()

        result = rb.get_failed_labels(db_path)

        assert result == {"1.1", "1.2"}

    def test_returns_empty_set_when_db_is_empty(self, tmp_path: Path) -> None:
        """DB with no failed entries → returns empty set."""
        db_path = tmp_path / "test.db"
        conn = rb.sqlite3.connect(str(db_path))
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
            """INSERT INTO subagents (id, label, origin, status, spawned_at)
               VALUES (?, ?, ?, ?, ?)""",
            ("task-1", "1.1", "user", "running", "2024-01-01T00:00:00Z"),
        )
        conn.execute(
            """INSERT INTO subagents (id, label, origin, status, spawned_at, completed_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            ("task-2", "1.2", "user", "completed", "2024-01-01T00:00:00Z", "2024-01-01T01:00:00Z"),
        )
        conn.commit()
        conn.close()

        result = rb.get_failed_labels(db_path)

        assert result == set()

    def test_returns_empty_set_when_db_does_not_exist(self, tmp_path: Path) -> None:
        """Non-existent DB → returns empty set."""
        db_path = tmp_path / "nonexistent.db"

        result = rb.get_failed_labels(db_path)

        assert result == set()

    def test_ignores_null_labels(self, tmp_path: Path) -> None:
        """Rows with NULL label are ignored."""
        db_path = tmp_path / "test.db"
        conn = rb.sqlite3.connect(str(db_path))
        conn.execute(
            """
            CREATE TABLE subagents (
                id TEXT PRIMARY KEY,
                label TEXT,
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
            """INSERT INTO subagents (id, label, origin, status, spawned_at, completed_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            ("task-1", "1.1", "user", "failed", "2024-01-01T00:00:00Z", "2024-01-01T01:00:00Z"),
        )
        conn.execute(
            """INSERT INTO subagents (id, label, origin, status, spawned_at, completed_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            ("task-2", None, "user", "failed", "2024-01-01T00:00:00Z", "2024-01-01T01:00:00Z"),
        )
        conn.commit()
        conn.close()

        result = rb.get_failed_labels(db_path)

        assert result == {"1.1"}

    def test_ignores_empty_string_labels(self, tmp_path: Path) -> None:
        """Rows with empty string label are ignored."""
        db_path = tmp_path / "test.db"
        conn = rb.sqlite3.connect(str(db_path))
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
            """INSERT INTO subagents (id, label, origin, status, spawned_at, completed_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            ("task-1", "1.1", "user", "failed", "2024-01-01T00:00:00Z", "2024-01-01T01:00:00Z"),
        )
        conn.execute(
            """INSERT INTO subagents (id, label, origin, status, spawned_at, completed_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            ("task-2", "", "user", "failed", "2024-01-01T00:00:00Z", "2024-01-01T01:00:00Z"),
        )
        conn.commit()
        conn.close()

        result = rb.get_failed_labels(db_path)

        assert result == {"1.1"}


class TestMarkerResetLogic:
    """Tests for [~] marker reset logic based on registry status."""

    def test_tilde_becomes_x_when_completed(self, tmp_path: Path) -> None:
        """[~] marker with completed subagent → becomes [x]."""
        backlog_path = tmp_path / "BACKLOG.md"
        backlog_path.write_text(
            "- [~] 1.2 Some task\n",
            encoding="utf-8",
        )

        db_path = tmp_path / "subagents.db"
        conn = rb.sqlite3.connect(str(db_path))
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
            """INSERT INTO subagents (id, label, origin, status, spawned_at, completed_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            ("task-123", "1.2", "user", "completed", "2024-01-01T00:00:00Z", "2024-01-01T01:00:00Z"),
        )
        conn.commit()
        conn.close()

        with (
            patch.object(rb, "BACKLOG_PATH", backlog_path),
            patch.object(rb, "DB_PATH", db_path),
        ):
            result = rb.main()

        content = backlog_path.read_text(encoding="utf-8")
        assert "- [x] 1.2 Some task" in content
        assert "- [~] 1.2" not in content
        assert result == 0

    def test_tilde_becomes_space_when_failed(self, tmp_path: Path) -> None:
        """[~] marker with failed subagent → becomes [ ]."""
        backlog_path = tmp_path / "BACKLOG.md"
        backlog_path.write_text(
            "- [~] 1.2 Some task\n",
            encoding="utf-8",
        )

        db_path = tmp_path / "subagents.db"
        conn = rb.sqlite3.connect(str(db_path))
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
            """INSERT INTO subagents (id, label, origin, status, spawned_at, completed_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            ("task-123", "1.2", "user", "failed", "2024-01-01T00:00:00Z", "2024-01-01T01:00:00Z"),
        )
        conn.commit()
        conn.close()

        with (
            patch.object(rb, "BACKLOG_PATH", backlog_path),
            patch.object(rb, "DB_PATH", db_path),
        ):
            result = rb.main()

        content = backlog_path.read_text(encoding="utf-8")
        assert "- [ ] 1.2 Some task" in content
        assert "- [~] 1.2" not in content
        assert result == 0

    def test_tilde_becomes_space_when_unknown(self, tmp_path: Path) -> None:
        """[~] marker with no registry entry → becomes [ ]."""
        backlog_path = tmp_path / "BACKLOG.md"
        backlog_path.write_text(
            "- [~] 1.2 Some task\n",
            encoding="utf-8",
        )

        db_path = tmp_path / "subagents.db"
        conn = rb.sqlite3.connect(str(db_path))
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
        # Different label in DB
        conn.execute(
            """INSERT INTO subagents (id, label, origin, status, spawned_at)
               VALUES (?, ?, ?, ?, ?)""",
            ("task-456", "1.3", "user", "running", "2024-01-01T00:00:00Z"),
        )
        conn.commit()
        conn.close()

        with (
            patch.object(rb, "BACKLOG_PATH", backlog_path),
            patch.object(rb, "DB_PATH", db_path),
        ):
            result = rb.main()

        content = backlog_path.read_text(encoding="utf-8")
        assert "- [ ] 1.2 Some task" in content
        assert "- [~] 1.2" not in content
        assert result == 0

    def test_space_marker_unchanged(self, tmp_path: Path) -> None:
        """[ ] marker is left unchanged."""
        backlog_path = tmp_path / "BACKLOG.md"
        backlog_path.write_text(
            "- [ ] 1.2 Some task\n",
            encoding="utf-8",
        )

        db_path = tmp_path / "subagents.db"
        conn = rb.sqlite3.connect(str(db_path))
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
            """INSERT INTO subagents (id, label, origin, status, spawned_at, completed_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            ("task-123", "1.2", "user", "completed", "2024-01-01T00:00:00Z", "2024-01-01T01:00:00Z"),
        )
        conn.commit()
        conn.close()

        with (
            patch.object(rb, "BACKLOG_PATH", backlog_path),
            patch.object(rb, "DB_PATH", db_path),
        ):
            result = rb.main()

        content = backlog_path.read_text(encoding="utf-8")
        assert "- [ ] 1.2 Some task" in content
        assert result == 0

    def test_x_marker_unchanged(self, tmp_path: Path) -> None:
        """[x] marker is left unchanged."""
        backlog_path = tmp_path / "BACKLOG.md"
        backlog_path.write_text(
            "- [x] 1.2 Some task\n",
            encoding="utf-8",
        )

        db_path = tmp_path / "subagents.db"
        conn = rb.sqlite3.connect(str(db_path))
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
            """INSERT INTO subagents (id, label, origin, status, spawned_at, completed_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            ("task-123", "1.2", "user", "completed", "2024-01-01T00:00:00Z", "2024-01-01T01:00:00Z"),
        )
        conn.commit()
        conn.close()

        with (
            patch.object(rb, "BACKLOG_PATH", backlog_path),
            patch.object(rb, "DB_PATH", db_path),
        ):
            result = rb.main()

        content = backlog_path.read_text(encoding="utf-8")
        assert "- [x] 1.2 Some task" in content
        assert result == 0

    def test_tilde_stays_when_running(self, tmp_path: Path) -> None:
        """[~] marker with running subagent → stays [~]."""
        backlog_path = tmp_path / "BACKLOG.md"
        backlog_path.write_text(
            "- [~] 1.2 Some task\n",
            encoding="utf-8",
        )

        db_path = tmp_path / "subagents.db"
        conn = rb.sqlite3.connect(str(db_path))
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
            """INSERT INTO subagents (id, label, origin, status, spawned_at, started_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            ("task-123", "1.2", "user", "running", "2024-01-01T00:00:00Z", "2024-01-01T00:30:00Z"),
        )
        conn.commit()
        conn.close()

        with (
            patch.object(rb, "BACKLOG_PATH", backlog_path),
            patch.object(rb, "DB_PATH", db_path),
        ):
            result = rb.main()

        content = backlog_path.read_text(encoding="utf-8")
        assert "- [~] 1.2 Some task" in content
        assert "- [ ] 1.2" not in content
        assert result == 0

    def test_tilde_stays_when_pending(self, tmp_path: Path) -> None:
        """[~] marker with pending subagent → stays [~]."""
        backlog_path = tmp_path / "BACKLOG.md"
        backlog_path.write_text(
            "- [~] 1.2 Some task\n",
            encoding="utf-8",
        )

        db_path = tmp_path / "subagents.db"
        conn = rb.sqlite3.connect(str(db_path))
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
            """INSERT INTO subagents (id, label, origin, status, spawned_at)
               VALUES (?, ?, ?, ?, ?)""",
            ("task-123", "1.2", "user", "pending", "2024-01-01T00:00:00Z"),
        )
        conn.commit()
        conn.close()

        with (
            patch.object(rb, "BACKLOG_PATH", backlog_path),
            patch.object(rb, "DB_PATH", db_path),
        ):
            result = rb.main()

        content = backlog_path.read_text(encoding="utf-8")
        assert "- [~] 1.2 Some task" in content
        assert "- [ ] 1.2" not in content
        assert result == 0

    def test_tilde_becomes_x_when_completed_via_prefix_match(self, tmp_path: Path) -> None:
        """[~] 1.2 matches registry label '1.2 Some desc' → becomes [x]."""
        backlog_path = tmp_path / "BACKLOG.md"
        backlog_path.write_text(
            "- [~] 1.2 Some task\n",
            encoding="utf-8",
        )

        db_path = tmp_path / "subagents.db"
        conn = rb.sqlite3.connect(str(db_path))
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
        # Label uses prefix format
        conn.execute(
            """INSERT INTO subagents (id, label, origin, status, spawned_at, completed_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            ("task-123", "1.2 Milestone description", "user", "completed", "2024-01-01T00:00:00Z", "2024-01-01T01:00:00Z"),
        )
        conn.commit()
        conn.close()

        with (
            patch.object(rb, "BACKLOG_PATH", backlog_path),
            patch.object(rb, "DB_PATH", db_path),
        ):
            result = rb.main()

        content = backlog_path.read_text(encoding="utf-8")
        assert "- [x] 1.2 Some task" in content
        assert "- [~] 1.2" not in content
        assert result == 0


if __name__ == "__main__":
    import pytest

    pytest.main([__file__, "-v"])
