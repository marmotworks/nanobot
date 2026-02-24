# Planning Brief: Task 1 — Playwright Skill Milestones 1.2 and 1.3

## Your Role
You are a planning subagent. Your job is to read the relevant files and produce a clear, actionable milestone breakdown. Do NOT implement anything.

## Task Goal
Task 1 is the Playwright skill at `nanobot/skills/playwright/`. Milestone 1.1 is complete — the skill is installed and verified. 

The remaining milestones are:
- **1.2**: Wire Playwright into the agent's decision logic — when should the agent use `playwright_fetch.py` instead of `web_fetch`? How should this be triggered?
- **1.3**: TBD — identify what else is needed to make the skill fully production-ready

## Files to Read
```bash
cat /Users/mhall/Workspaces/nanobot/nanobot/skills/playwright/SKILL.md
cat /Users/mhall/Workspaces/nanobot/nanobot/skills/playwright/playwright_fetch.py
cat /Users/mhall/Workspaces/nanobot/nanobot/agent/loop.py
cat /Users/mhall/Workspaces/nanobot/nanobot/agent/tools/registry.py
```

Also check how existing skills are wired into the agent:
```bash
grep -rn "playwright\|web_fetch" /Users/mhall/Workspaces/nanobot/nanobot/agent/ | head -30
ls /Users/mhall/Workspaces/nanobot/nanobot/agent/tools/
```

## Questions to Answer
1. Is `playwright_fetch.py` currently exposed as a tool the agent can call? If not, what would it take to add it?
2. Should the agent auto-decide when to use Playwright (e.g. based on URL patterns or failure fallback), or should it be an explicit tool call?
3. What's the simplest path to make the agent reliably use Playwright for JS-heavy pages?
4. What does 1.3 need to be? (e.g. tests, SKILL.md update, integration test)

## Research
- Check if there's a `web_fetch` tool in `nanobot/agent/tools/` and how it's structured
- Look at how other tools are registered and called

## Output Format
Write a milestone list to `/Users/mhall/.nanobot/workspace/tasks/plan-task-1-output.md`:

```
## Task 1: Playwright Skill — Remaining Milestones

### 1.2 <short title>
Criterion: `<command>` → `<expected output>`
File: `<single file>`
Blocker: none
Note: <approach + source URL if applicable>

### 1.3 <short title>
Criterion: `<command>` → `<expected output>`
File: `<single file>`
Blocker: 1.2
Note: <approach + source URL if applicable>
```

If more than 2 milestones are needed, add them. Each milestone must touch exactly one file and have one verifiable criterion.
