"""Tests for FailureTracker."""

from datetime import datetime

from nanobot.agent.tools.failure_tracker import FailureRecord, FailureTracker


class TestFailureTracker:
    """Test suite for FailureTracker."""

    def test_initialization(self):
        """Test FailureTracker initialization."""
        tracker = FailureTracker()
        assert tracker.max_records == 50
        assert tracker.failures == {}
        assert tracker.get_failure_count() == 0

    def test_record_failure(self):
        """Test recording a failure."""
        tracker = FailureTracker()
        tracker.record_failure("command1", "Error: Command not found")

        assert "command1" in tracker.failures
        assert tracker.failures["command1"].error_message == "Error: Command not found"
        assert tracker.get_failure_count() == 1

    def test_record_multiple_failures(self):
        """Test recording multiple failures."""
        tracker = FailureTracker()
        tracker.record_failure("cmd1", "Error 1")
        tracker.record_failure("cmd2", "Error 2")
        tracker.record_failure("cmd3", "Error 3")

        assert tracker.get_failure_count() == 3

    def test_increment_attempts(self):
        """Test that repeated failures increment attempt count."""
        tracker = FailureTracker()
        tracker.record_failure("cmd1", "Error 1")
        tracker.record_failure("cmd1", "Error 2")  # Same command
        tracker.record_failure("cmd1", "Error 3")  # Same command

        record = tracker.failures["cmd1"]
        assert record.attempts == 3
        assert record.error_message == "Error 3"  # Latest error

    def test_update_error_message(self):
        """Test that recording a failure updates the error message."""
        tracker = FailureTracker()
        tracker.record_failure("cmd1", "Error 1")
        tracker.record_failure("cmd1", "Error 2")  # Same command, different error

        record = tracker.failures["cmd1"]
        assert record.error_message == "Error 2"
        assert record.attempts == 2

    def test_get_failed_commands(self):
        """Test getting formatted failed commands."""
        tracker = FailureTracker()
        tracker.record_failure("cmd1", "Error 1")
        tracker.record_failure("cmd2", "Error 2")

        commands = tracker.get_failed_commands()
        assert len(commands) == 2
        assert "Command 'cmd1' failed: Error 1 (attempted 1 times)" in commands
        assert "Command 'cmd2' failed: Error 2 (attempted 1 times)" in commands

    def test_get_failed_commands_empty(self):
        """Test getting failed commands when none exist."""
        tracker = FailureTracker()
        commands = tracker.get_failed_commands()
        assert commands == []

    def test_get_failure_summary(self):
        """Test getting failure summary."""
        tracker = FailureTracker()
        tracker.record_failure("cmd1", "Error 1")
        tracker.record_failure("cmd2", "Error 2")

        summary = tracker.get_failure_summary()
        assert "failed in previous attempts" in summary
        assert "Command 'cmd1' failed: Error 1" in summary
        assert "Command 'cmd2' failed: Error 2" in summary

    def test_get_failure_summary_empty(self):
        """Test getting failure summary when none exist."""
        tracker = FailureTracker()
        summary = tracker.get_failure_summary()
        assert summary == ""

    def test_get_failure_count(self):
        """Test getting failure count."""
        tracker = FailureTracker()
        assert tracker.get_failure_count() == 0

        tracker.record_failure("cmd1", "Error 1")
        assert tracker.get_failure_count() == 1

        tracker.record_failure("cmd2", "Error 2")
        assert tracker.get_failure_count() == 2

    def test_get_record(self):
        """Test getting a specific failure record."""
        tracker = FailureTracker()
        tracker.record_failure("cmd1", "Error 1")

        record = tracker.get_record("cmd1")
        assert record is not None
        assert record.tool_name == "cmd1"
        assert record.error_message == "Error 1"
        assert record.attempts == 1

        assert tracker.get_record("cmd2") is None

    def test_has_failed(self):
        """Test checking if a tool has failed."""
        tracker = FailureTracker()
        assert not tracker.has_failed("cmd1")

        tracker.record_failure("cmd1", "Error 1")
        assert tracker.has_failed("cmd1")

    def test_clear(self):
        """Test clearing all failures."""
        tracker = FailureTracker()
        tracker.record_failure("cmd1", "Error 1")
        tracker.record_failure("cmd2", "Error 2")

        assert tracker.get_failure_count() == 2
        tracker.clear()
        assert tracker.get_failure_count() == 0
        assert tracker.failures == {}

    def test_max_records_trimming(self):
        """Test that old records are trimmed when exceeding max_records."""
        tracker = FailureTracker(max_records=5)

        # Add 10 failures
        for i in range(10):
            tracker.record_failure(f"cmd{i}", f"Error {i}")

        assert tracker.get_failure_count() == 5  # Only last 5 remain

    def test_timestamp_preservation(self):
        """Test that timestamps are preserved and recent ones are kept."""
        tracker = FailureTracker(max_records=10)

        # Add failures in order
        tracker.record_failure("cmd1", "Error 1")
        tracker.record_failure("cmd2", "Error 2")
        tracker.record_failure("cmd3", "Error 3")

        # Add one more to trigger trimming
        tracker.record_failure("cmd4", "Error 4")
        tracker.record_failure("cmd5", "Error 5")  # This should be kept

        assert tracker.get_failure_count() == 5
        assert "cmd5" in tracker.failures

    def test_failure_record_dataclass(self):
        """Test that FailureRecord is a proper dataclass."""
        record = FailureRecord(
            tool_name="test",
            error_message="Test error",
            attempts=1
        )

        assert record.tool_name == "test"
        assert record.error_message == "Test error"
        assert record.attempts == 1

        # Check timestamp
        assert isinstance(record.timestamp, datetime)

    def test_failure_record_defaults(self):
        """Test FailureRecord default values."""
        record = FailureRecord(tool_name="test", error_message="Test error")

        assert record.attempts == 1  # Default value
        assert isinstance(record.timestamp, datetime)  # Default value

    def test_max_records_default(self):
        """Test that max_records defaults to 50."""
        tracker = FailureTracker()
        assert tracker.max_records == 50

    def test_custom_max_records(self):
        """Test that custom max_records is respected."""
        tracker = FailureTracker(max_records=10)
        assert tracker.max_records == 10

        # Add 15 failures
        for i in range(15):
            tracker.record_failure(f"cmd{i}", f"Error {i}")

        assert tracker.get_failure_count() == 10


