from __future__ import annotations

from dataclasses import dataclass, field
import time
from typing import TYPE_CHECKING

import httpx

if TYPE_CHECKING:
    from log_watcher import LogEvent

RATE_LIMIT_SECONDS = 300  # 5 minutes


@dataclass
class DiscordAlerter:
    webhook_url: str
    rate_limit_seconds: float = RATE_LIMIT_SECONDS
    _last_sent: dict[str, float] = field(default_factory=dict, init=False)

    def should_send(self, event: LogEvent) -> bool:
        """Return True if enough time has passed since last alert for this level+logger combo."""
        key = f"{event.level}:{event.logger}"
        now = time.monotonic()
        last = self._last_sent.get(key, 0.0)
        return (now - last) >= self.rate_limit_seconds

    def send(self, event: LogEvent) -> bool:
        """Send a Discord webhook alert. Returns True if sent, False if rate-limited or failed."""
        if not self.should_send(event):
            return False
        key = f"{event.level}:{event.logger}"
        payload = {
            "content": f"**[{event.level}]** `{event.logger}`\n```\n{event.message}\n```\n*{event.timestamp}*"
        }
        try:
            resp = httpx.post(self.webhook_url, json=payload, timeout=5.0)
            resp.raise_for_status()
            self._last_sent[key] = time.monotonic()
            return True
        except Exception:
            return False
