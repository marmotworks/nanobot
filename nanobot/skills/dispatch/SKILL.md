---
description: Use this skill whenever dispatching a background subagent for a backlog milestone. Triggers: "dispatch next milestone", "run the cron", "advance the backlog", "spawn subagent for X". This skill enforces the mandatory dispatch checklist — do not bypass it.
---

# dispatch

## When to Use
- Advancing the backlog (cron fires or user requests it)
- Dispatching any milestone subagent
- Any time you would call the `spawn` tool for a backlog task

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
