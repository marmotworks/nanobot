from __future__ import annotations

from collections.abc import Callable  # noqa: TC003
from dataclasses import dataclass, field
from pathlib import Path  # noqa: TC003
import re
import time

LOG_PATTERN = re.compile(
    r"^(?P<timestamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d+)"
    r"\s+\|\s+(?P<level>\w+)\s+\|"
    r"\s+(?P<logger>[^\s]+)"
    r"\s+-\s+(?P<message>.+)$"
)

ALERT_LEVELS = {"WARNING", "ERROR", "CRITICAL"}


@dataclass
class LogEvent:
    timestamp: str
    level: str
    logger: str
    message: str
    raw: str


@dataclass
class LogWatcher:
    log_file: Path
    on_event: Callable[[LogEvent], None]
    poll_interval: float = 1.0
    _running: bool = field(default=False, init=False)
    _position: int = field(default=0, init=False)

    def parse_line(self, line: str) -> LogEvent | None:
        """Parse a loguru-formatted log line. Returns None if not parseable."""
        m = LOG_PATTERN.match(line.rstrip())
        if not m:
            return None
        return LogEvent(
            timestamp=m.group("timestamp"),
            level=m.group("level").strip(),
            logger=m.group("logger"),
            message=m.group("message"),
            raw=line.rstrip(),
        )

    def start(self) -> None:
        """Start tailing the log file. Blocks until stop() is called."""
        self._running = True
        if self.log_file.exists():
            self._position = self.log_file.stat().st_size
        while self._running:
            self._poll()
            time.sleep(self.poll_interval)

    def stop(self) -> None:
        """Stop the watcher loop."""
        self._running = False

    def _poll(self) -> None:
        if not self.log_file.exists():
            return
        size = self.log_file.stat().st_size
        if size < self._position:
            self._position = 0  # log rotated
        if size == self._position:
            return
        with self.log_file.open("r", encoding="utf-8", errors="replace") as f:
            f.seek(self._position)
            for line in f:
                event = self.parse_line(line)
                if event and event.level in ALERT_LEVELS:
                    self.on_event(event)
            self._position = f.tell()
