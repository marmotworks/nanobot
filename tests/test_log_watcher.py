# ruff: noqa: I001
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "nanobot", "skills", "log-watcher", "scripts"))

from log_history import LogHistory
from log_watcher import ALERT_LEVELS, LogWatcher


class TestLogParsing:
    """Tests for log line parsing functionality."""

    def test_parse_error_line(self) -> None:
        """Parse a valid ERROR line → returns LogEvent with correct level, timestamp, logger, message."""
        line = "2026-02-23 16:11:00.123 | ERROR | my.logger - Something went wrong"
        watcher = LogWatcher(log_file=Path("/tmp/test.log"), on_event=lambda e: None)
        event = watcher.parse_line(line)

        assert event is not None
        assert event.level == "ERROR"
        assert event.timestamp == "2026-02-23 16:11:00.123"
        assert event.logger == "my.logger"
        assert event.message == "Something went wrong"
        assert event.raw == line

    def test_parse_warning_line(self) -> None:
        """Parse a WARNING line → returns LogEvent."""
        line = "2026-02-23 16:11:00.456 | WARNING | app.logger - Low disk space"
        watcher = LogWatcher(log_file=Path("/tmp/test.log"), on_event=lambda e: None)
        event = watcher.parse_line(line)

        assert event is not None
        assert event.level == "WARNING"
        assert event.logger == "app.logger"
        assert event.message == "Low disk space"

    def test_parse_info_line(self) -> None:
        """Parse an INFO line → returns LogEvent with level INFO."""
        line = "2026-02-23 16:11:00.789 | INFO | main - Application started"
        watcher = LogWatcher(log_file=Path("/tmp/test.log"), on_event=lambda e: None)
        event = watcher.parse_line(line)

        assert event is not None
        assert event.level == "INFO"

    def test_parse_invalid_line(self) -> None:
        """Parse a non-loguru line (e.g. "hello world") → returns None."""
        line = "hello world"
        watcher = LogWatcher(log_file=Path("/tmp/test.log"), on_event=lambda e: None)
        event = watcher.parse_line(line)

        assert event is None

    def test_parse_multiword_message(self) -> None:
        """Message with special chars → parsed correctly."""
        line = '2026-02-23 16:11:00.999 | ERROR | api.client - Failed to connect to "server-1" (error: timeout)'
        watcher = LogWatcher(log_file=Path("/tmp/test.log"), on_event=lambda e: None)
        event = watcher.parse_line(line)

        assert event is not None
        assert event.level == "ERROR"
        assert event.logger == "api.client"
        assert event.message == 'Failed to connect to "server-1" (error: timeout)'


class TestAlertLevels:
    """Tests for alert level configuration."""

    def test_alert_levels_include_error(self) -> None:
        """"ERROR" in ALERT_LEVELS → True."""
        assert "ERROR" in ALERT_LEVELS

    def test_alert_levels_include_warning(self) -> None:
        """"WARNING" in ALERT_LEVELS → True."""
        assert "WARNING" in ALERT_LEVELS

    def test_alert_levels_exclude_info(self) -> None:
        """"INFO" not in ALERT_LEVELS → True."""
        assert "INFO" not in ALERT_LEVELS


class TestLogHistory:
    """Tests for LogHistory class."""

    def test_add_and_retrieve(self) -> None:
        """Add 2 events, get_all() returns 2."""
        with tempfile.TemporaryDirectory() as tmpdir:
            history_file = Path(tmpdir) / "history.json"
            history = LogHistory(history_file=history_file, max_size=500)

            history.add({"level": "ERROR", "message": "Error 1"})
            history.add({"level": "WARNING", "message": "Warning 1"})

            events = history.get_all()
            assert len(events) == 2
            assert events[0]["level"] == "ERROR"
            assert events[1]["level"] == "WARNING"

    def test_persistence(self) -> None:
        """Add event, create new LogHistory from same file, get_all() returns 1."""
        with tempfile.TemporaryDirectory() as tmpdir:
            history_file = Path(tmpdir) / "history.json"

            # First history instance
            history1 = LogHistory(history_file=history_file, max_size=500)
            history1.add({"level": "ERROR", "message": "Test error"})

            # Second history instance from same file
            history2 = LogHistory(history_file=history_file, max_size=500)
            events = history2.get_all()

            assert len(events) == 1
            assert events[0]["level"] == "ERROR"

    def test_max_size_enforced(self) -> None:
        """Add 600 events to a history with max_size=500, len(get_all()) == 500."""
        with tempfile.TemporaryDirectory() as tmpdir:
            history_file = Path(tmpdir) / "history.json"
            history = LogHistory(history_file=history_file, max_size=500)

            for i in range(600):
                history.add({"level": "INFO", "message": f"Message {i}"})

            events = history.get_all()
            assert len(events) == 500

    def test_clear(self) -> None:
        """Add events, call clear(), get_all() returns empty list."""
        with tempfile.TemporaryDirectory() as tmpdir:
            history_file = Path(tmpdir) / "history.json"
            history = LogHistory(history_file=history_file, max_size=500)

            history.add({"level": "ERROR", "message": "Error 1"})
            history.add({"level": "WARNING", "message": "Warning 1"})
            history.clear()

            events = history.get_all()
            assert len(events) == 0
