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
