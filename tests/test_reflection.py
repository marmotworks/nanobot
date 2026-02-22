"""Tests for ReflectionEngine - self-reflective capabilities."""

from unittest.mock import AsyncMock

import pytest

from nanobot.agent.reflection import ReflectionEngine


@pytest.fixture
def mock_llm_client():
    """Create a mock LLM client."""
    return AsyncMock()


@pytest.mark.asyncio
async def test_empty_messages(mock_llm_client):
    """Test that empty messages returns all zeros."""
    engine = ReflectionEngine(mock_llm_client)

    result = await engine.analyze_behavior([])

    assert result == {
        "tool_usage_frequency": {},
        "iteration_depth": 0,
        "response_length": 0,
    }


@pytest.mark.asyncio
async def test_assistant_messages(mock_llm_client):
    """Test that assistant messages are counted correctly."""
    engine = ReflectionEngine(mock_llm_client)

    messages = [
        {"role": "assistant", "content": "Hello"},
        {"role": "assistant", "content": "World"},
        {"role": "assistant", "content": "Test"},
    ]

    result = await engine.analyze_behavior(messages)

    assert result["iteration_depth"] == 3
    assert result["response_length"] == 14
    assert result["tool_usage_frequency"] == {}


@pytest.mark.asyncio
async def test_tool_messages(mock_llm_client):
    """Test that tool messages are counted correctly."""
    engine = ReflectionEngine(mock_llm_client)

    messages = [
        {"role": "tool", "name": "web_search", "content": "Results"},
        {"role": "tool", "name": "web_search", "content": "More"},
        {"role": "tool", "name": "calculator", "content": "123"},
    ]

    result = await engine.analyze_behavior(messages)

    assert result["tool_usage_frequency"] == {
        "web_search": 2,
        "calculator": 1,
    }
    assert result["iteration_depth"] == 0
    assert result["response_length"] == 0


@pytest.mark.asyncio
async def test_iteration_depth_capped(mock_llm_client):
    """Test that iteration depth is capped at 50."""
    engine = ReflectionEngine(mock_llm_client)

    messages = [{"role": "assistant", "content": "x"} for _ in range(60)]

    result = await engine.analyze_behavior(messages)

    assert result["iteration_depth"] == 50
    assert result["response_length"] == 60


@pytest.mark.asyncio
async def test_mixed_messages(mock_llm_client):
    """Test that mixed messages are counted correctly."""
    engine = ReflectionEngine(mock_llm_client)

    messages = [
        {"role": "system", "content": "System message"},
        {"role": "user", "content": "User query"},
        {"role": "assistant", "content": "Assistant response"},
        {"role": "tool", "name": "web_search", "content": "Search result"},
        {"role": "assistant", "content": "Follow-up"},
    ]

    result = await engine.analyze_behavior(messages)

    assert result["iteration_depth"] == 2
    assert result["response_length"] == len("Assistant response") + len("Follow-up")
    assert result["tool_usage_frequency"] == {"web_search": 1}


@pytest.mark.asyncio
async def test_no_issues(mock_llm_client):
    """Test that zeroed analysis returns generic suggestion."""
    engine = ReflectionEngine(mock_llm_client)

    analysis = {
        "tool_usage_frequency": {},
        "iteration_depth": 0,
        "response_length": 0,
    }

    suggestions = await engine.generate_improvements(analysis)

    assert len(suggestions) == 1
    assert "Good performance" in suggestions[0]


@pytest.mark.asyncio
async def test_high_iteration_depth(mock_llm_client):
    """Test that high iteration depth generates suggestion."""
    engine = ReflectionEngine(mock_llm_client)

    analysis = {
        "tool_usage_frequency": {},
        "iteration_depth": 20,
        "response_length": 0,
    }

    suggestions = await engine.generate_improvements(analysis)

    assert len(suggestions) == 1
    assert "High iteration depth" in suggestions[0]


@pytest.mark.asyncio
async def test_high_web_search(mock_llm_client):
    """Test that high web search count generates suggestion."""
    engine = ReflectionEngine(mock_llm_client)

    analysis = {
        "tool_usage_frequency": {"web_search": 25},
        "iteration_depth": 0,
        "response_length": 0,
    }

    suggestions = await engine.generate_improvements(analysis)

    assert len(suggestions) == 1
    assert "Frequent web searches" in suggestions[0]


@pytest.mark.asyncio
async def test_high_tool_usage(mock_llm_client):
    """Test that high total tool usage generates suggestion."""
    engine = ReflectionEngine(mock_llm_client)

    analysis = {
        "tool_usage_frequency": {"file_read": 30, "calculator": 30},
        "iteration_depth": 0,
        "response_length": 0,
    }

    suggestions = await engine.generate_improvements(analysis)

    assert len(suggestions) == 1
    assert "High tool usage" in suggestions[0]


@pytest.mark.asyncio
async def test_long_response(mock_llm_client):
    """Test that long response generates suggestion."""
    engine = ReflectionEngine(mock_llm_client)

    analysis = {
        "tool_usage_frequency": {},
        "iteration_depth": 0,
        "response_length": 5000,
    }

    suggestions = await engine.generate_improvements(analysis)

    assert len(suggestions) == 1
    assert "Long responses" in suggestions[0]


@pytest.mark.asyncio
async def test_effective_result(mock_llm_client):
    """Test that successful tool call is marked as effective."""
    engine = ReflectionEngine(mock_llm_client)

    tool_call = {"name": "web_search"}
    result = "Found 10 results"

    evaluation = await engine.evaluate_decision(tool_call, result)

    assert "effective" in evaluation
    assert "Tool web_search was effective" in evaluation


@pytest.mark.asyncio
async def test_suboptimal_result(mock_llm_client):
    """Test that failed tool call is marked as suboptimal."""
    engine = ReflectionEngine(mock_llm_client)

    tool_call = {"name": "calculator"}
    result = "Error: Division by zero"

    evaluation = await engine.evaluate_decision(tool_call, result)

    assert "suboptimal" in evaluation
    assert "Tool calculator was suboptimal" in evaluation


@pytest.mark.asyncio
async def test_result_length_in_output(mock_llm_client):
    """Test that result length appears in output."""
    engine = ReflectionEngine(mock_llm_client)

    tool_call = {"name": "web_search"}
    result = "x" * 100

    evaluation = await engine.evaluate_decision(tool_call, result)

    assert "100 characters" in evaluation


@pytest.mark.asyncio
async def test_small_session(mock_llm_client):
    """Test that small session returns empty patterns."""
    engine = ReflectionEngine(mock_llm_client)

    session = [
        {"role": "user", "content": "Query"},
        {"role": "assistant", "content": "Response"},
        {"role": "user", "content": "Follow-up"},
        {"role": "assistant", "content": "Answer"},
        {"role": "user", "content": "Thanks"},
    ]

    patterns = await engine.detect_patterns(session)

    assert patterns == []


@pytest.mark.asyncio
async def test_large_session(mock_llm_client):
    """Test that large session returns large_session pattern."""
    engine = ReflectionEngine(mock_llm_client)

    session = [{"role": "user", "content": "x"} for _ in range(55)]

    patterns = await engine.detect_patterns(session)

    assert len(patterns) == 1
    assert patterns[0]["type"] == "large_session"
    assert "Large session" in patterns[0]["message"]


@pytest.mark.asyncio
async def test_returns_string(mock_llm_client):
    """Test that generate_self_report returns a non-empty string."""
    engine = ReflectionEngine(mock_llm_client)

    report = await engine.generate_self_report()

    assert isinstance(report, str)
    assert len(report) > 0
    assert "ReflectionEngine" in report
