# Backlog Review Checklist

A step-by-step checklist for auditing backlog health.

## Checklist

1. **Stale in-progress markers** — Find any `[~]` milestones. Check if a subagent is actually running for them. If not, reset to `[ ]`.

2. **Orphaned milestones** — Find milestones whose blocker references a milestone that is already `[x]`. These are ready to run — remove the blocker or mark it "none".

3. **Tasks with no milestones** — Any task with status "Not started" and no milestone list needs a planning subagent.

4. **Status drift** — If all milestones for a task are `[x]`, the task status should be "Complete ✅". Fix any that aren't.

5. **Blocked tasks** — Verify the blocker still applies. If the blocking task is complete, unblock.

6. **Milestone criterion quality** — Spot-check 2-3 milestones. Each must have: a runnable command, an expected output, and a single file. Flag any that are vague.

## Summary

After completing all checks, write a one-paragraph health summary.
