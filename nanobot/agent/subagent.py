"""Subagent manager for background task execution."""

import asyncio
import json
import uuid
from pathlib import Path
from typing import Any, TYPE_CHECKING

from loguru import logger

from nanobot.bus.events import InboundMessage
from nanobot.bus.queue import MessageBus
from nanobot.providers.base import LLMProvider
from nanobot.agent.tools.registry import ToolRegistry
from nanobot.providers.registry import list_models, find_by_class_name
from nanobot.agent.tools.filesystem import ReadFileTool, WriteFileTool, EditFileTool, ListDirTool
from nanobot.agent.tools.shell import ExecTool
from nanobot.agent.tools.web import WebSearchTool, WebFetchTool

if TYPE_CHECKING:
    from nanobot.config.schema import Config, ExecToolConfig


class SubagentManager:
    """
    Manages background subagent execution.
    
    Subagents are lightweight agent instances that run in the background
    to handle specific tasks. They can use a different provider/model than
    the main agent (e.g. a local LM Studio model for vision tasks).
    """
    
    def __init__(
        self,
        provider: LLMProvider,
        workspace: Path,
        bus: MessageBus,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        brave_api_key: str | None = None,
        exec_config: "ExecToolConfig | None" = None,
        restrict_to_workspace: bool = False,
        config: "Config | None" = None,
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

    async def _get_provider_for_model(self, model: str) -> LLMProvider:
        """
        Return the appropriate LLMProvider for a given model name.

        Checks the custom (local) provider first — if it's configured and the
        model is in its model list, use it.  Then falls back to keyword-based
        provider matching via config, and finally to the main agent's provider.
        """
        if self._config is None:
            logger.info("SubagentManager: No config available, using main provider for model '{}'", model)
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
                logger.info("SubagentManager: Model '{}' found in custom provider — using CustomProvider", model)
                return probe

        # --- 2. Keyword-based provider matching ------------------------------
        provider_name = self._config.get_provider_name(model)
        logger.info("SubagentManager: Keyword-matched provider_name='{}' for model='{}'", provider_name, model)

        if provider_name == "custom":
            # Shouldn't normally reach here given step 1, but handle it anyway
            from nanobot.providers.custom_provider import CustomProvider
            p = self._config.get_provider(model)
            api_key = p.api_key if p else "lm-studio"
            api_base = self._config.get_api_base(model) or "http://localhost:8000/v1"
            logger.info("SubagentManager: Creating CustomProvider(api_base='{}') for model='{}'", api_base, model)
            return CustomProvider(api_key=api_key, api_base=api_base, default_model=model)

        if provider_name and provider_name != self._config.get_provider_name(self.model):
            # Different provider than the main agent — build it from config
            from nanobot.providers.litellm_provider import LiteLLMProvider
            p = self._config.get_provider(model)
            if p and p.api_key:
                api_base = self._config.get_api_base(model)
                logger.info("SubagentManager: Creating LiteLLMProvider for model='{}' via provider='{}'", model, provider_name)
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
        logger.info("SubagentManager.spawn() called with task='{}', label='{}', model='{}'",
                    task[:50] + "..." if len(task) > 50 else task,
                    label or "None",
                    model or "None")

        # Validate model if specified
        if model:
            logger.info("SubagentManager: Validating model '{}' for subagent", model)

            # Resolve the correct provider for this model FIRST, then validate against it
            candidate_provider = await self._get_provider_for_model(model)
            provider_class_name = candidate_provider.__class__.__name__
            logger.info("SubagentManager: Resolved provider '{}' (api_base='{}') for model validation",
                        provider_class_name, candidate_provider.api_base)

            try:
                available_models = await list_models(
                    provider_name=provider_class_name,
                    api_key=candidate_provider.api_key,
                    api_base=candidate_provider.api_base,
                )
            except Exception as e:
                logger.error("SubagentManager: list_models() failed: {}", e)
                error_msg = f"Error: Failed to fetch available models from provider: {str(e)}"
                return error_msg

            # Handle None or empty list from list_models
            if available_models is None:
                available_models = []
                logger.warning("SubagentManager: list_models returned None, defaulting to empty list")

            logger.info("SubagentManager: Available models from '{}': {}", provider_class_name, available_models)

            if available_models and model not in available_models:
                error_msg = f"Error: Model '{model}' is not available from the provider. " \
                           f"Available models: {', '.join(available_models)}"
                logger.error("SubagentManager: Model validation failed: {}", error_msg)
                return error_msg

            logger.info("SubagentManager: Model '{}' validated successfully", model)
        else:
            logger.info("SubagentManager: No model specified, will use default model: '{}'", self.model)

        task_id = str(uuid.uuid4())[:8]
        display_label = label or task[:30] + ("..." if len(task) > 30 else "")

        logger.info("SubagentManager: Creating background task with task_id='{}'", task_id)
        origin = {
            "channel": origin_channel,
            "chat_id": origin_chat_id,
        }

        # Create background task
        bg_task = asyncio.create_task(
            self._run_subagent(task_id, task, display_label, origin, model, image_path)
        )
        self._running_tasks[task_id] = bg_task

        # Cleanup when done
        bg_task.add_done_callback(lambda _: self._running_tasks.pop(task_id, None))

        logger.info("SubagentManager: Spawned subagent [{}]: {}", task_id, display_label)
        result = f"Subagent [{display_label}] started (id: {task_id}). I'll notify you when it completes."
        logger.info("SubagentManager: Returning success message: {}", result[:100] + "..." if len(result) > 100 else result)
        return result
    
    async def _run_subagent(
        self,
        task_id: str,
        task: str,
        label: str,
        origin: dict[str, str],
        model: str | None = None,
        image_path: str | None = None,
    ) -> None:
        """Execute the subagent task and announce the result."""
        logger.info("SubagentManager._run_subagent() called for task_id='{}'", task_id)

        # Use provided model or fall back to manager's default
        subagent_model = model or self.model

        logger.info("Subagent [{}] MODEL SELECTION:", task_id)
        logger.info("  - Received model param: '{}'", model or "None")
        logger.info("  - Manager default model: '{}'", self.model)
        logger.info("  - Final model to use: '{}'", subagent_model)

        logger.info("Subagent [{}] starting task with model: {}", task_id, subagent_model)

        # Resolve the correct provider for this model
        subagent_provider = await self._get_provider_for_model(subagent_model)
        logger.info("Subagent [{}] using provider: {}", task_id, subagent_provider.__class__.__name__)
        
        try:
            # Build subagent tools (no message tool, no spawn tool)
            tools = ToolRegistry()
            allowed_dir = self.workspace if self.restrict_to_workspace else None
            tools.register(ReadFileTool(workspace=self.workspace, allowed_dir=allowed_dir))
            tools.register(WriteFileTool(workspace=self.workspace, allowed_dir=allowed_dir))
            tools.register(EditFileTool(workspace=self.workspace, allowed_dir=allowed_dir))
            tools.register(ListDirTool(workspace=self.workspace, allowed_dir=allowed_dir))
            tools.register(ExecTool(
                working_dir=str(self.workspace),
                timeout=self.exec_config.timeout,
                restrict_to_workspace=self.restrict_to_workspace,
            ))
            tools.register(WebSearchTool(api_key=self.brave_api_key))
            tools.register(WebFetchTool())
            
            # Build messages with subagent-specific prompt
            system_prompt = self._build_subagent_prompt(task)

            # Build the user message — embed image as base64 if provided
            if image_path:
                import base64, mimetypes
                mime_type = mimetypes.guess_type(image_path)[0] or "image/png"
                with open(image_path, "rb") as f:
                    image_b64 = base64.b64encode(f.read()).decode()
                user_content: Any = [
                    {"type": "text", "text": task},
                    {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{image_b64}"}},
                ]
                logger.info("Subagent [{}] embedding image '{}' ({}) as base64 in user message", task_id, image_path, mime_type)
            else:
                user_content = task

            messages: list[dict[str, Any]] = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ]
            
            # Run agent loop (limited iterations)
            max_iterations = 15
            iteration = 0
            final_result: str | None = None
            
            while iteration < max_iterations:
                iteration += 1
                
                response = await subagent_provider.chat(
                    messages=messages,
                    tools=tools.get_definitions(),
                    model=subagent_model,
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                )
                
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
                    messages.append({
                        "role": "assistant",
                        "content": response.content or "",
                        "tool_calls": tool_call_dicts,
                    })
                    
                    # Execute tools
                    for tool_call in response.tool_calls:
                        args_str = json.dumps(tool_call.arguments, ensure_ascii=False)
                        logger.debug("Subagent [{}] executing: {} with arguments: {}", task_id, tool_call.name, args_str)
                        result = await tools.execute(tool_call.name, tool_call.arguments)
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "name": tool_call.name,
                            "content": result,
                        })
                else:
                    final_result = response.content
                    break
            
            if final_result is None:
                final_result = "Task completed but no final response was generated."
            
            logger.info("Subagent [{}] completed successfully", task_id)
            await self._announce_result(task_id, label, task, final_result, origin, "ok")
            
        except Exception as e:
            error_msg = f"Error: {str(e)}"
            logger.error("Subagent [{}] failed: {}", task_id, e)
            await self._announce_result(task_id, label, task, error_msg, origin, "error")
    
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
        status_text = "completed successfully" if status == "ok" else "failed"
        
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
        logger.debug("Subagent [{}] announced result to {}:{}", task_id, origin['channel'], origin['chat_id'])
    
    def _build_subagent_prompt(self, task: str) -> str:
        """Build a focused system prompt for the subagent."""
        from datetime import datetime
        import time as _time
        now = datetime.now().strftime("%Y-%m-%d %H:%M (%A)")
        tz = _time.strftime("%Z") or "UTC"

        return f"""# Subagent

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
    
    def get_running_count(self) -> int:
        """Return the number of currently running subagents."""
        return len(self._running_tasks)
