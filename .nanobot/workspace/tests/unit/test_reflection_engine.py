"""Tests for the ReflectionEngine class."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from agent.reflection import ReflectionEngine


class TestReflectionEngine:
    """Test suite for ReflectionEngine functionality."""

    @pytest.mark.asyncio
    async def test_reflection_engine_analyze_behavior_basic(self, mock_llm_client):
        """Test basic behavior analysis returns expected metrics."""
        engine = ReflectionEngine(mock_llm_client)

        # Sample messages showing tool usage and iterations
        messages = [
            {"role": "assistant", "content": "Hello!"},
            {
                "role": "tool",
                "tool_call_id": "call_123",
                "name": "web_search",
                "content": "Results for python test",
            },
            {"role": "assistant", "content": "Here are the results"},
        ]

        analysis = await engine.analyze_behavior(messages)

        # Verify analysis structure
        assert isinstance(analysis, dict)
        assert "tool_usage_frequency" in analysis
        assert "iteration_depth" in analysis
        assert "response_length" in analysis

        # Verify tool usage metrics
        assert isinstance(analysis["tool_usage_frequency"], dict)
        assert "web_search" in analysis["tool_usage_frequency"]

        # Verify iteration depth is reasonable
        assert analysis["iteration_depth"] >= 1
        assert analysis["iteration_depth"] <= 10  # Should be bounded

        # Verify response length is reasonable
        assert analysis["response_length"] >= 0

    @pytest.mark.asyncio
    async def test_reflection_engine_analyze_behavior_with_empty_messages(self, mock_llm_client):
        """Test handling of empty message list."""
        engine = ReflectionEngine(mock_llm_client)
        analysis = await engine.analyze_behavior([])

        assert isinstance(analysis, dict)
        assert analysis["tool_usage_frequency"] == {}
        assert analysis["iteration_depth"] == 0
        assert analysis["response_length"] == 0

    @pytest.mark.asyncio
    async def test_reflection_engine_analyze_behavior_with_large_context(self, mock_llm_client):
        """Test performance with large message history."""
        engine = ReflectionEngine(mock_llm_client)

        # Create 500+ messages
        large_messages = [
            {
                "role": "assistant" if i % 2 == 0 else "tool",
                "content": f"Message {i}",
                "tool_call_id": f"call_{i}" if i % 2 == 1 else None,
                "name": "web_search" if i % 2 == 1 else None,
            }
            for i in range(1000)
        ]

        # Should complete within reasonable time
        start_time = datetime.now()
        analysis = await engine.analyze_behavior(large_messages)
        elapsed = (datetime.now() - start_time).total_seconds()

        assert elapsed < 5  # Should complete in under 5 seconds
        assert isinstance(analysis, dict)

    @pytest.mark.asyncio
    async def test_reflection_engine_generate_improvements_basic(self, mock_llm_client):
        """Test basic improvement suggestions based on metrics."""
        engine = ReflectionEngine(mock_llm_client)

        analysis = {
            "tool_usage_frequency": {"web_search": 50},
            "iteration_depth": 20,
            "response_length": 5000,
            "user_satisfaction": 0.6,
        }

        improvements = await engine.generate_improvements(analysis)

        assert isinstance(improvements, list)
        assert len(improvements) >= 1
        assert all(isinstance(item, str) for item in improvements)

    @pytest.mark.asyncio
    async def test_reflection_engine_generate_improvements_contextual(self, mock_llm_client):
        """Test that improvements are relevant to detected issues."""
        engine = ReflectionEngine(mock_llm_client)

        # Analysis with high iteration depth (problem)
        high_iterations = {
            "tool_usage_frequency": {"web_search": 100},
            "iteration_depth": 25,
            "response_length": 8000,
            "user_satisfaction": 0.5,
        }

        # Analysis with low user satisfaction (problem)
        low_satisfaction = {
            "tool_usage_frequency": {},
            "iteration_depth": 5,
            "response_length": 500,
            "user_satisfaction": 0.3,
        }

        improvements_1 = await engine.generate_improvements(high_iterations)
        improvements_2 = await engine.generate_improvements(low_satisfaction)

        # High iterations should suggest breaking down tasks
        assert any(
            "iteration" in imp.lower() or "break" in imp.lower() for imp in improvements_1
        )

        # Low satisfaction should suggest improving quality
        assert any(
            "satisfaction" in imp.lower() or "quality" in imp.lower()
            for imp in improvements_2
        )

    @pytest.mark.asyncio
    async def test_reflection_engine_analyze_behavior_with_no_tool_calls(self, mock_llm_client):
        """Test behavior analysis with no tool calls."""
        engine = ReflectionEngine(mock_llm_client)

        messages = [
            {"role": "assistant", "content": "Hello world"},
            {"role": "user", "content": "Hi there"},
            {"role": "assistant", "content": "How can I help you?"},
        ]

        analysis = await engine.analyze_behavior(messages)

        assert analysis["tool_usage_frequency"] == {}
        assert analysis["iteration_depth"] >= 1


@pytest.fixture
def mock_llm_client():
    """Mock LLM client for testing."""
    client = MagicMock()
    client.chat.completions.create = AsyncMock()
    return client