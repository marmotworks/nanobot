---
name: gateway-ctl
description: Manage the nanobot gateway process — start, stop, restart, check status, install/uninstall as a launchd daemon, and tail logs. Use when the user asks to restart the gateway, check if it's running, install the daemon, or view gateway logs.
---

# Gateway Control

## Quick Reference

| Action | Command |
|--------|---------|
| Check status | `bash nanobot/skills/gateway-ctl/scripts/gateway_ctl.sh status` |
| Start | `bash nanobot/skills/gateway-ctl/scripts/gateway_ctl.sh start` |
| Stop | `bash nanobot/skills/gateway-ctl/scripts/gateway_ctl.sh stop` |
| Restart | `bash nanobot/skills/gateway-ctl/scripts/gateway_ctl.sh restart` |
| Install daemon | `bash nanobot/skills/gateway-ctl/scripts/gateway_ctl.sh install-daemon` |
| Uninstall daemon | `bash nanobot/skills/gateway-ctl/scripts/gateway_ctl.sh uninstall-daemon` |
| Daemon status | `bash nanobot/skills/gateway-ctl/scripts/gateway_ctl.sh daemon-status` |
| Tail logs | `bash nanobot/skills/gateway-ctl/scripts/gateway_ctl.sh logs` |

## Notes

- The gateway runs as `nanobot gateway` — the script uses `pgrep`/`pkill` to find it.
- Daemon management uses launchd (`~/Library/LaunchAgents/com.nanobot.gateway.plist`) via `nanobot gateway --install-daemon`.
- When the daemon is installed, launchd auto-restarts the gateway on crash. Use `daemon-status` to check.
- The `start` and `restart` commands launch the gateway in the background. For production use, prefer the daemon.
- Log files are in `~/.nanobot/` — use `logs` to tail the most recent one.
- After code changes, use `restart` to pick up the new code (gateway runs in editable install mode).
