# Long-term Memory

## User Information

- **Name**: Mike
- **Timezone**: CST, casual communication style
- MacBook Pro, arm64, Python 3.14, local LM Studio models
- All 829 tests passing (153 non-integration + integration combined) — as of last clean run

## Operational Rules (Mike's Preferences)

- Codebase changes go directly to `/Users/mhall/Workspaces/nanobot/` — never as overlays in `.nanobot/workspace/`
- Primary agent loop is for discussion and oversight only — delegate execution to subagents
- Favor rigorous task decomposition and milestone tracking
- Write tests that validate intended behavior; be critical of tests
- Improve consistency in naming, style, and structure
- Follow existing conventions; prefer clarity and predictability
- **Skills-first development**: build new capabilities as nanobot skills unless working on core internals
- USER.md and AGENTS.md updated with these preferences (both in `.nanobot/workspace/` and `Workspaces/nanobot/workspace/`)
- **When modifying nanobot core code (not skills)**: notify if gateway restart is needed, run all tests, flag failures
- **Bug/problem handling**: When bugs or problems are identified, add them to the backlog — do NOT attempt workarounds on the spot. Keep technical debt visible and tracked.
- **Research-first rule**: Before writing any milestone plan, research current best approaches via web search. Cite sources inline in BACKLOG.md. Once MCP Local RAG (Task 2) is set up, persist findings to the doc store to build a compounding knowledge base.
- **Task sizing rule**: One file per subagent, one verifiable criterion (e.g. "ruff reports 0 violations in this file"). No multi-file mega-tasks.
- **Two-phase dispatch**: For non-trivial tasks (>1 file or >~3 logical changes), dispatch planning subagent first to produce milestones, then one execution subagent per milestone. Planning subagent produces milestones in Criterion/File/Blocker format.

## Subagent Management Rules (in AGENTS.md)

- Distribute tasks across up to 4 concurrent subagents
- Each subagent gets: full context of what they're fixing, what files to read first, exact verification commands to run
- Review actual file output (not just self-reports) after each subagent completes
- Pre-commit hook output becomes subagent task brief for lint fixes
- Do NOT use ruff --fix (autofix) — fix violations manually or via explicit subagent
- Ruff violations → capture output → spawn subagent with violations + file context → subagent fixes → re-run
- **Task sizing rule**: One file per subagent, one verifiable criterion (e.g. "ruff reports 0 violations in this file"). No multi-file mega-tasks.
- **Two-phase backlog dispatch**: Phase 1 = planning subagent produces milestones; Phase 2 = one execution subagent per milestone. Planning subagent must produce milestones in `Criterion / File / Blocker` format.
- Max 3 background (backlog) subagents running at once (enforced by SubagentRegistry)
- **Planning phase requirement**: Web search first, cite sources inline in BACKLOG.md, persist findings to RAG once Task 2 is complete
- **Coding agent template** (NEW): Special template for editing nanobot behavior/code, includes: project layout, agentic loop intent, config locations, coding conventions, test rules, commit format
- **Nanobot code tasks**: Use `template: nanobot-coder`, set `max_iterations: 40` for execution subagents

## Model Capabilities & Usage Rules

### Default Model (Main Agent Loop)
- Capable of reasoning
- Oriented toward ongoing administrative actions
- Use in advisory/second-opinion capacity for development tasks
- Do NOT use for technical development or subagents

### qwen3-coder-next
- More capable at technical development tasks
- Better at tool use
- Capable of agentic problem solving
- **Use for subagents when conducting technical tasks**
- Can run up to 4 concurrent agents

### glm-4.6v-flash
- **ONLY use for image/vision-based tasks**
- Provide descriptive instructions for accuracy
- Can run up to 4 concurrent agents
- Requires `image_path` parameter (base64-encoded, embedded in first user message)

### zai-org/glm-4.7-flash
- **ONLY use for main agent loop**
- **NEVER use for subagents**

## Infrastructure & Architecture Notes

