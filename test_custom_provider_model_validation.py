"""
Test that CustomProvider model validation works correctly in subagents.
"""
import pytest
import asyncio
from pathlib import Path
from nanobot.agent.subagent import SubagentManager
from nanobot.bus import MessageBus
from nanobot.providers.custom_provider import CustomProvider
from nanobot.providers.registry import find_by_class_name


@pytest.mark.asyncio
async def test_custom_provider_class_name_mapping():
    """Test that CustomProvider class name maps to 'custom' spec name."""
    # Test the mapping
    assert find_by_class_name("CustomProvider") is not None
    assert find_by_class_name("customprovider") is not None
    print("✓ Provider class name mapping works")


@pytest.mark.asyncio
async def test_subagent_model_validation_with_custom_provider():
    """Test that subagent can validate models with CustomProvider."""
    workspace = Path("/tmp/test_workspace")
    workspace.mkdir(exist_ok=True)

    # Create a CustomProvider (like LM Studio)
    provider = CustomProvider(
        api_key="lm-studio",
        api_base="http://localhost:1234/v1",
        default_model="qwen3-coder-next"
    )

    bus = MessageBus()

    # Create subagent manager
    manager = SubagentManager(
        provider=provider,
        workspace=workspace,
        bus=bus,
        model="qwen3-coder-next",  # This should be validated correctly
        temperature=0.7,
        max_tokens=100
    )

    # Test that the model was set correctly
    assert manager.model == "qwen3-coder-next"
    print("✓ SubagentManager accepts CustomProvider with model parameter")

    # Test that find_by_class_name works
    spec = find_by_class_name("CustomProvider")
    assert spec is not None
    assert spec.name == "custom"
    print(f"✓ find_by_class_name('CustomProvider') returns {spec.name}")


if __name__ == "__main__":
    asyncio.run(test_custom_provider_class_name_mapping())
    asyncio.run(test_subagent_model_validation_with_custom_provider())
    print("\n✅ All tests passed!")