class TestFailureTrackerIntegration:
    """Integration tests for FailureTracker."""

    def test_full_workflow(self):
        """Test a full workflow of recording and using failures."""
        tracker = FailureTracker()

        # Record some failures
        tracker.record_failure("spawn", "Tool 'xyz' not found")
        tracker.record_failure("read_file", "Permission denied")

        # Check failure exists
        assert tracker.has_failed("spawn")
        assert tracker.has_failed("read_file")

        # Get summary
        summary = tracker.get_failure_summary()
        assert "failed in previous attempts" in summary
        assert "spawn" in summary
        assert "read_file" in summary

        # Get failed commands
        commands = tracker.get_failed_commands()
        assert len(commands) == 2

        # Clear and verify
        tracker.clear()
        assert tracker.get_failure_count() == 0
        assert tracker.get_failure_summary() == ""

    def test_error_message_update(self):
        """Test that error messages are updated on repeated failures."""
        tracker = FailureTracker()
        tracker.record_failure("cmd", "First error")
        tracker.record_failure("cmd", "Second error")
        tracker.record_failure("cmd", "Third error")

        record = tracker.get_record("cmd")
        assert record.attempts == 3
        assert record.error_message == "Third error"

    def test_timestamp_difference(self):
        """Test that timestamps differ for different failures."""
        tracker = FailureTracker()
        tracker.record_failure("cmd1", "Error 1")
        tracker.record_failure("cmd2", "Error 2")

        record1 = tracker.get_record("cmd1")
        record2 = tracker.get_record("cmd2")

        assert record1.timestamp != record2.timestamp

    def test_multiple_failures_same_command(self):
        """Test handling multiple failures for the same command."""
        tracker = FailureTracker()

        # Add 5 failures for the same command
        for i in range(5):
            tracker.record_failure("cmd", f"Error {i}")

        record = tracker.get_record("cmd")
        assert record.attempts == 5
        assert record.error_message == "Error 4"  # Latest error

    def test_failed_commands_formatting(self):
        """Test that failed commands are formatted correctly."""
        tracker = FailureTracker()
        tracker.record_failure("tool1", "Error 1")
        tracker.record_failure("tool2", "Error 2")
        tracker.record_failure("tool3", "Error 3")

        commands = tracker.get_failed_commands()
        expected = [
            "Command 'tool1' failed: Error 1 (attempted 1 times)",
            "Command 'tool2' failed: Error 2 (attempted 1 times)",
            "Command 'tool3' failed: Error 3 (attempted 1 times)",
        ]

        for expected_cmd, actual_cmd in zip(expected, commands, strict=False):
            assert expected_cmd == actual_cmd

    def test_empty_failure_tracker_no_summary(self):
        """Test that empty tracker produces no summary."""
        tracker = FailureTracker()
        summary = tracker.get_failure_summary()
        assert summary == ""

    def test_failure_tracker_with_max_records(self):
        """Test failure tracker with custom max_records."""
        tracker = FailureTracker(max_records=3)

        # Add 10 failures (cmd0-cmd9)
        for i in range(10):
            tracker.record_failure(f"cmd{i}", f"Error {i}")

        # Should only have 3 records (last 3: cmd7, cmd8, cmd9)
        assert tracker.get_failure_count() == 3

        # Should be the last 3 commands
        assert "cmd7" in tracker.failures
        assert "cmd8" in tracker.failures
        assert "cmd9" in tracker.failures

        # Should not have the first 7
        assert "cmd0" not in tracker.failures
        assert "cmd1" not in tracker.failures
        assert "cmd2" not in tracker.failures

    def test_failure_tracker_preserves_metadata(self):
        """Test that failure tracker preserves tool name and error."""
        tracker = FailureTracker()
        tracker.record_failure("my-custom-command", "Access denied: File not found")

        record = tracker.get_record("my-custom-command")
        assert record.tool_name == "my-custom-command"
        assert record.error_message == "Access denied: File not found"
        assert record.attempts == 1

    def test_failure_tracker_concurrent_failures(self):
        """Test handling multiple failures for different tools."""
        tracker = FailureTracker()

        tools = ["tool1", "tool2", "tool3", "tool4", "tool5"]
        errors = ["Error 1", "Error 2", "Error 3", "Error 4", "Error 5"]

        for tool, error in zip(tools, errors, strict=False):
            tracker.record_failure(tool, error)

        assert tracker.get_failure_count() == 5

        for tool in tools:
            assert tracker.has_failed(tool)

        commands = tracker.get_failed_commands()
        assert len(commands) == 5

    def test_failure_tracker_clear_all(self):
        """Test clearing all failures."""
        tracker = FailureTracker()

        # Add failures
        tracker.record_failure("cmd1", "Error 1")
        tracker.record_failure("cmd2", "Error 2")
        tracker.record_failure("cmd3", "Error 3")

        assert tracker.get_failure_count() == 3

        # Clear
        tracker.clear()

        # Verify all cleared
        assert tracker.get_failure_count() == 0
        assert tracker.failures == {}
        assert tracker.get_failed_commands() == []
        assert tracker.get_failure_summary() == ""

    def test_failure_tracker_get_record_after_clear(self):
        """Test that get_record returns None after clearing."""
        tracker = FailureTracker()
        tracker.record_failure("cmd1", "Error 1")

        record = tracker.get_record("cmd1")
        assert record is not None

        tracker.clear()
        assert tracker.get_record("cmd1") is None

    def test_failure_tracker_has_failed_after_clear(self):
        """Test that has_failed returns False after clearing."""
        tracker = FailureTracker()
        tracker.record_failure("cmd1", "Error 1")

        assert tracker.has_failed("cmd1")

        tracker.clear()
        assert not tracker.has_failed("cmd1")
