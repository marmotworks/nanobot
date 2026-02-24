---
description: Use this skill whenever dispatching a background subagent for a backlog milestone. Triggers: "dispatch next milestone", "run the cron", "advance the backlog", "spawn subagent for X". This skill enforces the mandatory dispatch checklist — do not bypass it.
---

# dispatch

## When to Use
- Advancing the backlog (cron fires or user requests it)
- Dispatching any milestone subagent
- Any time you would call the `spawn` tool for a backlog task

## Phase 1: Planning Subagents
**Use Phase 1 dispatches when the task has no milestones yet and needs research + milestone breakdown.**

### When to Use Phase 1:
- Task has no milestones in BACKLOG
- Requires research, exploration, or planning before execution
- Goal: produce a list of milestones with citations/sources

### How Phase 1 Differs from Phase 2:
- Creates milestones (Phase 2 executes existing milestones)
- No `[~]` BACKLOG marker needed yet (milestones don't exist)
- Output: milestone list that will be added to BACKLOG

### Capacity Check Still Applies:
- Consult SubagentRegistry for current capacity (same as Phase 2)
- Use `verify_dispatch.py` to check active subagents
- Both Phase 1 and Phase 2 count toward the same capacity limits

## Phase 2: Milestone Execution
**Use Phase 2 dispatches when milestones already exist in BACKLOG and need execution.**

## The Dispatch Checklist
**Always follow `references/dispatch-checklist.md` step by step. No steps are optional.**

## Verification
After dispatch, run:
```bash
python3 /Users/mhall/Workspaces/nanobot/nanobot/skills/dispatch/scripts/verify_dispatch.py
```
This cross-references BACKLOG.md `[~]` markers against the SubagentRegistry and flags stale or orphaned entries.

## Relationship to task-tracker
- Use `task-tracker` for status checks, triage, review, and close-out
- Use `dispatch` for the act of spawning a subagent
- The `task-tracker` Cron Dispatch section delegates to this skill
