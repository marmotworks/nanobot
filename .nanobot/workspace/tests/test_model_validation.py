"""Test model validation for subagents."""

import asyncio
from pathlib import Path
from nanobot.providers.custom_provider import CustomProvider
from nanobot.providers.registry import list_models
from nanobot.agent.subagent import SubagentManager
from nanobot.bus.queue import MessageBus


async def test_list_models():
    """Test model listing from provider."""
    print("Testing model listing...")

    # Create a custom provider
    provider = CustomProvider(
        api_key="test-key",
        api_base="http://localhost:1234/v1",
        default_model="glm-4.7-flash"
    )

    # List models
    models = await list_models(
        provider_name="custom",
        api_key="test-key",
        api_base="http://localhost:1234/v1"
    )

    print(f"Available models: {models}")

    if models:
        print(f"✓ Successfully listed {len(models)} models")
        # Test validation
        if "glm-4.7-flash" in models:
            print("✓ Default model is in the list")
        else:
            print("✗ Default model is NOT in the list")
    else:
        print("⚠ No models returned (this is expected if API is not running)")


async def test_spawn_with_model():
    """Test spawning a subagent with a specific model."""
    print("\nTesting subagent spawn with model validation...")

    # Create a custom provider
    provider = CustomProvider(
        api_key="test-key",
        api_base="http://localhost:1234/v1",
        default_model="glm-4.7-flash"
    )

    # Create a message bus
    bus = MessageBus()

    # Create subagent manager
    manager = SubagentManager(
        provider=provider,
        workspace=Path("/tmp/nanobot_test"),
        bus=bus,
        model="glm-4.7-flash"
    )

    # Test with a model that exists
    result = await manager.spawn(
        task="Echo back this message: Hello from subagent!",
        label="Test Subagent",
        model="glm-4.7-flash"
    )

    print(f"Spawn result: {result}")

    if "started" in result.lower():
        print("✓ Subagent spawned successfully with model validation")
    else:
        print("✗ Subagent spawn failed")


async def test_invalid_model():
    """Test spawning a subagent with an invalid model."""
    print("\nTesting subagent spawn with invalid model...")

    # Create a custom provider
    provider = CustomProvider(
        api_key="test-key",
        api_base="http://localhost:1234/v1",
        default_model="glm-4.7-flash"
    )

    # Create a message bus
    bus = MessageBus()

    # Create subagent manager
    manager = SubagentManager(
        provider=provider,
        workspace=Path("/tmp/nanobot_test"),
        bus=bus,
        model="glm-4.7-flash"
    )

    # Try with a model that doesn't exist
    result = await manager.spawn(
        task="Echo back this message: Hello!",
        label="Test Invalid",
        model="nonexistent-model-xyz"
    )

    print(f"Spawn result: {result}")

    if "Error" in result and "not available" in result.lower():
        print("✓ Invalid model correctly rejected")
    else:
        print("⚠ Unexpected result (may be expected if API allows any model)")


async def main():
    """Run all tests."""
    print("=" * 60)
    print("Model Validation Tests")
    print("=" * 60)

    try:
        await test_list_models()
        await test_spawn_with_model()
        await test_invalid_model()
    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 60)
    print("Tests complete!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())