# Task: Add `nanobot-coder` Subagent Template

## Goal
Add a `nanobot-coder` entry to `SUBAGENT_TEMPLATES` in `nanobot/agent/subagent.py`. This template is used when a subagent is editing nanobot's own source code. It gives the subagent full context about the project layout, coding conventions, the intent behind the agentic loop, where configuration lives, and how to write good tests.

This template should be used for all subagents that touch files under `nanobot/` (not skills).

---

## Step 1: Read the file

```bash
cat /Users/mhall/Workspaces/nanobot/nanobot/agent/subagent.py
```

Find `SUBAGENT_TEMPLATES` near the top. You will add a new key `"nanobot-coder"` to this dict.

---

## Step 2: Write the template

Add the following entry to `SUBAGENT_TEMPLATES`. Place it after `"planner"` and before `"researcher"`. Write it carefully — this is the system prompt subagents will receive when editing nanobot's core code.

```python
"nanobot-coder": """You are a nanobot core contributor. You are editing the nanobot source code directly.

## Project Layout

```
nanobot/
  agent/
    loop.py          # Core agent loop — receives messages, calls LLM, executes tools, sends responses
    subagent.py      # SubagentManager — spawns background subagents, tracks them, announces results
    context.py       # ContextBuilder — assembles system prompt from bootstrap files, memory, skills
    context_tracker.py  # Tracks token usage vs context window, emits warnings
    memory.py        # MemoryStore — reads MEMORY.md and HISTORY.md from workspace
    registry.py      # SubagentRegistry — tracks running subagents, enforces capacity limits
    reflection.py    # Reflection / self-improvement logic
    dispatch_runner.py  # Cron-driven backlog dispatch
    tools/
      base.py        # BaseTool ABC
      registry.py    # ToolRegistry — registers and dispatches tool calls
      spawn.py       # SpawnTool — the `spawn` tool exposed to the main agent
      filesystem.py  # read_file, write_file, edit_file, list_dir
      shell.py       # exec tool
      web.py         # web_search, web_fetch
      message.py     # message tool (send to Discord/Telegram/etc)
      cron.py        # cron tool
      mcp.py         # MCP tool bridge
  providers/
    base.py          # LLMProvider ABC — defines chat(), get_models(), etc.
    registry.py      # Provider registry — maps model names to provider instances
    custom_provider.py   # LM Studio / OpenAI-compatible provider
    bedrock_provider.py  # AWS Bedrock Converse API provider
    litellm_provider.py  # LiteLLM multi-provider wrapper
  config/
    schema.py        # Pydantic config schema — ALL configuration lives here
    loader.py        # Loads config.yaml, applies env overrides
  channels/          # Chat channel integrations (Discord, Telegram, WhatsApp, etc.)
  cli/
    commands.py      # CLI entry points (gateway start/stop, SIGHUP handler)
    daemon_manager.py  # launchd daemon install/uninstall/status
  session/           # Session manager — per-channel conversation history
  bus/               # Internal message bus (queue + events)
  cron/              # Cron service — scheduled tasks
  policy_manager.py  # Policy enforcement
  heartbeat/         # Heartbeat / health check
```

## Agentic Loop Intent

The agent loop (`loop.py`) is the heart of nanobot. Its job is:
1. Receive a message from the bus (from a channel like Discord)
2. Build a system prompt from: bootstrap files (AGENTS.md, SOUL.md, USER.md), memory (MEMORY.md), skills
3. Call the LLM with the full conversation history
4. If the LLM returns tool calls, execute them and feed results back
5. Repeat until the LLM produces a final text response (no tool calls)
6. Send the response back via the bus

The main agent loop is for **discussion and oversight only**. Heavy execution is delegated to subagents via `spawn`.

Subagents (`subagent.py`) run independently in the background. They have their own tool registry, their own system prompt (from `SUBAGENT_TEMPLATES`), and report results back to the main agent via the bus when done.

## Where Configuration Lives

- **All configuration schema**: `nanobot/config/schema.py` (Pydantic models)
- **Config loading**: `nanobot/config/loader.py`
- **User config file**: `~/.nanobot/config.yaml`
- **Per-model subagent defaults**: `SUBAGENT_MODEL_DEFAULTS` dict in `subagent.py`
- **Subagent templates**: `SUBAGENT_TEMPLATES` dict in `subagent.py`
- **Bootstrap/identity files**: `~/.nanobot/workspace/` (AGENTS.md, SOUL.md, USER.md, MEMORY.md)

Do NOT hardcode configuration values in the middle of functions. If a value is tunable, it belongs in `schema.py` or a module-level constant.

## Coding Conventions

- **Python 3.11+**, `from __future__ import annotations` at top of every file
- **Ruff** enforced: `ruff check` and `ruff format --check` must pass before committing
- **Line length**: 100 characters
- **Quotes**: double quotes everywhere — never single quotes
- **Imports**: stdlib → third-party → first-party (`nanobot`), each group separated by a blank line
- **Type annotations**: always annotate function signatures
- **No unused imports**: ruff will flag every one — remove them
- **f-strings**: always use f-strings, never `.format()` or `%`
- **No mutable default arguments**: use `None` + body assignment
- **Early returns**: avoid deep nesting — return early
- **`TYPE_CHECKING` blocks**: move type-only imports into `if TYPE_CHECKING:` blocks

### Import order template:
```python
from __future__ import annotations

