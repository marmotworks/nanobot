"""Unit tests for review_backlog.py [~] reset logic."""

from __future__ import annotations

import os
from pathlib import Path
from subprocess import run

import pytest


class TestTildeResetLogic:
    """Tests for [~] marker reset logic based on registry status."""

    def test_tilde_reset_to_open_when_no_registry_entry(self, tmp_path: Path) -> None:
        """BACKLOG with [~] marker, empty registry → resets to [ ]."""
        # Create temp BACKLOG.md with [~] marker
        backlog_path = tmp_path / "memory" / "BACKLOG.md"
        backlog_path.parent.mkdir(parents=True)
        backlog_content = """## Task 1: Sample task

Status: In progress

Blocker: none

- [ ] 1.1 Not started milestone
- [~] 1.2 In progress milestone
- [x] 1.3 Complete milestone
"""
        backlog_path.write_text(backlog_content)

        # Create empty registry DB
        db_path = tmp_path / "subagents.db"
        db_path.touch()

        # Run review_backlog.py with temp paths
        script_path = Path(__file__).parent.parent / "nanobot" / "skills" / "task-tracker" / "scripts" / "review_backlog.py"
        env = os.environ.copy()
        env["BACKLOG_PATH"] = str(backlog_path)
        env["DB_PATH"] = str(db_path)

        result = run(
            ["python3", str(script_path)],
            env=env,
            capture_output=True,
            text=True,
        )

        # Verify [~] marker resets to [ ] (no registry entry)
        result_content = backlog_path.read_text()
        assert "- [ ] 1.2 In progress milestone" in result_content
        assert "- [~] 1.2" not in result_content
        assert result.returncode == 0

    def test_tilde_becomes_done_when_completed(self, tmp_path: Path) -> None:
        """BACKLOG with [~] marker, registry has completed entry → becomes [x]."""
        # Create temp BACKLOG.md with [~] marker
        backlog_path = tmp_path / "memory" / "BACKLOG.md"
        backlog_path.parent.mkdir(parents=True)
        backlog_content = """## Task 1: Sample task

Status: In progress

Blocker: none

- [ ] 1.1 Not started milestone
- [~] 1.2 In progress milestone
- [x] 1.3 Complete milestone
"""
        backlog_path.write_text(backlog_content)

        # Create registry DB with completed entry for milestone 1.2
        db_path = tmp_path / "subagents.db"
        conn = __import__("sqlite3").connect(str(db_path))
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS subagents (
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

        # Run review_backlog.py with temp paths
        script_path = Path(__file__).parent.parent / "nanobot" / "skills" / "task-tracker" / "scripts" / "review_backlog.py"
        env = os.environ.copy()
        env["BACKLOG_PATH"] = str(backlog_path)
        env["DB_PATH"] = str(db_path)

        result = run(
            ["python3", str(script_path)],
            env=env,
            capture_output=True,
            text=True,
        )

        # Verify [~] marker becomes [x] (completed status)
        result_content = backlog_path.read_text()
        assert "- [x] 1.2 In progress milestone" in result_content
        assert "- [~] 1.2" not in result_content
        assert result.returncode == 0

    def test_tilde_stays_when_running(self, tmp_path: Path) -> None:
        """BACKLOG with [~] marker, registry has running entry → stays [~]."""
        # Create temp BACKLOG.md with [~] marker
        backlog_path = tmp_path / "memory" / "BACKLOG.md"
        backlog_path.parent.mkdir(parents=True)
        backlog_content = """## Task 1: Sample task

Status: In progress

Blocker: none

- [ ] 1.1 Not started milestone
- [~] 1.2 In progress milestone
- [x] 1.3 Complete milestone
"""
        backlog_path.write_text(backlog_content)

        # Create registry DB with running entry for milestone 1.2
        db_path = tmp_path / "subagents.db"
        conn = __import__("sqlite3").connect(str(db_path))
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS subagents (
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

        # Run review_backlog.py with temp paths
        script_path = Path(__file__).parent.parent / "nanobot" / "skills" / "task-tracker" / "scripts" / "review_backlog.py"
        env = os.environ.copy()
        env["BACKLOG_PATH"] = str(backlog_path)
        env["DB_PATH"] = str(db_path)

        result = run(
            ["python3", str(script_path)],
            env=env,
            capture_output=True,
            text=True,
        )

        # Verify [~] marker stays [~] (running status)
        result_content = backlog_path.read_text()
        assert "- [~] 1.2 In progress milestone" in result_content
        assert "- [ ] 1.2" not in result_content
        assert "- [x] 1.2" not in result_content
        assert result.returncode == 0

    def test_tilde_reset_when_failed(self, tmp_path: Path) -> None:
        """BACKLOG with [~] marker, registry has failed entry → resets to [ ]."""
        # Create temp BACKLOG.md with [~] marker
        backlog_path = tmp_path / "memory" / "BACKLOG.md"
        backlog_path.parent.mkdir(parents=True)
        backlog_content = """## Task 1: Sample task

Status: In progress

Blocker: none

- [ ] 1.1 Not started milestone
- [~] 1.2 In progress milestone
- [x] 1.3 Complete milestone
"""
        backlog_path.write_text(backlog_content)

        # Create registry DB with failed entry for milestone 1.2
        db_path = tmp_path / "subagents.db"
        conn = __import__("sqlite3").connect(str(db_path))
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS subagents (
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
            ("task-123", "1.2", "user", "failed", "2024-01-01T00:00:00Z", "2024-01-01T00:30:00Z"),
        )
        conn.commit()
        conn.close()

        # Run review_backlog.py with temp paths
        script_path = Path(__file__).parent.parent / "nanobot" / "skills" / "task-tracker" / "scripts" / "review_backlog.py"
        env = os.environ.copy()
        env["BACKLOG_PATH"] = str(backlog_path)
        env["DB_PATH"] = str(db_path)

        result = run(
            ["python3", str(script_path)],
            env=env,
            capture_output=True,
            text=True,
        )

        # Verify [~] marker resets to [ ] (failed status)
        result_content = backlog_path.read_text()
        assert "- [ ] 1.2 In progress milestone" in result_content
        assert "- [~] 1.2" not in result_content
        assert "- [x] 1.2" not in result_content
        assert result.returncode == 0

    def test_tilde_reset_when_lost(self, tmp_path: Path) -> None:
        """BACKLOG with [~] marker, registry has lost entry → resets to [ ]."""
        # Create temp BACKLOG.md with [~] marker
        backlog_path = tmp_path / "memory" / "BACKLOG.md"
        backlog_path.parent.mkdir(parents=True)
        backlog_content = """## Task 1: Sample task

Status: In progress

Blocker: none

- [ ] 1.1 Not started milestone
- [~] 1.2 In progress milestone
- [x] 1.3 Complete milestone
"""
        backlog_path.write_text(backlog_content)

        # Create registry DB with lost entry for milestone 1.2
        db_path = tmp_path / "subagents.db"
        conn = __import__("sqlite3").connect(str(db_path))
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS subagents (
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
            ("task-123", "1.2", "user", "lost", "2024-01-01T00:00:00Z", "2024-01-01T00:30:00Z"),
        )
        conn.commit()
        conn.close()

        # Run review_backlog.py with temp paths
        script_path = Path(__file__).parent.parent / "nanobot" / "skills" / "task-tracker" / "scripts" / "review_backlog.py"
        env = os.environ.copy()
        env["BACKLOG_PATH"] = str(backlog_path)
        env["DB_PATH"] = str(db_path)

        result = run(
            ["python3", str(script_path)],
            env=env,
            capture_output=True,
            text=True,
        )

        # Verify [~] marker resets to [ ] (lost status)
        result_content = backlog_path.read_text()
        assert "- [ ] 1.2 In progress milestone" in result_content
        assert "- [~] 1.2" not in result_content
        assert "- [x] 1.2" not in result_content
        assert result.returncode == 0

    def test_tilde_reset_when_pending(self, tmp_path: Path) -> None:
        """BACKLOG with [~] marker, registry has pending entry → stays [~]."""
        # Create temp BACKLOG.md with [~] marker
        backlog_path = tmp_path / "memory" / "BACKLOG.md"
        backlog_path.parent.mkdir(parents=True)
        backlog_content = """## Task 1: Sample task

Status: In progress

Blocker: none

- [ ] 1.1 Not started milestone
- [~] 1.2 In progress milestone
- [x] 1.3 Complete milestone
"""
        backlog_path.write_text(backlog_content)

        # Create registry DB with pending entry for milestone 1.2
        db_path = tmp_path / "subagents.db"
        conn = __import__("sqlite3").connect(str(db_path))
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS subagents (
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

        # Run review_backlog.py with temp paths
        script_path = Path(__file__).parent.parent / "nanobot" / "skills" / "task-tracker" / "scripts" / "review_backlog.py"
        env = os.environ.copy()
        env["BACKLOG_PATH"] = str(backlog_path)
        env["DB_PATH"] = str(db_path)

        result = run(
            ["python3", str(script_path)],
            env=env,
            capture_output=True,
            text=True,
        )

        # Verify [~] marker stays [~] (pending status)
        result_content = backlog_path.read_text()
        assert "- [~] 1.2 In progress milestone" in result_content
        assert "- [ ] 1.2" not in result_content
        assert "- [x] 1.2" not in result_content
        assert result.returncode == 0

    def test_tilde_reset_with_label_prefix_match(self, tmp_path: Path) -> None:
        """BACKLOG with [~] 1.2, registry has '1.2 Some description' → stays [~]."""
        # Create temp BACKLOG.md with [~] marker
        backlog_path = tmp_path / "memory" / "BACKLOG.md"
        backlog_path.parent.mkdir(parents=True)
        backlog_content = """## Task 1: Sample task

Status: In progress

Blocker: none

- [ ] 1.1 Not started milestone
- [~] 1.2 In progress milestone
- [x] 1.3 Complete milestone
"""
        backlog_path.write_text(backlog_content)

        # Create registry DB with entry using label prefix format
        db_path = tmp_path / "subagents.db"
        conn = __import__("sqlite3").connect(str(db_path))
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS subagents (
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
        # Label uses prefix format: "1.2 Some description"
        conn.execute(
            """INSERT INTO subagents (id, label, origin, status, spawned_at, started_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            ("task-123", "1.2 Milestone description", "user", "running", "2024-01-01T00:00:00Z", "2024-01-01T00:30:00Z"),
        )
        conn.commit()
        conn.close()

        # Run review_backlog.py with temp paths
        script_path = Path(__file__).parent.parent / "nanobot" / "skills" / "task-tracker" / "scripts" / "review_backlog.py"
        env = os.environ.copy()
        env["BACKLOG_PATH"] = str(backlog_path)
        env["DB_PATH"] = str(db_path)

        result = run(
            ["python3", str(script_path)],
            env=env,
            capture_output=True,
            text=True,
        )

        # Verify [~] marker stays [~] (prefix match works)
        result_content = backlog_path.read_text()
        assert "- [~] 1.2 In progress milestone" in result_content
        assert "- [ ] 1.2" not in result_content
        assert result.returncode == 0

    def test_multiple_tildes_different_statuses(self, tmp_path: Path) -> None:
        """Multiple [~] markers with different registry statuses."""
        # Create temp BACKLOG.md with multiple [~] markers
        backlog_path = tmp_path / "memory" / "BACKLOG.md"
        backlog_path.parent.mkdir(parents=True)
        backlog_content = """## Task 1: Sample task

Status: In progress

Blocker: none

- [ ] 1.1 Not started milestone
- [~] 1.2 In progress milestone 1
- [~] 1.3 In progress milestone 2
- [~] 1.4 In progress milestone 3
- [x] 1.5 Complete milestone
"""
        backlog_path.write_text(backlog_content)

        # Create registry DB with different statuses
        db_path = tmp_path / "subagents.db"
        conn = __import__("sqlite3").connect(str(db_path))
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS subagents (
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
        # 1.2 is completed → should become [x]
        conn.execute(
            """INSERT INTO subagents (id, label, origin, status, spawned_at, completed_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            ("task-12", "1.2", "user", "completed", "2024-01-01T00:00:00Z", "2024-01-01T01:00:00Z"),
        )
        # 1.3 is running → should stay [~]
        conn.execute(
            """INSERT INTO subagents (id, label, origin, status, spawned_at, started_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            ("task-13", "1.3", "user", "running", "2024-01-01T00:00:00Z", "2024-01-01T00:30:00Z"),
        )
        # 1.4 is failed → should reset to [ ]
        conn.execute(
            """INSERT INTO subagents (id, label, origin, status, spawned_at, completed_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            ("task-14", "1.4", "user", "failed", "2024-01-01T00:00:00Z", "2024-01-01T00:30:00Z"),
        )
        conn.commit()
        conn.close()

        # Run review_backlog.py with temp paths
        script_path = Path(__file__).parent.parent / "nanobot" / "skills" / "task-tracker" / "scripts" / "review_backlog.py"
        env = os.environ.copy()
        env["BACKLOG_PATH"] = str(backlog_path)
        env["DB_PATH"] = str(db_path)

        result = run(
            ["python3", str(script_path)],
            env=env,
            capture_output=True,
            text=True,
        )

        # Verify different transformations
        result_content = backlog_path.read_text()
        assert "- [x] 1.2 In progress milestone 1" in result_content  # completed → [x]
        assert "- [~] 1.3 In progress milestone 2" in result_content  # running → stays [~]
        assert "- [ ] 1.4 In progress milestone 3" in result_content  # failed → [ ]
        assert "- [~] 1.2" not in result_content
        assert "- [~] 1.4" not in result_content
        assert result.returncode == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
