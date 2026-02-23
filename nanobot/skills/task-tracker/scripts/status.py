#!/usr/bin/env python3
"""
Task Tracker Status Script

Reads ~/.nanobot/workspace/memory/BACKLOG.md and prints a clean status table.
"""

from __future__ import annotations

import os
import re
import sys

BACKLOG_PATH = os.path.expanduser("~/.nanobot/workspace/memory/BACKLOG.md")


def read_backlog() -> str:
    try:
        with open(BACKLOG_PATH) as f:
            return f.read()
    except FileNotFoundError:
        print(f"Error: BACKLOG.md not found at {BACKLOG_PATH}", file=sys.stderr)
        sys.exit(1)


def normalize_status(raw: str) -> str:
    """Collapse freeform status text into a canonical label."""
    s = raw.strip()
    if "Complete" in s or "✅" in s:
        return "Complete ✅"
    if "Blocked" in s:
        return "Blocked"
    if "Planning" in s:
        return "Planning"
    if "In progress" in s or "in progress" in s or "Partially" in s:
        return "In progress"
    if "Not started" in s:
        return "Not started"
    # Fallback: truncate to 20 chars
    return s[:20]


def parse_tasks(content: str) -> list[dict]:
    tasks = []
    lines = content.split("\n")
    i = 0

    while i < len(lines):
        match = re.match(r"^## Task (\d+)[:\s](.+)$", lines[i].strip())
        if match:
            task_num = int(match.group(1))
            title = match.group(2).strip()
            # Strip trailing ✅ or "Complete" from title
            title = re.sub(r"\s*✅.*$", "", title).strip()

            task_data: dict = {
                "number": task_num,
                "title": title,
                "status": "Not started",
                "blocker": None,
                "milestones": [],
            }

            i += 1
            while i < len(lines):
                line = lines[i]
                if re.match(r"^## (Task \d+|Completed)", line.strip()):
                    i -= 1  # let outer loop re-process this header line
                    break

                status_match = re.match(r"\*\*Status\*\*: (.+)$", line.strip())
                if status_match:
                    task_data["status"] = normalize_status(status_match.group(1))

                blocker_match = re.match(r"\*\*Blocker\*\*: (.+)$", line.strip())
                if blocker_match:
                    task_data["blocker"] = blocker_match.group(1).strip()

                milestone_match = re.match(r"^- \[([ x~])\] (\d+\.\d+) (.+)$", line.strip())
                if milestone_match:
                    marker = milestone_match.group(1)
                    m_num = milestone_match.group(2)
                    desc = milestone_match.group(3).strip()
                    milestone: dict = {
                        "number": m_num,
                        "status": marker,
                        "description": desc,
                        "blocker": None,
                        "criterion": "",
                        "file": "",
                        "note": "",
                    }
                    # Scan continuation lines for Criterion:, File:, Blocker:, Note:
                    j = i + 1
                    while j < len(lines):
                        cont = lines[j].strip()
                        if not cont or re.match(r"^- \[([ x~])\]", cont):
                            break
                        if cont.startswith("Criterion:"):
                            milestone["criterion"] = cont[10:].strip()
                        elif cont.startswith("File:"):
                            milestone["file"] = cont[5:].strip()
                        elif cont.startswith("Blocker:"):
                            milestone["blocker"] = cont[8:].strip()
                        elif cont.startswith("Note:"):
                            milestone["note"] = cont[5:].strip()
                        j += 1
                    task_data["milestones"].append(milestone)
                    i = j - 1

                i += 1

            tasks.append(task_data)
        i += 1

    return tasks


def get_next_action(task: dict) -> str:
    status = task["status"]

    if status == "Complete ✅":
        return "—"

    if status == "Blocked":
        blocker = task.get("blocker") or ""
        return f"Blocked: {blocker}" if blocker else "Blocked"

    milestones = task["milestones"]

    if not milestones:
        if status in ("Not started", "Planning"):
            return "Planning needed"
        return "—"

    # In-progress marker
    for m in milestones:
        if m["status"] == "~":
            return f"In progress: {m['number']}"

    # Next unchecked
    for m in milestones:
        if m["status"] == " ":
            b = m.get("blocker") or "none"
            if b and b != "none":
                return f"Waiting: {m['number']} (blocked on {b})"
            return f"Next: {m['number']} {m['description']}"

    # All done
    return "All milestones done ✅"


def format_table(tasks: list[dict]) -> str:
    col_task = 4
    col_title = max(20, max(len(t["title"]) for t in tasks))
    col_title = min(col_title, 38)
    col_status = 14
    col_ms = 10
    col_next = 50

    def row(num: str, title: str, status: str, ms: str, nxt: str) -> str:
        return (
            num.rjust(col_task)
            + "  "
            + title[:col_title].ljust(col_title)
            + "  "
            + status[:col_status].ljust(col_status)
            + "  "
            + ms[:col_ms].ljust(col_ms)
            + "  "
            + nxt[:col_next]
        )

    header = row("Task", "Title", "Status", "Milestones", "Next Action")
    sep = row("-" * col_task, "-" * col_title, "-" * col_status, "-" * col_ms, "-" * col_next)

    rows = [header, sep]
    for t in sorted(tasks, key=lambda x: x["number"]):
        total = len(t["milestones"])
        done = sum(1 for m in t["milestones"] if m["status"] == "x")
        ms_str = f"{done}/{total}" if total > 0 else "—"
        rows.append(row(str(t["number"]), t["title"], t["status"], ms_str, get_next_action(t)))

    return "\n".join(rows)


def main() -> None:
    content = read_backlog()
    tasks = parse_tasks(content)

    if not tasks:
        print("No tasks found in BACKLOG.md")
        return

    print(format_table(tasks))


if __name__ == "__main__":
    main()
