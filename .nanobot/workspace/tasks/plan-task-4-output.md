## Task 4: Test Coverage — Milestone Breakdown

### 4.1 Test `CronTool.execute` with all action types
Criterion: `python3 -m pytest tests/test_cron_tool.py -v --cov=nanobot.agent.tools.cron --cov-report=term-missing` → **100% coverage**
File: `tests/test_cron_tool.py`
Covers: `nanobot.agent.tools.cron.CronTool`
Blocker: none
Note: Test `execute()` with `add`, `list`, `remove` actions; test validation errors (missing message, unknown timezone, invalid schedule); mock `CronService` to avoid disk I/O

### 4.2 Test `ExecTool._guard_command` safety guards
Criterion: `python3 -m pytest tests/test_shell_tool.py -v --cov=nanobot.agent.tools.shell --cov-report=term-missing` → **100% coverage**
File: `tests/test_shell_tool.py`
Covers: `nanobot.agent.tools.shell.ExecTool._guard_command`
Blocker: none
Note: Test deny patterns (rm -rf, shutdown, fork bomb); test allowlist; test workspace restriction with path traversal; test absolute path validation

### 4.3 Test `WebSearchTool.execute` with API mocking
Criterion: `python3 -m pytest tests/test_web_search_tool.py -v --cov=nanobot.agent.tools.web --cov-report=term-missing` → **100% coverage**
File: `tests/test_web_search_tool.py`
Covers: `nanobot.agent.tools.web.WebSearchTool`
Blocker: none
Note: Mock `httpx.AsyncClient` to avoid real API calls; test missing API key; test empty results; test result parsing and formatting

### 4.4 Test `WebFetchTool.execute` with URL validation
Criterion: `python3 -m pytest tests/test_web_fetch_tool.py -v --cov=nanobot.agent.tools.web --cov-report=term-missing` → **100% coverage**
File: `tests/test_web_fetch_tool.py`
Covers: `nanobot.agent.tools.web.WebFetchTool`
Blocker: none
Note: Test URL validation (_validate_url); test JSON content type; test HTML extraction via readability; test truncation; mock httpx client

### 4.5 Test `MemoryStore` persistence and consolidation flow
Criterion: `python3 -m pytest tests/test_memory_store.py -v --cov=nanobot.agent.memory --cov-report=term-missing` → **100% coverage**
File: `tests/test_memory_store.py`
Covers: `nanobot.agent.memory.MemoryStore`
Blocker: none
Note: Test read/write long-term memory; test append_history; test get_memory_context; test consolidate() with mocked LLM provider; test archive_all and memory_window modes

### 4.6 Test `CronService` job lifecycle and timer
Criterion: `python3 -m pytest tests/test_cron_service_full.py -v --cov=nanobot.cron.service --cov-report=term-missing` → **100% coverage**
File: `tests/test_cron_service_full.py`
Covers: `nanobot.cron.service.CronService`
Blocker: none
Note: Test start/stop lifecycle; test add_job with all schedule types (at, every, cron); test list_jobs, remove_job, enable_job; test _execute_job and delete_after_run for one-shot jobs

### 4.7 Test `CronService._compute_next_run` for all schedule kinds
Criterion: `python3 -m pytest tests/test_cron_scheduler.py -v --cov=nanobot.cron.service --cov-report=term-missing` → **100% coverage**
File: `tests/test_cron_scheduler.py`
Covers: `nanobot.cron.service._compute_next_run`
Blocker: none
Note: Test `at` schedule (one-time); test `every` schedule (recurring); test `cron` schedule with croniter; test edge cases (past time, invalid timezone)

### 4.8 Test `cli.commands._make_provider` provider selection logic
Criterion: `python3 -m pytest tests/test_cli_make_provider.py -v --cov=nanobot.cli.commands --cov-report=term-missing` → **100% coverage**
File: `tests/test_cli_make_provider.py`
Covers: `nanobot.cli.commands._make_provider`
Blocker: none
Note: Test provider selection for bedrock, openai_codex, custom, and litellm; test missing API key error; mock Config to isolate logic

### 4.9 Test `cli.commands.gateway` daemon management options
Criterion: `python3 -m pytest tests/test_cli_gateway_daemon.py -v --cov=nanobot.cli.commands --cov-report=term-missing --cov-report=xml` → **100% coverage**
File: `tests/test_cli_gateway_daemon.py`
Covers: `nanobot.cli.commands.gateway` (daemon install/uninstall/status branches)
Blocker: none
Note: Mock subprocess calls for npm; mock daemon manager functions; test SIGHUP handler registration; mock all async components

### 4.10 Test `cli.commands.agent` interactive mode input handling
Criterion: `python3 -m pytest tests/test_cli_agent_interactive.py -v --cov=nanobot.cli.commands --cov-report=term-missing` → **100% coverage**
File: `tests/test_cli_agent_interactive.py`
Covers: `nanobot.cli.commands.agent` interactive mode
Blocker: none
Note: Mock `_init_prompt_session`, `_read_interactive_input_async`, bus publish/consume; test exit commands; test message flow through bus
