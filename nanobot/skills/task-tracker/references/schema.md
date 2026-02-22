# BACKLOG.md Schema

## Task Header

```
## Task N: Title

**Goal**: One sentence description.
**Status**: Not started | Planning | In progress | Blocked | Complete ✅
**Blocker**: Task X (or omit if none)
```

## Milestone Format

```
- [ ] N.M Short description
      Criterion: `<command>` → `<expected output>`
      File: `<single file path>` (or "N/A")
      Blocker: N.X (or "none")
```

## Milestone Status Markers

- `[ ]` — not started
- `[~]` — in-progress (subagent dispatched)
- `[x]` — complete

## Rules

- One file per milestone
- One verifiable criterion per milestone
- Milestones must be sequentially numbered N.1, N.2, ...
- Blocker must reference a specific milestone (N.X) or "none"
- Task status must be kept in sync with milestone state
