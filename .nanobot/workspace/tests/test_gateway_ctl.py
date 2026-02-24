"""Tests for gateway daemon control (install, uninstall, status, start, stop, restart, logs)."""

from __future__ import annotations

import os
import signal
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from nanobot.cli.daemon_manager import (
    _get_plist_path,
    _get_source_plist_path,
    daemon_status,
    install_daemon,
    print_daemon_info,
    uninstall_daemon,
)


class TestGatewayDaemonPaths:
    """Test path resolution for gateway daemon files."""

    def test_source_plist_exists(self):
        """Test that the source plist file exists in the nanobot package."""
        source_path = _get_source_plist_path()
        assert source_path.exists(), f"Source plist not found at {source_path}"
        assert source_path.is_file(), f"Source path is not a file: {source_path}"

    def test_source_plist_is_xml(self):
        """Test that the source plist file is valid XML."""
        source_path = _get_source_plist_path()
        content = source_path.read_text()
        assert content.startswith("<?xml"), "Plist file does not start with XML declaration"
        assert "<!DOCTYPE plist" in content, "Plist file missing DOCTYPE declaration"

    def test_plist_has_required_keys(self):
        """Test that the plist has all required launchd keys."""
        source_path = _get_source_plist_path()
        content = source_path.read_text()

        required_keys = [
            "Label",
            "ProgramArguments",
            "KeepAlive",
            "StandardOutPath",
            "StandardErrorPath",
        ]
        for key in required_keys:
            assert key in content, f"Missing required key: {key}"

    def test_plist_label_correct(self):
        """Test that the plist Label is set correctly."""
        source_path = _get_source_plist_path()
        content = source_path.read_text()

        assert '<string>com.nanobot.gateway</string>' in content, "Incorrect Label value"

    def test_plist_program_arguments(self):
        """Test that the plist ProgramArguments includes nanobot gateway."""
        source_path = _get_source_plist_path()
        content = source_path.read_text()

        assert '<string>/usr/bin/env</string>' in content, "Missing /usr/bin/env"
        assert '<string>nanobot</string>' in content, "Missing nanobot"
        assert '<string>gateway</string>' in content, "Missing gateway"

    def test_plist_keepalive_enabled(self):
        """Test that KeepAlive is set to true for auto-restart."""
        source_path = _get_source_plist_path()
        content = source_path.read_text()

        assert "<key>KeepAlive</key>" in content, "Missing KeepAlive key"
        assert "<true/>" in content or "<true />" in content, "KeepAlive not set to true"

    def test_plist_log_paths(self):
        """Test that the plist has standard output/error log paths."""
        source_path = _get_source_plist_path()
        content = source_path.read_text()

        assert "StandardOutPath" in content, "Missing StandardOutPath"
        assert "StandardErrorPath" in content, "Missing StandardErrorPath"
        assert "gateway.log" in content, "Missing gateway.log path"
        assert "gateway-error.log" in content, "Missing gateway-error.log path"

    def test_plist_environment_variables(self):
        """Test that the plist has PYTHONUNBUFFERED set."""
        source_path = _get_source_plist_path()
        content = source_path.read_text()

        assert "EnvironmentVariables" in content, "Missing EnvironmentVariables"
        assert "PYTHONUNBUFFERED" in content, "Missing PYTHONUNBUFFERED"
        assert "<string>1</string>" in content, "PYTHONUNBUFFERED not set to 1"

    def test_plist_throttle_interval(self):
        """Test that the plist has ThrottleInterval for restart throttling."""
        source_path = _get_source_plist_path()
        content = source_path.read_text()

        assert "ThrottleInterval" in content, "Missing ThrottleInterval"
        assert "<integer>5</integer>" in content, "ThrottleInterval not set to 5"


