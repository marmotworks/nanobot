#!/bin/bash
# Dispatch Cron Script
# Runs readiness check, then marks the next ready milestone as [~] (in-progress)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKLOG_PATH="$HOME/.nanobot/workspace/memory/BACKLOG.md"
REGISTRY_DB="$HOME/.nanobot/workspace/subagents.db"

# Phase 1: Clear stale blockers
echo "=== Dispatch Cron ==="
echo "Running readiness check..."
python3 "$SCRIPT_DIR/check_readiness.py"
echo ""

# Phase 2: Find and mark next ready milestone as in-progress
echo "Checking for ready milestones..."

# Write the Python script to a temp file to avoid quoting issues
cat > /tmp/find_ready_milestone.py << 'PYTHON_SCRIPT'
import sys
import re
import sqlite3
import importlib.util

BACKLOG_PATH = '/Users/mhall/.nanobot/workspace/memory/BACKLOG.md'
REGISTRY_DB = '/Users/mhall/.nanobot/workspace/subagents.db'

# Dynamically import status.py functions
spec = importlib.util.spec_from_file_location("status", "/Users/mhall/Workspaces/nanobot/nanobot/skills/task-tracker/scripts/status.py")
status = importlib.util.module_from_spec(spec)
spec.loader.exec_module(status)

read_backlog = status.read_backlog
parse_tasks = status.parse_tasks

content = read_backlog()
tasks = parse_tasks(content)

def check_subagent_completed(milestone_num: str, milestone_text: str) -> bool:
    """Check if a subagent has already completed this task."""
    try:
        conn = sqlite3.connect(REGISTRY_DB)
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(
            "SELECT status FROM subagents WHERE (label = ? OR label LIKE ?) AND status IN ('completed', 'ok')",
            (milestone_num, f"{milestone_num}%"),
        )
        row = cursor.fetchone()
        conn.close()
        return row is not None
    except sqlite3.OperationalError:
        return False

def mark_milestone_done(milestone_num: str) -> bool:
    """Mark a milestone as [x] done in BACKLOG.md."""
    pattern = rf'- \[~\] ({re.escape(milestone_num)} )'
    replacement = f'- [x] {milestone_num} '

    with open(BACKLOG_PATH, 'r') as f:
        lines = f.readlines()

    updated = False
    for i, line in enumerate(lines):
        if re.match(pattern, line):
            lines[i] = re.sub(pattern, replacement, line)
            updated = True
            break

    if updated:
        with open(BACKLOG_PATH, 'w') as f:
            f.writelines(lines)
        return True
    return False

# Phase 2a: Check [~] milestones for completed subagents
for task in sorted(tasks, key=lambda t: t['number']):
    if 'Complete' in task['status'] or task['status'] == 'Blocked':
        continue
    for m in task['milestones']:
        milestone_num = m['number']
        milestone_text = m.get('text', '')

        if m['status'] == '~' and milestone_text:
            # Milestone is in-progress — check if subagent already completed
            if check_subagent_completed(milestone_num, milestone_text):
                print(f'Found completed subagent for {milestone_num}')
                if mark_milestone_done(milestone_num):
                    print(f'Marked {milestone_num} as completed')
                    continue  # Skip dispatch for this milestone
                else:
                    print(f'Warning: Could not mark {milestone_num} as done')

# Phase 2b: Find and mark next ready [ ] milestone as in-progress
for task in sorted(tasks, key=lambda t: t['number']):
    if 'Complete' in task['status'] or task['status'] == 'Blocked':
        continue
    for m in task['milestones']:
        milestone_num = m['number']

        # Skip if already in-progress (we just checked those)
        if m['status'] == '~':
            continue

        if m['status'] == ' ' and (not m.get('blocker') or m.get('blocker') == 'none'):
            # Found a ready milestone - mark it as [~] in BACKLOG.md
            milestone_text = m.get('text', '')
            criterion = m.get('criterion', '')
            file_path = m.get('file', '')
            blocker = m.get('blocker', 'none')

            # Print READY line
            print(f'READY:{milestone_num}:{task["number"]}')

            # Print full milestone text as TASK_BRIEF
            task_brief = f"## Milestone {milestone_num}: {milestone_text}\nCriterion: {criterion}\nFile: {file_path}\nBlocker: {blocker}"
            print(f'TASK_BRIEF:{task_brief}')

            # Edit BACKLOG.md to mark as in-progress
            pattern = rf'- \[ \] ({re.escape(milestone_num)} )'
            replacement = f'- [~] {milestone_num} '

            with open(BACKLOG_PATH, 'r') as f:
                lines = f.readlines()

            updated = False
            for i, line in enumerate(lines):
                if re.match(pattern, line):
                    lines[i] = re.sub(pattern, replacement, line)
                    updated = True
                    break

            if updated:
                with open(BACKLOG_PATH, 'w') as f:
                    f.writelines(lines)
                print(f'Marked {milestone_num} as in-progress')
            else:
                print(f'Warning: Could not find milestone {milestone_num} in BACKLOG.md')
            sys.exit(0)
print('NONE')
PYTHON_SCRIPT

python3 /tmp/find_ready_milestone.py
result=$?

if [ "$result" -eq 0 ]; then
    # Milestone was found and marked [~]
    echo "Milestone marked in-progress - subagent will pick up on next dispatch or completion trigger"
else
    echo "No ready milestones found."
fi