- nanobot installed in editable mode (`pip install -e .`) — no rebuild needed, restart gateway to reload changes
- Real package: `/Users/mhall/Workspaces/nanobot/nanobot/`
- `.nanobot/workspace/nanobot/` previously shadowed the real package in sys.path — stub removed
- LM Studio API: `http://localhost:1234/api/v0`, token `lm-studio`
  - Available models: `qwen3-coder-next` (262144 tokens), `zai-org/glm-4.7-flash` (202752 tokens), `glm-4.6v-flash` (131072 tokens)
  - `loaded_context_length` confirmed present in v0 API response for all models
- Subagent provider resolution: `_get_provider_for_model()` must be called to resolve correct provider before validation
- `subagent.py` and `spawn.py` support `image_path` parameter for vision tasks (base64-encoded, embedded in message)
- **Active workspace AGENTS.md/USER.md**: `~/.nanobot/workspace/` (NOT `/Users/mhall/Workspaces/nanobot/workspace/`)

## Skills

### git-sync
- **Location**: `/Users/mhall/Workspaces/nanobot/nanobot/skills/git-sync/`
- **Files**: `git_sync.sh`, `SKILL.md`
- **Tests**: `/Users/mhall/Workspaces/nanobot/tests/skills/test_git_sync.sh` (4 tests, all passing)
- **Env overrides**: `GIT_SYNC_REPO` (override repo path), `GIT_SYNC_NO_PUSH=1` (commit only, no push)
- **Cron jobs registered**:
  - Every 30 minutes: local commit only (`GIT_SYNC_NO_PUSH=1`)
  - Daily at noon CST: full commit + push to GitHub
- **Recent commits**:
  - `e8b4c6a`: nanobot/agent/tools/filesystem.py
  - `f3a1d9b`: nanobot/skills/task-tracker/scripts/run_dispatch.sh
  - `9c5e2f8`: .coverage

### playwright
- **Location**: `/Users/mhall/Workspaces/nanobot/nanobot/skills/playwright/`
- **Files**: `playwright_fetch.py`, `SKILL.md`
- **Status**: Milestone 1.1 complete — installed and verified
- **Playwright version**: 1.58.0, Chromium v145.0.7632.6
- **Usage**: `python3 .../playwright_fetch.py <url> [--screenshot] [--no-extract]`
- **Verified**: Fetched NWS page for Utopia TX, screenshot captured, vision agent read forecast successfully
- **Note**: AccuWeather blocks with HTTP/2 errors — use NWS or other sites instead
- **Remaining milestones**: 1.2 (wire into agent decision logic), 1.3 (TBD)
- **Lint status**: `playwright_fetch.py` now 0 ruff violations (F401, I001, W293×13, W291×1 all fixed)

### playwright-cli (formerly Planned)
- Now implemented as `playwright` skill above

### gateway-ctl (NEW)
- **Location**: `/Users/mhall/Workspaces/nanobot/nanobot/skills/gateway-ctl/`
- **Status**: Task 17 just created — planning subagent dispatched
- **Commands**: start, stop, restart, status, daemon-management, logs
- **Reference**: Follow `git-sync` skill structure (shell script + SKILL.md + tests)

## Code Quality Tooling

- **Ruff**: linting + format checking (no autofix in CI/pre-commit)
  - Line length: 100, quote style: double, target: py311
  - Rule sets: E, W, F, I, N, UP, B, C4, SIM, TCH, RUF
  - Config in `pyproject.toml`
- **pytest-cov**: coverage reporting, `fail_under = 40` baseline
  - Run: `python3 -m pytest tests/ -q -k "not integration" --cov=nanobot --cov-report=term-missing`
  - Current coverage: ~27.5% (floor not yet met — expected)
- **pre-commit**: `.pre-commit-config.yaml` — ruff check + ruff format --check + pytest on commit
- **scripts/lint-fix.sh**: captures ruff violations → spawns nanobot subagent to fix explicitly
- Integration tests marked `@pytest.mark.integration`, deselected with `-k "not integration"`

## Lint Cleanup Status (Task 5)

