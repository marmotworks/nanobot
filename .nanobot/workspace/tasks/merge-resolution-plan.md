## nanobot/agent/context.py
**Upstream**: Removed redundant `platform` import (moved to top), changed `BOOTSTRAP_FILES` from class attribute to `ClassVar`, added `failure_tracker` and `context_tracker` parameters to `__init__`, added failure summary and context window usage to system prompt, and changed identity section to emphasize direct text responses over tool calls.
**Ours**: Added `failure_tracker` parameter, context tracker support, and improved identity section with more explicit instructions about direct responses and tool usage.
**Resolution**: Keep ours — our fork already incorporates upstream's `failure_tracker` and `context_tracker` changes, and our identity section improvements are compatible. The changes are additive and already merged.

## nanobot/agent/loop.py
**Upstream**: Changed default `max_iterations` from 40 to 20, `temperature` from 0.1 to 0.7, `memory_window` from 100 to 50; removed `channels_config` parameter; added `PolicyManager`, `ContextTracker`, and DiscordReactTool; improved MCP connection with contextlib; added `_chat_with_fallback` with tiered fallback support; removed redundant `AsyncExitStack` imports.
**Ours**: Added `config` parameter, policy manager integration, context tracker, DiscordReactTool registration, and fallback mechanisms. Our fork has `max_iterations=40` and `temperature=0.7`.
**Resolution**: Manual merge. Keep upstream's `max_iterations=20` and `temperature=0.7` defaults (they're more reasonable), but keep our `config` parameter, policy manager, and DiscordReactTool additions. The context tracker and MCP improvements from upstream should be integrated.

## nanobot/agent/tools/registry.py
**Upstream**: Added `FailureTracker` integration to track and record tool failures; removed `_HINT` suffix from error messages; improved error handling to record failures.
**Ours**: Already includes failure tracker integration with the same pattern.
**Resolution**: Keep ours — our fork already has the upstream failure tracking changes integrated. No additional merge needed.

## nanobot/bus/events.py
**Upstream**: Removed `session_key_override` field from `InboundMessage`; simplified `session_key` property to always use `f"{channel}:{chat_id}"`.
**Ours**: Already reflects this change (no `session_key_override` in our version).
**Resolution**: Keep ours — our fork already has the upstream simplification applied. The override field was removed upstream.

## nanobot/channels/discord.py
**Upstream**: Added expressive emoji triggers (`EXPRESSIVE_TRIGGERS`), interactive reaction actions (`INTERACTIVE_ACTIONS`), reaction handling via `_react_to_message` and `_handle_reaction_add`, and simplified typing loop with `contextlib.suppress`.
**Ours**: Already has all these changes — expressive triggers, interactive actions, reaction handling, and simplified typing loop.
**Resolution**: Keep ours — our fork already has the upstream Discord reaction features integrated. The emoji registries and reaction handlers are present.

## nanobot/channels/manager.py
**Upstream**: Simplified channel initialization (removed redundant parens), replaced `AsyncExitStack` with `contextlib`, improved supervisor pattern with `contextlib.suppress`, removed progress message filtering logic.
**Ours**: Already has `contextlib` usage, simplified initialization, and progress filtering removal.
**Resolution**: Keep ours — our fork already has the upstream simplifications. The channel initialization and cleanup patterns match upstream.

## nanobot/cli/commands.py
**Upstream**: Added daemon management (`--install-daemon`, `--uninstall-daemon`, `--daemon-status`), SIGHUP handler for config reload, BedrockProvider direct support, and refactored `_create_workspace_templates` to use inlined templates instead of importlib.resources.
**Ours**: Already has daemon management, SIGHUP handler, BedrockProvider support, and inlined templates.
**Resolution**: Keep ours — our fork already has the upstream CLI improvements. The daemon management and SIGHUP handler are present.

## nanobot/heartbeat/service.py
**Upstream**: Removed `on_notify` callback; simplified `HEARTBEAT_PROMPT` and `HEARTBEAT_OK_TOKEN` handling; removed `start` idempotency check; simplified `_is_heartbeat_empty` logic.
**Ours**: Already has the simplified `on_notify` removed, improved `HEARTBEAT_OK_TOKEN` checking, and simplified logic.
**Resolution**: Keep ours — our fork already incorporates upstream's heartbeat simplifications. The progress suppression and response handling match upstream.

## workspace/AGENTS.md
**Upstream**: Deleted this file (moved to nanobot/templates/ for packaging).
**Ours**: Modified and kept the file with enhanced planning gate rules and dispatch checklist.
**Resolution**: Keep ours — the file was moved upstream for packaging but our fork needs the local workspace template for agent instructions. The enhanced planning gate rules and dispatch checklist are valuable additions.
