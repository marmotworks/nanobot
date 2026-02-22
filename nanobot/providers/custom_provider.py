"""Direct OpenAI-compatible provider — bypasses LiteLLM."""

from __future__ import annotations

from typing import Any

import httpx
import json_repair
from openai import AsyncOpenAI

from nanobot.providers.base import LLMProvider, LLMResponse, ToolCallRequest


class CustomProvider(LLMProvider):

    def __init__(self, api_key: str = "no-key", api_base: str = "http://localhost:8000/v1", default_model: str = "default"):
        super().__init__(api_key, api_base)
        self.default_model = default_model
        self._client = AsyncOpenAI(api_key=api_key, base_url=api_base)

    async def chat(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]] | None = None,
                   model: str | None = None, max_tokens: int = 4096, temperature: float = 0.7) -> LLMResponse:
        kwargs: dict[str, Any] = {"model": model or self.default_model, "messages": messages,
                                  "max_tokens": max(1, max_tokens), "temperature": temperature}
        if tools:
            kwargs.update(tools=tools, tool_choice="auto")
        try:
            return self._parse(await self._client.chat.completions.create(**kwargs))
        except Exception as e:
            return LLMResponse(content=f"Error: {e}", finish_reason="error")

    def _parse(self, response: Any) -> LLMResponse:
        choice = response.choices[0]
        msg = choice.message
        tool_calls = [
            ToolCallRequest(id=tc.id, name=tc.function.name,
                            arguments=json_repair.loads(tc.function.arguments) if isinstance(tc.function.arguments, str) else tc.function.arguments)
            for tc in (msg.tool_calls or [])
        ]
        u = response.usage
        return LLMResponse(
            content=msg.content, tool_calls=tool_calls, finish_reason=choice.finish_reason or "stop",
            usage={"prompt_tokens": u.prompt_tokens, "completion_tokens": u.completion_tokens, "total_tokens": u.total_tokens} if u else {},
            reasoning_content=getattr(msg, "reasoning_content", None),
        )

    def get_default_model(self) -> str:
        return self.default_model

    async def _query_lm_studio_v0_api(self) -> list[dict[str, Any]]:
        """
        Query LM Studio v0 REST API for model metadata including context length.
        Returns a list of model info with rich metadata.
        """
        # LM Studio v0 API endpoint — use self.api_base (stored by base class) to avoid
        # recovering the URL from the OpenAI client, which may mangle it internally.
        import urllib.parse
        base_url = (self.api_base or "http://localhost:1234/v1").rstrip('/')
        parsed = urllib.parse.urlparse(base_url)

        # Always construct v0 URL from scheme + host only (v0 API is at root, not under /v1)
        v0_api_url = f"{parsed.scheme}://{parsed.netloc}/api/v0/models"
        headers = {"Authorization": f"Bearer {self.api_key}"}

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(v0_api_url, headers=headers, timeout=10.0)
                response.raise_for_status()
                data = response.json()

                # Parse model information - LM Studio v0 uses "data" field
                models = []
                for model_data in data.get("data", []):
                    models.append({
                        "id": model_data.get("id"),
                        "object": model_data.get("object", "model"),
                        "type": model_data.get("type", "unknown"),
                        "publisher": model_data.get("publisher", "unknown"),
                        "arch": model_data.get("arch", "unknown"),
                        "state": model_data.get("state", "unknown"),
                        "max_context_length": model_data.get("max_context_length"),
                        "loaded_context_length": model_data.get("loaded_context_length"),
                        "capabilities": model_data.get("capabilities", []),
                        "loaded": model_data.get("loaded", False)
                    })

                return models

        except httpx.HTTPError as e:
            print(f"Warning: Failed to query LM Studio v0 API: {e}")
            return []
        except Exception as e:
            print(f"Warning: Unexpected error querying LM Studio v0 API: {e}")
            return []

    async def get_models(self) -> list[dict[str, Any]]:
        """
        Query available models from the LM Studio v0 API.
        Returns a list of model metadata including context_length.
        Falls back to OpenAI-compatible API if v0 API fails.
        """
        # Try LM Studio v0 API first
        v0_models = await self._query_lm_studio_v0_api()

        if v0_models:
            return v0_models

        # Fallback to OpenAI-compatible API
        try:
            models = await self._client.models.list()
            return [
                {
                    "id": model.id,
                    "context_length": getattr(model, "context_length", None)
                }
                for model in models.data
            ]
        except Exception as e:
            # If listing fails, return default model info
            return [
                {
                    "id": self.default_model,
                    "context_length": None
                }
            ]
