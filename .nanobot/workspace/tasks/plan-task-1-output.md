## Task 1: Playwright Skill — Remaining Milestones

### 1.2 Wire Playwright into agent tool registry
Criterion: `grep -n "playwright_fetch" /Users/mhall/Workspaces/nanobot/nanobot/agent/loop.py` → `133: self.tools.register(WebFetchTool())` with addition of Playwright tool registration
File: `nanobot/agent/loop.py`
Blocker: none
Note: Add PlaywrightFetchTool wrapper class that implements Tool interface (name, description, parameters, execute) and register it alongside WebFetchTool. The agent can then call `playwright_fetch` directly. This requires creating `/Users/mhall/Workspaces/nanobot/nanobot/agent/tools/playwright.py` as a wrapper that calls the skill script.

### 1.3 Create PlaywrightFetchTool wrapper class
Criterion: `python3 -c "from nanobot.agent.tools.playwright import PlaywrightFetchTool; t = PlaywrightFetchTool(); print(t.name, t.to_schema())"` → outputs tool name and valid OpenAI schema
File: `nanobot/agent/tools/playwright.py`
Blocker: 1.2
Note: Create a new Tool subclass that wraps the playwright_fetch.py skill. The execute method should invoke the script via subprocess with proper argument mapping. This enables the agent to use Playwright as a callable tool instead of relying on ad-hoc script execution.

### 1.4 Add auto-decision fallback logic
Criterion: Test case: web_fetch fails on JS-heavy site → agent falls back to playwright_fetch automatically
File: `nanobot/agent/tools/failure_tracker.py`
Blocker: 1.3
Note: Extend the failure tracker to record when web_fetch returns empty/error for URLs, then teach the agent to prefer playwright_fetch for such patterns. Alternatively, add a unified web access tool that tries web_fetch first, then playwright_fetch on failure. This makes the skill transparent to the user.

### 1.5 Integration test for Playwright tool
Criterion: `pytest -v tests/test_playwright_tool.py` → passes with 100% coverage of PlaywrightFetchTool
File: `tests/test_playwright_tool.py`
Blocker: 1.3
Note: Create integration tests that verify the tool registers correctly, validates parameters, and successfully fetches a test URL (e.g., a known JS-heavy site). Test both success and timeout/error paths.
