# log-watcher Skill

Monitor the nanobot gateway log file for WARNING and ERROR events. Alert on Discord and maintain a rolling history.

## Usage

```bash
python3 nanobot/skills/log-watcher/scripts/run_watcher.py --log-file <path> [--history-file <path>]
```

## Components

- `log_watcher.py` — watchdog-based file monitor with log line parsing
- `log_history.py` — rolling JSON history store (last 500 events)
- `discord_alert.py` — sends Discord alerts for ERROR/CRITICAL events
- `run_watcher.py` — CLI entry point, wires all components together

## Log Format

Expects loguru-formatted lines:
```
2026-02-22 14:30:00.123 | ERROR    | nanobot.agent.loop:_process_message:589 - Error message here
```

## History File

Stored at `~/.nanobot/workspace/log_history.json` by default. Keeps last 500 entries.

## Alert Rate Limiting

Max 1 Discord alert per error type per 5 minutes to prevent flooding.