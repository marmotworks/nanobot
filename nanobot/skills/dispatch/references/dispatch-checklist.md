# Dispatch Checklist

Follow every step in order. Do not skip any step. Do not proceed to the next step until the current one is complete.

## Step 1: Identify the next ready milestone

Read `~/.nanobot/workspace/memory/BACKLOG.md`.

A milestone is **ready** if ALL of the following are true:
- Its marker is `[ ]` (not `[x]` and not `[~]`)
- Its `Blocker:` field is `none` OR the referenced milestone is already `[x]`
- Its parent task is not marked `Blocked` or `Complete`

Select the first ready milestone found. If none are ready, stop — report "No ready milestones."

## Step 2: Write the task brief

Write a complete task brief for the milestone. The brief must include:
- The milestone number and title
- The goal (what the subagent must accomplish)
- The single file to read first (from the `File:` field)
- Any additional context needed (read the parent task's Goal and any relevant notes)
- The exact verification command and expected output (from the `Criterion:` field)
- Code style requirements (ruff, double quotes, type annotations)
- Instruction to report the full output of the verification command

Do NOT abbreviate the brief. Subagents start with no memory — they need full context.

## Step 3: Mark `[~]` in BACKLOG.md — DO THIS BEFORE CALLING SPAWN

Edit `~/.nanobot/workspace/memory/BACKLOG.md` and change the milestone marker from `[ ]` to `[~]`.

**This step must happen before the spawn tool call.** If the agent crashes or the spawn call fails, the `[~]` marker prevents a duplicate dispatch on the next cron fire.

Verify the edit was saved by reading the file back and confirming `[~]` is present.

## Step 4: Call the spawn tool

Call the `spawn` tool with:
- `task`: the full task brief from Step 2
- `label`: `"N.M <short title>"` (e.g. `"6.3 Implement streaming"`)
- `model`: `"qwen3-coder-next"` (always — for technical tasks)

**The spawn tool call MUST appear in the same response as any announcement. Never announce a dispatch without immediately calling the tool.**

## Step 5: Verify the spawn succeeded

Check the return value from `spawn`. If it contains "Error" or "capacity limit":
- The spawn failed
- Go to Step 6

If the return value contains "started" or a task ID:
- The spawn succeeded
- Record the task ID in a note if helpful
- Done ✅

## Step 6: Handle spawn failure (only if Step 5 failed)

If spawn failed:
1. Edit BACKLOG.md — reset the milestone marker from `[~]` back to `[ ]`
2. Report the failure reason to the user
3. Do NOT retry immediately — let the next cron cycle handle it
