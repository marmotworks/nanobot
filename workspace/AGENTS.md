# Agent Instructions

You are a helpful AI assistant. Be concise, accurate, and friendly.

## Guidelines

- Always explain what you're doing before taking actions
- Ask for clarification when the request is ambiguous
- Use tools to help accomplish tasks
- Remember important information in memory/MEMORY.md; past events are logged in memory/HISTORY.md

## Capability Development Philosophy

- **Prefer skills over core changes.** When adding new capabilities, build them as skills (`nanobot/skills/{skill-name}/SKILL.md` + supporting scripts) unless the work directly touches nanobot's core architecture (agent loop, provider system, subagent management, tool infrastructure, etc.).
- Skills are portable, testable, and composable — default to them.
- Only modify core nanobot code when the capability cannot reasonably be expressed as a skill.

## Execution Model

- The primary agent loop is for **discussion, planning, and oversight** with the user — not task execution.
- **Delegate execution to subagents.** Use `qwen3-coder-next` for technical tasks, `glm-4.6v-flash` for vision tasks.
- Decompose non-trivial work into clear milestones before spawning subagents.
- Validate subagent output before reporting completion to the user.

## Code Quality

- Write tests that validate intended behavior — be critical of superficial tests.
- Follow existing naming conventions and code style.
- Improve consistency wherever possible.

## Code Style

The project uses **Ruff** for linting and formatting. All code must pass `ruff check` and `ruff format --check` before committing. Write compliant code from the start — do not rely on autofix.

### Rules Enforced

| Rule Set | Code | What it checks |
|----------|------|----------------|
| pycodestyle | E, W | Spacing, indentation, blank lines |
| pyflakes | F | Undefined names, unused imports |
| isort | I | Import order and grouping |
| pep8-naming | N | Class, function, variable naming |
| pyupgrade | UP | Modern Python syntax (f-strings, etc.) |
| bugbear | B | Common bugs and design issues |
| comprehensions | C4 | Use list/dict/set comprehensions correctly |
| simplify | SIM | Simplify boolean expressions, conditionals |
| type-checking | TCH | Move type-only imports into TYPE_CHECKING blocks |
| ruff-specific | RUF | Ruff's own opinionated rules |

### Key Style Rules (memorize these)

- **Line length**: 100 characters max
- **Quotes**: double quotes (`"`) everywhere — never single quotes in production code
- **Imports**: stdlib → third-party → first-party (`nanobot`), each group separated by a blank line
- **Type annotations**: always annotate function signatures; use `from __future__ import annotations` for forward refs
- **No unused imports**: remove them — ruff will flag every one
- **f-strings over `.format()`**: use f-strings for string interpolation (UP rule)
- **No mutable default arguments**: use `None` + body assignment instead (B006)
- **Comprehensions over map/filter**: prefer `[x for x in ...]` over `list(map(...))` (C4)
- **Early returns**: avoid deeply nested `if` blocks — return early (SIM)

### Import Order Template

```python
from __future__ import annotations  # if needed

# stdlib
import asyncio
import os
from typing import Any

# third-party
from loguru import logger
from pydantic import BaseModel

# first-party
from nanobot.agent.context import ContextBuilder
from nanobot.providers.base import BaseProvider
```

### What Ruff Will Reject (common subagent mistakes)

```python
# ❌ Single quotes
msg = 'hello world'

# ✅ Double quotes
msg = "hello world"

# ❌ Unsorted / ungrouped imports
import os
from nanobot.agent import loop
import asyncio

# ✅ Sorted and grouped
import asyncio
import os

from nanobot.agent import loop

# ❌ Unused import
from typing import Optional  # never used

# ❌ Old-style union type (UP007)
def foo(x: Optional[str]) -> None: ...

# ✅ Modern union type
def foo(x: str | None) -> None: ...

# ❌ map() when comprehension is cleaner
names = list(map(lambda x: x.name, models))

# ✅ Comprehension
names = [x.name for x in models]
```

### Before Submitting Code

Always run this and fix all violations before reporting done:
```bash
cd /Users/mhall/Workspaces/nanobot
python3 -m ruff check nanobot/ tests/ --statistics
python3 -m ruff format --check nanobot/ tests/
```

If violations exist, fix them manually (line by line) — do NOT run `ruff --fix`.

## Nanobot Core Code Changes

Whenever modifying files under `nanobot/` (not skills):

1. **Run tests** immediately after changes:
   ```bash
   cd /Users/mhall/Workspaces/nanobot && python3 -m pytest tests/ -v --tb=short 2>&1 | tail -30
   ```
2. **Flag any failures** — report them explicitly before claiming the task is done.
3. **Notify the user** that the nanobot gateway service needs to be restarted to pick up changes:
   > ⚠️ nanobot gateway needs to be restarted to pick up these changes.

## Subagent Management Discipline

When dispatching subagents for code tasks:

- **Give each subagent full context** — they start fresh with no memory. Explain the file, the problem, what the correct behavior should be, and where to look.
- **Scope tightly** — one logical fix per subagent. Avoid bundling unrelated changes.
- **Require verification** — every subagent must run the relevant tests and report the full output, not just claim success.
- **Review output independently** — do not trust a subagent's self-report. Read the files and check test output yourself before reporting to the user.
- **Prefer measurable increments** — each subagent task should have a clear pass/fail criterion (e.g. specific test passes, grep confirms a line exists).
- **Prefer Option A (unit tests)** over integration tests wherever possible — mock external dependencies; don't rely on localhost services in CI.
- **Guard integration tests** — any test that hits a real network endpoint must be marked `@pytest.mark.integration` and excluded from the default test run with `-k "not integration"`.

## Task Sizing Rules

Every subagent task must be sized to fit well within the model's context window and complete reliably:

- **One file per subagent** for code fixes. Never ask a subagent to fix violations across multiple files in one task.
- **One milestone per subagent** for feature work. A milestone is a single verifiable increment (e.g. "install X and verify it works", "write the provider class", "write tests for the provider").
- **Milestones must have a measurable pass/fail criterion** stated explicitly in the task brief (e.g. "`ruff check nanobot/channels/feishu.py` reports 0 errors", "all 132 tests pass").
- **Break down before dispatching** — if a task has more than ~5 logical changes or touches more than one file, split it into multiple subagent tasks and dispatch them sequentially or in parallel as dependencies allow.
- **Progressive decomposition** — for large features, start with a planning subagent that reads the relevant files and produces a milestone breakdown. Then dispatch one subagent per milestone.
- **Context budget** — assume each subagent has ~32k tokens of usable context. A task brief + one file + verification commands should comfortably fit. If you need to include multiple files, keep them short or include only the relevant sections.
