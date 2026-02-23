"""Subagent manager for background task execution."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
import json
from pathlib import Path
from typing import TYPE_CHECKING, Any
import uuid

from loguru import logger

from nanobot.agent.registry import CapacityError, SubagentRegistry
from nanobot.agent.tools.filesystem import EditFileTool, ListDirTool, ReadFileTool, WriteFileTool
from nanobot.agent.tools.registry import ToolRegistry
from nanobot.agent.tools.shell import ExecTool
from nanobot.agent.tools.web import WebFetchTool, WebSearchTool
from nanobot.bus.events import InboundMessage
from nanobot.providers.registry import list_models

if TYPE_CHECKING:
    from nanobot.bus.queue import MessageBus
    from nanobot.config.schema import Config, ExecToolConfig
    from nanobot.providers.base import LLMProvider

SUBAGENT_TEMPLATES: dict[str, str] = {
    "code-fixer": """You are a code-fixer subagent. Your task is to debug and fix code issues.

Follow these guidelines:
- Analyze the code carefully to identify the root cause of the issue
- Fix the specific issue without introducing new bugs
- Run tests to verify the fix works correctly
- Follow ruff code style: use double quotes, include type annotations, and remove unused imports
- Make minimal changes to achieve the goal""",
    "code-builder": """You are a code-builder subagent. Your task is to build new features or files from scratch.

Follow these guidelines:
- Write clean, maintainable code that follows the existing conventions in the codebase
- Use type annotations throughout
- Follow ruff code style: use double quotes, include type annotations, and remove unused imports
- Break down complex tasks into smaller, manageable components
- Test your implementation to ensure it works as expected""",
    "planner": """You are a planner subagent. Your task is to research and produce detailed plans.

Follow these guidelines:
- Research the topic thoroughly before producing a plan
- Cite sources explicitly when using external information
- Produce milestone lists with measurable criteria for each milestone
- Consider dependencies and resource requirements
- Provide clear success criteria for each planned item""",
    "researcher": """You are a researcher subagent. Your task is to gather accurate information.

