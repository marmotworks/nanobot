"""Agent loop: the core processing engine."""

from __future__ import annotations

import asyncio
import contextlib
import json
import re
from typing import TYPE_CHECKING

from loguru import logger

from nanobot.agent.context import ContextBuilder
from nanobot.agent.context_tracker import ContextTracker
from nanobot.agent.memory import MemoryStore
from nanobot.agent.subagent import SubagentManager
from nanobot.agent.tools.cron import CronTool
from nanobot.agent.tools.filesystem import EditFileTool, ListDirTool, ReadFileTool, WriteFileTool
from nanobot.agent.tools.message import MessageTool
from nanobot.agent.tools.registry import ToolRegistry
from nanobot.agent.tools.shell import ExecTool
from nanobot.agent.tools.spawn import SpawnTool
from nanobot.agent.tools.web import WebFetchTool, WebSearchTool
from nanobot.bus.events import InboundMessage, OutboundMessage
from nanobot.policy_manager import PolicyManager
from nanobot.session.manager import SessionManager

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable
    from pathlib import Path

    from nanobot.bus.queue import MessageBus
    from nanobot.config.schema import ExecToolConfig
    from nanobot.cron.service import CronService
    from nanobot.providers.base import LLMProvider


class AgentLoop:
    """
    The agent loop is the core processing engine.

    It:
    1. Receives messages from the bus
    2. Builds context with history, memory, skills
    3. Calls the LLM
    4. Executes tool calls
    5. Sends responses back
    """

    def __init__(
        self,
        bus: MessageBus,
        provider: LLMProvider,
        workspace: Path,
        model: str | None = None,
        max_iterations: int = 20,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        memory_window: int = 50,
        brave_api_key: str | None = None,
        exec_config: ExecToolConfig | None = None,
        cron_service: CronService | None = None,
        restrict_to_workspace: bool = False,
        session_manager: SessionManager | None = None,
        mcp_servers: dict | None = None,
        config: object | None = None,
    ):
        from nanobot.config.schema import ExecToolConfig

        self.bus = bus
        self.provider = provider
        self.workspace = workspace
        self.model = model or provider.get_default_model()
        self.max_iterations = max_iterations
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.memory_window = memory_window
        self.brave_api_key = brave_api_key
        self.exec_config = exec_config or ExecToolConfig()
        self.cron_service = cron_service
        self.restrict_to_workspace = restrict_to_workspace

        self.context = ContextBuilder(workspace)
        self.sessions = session_manager or SessionManager(workspace)
        self.tools = ToolRegistry()
        self.subagents = SubagentManager(
            provider=provider,
            workspace=workspace,
            bus=bus,
            model=self.model,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            brave_api_key=brave_api_key,
            exec_config=self.exec_config,
            restrict_to_workspace=restrict_to_workspace,
            config=config,
        )
        self.policy_manager = PolicyManager(workspace / "config" / "policies.json")
        self.context_tracker = ContextTracker(provider)
        self.set_context_tracker(self.context_tracker)

        self._config = config

        self._running = False
        self._mcp_servers = mcp_servers or {}
        self._mcp_stack: contextlib.AsyncExitStack | None = None
        self._mcp_connected = False
        self._mcp_connecting = False
        self._consolidating: set[str] = set()  # Session keys with consolidation in progress
        self._consolidation_locks: dict[
            str, asyncio.Lock
        ] = {}  # Locks per session for consolidation deduplication
        self._consolidation_tasks: list[asyncio.Task[bool]] = []  # In-flight consolidation tasks
        self._register_default_tools()

    def set_context_tracker(self, context_tracker: ContextTracker) -> None:
        """Set the context tracker for the ContextBuilder."""
        self.context.context_tracker = context_tracker

    def _register_default_tools(self) -> None:
        """Register the default set of tools."""
        allowed_dir = self.workspace if self.restrict_to_workspace else None
        for cls in (ReadFileTool, WriteFileTool, EditFileTool, ListDirTool):
            self.tools.register(cls(workspace=self.workspace, allowed_dir=allowed_dir))
        self.tools.register(
            ExecTool(
                working_dir=str(self.workspace),
                timeout=self.exec_config.timeout,
                restrict_to_workspace=self.restrict_to_workspace,
            )
        )
        self.tools.register(WebSearchTool(api_key=self.brave_api_key))
        self.tools.register(WebFetchTool())
        self.tools.register(MessageTool(send_callback=self.bus.publish_outbound))
        self.tools.register(SpawnTool(manager=self.subagents, policy_manager=self.policy_manager))
        if self.cron_service:
            self.tools.register(CronTool(self.cron_service))
        # Register discord_react if a Discord token is available
        if self._config is not None:
            token = getattr(getattr(self._config, "discord", None), "token", None)
            if token:
                from nanobot.agent.tools.react import DiscordReactTool

                self.tools.register(DiscordReactTool(token=token))

    async def _connect_mcp(self) -> None:
        """Connect to configured MCP servers (one-time, lazy)."""
        if self._mcp_connected or self._mcp_connecting or not self._mcp_servers:
            return
        self._mcp_connecting = True
        from nanobot.agent.tools.mcp import connect_mcp_servers

        try:
            self._mcp_stack = contextlib.AsyncExitStack()
            await self._mcp_stack.__aenter__()
            await connect_mcp_servers(self._mcp_servers, self.tools, self._mcp_stack)
            self._mcp_connected = True
        except Exception as e:
            logger.error("Failed to connect MCP servers (will retry next message): {}", e)
            if self._mcp_stack:
                with contextlib.suppress(Exception):
                    await self._mcp_stack.aclose()
                self._mcp_stack = None
        finally:
            self._mcp_connecting = False

    def _set_tool_context(self, channel: str, chat_id: str, message_id: str | None = None) -> None:
        """Update context for all tools that need routing info."""
        if (message_tool := self.tools.get("message")) and isinstance(message_tool, MessageTool):
            message_tool.set_context(channel, chat_id, message_id)

        if (spawn_tool := self.tools.get("spawn")) and isinstance(spawn_tool, SpawnTool):
            spawn_tool.set_context(channel, chat_id)

        if (cron_tool := self.tools.get("cron")) and isinstance(cron_tool, CronTool):
            cron_tool.set_context(channel, chat_id)

    @staticmethod
    def _strip_think(text: str | None) -> str | None:
        """Remove <think>…</think> blocks that some models embed in content."""
        if not text:
            return None
        return re.sub(r"<think>[\s\S]*?</think>", "", text).strip() or None

    @staticmethod
    def _tool_hint(tool_calls: list) -> str:
        """Format tool calls as concise hint, e.g. 'web_search("query")'."""

        def _fmt(tc):
            val = next(iter(tc.arguments.values()), None) if tc.arguments else None
            if not isinstance(val, str):
                return tc.name
            return f'{tc.name}("{val[:40]}…")' if len(val) > 40 else f'{tc.name}("{val}")'

        return ", ".join(_fmt(tc) for tc in tool_calls)

    async def _chat_with_fallback(
        self,
        messages: list[dict],
        tools: list[dict],
        model: str,
        temperature: float,
        max_tokens: int,
    ):
        """Call provider.chat(), falling back through multiple tiers on rate limit or auth errors."""
        from nanobot.providers.base import LLMResponse

        # Tier 1: Primary provider
        response = await self.provider.chat(
            messages=messages,
            tools=tools,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        # Detect rate limit / auth / overload errors returned as content strings
        content = response.content or ""
        is_error = response.finish_reason == "error" or (
            isinstance(content, str) and content.startswith("Error calling LLM:")
        )
        is_fallback_error = is_error and any(
            kw in content
            for kw in ("rate_limit", "RateLimitError", "overloaded", "AuthenticationError", "quota")
        )

        if is_fallback_error:
            # Skip fallback if primary is already BedrockProvider to avoid infinite loop
            provider_name = self.provider.__class__.__name__
            if provider_name == "BedrockProvider":
                logger.warning(
                    "Primary provider is BedrockProvider, skipping fallback: {}", content[:120]
                )
                return response

            # Tier 2: Local CustomProvider with config-driven values
            tier2_model = "zai-org/glm-4.7-flash"
            tier2_api_base = "http://localhost:1234/v1"
            if (
                self._config is not None
                and self._config.fallback is not None
                and self._config.fallback.tier2 is not None
            ):
                tier2_model = self._config.fallback.tier2.model
                tier2_api_base = self._config.fallback.tier2.api_base or "http://localhost:1234/v1"

            logger.warning(
                "Primary provider error — falling back to local {}: {}", tier2_model, content[:120]
            )
            try:
                from nanobot.providers.custom_provider import CustomProvider

                fallback = CustomProvider(
                    api_key="lm-studio",
                    api_base=tier2_api_base,
                    default_model=tier2_model,
                )
                response = await fallback.chat(
                    messages=messages,
                    tools=tools,
                    model=tier2_model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                logger.info("Fallback to {} succeeded", tier2_model)
            except Exception as e:
                logger.error("Tier 2 fallback provider also failed: {}", e)
                # Tier 3: AWS Bedrock with config-driven values
                tier3_region = "us-east-1"
                tier3_model = "us.anthropic.claude-sonnet-4-6"
                if (
                    self._config is not None
                    and self._config.fallback is not None
                    and self._config.fallback.tier3 is not None
                ):
                    tier3_region = self._config.fallback.tier3.region or "us-east-1"
                    tier3_model = (
                        self._config.fallback.tier3.model or "us.anthropic.claude-sonnet-4-6"
                    )

                logger.warning(
                    "Tier 2 fallback failed — falling back to AWS Bedrock ({})", tier3_model
                )
                try:
                    from nanobot.providers.bedrock_provider import BedrockProvider

                    fallback = BedrockProvider(
                        region_name=tier3_region,
                        default_model=tier3_model,
                    )
                    response = await fallback.chat(
                        messages=messages,
                        tools=tools,
                        model=tier3_model,
                        temperature=temperature,
                        max_tokens=max_tokens,
                    )
                    logger.info("Fallback to AWS Bedrock ({}) succeeded", tier3_model)
                except Exception as e2:
                    logger.error("Tier 3 fallback also failed: {}", e2)
                    return LLMResponse(
                        content=f"All three providers failed: Tier1 error; Tier2: {e}; Tier3: {e2}",
                        finish_reason="error",
                    )

        return response

    async def _run_agent_loop(
        self,
        initial_messages: list[dict],
        on_progress: Callable[[str], Awaitable[None]] | None = None,
    ) -> tuple[str | None, list[str], object | None]:
        """Run the agent iteration loop. Returns (final_content, tools_used, last_response)."""
        messages = initial_messages
        iteration = 0
        final_content = None
        tools_used: list[str] = []
        last_response = None

        while iteration < self.max_iterations:
            iteration += 1

            response = await self._chat_with_fallback(
                messages=messages,
                tools=self.tools.get_definitions(),
                model=self.model,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )

            # Feed token usage into context tracker
            if response.usage and "total_tokens" in response.usage:
                self.context_tracker.add_tokens(self.model, response.usage["total_tokens"])

            last_response = response

            if response.has_tool_calls:
                if on_progress:
                    clean = self._strip_think(response.content)
                    if clean:
                        await on_progress(clean)
                    await on_progress(self._tool_hint(response.tool_calls))

                tool_call_dicts = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.name,
                            "arguments": json.dumps(tc.arguments, ensure_ascii=False),
                        },
                    }
                    for tc in response.tool_calls
                ]
                messages = self.context.add_assistant_message(
                    messages,
                    response.content,
                    tool_call_dicts,
                    reasoning_content=response.reasoning_content,
                )

                for tool_call in response.tool_calls:
                    tools_used.append(tool_call.name)
                    args_str = json.dumps(tool_call.arguments, ensure_ascii=False)
                    logger.info("Tool call: {}({})", tool_call.name, args_str[:200])
                    result = await self.tools.execute(tool_call.name, tool_call.arguments)
                    messages = self.context.add_tool_result(
                        messages, tool_call.id, tool_call.name, result
                    )
            else:
                final_content = self._strip_think(response.content)
                break

        return final_content, tools_used, last_response

    async def run(self) -> None:
        """Run the agent loop, processing messages from the bus."""
        self._running = True
        await self._connect_mcp()
        try:
            await self.context_tracker._load_initial_context()
            logger.info(
                "Context tracker initialized with {} models",
                len(self.context_tracker.context_usage),
            )
        except Exception as e:
            logger.warning("Context tracker initialization failed (non-fatal): {}", e)
        logger.info("Agent loop started")

        while self._running:
            try:
                msg = await asyncio.wait_for(self.bus.consume_inbound(), timeout=1.0)
                try:
                    response = await self._process_message(msg)
                    if response is not None:
                        await self.bus.publish_outbound(response)
                    elif msg.channel == "cli":
                        await self.bus.publish_outbound(
                            OutboundMessage(
                                channel=msg.channel,
                                chat_id=msg.chat_id,
                                content="",
                                metadata=msg.metadata or {},
                            )
                        )
                except Exception as e:
                    logger.error("Error processing message: {}", e)
                    await self.bus.publish_outbound(
                        OutboundMessage(
                            channel=msg.channel,
                            chat_id=msg.chat_id,
                            content=f"Sorry, I encountered an error: {e!s}",
                        )
                    )
            except TimeoutError:
                continue

    async def close_mcp(self) -> None:
        """Close MCP connections."""
        if self._mcp_stack:
            with contextlib.suppress(RuntimeError, BaseExceptionGroup):
                await self._mcp_stack.aclose()
            self._mcp_stack = None

    def stop(self) -> None:
        """Stop the agent loop."""
        self._running = False
        logger.info("Agent loop stopping")

    async def _process_message(
        self,
        msg: InboundMessage,
        session_key: str | None = None,
        on_progress: Callable[[str], Awaitable[None]] | None = None,
    ) -> OutboundMessage | None:
        """Process a single inbound message and return the response."""
        # System messages: parse origin from chat_id ("channel:chat_id")
        if msg.channel == "system":
            channel, chat_id = (
                msg.chat_id.split(":", 1) if ":" in msg.chat_id else ("cli", msg.chat_id)
            )
            logger.info("Processing system message from {}", msg.sender_id)
            key = f"{channel}:{chat_id}"
            session = self.sessions.get_or_create(key)
            self._set_tool_context(channel, chat_id, msg.metadata.get("message_id"))
            messages = self.context.build_messages(
                history=session.get_history(max_messages=self.memory_window),
                current_message=msg.content,
                channel=channel,
                chat_id=chat_id,
            )
            # Suppress MessageTool for system messages to prevent double messages
            # The main agent's text response is the only output we want
            saved_tools = self.tools
            self.tools = ToolRegistry()
            for tool_name in saved_tools.list_names():
                tool = saved_tools.get(tool_name)
                if not isinstance(tool, MessageTool):
                    self.tools.register(tool)
            try:
                final_content, _, _ = await self._run_agent_loop(messages)
            finally:
                self.tools = saved_tools
            session.add_message("user", f"[System: {msg.sender_id}] {msg.content}")
            session.add_message("assistant", final_content or "Background task completed.")
            self.sessions.save(session)
            return OutboundMessage(
                channel=channel,
                chat_id=chat_id,
                content=final_content or "Background task completed.",
            )

        preview = msg.content[:80] + "..." if len(msg.content) > 80 else msg.content
        logger.info("Processing message from {}:{}: {}", msg.channel, msg.sender_id, preview)

        key = session_key or msg.session_key
        session = self.sessions.get_or_create(key)

        # Slash commands
        cmd = msg.content.strip().lower()
        if cmd == "/new":
            # Wait for any in-flight consolidation tasks to complete BEFORE acquiring lock
            if self._consolidation_tasks:
                _done, _pending = await asyncio.wait(
                    self._consolidation_tasks, timeout=None, return_when=asyncio.ALL_COMPLETED
                )

            # Acquire the consolidation lock to prevent concurrent consolidation
            lock = self._get_consolidation_lock(session.key)
            async with lock:
                # Archive only unconsolidated messages (not all messages)
                session.messages[
                    session.last_consolidated : -session.keep_count
                ] if session.keep_count > 0 else session.messages[session.last_consolidated :]

                success = await self._consolidate_memory(session, archive_all=True)
                if not success:
                    logger.error("Memory consolidation failed during archive_all")

                if success:
                    # Clear session only after successful archival
                    session.clear()
                    self.sessions.save(session)
                    self.sessions.invalidate(session.key)

                    # Clean up the consolidation lock for invalidated session
                    if session.key in self._consolidation_locks:
                        del self._consolidation_locks[session.key]

                    return OutboundMessage(
                        channel=msg.channel,
                        chat_id=msg.chat_id,
                        content="New session started. Memory consolidation in progress.",
                    )
                else:
                    return OutboundMessage(
                        channel=msg.channel,
                        chat_id=msg.chat_id,
                        content="Failed to archive session memory. Session preserved.",
                    )
        if cmd == "/help":
            return OutboundMessage(
                channel=msg.channel,
                chat_id=msg.chat_id,
                content="🐈 nanobot commands:\n/new — Start a new conversation\n/help — Show available commands",
            )

        if len(session.messages) > self.memory_window and session.key not in self._consolidating:
            self._consolidating.add(session.key)

            async def _consolidate_and_unlock():
                lock = self._get_consolidation_lock(session.key)
                try:
                    async with lock:
                        await self._consolidate_memory(session)
                finally:
                    self._consolidating.discard(session.key)

            unlock_task = asyncio.create_task(_consolidate_and_unlock())
            self._consolidation_tasks.append(unlock_task)
            unlock_task.add_done_callback(
                lambda t: (
                    self._consolidation_tasks.remove(t) if t in self._consolidation_tasks else None
                )
            )

        self._set_tool_context(msg.channel, msg.chat_id, msg.metadata.get("message_id"))
        if (message_tool := self.tools.get("message")) and isinstance(message_tool, MessageTool):
            message_tool.start_turn()

        initial_messages = self.context.build_messages(
            history=session.get_history(max_messages=self.memory_window),
            current_message=msg.content,
            media=msg.media if msg.media else None,
            channel=msg.channel,
            chat_id=msg.chat_id,
        )

        async def _bus_progress(content: str) -> None:
            meta = dict(msg.metadata or {})
            meta["_progress"] = True
            await self.bus.publish_outbound(
                OutboundMessage(
                    channel=msg.channel,
                    chat_id=msg.chat_id,
                    content=content,
                    metadata=meta,
                )
            )

        final_content, tools_used, last_response = await self._run_agent_loop(
            initial_messages,
            on_progress=on_progress or _bus_progress,
        )

        if final_content is None:
            logger.warning(
                "Empty response from model: finish_reason={}, content={!r}, tool_calls={}",
                last_response.finish_reason if last_response else "N/A",
                last_response.content if last_response else "N/A",
                last_response.tool_calls if last_response else [],
            )
            # Retry once with a nudge prompt
            nudge_message = {
                "role": "user",
                "content": "Please provide a text response summarizing what you did or found.",
            }
            initial_messages.append(nudge_message)
            final_content, _, last_response = await self._run_agent_loop(
                initial_messages,
                on_progress=on_progress or _bus_progress,
            )

            if final_content is None:
                # Final fallback if retry also fails
                finish_reason = last_response.finish_reason if last_response else "N/A"
                raw_content = last_response.content if last_response else None
                snippet = raw_content[:200] if raw_content and len(raw_content) > 0 else "N/A"
                final_content = f"Model returned no response (finish_reason: {finish_reason}). Raw output: {snippet}"

        preview = final_content[:120] + "..." if len(final_content) > 120 else final_content
        logger.info("Response to {}:{}: {}", msg.channel, msg.sender_id, preview)

        session.add_message("user", msg.content)
        session.add_message(
            "assistant", final_content, tools_used=tools_used if tools_used else None
        )
        self.sessions.save(session)

        if (
            (message_tool := self.tools.get("message"))
            and isinstance(message_tool, MessageTool)
            and message_tool._sent_in_turn
        ):
            return None

        return OutboundMessage(
            channel=msg.channel,
            chat_id=msg.chat_id,
            content=final_content,
            metadata=msg.metadata or {},
        )

    def _get_consolidation_lock(self, session_key: str) -> asyncio.Lock:
        """Get or create a lock for a session to deduplicate consolidation tasks.

        Args:
            session_key: The session identifier

        Returns:
            An asyncio.Lock for the given session
        """
        if session_key not in self._consolidation_locks:
            self._consolidation_locks[session_key] = asyncio.Lock()
        return self._consolidation_locks[session_key]

    async def _consolidate_memory(self, session, archive_all: bool = False) -> bool:
        """Delegate to MemoryStore.consolidate().

        Args:
            session: The session to consolidate
            archive_all: If True, archive all messages (used by /new command)

        Returns:
            True if consolidation succeeded, False otherwise
        """
        result = await MemoryStore(self.workspace).consolidate(
            session,
            self.provider,
            self.model,
            archive_all=archive_all,
            memory_window=self.memory_window,
        )
        return result is not False

    async def process_direct(
        self,
        content: str,
        session_key: str = "cli:direct",
        channel: str = "cli",
        chat_id: str = "direct",
        on_progress: Callable[[str], Awaitable[None]] | None = None,
    ) -> str:
        """Process a message directly (for CLI or cron usage)."""
        await self._connect_mcp()
        if not self.context_tracker.context_usage:
            try:
                await self.context_tracker._load_initial_context()
                logger.info(
                    "Context tracker initialized with {} models",
                    len(self.context_tracker.context_usage),
                )
            except Exception as e:
                logger.warning("Context tracker initialization failed (non-fatal): {}", e)
        msg = InboundMessage(channel=channel, sender_id="user", chat_id=chat_id, content=content)
        response = await self._process_message(
            msg, session_key=session_key, on_progress=on_progress
        )
        return response.content if response else ""
