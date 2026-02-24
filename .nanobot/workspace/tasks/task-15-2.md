# Task 15.2 — Extract narrative from `final_result` in `_announce_result`

## Goal

In `nanobot/agent/subagent.py`, replace the generic status text in `_announce_result` with a
brief narrative extracted from the subagent's actual result. Add a `_extract_narrative` helper
function that does the extraction.

## File to edit

`/Users/mhall/Workspaces/nanobot/nanobot/agent/subagent.py`

## What to change

### 1. Add `_extract_narrative` helper (module-level function, before `SubagentManager` class)

```python
def _extract_narrative(result: str | None) -> str:
    """Extract a brief narrative from a subagent result for user-facing announcements.

    Returns the first non-empty paragraph, truncated to 300 characters.
    Returns a warning string if the result is empty or incomplete.
    """
    if not result or result.strip() == "":
        return "⚠️ No result produced."
    if result.startswith("[INCOMPLETE]"):
        return "⚠️ Task completed with no output (incomplete)."

    # Split into paragraphs, find the first non-empty one
    paragraphs = [p.strip() for p in result.split("\n\n") if p.strip()]
    if not paragraphs:
        return "⚠️ No result produced."

    narrative = paragraphs[0]
    if len(narrative) > 300:
        narrative = narrative[:297] + "..."
    return narrative
```

### 2. Update `_announce_result` to use `_extract_narrative`

Current `_announce_result` builds `announce_content` like this:

```python
announce_content = f"""[Subagent '{label}' {status_text}]

Task: {task}

Result:
{result}

Summarize this naturally for the user. Keep it brief (1-2 sentences). Do not mention technical details like "subagent" or task IDs."""
```

Change it to:

```python
narrative = _extract_narrative(result)

announce_content = f"""[Subagent '{label}' {status_text}]

Task: {task}

Result:
{result}

Summarize this naturally for the user. Keep it brief (1-2 sentences). Do not mention technical details like "subagent" or task IDs.

Suggested summary: {narrative}"""
```

The `Suggested summary` line gives the main agent a ready-made narrative to use or adapt,
without forcing it — the main agent still sees the full result and can override.

### 3. Pass narrative to `tag_out` as `result_summary`

In `_run_subagent`, the `tag_out` call is at the very end in the `finally` block:

```python
finally:
    self.registry.tag_out(task_id, final_status)
```

Check the signature of `tag_out` in `nanobot/agent/registry.py`:
```bash
grep -n "def tag_out" /Users/mhall/Workspaces/nanobot/nanobot/agent/registry.py
```

If `tag_out` accepts a `result_summary` parameter, pass it:
```python
finally:
    narrative = _extract_narrative(final_result if final_status == "completed" else None)
    self.registry.tag_out(task_id, final_status, result_summary=narrative)
```

If it does NOT accept `result_summary`, do NOT add it — just leave `tag_out` as-is and note
this in your report. Do not modify `registry.py` in this milestone.

## Verification

### Step 1: Inline test
```bash
cd /Users/mhall/Workspaces/nanobot
python3 -c "
from nanobot.agent.subagent import _extract_narrative

# Normal result
r = _extract_narrative('Fix applied successfully. The bug was in line 42.')
assert r == 'Fix applied successfully. The bug was in line 42.', f'Got: {r!r}'

# Empty result
r = _extract_narrative('')
assert r == '⚠️ No result produced.', f'Got: {r!r}'

# None result
r = _extract_narrative(None)
assert r == '⚠️ No result produced.', f'Got: {r!r}'

# Incomplete result
r = _extract_narrative('[INCOMPLETE] ran out of iterations')
assert r == '⚠️ Task completed with no output (incomplete).', f'Got: {r!r}'

# Long result (truncation)
long = 'x' * 400
r = _extract_narrative(long)
assert len(r) == 300, f'Expected 300 chars, got {len(r)}'
assert r.endswith('...'), f'Expected ellipsis, got: {r[-5:]!r}'

# Multi-paragraph result
r = _extract_narrative('First paragraph.\n\nSecond paragraph.')
assert r == 'First paragraph.', f'Got: {r!r}'

print('All assertions passed.')
"
```
Expected: `All assertions passed.`

### Step 2: Ruff check
```bash
cd /Users/mhall/Workspaces/nanobot
python3 -m ruff check nanobot/agent/subagent.py
```
Expected: `All checks passed.`

### Step 3: Full test suite
```bash
cd /Users/mhall/Workspaces/nanobot
python3 -m pytest tests/ -q -k "not integration" --timeout=30 2>&1 | tail -5
```
Expected: 829+ passed, 0 failed.

## Code style rules

- Double quotes everywhere
- No unused imports
- Do NOT use `ruff --fix`
- Type annotations on all function signatures

## Report

- Show the exact diff you made (before/after for each change)
- Full output of the inline test
- Full output of ruff check
- Full output of pytest (last 5 lines)
- Whether `tag_out` accepted `result_summary` (yes/no)
- PASS or FAIL
