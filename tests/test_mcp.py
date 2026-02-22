from __future__ import annotations

from unittest.mock import ANY, AsyncMock, MagicMock, patch

import pytest


class FakeTextContent:
    """Fake TextContent class for testing isinstance checks."""

    def __init__(self, text: str) -> None:
        self.text = text


class TestMCPToolWrapperProperties:
    """Tests for MCPToolWrapper property getters (no async)."""

    def test_name_returns_prefixed_name(self) -> None:
        """Test that name property returns mcp_{server_name}_{tool_def.name}."""
        from nanobot.agent.tools.mcp import MCPToolWrapper

        mock_session = MagicMock()
        mock_tool_def = MagicMock()
        mock_tool_def.name = "search"

        wrapper = MCPToolWrapper(mock_session, "my_server", mock_tool_def)

        assert wrapper.name == "mcp_my_server_search"

    def test_description_returns_tool_def_description_when_set(self) -> None:
        """Test that description property returns tool_def.description when set."""
        from nanobot.agent.tools.mcp import MCPToolWrapper

        mock_session = MagicMock()
        mock_tool_def = MagicMock()
        mock_tool_def.name = "search"
        mock_tool_def.description = "Search the web"

        wrapper = MCPToolWrapper(mock_session, "my_server", mock_tool_def)

        assert wrapper.description == "Search the web"

    def test_description_fallback_to_tool_def_name_when_none(self) -> None:
        """Test that description falls back to tool_def.name when description is None."""
        from nanobot.agent.tools.mcp import MCPToolWrapper

        mock_session = MagicMock()
        mock_tool_def = MagicMock()
        mock_tool_def.name = "search"
        mock_tool_def.description = None

        wrapper = MCPToolWrapper(mock_session, "my_server", mock_tool_def)

        assert wrapper.description == "search"

    def test_description_fallback_to_tool_def_name_when_empty(self) -> None:
        """Test that description falls back to tool_def.name when description is empty string."""
        from nanobot.agent.tools.mcp import MCPToolWrapper

        mock_session = MagicMock()
        mock_tool_def = MagicMock()
        mock_tool_def.name = "search"
        mock_tool_def.description = ""

        wrapper = MCPToolWrapper(mock_session, "my_server", mock_tool_def)

        assert wrapper.description == "search"

    def test_parameters_returns_tool_def_inputSchema_when_set(self) -> None:
        """Test that parameters returns tool_def.inputSchema when set."""
        from nanobot.agent.tools.mcp import MCPToolWrapper

        mock_session = MagicMock()
        mock_tool_def = MagicMock()
        mock_tool_def.name = "search"
        mock_tool_def.inputSchema = {
            "type": "object",
            "properties": {"query": {"type": "string"}},
        }

        wrapper = MCPToolWrapper(mock_session, "my_server", mock_tool_def)

        assert wrapper.parameters == {
            "type": "object",
            "properties": {"query": {"type": "string"}},
        }

    def test_parameters_fallback_to_empty_schema_when_inputSchema_none(self) -> None:
        """Test that parameters falls back to empty schema when inputSchema is None."""
        from nanobot.agent.tools.mcp import MCPToolWrapper

        mock_session = MagicMock()
        mock_tool_def = MagicMock()
        mock_tool_def.name = "search"
        mock_tool_def.inputSchema = None

        wrapper = MCPToolWrapper(mock_session, "my_server", mock_tool_def)

        assert wrapper.parameters == {"type": "object", "properties": {}}


