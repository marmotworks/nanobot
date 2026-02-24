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

### Close Out (task completion)

When all milestones for a task are `[x]` and the work is committed:

1. **Announce on Discord** — send a brief completion message to channel `discord`, chat ID `1475026411193499792`. Include task title and what was delivered.
2. **Update task status** — set `**Status**: Complete ✅` in BACKLOG.md.
3. **Move to Completed section** — cut the entire task block (header + goal + milestones) from the active section and paste a summary entry under `## Completed` at the bottom of BACKLOG.md. Format:
   ```
   ### Task N: Title ✅
   - One-line summary of what was delivered
   - Commit hash if applicable
   ```
4. **Verify** — run `status.py` and confirm the task no longer appears in the active list.

Do NOT leave completed tasks in the active section. Do NOT skip the Discord announcement.

### Cron Dispatch

**Step 0 — Run readiness check first (mandatory):**
```bash
python3 /Users/mhall/Workspaces/nanobot/nanobot/skills/task-tracker/scripts/check_readiness.py
```
This clears any stale blockers before dispatch. Always run this before selecting the next milestone.

Then follow two-phase dispatch via the `dispatch` skill — read `/Users/mhall/Workspaces/nanobot/nanobot/skills/dispatch/SKILL.md` and follow its checklist. Do not improvise the dispatch process.

1. **Phase 1 (planning)**: If a task has status "Not started" and no milestones → spawn planning subagent (qwen3-coder-next). Planning subagent must web search first, cite sources inline in BACKLOG.md.
2. **Phase 2 (execution)**: If a task has milestones and the next unchecked milestone has `Blocker: none` and is not `[~]` → use the `dispatch` skill to spawn an execution subagent (qwen3-coder-next) for that one milestone.
3. Skip tasks marked `Blocked` or `Complete`.
4. Skip milestones marked `[~]` (in-progress).
5. Dispatch at most **1 background subagent at a time**.
6. After dispatching, mark the milestone `[~]` in BACKLOG.md (the dispatch checklist enforces this).
