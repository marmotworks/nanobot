"""Integration tests for BedrockProvider with real AWS Bedrock API calls."""

from __future__ import annotations

import pytest

from nanobot.providers.bedrock_provider import BedrockProvider


@pytest.mark.integration
@pytest.mark.asyncio
async def test_chat_integration():
    """Test BedrockProvider.chat() with real AWS Bedrock API call.

    Uses the us.anthropic.claude-sonnet-4-6 inference profile which is the
    standard cross-region inference profile for Claude Sonnet 4.x models.
    """
    provider = BedrockProvider(default_model="us.anthropic.claude-sonnet-4-6")

    response = await provider.chat(
        messages=[{"role": "user", "content": "Say hello in exactly 3 words."}],
        model="us.anthropic.claude-sonnet-4-6",
    )

    assert isinstance(response.content, str)
    assert len(response.content) > 0
    assert response.usage["total_tokens"] > 0