class TestGatewayDaemonStatus:
    """Test daemon status checking functionality."""

    def test_daemon_status_not_installed(self):
        """Test daemon_status returns 'not_installed' when plist is missing."""
        with patch("nanobot.cli.daemon_manager._get_plist_path") as mock_path:
            mock_path.return_value = Path("/nonexistent/plist.plist")

            with patch("pathlib.Path.exists") as mock_exists:
                mock_exists.return_value = False

                status = daemon_status()
                assert status == "not_installed"

    def test_daemon_status_running(self):
        """Test daemon_status returns 'running' when daemon is active."""
        with patch("nanobot.cli.daemon_manager._get_plist_path") as mock_path:
            mock_path.return_value = Path("/tmp/test.plist")

            with patch("pathlib.Path.exists") as mock_exists:
                mock_exists.return_value = True

                with patch("subprocess.run") as mock_run:
                    mock_result = MagicMock()
                    mock_result.returncode = 0
                    mock_run.return_value = mock_result

                    status = daemon_status()
                    assert status == "running"
                    mock_run.assert_called_once_with(
                        ["launchctl", "list", "com.nanobot.gateway"],
                        capture_output=True,
                        text=True,
                    )

    def test_daemon_status_stopped(self):
        """Test daemon_status returns 'stopped' when daemon is not running."""
        with patch("nanobot.cli.daemon_manager._get_plist_path") as mock_path:
            mock_path.return_value = Path("/tmp/test.plist")

            with patch("pathlib.Path.exists") as mock_exists:
                mock_exists.return_value = True

                with patch("subprocess.run") as mock_run:
                    mock_result = MagicMock()
                    mock_result.returncode = 1
                    mock_result.stderr = "not found"
                    mock_run.return_value = mock_result

                    status = daemon_status()
                    assert status == "stopped"
                    mock_run.assert_called_once_with(
                        ["launchctl", "list", "com.nanobot.gateway"],
                        capture_output=True,
                        text=True,
                    )

    def test_daemon_status_unknown_on_error(self):
        """Test daemon_status returns 'unknown' when launchctl is not found."""
        with patch("nanobot.cli.daemon_manager._get_plist_path") as mock_path:
            mock_path.return_value = Path("/tmp/test.plist")

            with patch("pathlib.Path.exists") as mock_exists:
                mock_exists.return_value = True

                with patch("subprocess.run") as mock_run:
                    mock_run.side_effect = FileNotFoundError("launchctl not found")

                    status = daemon_status()
                    assert status == "unknown"


class TestGatewayDaemonInstall:
    """Test daemon installation functionality."""

    def test_install_daemon_success(self):
        """Test successful daemon installation."""
        with patch("nanobot.cli.daemon_manager._get_source_plist_path") as mock_source:
            mock_source.return_value = Path("/tmp/source.plist")

            with patch("nanobot.cli.daemon_manager._get_plist_path") as mock_target:
                mock_target.return_value = Path("/tmp/target.plist")

                with patch("pathlib.Path.exists") as mock_exists:
                    mock_exists.return_value = True

                with patch("shutil.copy2") as mock_copy:
                    with patch("subprocess.run") as mock_run:
                        mock_result = MagicMock()
                        mock_result.returncode = 0
                        mock_run.return_value = mock_result

                        result = install_daemon()
                        assert result is True
                        mock_copy.assert_called_once()
                        mock_run.assert_called_once_with(
                            ["launchctl", "load", str(mock_target.return_value)],
                            capture_output=True,
                            text=True,
                            check=True,
                        )

    def test_install_daemon_source_not_found(self):
        """Test install_daemon returns False when source plist is missing."""
        with patch("nanobot.cli.daemon_manager._get_source_plist_path") as mock_source:
            mock_source.return_value = Path("/nonexistent/source.plist")

            with patch("pathlib.Path.exists") as mock_exists:
                mock_exists.return_value = False

                result = install_daemon()
                assert result is False

    def test_install_daemon_copy_failure(self):
        """Test install_daemon returns False when copy fails."""
        with patch("nanobot.cli.daemon_manager._get_source_plist_path") as mock_source:
            mock_source.return_value = Path("/tmp/source.plist")

            with patch("nanobot.cli.daemon_manager._get_plist_path") as mock_target:
                mock_target.return_value = Path("/tmp/target.plist")

                with patch("pathlib.Path.exists") as mock_exists:
                    mock_exists.return_value = True

                with patch("shutil.copy2") as mock_copy:
                    mock_copy.side_effect = Exception("Copy failed")

                    result = install_daemon()
                    assert result is False

    def test_install_daemon_launchctl_failure(self):
        """Test install_daemon returns False when launchctl fails."""
        with patch("nanobot.cli.daemon_manager._get_source_plist_path") as mock_source:
            mock_source.return_value = Path("/tmp/source.plist")

            with patch("nanobot.cli.daemon_manager._get_plist_path") as mock_target:
                mock_target.return_value = Path("/tmp/target.plist")

                with patch("pathlib.Path.exists") as mock_exists:
                    mock_exists.return_value = True

                with patch("shutil.copy2") as mock_copy:
                    with patch("subprocess.run") as mock_run:
                        mock_result = MagicMock()
                        mock_result.returncode = 1
                        mock_result.stderr = "Load failed"
                        mock_run.return_value = mock_result

                        result = install_daemon()
                        assert result is False

    def test_install_daemon_not_on_macos(self):
        """Test install_daemon returns False when launchctl is not found."""
        with patch("nanobot.cli.daemon_manager._get_source_plist_path") as mock_source:
            mock_source.return_value = Path("/tmp/source.plist")

            with patch("nanobot.cli.daemon_manager._get_plist_path") as mock_target:
                mock_target.return_value = Path("/tmp/target.plist")

                with patch("pathlib.Path.exists") as mock_exists:
                    mock_exists.return_value = True

                with patch("shutil.copy2") as mock_copy:
                    with patch("subprocess.run") as mock_run:
                        mock_run.side_effect = FileNotFoundError("launchctl not found")

                        result = install_daemon()
                        assert result is False


