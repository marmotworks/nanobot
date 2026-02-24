#!/usr/bin/env bash
# gateway_ctl.sh — control the nanobot gateway process
# Usage: gateway_ctl.sh <command>
# Commands: start, stop, restart, status, reload, install-daemon, uninstall-daemon, daemon-status, logs

set -euo pipefail

COMMAND="${1:-status}"
LOG_FILE="$HOME/.nanobot/gateway.log"
PID_FILE="$HOME/.nanobot/gateway.pid"

case "$COMMAND" in
  start)
    if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
      echo "Gateway already running (PID $(cat "$PID_FILE"))"
      exit 0
    fi
    nohup nanobot gateway >> "$LOG_FILE" 2>&1 &
    echo $! > "$PID_FILE"
    echo "Gateway started (PID $!)"
    ;;
  stop)
    if [ -f "$PID_FILE" ]; then
      PID=$(cat "$PID_FILE")
      if kill -0 "$PID" 2>/dev/null; then
        kill "$PID"
        rm -f "$PID_FILE"
        echo "Gateway stopped (PID $PID)"
      else
        echo "Gateway not running (stale PID file removed)"
        rm -f "$PID_FILE"
      fi
    else
      echo "Gateway not running (no PID file)"
    fi
    ;;
  restart)
    "$0" stop
    sleep 1
    "$0" start
    ;;
  reload)
    if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
      kill -HUP "$(cat "$PID_FILE")"
      echo "SIGHUP sent to gateway (PID $(cat "$PID_FILE")) — config reloaded"
    else
      echo "Gateway not running"
      exit 1
    fi
    ;;
  status)
    if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
      echo "Gateway running (PID $(cat "$PID_FILE"))"
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
    tail -f "$LOG_FILE"
    ;;
  *)
    echo "Unknown command: $COMMAND"
    echo "Usage: gateway_ctl.sh <start|stop|restart|reload|status|install-daemon|uninstall-daemon|daemon-status|logs>"
    exit 1
    ;;
esac
