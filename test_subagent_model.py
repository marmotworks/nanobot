"""
Test that subagents can accept a model parameter.
"""
import pytest
import asyncio
from pathlib import Path
from nanobot.agent.subagent import SubagentManager
from nanobot.bus import MessageBus
from nanobot.provider import LLMProvider


@pytest.mark.asyncio
async def test_subagent_manager_accepts_model():
    """Test that SubagentManager can be initialized with a specific model."""
    workspace = Path("/tmp/test_workspace")
    workspace.mkdir(exist_ok=True)
    
    # Create a mock provider
    provider = LLMProvider(
        name="test",
        api_key="test-key",
        api_base="http://localhost:1234/v1"
    )
    
    bus = MessageBus()
    
    # Test 1: SubagentManager accepts model parameter
    manager = SubagentManager(
        provider=provider,
        workspace=workspace,
        bus=bus,
        model="deepseek/deepseek-chat",  # Should accept this
        temperature=0.7,
        max_tokens=100
    )
    
    assert manager.model == "deepseek/deepseek-chat"
    print("✓ SubagentManager accepts model parameter")
    
    # Test 2: SubagentManager falls back to default if model not specified
    manager_default = SubagentManager(
        provider=provider,
        workspace=workspace,
        bus=bus,
        temperature=0.7,
        max_tokens=100
    )
    
    assert manager_default.model is not None
    print("✓ SubagentManager falls back to default model when not specified")


if __name__ == "__main__":
    asyncio.run(test_subagent_manager_accepts_model())