Follow these guidelines:
- Fetch real URLs to verify facts, not guess or hallucinate
- Cite sources explicitly for all claims
- Be thorough and check multiple sources when needed
- Report findings clearly with source references
- If information is not available, state that clearly rather than guessing""",
}


class SubagentManager:
    """
    Manages background subagent execution.

    Subagents are lightweight agent instances that run in the background
    to handle specific tasks. They can use a different provider/model than
    the main agent (e.g. a local LM Studio model for vision tasks).
    """

    PENDING_TIMEOUT_SECS = 300
    EXECUTION_TIMEOUT_SECS = 1200
    MAX_RETRY_COUNT = 3

    def __init__(
        self,
        provider: LLMProvider,
        workspace: Path,
        bus: MessageBus,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        brave_api_key: str | None = None,
        exec_config: ExecToolConfig | None = None,
        restrict_to_workspace: bool = False,
        config: Config | None = None,
        db_path: Path | None = None,
    ):
        from nanobot.config.schema import ExecToolConfig

        self.provider = provider
        self.workspace = workspace
        self.bus = bus
        self.model = model or provider.get_default_model()
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.brave_api_key = brave_api_key
        self.exec_config = exec_config or ExecToolConfig()
        self.restrict_to_workspace = restrict_to_workspace
        self._config = config  # Full config for resolving per-model providers
        self._running_tasks: dict[str, asyncio.Task[None]] = {}
        self._dispatch_task: asyncio.Task[None] | None = None
        db_path = db_path or Path.home() / ".nanobot" / "workspace" / "subagents.db"
        self.registry = SubagentRegistry(db_path)
        self.registry.open()
        self.registry.recover_on_startup()

    async def _get_provider_for_model(self, model: str) -> LLMProvider:
        """
        Return the appropriate LLMProvider for a given model name.

        Checks the custom (local) provider first — if it's configured and the
        model is in its model list, use it.  Then falls back to keyword-based
        provider matching via config, and finally to the main agent's provider.
        """
        if self._config is None:
            logger.info(
                "SubagentManager: No config available, using main provider for model '{}'",
                model,
            )
            return self.provider

        # --- 1. Check custom (local) provider first --------------------------
        # The custom provider has no keywords, so keyword matching never picks
        # it.  We probe it directly: if it's configured and lists this model,
        # it wins unconditionally.
        custom_cfg = getattr(self._config.providers, "custom", None)
        if custom_cfg and custom_cfg.api_base:
            from nanobot.providers.custom_provider import CustomProvider

            probe = CustomProvider(
                api_key=custom_cfg.api_key or "lm-studio",
                api_base=custom_cfg.api_base,
                default_model=model,
            )
            try:
                models_data = await probe.get_models()
                local_models = [m["id"] for m in models_data if m.get("id")]
            except Exception as e:
                local_models = []
                logger.warning("SubagentManager: Could not probe custom provider: {}", e)

            logger.info("SubagentManager: Custom provider local models: {}", local_models)
            if model in local_models:
                logger.info(
                    "SubagentManager: Model '{}' found in custom provider — using CustomProvider",
                    model,
                )
                return probe

        # --- 2. Keyword-based provider matching ------------------------------
        provider_name = self._config.get_provider_name(model)
        logger.info(
            "SubagentManager: Keyword-matched provider_name='{}' for model='{}'",
            provider_name,
            model,
        )

        if provider_name == "custom":
            # Shouldn't normally reach here given step 1, but handle it anyway
            from nanobot.providers.custom_provider import CustomProvider

            p = self._config.get_provider(model)
            api_key = p.api_key if p else "lm-studio"
            api_base = self._config.get_api_base(model) or "http://localhost:8000/v1"
            logger.info(
                "SubagentManager: Creating CustomProvider(api_base='{}') for model='{}'",
                api_base,
                model,
            )
            return CustomProvider(api_key=api_key, api_base=api_base, default_model=model)

        elif provider_name == "bedrock":
            from nanobot.providers.bedrock_provider import BedrockProvider

            region = getattr(
                getattr(self._config.providers, "bedrock", None), "region", "us-east-1"
            )
            default_model = model
            logger.info(
                "SubagentManager: Creating BedrockProvider(region='{}') for model='{}'",
                region,
                model,
            )
            return BedrockProvider(region_name=region, default_model=default_model)

        if provider_name and provider_name != self._config.get_provider_name(self.model):
            # Different provider than the main agent — build it from config
            from nanobot.providers.litellm_provider import LiteLLMProvider

            p = self._config.get_provider(model)
            if p and p.api_key:
                api_base = self._config.get_api_base(model)
                logger.info(
                    "SubagentManager: Creating LiteLLMProvider for model='{}' via provider='{}'",
                    model,
                    provider_name,
                )
                return LiteLLMProvider(
                    api_key=p.api_key,
                    api_base=api_base,
                    default_model=model,
                    extra_headers=p.extra_headers,
                    provider_name=provider_name,
                )

        logger.info("SubagentManager: Using main provider for model='{}'", model)
        return self.provider

    async def spawn(
        self,
        task: str,
        label: str | None = None,
        origin_channel: str = "cli",
        origin_chat_id: str = "direct",
        model: str | None = None,
        image_path: str | None = None,
        template: str | None = None,
    ) -> str:
        """
        Spawn a subagent to execute a task in the background.

        Args:
            task: The task description for the subagent.
            label: Optional human-readable label for the task.
            origin_channel: The channel to announce results to.
            origin_chat_id: The chat ID to announce results to.
            model: Optional model to use for this subagent. If not specified,
                   uses the model configured in __init__.

        Returns:
            Status message indicating the subagent was started.
        """
        logger.info(
            "SubagentManager.spawn() called with task='{}', label='{}', model='{}'",
            task[:50] + "..." if len(task) > 50 else task,
            label or "None",
            model or "None",
        )

        # Validate model if specified
        if model:
            logger.info("SubagentManager: Validating model '{}' for subagent", model)

            # Resolve the correct provider for this model FIRST, then validate against it
            candidate_provider = await self._get_provider_for_model(model)
            provider_class_name = candidate_provider.__class__.__name__
            logger.info(
                "SubagentManager: Resolved provider '{}' (api_base='{}') for model validation",
                provider_class_name,
                candidate_provider.api_base,
            )

            # BedrockProvider uses IAM auth — skip list_models validation
            if provider_class_name == "BedrockProvider":
                available_models = None  # skip validation
            else:
                try:
                    available_models = await list_models(
                        provider_name=provider_class_name,
                        api_key=candidate_provider.api_key,
                        api_base=candidate_provider.api_base,
                    )
                except Exception as e:
                    logger.error("SubagentManager: list_models() failed: {}", e)
                    error_msg = f"Error: Failed to fetch available models from provider: {e!s}"
                    return error_msg

                # Handle None or empty list from list_models
                if available_models is None:
                    available_models = []
                    logger.warning(
                        "SubagentManager: list_models returned None, defaulting to empty list"
                    )

            logger.info(
                "SubagentManager: Available models from '{}': {}",
                provider_class_name,
                available_models,
            )

            if available_models and model not in available_models:
                error_msg = (
                    f"Error: Model '{model}' is not available from the provider. "
                    f"Available models: {', '.join(available_models)}"
                )
                logger.error("SubagentManager: Model validation failed: {}", error_msg)
                return error_msg

            logger.info("SubagentManager: Model '{}' validated successfully", model)
        else:
            logger.info(
                "SubagentManager: No model specified, will use default model: '{}'", self.model
            )

        task_id = str(uuid.uuid4())[:8]
        display_label = label or task[:30] + ("..." if len(task) > 30 else "")

        # Register the task in the registry (atomic capacity check + insert)
        try:
            self.registry.tag_in_atomic(task_id, display_label, "user")
        except CapacityError as e:
            return str(e)

        logger.info("SubagentManager: Creating background task with task_id='{}'", task_id)
        origin = {
            "channel": origin_channel,
            "chat_id": origin_chat_id,
        }

        # Create background task
        bg_task = asyncio.create_task(
            self._run_subagent(task_id, task, display_label, origin, model, image_path, template)
        )
        self._running_tasks[task_id] = bg_task

        # Cleanup when done
        bg_task.add_done_callback(lambda _: self._running_tasks.pop(task_id, None))

        logger.info("SubagentManager: Spawned subagent [{}]: {}", task_id, display_label)
        result = f"Subagent [{display_label}] started (id: {task_id}). I'll notify you when it completes."
        logger.info(
            "SubagentManager: Returning success message: {}",
            result[:100] + "..." if len(result) > 100 else result,
        )
        return result

    async def _run_subagent(
        self,
        task_id: str,
        task: str,
        label: str,
        origin: dict[str, str],
        model: str | None = None,
        image_path: str | None = None,
        template: str | None = None,
    ) -> None:
        """Execute the subagent task and announce the result."""
        logger.info("SubagentManager._run_subagent() called for task_id='{}'", task_id)

        final_status = "failed"

        # Use provided model or fall back to manager's default
        subagent_model = model or self.model

        logger.info("Subagent [{}] MODEL SELECTION:", task_id)
        logger.info("  - Received model param: '{}'", model or "None")
        logger.info("  - Manager default model: '{}'", self.model)
        logger.info("  - Final model to use: '{}'", subagent_model)

        logger.info("Subagent [{}] starting task with model: {}", task_id, subagent_model)

        # Resolve the correct provider for this model
        subagent_provider = await self._get_provider_for_model(subagent_model)
        logger.info(
            "Subagent [{}] using provider: {}", task_id, subagent_provider.__class__.__name__
        )

        try:
            # Build subagent tools (no message tool, no spawn tool)
            tools = ToolRegistry()
            allowed_dir = self.workspace if self.restrict_to_workspace else None
            tools.register(ReadFileTool(workspace=self.workspace, allowed_dir=allowed_dir))
            tools.register(WriteFileTool(workspace=self.workspace, allowed_dir=allowed_dir))
            tools.register(EditFileTool(workspace=self.workspace, allowed_dir=allowed_dir))
            tools.register(ListDirTool(workspace=self.workspace, allowed_dir=allowed_dir))
            tools.register(
                ExecTool(
                    working_dir=str(self.workspace),
                    timeout=self.exec_config.timeout,
                    restrict_to_workspace=self.restrict_to_workspace,
                )
            )
            tools.register(WebSearchTool(api_key=self.brave_api_key))
            tools.register(WebFetchTool())

            # Build messages with subagent-specific prompt
            system_prompt = self._build_subagent_prompt(task, template=template)

            # Build the user message — embed image as base64 if provided
            if image_path:
                import base64
                import mimetypes

                mime_type = mimetypes.guess_type(image_path)[0] or "image/png"
                with open(image_path, "rb") as f:
                    image_b64 = base64.b64encode(f.read()).decode()
                user_content: Any = [
                    {"type": "text", "text": task},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:{mime_type};base64,{image_b64}"},
                    },
                ]
                logger.info(
                    "Subagent [{}] embedding image '{}' ({}) as base64 in user message",
                    task_id,
                    image_path,
                    mime_type,
                )
            else:
                user_content = task

            messages: list[dict[str, Any]] = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ]

            # Run agent loop (limited iterations)
            max_iterations = 30
            iteration = 0
            final_result: str | None = None
            first_response_processed = False

            while iteration < max_iterations:
                iteration += 1

                response = await subagent_provider.chat(
                    messages=messages,
                    tools=tools.get_definitions(),
                    model=subagent_model,
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                )

                # Call set_running after first successful response
                if iteration == 1 and not first_response_processed:
                    self.registry.set_running(task_id)
                    first_response_processed = True

                if response.has_tool_calls:
                    # Add assistant message with tool calls
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
                    messages.append(
                        {
                            "role": "assistant",
                            "content": response.content or "",
                            "tool_calls": tool_call_dicts,
                        }
                    )

                    # Execute tools
                    for tool_call in response.tool_calls:
                        args_str = json.dumps(tool_call.arguments, ensure_ascii=False)
                        logger.debug(
                            "Subagent [{}] executing: {} with arguments: {}",
                            task_id,
                            tool_call.name,
                            args_str,
                        )
                        result = await tools.execute(tool_call.name, tool_call.arguments)
                        messages.append(
                            {
                                "role": "tool",
                                "tool_call_id": tool_call.id,
                                "name": tool_call.name,
                                "content": result,
                            }
                        )
                else:
                    final_result = response.content
                    break

            if final_result is None:
                # Loop exhausted max_iterations without producing a text response
                last_content = response.content if "response" in dir() else None
                logger.warning(
                    "Subagent [{}] exhausted {} iterations without producing a text response. "
                    "Last model output: {}",
                    task_id,
                    max_iterations,
                    repr(last_content)[:200] if last_content else "(none)",
                )
                final_result = (
                    f"[INCOMPLETE] Subagent exhausted {max_iterations} iterations without producing "
                    f"a final response. Last model output: "
                    f"{repr(last_content)[:300] if last_content else '(none)'}\n\n"
                    f"The task may be incomplete. Please review and retry if needed."
                )

            logger.info("Subagent [{}] completed with result: {}", task_id, final_result[:100])
            await self._announce_result(task_id, label, task, final_result, origin, "ok")
            final_status = "completed"

        except Exception as e:
            error_msg = f"Error: {e!s}"
            logger.error("Subagent [{}] failed: {}", task_id, e)
            await self._announce_result(task_id, label, task, error_msg, origin, "error")

        finally:
            self.registry.tag_out(task_id, final_status)

    async def _announce_result(
        self,
        task_id: str,
        label: str,
        task: str,
        result: str,
        origin: dict[str, str],
        status: str,
    ) -> None:
        """Announce the subagent result to the main agent via the message bus."""
        is_incomplete = result.startswith("[INCOMPLETE]")
        status_text = (
            "failed"
            if status != "ok"
            else ("completed (incomplete)" if is_incomplete else "completed successfully")
        )

        announce_content = f"""[Subagent '{label}' {status_text}]

