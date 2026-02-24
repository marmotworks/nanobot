from __future__ import annotations

from collections import deque
import json
from pathlib import Path

DEFAULT_HISTORY_FILE = Path.home() / ".nanobot" / "workspace" / "log_history.json"
MAX_HISTORY = 500


class LogHistory:
    def __init__(self, history_file: Path | str = DEFAULT_HISTORY_FILE, max_size: int = MAX_HISTORY) -> None:
        self.history_file = Path(history_file)
        self.max_size = max_size
        self._events: deque[dict[str, str]] = deque(maxlen=max_size)
        self._load()

    def _load(self) -> None:
        """Load existing history from disk if present."""
        if self.history_file.exists():
            try:
                data = json.loads(self.history_file.read_text(encoding="utf-8"))
                for entry in data[-self.max_size:]:
                    self._events.append(entry)
            except (json.JSONDecodeError, KeyError):
                self._events.clear()

    def add(self, event: dict[str, str]) -> None:
        """Add a log event dict to history and persist to disk."""
        self._events.append(event)
        self._save()

    def append(self, event: dict[str, str]) -> None:
        """Alias for add()."""
        self.add(event)

    def recent(self, n: int) -> list[dict[str, str]]:
        """Return the most recent n events."""
        return list(self._events)[-n:]

    def _save(self) -> None:
        """Persist current history to disk."""
        self.history_file.parent.mkdir(parents=True, exist_ok=True)
        self.history_file.write_text(
            json.dumps(list(self._events), indent=2),
            encoding="utf-8",
        )

    def get_all(self) -> list[dict[str, str]]:
        """Return all events as a list (oldest first)."""
        return list(self._events)

    def clear(self) -> None:
        """Clear all history from memory and disk."""
        self._events.clear()
        if self.history_file.exists():
            self.history_file.unlink()