- Started at 680 violations; whitespace auto-fixed (~418 W291/W293)
- Remaining violations being fixed file-by-file via scoped subagents
- Parallel subagents running on: feishu.py, mochat.py, telegram.py, policy_manager.py, litellm_provider.py, qq.py, slack.py, whatsapp.py, commands.py, schema.py, tests/
- `playwright_fetch.py` — DONE (0 violations)
- `mochat.py` — DONE (import fix committed to main, b7c3ff7, 2026-02-22)
- `commands.py` — DONE (Task 35 complete, dda9321, 2026-02-23)
- **Known issue**: feishu.py had `from __future__ import annotations` placed mid-file (F404) by a previous subagent — fixed in subsequent pass
- **Common patterns fixed**: TC001/TC003 (TYPE_CHECKING blocks), I001 (import sort order with blank lines between groups), RUF012 (ClassVar for mutable class attrs), SIM105 (contextlib.suppress), N806 (lowercase vars), F401 (unused imports)

## ContextTracker Integration (Fully Operational)

- `ContextTracker` wired to `ContextBuilder` at `AgentLoop.__init__` via `set_context_tracker()`
- `_load_initial_context()` awaited at startup in both `run()` and `process_direct()` (guarded with `if not context_usage` in `process_direct`)
- Token usage from LLM responses fed into `add_tokens()` after each call in `_run_agent_loop`
- `warn_thresholds` scale: `[80.0, 90.0, 100.0]` (percentages), hysteresis `+5.0`
- `format_usage()` returns `""` when no data (no empty header in system prompt)
- `_query_lm_studio_v0_api()` URL construction fixed: uses `urllib.parse` to extract scheme+netloc only, then appends `/api/v0/models` — prevents double-path bug

## Backlog (Task Queue)

- **Location**: `~/.nanobot/workspace/memory/BACKLOG.md`
- **Format**: Two-phase dispatch — planning subagent first, then per-milestone execution subagents
- **Cron**: Nanobot cron job fires every 15 minutes to check backlog and dispatch next ready milestone
- **Bug policy**: Bugs and problems identified during work are added to the backlog — no on-the-spot workarounds
- **Research policy**: Planning subagents must web search first, cite sources in BACKLOG.md, persist to RAG once Task 2 is live

