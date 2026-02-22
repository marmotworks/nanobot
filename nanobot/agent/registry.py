"""Subagent registry backed by SQLite for tracking subagent tasks."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path  # noqa: TC003  -- used at runtime, not type-check-only
import sqlite3

from loguru import logger


class SubagentRegistry:
    """SQLite-backed registry for tracking subagent tasks."""

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self._conn: sqlite3.Connection | None = None

    def open(self) -> None:
        """Open SQLite connection and create tables if not exists."""
        self._conn = sqlite3.connect(self.db_path)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute(
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
        self._conn.commit()

    def close(self) -> None:
        """Close the SQLite connection if open."""
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def recover_on_startup(self) -> int:
        """Mark all pending/running rows as lost. Returns count of rows updated."""
        assert self._conn is not None
        now = datetime.now(UTC).isoformat()
        cursor = self._conn.execute(
            """
            UPDATE subagents
            SET status = 'lost', completed_at = ?
            WHERE status IN ('pending', 'running')
            """,
            (now,),
        )
        self._conn.commit()
        count = cursor.rowcount
        if count:
            logger.warning("SubagentRegistry: marked {} orphaned task(s) as lost on startup", count)
        return count

    def tag_in(self, task_id: str, label: str, origin: str) -> None:
        """Insert a new task row with status='pending'."""
        assert self._conn is not None
        if origin not in ("user", "cron"):
            raise ValueError(f"origin must be 'user' or 'cron', got '{origin}'")
        now = datetime.now(UTC).isoformat()
        self._conn.execute(
            """
            INSERT INTO subagents (id, label, origin, status, spawned_at)
            VALUES (?, ?, ?, 'pending', ?)
            """,
            (task_id, label, origin, now),
        )
        self._conn.commit()

    def set_running(self, task_id: str) -> None:
        """Update status to 'running' and record started_at timestamp."""
        assert self._conn is not None
        now = datetime.now(UTC).isoformat()
        self._conn.execute(
            """
            UPDATE subagents SET status = 'running', started_at = ?
            WHERE id = ?
            """,
            (now, task_id),
        )
        self._conn.commit()

    def tag_out(self, task_id: str, status: str, result_summary: str = "") -> None:
        """Update status to a terminal state with result summary."""
        assert self._conn is not None
        now = datetime.now(UTC).isoformat()
        summary = result_summary[:200] if result_summary else ""
        self._conn.execute(
            """
            UPDATE subagents SET status = ?, completed_at = ?, result_summary = ?
            WHERE id = ?
            """,
            (status, now, summary, task_id),
        )
        self._conn.commit()

    def mark_lost(self, task_id: str, stack_frame: str = "") -> None:
        """Mark a task as lost with optional stack frame info."""
        assert self._conn is not None
        now = datetime.now(UTC).isoformat()
        self._conn.execute(
            """
            UPDATE subagents SET status = 'lost', completed_at = ?, stack_frame = ?
            WHERE id = ?
            """,
            (now, stack_frame, task_id),
        )
        self._conn.commit()

    def mark_requeue(self, task_id: str) -> None:
        """Mark a task as cancelled_requeue and increment retry_count."""
        assert self._conn is not None
        now = datetime.now(UTC).isoformat()
        self._conn.execute(
            """
            UPDATE subagents
            SET status = 'cancelled_requeue', completed_at = ?, retry_count = retry_count + 1
            WHERE id = ?
            """,
            (now, task_id),
        )
        self._conn.commit()

    def get_running_count(self) -> int:
        """Return count of pending + running tasks."""
        assert self._conn is not None
        cursor = self._conn.execute(
            "SELECT COUNT(*) FROM subagents WHERE status IN ('pending', 'running')"
        )
        return cursor.fetchone()[0]

    def get_all_active(self) -> list[dict]:
        """Return all pending/running tasks as list of dicts."""
        assert self._conn is not None
        cursor = self._conn.execute(
            """
            SELECT id, label, origin, status, spawned_at, started_at, retry_count, stack_frame
            FROM subagents WHERE status IN ('pending', 'running')
            """
        )
        return [dict(row) for row in cursor.fetchall()]

    def get_retry_count(self, task_id: str) -> int:
        """Return retry_count for a task, or 0 if not found."""
        assert self._conn is not None
        cursor = self._conn.execute("SELECT retry_count FROM subagents WHERE id = ?", (task_id,))
        row = cursor.fetchone()
        return row[0] if row else 0
