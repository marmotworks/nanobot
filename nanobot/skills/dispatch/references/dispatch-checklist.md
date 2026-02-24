# Dispatch Checklist

Follow every step in order. Do not skip any step. Do not proceed to the next step until the current one is complete.

## Phase 1: Planning Dispatch
**Use this checklist when dispatching a planning subagent for a task with no milestones yet.**

### Step 1: Identify task needing planning

Read `~/.nanobot/workspace/memory/BACKLOG.md`.

A task needs Phase 1 planning if:
- The task exists in BACKLOG but has **no milestones** yet (no numbered items like `1.1`, `1.2`, etc.)
- The task requires research exploration before concrete milestones can be defined

### Step 2: Write task brief for planning subagent

Write a complete task brief for the planning subagent. The brief must include:
- The task number and title
- The goal: "Produce a list of milestones with citations/sources"
- Any existing context from the task description
- Expected output format: numbered milestones with brief descriptions and citations
- Code style requirements (ruff, double quotes, type annotations) if applicable

Do NOT abbreviate the brief. Subagents start with no memory — they need full context.

### Step 3: Check SubagentRegistry capacity

Read from SQLite database or call `verify_dispatch.py` to check:
- Current number of active subagents
- Capacity limit (typically 3 concurrent subagents)
- Ensure spawning a planning subagent won't exceed capacity

### Step 4: Mark task as "Planning in progress" in BACKLOG.md (optional)

Optionally add a note to the task in BACKLOG.md indicating "Planning in progress" to prevent duplicate dispatches. This is not a `[~]` marker (no milestones exist yet).

### Step 5: Spawn planning subagent

Call the `spawn` tool with:
- `task`: the full task brief from Step 2
- `label`: `"Planning: <task name>"` (e.g. `"Planning: Task 5 Research"`)
- `model`: `"qwen3-coder-next"` (always — for technical tasks)
- `template`: `"nanobot-coder"` (always — for ALL nanobot code tasks, no exceptions)
- `max_iterations`: `40` (planning tasks need room to read files and write milestones; 30 is not enough)

### Step 6: Verify spawn succeeded

Check the return value from `spawn`. If it contains "Error" or "capacity limit":
- The spawn failed
- Do NOT proceed with planning task

If the return value contains "started" or a task ID:
- The spawn succeeded
- Record the task ID in a note if helpful
- Done ✅

---

## Phase 2: Milestone Execution Dispatch
**Use this checklist when dispatching an execution subagent for an existing milestone.**

### Step 1: Identify the next ready milestone

Read `~/.nanobot/workspace/memory/BACKLOG.md`.

A milestone is **ready** if ALL of the following are true:
- Its marker is `[ ]` — milestones marked `[~]` (in-progress) or `[x]` (complete) must be **skipped**
- Its `Blocker:` field is `none` OR the referenced milestone is already `[x]`
- Its parent task is not marked `Blocked` or `Complete`

**Before selecting a milestone, scan for any `[~]` markers. If found, run `verify_dispatch.py` to check for stale markers before proceeding.**

Select the first ready milestone found. If none are ready, stop — report "No ready milestones."

### Step 2: Write the task brief

Write a complete task brief for the milestone. The brief must include:
- The milestone number and title
- The goal (what the subagent must accomplish)
- The single file to read first (from the `File:` field)
- Any additional context needed (read the parent task's Goal and any relevant notes)
- The exact verification command and expected output (from the `Criterion:` field)
- Code style requirements (ruff, double quotes, type annotations)
- Instruction to report the full output of the verification command

Do NOT abbreviate the brief. Subagents start with no memory — they need full context.

### Step 3: Mark `[~]` in BACKLOG.md — DO THIS BEFORE CALLING SPAWN

Edit `~/.nanobot/workspace/memory/BACKLOG.md` and change the milestone marker from `[ ]` to `[~]`.

**This step must happen before the spawn tool call.** If the agent crashes or the spawn call fails, the `[~]` marker prevents a duplicate dispatch on the next cron fire.

Verify the edit was saved by reading the file back and confirming `[~]` is present.

### Step 4: Call the spawn tool

Call the `spawn` tool with:
- `task`: the full task brief from Step 2
- `label`: `"N.M <short title>"` (e.g. `"6.3 Implement streaming"`)
- `model`: `"qwen3-coder-next"` (always — for technical tasks)
- `template`: `"nanobot-coder"` (always — for ALL nanobot code tasks, no exceptions)
- `max_iterations`: `40` (nanobot code tasks are complex; 30 is not enough — this is non-negotiable)

**The spawn tool call MUST appear in the same response as any announcement. Never announce a dispatch without immediately calling the tool.**

### Step 5: Verify the spawn succeeded

Check the return value from `spawn`. If it contains "Error" or "capacity limit":
- The spawn failed
- Go to Step 6

If the return value contains "started" or a task ID:
- The spawn succeeded
- Record the task ID in a note if helpful
- **Do NOT call the `message` tool to announce the dispatch** — the cron job's `deliver: true` setting handles delivery automatically. Calling `message` causes duplicate posts.
- Done ✅

### Step 6: Handle spawn failure (only if Step 5 failed)

If spawn failed:
1. Edit BACKLOG.md — reset the milestone marker from `[~]` back to `[ ]`
2. Report the failure reason to the user
3. Do NOT retry immediately — let the next cron cycle handle it
