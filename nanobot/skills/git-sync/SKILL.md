---
name: git-sync
description: Automatically sync changes to the nanobot repository by staging committing, and pushing.
---

# Git Sync

Automatically sync changes to the nanobot repository. This skill checks for changes, stages all files, generates a meaningful commit message, commits, and pushes to GitHub.

## What It Does

1. Checks git status of `/Users/mhall/Workspaces/nanobot`
2. If there are changes:
   - Gathers a summary of what changed
   - Generates a commit message in format: `auto-sync: <date> — <short summary>`
   - Stages all files with `git add -A`
   - Commits with the generated message
   - Pushes to GitHub
3. If no changes exist, prints "No changes to commit." and exits successfully

## How to Invoke

Run the script manually:

```bash
bash nanobot/skills/git-sync/git_sync.sh
```

Or invoke via the agent:

```bash
exec(action="bash", command="bash nanobot/skills/git-sync/git_sync.sh")
```

## Output

The script outputs:
- "No changes to commit." when there are no changes (exit 0)
- "Changes detected. Committing and pushing..." followed by git diff stats
- "Successfully synced changes." with commit hash on success (exit 0)
- Error messages with exit code on failure (exit non-zero)

## Scheduling with Cron

Use the cron skill to schedule automatic syncs. Example cron expressions:

### Every 15 minutes
```
cron(action="add", message="Run git-sync to auto-sync changes", every_seconds=900)
```

### Every hour at the start
```
cron(action="add", message="Run git-sync to auto-sync changes", cron_expr="0 * * * *")
```

### Daily at 9am
```
cron(action="add", message="Run git-sync to auto-sync changes", cron_expr="0 9 * * *")
```

### Weekdays at 5pm
```
cron(action="add", message="Run git-sync to auto-sync changes", cron_expr="0 17 * * 1-5")
```

## Example Usage

### Manual Invocation
```bash
bash nanobot/skills/git-sync/git_sync.sh
```

### Check Output
After running, verify the sync:
```bash
cd /Users/mhall/Workspaces/nanobot && git log --oneline -3
```

## Environment Variables

The script respects `GIT_SYNC_REPO` environment variable. Set this to override the default repo path:

```bash
GIT_SYNC_REPO=/path/to/custom/repo bash nanobot/skills/git-sync/git_sync.sh
```

## Requirements

- Git must be installed and available in PATH
- The nanobot repo must be a valid git repository
- SSH keys or credentials must be configured for GitHub push access
