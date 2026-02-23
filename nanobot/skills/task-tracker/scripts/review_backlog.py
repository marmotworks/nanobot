#!/usr/bin/env python3
"""Backlog review script — applies REVIEW_CHECKLIST.md rules to BACKLOG.md."""

from __future__ import annotations

from pathlib import Path
import re
import sqlite3
import sys


def match_milestone_label(label: str, milestone_num: str) -> bool:
    """Return True if label matches the given milestone number.

    Matches if the label equals milestone_num exactly, or starts with
    '{milestone_num} ' (with trailing space, to avoid '30.1' matching '30.10').
    """
    return label == milestone_num or label.startswith(f"{milestone_num} ")


BACKLOG_PATH = Path.home() / ".nanobot/workspace/memory/BACKLOG.md"
DB_PATH = Path.home() / ".nanobot/workspace/subagents.db"


def get_active_labels(db_path: Path) -> set[str]:
    """Return labels of subagents currently running."""
    if not db_path.exists():
        return set()
    try:
        conn = sqlite3.connect(str(db_path))
        rows = conn.execute(
            "SELECT label FROM subagents WHERE status IN ('running', 'pending')"
        ).fetchall()
        conn.close()
        return {row[0] for row in rows if row[0]}
    except Exception:
        return set()


def get_completed_milestones(content: str) -> set[str]:
    """Return set of milestone numbers marked [x]."""
    completed = set()
    for match in re.finditer(r"- \[x\] (\d+\.\d+)", content):
        completed.add(match.group(1))
    return completed


def main() -> int:
    if not BACKLOG_PATH.exists():
        print("BACKLOG.md not found")
        return 1

    content = BACKLOG_PATH.read_text()
    original = content
    active_labels = get_active_labels(DB_PATH)
    completed = get_completed_milestones(content)

    blockers_cleared = 0
    orphans_reset = 0

    # Rule 1: Clear completed blockers
    def clear_blocker(m: re.Match) -> str:
        nonlocal blockers_cleared
        blocker_num = m.group(1)
        if blocker_num in completed:
            blockers_cleared += 1
            return m.group(0).replace(f"Blocker: {blocker_num}", "Blocker: none")
        return m.group(0)

    content = re.sub(
        r"(- \[[ ]\] \d+\.\d+.*?\n(?:.*?\n)*?.*?Blocker: )(\d+\.\d+)",
        clear_blocker,
        content,
    )

    # Rule 2: Reset orphaned [~] markers
    lines = content.split("\n")
    new_lines = []
    for line in lines:
        m = re.match(r"(\s*- \[~\] )(\d+\.\d+)(.*)", line)
        if m:
            milestone_num = m.group(2)
            is_active = any(
                match_milestone_label(label, milestone_num)
                for label in active_labels
            )
            if not is_active:
                line = m.group(1).replace("[~]", "[ ]") + m.group(2) + m.group(3)
                orphans_reset += 1
        new_lines.append(line)
    content = "\n".join(new_lines)

    if content != original:
        BACKLOG_PATH.write_text(content)

    print(f"Blockers cleared: {blockers_cleared}")
    print(f"Orphaned [~] markers reset: {orphans_reset}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