Task: {task}

Result:
{result}

Summarize this naturally for the user. Keep it brief (1-2 sentences). Do not mention technical details like "subagent" or task IDs."""

        # Inject as system message to trigger main agent
        msg = InboundMessage(
            channel="system",
            sender_id="subagent",
            chat_id=f"{origin['channel']}:{origin['chat_id']}",
            content=announce_content,
        )

        await self.bus.publish_inbound(msg)
        logger.debug(
            "Subagent [{}] announced result to {}:{}", task_id, origin["channel"], origin["chat_id"]
        )

        # Trigger dispatch after subagent completion (non-blocking)
        self._trigger_dispatch()

    def _trigger_dispatch(self) -> None:
        """Fire-and-forget: trigger dispatch via dispatch_runner.dispatch_next()."""
        logger.debug("Dispatch triggered via _trigger_dispatch()")

    async def _rollback_milestone_marker(self, milestone_num: str) -> None:
        """Rollback [~] marker back to [ ] in BACKLOG.md if spawn failed.

        Args:
            milestone_num: The milestone number to rollback (e.g., '30.5')
        """
        backlog_path = Path.home() / ".nanobot" / "workspace" / "memory" / "BACKLOG.md"

        if not backlog_path.exists():
            logger.warning(
                "BACKLOG.md not found at {}, cannot rollback milestone {}",
                backlog_path,
                milestone_num,
            )
            return

        try:
            content = backlog_path.read_text()
        except OSError as e:
            logger.error("Failed to read BACKLOG.md: {}", e)
            return

        # Find and replace the first occurrence of [~] for this milestone
        import re

        pattern = rf"- \[~\] ({re.escape(milestone_num)} )"
        replacement = f"- [ ] {milestone_num} "

        new_content = re.sub(pattern, replacement, content, count=1)

        if new_content == content:
            logger.warning(
                "No [~] marker found for milestone {} in BACKLOG.md, nothing to rollback",
                milestone_num,
            )
            return

        try:
            backlog_path.write_text(new_content)
            logger.info(
                "Rollback milestone {} from [~] to [ ] in BACKLOG.md",
                milestone_num,
            )
        except OSError as e:
            logger.error("Failed to write BACKLOG.md: {}", e)

    def _build_subagent_prompt(self, task: str, template: str | None = None) -> str:
        """Build a focused system prompt for the subagent."""
        from datetime import datetime
        import time as _time

        now = datetime.now().strftime("%Y-%m-%d %H:%M (%A)")
        tz = _time.strftime("%Z") or "UTC"

        system_prompt = f"""# Subagent

