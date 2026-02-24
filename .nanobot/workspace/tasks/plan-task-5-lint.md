# Planning Brief: Task 5 — Ruff Lint Cleanup (Remaining ~76 Violations)

## Your Role
You are a planning subagent. Your job is to read the relevant files and produce a clear, actionable milestone breakdown. Do NOT implement anything.

## Task Goal
Complete the ruff lint cleanup for the nanobot project. ~76 violations remain across multiple files. Each milestone must fix exactly ONE file.

## Step 1: Get current violation list
```bash
cd /Users/mhall/Workspaces/nanobot
python3 -m ruff check nanobot/ tests/ --statistics 2>&1
python3 -m ruff check nanobot/ tests/ 2>&1 | head -100
```

## Step 2: Group violations by file
```bash
python3 -m ruff check nanobot/ tests/ --output-format=concise 2>&1 | awk -F: '{print $1}' | sort | uniq -c | sort -rn
```

## Rules
- Each milestone = exactly one file
- Criterion = `python3 -m ruff check <file>` → `All checks passed.`
- Do NOT use `ruff --fix` — violations must be fixed manually
- Skip files that are already clean
- Priority: files with the most violations first

## Output Format
Write a milestone list to `/Users/mhall/.nanobot/workspace/tasks/plan-task-5-output.md`:

```
## Task 5: Ruff Lint Cleanup — Remaining Files

### 5.X <filename> (<N> violations)
Criterion: `python3 -m ruff check <file>` → `All checks passed.`
File: `<file path>`
Blocker: none
Note: <violation types, e.g. "TC001, I001, RUF012">
```

List every file with violations. One milestone per file.
