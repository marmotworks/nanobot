# Task 15+38: Per-Spawn Subagent Parameters + Narrative Summary

## Goal

Extend the subagent spawning system so that `temperature`, `max_tokens`, `max_iterations`, and `model` can be specified per-spawn call, with sensible per-model defaults as fallbacks. Store these defaults in a config structure and use them throughout the subagent execution path.

This combines:
- **Task 15**: Richer subagent completion narratives (15.2 already done — `_extract_narrative` wired in)
- **Task 38**: Per-spawn overridable parameters

---

## Files Involved

### `nanobot/agent/tools/spawn.py`
The `SpawnTool` — the LLM-facing tool that the agent calls. Currently accepts: `task`, `label`, `model`, `image_path`, `template`. **Needs**: `temperature`, `max_tokens`, `max_iterations` added to `parameters` schema and `execute()` signature.

### `nanobot/agent/subagent.py`
The `SubagentManager` — manages execution. Currently:
- `__init__` stores `self.temperature = 0.7`, `self.max_tokens = 4096` as manager-level defaults
- `spawn()` accepts: `task`, `label`, `origin_channel`, `origin_chat_id`, `model`, `image_path`, `template` — **no per-spawn overrides**
- `_run_subagent()` uses `self.temperature`, `self.max_tokens`, hardcoded `max_iterations = 30`

**Needs**: `temperature`, `max_tokens`, `max_iterations` threaded through `spawn()` → `_run_subagent()` with manager defaults as fallback.

---

## Recommended Parameter Defaults (by model)

Based on known model capabilities:

### `qwen3-coder-next` (LM Studio, technical tasks)
- `temperature`: `0.2` — lower for precise code generation
- `max_tokens`: `8192` — large output for complex code
- `max_iterations`: `40` — technical tasks may need more tool calls

### `glm-4.6v-flash` (LM Studio, vision tasks)
- `temperature`: `0.5`
- `max_tokens`: `2048` — vision responses are typically shorter
- `max_iterations`: `10` — vision tasks are single-shot

### `minimax.minimax-m2.1` (Bedrock, main agent / planning)
- `temperature`: `0.7`
- `max_tokens`: `8192` — MiniMax supports up to 8192 output tokens
- `max_iterations`: `30`

### Default fallback (any other model)
- `temperature`: `0.7`
- `max_tokens`: `4096`
- `max_iterations`: `30`

---

## Implementation Plan

### Milestone A: Add per-model default config to `subagent.py`

**File**: `nanobot/agent/subagent.py`

Add a module-level dict `SUBAGENT_MODEL_DEFAULTS` mapping model name patterns to default params:

```python
SUBAGENT_MODEL_DEFAULTS: dict[str, dict[str, Any]] = {
    "qwen3-coder-next": {"temperature": 0.2, "max_tokens": 8192, "max_iterations": 40},
    "glm-4.6v-flash":   {"temperature": 0.5, "max_tokens": 2048, "max_iterations": 10},
    "minimax.minimax-m2.1": {"temperature": 0.7, "max_tokens": 8192, "max_iterations": 30},
}

SUBAGENT_DEFAULT_PARAMS: dict[str, Any] = {
    "temperature": 0.7,
    "max_tokens": 4096,
    "max_iterations": 30,
}
```

Add a helper `_get_model_defaults(model: str) -> dict[str, Any]` that looks up the model in `SUBAGENT_MODEL_DEFAULTS` (exact match first, then prefix match), falling back to `SUBAGENT_DEFAULT_PARAMS`.

**Criterion**: `python3 -c "from nanobot.agent.subagent import SUBAGENT_MODEL_DEFAULTS, _get_model_defaults; print(_get_model_defaults('qwen3-coder-next'))"` → `{'temperature': 0.2, 'max_tokens': 8192, 'max_iterations': 40}`

---

### Milestone B: Thread params through `spawn()` and `_run_subagent()`

**File**: `nanobot/agent/subagent.py`

