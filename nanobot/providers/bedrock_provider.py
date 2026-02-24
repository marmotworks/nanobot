"""AWS Bedrock provider using the Converse API."""

from __future__ import annotations

import asyncio
import json
from typing import TYPE_CHECKING, Any

# third-party
import boto3
from botocore.config import Config as BotocoreConfig
import botocore.exceptions
from loguru import logger

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

# first-party
from nanobot.providers.base import LLMProvider, LLMResponse, ToolCallRequest


class BedrockProvider(LLMProvider):
    """AWS Bedrock provider using the Converse API."""

    def __init__(
        self,
        region_name: str = "us-east-1",
        default_model: str = "us.anthropic.claude-sonnet-4-6",
        fallback_models: list[str] | None = None,
    ):
        self.region_name = region_name
        self.default_model = default_model
        self._client = boto3.client(
            "bedrock-runtime",
            region_name=region_name,
            config=BotocoreConfig(read_timeout=300, connect_timeout=30),
        )
        # Tier-3 fallback chain: models to try if primary fails
        self.fallback_models: list[str] = fallback_models or []

    def get_default_model(self) -> str:
        """Get the default model for this provider."""
        return self.default_model

    def _convert_messages(
        self,
        messages: list[dict[str, Any]],
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """Convert OpenAI-style messages to Bedrock format.

        Returns:
            Tuple of (bedrock_messages, system_prompts)
        """
        bedrock_messages: list[dict[str, Any]] = []
        system_prompts: list[dict[str, Any]] = []

        i = 0
        while i < len(messages):
            msg = messages[i]
            role = msg.get("role", "")

            if role == "system":
                system_prompts.append({"text": msg.get("content", "")})
                i += 1
            elif role == "tool":
                # Collect all consecutive tool messages
                tool_results = []
                while i < len(messages) and messages[i].get("role") == "tool":
                    m = messages[i]
                    tool_results.append({
                        "toolResult": {
                            "toolUseId": m.get("tool_call_id", ""),
                            "content": [{"text": str(m.get("content", ""))}],
                        },
                    })
                    i += 1
                bedrock_messages.append({"role": "user", "content": tool_results})
                continue
            elif role == "assistant" and "tool_calls" in msg:
                tool_uses = []
                for tc in msg.get("tool_calls", []):
                    args = tc.get("function", {}).get("arguments", {})
                    # Ensure input is always a dict (Bedrock requires json object, not string)
                    input_obj = json.loads(args) if isinstance(args, str) else args
                    tool_uses.append({
                        "toolUse": {
                            "toolUseId": tc.get("id", ""),
                            "name": tc.get("function", {}).get("name", ""),
                            "input": input_obj,
                        },
                    })
                bedrock_messages.append({
                    "role": "assistant",
                    "content": tool_uses,
                })
                i += 1
            else:
                content = msg.get("content", "")
                bedrock_messages.append({
                    "role": role,
                    "content": [{"text": content}],
                })
                i += 1

        return self._sanitize_bedrock_messages(bedrock_messages), system_prompts

    def _sanitize_bedrock_messages(
        self,
        bedrock_messages: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Sanitize Bedrock messages to remove unpaired toolUse/toolResult pairs.

        Bedrock requires that every assistant message containing toolUse blocks
        must be immediately followed by a user message containing toolResult blocks
        covering ALL tool use IDs. This method removes unpaired toolUse messages
        and any orphaned toolResult messages.

        Args:
            bedrock_messages: List of converted Bedrock message dicts.

        Returns:
            Sanitized list of Bedrock messages.
        """
        if not bedrock_messages:
            return bedrock_messages

        # Pass 1: Identify assistant+toolUse messages that need removal
        assistant_to_remove: set[int] = set()
        orphaned_tool_result_ids: set[str] = set()

        for idx, msg in enumerate(bedrock_messages):
            if msg.get("role") != "assistant":
                continue

            content = msg.get("content", [])
            tool_use_ids: set[str] = set()
            for block in content:
                if "toolUse" in block:
                    tool_use_ids.add(block["toolUse"].get("toolUseId", ""))

            if not tool_use_ids:
                continue

            # Collect ALL tool result IDs from consecutive user+toolResult messages immediately following
            covered_ids: set[str] = set()
            scan_idx = idx + 1
            while scan_idx < len(bedrock_messages):
                next_msg = bedrock_messages[scan_idx]
                if next_msg.get("role") != "user":
                    break
                next_content = next_msg.get("content", [])
                has_tool_result = any("toolResult" in block for block in next_content)
                if not has_tool_result:
                    break
                for block in next_content:
                    if "toolResult" in block:
                        covered_ids.add(block["toolResult"].get("toolUseId", ""))
                scan_idx += 1

            # If no following messages at all, keep (valid — waiting for results)
            if scan_idx == idx + 1 and scan_idx >= len(bedrock_messages):
                continue

            # If all IDs are covered, valid pair
            if covered_ids >= tool_use_ids:
                continue

            # Otherwise, mark for removal
            assistant_to_remove.add(idx)
            orphaned_tool_result_ids.update(tool_use_ids)

        # Pass 2: Build sanitized list, skipping removed assistant messages and orphaned toolResult messages
        sanitized: list[dict[str, Any]] = []
        for idx, msg in enumerate(bedrock_messages):
            # Skip assistant messages marked for removal
            if idx in assistant_to_remove:
                content = msg.get("content", [])
                tool_use_ids: set[str] = set()
                for block in content:
                    if "toolUse" in block:
                        tool_use_ids.add(block["toolUse"].get("toolUseId", ""))
                if tool_use_ids:
                    logger.warning("Bedrock: removing unpaired toolUse message with IDs: {}", tool_use_ids)
                continue

            # Skip user+toolResult messages whose toolUseId references a removed assistant message
            if msg.get("role") == "user":
                content = msg.get("content", [])
                filtered_content = []
                for block in content:
                    if "toolResult" in block:
                        tool_id = block["toolResult"].get("toolUseId", "")
                        # Only keep this toolResult if it corresponds to a non-removed assistant message
                        tool_result_kept = tool_id not in orphaned_tool_result_ids
                        if tool_result_kept:
                            filtered_content.append(block)
                    else:
                        filtered_content.append(block)
                msg = {**msg, "content": filtered_content}
                # Skip the entire user message if it has no content left
                if not msg["content"]:
                    continue

            sanitized.append(msg)

        return sanitized

    def _convert_tools(
        self,
        tools: list[dict[str, Any]] | None,
    ) -> list[dict[str, Any]] | None:
        """Convert OpenAI-style tools to Bedrock format."""
        if not tools:
            return None

        bedrock_tools: list[dict[str, Any]] = []
        for tool in tools:
            if tool.get("type") == "function":
                func = tool.get("function", {})
                bedrock_tools.append({
                    "toolSpec": {
                        "name": func.get("name", ""),
                        "description": func.get("description", ""),
                        "inputSchema": {"json": func.get("parameters", {})},
                    },
                })

        return bedrock_tools if bedrock_tools else None

    def _parse_response(self, response: dict[str, Any]) -> LLMResponse:
        """Parse Bedrock Converse API response."""
        output = response.get("output", {}).get("message", {})
        content_blocks = output.get("content", [])

        text_parts: list[str] = []
        tool_calls: list[ToolCallRequest] = []

        for block in content_blocks:
            if "text" in block:
                text_parts.append(block["text"])
            elif "reasoningContent" in block:
                # Log reasoning content for debugging — NEVER expose to users
                reasoning = block["reasoningContent"]
                thinking = reasoning.get("reasoningText", {})
                if isinstance(thinking, dict) and thinking.get("text"):
                    logger.debug(f"Bedrock reasoning content (not exposed to user): {thinking['text'][:200]}...")
                # Do NOT use reasoning as fallback — it's internal model thinking
                continue  # skip to next block
            elif "toolUse" in block:
                tool_use = block["toolUse"]
                tool_calls.append(ToolCallRequest(
                    id=tool_use.get("toolUseId", ""),
                    name=tool_use.get("name", ""),
                    arguments=tool_use.get("input", {}),
                ))

        text = "\n".join(text_parts) if text_parts else None

        usage = response.get("usage", {})
        usage_dict = {
            "prompt_tokens": usage.get("inputTokens", 0),
            "completion_tokens": usage.get("outputTokens", 0),
            "total_tokens": usage.get("totalTokens", 0),
        }

        stop_reason = response.get("stopReason", "end_turn")

        return LLMResponse(
            content=text,
            tool_calls=tool_calls,
            finish_reason=stop_reason,
            usage=usage_dict,
        )

    async def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        model: str | None = None,
        max_tokens: int = 8192,
        temperature: float = 0.7,
        stream: bool = False,
        additional_fields: dict[str, Any] | None = None,
    ) -> LLMResponse | AsyncGenerator[str, None]:
        """Send a chat completion request to Bedrock.

        Args:
            messages: List of message dicts with 'role' and 'content'.
            tools: Optional list of tool definitions.
            model: Model identifier.
            max_tokens: Maximum tokens in response.
            temperature: Sampling temperature.
            stream: If True, return async generator yielding text chunks.

        Returns:
            LLMResponse if stream=False, or AsyncGenerator[str] if stream=True.
        """
        bedrock_messages, system_prompts = self._convert_messages(messages)
        bedrock_tools = self._convert_tools(tools)

        model_id = model or self.default_model

        if stream:
            return self._chat_stream(
                bedrock_messages, system_prompts, bedrock_tools, model_id, max_tokens, temperature, additional_fields
            )

        # Tier-3 fallback: try primary model, then fallback models on retryable errors
        models_to_try = [model_id] + [
            m for m in self.fallback_models if m != model_id
        ]

        last_exception = None
        for try_model in models_to_try:
            try:
                response = await self._converse_with_model(
                    bedrock_messages, system_prompts, bedrock_tools, try_model, max_tokens, temperature, additional_fields
                )
                return response
            except Exception as e:
                last_exception = e
                # Check if this is a retryable exception
                if not self._is_retryable_exception(e):
                    # Non-retryable error: fail immediately
                    logger.error("Bedrock: non-retryable error from model {}: {}", try_model, e)
                    raise

        # All models failed: raise the last exception
        logger.error("Bedrock: all models failed (tried {}). Last error: {}", models_to_try, last_exception)
        raise last_exception

    async def _converse_with_model(
        self,
        bedrock_messages: list[dict[str, Any]],
        system_prompts: list[dict[str, Any]],
        bedrock_tools: list[dict[str, Any]] | None,
        model_id: str,
        max_tokens: int,
        temperature: float,
        additional_fields: dict[str, Any] | None = None,
    ) -> LLMResponse:
        """Execute a single converse call and return parsed response."""
        def _converse() -> dict[str, Any]:
            kwargs: dict[str, Any] = {
                "modelId": model_id,
                "messages": bedrock_messages,
                "inferenceConfig": {
                    "maxTokens": max(1, max_tokens),
                    "temperature": temperature,
                },
            }
            if system_prompts:
                kwargs["system"] = system_prompts
            if bedrock_tools:
                kwargs["toolConfig"] = {"tools": bedrock_tools}
            if additional_fields:
                kwargs["additionalModelRequestFields"] = additional_fields

            return self._client.converse(**kwargs)

        response = await asyncio.get_event_loop().run_in_executor(None, _converse)
        return self._parse_response(response)

    def _is_retryable_exception(self, exception: Exception) -> bool:
        """Check if an exception is retryable (should trigger fallback)."""
        if isinstance(exception, botocore.exceptions.ClientError):
            error_code = exception.response.get("Error", {}).get("Code", "")
            return error_code in {
                "ThrottlingException",
                "ModelStreamErrorException",
                "ServiceUnavailableException",
                "InternalServerException",
            }
        return False

    async def _chat_stream(
        self,
        bedrock_messages: list[dict[str, Any]],
        system_prompts: list[dict[str, Any]],
        bedrock_tools: list[dict[str, Any]] | None,
        model_id: str,
        max_tokens: int,
        temperature: float,
        additional_fields: dict[str, Any] | None = None,
    ) -> AsyncGenerator[str, None]:
        """Stream chat completions from Bedrock.

        Yields:
            Text chunks as they arrive from the model.
        """
        kwargs: dict[str, Any] = {
            "modelId": model_id,
            "messages": bedrock_messages,
            "inferenceConfig": {
                "maxTokens": max(1, max_tokens),
                "temperature": temperature,
            },
        }
        if system_prompts:
            kwargs["system"] = system_prompts
        if bedrock_tools:
            kwargs["toolConfig"] = {"tools": bedrock_tools}
        if additional_fields:
            kwargs["additionalModelRequestFields"] = additional_fields

        def _converse_stream() -> dict[str, Any]:
            return self._client.converse_stream(**kwargs)

        response = await asyncio.get_event_loop().run_in_executor(None, _converse_stream)
        stream = response.get("stream")

        if stream:
            text_yielded = False
            for event in stream:
                if "contentBlockDelta" in event:
                    delta = event["contentBlockDelta"].get("delta", {})
                    if "text" in delta:
                        text_yielded = True
                        yield delta["text"]
                    elif "reasoningContent" in delta:
                        pass  # skip reasoning deltas in stream
                elif "messageStop" in event:
                    # End of stream
                    break
                elif "metadata" in event:
                    # Token usage metadata - can be logged but doesn't yield text
                    pass
            if not text_yielded:
                logger.warning("Bedrock stream: no text content yielded (model may have emitted only reasoning blocks)")

    async def get_models(self) -> list[str]:
        """Return static list of supported Bedrock models."""
        return [
            "us.anthropic.claude-sonnet-4-6",
            "us.anthropic.claude-opus-4-6-v1",
            "minimax.minimax-m2.1",
            "minimax.minimax-m2",
        ]
