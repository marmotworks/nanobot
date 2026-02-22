# Task Tracker

This skill manages the nanobot background task backlog. Use it for: (1) checking task status ("what's in the backlog?", "what's next?", "what's in-flight?"), (2) triaging new bugs or tasks, (3) reviewing and auditing backlog health, (4) advancing the cron dispatch loop, (5) anything involving BACKLOG.md.

## Backlog Location

`~/.nanobot/workspace/memory/BACKLOG.md`

## Workflows

### Status Check

Run `python3 /Users/mhall/Workspaces/nanobot/nanobot/skills/task-tracker/scripts/status.py` to get a clean status table. Read `references/schema.md` for field definitions if needed.

### Triage (new bug or task)

Read `references/triage-checklist.md` and follow it step by step. Do not skip steps.

### Review (audit backlog health)

Read `references/review-checklist.md` and follow it step by step. Do not skip steps.

### Cron Dispatch

Follow two-phase dispatch:
1. **Phase 1 (planning)**: If a task has status "Not started" and no milestones → spawn planning subagent (qwen3-coder-next). Planning subagent must web search first, cite sources inline in BACKLOG.md.
2. **Phase 2 (execution)**: If a task has milestones and the next unchecked milestone has no blocker and is not in-progress → spawn execution subagent (qwen3-coder-next) for that one milestone.
3. Skip tasks marked `Blocked` or `Complete`.
4. Skip milestones marked `[~]` (in-progress).
5. Dispatch at most **1 background subagent at a time** (conservative default until registry is verified).
6. After dispatching, mark the milestone `[~]` in BACKLOG.md.