1. Add `temperature: float | None = None`, `max_tokens: int | None = None`, `max_iterations: int | None = None` to `spawn()` signature
2. Pass them through to `_run_subagent()`
3. In `_run_subagent()`, resolve final values:
   ```python
   model_defaults = _get_model_defaults(subagent_model)
   effective_temperature = temperature if temperature is not None else model_defaults["temperature"]
   effective_max_tokens = max_tokens if max_tokens is not None else model_defaults["max_tokens"]
   effective_max_iterations = max_iterations if max_iterations is not None else model_defaults["max_iterations"]
   ```
4. Replace hardcoded `max_iterations = 30`, `self.temperature`, `self.max_tokens` with the effective values in the loop

**Criterion**: `python3 -m pytest tests/ -q -k "not integration" --timeout=30 2>&1 | tail -3` → `829 passed`

---

### Milestone C: Add params to `SpawnTool.parameters` schema and `execute()`

**File**: `nanobot/agent/tools/spawn.py`

1. Add to `parameters` dict:
   ```python
   "temperature": {
       "type": "number",
       "description": "Sampling temperature (0.0–1.0). Lower = more deterministic. Defaults to model-specific value (e.g. 0.2 for qwen3-coder-next).",
   },
   "max_tokens": {
       "type": "integer",
       "description": "Maximum output tokens. Defaults to model-specific value (e.g. 8192 for qwen3-coder-next).",
   },
   "max_iterations": {
       "type": "integer",
       "description": "Maximum tool-call iterations before the subagent is considered incomplete. Defaults to model-specific value.",
   },
   ```
2. Add `temperature: float | None = None`, `max_tokens: int | None = None`, `max_iterations: int | None = None` to `execute()` signature
3. Pass them through to `self._manager.spawn()`

**Criterion**: `python3 -c "from nanobot.agent.tools.spawn import SpawnTool; import inspect; sig = inspect.signature(SpawnTool.execute); print(list(sig.parameters.keys()))"` → list includes `temperature`, `max_tokens`, `max_iterations`

---

### Milestone D: Unit tests

**File**: `tests/test_subagent_params.py`

Write tests for:
1. `_get_model_defaults("qwen3-coder-next")` returns correct values
2. `_get_model_defaults("unknown-model")` returns `SUBAGENT_DEFAULT_PARAMS`
3. `_get_model_defaults("minimax.minimax-m2.1")` returns 8192 max_tokens
4. `SubagentManager.spawn()` accepts `temperature`, `max_tokens`, `max_iterations` without error (mock the provider)
5. `SpawnTool.execute()` passes `temperature`/`max_tokens`/`max_iterations` through to `manager.spawn()`

**Criterion**: `python3 -m pytest tests/test_subagent_params.py -v --timeout=30 2>&1 | tail -10` → all pass

---

### Milestone E: Ruff + full test suite + commit

**Files**: `nanobot/agent/subagent.py`, `nanobot/agent/tools/spawn.py`, `tests/test_subagent_params.py`

```bash
cd /Users/mhall/Workspaces/nanobot
python3 -m ruff check nanobot/agent/subagent.py nanobot/agent/tools/spawn.py tests/test_subagent_params.py
python3 -m pytest tests/ -q -k "not integration" --timeout=30 2>&1 | tail -5
git add nanobot/agent/subagent.py nanobot/agent/tools/spawn.py tests/test_subagent_params.py
git commit -m "Task 15+38: per-spawn temperature/max_tokens/max_iterations with per-model defaults"
git push origin main
```

**Criterion**: `git log --oneline -1` → commit message contains "Task 15+38"

---

## Important Notes

- **Do NOT change `SubagentManager.__init__` defaults** — `self.temperature = 0.7` and `self.max_tokens = 4096` remain as the manager-level fallback. The new per-model defaults are layered on top of those, and per-spawn overrides are layered on top of those.
- **Ruff style**: double quotes, no unused imports, no `ruff --fix`
- **One milestone per commit** is preferred but not required — at minimum commit after Milestone D (tests passing) and after Milestone E (full suite + push)
- The `_extract_narrative` function and `_announce_result` wiring from 15.2 are already in place — do not touch them

## Execution Order

A → B → C → D → E (sequential, each depends on the previous)

Start with Milestone A. Verify criterion passes before moving to B.
