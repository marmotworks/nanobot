#!/usr/bin/env bash
# gateway_ctl.sh — nanobot gateway management
set -euo pipefail

COMMAND="${1:-status}"

case "$COMMAND" in
  start)
    nanobot gateway &
    echo "Gateway started (PID $!)"
    ;;
  stop)
    pkill -f "nanobot gateway" && echo "Gateway stopped" || echo "Gateway not running"
    ;;
  restart)
    pkill -f "nanobot gateway" 2>/dev/null || true
    sleep 1
    nanobot gateway &
    echo "Gateway restarted (PID $!)"
    ;;
  status)
    if pgrep -f "nanobot gateway" > /dev/null; then
      PID=$(pgrep -f "nanobot gateway")
      echo "Gateway running (PID $PID)"
    else
      echo "Gateway not running"
    fi
    ;;
  install-daemon)
    nanobot gateway --install-daemon
    ;;
  uninstall-daemon)
    nanobot gateway --uninstall-daemon
    ;;
  daemon-status)
    nanobot gateway --daemon-status
    ;;
  logs)
    LOG_FILE="${2:-}"
    if [ -z "$LOG_FILE" ]; then
      # Try to find the log file
      LOG_FILE=$(find ~/.nanobot -name "*.log" 2>/dev/null | head -1)
    fi
    if [ -n "$LOG_FILE" ] && [ -f "$LOG_FILE" ]; then
      tail -50 "$LOG_FILE"
    else
      echo "No log file found. Check ~/.nanobot/ for log files."
    fi
    ;;
  *)
    echo "Usage: gateway_ctl.sh {start|stop|restart|status|install-daemon|uninstall-daemon|daemon-status|logs [logfile]}"
    exit 1
    ;;
esac