class TestMCPToolWrapperExecute:
    """Tests for MCPToolWrapper.execute() method."""

    @pytest.mark.asyncio
    async def test_returns_joined_text_from_textContent_blocks(self) -> None:
        """Test that execute returns joined text from TextContent blocks."""
        mock_session = AsyncMock()
        mock_tool_def = MagicMock()
        mock_tool_def.name = "search"

        # Create a mock types module with TextContent class
        mock_types = MagicMock()
        mock_types.TextContent = FakeTextContent

        mock_result = MagicMock()
        mock_result.content = [FakeTextContent("First result"), FakeTextContent("Second result")]
        mock_session.call_tool.return_value = mock_result

        with patch("mcp.types", mock_types):
            from nanobot.agent.tools.mcp import MCPToolWrapper

            wrapper = MCPToolWrapper(mock_session, "my_server", mock_tool_def)
            result = await wrapper.execute(query="test")

            assert result == "First result\nSecond result"
            mock_session.call_tool.assert_called_once_with(
                "search",
                arguments={"query": "test"},
            )

    @pytest.mark.asyncio
    async def test_returns_no_output_when_content_list_empty(self) -> None:
        """Test that execute returns "(no output)" when content list is empty."""
        mock_session = AsyncMock()
        mock_tool_def = MagicMock()
        mock_tool_def.name = "search"

        mock_result = MagicMock()
        mock_result.content = []
        mock_session.call_tool.return_value = mock_result

        with patch("mcp.types", MagicMock()):
            from nanobot.agent.tools.mcp import MCPToolWrapper

            wrapper = MCPToolWrapper(mock_session, "my_server", mock_tool_def)
            result = await wrapper.execute()

            assert result == "(no output)"

    @pytest.mark.asyncio
    async def test_handles_non_textContent_blocks_falls_back_to_str(self) -> None:
        """Test that execute handles non-TextContent blocks by falling back to str()."""
        mock_session = AsyncMock()
        mock_tool_def = MagicMock()
        mock_tool_def.name = "search"

        # Create a mock types module with TextContent class
        mock_types = MagicMock()
        mock_types.TextContent = FakeTextContent

        mock_result = MagicMock()
        mock_result.content = [FakeTextContent("Text block"), "plain string"]
        mock_session.call_tool.return_value = mock_result

        with patch("mcp.types", mock_types):
            from nanobot.agent.tools.mcp import MCPToolWrapper

            wrapper = MCPToolWrapper(mock_session, "my_server", mock_tool_def)
            result = await wrapper.execute()

            assert result == "Text block\nplain string"

    @pytest.mark.asyncio
    async def test_passes_kwargs_through_to_session_call_tool_correctly(self) -> None:
        """Test that execute passes kwargs through to session.call_tool correctly."""
        mock_session = AsyncMock()
        mock_tool_def = MagicMock()
        mock_tool_def.name = "search"

        # Create a mock types module with TextContent class
        mock_types = MagicMock()
        mock_types.TextContent = FakeTextContent

        mock_result = MagicMock()
        mock_result.content = [FakeTextContent("result")]
        mock_session.call_tool.return_value = mock_result

        with patch("mcp.types", mock_types):
            from nanobot.agent.tools.mcp import MCPToolWrapper

            wrapper = MCPToolWrapper(mock_session, "my_server", mock_tool_def)
            await wrapper.execute(param1="value1", param2=42)

            mock_session.call_tool.assert_called_once_with(
                "search",
                arguments={"param1": "value1", "param2": 42},
            )


class TestConnectMcpServers:
    """Tests for connect_mcp_servers() function."""

    @pytest.mark.asyncio
    async def test_skips_servers_with_no_command_and_no_url_logs_warning(
        self,
    ) -> None:
        """Test that servers with no command and no url are skipped with a warning."""
        from nanobot.agent.tools.mcp import connect_mcp_servers

        mcp_servers = {
            "bad_server": MagicMock(command=None, url=None),
        }
        mock_registry = MagicMock()
        mock_stack = MagicMock()
        mock_stack.__aenter__ = AsyncMock(return_value=mock_stack)
        mock_stack.__aexit__ = AsyncMock(return_value=None)

        with patch("nanobot.agent.tools.mcp.logger") as mock_logger:
            await connect_mcp_servers(mcp_servers, mock_registry, mock_stack)

            mock_logger.warning.assert_called_once_with(
                "MCP server '{}': no command or url configured, skipping",
                "bad_server",
            )

    @pytest.mark.asyncio
    async def test_handles_exceptions_gracefully_logs_error_continues(
        self,
    ) -> None:
        """Test that exceptions during connect are logged and processing continues."""
        from nanobot.agent.tools.mcp import connect_mcp_servers

        mcp_servers = {
            "server1": MagicMock(command="node", url=None),
            "server2": MagicMock(command="python", url=None),
        }
        mock_registry = MagicMock()
        mock_stack = MagicMock()

        mock_read = AsyncMock()
        mock_write = AsyncMock()
        mock_session_instance = AsyncMock()
        mock_session_instance.initialize = AsyncMock()
        mock_session_instance.list_tools = AsyncMock(return_value=MagicMock(tools=[]))

        mock_stack.enter_async_context = AsyncMock(
            side_effect=[
                (mock_read, mock_write),  # server1 call 1: stdio_client → (read, write)
                mock_session_instance,  # server1 call 2: ClientSession → session
                ConnectionError("Failed to connect"),  # server2 call 1: stdio_client → raises
            ],
        )

        with (
            patch("nanobot.agent.tools.mcp.logger") as mock_logger,
            patch("mcp.ClientSession") as mock_session_cls,
            patch("mcp.StdioServerParameters"),
            patch("mcp.client.stdio.stdio_client") as mock_stdio_client,
        ):
            mock_session_cls.return_value = mock_session_instance
            mock_stdio_client.return_value = AsyncMock()

            await connect_mcp_servers(mcp_servers, mock_registry, mock_stack)

            # Verify error was logged for server2
            assert mock_logger.error.call_count == 1
            mock_logger.error.assert_called_once_with(
                "MCP server '{}': failed to connect: {}",
                "server2",
                ANY,
            )
            # First server should still have been processed
            assert mock_logger.info.call_count >= 1
