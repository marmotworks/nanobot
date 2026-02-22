#!/usr/bin/env python3
"""Verify dispatch state by cross-referencing BACKLOG.md [~] markers."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
import re


def parse_backlog(backlog_path: Path) -> list[dict]:
    """Parse BACKLOG.md and extract in-progress milestones.

    Args:
        backlog_path: Path to BACKLOG.md file.

    Returns:
        List of dicts with task_num, task_title, milestone_num,
        milestone_desc, and optional start_date.
    """
    backlog = backlog_path.read_text()
    lines = backlog.split("\n")

    milestones: list[dict] = []
    current_task_num: int | None = None
    current_task_title: str | None = None

    for line in lines:
        # Match task headers: "## Task N:" or "## Task N."
        task_match = re.match(r"^## Task\s+(\d+)[\s:.]?(.*)", line)
        if task_match:
            current_task_num = int(task_match.group(1))
            current_task_title = task_match.group(2).strip()
            continue

        # Match [~] milestone lines
        milestone_match = re.match(r"^\s*-\s+\[~\]\s+(\d+\.\d+)\s+(.*)", line)
        if milestone_match and current_task_num is not None:
            milestones.append({
                "task_num": current_task_num,
                "task_title": current_task_title or "",
                "milestone_num": milestone_match.group(1),
                "milestone_desc": milestone_match.group(2).strip(),
                "start_date": None,
            })

    return milestones


def format_date(date: datetime | None) -> str:
    """Format a date relative to now, or return 'unknown' if None."""
    if date is None:
        return "unknown"
    delta = datetime.now() - date
    days = delta.days
    hours = delta.seconds // 3600
    parts: list[str] = []
    if days > 0:
        parts.append(f"{days} day{'s' if days != 1 else ''}")
    if hours > 0:
        parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
    if not parts:
        return "less than an hour"
    return ", ".join(parts)


def main() -> int:
    """Main entry point for verify_dispatch script."""
    backlog_path = Path.home() / ".nanobot" / "workspace" / "memory" / "BACKLOG.md"

    if not backlog_path.exists():
        print(f"Error: BACKLOG.md not found at {backlog_path}")
        return 1

    milestones = parse_backlog(backlog_path)

    if not milestones:
        print("✅ No in-progress milestones. Dispatch state is clean.")
        return 0

    print("⚠️  In-progress milestones (subagents may be running):")
    print()

    for m in milestones:
        print(f"  Task {m['task_num']}: {m['task_title']}")
        start_info = f" ({format_date(m['start_date'])} ago)" if m["start_date"] else ""
        print(f"    [~] {m['milestone_num']}  {m['milestone_desc']}{start_info}")
        print()

    print(f"Total: {len(milestones)} in-progress milestone(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