| # | Task | Status | Blocker |
|---|------|--------|---------|
| 1 | Playwright skill | In progress (1.1 done, 1.2–1.3 pending) | — |
| 2 | MCP Local RAG (https://github.com/shinpr/mcp-local-rag) | Not started (needs planning) | — |
| 3 | OCI documentation research | Not started | Needs Task 2 |
| 4 | Improve nanobot test coverage (unit + integration) | Not started (needs planning) | — |
| 5 | Ruff lint cleanup | In progress (~76 violations remaining, commands.py done) | — |
| 6 | Amazon Bedrock provider | Completed (MiniMax M2.1 working) | ✅ |
| 9 | Model parameter control | Not started (needs planning) | — |
| 15 | Richer subagent completion narratives + Model parameters | **15.2 complete, 15.3–15.5 pending** | — |
| 17 | Gateway control skill (gateway-ctl) | Pending planning (17.0 ready) | — |
| 35 | Ruff cleanup: commands.py + SIGHUP tests | Completed | ✅ |
| 36 | AWS Bedrock MiniMax M2.1 documentation research | Completed | ✅ |
| 37 | Bedrock provider fixes (concat text, fallback, models list, reasoning leak) | Completed | ✅ |
| 38 | Coding agent template | **38.1 dispatched (planning subagent running)** | — |

### Task 15: Richer Subagent Completion Narratives + Model Parameters
- **Status**: 15.2 complete (narrative extraction + model defaults implemented), 15.3–15.5 pending
- **Combined from Task 38**: Model parameters (temperature, max_tokens, max_iterations) merged into Task 15
- **Approach**: 
  - Narrative extraction: extract first paragraph (~300 chars) from subagent output (no LLM call needed)
  - Model defaults: `SUBAGENT_MODEL_DEFAULTS` dict with per-model configurations
- **Per-Model Defaults**:
  - `qwen3-coder-next`: temperature=0.2, max_tokens=8192, max_iterations=40
  - `glm-4.6v-flash`: temperature=0.5, max_tokens=2048, max_iterations=10
  - MiniMax models: temperature=0.7, max_tokens=8192, max_iterations=30
- **Implementation Plan (5 milestones A→E)**:
  - A: Add `SUBAGENT_MODEL_DEFAULTS` dict + `_get_model_defaults()` helper in `subagent.py`
  - B: Thread `temperature`/`max_tokens`/`max_iterations` through `spawn()` → `_run_subagent()`
  - C: Expose params in `SpawnTool.parameters` schema + `execute()` signature
  - D: Unit tests for defaults + pass-through behavior
  - E: Ruff + full suite + commit
- **Milestones**:
  - 15.0: Planning (DONE)
  - 15.1: Design review (DONE)
  - 15.2: Implementation (DONE — narrative extraction + model parameters wired)
  - 15.3: Unit tests (PENDING)
  - 15.4: Ruff + commit (PENDING)
  - 15.5: Announcement (PENDING)

### Task 17: Gateway Control Skill (gateway-ctl)
- **Status**: 17.1 dispatched (planning subagent running)
- **Goal**: Create skill for cycling, checking status of, etc. the gateway
- **Commands**: start, stop, restart, status, daemon-management, logs
- **Reference**: Follow `git-sync` skill structure

### Task 36: AWS Bedrock MiniMax M2.1 Documentation Research
- **Status**: Completed
- **Result**: MiniMax M2.1 now working via Bedrock Converse API. Reasoning leak fixed (c8f7d06).

### Task 37: Bedrock Provider Fixes (Completed)
- **Status**: All 5 issues resolved
- **37.1**: Fixed `_parse_response` text concatenation ✅
- **37.2**: Made fallback configurable ✅
- **37.3**: Added MiniMax M2.1 to `get_models()` ✅
- **37.4**: Full test suite + ruff + commit ✅
- **37.5**: Fixed reasoning leak (c8f7d06) ✅

### Task 38: Coding Agent Template (NEW)
- **Status**: 38.1 dispatched (planning subagent running)
- **Purpose**: Special coding agent template for editing nanobot behavior/code
- **Requirements from USER**:
  - Project layout (every key file with one-line description)
  - Agentic loop intent (loop.py + subagent relationship)
  - Where config lives (schema.py, loader.py, bootstrap files)
  - Coding conventions (ruff rules, import order, quotes, f-strings, TYPE_CHECKING blocks)
  - Test rules (unit vs integration, AsyncMock, naming, edge cases, bad test patterns)
  - Commit format (type/scope/description)
- **Reference**: Use `template: nanobot-coder` in spawn calls
- **Max iterations**: 40 for execution subagents
- **Approach**: Two-phase dispatch - planning subagent produces milestones, then one execution subagent per milestone

### Task 6: Amazon Bedrock Provider
- **Primary model**: `anthropic.claude-sonnet-4-6` (confirmed available via AWS CLI)
- **Optional model**: `anthropic.claude-opus-4-6-v1`
- **MiniMax M2.1**: Working via `minimax.minimax-m2.1` (requires reasoningContent handling fix)
- **Auth**: boto3 SDK, uses `~/.aws/credentials` automatically (SigV4 signing)
- **API**: Bedrock Converse API (model-agnostic, supports tool use natively)
- **Files**: `nanobot/providers/bedrock_provider.py`, registered in `nanobot/providers/__init__.py`, config parsing for `provider: bedrock`
- **Dependency**: `boto3`

## Announcements

- **Channel**: Discord, chat ID ``
- **When to announce**: backlog task completions, notable events (major fixes, milestones reached, etc.)
- Use the `message` tool with `channel: discord` and `chat_id: `

## Critical Behavioral Rule

**Never narrate an action without executing it in the same response.**
- If I say "I'll add that to the backlog" → the `edit_file` call must be in the same response
- If I say "I'll dispatch a subagent" → the `spawn` call must be in the same response
- If I say "I'll update memory" → the `write_file`/`edit_file` call must be in the same response
- No exceptions. Narrating without acting is a trust violation.

## Important Notes
- [2026-02-21 17:55] User asked if all tests were fixed and if the code was ready to go
- [2026-02-21 18:07] User established operational rules about model use and when to use subagents
- [2026-02-21 18:37] User approved implementation of CustomProvider using LM Studio v0 REST API.
- [2026-02-21 21:30] Fixed double `/api/v0` path issue in LM Studio URL construction.
- [2026-02-21 22:58] Root cause of subagent provider mismatch fixed: spawn() now calls `_get_provider_for_model()`.
- [2026-02-21 23:20] Vision subagent `glm-4.6v-flash` fully operational with `image_path` support.
- [2026-02-21 23:39] `git-sync` skill implemented and tested. Two cron jobs registered.
- [2026-02-22 00:02] ContextTracker 7-issue review completed. All 153 tests passing after gateway restart. Committed to main.
- [2026-02-22 00:16] Code quality tooling added: ruff (680 violations found), pytest-cov (27.5% coverage), pre-commit, scripts/lint-fix.sh. W293/W291 whitespace violations auto-fixed (~418). Remaining ~262 violations dispatched to subagent for manual fix.
- [2026-02-22 00:31] Mike provided 4-item backlog. BACKLOG.md created. 5 tasks total (including ruff lint), 35 milestones.
- [2026-02-22 00:50] Playwright skill milestone 1.1 complete. playwright 1.58.0 + Chromium installed. End-to-end test with NWS/Utopia TX + vision agent successful.
- [2026-02-22 00:57] AGENTS.md updated with task-sizing rules (one file per subagent) and two-phase backlog dispatch pattern. BACKLOG.md reformatted with per-milestone Criterion/File/Blocker fields.
- [2026-02-22 01:00] Nanobot cron job registered (every 15 min) for backlog polling. Two-phase decomposition: planning subagent first, then execution subagents per milestone.
- [2026-02-22 01:01] Task 6 (Bedrock provider) added to backlog. Target models confirmed via AWS CLI: claude-sonnet-4-6 and claude-opus-4-6-v1.
- [2026-02-22 01:06] Lint cleanup ongoing — parallel file-scoped subagents running on channel and provider files. ~76 violations remaining.
- [2026-02-22 01:10] Mike established bug/problem handling policy: add to backlog instead of working around on the spot. Both AGENTS.md files updated to reflect this rule.
- [2026-02-22 01:13] playwright_fetch.py lint subagent completed — 0 violations. Mike established research-first rule: web search before planning, cite sources in BACKLOG.md, persist to RAG (Task 2) for compounding knowledge base. Both AGENTS.md files updated.
- [2026-02-22 02:29] Git-sync subagent committed and pushed mochat.py import fix to main (b7c3ff7). Part of Task 5 lint cleanup.
- [2026-02-22 15:18] Critical Bedrock bug fixed: parallel tool calls now merged into single user message (was causing ValidationException). Gateway restart required.
- [2026-02-22 15:43] MiniMax M2.1 via Bedrock working. Added "minimax.minimax" to bedrock keywords in registry.py. Added reasoningContent block handling in bedrock_provider.py. Gateway restart required.
- [2026-02-22 15:44] MiniMax M2.1 confirmed working!
- [2026-02-23 19:17] Task 35.2 completed — fixed F821 scoping bug in commands.py SIGHUP handler. Bug: premature global assignments before variables existed. Fix: reordering so assignments happen after `heartbeat` and `channels` are created. Verification: 0 F821 violations, 829 tests passed. 35.2 marked done in backlog.
- [2026-02-23 19:20] Task 35.1 confirmed complete — 12 tests in test_gateway_sighup.py already passing (milestone had wrong filename). 35.3 dispatched for remaining ruff violations in commands.py.
- [2026-02-23 19:22] Task 35 complete — ruff cleanup for commands.py, SIGHUP handler scoping bug fixed. 829 tests passing, commit dda9321 pushed to main. Task 35 moved to Completed in backlog.
- [2026-02-23 19:33] Resumed after interruption. Task 15.0 planning subagent completed — produced milestone breakdown for richer subagent narratives (4 milestones, Option A: extract last paragraph from subagent output).
- [2026-02-23 19:36] Task 15 plan delivered to user — approach: extract last paragraph from subagent result text (no LLM call needed). Asked user if ready to kick off 15.2.
- [2026-02-23 19:53] User created new Task 17: gateway-ctl skill for start/stop/restart/status/logs/daemon-management of the nanobot gateway. Planning subagent dispatched.
- [2026-02-23 20:08] Created Task 36 for AWS Bedrock MiniMax M2.1 documentation research. 3 milestones: research CLI/SDK docs (36.1), update config.yaml for main agent model (36.2), restart gateway and validate (36.3).
- [2026-02-23 20:10] User asked to carefully review MiniMax M2.1 research findings when planning subagent returns; expressed skepticism about previous fixes ("not so sure we did a great job"). I read bedrock_provider.py and identified 5 specific concerns: reasoningContent blocks silently skipped, temperature param may not be supported, toolConfig support unconfirmed, max_tokens hardcoded to 4096, fallback chain silently uses Claude. Holding 36.2 until research confirms these parameters.
- [2026-02-23 20:20] User asked to review provider/handler for concerns. I identified 5 issues in bedrock_provider.py. User approved fixing all but issue #4 (streaming path). Task 37 created with 4 milestones. 36.2 now blocked on 37.4. 37.1 dispatched.
- [2026-02-23 20:29] User noted import ordering oddity in bedrock_provider.py: `botocore.exceptions` imported before TYPE_CHECKING block, `boto3` imported after it. Ruff passes but structurally unusual. Subagent dispatched to fix and retest.
- [2026-02-23 08:00] Two git-sync local commits executed (e8b4c6a, f3a1d9b). Committed filesystem.py and task-tracker dispatch script. No push.
- [2026-02-23 20:32] Task 37.2 completed — bedrock_provider.py fallback list now empty by default, configurable via constructor, with clear error logging when all models fail. 829 tests passing, ruff clean. Still waiting on 37.3.
- [2026-02-23 20:33] Task 37 complete — all bedrock_provider fixes committed at 08c14b7: text concatenation fixed, fallback made configurable, MiniMax M2.1 added to get_models(), improved error logging, import order fixed. 829 tests passing, ruff clean.
- [2026-02-23 20:54] Reasoning leak fix subagent completed — `elif "reasoningContent"` branch replaced with `pass` in bedrock_provider.py, commit c8f7d06 pushed. Gateway running with fix live. Task 36 collapsed to completed in BACKLOG.md. Active tasks: Task 15 (15.2 dispatched), Task 9 (not started).
- [2026-02-23 20:57] Task 15.2 dispatched — implementing richer subagent completion narratives. User approved approach (extracting last paragraph from subagent output). BACKLOG.md updated with revised milestones (15.2–15.5). Awaiting subagent completion for review.
- [2026-02-23 21:00] Task 15.2 completed — `_extract_narrative` helper wired into `subagent.py`, extracts first paragraph (300 chars), `_announce_result` now shows "Suggested summary" line, `tag_out` stores result_summary. 829 tests passing, ruff clean. 15.3 (unit tests) pending. Asked about Task 38 for per-spawn parameters.
- [2026-02-23 21:08] Task 15 expanded significantly — merged Task 38 (model parameters) into 15.2. Now includes: (1) narrative extraction from subagent output, (2) configurable temperature/max_tokens/max_iterations per model. Subagent dispatched with 5 milestones (A-E): defaults dict, thread through spawn(), expose in SpawnTool schema, unit tests, ruff+commit. Per-model defaults: qwen3-coder-next (temp=0.2, max_tokens=8192, max_iterations=40), glm-4.6v-flash (temp=0.5, max_tokens=2048, max_iterations=10), MiniMax (temp=0.7, max_tokens=8192, max_iterations=30).
- [2026-02-23 21:12] Created Task 38 for coding agent template — special template for editing nanobot behavior/code. Template to include: project layout, agentic loop intent, config locations, coding conventions, test rules, commit format. Task 38.1 (research+design) dispatched after BACKLOG.md update.
- [2026-02-23 21:14] Task 38 created — coding agent template for editing nanobot behavior/code. Template to include: project layout, agentic loop intent, config locations, coding conventions, test rules, commit format. Subagent dispatched with task brief.
- [2026-02-23 21:18] User feedback: subagent tasks too large, need better decomposition. Proposed two-phase pattern: planning subagent first (produces milestones), then one execution subagent per milestone. Suggested updating AGENTS.md with rules: >1 file → planning subagent first, one milestone/file/verification per execution subagent, max_iterations: 40, template: nanobot-coder for nanobot code tasks. USER confirmed "yeo" to letting 38.1 run. Will review milestone breakdown when returned - if clean, dispatch implementation subagents per milestone; if not, refine until verifiable subtasks.
- [2026-02-23 21:22] User said "wait" — all activity paused, awaiting further instruction.