"""Gateway daemon management for macOS launchd."""

from pathlib import Path
import shutil
import subprocess

from rich.console import Console

console = Console()
EXIT_COMMANDS = {"exit", "quit", "/exit", "/quit", ":q"}


def _get_plist_path() -> Path:
    """Get the launchd plist path in user LaunchAgents directory."""
    return Path.home() / "Library" / "LaunchAgents" / "com.nanobot.gateway.plist"


def _get_source_plist_path() -> Path:
    """Get the source plist path in the nanobot package."""
    # Source plist is in nanobot/cli/launchd/
    return Path(__file__).parent / "launchd" / "com.nanobot.gateway.plist"


def install_daemon() -> bool:
    """Install the nanobot gateway as a launchd daemon.

    Returns:
        True if installation succeeded, False otherwise.
    """
    source_plist = _get_source_plist_path()
    target_plist = _get_plist_path()

    if not source_plist.exists():
        console.print(f"[red]Source plist not found: {source_plist}[/red]")
        return False

    # Create LaunchAgents directory if needed
    target_plist.parent.mkdir(parents=True, exist_ok=True)

    # Copy plist to target location
    try:
        shutil.copy2(source_plist, target_plist)
        console.print(f"[green]✓[/green] Plist copied to {target_plist}")
    except Exception as e:
        console.print(f"[red]Failed to copy plist: {e}[/red]")
        return False

    # Load the daemon with launchctl
    try:
        subprocess.run(
            ["launchctl", "load", str(target_plist)],
            capture_output=True,
            text=True,
            check=True,
        )
        console.print("[green]✓[/green] Daemon loaded with launchctl")
        return True
    except subprocess.CalledProcessError as e:
        console.print(f"[red]Failed to load daemon: {e.stderr}[/red]")
        return False
    except FileNotFoundError:
        console.print("[red]launchctl not found. This tool only works on macOS.[/red]")
        return False


def uninstall_daemon() -> bool:
    """Uninstall the nanobot gateway launchd daemon.

    Returns:
        True if uninstallation succeeded, False otherwise.
    """
    target_plist = _get_plist_path()

    if not target_plist.exists():
        console.print("[yellow]Daemon not installed[/yellow]")
        return False

    # Unload the daemon with launchctl
    try:
        subprocess.run(
            ["launchctl", "unload", str(target_plist)],
            capture_output=True,
            text=True,
            check=True,
        )
        console.print("[green]✓[/green] Daemon unloaded with launchctl")
    except subprocess.CalledProcessError as e:
        console.print(f"[red]Failed to unload daemon: {e.stderr}[/red]")
        return False
    except FileNotFoundError:
        console.print("[red]launchctl not found. This tool only works on macOS.[/red]")
        return False

    # Remove the plist file
    try:
        target_plist.unlink()
        console.print(f"[green]✓[/green] Plist removed from {target_plist}")
    except Exception as e:
        console.print(f"[yellow]Warning: Failed to remove plist: {e}[/yellow]")
        return False

    return True


def daemon_status() -> str:
    """Check the status of the nanobot gateway daemon.

    Returns:
        Status string: 'running', 'stopped', or 'not_installed'.
    """
    target_plist = _get_plist_path()

    if not target_plist.exists():
        return "not_installed"

    try:
        result = subprocess.run(
            ["launchctl", "list", "com.nanobot.gateway"],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            return "running"
        else:
            return "stopped"
    except FileNotFoundError:
        return "unknown"


def print_daemon_info():
    """Print information about the daemon setup."""
    from nanobot import __logo__

    console.print(f"{__logo__} nanobot Gateway Daemon\n")

    status = daemon_status()
    console.print(f"Status: [bold]{status}[/bold]\n")

    if status != "not_installed":
        target_plist = _get_plist_path()
        console.print(f"Plist location: {target_plist}")

        # Show log paths
        console.print("\nLog paths:")
        console.print("  Standard output: ~/Library/Logs/nanobot/gateway.log")
        console.print("  Standard error:  ~/Library/Logs/nanobot/gateway-error.log")
