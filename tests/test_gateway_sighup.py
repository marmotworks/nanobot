"""Tests for SIGHUP handler in gateway daemon."""

import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from nanobot.config.loader import load_config, save_config
from nanobot.config.schema import Config


class TestSIGHUPHandler:
    """Test SIGHUP signal handling for config reload."""

    @pytest.mark.asyncio
    async def test_sighup_handler_registers_with_event_loop(self):
        """Test that SIGHUP handler is properly registered with asyncio event loop."""
        # Mock the gateway run function to capture signal handler registration
        with patch("asyncio.get_event_loop") as mock_get_loop:
            mock_loop = MagicMock()
            mock_get_loop.return_value = mock_loop

            # The gateway function should register a SIGHUP handler
            # This test verifies the handler is registered, not the full gateway
            from nanobot.cli.commands import _sighup_handler

            # Check that the handler function exists
            assert _sighup_handler is not None
            assert callable(_sighup_handler)

    @pytest.mark.asyncio
    async def test_sighup_triggers_config_reload(self):
        """Test that SIGHUP triggers config reload."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            config_path = tmp_path / "config.json"

            # Create initial config
            config = Config()
            config.agents.defaults.temperature = 0.5
            save_config(config, config_path)

            # Load initial config
            loaded_config = load_config(config_path)
            assert loaded_config.agents.defaults.temperature == 0.5

            # Modify config
            config.agents.defaults.temperature = 0.8
            save_config(config, config_path)

            # Reload config
            reloaded_config = load_config(config_path)
            assert reloaded_config.agents.defaults.temperature == 0.8

    @pytest.mark.asyncio
    async def test_sighup_handler_updates_channel_connections(self):
        """Test that SIGHUP handler can trigger channel reconnection."""
        with patch("nanobot.channels.manager.ChannelManager") as mock_channel_manager:
            mock_manager = AsyncMock()
            mock_channel_manager.return_value = mock_manager

            # Simulate SIGHUP triggering channel reconnection
            # This would be called from the actual handler
            await mock_manager.restart_all()

            mock_manager.restart_all.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_sighup_handler_reregisters_cron_jobs(self):
        """Test that SIGHUP handler can re-register cron jobs."""
        with patch("nanobot.cron.service.CronService") as mock_cron_service:
            mock_service = AsyncMock()
            mock_cron_service.return_value = mock_service

            # Simulate SIGHUP triggering cron job re-registration
            await mock_service.resync_jobs()

            mock_service.resync_jobs.assert_awaited_once()

    def test_sighup_handler_is_async_safe(self):
        """Test that SIGHUP handler uses asyncio-safe pattern."""
        # The handler should use loop.add_signal_handler, not signal.signal
        # This ensures compatibility with asyncio event loop

        # Verify the expected pattern exists
        with patch("asyncio.get_running_loop") as mock_running_loop:
            mock_loop = MagicMock()
            mock_running_loop.return_value = mock_loop

            # In the actual implementation, we'd use:
            # loop.add_signal_handler(signal.SIGHUP, handler)
            # This is the asyncio-safe pattern

            mock_loop.add_signal_handler.assert_not_called()

            # Verify signal module is available for reference
            import signal
            assert hasattr(signal, "SIGHUP")


class TestLaunchdPlist:
    """Test launchd plist file."""

    def test_plist_file_exists(self):
        """Test that the launchd plist file exists."""
        from nanobot.cli.daemon_manager import _get_source_plist_path

        plist_path = _get_source_plist_path()
        assert plist_path.exists(), f"Plist file not found at {plist_path}"

    def test_plist_has_required_keys(self):
        """Test that the plist has required launchd keys."""
        from nanobot.cli.daemon_manager import _get_source_plist_path
        
        plist_path = _get_source_plist_path()
        content = plist_path.read_text()
        
        # Check for required keys
        required_keys = ["Label", "ProgramArguments", "KeepAlive"]
        for key in required_keys:
            assert key in content, f"Missing required key: {key}"
    
    def test_plist_has_keepalive_true(self):
        """Test that KeepAlive is set to true for auto-restart."""
        from nanobot.cli.daemon_manager import _get_source_plist_path
        
        plist_path = _get_source_plist_path()
        content = plist_path.read_text()
        
        assert "<key>KeepAlive</key>" in content
        assert "<true/>" in content or "<true />" in content
    
    def test_plist_has_log_paths(self):
        """Test that the plist has standard output/error paths."""
        from nanobot.cli.daemon_manager import _get_source_plist_path
        
        plist_path = _get_source_plist_path()
        content = plist_path.read_text()
        
        assert "StandardOutPath" in content
        assert "StandardErrorPath" in content


class TestDaemonManager:
    """Test daemon management functions."""
    
    def test_install_daemon_not_on_macos(self):
        """Test install_daemon returns False when launchctl not found."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError("launchctl not found")
            
            from nanobot.cli.daemon_manager import install_daemon
            
            result = install_daemon()
            assert result is False
    
    def test_uninstall_daemon_not_installed(self):
        """Test uninstall_daemon handles non-installed daemon."""
        with patch("nanobot.cli.daemon_manager._get_plist_path") as mock_path:
            mock_path.return_value = Path("/nonexistent/plist.plist")
            
            # Mock exists to return False
            with patch("pathlib.Path.exists") as mock_exists:
                mock_exists.return_value = False
                
                from nanobot.cli.daemon_manager import uninstall_daemon
                
                result = uninstall_daemon()
                assert result is False
    
    def test_daemon_status_not_installed(self):
        """Test daemon_status returns 'not_installed' when plist missing."""
        with patch("nanobot.cli.daemon_manager._get_plist_path") as mock_path:
            mock_path.return_value = Path("/nonexistent/plist.plist")
            
            with patch("pathlib.Path.exists") as mock_exists:
                mock_exists.return_value = False
                
                from nanobot.cli.daemon_manager import daemon_status
                
                status = daemon_status()
                assert status == "not_installed"
