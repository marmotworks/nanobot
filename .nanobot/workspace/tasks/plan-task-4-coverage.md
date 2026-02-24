# Planning Brief: Task 4 — Improve Nanobot Test Coverage

## Your Role
You are a planning subagent. Your job is to read the relevant files and produce a clear, actionable milestone breakdown. Do NOT implement anything.

## Task Goal
Improve test coverage for the nanobot project. Current coverage is ~27.5% with a `fail_under = 40` baseline not yet met. The goal is to write meaningful unit tests that cover real behavior — not superficial coverage padding.

## Files to Read
```bash
cat /Users/mhall/Workspaces/nanobot/pyproject.toml
python3 -m pytest tests/ -q -k "not integration" --cov=nanobot --cov-report=term-missing 2>&1 | tail -60
ls /Users/mhall/Workspaces/nanobot/tests/
ls /Users/mhall/Workspaces/nanobot/nanobot/
ls /Users/mhall/Workspaces/nanobot/nanobot/providers/
ls /Users/mhall/Workspaces/nanobot/nanobot/agent/
```

Also check the most under-covered files:
```bash
python3 -m pytest tests/ -q -k "not integration" --cov=nanobot --cov-report=term-missing 2>&1 | grep -E "^\s+[0-9]" | sort -k4 -n | head -30
```

## Questions to Answer
1. Which files have the lowest coverage and are most valuable to test?
2. What behaviors are currently untested that are most likely to break?
3. Which tests can be written as pure unit tests (no network, no subprocess)?
4. What's the realistic path to reach 40% coverage?

## Rules for Good Tests
- Test **behavior**, not implementation details
- Mock external dependencies (boto3, httpx, discord, etc.) — never hit real network in unit tests
- Use `AsyncMock` for async methods
- Name tests `test_<what>_<condition>_<expected>` 
- Each test file covers exactly one module
- Integration tests must be marked `@pytest.mark.integration`

## Output Format
Write a milestone list to `/Users/mhall/.nanobot/workspace/tasks/plan-task-4-output.md`:

```
## Task 4: Test Coverage — Milestone Breakdown

### 4.1 <short title>
Criterion: `<command>` → `<expected output>`
File: `<single test file to create>`
Covers: `<module being tested>`
Blocker: none
Note: <what behaviors to test>

### 4.2 ...
```

Aim for 5-8 milestones, each creating one test file covering one module. Prioritize the most impactful coverage gains first. Each milestone must be independently executable.
