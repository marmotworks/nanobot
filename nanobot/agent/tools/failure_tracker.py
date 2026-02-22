"""
FailureTracker - Tracks failed tool calls to prevent repeated failures.

Records tool execution failures with error messages and makes this information
available to the agent's context so it can learn from mistakes.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path


@dataclass
class FailureRecord:
    """Records a failed tool call."""
    tool_name: str
    error_message: str
    timestamp: datetime = field(default_factory=datetime.now)
    attempts: int = 1


class FailureTracker:
    """Tracks tool execution failures to prevent repeated failures."""

    def __init__(self, max_records: int = 50):
        """
        Initialize the FailureTracker.

        Args:
            max_records: Maximum number of failure records to keep
        """
        self.max_records = max_records
        self.failures: Dict[str, FailureRecord] = {}  # tool_name -> FailureRecord

    def record_failure(self, tool_name: str, error_message: str) -> None:
        """
        Record a failed tool call.

        Args:
            tool_name: Name of the tool that failed
            error_message: Error message from the failure
        """
        if tool_name in self.failures:
            # Increment attempt count
            self.failures[tool_name].attempts += 1
            self.failures[tool_name].error_message = error_message
        else:
            # Create new failure record
            self.failures[tool_name] = FailureRecord(
                tool_name=tool_name,
                error_message=error_message
            )

        # Trim old records if we exceed max
        if len(self.failures) > self.max_records:
            # Sort by timestamp (oldest first) and remove oldest
            sorted_failures = sorted(
                self.failures.items(),
                key=lambda x: x[1].timestamp
            )
            self.failures = dict(sorted_failures[-self.max_records:])

    def get_failed_commands(self) -> List[str]:
        """
        Get formatted list of failed commands for inclusion in prompts.

        Returns:
            List of formatted strings like:
            "- Command 'xyz' failed: [error message] (attempted X times)"
        """
        if not self.failures:
            return []

        formatted = []
        for tool_name, record in self.failures.items():
            formatted.append(
                f"Command '{tool_name}' failed: {record.error_message} "
                f"(attempted {record.attempts} times)"
            )

        return formatted

    def get_failure_summary(self) -> str:
        """
        Get a summary of all failures for the system prompt.

        Returns:
            Formatted summary string
        """
        failed_commands = self.get_failed_commands()
        if not failed_commands:
            return ""

        return (
            f"\nNote: The following commands have failed in previous attempts:\n"
            f"{chr(10).join(failed_commands)}\n"
            f"Please avoid retrying these commands."
        )

    def get_failure_count(self) -> int:
        """Return the total number of unique tools that have failed."""
        return len(self.failures)

    def clear(self) -> None:
        """Clear all failure records."""
        self.failures.clear()

    def get_record(self, tool_name: str) -> Optional[FailureRecord]:
        """Get a specific failure record."""
        return self.failures.get(tool_name)

    def has_failed(self, tool_name: str) -> bool:
        """Check if a tool has failed before."""
        return tool_name in self.failures