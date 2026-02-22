"""AWS Bedrock provider using the Converse API."""

from __future__ import annotations

import asyncio
import json
from typing import TYPE_CHECKING, Any

import boto3
from loguru import logger

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

from nanobot.providers.base import LLMProvider, LLMResponse, ToolCallRequest


class BedrockProvider(LLMProvider):
    """AWS Bedrock provider using the Converse API."""

    def __init__(
        self,
        region_name: str = "us-east-1",
        default_model: str = "us.anthropic.claude-sonnet-4-6",
    ):
        self.region_name = region_name
        self.default_model = default_model
        self._client = boto3.client("bedrock-runtime", region_name=region_name)

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

        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")

            if role == "system":
                system_prompts.append({"text": content})
            elif role == "tool":
                tool_call_id = msg.get("tool_call_id", "")
                bedrock_messages.append({
                    "role": "user",
                    "content": [{
                        "toolResult": {
                            "toolUseId": tool_call_id,
                            "content": [{"text": str(content)}],
                        },
                    }],
                })
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
            else:
                bedrock_messages.append({
                    "role": role,
                    "content": [{"text": content}],
                })

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
        # A toolUse at the end of the list (no following message) is VALID and must be kept.
        # A toolUse followed by a non-user message is INVALID and must be stripped.
        # A toolUse followed by a user message without ALL matching toolResult IDs is INVALID and must be stripped.
        assistant_to_remove: set[int] = set()
        orphaned_tool_result_ids: set[str] = set()

        for idx, msg in enumerate(bedrock_messages):
            if msg.get("role") != "assistant":
                continue

            # Check if this assistant message has toolUse blocks
            content = msg.get("content", [])
            tool_use_ids: set[str] = set()
            for block in content:
                if "toolUse" in block:
                    tool_use_ids.add(block["toolUse"].get("toolUseId", ""))

            if not tool_use_ids:
                continue  # No toolUse blocks, skip

            # Check if the immediately next message is a user message with ALL toolResult blocks
            next_idx = idx + 1

            # If there's no next message, the toolUse is valid (results may follow in actual usage)
            if next_idx >= len(bedrock_messages):
                continue  # Keep toolUse at end

            next_msg = bedrock_messages[next_idx]

            # If next message is not a user message, this toolUse is invalid
            if next_msg.get("role") != "user":
                assistant_to_remove.add(idx)
                orphaned_tool_result_ids.update(tool_use_ids)
                continue

            # Next message is a user message - check if it has ALL toolResult blocks
            next_content = next_msg.get("content", [])
            result_ids_in_next: set[str] = set()
            for block in next_content:
                if "toolResult" in block:
                    result_ids_in_next.add(block["toolResult"].get("toolUseId", ""))
            # Check if all toolUse IDs are covered
            if result_ids_in_next >= tool_use_ids:
                continue  # Valid pair, keep both

            # User message exists but doesn't have all toolResult blocks - invalid
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

        text = None
        tool_calls: list[ToolCallRequest] = []

        for block in content_blocks:
            if "text" in block:
                text = block["text"]
            elif "toolUse" in block:
                tool_use = block["toolUse"]
                tool_calls.append(ToolCallRequest(
                    id=tool_use.get("toolUseId", ""),
                    name=tool_use.get("name", ""),
                    arguments=tool_use.get("input", {}),
                ))

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
        max_tokens: int = 4096,
        temperature: float = 0.7,
        stream: bool = False,
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
                bedrock_messages, system_prompts, bedrock_tools, model_id, max_tokens, temperature
            )

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

            return self._client.converse(**kwargs)

        response = await asyncio.get_event_loop().run_in_executor(None, _converse)
        return self._parse_response(response)

    async def _chat_stream(
        self,
        bedrock_messages: list[dict[str, Any]],
        system_prompts: list[dict[str, Any]],
        bedrock_tools: list[dict[str, Any]] | None,
        model_id: str,
        max_tokens: int,
        temperature: float,
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

        def _converse_stream() -> dict[str, Any]:
            return self._client.converse_stream(**kwargs)

        response = await asyncio.get_event_loop().run_in_executor(None, _converse_stream)
        stream = response.get("stream")

        if stream:
            for event in stream:
                if "contentBlockDelta" in event:
                    delta = event["contentBlockDelta"].get("delta", {})
                    if "text" in delta:
                        yield delta["text"]
                elif "messageStop" in event:
                    # End of stream
                    break
                elif "metadata" in event:
                    # Token usage metadata - can be logged but doesn't yield text
                    pass

    async def get_models(self) -> list[str]:
        """Return static list of supported models."""
        return [
            "us.anthropic.claude-sonnet-4-6",
            "us.anthropic.claude-opus-4-6-v1",
        ]