## Current Time
{now} ({tz})

You are a subagent spawned by the main agent to complete a specific task.

## Rules
1. Stay focused - complete only the assigned task, nothing else
2. Your final response will be reported back to the main agent
3. Do not initiate conversations or take on side tasks
4. Be concise but informative in your findings

## What You Can Do
- Read and write files in the workspace
- Execute shell commands
- Search the web and fetch web pages
- Complete the task thoroughly

## What You Cannot Do
- Send messages directly to users (no message tool available)
- Spawn other subagents
- Access the main agent's conversation history

## Workspace
Your workspace is at: {self.workspace}
Skills are available at: {self.workspace}/skills/ (read SKILL.md files as needed)

When you have completed the task, provide a clear summary of your findings or actions."""

        if template is not None:
            template_content = SUBAGENT_TEMPLATES.get(template)
            if template_content is not None:
                system_prompt = f"""{template_content}

{system_prompt}"""
            else:
                logger.warning(
                    "SubagentManager: Template '{}' not found in SUBAGENT_TEMPLATES",
                    template,
                )

        return system_prompt

    def get_running_count(self) -> int:
        """Return the number of currently running subagents."""
        return len(self._running_tasks)

    async def check_timeouts(self) -> None:
        """
        Check for timed-out tasks and handle them appropriately.

        For pending tasks (never got a first LLM response):
        - If age > 300 seconds (5 min), cancel and handle based on retry count
        For running tasks (got a response but still running):
        - If age > 1200 seconds (20 min), cancel and mark as lost with stack frame
        """
        now = datetime.now(UTC)

        for task_row in self.registry.get_all_active():
            task_id = task_row["id"]
            status = task_row["status"]
            origin = task_row["origin"]
            retry_count = task_row["retry_count"] or 0

            spawned_at_str = task_row["spawned_at"]

            try:
                spawned_at = datetime.fromisoformat(spawned_at_str.replace("Z", "+00:00"))
            except (ValueError, TypeError) as e:
                logger.warning(
                    "Subagent [{}] invalid spawned_at '{}': {}", task_id, spawned_at_str, e
                )
                continue

            age_seconds = (now - spawned_at).total_seconds()

            if status == "pending" and age_seconds > self.PENDING_TIMEOUT_SECS:
                await self._handle_pending_timeout(task_id, origin, retry_count)

            elif status == "running" and age_seconds > self.EXECUTION_TIMEOUT_SECS:
                await self._handle_execution_timeout(task_id)

    async def _handle_pending_timeout(self, task_id: str, origin: str, retry_count: int) -> None:
        """Handle a pending task that has timed out."""
        task = self._running_tasks.get(task_id)

        if task is not None and not task.done():
            task.cancel()
            logger.warning("Subagent [{}] cancelled due to pending timeout", task_id)
        else:
            logger.warning(
                "Subagent [{}] task not found in _running_tasks or already done", task_id
            )

        if retry_count < self.MAX_RETRY_COUNT and origin == "cron":
            self.registry.mark_requeue(task_id)
            logger.info("Subagent [{}] requeued (retry_count={})", task_id, retry_count)
        else:
            self.registry.mark_lost(task_id)
            self._log_discord_alert(
                task_id=task_id,
                label=task_id,
                message="Task timed out as pending (max retries or user origin)",
            )
            logger.error("Subagent [{}] lost (max retries or user origin)", task_id)

    async def _handle_execution_timeout(self, task_id: str) -> None:
        """Handle a running task that has exceeded execution timeout."""
        task = self._running_tasks.get(task_id)

        stack_frame = ""
        if task is not None and not task.done():
            try:
                stack = task.get_stack()
                if stack:
                    frame = stack[-1]
                    frame_str = (
                        f"{frame.f_code.co_filename}:{frame.f_lineno} in {frame.f_code.co_name}"
                    )
                    stack_frame = frame_str
            except Exception as e:
                logger.warning("Subagent [{}] could not get stack frame: {}", task_id, e)

            task.cancel()
            logger.warning("Subagent [{}] cancelled due to execution timeout", task_id)

        self.registry.mark_lost(task_id, stack_frame=stack_frame)
        self._log_discord_alert(
            task_id=task_id,
            label=task_id,
            message="Task timed out during execution",
            stack_frame=stack_frame,
        )
        logger.error("Subagent [{}] lost (execution timeout)", task_id)

    def _log_discord_alert(
        self, task_id: str, label: str, message: str, stack_frame: str = ""
    ) -> None:
        """
        Log Discord alert at ERROR level.

        Note: Full Discord integration will be wired in milestone 10.7.
        For now, logs the alert details for manual handling.
        """
        alert_msg = f"[Discord Alert] Subagent '{label}' ({task_id}): {message}"
        if stack_frame:
            alert_msg += f" | Stack: {stack_frame}"

        logger.error(alert_msg)
