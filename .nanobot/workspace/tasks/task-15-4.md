# Task 15.4 — Unit tests for `_extract_narrative`

## Goal
Write unit tests for the `_extract_narrative` function in `nanobot/agent/subagent.py`.

## Step 1: Read the function
```bash
grep -n "_extract_narrative" /Users/mhall/Workspaces/nanobot/nanobot/agent/subagent.py
```
Then read the full function implementation to understand its exact behavior.

## Step 2: Write tests

Create `tests/test_subagent_narrative.py` with these test cases:

1. **Normal result** — single paragraph → returned as-is (up to 300 chars)
2. **Empty string** → returns `⚠️` prefixed message
3. **None input** → returns `⚠️` prefixed message
4. **`[INCOMPLETE]` prefix** → returns `⚠️` prefixed message
5. **Long result** (>300 chars) → truncated with `...`
6. **Multi-paragraph result** → only first non-empty paragraph returned
7. **Whitespace-only result** → returns `⚠️` prefixed message

## Step 3: Verify
```bash
cd /Users/mhall/Workspaces/nanobot
python3 -m pytest tests/test_subagent_narrative.py -v 2>&1 | tail -20
```
Expected: all tests pass.

```bash
cd /Users/mhall/Workspaces/nanobot
python3 -m ruff check tests/test_subagent_narrative.py
```
Expected: `All checks passed.`

## Step 4: Full suite
```bash
cd /Users/mhall/Workspaces/nanobot
python3 -m pytest tests/ -q -k "not integration" --timeout=30 2>&1 | tail -5
```
Expected: 830+ passed, 0 failed.

## Code style
- Double quotes everywhere
- No unused imports
- Do NOT use ruff --fix
- Use `pytest` style (plain functions, no classes needed)

## Report
- Full output of all verification commands
- PASS or FAIL