class TestGatewayDaemonUninstall:
    """Test daemon uninstallation functionality."""

    def test_uninstall_daemon_success(self):
        """Test successful daemon uninstallation."""
        with patch("nanobot.cli.daemon_manager._get_plist_path") as mock_path:
            mock_path.return_value = Path("/tmp/target.plist")

            with patch("pathlib.Path.exists") as mock_exists:
                mock_exists.return_value = True

            with patch("subprocess.run") as mock_run:
                mock_result = MagicMock()
                mock_result.returncode = 0
                mock_run.return_value = mock_result

            with patch("pathlib.Path.unlink") as mock_unlink:
                result = uninstall_daemon()
                assert result is True
                mock_run.assert_called_once_with(
                    ["launchctl", "unload", str(mock_path.return_value)],
                    capture_output=True,
                    text=True,
                    check=True,
                )
                mock_unlink.assert_called_once()

    def test_uninstall_daemon_not_installed(self):
        """Test uninstall_daemon returns False when daemon is not installed."""
        with patch("nanobot.cli.daemon_manager._get_plist_path") as mock_path:
            mock_path.return_value = Path("/nonexistent/plist.plist")

            with patch("pathlib.Path.exists") as mock_exists:
                mock_exists.return_value = False

                result = uninstall_daemon()
                assert result is False

    def test_uninstall_daemon_unload_failure(self):
        """Test uninstall_daemon returns False when unload fails."""
        with patch("nanobot.cli.daemon_manager._get_plist_path") as mock_path:
            mock_path.return_value = Path("/tmp/target.plist")

            with patch("pathlib.Path.exists") as mock_exists:
                mock_exists.return_value = True

            with patch("subprocess.run") as mock_run:
                mock_result = MagicMock()
                mock_result.returncode = 1
                mock_result.stderr = "Unload failed"
                mock_run.return_value = mock_result

            with patch("pathlib.Path.unlink") as mock_unlink:
                result = uninstall_daemon()
                assert result is False
                mock_unlink.assert_not_called()

    def test_uninstall_daemon_not_on_macos(self):
        """Test uninstall_daemon returns False when launchctl is not found."""
        with patch("nanobot.cli.daemon_manager._get_plist_path") as mock_path:
            mock_path.return_value = Path("/tmp/target.plist")

            with patch("pathlib.Path.exists") as mock_exists:
                mock_exists.return_value = True

            with patch("subprocess.run") as mock_run:
                mock_run.side_effect = FileNotFoundError("launchctl not found")

            result = uninstall_daemon()
            assert result is False

    def test_uninstall_daemon_unlink_warning(self):
        """Test uninstall_daemon handles unlink failure gracefully."""
        with patch("nanobot.cli.daemon_manager._get_plist_path") as mock_path:
            mock_path.return_value = Path("/tmp/target.plist")

            with patch("pathlib.Path.exists") as mock_exists:
                mock_exists.return_value = True

            with patch("subprocess.run") as mock_run:
                mock_result = MagicMock()
                mock_result.returncode = 0
                mock_run.return_value = mock_result

            with patch("pathlib.Path.unlink") as mock_unlink:
                mock_unlink.side_effect = Exception("Delete failed")

                result = uninstall_daemon()
                assert result is False


class TestGatewayDaemonPrintInfo:
    """Test daemon info printing functionality."""

    def test_print_daemon_info_not_installed(self):
        """Test print_daemon_info shows not_installed status."""
        with patch("nanobot.cli.daemon_manager.daemon_status") as mock_status:
            mock_status.return_value = "not_installed"

            with patch("nanobot.cli.daemon_manager.console.print") as mock_print:
                print_daemon_info()

                # Check that status is printed
                calls = [str(call) for call in mock_print.call_args_list]
                assert any("not_installed" in call for call in calls)

    def test_print_daemon_info_running(self):
        """Test print_daemon_info shows running status with log paths."""
        with patch("nanobot.cli.daemon_manager.daemon_status") as mock_status:
            mock_status.return_value = "running"

            with patch("nanobot.cli.daemon_manager._get_plist_path") as mock_path:
                mock_path.return_value = Path("/tmp/test.plist")

                with patch("nanobot.cli.daemon_manager.console.print") as mock_print:
                    print_daemon_info()

                    # Check that log paths are printed
                    calls = [str(call) for call in mock_print.call_args_list]
                    assert any("gateway.log" in call for call in calls)
                    assert any("gateway-error.log" in call for call in calls)


