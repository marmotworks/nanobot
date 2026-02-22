#!/usr/bin/env bash
set -euo pipefail

# Use GIT_SYNC_REPO env variable if set, otherwise use default
REPO="${GIT_SYNC_REPO:-/Users/mhall/Workspaces/nanobot}"

cd "$REPO"

# Check for changes
changes=$(git status --porcelain)

if [[ -z "$changes" ]]; then
  echo "No changes to commit."
  exit 0
fi

echo "Changes detected. Committing and pushing..."

# Gather summary of changes
diff_stat=$(git diff --stat HEAD)
short_status=$(git status --short)

# Generate commit message
date_str=$(date +%Y-%m-%d)

# Extract changed files for summary
# Get unique file paths from status, sort them, and join with comma
changed_files=$(echo "$short_status" | awk '{
    # Remove leading characters and get file path
    gsub(/^[AMDRC?]{2} +/, "", $0)
    print $0
  }' | sort -u | tr '\n' ',' | sed 's/,$//')

# Truncate if too long
if [[ ${#changed_files} -gt 80 ]]; then
  changed_files="${changed_files:0:77}..."
fi

commit_message="auto-sync: ${date_str} — ${changed_files}"

echo "Commit message: ${commit_message}"
echo ""
echo "Diff summary:"
echo "$diff_stat"
echo ""

# Stage all changes
git add -A

# Commit
commit_output=$(git commit -m "$commit_message")
commit_hash=$(echo "$commit_output" | grep -oE '^\[.* [a-f0-9]{7}\]' | head -1 | awk '{print $2}' | tr -d ']')

echo "Committed: $commit_hash"

# Push (skip if GIT_SYNC_NO_PUSH is set, e.g. during testing)
if [[ "${GIT_SYNC_NO_PUSH:-}" == "1" ]]; then
  echo "Successfully committed changes (push skipped)."
  exit 0
fi

if git push; then
  echo "Successfully synced changes."
  exit 0
else
  echo "Failed to push changes." >&2
  exit 1
fi