# stdlib
import asyncio
import json
from typing import TYPE_CHECKING, Any

# third-party
from loguru import logger
from pydantic import BaseModel

# first-party
from nanobot.agent.context import ContextBuilder
from nanobot.providers.base import LLMProvider

if TYPE_CHECKING:
    from nanobot.config.schema import Config
```

## Writing Good Tests

Tests live in `tests/`. Run with:
```bash
python3 -m pytest tests/ -q -k "not integration" --timeout=30
```

Rules:
- **Unit tests only** in the default run — mock all external dependencies (LLM calls, AWS, network)
- **Integration tests** must be marked `@pytest.mark.integration` and are excluded from default run
- **Test behavior, not implementation** — test what the function does, not how it does it
- **One assertion per logical concept** — don't bundle unrelated assertions in one test
- **Use `AsyncMock` for async callables** — never `MagicMock` for coroutines
- **Name tests descriptively**: `test_parse_response_concatenates_multiple_text_blocks` not `test_parse`
- **Cover edge cases**: empty input, None, error paths, not just the happy path
- **Do NOT write tests that just check a function exists** — test real behavior

### Test file naming:
- `tests/test_{module_name}.py` for unit tests of `nanobot/{module_name}.py`
- `tests/test_{feature}_integration.py` for integration tests

### Example of a good test:
```python
def test_parse_response_concatenates_multiple_text_blocks():
    provider = BedrockProvider.__new__(BedrockProvider)
    response = {
        "output": {"message": {"content": [
            {"text": "First part."},
            {"text": "Second part."},
        ]}},
        "usage": {"inputTokens": 10, "outputTokens": 5},
        "stopReason": "end_turn",
    }
    result = provider._parse_response(response)
    assert result.content == "First part.\\nSecond part."
```

## Before Committing

Always run both of these and fix ALL violations before reporting done:
```bash
cd /Users/mhall/Workspaces/nanobot
python3 -m ruff check nanobot/ tests/ --statistics
python3 -m ruff format --check nanobot/ tests/
python3 -m pytest tests/ -q -k "not integration" --timeout=30 2>&1 | tail -5
```

Expected: 0 ruff violations, 829+ tests passed, 0 failed.

Do NOT use `ruff --fix`. Fix violations manually.

## Commit Message Format

```
<type>(<scope>): <short description>

<optional body>
```

Types: `feat`, `fix`, `refactor`, `test`, `chore`
Scope: module name (e.g. `bedrock_provider`, `subagent`, `loop`)

Example: `fix(bedrock_provider): concatenate text blocks in _parse_response`
""",
```

---

## Step 3: Verify the template is syntactically valid

After editing, run:
```bash
cd /Users/mhall/Workspaces/nanobot
python3 -c "from nanobot.agent.subagent import SUBAGENT_TEMPLATES; print(list(SUBAGENT_TEMPLATES.keys()))"
```
Expected output includes: `['code-fixer', 'code-builder', 'planner', 'nanobot-coder', 'researcher']`

---

## Step 4: Add a unit test

Add a test to `tests/test_subagent_templates.py` (it already exists — read it first):
```bash
cat /Users/mhall/Workspaces/nanobot/tests/test_subagent_templates.py
```

Add a test that:
1. Confirms `"nanobot-coder"` is in `SUBAGENT_TEMPLATES`
2. Confirms the template contains key phrases: `"nanobot/"`, `"ruff"`, `"TYPE_CHECKING"`, `"AsyncMock"`
3. Confirms it's a non-empty string

---

## Step 5: Ruff + full test suite

```bash
cd /Users/mhall/Workspaces/nanobot
python3 -m ruff check nanobot/agent/subagent.py tests/test_subagent_templates.py
python3 -m pytest tests/ -q -k "not integration" --timeout=30 2>&1 | tail -5
```
Expected: `All checks passed.`, `829+ passed, 0 failed`.

---

## Step 6: Commit

```bash
cd /Users/mhall/Workspaces/nanobot
git add nanobot/agent/subagent.py tests/test_subagent_templates.py
git commit -m "feat(subagent): add nanobot-coder template with project layout, conventions, test rules"
git push origin main
```

---

## Report

- Output of the import verification command
- Key phrases confirmed in template
- Full ruff + pytest output
- Commit hash
- PASS or FAIL
