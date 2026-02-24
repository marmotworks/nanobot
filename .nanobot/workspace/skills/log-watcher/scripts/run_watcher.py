from __future__ import annotations

# ruff: noqa: I001
import argparse
import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

# sys.path manipulation required — scripts dir is not an installable package
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from discord_alert import DiscordAlerter
from log_history import LogHistory
from log_watcher import LogEvent, LogWatcher

DEFAULT_LOG_FILE = Path.home() / ".nanobot" / "workspace" / "logs" / "nanobot.log"
DEFAULT_HISTORY_FILE = Path.home() / ".nanobot" / "workspace" / "log_history.json"


def make_handler(history: LogHistory, alerter: DiscordAlerter | None) -> Callable[[LogEvent], None]:
    def handle(event: LogEvent) -> None:
        history.add({
            "timestamp": event.timestamp,
            "level": event.level,
            "logger": event.logger,
            "message": event.message,
        })
        if alerter:
            alerter.send(event)
    return handle


def main() -> None:
    parser = argparse.ArgumentParser(description="Watch nanobot log file for errors")
    parser.add_argument("--log-file", type=Path, default=DEFAULT_LOG_FILE)
    parser.add_argument("--history-file", type=Path, default=DEFAULT_HISTORY_FILE)
    parser.add_argument("--webhook-url", type=str, default=None, help="Discord webhook URL for alerts")
    parser.add_argument("--poll-interval", type=float, default=1.0)
    args = parser.parse_args()

    history = LogHistory(history_file=args.history_file)
    alerter = DiscordAlerter(webhook_url=args.webhook_url) if args.webhook_url else None
    handler = make_handler(history, alerter)

    watcher = LogWatcher(log_file=args.log_file, on_event=handler, poll_interval=args.poll_interval)
    print(f"Watching {args.log_file} ...")
    watcher.start()


if __name__ == "__main__":
    main()
