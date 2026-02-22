#!/usr/bin/env python3
"""Verify dispatch state by cross-referencing BACKLOG.md [~] markers."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
import re
import sqlite3


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
    now = datetime.now()
    if date.tzinfo is not None:
        now = now.replace(tzinfo=date.tzinfo)
    delta = now - date
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


def query_registry(db_path: Path) -> list[dict]:
    """Query SubagentRegistry for active subagents.

    Args:
        db_path: Path to subagents.db SQLite database.

    Returns:
        List of dicts with keys: id, label, status, spawned_at.
        Returns empty list with warning if DB doesn't exist.
    """
    if not db_path.exists():
        print(f"Warning: SubagentRegistry DB not found at {db_path}")
        print("Continuing with BACKLOG.md-only verification.\n")
        return []

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, label, status, spawned_at FROM subagents "
        "WHERE status IN ('pending', 'running')"
    )
    rows = cursor.fetchall()
    conn.close()

    results: list[dict] = []
    for row in rows:
        id_val, label, status, spawned_at_str = row
        try:
            spawned_at = datetime.fromisoformat(spawned_at_str.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            spawned_at = None
        results.append({
            "id": id_val,
            "label": label,
            "status": status,
            "spawned_at": spawned_at,
        })
    return results


def main() -> int:
    """Main entry point for verify_dispatch script."""
    backlog_path = Path.home() / ".nanobot" / "workspace" / "memory" / "BACKLOG.md"
    registry_path = Path.home() / ".nanobot" / "workspace" / "subagents.db"

    if not backlog_path.exists():
        print(f"Error: BACKLOG.md not found at {backlog_path}")
        return 1

    milestones = parse_backlog(backlog_path)
    active_subagents = query_registry(registry_path)

    # Find STALE milestones (in BACKLOG but no matching subagent)
    stale_milestones: list[dict] = []
    matched_milestones: list[tuple[dict, dict]] = []
    for m in milestones:
        milestone_num = m["milestone_num"]
        matched_subagent = None
        for sub in active_subagents:
            if milestone_num in sub["label"]:
                matched_subagent = sub
                break
        if matched_subagent:
            matched_milestones.append((m, matched_subagent))
        else:
            stale_milestones.append(m)

    # Find ORPHANED subagents (active but no matching milestone)
    orphaned_subagents: list[dict] = []
    for sub in active_subagents:
        matched_milestone = None
        for m in milestones:
            if m["milestone_num"] in sub["label"]:
                matched_milestone = m
                break
        if matched_milestone is None:
            orphaned_subagents.append(sub)

    # Print report
    print("=== Dispatch Verification ===")
    print()

    print(f"In-progress milestones ([~] in BACKLOG.md): {len(milestones)}")
    for m in milestones:
        print(f"  [~] {m['milestone_num']}  {m['milestone_desc']}")
    print()

    print(f"Active subagents in registry: {len(active_subagents)}")
    for sub in active_subagents:
        spawned_str = format_date(sub["spawned_at"])
        print(f"  {sub['id']} | {sub['label']} | {sub['status']} | spawned {spawned_str}")
    print()

    print("Issues found:")
    if not stale_milestones and not orphaned_subagents:
        print("  ✓ No issues found.")
    else:
        # STALE milestones
        if stale_milestones:
            for m in stale_milestones:
                print(f"  ⚠  STALE: [~] {m['milestone_num']} — no active subagent found "
                      "(safe to reset to [ ])")
        else:
            print("  (no STALE milestones)")

        # Matched milestones
        if matched_milestones:
            for m, sub in matched_milestones:
                print(f"  ✓  OK: [~] {m['milestone_num']} — matched to subagent {sub['id']}")
        else:
            print("  (no matched milestones)")

        # ORPHANED subagents
        if orphaned_subagents:
            print()
            print("Orphaned subagents (active in registry, no [~] in BACKLOG.md):")
            for sub in orphaned_subagents:
                print(f"  ⚠  ORPHANED: {sub['id']} — {sub['label']}")
        else:
            print()
            print("Orphaned subagents (active in registry, no [~] in BACKLOG.md):")
            print("  (none)")

    print()
    print("Run 'status.py' for full backlog overview.")

    # Determine exit code
    if stale_milestones or orphaned_subagents:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
