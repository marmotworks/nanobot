# Backlog Review Checklist

A review subagent reads BACKLOG.md and applies these rules in order:

## Rules

1. **Clear completed blockers**: If milestone X.N has `Blocker: X.M` and X.M is marked `[x]`, clear the blocker (set to `none`).

2. **Reset orphaned in-progress markers**: If a milestone is marked `[~]` but no subagent with that label is active in the subagent registry, reset it to `[ ]`.

3. **Close complete tasks**: If ALL milestones in a task are `[x]`, mark the task status as `Complete`.

4. **Flag blocked tasks**: If a task has milestones where the blocker references a task that doesn't exist or is already complete, flag it for human review.

5. **Do not auto-approve**: Never mark a milestone `[ ]` → `[x]` without a subagent having done the work. Only reset `[~]` → `[ ]` for orphaned markers.

## Output

After applying rules, write the updated BACKLOG.md and report:
- How many blockers were cleared
- How many orphaned [~] markers were reset
- How many tasks were closed
- Any flags for human review
