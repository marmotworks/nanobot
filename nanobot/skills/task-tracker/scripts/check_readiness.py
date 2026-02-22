#!/usr/bin/env python3
"""
Readiness Check Script

Scans BACKLOG.md, identifies tasks and milestones whose blockers are complete,
automatically clears those blockers, and reports what changed.
"""

from __future__ import annotations

import os
import re
import sys

BACKLOG_PATH = os.path.expanduser("~/.nanobot/workspace/memory/BACKLOG.md")


def read_backlog() -> str:
    """Read the BACKLOG.md file content."""
    try:
        with open(BACKLOG_PATH) as f:
            return f.read()
    except FileNotFoundError:
        print(f"Error: BACKLOG.md not found at {BACKLOG_PATH}", file=sys.stderr)
        sys.exit(1)
    except OSError as e:
        print(f"Error reading BACKLOG.md: {e}", file=sys.stderr)
        sys.exit(1)


def parse_tasks(content: str) -> list[dict]:
    """Parse tasks from BACKLOG.md content."""
    tasks = []
    lines = content.split("\n")
    i = 0

    while i < len(lines):
        match = re.match(r"^## Task (\d+)[:\s](.+)$", lines[i].strip())
        if match:
            task_num = int(match.group(1))
            title = match.group(2).strip()
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
                    i -= 1
                    break

                status_match = re.match(r"\*\*Status\*\*: (.+)$", line.strip())
                if status_match:
                    task_data["status"] = status_match.group(1).strip()

                blocker_match = re.match(r"\*\*Blocker\*\*: (.+)$", line.strip())
                if blocker_match:
                    task_data["blocker"] = blocker_match.group(1).strip()

                milestone_match = re.match(
                    r"^- \[([ x~])\] (\d+\.\d+) (.+)$", line.strip()
                )
                if milestone_match:
                    marker = milestone_match.group(1)
                    m_num = milestone_match.group(2)
                    desc = milestone_match.group(3).strip()
                    milestone: dict = {
                        "number": m_num,
                        "status": marker,
                        "description": desc,
                        "blocker": None,
                    }
                    j = i + 1
                    while j < len(lines):
                        cont = lines[j].strip()
                        if not cont or re.match(r"^- \[([ x~])\]", cont):
                            break
                        if cont.startswith("Blocker:"):
                            milestone["blocker"] = cont[8:].strip()
                        j += 1
                    task_data["milestones"].append(milestone)
                    i = j - 1

                i += 1

            tasks.append(task_data)
        i += 1

    return tasks


def is_task_complete(status: str) -> bool:
    """Check if a task status indicates completion."""
    return "Complete" in status or "✅" in status


def is_milestone_complete(marker: str) -> bool:
    """Check if a milestone marker indicates completion."""
    return marker == "x"


def find_complete_tasks_and_milestones(
    tasks: list[dict],
) -> tuple[set[int], dict[str, bool]]:
    """Build sets of complete task numbers and milestone numbers."""
    complete_tasks = set()
    for task in tasks:
        if is_task_complete(task["status"]):
            complete_tasks.add(task["number"])

    complete_milestones: dict[str, bool] = {}
    for task in tasks:
        for milestone in task["milestones"]:
            if is_milestone_complete(milestone["status"]):
                complete_milestones[milestone["number"]] = True

    return complete_tasks, complete_milestones


def check_and_clear_task_blockers(
    tasks: list[dict],
    complete_tasks: set[int],
    content: str,
) -> tuple[str, list[str]]:
    """Check task blockers and clear those pointing to complete tasks."""
    changes: list[str] = []
    new_content = content

    for task in tasks:
        if task["blocker"] is None:
            continue

        blocker_match = re.match(r"Task (\d+)", task["blocker"])
        if blocker_match:
            blocker_num = int(blocker_match.group(1))
            if blocker_num in complete_tasks:
                old_line = f"**Blocker**: {task['blocker']}"
                new_line = "**Blocker**: none"
                new_content = new_content.replace(old_line, new_line, 1)
                changes.append(
                    f"Task {task['number']}: {task['title']} — "
                    f'blocker "Task {blocker_num}" cleared (Task {blocker_num} is complete)'
                )

    return new_content, changes


def check_and_clear_milestone_blockers(
    tasks: list[dict],
    complete_milestones: dict[str, bool],
    content: str,
) -> tuple[str, list[str]]:
    """Check milestone blockers and clear those pointing to complete milestones."""
    changes: list[str] = []
    new_content = content

    for task in tasks:
        for milestone in task["milestones"]:
            if milestone["blocker"] is None:
                continue

            if milestone["blocker"] in complete_milestones:
                old_line = f"Blocker: {milestone['blocker']}"
                new_line = "Blocker: none"
                new_content = new_content.replace(old_line, new_line, 1)
                changes.append(
                    f"Milestone {milestone['number']}: {milestone['description']} — "
                    f'blocker "{milestone["blocker"]}" cleared ({milestone["blocker"]} is [x])'
                )

    return new_content, changes


def write_backlog(content: str) -> None:
    """Write the updated content back to BACKLOG.md."""
    try:
        with open(BACKLOG_PATH, "w") as f:
            f.write(content)
    except OSError as e:
        print(f"Error writing BACKLOG.md: {e}", file=sys.stderr)
        sys.exit(1)


def main() -> None:
    content = read_backlog()
    tasks = parse_tasks(content)

    complete_tasks, complete_milestones = find_complete_tasks_and_milestones(tasks)

    new_content, task_changes = check_and_clear_task_blockers(
        tasks, complete_tasks, content
    )
    new_content, milestone_changes = check_and_clear_milestone_blockers(
        tasks, complete_milestones, new_content
    )

    total_changes = len(task_changes) + len(milestone_changes)

    if total_changes == 0:
        print("✅ All blockers are current. No changes needed.")
        return

    if new_content != content:
        write_backlog(new_content)

    print("=== Readiness Check ===\n")
    print("Blockers cleared:")

    for change in task_changes:
        print(f"  {change}")
    for change in milestone_changes:
        print(f"  {change}")

    print(f"\nUpdated BACKLOG.md with {total_changes} change(s).")


if __name__ == "__main__":
    main()
