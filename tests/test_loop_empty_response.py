"""Unit tests for empty response / nudge retry logic in AgentLoop."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from nanobot.agent.loop import AgentLoop
from nanobot.bus.queue import MessageBus


class TestEmptyResponseAndNudgeRetry:
    """Test suite for empty response detection, diagnostic logging, and nudge retry."""

    @pytest.mark.asyncio
    async def test_empty_response_logs_diagnostic(self):
        """Test that empty response triggers diagnostic log warning."""
        mock_bus = MagicMock(spec=MessageBus)
        mock_provider = AsyncMock()
        mock_provider.get_default_model.return_value = "gpt-4"

        mock_response = MagicMock()
        mock_response.finish_reason = "stop"
        mock_response.content = None
        mock_response.tool_calls = []
        mock_response.usage = None

        # First call returns empty, second call (nudge retry) also returns empty
        # This triggers the double failure path with error message
        mock_run_agent_loop = AsyncMock(return_value=(None, [], mock_response))

        with (
            patch("nanobot.agent.loop.PolicyManager"),
            patch("nanobot.agent.loop.ContextBuilder"),
            patch("nanobot.agent.loop.ContextTracker"),
            patch("nanobot.agent.loop.ToolRegistry"),
            patch("nanobot.agent.loop.SubagentManager"),
            patch("nanobot.agent.loop.SessionManager"),
            patch("nanobot.agent.loop.MessageTool"),
            patch("nanobot.agent.loop.SpawnTool"),
            patch("nanobot.agent.loop.ExecTool"),
            patch("nanobot.agent.loop.WebSearchTool"),
            patch("nanobot.agent.loop.WebFetchTool"),
            patch("nanobot.agent.loop.ReadFileTool"),
            patch("nanobot.agent.loop.WriteFileTool"),
            patch("nanobot.agent.loop.EditFileTool"),
            patch("nanobot.agent.loop.ListDirTool"),
            patch("nanobot.agent.loop.CronTool"),
            patch("nanobot.agent.loop.ContextTracker") as mock_tracker_cls,
        ):
            mock_tracker = MagicMock()
            mock_tracker_cls.return_value = mock_tracker
            mock_tracker.context_usage = {}
            mock_tracker.add_tokens = MagicMock()

            mock_tool_registry = MagicMock()
            mock_tool_registry.get.return_value = None

            agent = AgentLoop(
                bus=mock_bus,
                provider=mock_provider,
                workspace=MagicMock(),
                model="gpt-4",
            )

            agent.tools = mock_tool_registry

            with patch("nanobot.agent.loop.logger.warning") as mock_warning:
                agent._run_agent_loop = mock_run_agent_loop

                result = await agent.process_direct("hello")

                # After nudge retry also fails, we get the error message
                assert "finish_reason" in result
                # Verify diagnostic log was called for the empty response
                # (may be called more than once due to context tracker warning)
                assert any(
                    "Empty response from model" in str(call)
                    for call in mock_warning.call_args_list
                )

    @pytest.mark.asyncio
    async def test_nudge_retry_succeeds(self):
        """Test that nudge retry succeeds on second attempt."""
        mock_bus = MagicMock(spec=MessageBus)
        mock_provider = AsyncMock()
        mock_provider.get_default_model.return_value = "gpt-4"

        mock_response = MagicMock()
        mock_response.finish_reason = "stop"
        mock_response.content = None
        mock_response.tool_calls = []
        mock_response.usage = None

        mock_response_retry = MagicMock()
        mock_response_retry.finish_reason = "stop"
        mock_response_retry.content = "hello from retry"
        mock_response_retry.tool_calls = []
        mock_response_retry.usage = None

        call_count = 0

        async def mock_run_agent_loop(messages, on_progress=None):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return (None, [], mock_response)
            else:
                return ("hello from retry", [], mock_response_retry)

        with (
            patch("nanobot.agent.loop.PolicyManager"),
            patch("nanobot.agent.loop.ContextBuilder"),
            patch("nanobot.agent.loop.ContextTracker"),
            patch("nanobot.agent.loop.ToolRegistry"),
            patch("nanobot.agent.loop.SubagentManager"),
            patch("nanobot.agent.loop.SessionManager"),
            patch("nanobot.agent.loop.MessageTool"),
            patch("nanobot.agent.loop.SpawnTool"),
            patch("nanobot.agent.loop.ExecTool"),
            patch("nanobot.agent.loop.WebSearchTool"),
            patch("nanobot.agent.loop.WebFetchTool"),
            patch("nanobot.agent.loop.ReadFileTool"),
            patch("nanobot.agent.loop.WriteFileTool"),
            patch("nanobot.agent.loop.EditFileTool"),
            patch("nanobot.agent.loop.ListDirTool"),
            patch("nanobot.agent.loop.CronTool"),
            patch("nanobot.agent.loop.ContextTracker") as mock_tracker_cls,
        ):
            mock_tracker = MagicMock()
            mock_tracker_cls.return_value = mock_tracker
            mock_tracker.context_usage = {}
            mock_tracker.add_tokens = MagicMock()

            mock_tool_registry = MagicMock()
            mock_tool_registry.get.return_value = None

            agent = AgentLoop(
                bus=mock_bus,
                provider=mock_provider,
                workspace=MagicMock(),
                model="gpt-4",
            )

            agent.tools = mock_tool_registry
            agent._run_agent_loop = mock_run_agent_loop

            result = await agent.process_direct("hello")

            assert result == "hello from retry"
            assert call_count == 2

    @pytest.mark.asyncio
    async def test_double_failure_surfaces_cause(self):
        """Test that double failure surfaces finish_reason in error message."""
        mock_bus = MagicMock(spec=MessageBus)
        mock_provider = AsyncMock()
        mock_provider.get_default_model.return_value = "gpt-4"

        mock_response = MagicMock()
        mock_response.finish_reason = "length"
        mock_response.content = "some content"
        mock_response.tool_calls = []
        mock_response.usage = None

        async def mock_run_agent_loop(messages, on_progress=None):
            return (None, [], mock_response)

        with (
            patch("nanobot.agent.loop.PolicyManager"),
            patch("nanobot.agent.loop.ContextBuilder"),
            patch("nanobot.agent.loop.ContextTracker"),
            patch("nanobot.agent.loop.ToolRegistry"),
            patch("nanobot.agent.loop.SubagentManager"),
            patch("nanobot.agent.loop.SessionManager"),
            patch("nanobot.agent.loop.MessageTool"),
            patch("nanobot.agent.loop.SpawnTool"),
            patch("nanobot.agent.loop.ExecTool"),
            patch("nanobot.agent.loop.WebSearchTool"),
            patch("nanobot.agent.loop.WebFetchTool"),
            patch("nanobot.agent.loop.ReadFileTool"),
            patch("nanobot.agent.loop.WriteFileTool"),
            patch("nanobot.agent.loop.EditFileTool"),
            patch("nanobot.agent.loop.ListDirTool"),
            patch("nanobot.agent.loop.CronTool"),
            patch("nanobot.agent.loop.ContextTracker") as mock_tracker_cls,
        ):
            mock_tracker = MagicMock()
            mock_tracker_cls.return_value = mock_tracker
            mock_tracker.context_usage = {}
            mock_tracker.add_tokens = MagicMock()

            mock_tool_registry = MagicMock()
            mock_tool_registry.get.return_value = None

            agent = AgentLoop(
                bus=mock_bus,
                provider=mock_provider,
                workspace=MagicMock(),
                model="gpt-4",
            )

            agent.tools = mock_tool_registry
            agent._run_agent_loop = mock_run_agent_loop

            result = await agent.process_direct("hello")

            assert "finish_reason" in result
            assert "length" in result
