#!/usr/bin/env bash
# lint-fix.sh — Run ruff, capture violations, spawn nanobot subagent to fix them
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

echo "=== Running ruff check ==="
RUFF_OUTPUT=$(python3 -m ruff check nanobot/ tests/ 2>&1 || true)

if [ -z "$RUFF_OUTPUT" ] || echo "$RUFF_OUTPUT" | grep -q "All checks passed"; then
    echo "✅ No lint violations found."
    exit 0
fi

echo "=== Violations found ==="
echo "$RUFF_OUTPUT"

echo ""
echo "=== Spawning nanobot agent to fix violations ==="

# Build the task brief for the subagent
TASK_BRIEF="You are fixing ruff lint violations in the nanobot project at $REPO_ROOT.

Here are the violations to fix:

\`\`\`
$RUFF_OUTPUT
\`\`\`

Rules:
- Fix each violation explicitly — do NOT run ruff --fix (no autofix)
- After fixing, run: python3 -m ruff check nanobot/ tests/ to confirm clean
- Then run: python3 -m pytest tests/ -x -q -k 'not integration' --tb=short to confirm tests pass
- Report the result of both commands"

# Use nanobot CLI to spawn a subagent if available, otherwise print instructions
if command -v nanobot &>/dev/null; then
    nanobot run --model qwen3-coder-next "$TASK_BRIEF"
else
    echo ""
    echo "=== nanobot CLI not available — paste the following task to a subagent ==="
    echo "$TASK_BRIEF"
fi
