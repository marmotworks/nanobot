"""Dispatch runner — encapsulates the full dispatch cycle programmatically with no LLM involvement."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
import fcntl
from pathlib import Path
import re
import sqlite3

from loguru import logger

BACKLOG_PATH = Path.home() / ".nanobot" / "workspace" / "memory" / "BACKLOG.md"
REGISTRY_DB = Path.home() / ".nanobot" / "workspace" / "subagents.db"
LOCK_FILE = Path.home() / ".nanobot" / "workspace" / ".backlog.lock"
SCRIPTS_DIR = Path(__file__).parent.parent / "skills" / "task-tracker" / "scripts"
MAX_CAPACITY = 3


@dataclass
class DispatchResult:
    milestone_num: str | None
    label: str | None
    task_brief: str | None
    spawn_result: str | None
    dispatched: bool


async def run_review_backlog() -> None:
    """Run review_backlog.py as a subprocess to clear stale markers and blockers."""
    script = SCRIPTS_DIR / "review_backlog.py"
    if not script.exists():
        logger.warning("review_backlog.py not found at {}", script)
        return
    proc = await asyncio.create_subprocess_exec(
        "python3", str(script),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)
    if proc.returncode != 0:
        logger.warning("review_backlog.py exited {}: {}", proc.returncode, stderr.decode())
    else:
        logger.debug("review_backlog.py: {}", stdout.decode().strip())


def get_running_count() -> int:
    """Return count of pending+running subagents in the registry."""
    if not REGISTRY_DB.exists():
        return 0
    try:
        conn = sqlite3.connect(str(REGISTRY_DB))
        cursor = conn.execute(
            "SELECT COUNT(*) FROM subagents WHERE status IN ('pending', 'running')"
        )
        count = cursor.fetchone()[0]
        conn.close()
        return count
    except Exception:
        return 0


def find_ready_milestone() -> DispatchResult | None:
    """
    Under an exclusive file lock, find the first ready [ ] milestone in BACKLOG.md
    with no unmet blockers, write [~], and return its details.
    Returns None if no ready milestone found or capacity is full.
    """
    if get_running_count() >= MAX_CAPACITY:
        logger.info("Dispatch: at capacity ({}/{}), skipping", get_running_count(), MAX_CAPACITY)
        return None

    LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(str(LOCK_FILE), "w") as lock_fh:
        fcntl.flock(lock_fh, fcntl.LOCK_EX)
        try:
            return _find_and_mark(lock_fh)
        finally:
            fcntl.flock(lock_fh, fcntl.LOCK_UN)


def _find_and_mark(lock_fh: object) -> DispatchResult | None:
    """Find and mark the next ready milestone. Called under lock."""
    if not BACKLOG_PATH.exists():
        logger.warning("BACKLOG.md not found at {}", BACKLOG_PATH)
        return None

    content = BACKLOG_PATH.read_text(encoding="utf-8")
    lines = content.splitlines(keepends=True)

    # Parse milestones: find [ ] lines with their metadata
    i = 0
    while i < len(lines):
        line = lines[i]
        m = re.match(r"^- \[ \] (\d+\.\d+) (.+)$", line.strip())
        if m:
            milestone_num = m.group(1)
            description = m.group(2).strip()
            # Read metadata lines that follow
            criterion = ""
            file_path = ""
            blocker = "none"
            note = ""
            j = i + 1
            while j < len(lines):
                cont = lines[j].strip()
                if not cont or re.match(r"^- \[", cont) or re.match(r"^##", cont):
                    break
                if cont.startswith("Criterion:"):
                    criterion = cont[len("Criterion:"):].strip()
                elif cont.startswith("File:"):
                    file_path = cont[len("File:"):].strip()
                elif cont.startswith("Blocker:"):
                    blocker = cont[len("Blocker:"):].strip()
                elif cont.startswith("Note:"):
                    note = cont[len("Note:"):].strip()
                j += 1

            # Skip if blocker is set and not "none"
            if blocker and blocker != "none":
                i += 1
                continue

            # Found a ready milestone — mark it [~]
            lines[i] = line.replace(f"- [ ] {milestone_num} ", f"- [~] {milestone_num} ", 1)
            BACKLOG_PATH.write_text("".join(lines), encoding="utf-8")
            logger.info("Dispatch: marked milestone {} as [~]", milestone_num)

            task_brief = f"## Milestone {milestone_num}: {description}\nCriterion: {criterion}\nFile: {file_path}\nBlocker: {blocker}"
            if note:
                task_brief += f"\nNote: {note}"

            return DispatchResult(
                milestone_num=milestone_num,
                label=milestone_num,
                task_brief=task_brief,
                spawn_result=None,
                dispatched=False,
            )
        i += 1

    return None


async def dispatch_next(manager: object) -> DispatchResult | None:
    """
    Full dispatch cycle:
    1. Run review_backlog.py to clean stale markers
    2. Find next ready milestone (under lock)
    3. Spawn subagent for it
    4. Rollback [~] if spawn fails

    Args:
        manager: SubagentManager instance with .spawn() method

    Returns:
        DispatchResult or None if nothing to dispatch
    """
    await run_review_backlog()

    result = find_ready_milestone()
    if result is None:
        logger.info("Dispatch: no ready milestones")
        return None

    # Append BACKLOG.md update instruction to task brief
    task_brief = result.task_brief + f"""

---
## IMPORTANT: Mark this milestone complete when done

When you have finished the task and verified the criterion passes, update the BACKLOG.md file:
- File: `/Users/mhall/.nanobot/workspace/memory/BACKLOG.md`
- Find the line: `- [~] {result.milestone_num} `
- Change it to: `- [x] {result.milestone_num} `

Use the edit_file tool to make this change. Do this as your final step before reporting done.
"""

    spawn_result = await manager.spawn(
        task=task_brief,
        label=result.milestone_num,
        origin_channel="discord",
        origin_chat_id="1475026411193499792",
        model="qwen3-coder-next",
    )

    result.spawn_result = spawn_result
    result.dispatched = not spawn_result.startswith("Error:")

    if not result.dispatched:
        # Rollback [~] → [ ]
        await manager._rollback_milestone_marker(result.milestone_num)
        logger.warning("Dispatch: spawn failed for {}, rolled back [~]", result.milestone_num)

    return result
