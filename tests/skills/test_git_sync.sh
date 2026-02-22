#!/usr/bin/env bash
set -euo pipefail

# Test script for git_sync.sh
# This creates a temporary git repo and tests the script logic
# without modifying the real nanobot repository

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_SCRIPT="$SCRIPT_DIR/../../nanobot/skills/git-sync/git_sync.sh"
TEST_DIR=$(mktemp -d)

cleanup() {
  echo "Cleaning up temporary directory: $TEST_DIR"
  rm -rf "$TEST_DIR"
}
trap cleanup EXIT

echo "=== Git Sync Test Suite ==="
echo "Test directory: $TEST_DIR"
echo ""

# Test 1: No changes scenario
echo "--- Test 1: No changes to commit ---"
cd "$TEST_DIR"
git init -q
git config user.email "test@example.com"
git config user.name "Test User"

# Create an initial commit
echo "Initial content" > file.txt
git add file.txt
git commit -q -m "Initial commit"

# Run script with GIT_SYNC_REPO override
GIT_SYNC_REPO="$TEST_DIR" bash "$SKILL_SCRIPT"
result=$?

if [[ $result -eq 0 ]]; then
  echo "✓ Test 1 PASSED: Script exited 0 with no changes"
else
  echo "✗ Test 1 FAILED: Script exited with code $result"
  exit 1
fi
echo ""

# Test 2: Changes detected scenario
echo "--- Test 2: Changes detected and committed ---"
cd "$TEST_DIR"

# Make a change
echo "Modified content" > file.txt
echo "New file" > newfile.txt

# Run script with GIT_SYNC_REPO override and GIT_SYNC_NO_PUSH=1 to skip push
output=$(GIT_SYNC_REPO="$TEST_DIR" GIT_SYNC_NO_PUSH=1 bash "$SKILL_SCRIPT" 2>&1)
result=$?

if [[ $result -ne 0 ]]; then
  echo "✗ Test 2 FAILED: Script exited with code $result"
  echo "Output: $output"
  exit 1
fi

# Check that commit message was generated
if echo "$output" | grep -q "auto-sync:"; then
  echo "✓ Commit message generated correctly"
else
  echo "✗ Test 2 FAILED: No auto-sync commit message found"
  echo "Output: $output"
  exit 1
fi

# Verify the new file was committed (should appear in git log)
cd "$TEST_DIR"
if git show --name-only HEAD | grep -q "newfile.txt"; then
  echo "✓ Test 2 PASSED: New file was committed"
else
  echo "✗ Test 2 FAILED: New file was not committed"
  echo "git log:"
  git log --oneline -3
  exit 1
fi
echo ""

# Test 3: Multiple changes scenario
echo "--- Test 3: Multiple changes with proper summary ---"
cd "$TEST_DIR"

# Create multiple changes
echo "Changed 1" > file1.txt
echo "Changed 2" > file2.txt
echo "Changed 3" > file3.txt

output=$(GIT_SYNC_REPO="$TEST_DIR" GIT_SYNC_NO_PUSH=1 bash "$SKILL_SCRIPT" 2>&1)
result=$?

if [[ $result -eq 0 ]]; then
  echo "✓ Test 3 PASSED: Multiple changes handled correctly"
else
  echo "✗ Test 3 FAILED: Script exited with code $result"
  echo "Output: $output"
  exit 1
fi

# Verify summary contains at least one of the changed files
if echo "$output" | grep -qE "file[123]\.txt"; then
  echo "✓ Test 3 PASSED: Summary includes changed files"
else
  echo "✗ Test 3 FAILED: Summary does not include changed files"
  echo "Output: $output"
  exit 1
fi
echo ""

# Test 4: Verify script is idempotent (second run should show no changes)
echo "--- Test 4: Idempotency check ---"
cd "$TEST_DIR"

output=$(GIT_SYNC_REPO="$TEST_DIR" GIT_SYNC_NO_PUSH=1 bash "$SKILL_SCRIPT" 2>&1)
result=$?

if [[ $result -eq 0 ]] && echo "$output" | grep -q "No changes to commit"; then
  echo "✓ Test 4 PASSED: Script is idempotent"
else
  echo "✗ Test 4 FAILED: Script should show no changes on second run"
  echo "Output: $output"
  exit 1
fi
echo ""

echo "=== All Tests Passed ==="
echo ""
echo "Summary:"
echo "- Test 1: No changes scenario ✓"
echo "- Test 2: Changes detected and committed ✓"
echo "- Test 3: Multiple changes with proper summary ✓"
echo "- Test 4: Idempotency check ✓"
echo ""
echo "Note: The real nanobot repository at /Users/mhall/Workspaces/nanobot was not modified."
