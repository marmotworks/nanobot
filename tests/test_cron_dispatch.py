"""
Tests for dispatching milestone markers.

Tests verify that:
1. check_readiness.py correctly handles [~] markers (in-progress, not blockers)
2. verify_dispatch.py correctly identifies stale [~] markers
"""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch


def test_marks_in_progress(tmp_path: Path) -> None:
    """Verify that [~] markers in BACKLOG.md are preserved by check_readiness.py.

    A milestone marked [~] is in-progress, not a blocker, so it should NOT be
    cleared or reset to [ ] by the readiness check.
    """
    # Create temp BACKLOG.md with a milestone marked [~]
    backlog_path = tmp_path / "memory" / "BACKLOG.md"
    backlog_path.parent.mkdir(parents=True)
    backlog_content = """## Task 1: Sample task

Status: In progress

Blocker: none

- [ ] 1.1 Not started milestone
- [~] 1.2 In progress milestone
- [x] 1.3 Complete milestone
"""
    backlog_path.write_text(backlog_content)

    # Call check_readiness.py via subprocess with BACKLOG_PATH env var
    script_path = Path(__file__).parent.parent / "nanobot" / "skills" / "task-tracker" / "scripts" / "check_readiness.py"
    env = os.environ.copy()
    env["BACKLOG_PATH"] = str(backlog_path)

    import subprocess
    subprocess.run(
        ["python3", str(script_path)],
        env=env,
        capture_output=True,
        text=True,
    )

    # Verify [~] marker is unchanged (script should not modify in-progress milestones)
    result_content = backlog_path.read_text()
    assert "[~] 1.2 In progress milestone" in result_content
    assert "[ ] 1.2" not in result_content


def test_skips_in_progress(tmp_path: Path) -> None:
    """Verify that verify_dispatch.py identifies [~] milestones with no subagent as STALE.

    A milestone marked [~] without an active subagent should result in exit code 1.
    """
    # Create temp BACKLOG.md with a milestone marked [~]
    backlog_path = tmp_path / "memory" / "BACKLOG.md"
    backlog_path.parent.mkdir(parents=True)
    backlog_content = """## Task 1: Sample task

Status: In progress

Blocker: none

- [~] 1.2 In progress milestone with no subagent
"""
    backlog_path.write_text(backlog_content)

    # Create empty DB
    db_path = tmp_path / "subagents.db"
    db_path.touch()

    # Monkeypatch Path.home() to return temp path
    def mock_home() -> Path:
        return tmp_path

    # Import verify_dispatch and run main
    from nanobot.skills.dispatch.scripts import verify_dispatch

    with patch.object(Path, "home", side_effect=mock_home):
        result = verify_dispatch.main()

    # Verify exit code is 1 (stale marker detected)
    assert result == 1