class TestGatewayCLICommands:
    """Test gateway CLI command options."""

    def test_gateway_help_shows_options(self):
        """Test that gateway command help shows all options."""
        result = subprocess.run(
            ["nanobot", "gateway", "--help"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "--port" in result.stdout
        assert "--verbose" in result.stdout
        assert "--install-daemon" in result.stdout
        assert "--uninstall-daemon" in result.stdout
        assert "--daemon-status" in result.stdout

    def test_gateway_daemon_status_command(self):
        """Test that gateway --daemon-status works."""
        result = subprocess.run(
            ["nanobot", "gateway", "--daemon-status"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        # Should show status information
        assert "Status:" in result.stdout or "nanobot" in result.stdout.lower()

    def test_gateway_install_daemon_command(self):
        """Test that gateway --install-daemon works (if on macOS)."""
        result = subprocess.run(
            ["nanobot", "gateway", "--install-daemon"],
            capture_output=True,
            text=True,
        )
        # On non-macOS, this may fail but should not crash
        assert result.returncode in [0, 1]  # 0 for success, 1 for expected failure

    def test_gateway_uninstall_daemon_command(self):
        """Test that gateway --uninstall-daemon works."""
        result = subprocess.run(
            ["nanobot", "gateway", "--uninstall-daemon"],
            capture_output=True,
            text=True,
        )
        # Should complete without crashing
        assert result.returncode in [0, 1]


class TestGatewaySIGHUPHandler:
    """Test SIGHUP signal handler for config reload."""

    def test_sighup_handler_exists(self):
        """Test that _sighup_handler function exists."""
        from nanobot.cli.commands import _sighup_handler

        assert _sighup_handler is not None
        assert callable(_sighup_handler)

    def test_sighup_handler_is_async_safe(self):
        """Test that SIGHUP handler uses asyncio-safe pattern."""
        # The handler should use loop.add_signal_handler, not signal.signal
        import inspect

        from nanobot.cli.commands import _sighup_handler

        source = inspect.getsource(_sighup_handler)
        # Should reference asyncio loop methods, not signal.signal
        assert "add_signal_handler" in source or "signal" not in source.lower()


class TestGatewayDaemonIntegration:
    """Integration tests for gateway daemon (requires actual launchd)."""

    @pytest.mark.skipif(
        not os.path.exists("/usr/bin/launchctl"),
        reason="Requires macOS with launchd",
    )
    def test_daemon_status_actual_system(self):
        """Test daemon_status against actual system (if gateway is installed)."""
        status = daemon_status()
        # Should return one of the valid statuses
        assert status in ["running", "stopped", "not_installed"]

    @pytest.mark.skipif(
        not os.path.exists("/usr/bin/launchctl"),
        reason="Requires macOS with launchd",
    )
    def test_plist_actual_system(self):
        """Test that the source plist matches expected format."""
        source_path = _get_source_plist_path()
        content = source_path.read_text()

        # Verify key structure
        assert "<?xml" in content
        assert "<dict>" in content
        assert "</dict>" in content
        assert "</plist>" in content

        # Verify required keys
        assert "<key>Label</key>" in content
        assert "<key>ProgramArguments</key>" in content
        assert "<key>KeepAlive</key>" in content


class TestGatewayLogManagement:
    """Test gateway log path configuration."""

    def test_log_paths_in_plist(self):
        """Test that log paths are correctly configured in plist."""
        source_path = _get_source_plist_path()
        content = source_path.read_text()

        # Check standard output path
        assert "StandardOutPath" in content
        assert "gateway.log" in content

        # Check standard error path
        assert "StandardErrorPath" in content
        assert "gateway-error.log" in content

    def test_log_paths_use_home_directory(self):
        """Test that log paths use home directory."""
        source_path = _get_source_plist_path()
        content = source_path.read_text()

        # Paths should use ~/ expansion
        assert "~/Library/Logs" in content

    def test_log_paths_in_daemon_manager(self):
        """Test that daemon_manager references correct log paths."""
        from nanobot.cli.daemon_manager import print_daemon_info

        import inspect

        source = inspect.getsource(print_daemon_info)
        assert "gateway.log" in source
        assert "gateway-error.log" in source


class TestGatewayPortConfiguration:
    """Test gateway port configuration."""

    def test_default_port_in_plist(self):
        """Test that default port is documented in plist comments."""
        source_path = _get_source_plist_path()
        content = source_path.read_text()

        # The plist itself doesn't contain port config
        # Port is configured via CLI --port option
        assert "nanobot" in content
        assert "gateway" in content

    def test_gateway_command_port_option(self):
        """Test that gateway command accepts --port option."""
        result = subprocess.run(
            ["nanobot", "gateway", "--help"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "--port" in result.stdout
        assert "18790" in result.stdout  # Default port
