---
name: gateway
description: Manage the nanobot gateway process — start, stop, restart, check status, reload config (SIGHUP), install/uninstall as a launchd daemon, and tail logs. Use when the user asks to start/stop/restart the gateway, check if it's running, reload config without restarting, install it as a background service, or view gateway logs.
---

# Gateway Control

## Quick Reference

| What | Command |
|------|---------|
| Start gateway | `gateway_ctl.sh start` |
| Stop gateway | `gateway_ctl.sh stop` |
| Restart gateway | `gateway_ctl.sh restart` |
| Check status | `gateway_ctl.sh status` |
| Reload config (no restart) | `gateway_ctl.sh reload` |
| Install as launchd daemon | `gateway_ctl.sh install-daemon` |
| Uninstall daemon | `gateway_ctl.sh uninstall-daemon` |
| Check daemon status | `gateway_ctl.sh daemon-status` |
| Tail logs | `gateway_ctl.sh logs` |

## Script Location
`/Users/mhall/Workspaces/nanobot/nanobot/skills/gateway/scripts/gateway_ctl.sh`

## Notes
- PID file: `~/.nanobot/gateway.pid`
- Log file: `~/.nanobot/gateway.log`
- SIGHUP (`reload`) re-reads config and reconnects channels without full restart
- `install-daemon` uses launchd (`~/Library/LaunchAgents/com.nanobot.gateway.plist`) with `KeepAlive: true` for auto-restart on crash
- After code changes, use `restart` (not `reload`) to pick up new Python code
