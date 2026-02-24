# Cron Dispatch Behavior Analysis Report

**Date**: 2026-02-23  
**Investigation Target**: `/Users/mhall/Workspaces/nanobot/`

---

## 1. Cron Trigger

**What exactly triggers the cron handler? How often? Is it the main agent loop or a background thread?**

### Answer

The cron handler is triggered by a **background asyncio timer** managed by the `CronService` class in `nanobot/cron/service.py`. It is **not part of the main agent loop**, but rather a separate scheduled execution mechanism.

#### Trigger Mechanism
- **File**: `nanobot/cron/service.py`, lines 145–167
- The `_arm_timer()` method schedules a timer task based on the earliest `next_run_at_ms` across all enabled jobs
- When the timer expires, `_on_timer()` is invoked (lines 133–144)
- `_on_timer()` identifies "due jobs" and calls `_execute_job()` for each

#### Frequency
- For backlog dispatch, the cron job is configured via `run_dispatch.sh` in the `task-tracker` skill
- The interval is **15 minutes** based on the Task 18 description in BACKLOG.md
- The actual scheduling is defined in `cron/jobs.json` via the `every_ms` field

#### Execution Context
- Runs in a **background asyncio task** created by `_arm_timer()` (line 148–155)
- The callback (`on_job`) is invoked asynchronously (line 137–140 in `_execute_job`)
- The callback is set in `cli/commands.py` lines 381–397 for the gateway, and lines 983–993 for the `cron run` command

---

## 2. Dispatch Flow

**Walk through exactly what happens on a cron tick that finds a ready `[ ]` milestone. What reads happen, what writes happen, in what order?**

### Answer

The dispatch flow for a ready `[ ]` milestone involves **three coordinated scripts**:

### Step 1: Cron fires → `run_dispatch.sh` (lines 1–202)

**File**: `nanobot/skills/task-tracker/scripts/run_dispatch.sh`

#### Read Operations:
1. **Phase 1**: `review_backlog.py` reads `BACKLOG.md` and checks the registry (`subagents.db`)
2. **Phase 2**: Embedded Python script reads `BACKLOG.md` to find ready milestones

#### Write Operations (in order):
1. **`review_backlog.py`** (lines 1–100 in `review_backlog.py`):
   - Reads `BACKLOG.md` and `subagents.db`
   - Clears completed blockers (lines 35–49)
   - Resets orphaned `[~]` markers to `[ ]` (lines 52–69)
   - Writes updated `BACKLOG.md` if changes detected (line 75)

2. **`run_dispatch.sh` embedded script** (lines 41–202):
   - Scans milestones for `[ ]` marker with no blocker (lines 147–161)
   - When found, writes to `BACKLOG.md` to change `[ ]` → `[~]` (lines 171–184)
   - Prints `READY:<milestone_num>` and `TASK_BRIEF:<full milestone>` for main agent consumption

#### Timing Order:
```
1. review_backlog.py runs (clears stale markers, resets orphaned [~])
2. Find next ready [ ] milestone
3. Mark as [~] in BACKLOG.md
4. Output READY/TASK_BRIEF to stdout
```

### Step 2: Main agent consumes READY/TASK_BRIEF

**File**: `nanobot/agent/subagent.py` lines 281–357 (`_run_dispatch_script`)

- The `check_timeouts()` method (called periodically) triggers `_trigger_dispatch()`
- `_trigger_dispatch()` executes `run_dispatch.sh` and parses output
- If `READY:<num>` and `TASK_BRIEF:<text>` are found, it calls `spawn()`

### Step 3: Subagent registry tag-in

**File**: `nanobot/agent/subagent.py` lines 186–201 (`spawn()`)

#### Write Operations:
1. **Registry tag-in**: `self.registry.tag_in(task_id, label, origin_str)` (line 199)
   - Inserts row into `subagents` table with `status='pending'`
2. **Registry set_running**: `self.registry.set_running(task_id)` (line 354)
   - Called after first successful LLM response, updates `status='running'`
3. **Registry tag-out**: `self.registry.tag_out(task_id, status, result_summary)` (line 433)
   - Called on completion, updates `status='completed'` or `'failed'`

#### Backlog Update on Completion:
- Subagent completes → `_announce_result()` → `self._trigger_dispatch()` is called
- This triggers `run_dispatch.sh` again → `review_backlog.py` checks for completed subagents
- `review_backlog.py` marks `[~]` → `[x]` in `BACKLOG.md` (lines 39–52)

---

## 3. Duplicate Dispatch Risk

**If the cron fires twice before the first subagent registers in SQLite, can the same milestone be dispatched twice? What prevents this?**

### Answer

**YES, there is a duplicate dispatch risk** — the current implementation **does not fully prevent** double dispatch.

#### Root Cause (Lines 147–161 in `run_dispatch.sh`):
```python
for m in task['milestones']:
    milestone_num = m['number']

    # Skip if already in-progress (we just checked those)
    if m['status'] == '~':
        continue

    if m['status'] == ' ' and (not m.get('blocker') or m.get('blocker') == 'none'):
        # Found a ready milestone - mark it as [~] in BACKLOG.md
        ...
```

#### Race Condition:
1. **Cron fires at T=0**: `review_backlog.py` resets orphaned `[~]` markers to `[ ]`
2. **Cron finds ready `[ ]` milestone**: Marks it as `[~]` and outputs `READY`
3. **Subagent `spawn()` is called**: Calls `registry.tag_in()` → inserts row with `status='pending'`
4. **Cron fires again at T+15min**: If the first subagent hasn't completed yet:
   - `review_backlog.py` checks for active subagents (lines 10–25 in `review_backlog.py`)
   - If the subagent's label matches the milestone number, it's considered "active" (lines 18–23)
   - **BUT** the check only looks for `status IN ('running', 'pending')` — if the subagent is in `pending` state, it's active
   - **However**, if there's a timing window where the subagent hasn't reached `set_running()` yet (still `pending`), and the cron fires again, the subagent could be duplicated

#### Protection Mechanisms (Partial):
1. **Registry check in `review_backlog.py`** (lines 10–25):
   ```python
   def get_active_labels(db_path: Path) -> set[str]:
       if not db_path.exists():
           return set()
       try:
           conn = sqlite3.connect(str(db_path))
           rows = conn.execute(
               "SELECT label FROM subagents WHERE status IN ('running', 'pending')"
           ).fetchall()
           conn.close()
           return {row[0] for row in rows if row[0]}
       except Exception:
           return set()
   ```
   - This returns active labels for the "orphaned [~] reset" logic (lines 52–69)
   - **But this does NOT prevent dispatch** — it only prevents resetting `[~]` markers

2. **`run_dispatch.sh` skips `[~]` milestones** (line 149):
   ```python
   if m['status'] == '~':
       continue
   ```
   - This is the **only protection** — once marked `[~]`, the milestone is skipped
   - **Problem**: The `[~]` write happens **after** the registry tag-in, creating a window where:
     - Registry: `status='pending'` (exists)
     - BACKLOG: still `[ ]` (not yet written)
     - Cron fires → finds `[ ]` → dispatches duplicate

#### Conclusion:
The protection is **race-condition prone**. A cron fire during the tiny window between registry tag-in and BACKLOG `[~]` write can cause duplicate dispatch.

---

## 4. Stale Marker Reset

**The cron handler resets stale `[~]` markers to `[ ]`. What defines "stale"? Is this time-based, registry-based, or heuristic? Can a legitimate in-progress subagent get its marker reset?**

### Answer

**Stale is defined by registry state, not time**.

#### Definition of "Stale" (Lines 52–69 in `review_backlog.py`):
```python
# Rule 2: Reset orphaned [~] markers
lines = content.split("\n")
new_lines = []
for line in lines:
    m = re.match(r"(\s*- \[~\] )(\d+\.\d+)(.*)", line)
    if m:
        milestone_num = m.group(2)
        # Check if any active subagent label matches this milestone
        is_active = any(
            label == milestone_num or label.startswith(milestone_num)
            for label in active_labels
        )
        if not is_active:
            line = m.group(1).replace("[~]", "[ ]") + m.group(2) + m.group(3)
            orphans_reset += 1
    new_lines.append(line)
content = "\n".join(new_lines)
```

#### Stale Definition:
- A `[~]` milestone is **stale** if:
  1. Its milestone number (e.g., `7.3`) does **not match** any label in `subagents` table where `status IN ('running', 'pending')`
  2. Match is done via `label == milestone_num or label.startswith(milestone_num)`

#### Can a legitimate in-progress subagent get reset?
**YES, it can** — this is a **reliability gap**.

##### Scenario:
1. Subagent `spawn()` is called with label=`7.3`
2. `registry.tag_in()` inserts row with `label='7.3'`, `status='pending'`
3. **Gateway restart** or **DB corruption** occurs before `set_running()` is called
4. On restart, `SubagentRegistry.recover_on_startup()` marks all pending/running as `lost` (lines 48–58 in `registry.py`)
5. Now the subagent is `status='lost'` → **no longer in `active_labels`**
6. Next cron tick → `review_backlog.py` sees `[~] 7.3` with no active subagent → resets to `[ ]`
7. **Result**: `[~]` marker is reset even though the subagent was legitimate (just marked `lost`)

##### Another Scenario:
- Subagent completes successfully → `tag_out()` with `status='completed'`
- Next cron tick → `review_backlog.py` doesn't reset `[~]` because the subagent is `completed` (not in `active_labels`)
- But the milestone should remain `[~]` until manually marked `[x]`
- **This is handled by `run_dispatch.sh` lines 39–52**, which check for completed subagents and mark `[x]`

#### Conclusion:
- "Stale" = **no matching active subagent in registry**
- **Time-based** logic is NOT used in `review_backlog.py`
- A legitimate subagent **can** get its marker reset if it transitions to `lost` or `failed` state

---

## 5. Dispatch Skill vs. Cron Code

**The `dispatch/SKILL.md` defines a checklist. Is this checklist enforced in code, or is it only a prompt instruction? What happens when the main agent ignores it?**

### Answer

**The checklist in `SKILL.md` is ONLY a prompt instruction — it is NOT enforced in code.**

#### Evidence:
1. **File**: `nanobot/skills/dispatch/SKILL.md` (lines 1–56)
   - The file is a **skill definition** for the main agent, not a Python module
   - It contains instructions like "Always follow `references/dispatch-checklist.md` step by step"
   - There is **no Python code** that reads or enforces this checklist

2. **`dispatch-checklist.md` reference**:
   - `SKILL.md` line 22: "Always follow `references/dispatch-checklist.md` step by step"
   - But `references/` directory is not checked in this investigation
   - Even if it exists, it would be a **prompt instruction**, not an enforced constraint

3. **Cron handler (`run_dispatch.sh`) does not follow any checklist**:
   - It directly finds `[ ]` milestones and marks them `[~]`
   - No capacity check, no verification, no checklist steps

4. **Main agent loop does not call dispatch checklist**:
   - `SpawnTool.execute()` (lines 50–119 in `spawn.py`) calls `manager.spawn()` directly
   - No intermediate checklist enforcement

#### What happens when the main agent ignores it?
- **Nothing** — the checklist is advisory only
- The cron handler will dispatch milestones regardless of checklist compliance
- There are **no penalties** or **recovery actions** for ignoring the checklist

#### Conclusion:
- The dispatch checklist is a **human-readable instruction** for the main agent
- It is **not enforced** by any code
- Ignoring it has **no technical consequences** — only potential logical errors

---

## 6. Redundant State Management

**Is there any state managed in both the cron handler AND the main agent loop that could diverge? List specific variables/files.**

### Answer

**YES** — there are multiple state management points that could diverge.

#### 1. `BACKLOG.md` milestone markers vs. Registry state

| File | Cron Handler State | Main Agent State | Divergence Risk |
|------|-------------------|------------------|-----------------|
| `~/.nanobot/workspace/memory/BACKLOG.md` | Marks `[ ]` → `[~]` → `[x]` | Subagent writes `[x]` on completion | **HIGH** — if subagent fails to write `[x]`, cron may dispatch duplicate |
| `~/.nanobot/workspace/subagents.db` | `tag_in()`, `set_running()`, `tag_out()` | Same methods called | **LOW** — registry is authoritative |

**Divergence Scenario**:
- Subagent completes → `tag_out()` is called
- But `BACKLOG.md` is not updated to `[x]` (e.g., file permission error)
- Next cron tick → `run_dispatch.sh` finds `[~]` milestone
- `review_backlog.py` checks registry → subagent is `completed` (not in `active_labels`)
- Milestone is **not** reset to `[ ]` (correct behavior)
- But if `run_dispatch.sh` doesn't find the completed subagent, it won't mark `[x]`

#### 2. Running subagent count

| File | Cron Handler State | Main Agent State | Divergence Risk |
|------|-------------------|------------------|-----------------|
| `subagents.db` (count query) | `get_running_count()` in `spawn()` | `get_running_count()` in `check_timeouts()` | **LOW** — both use same DB |

**Note**: The capacity enforcement (max 3) is done via `get_running_count()` in both places:
- `spawn()` line 195: `count = self.registry.get_running_count()`
- `check_timeouts()` doesn't enforce capacity — it only checks timeouts

#### 3. Active milestone tracking

| File | Cron Handler State | Main Agent State | Divergence Risk |
|------|-------------------|------------------|-----------------|
| `~/.nanobot/workspace/memory/BACKLOG.md` | `run_dispatch.sh` writes `[~]` | Subagent doesn't track | **MEDIUM** — no bidirectional sync |

**Risk**: If `run_dispatch.sh` writes `[~]` but the subagent never starts (e.g., crash before spawn), the milestone remains `[~]` indefinitely.

#### 4. Time-based state

| File | Cron Handler State | Main Agent State | Divergence Risk |
|------|-------------------|------------------|-----------------|
| `subagents.db` timestamps | `spawned_at`, `started_at`, `completed_at` | Same fields | **LOW** — consistent |

#### Summary of Divergence Risks:
1. **HIGH**: `BACKLOG.md` marker state vs. subagent completion
   - Root cause: No atomicity between DB write and file write
   - Fix: Write to DB first, then BACKLOG.md; if BACKLOG.md write fails, roll back DB

2. **MEDIUM**: `[~]` marker orphaned if subagent fails to start
   - Root cause: No "subagent started" confirmation
   - Fix: Add `started_at` timestamp; reset `[~]` if no progress after timeout

3. **LOW**: Capacity count mismatch
   - Root cause: None — both use same DB

---

## 7. Failure Modes

### 7.1 Cron fires during gateway restart

**What happens?**

**File**: `nanobot/agent/registry.py` lines 48–58 (`recover_on_startup()`)

```python
def recover_on_startup(self) -> int:
    """Mark all pending/running rows as lost. Returns count of rows updated."""
    assert self._conn is not None
    now = datetime.now(UTC).isoformat()
    cursor = self._conn.execute(
        """
        UPDATE subagents
        SET status = 'lost', completed_at = ?
        WHERE status IN ('pending', 'running')
        """,
        (now,),
    )
    self._conn.commit()
    count = cursor.rowcount
    if count:
        logger.warning("SubagentRegistry: marked {} orphaned task(s) as lost on startup", count)
    return count
```

#### Behavior:
1. Gateway restart → `SubagentManager.__init__()` calls `self.registry.recover_on_startup()`
2. All `pending`/`running` subagents are marked `lost`
3. Next cron tick → `review_backlog.py` sees `lost` subagents (not in `active_labels`)
4. `[~]` markers with `lost` subagents are reset to `[ ]` (lines 52–69)

#### Impact:
- **No data loss** — subagent results are lost, but milestone markers are reset
- **Duplicate dispatch possible** — milestone is reset to `[ ]`, cron may dispatch again

---

### 7.2 BACKLOG.md is being written by main agent at same time cron reads it

**What happens?**

#### Behavior:
- `run_dispatch.sh` reads `BACKLOG.md` via `read_backlog()` (line 10–15 in `status.py`)
- Main agent may write `BACKLOG.md` via `edit_file` tool
- **No locking mechanism** exists between read/write

#### Potential Issues:
1. **Read during write**: Cron reads partially written file → parse errors
2. **Write during read**: File changes mid-parse → inconsistent state
3. **No atomic operations**: Both operations are non-atomic

#### Mitigation:
- The scripts use simple `read()` and `write()` — no file locking
- SQLite operations use `commit()` for atomicity, but file I/O is not atomic

#### Recommendation:
- Use file locking (e.g., `fcntl.flock()`) or SQLite-based state for coordination

---

### 7.3 Subagent completes but cron has already reset its `[~]` marker

**What happens?**

#### Scenario:
1. Subagent starts → `spawn()` → `registry.tag_in()` → `BACKLOG.md` `[ ]` → `[~]`
2. Cron fires at T+15min → `review_backlog.py` checks for active subagents
3. Subagent is `pending` (not yet `set_running()`) → not in `active_labels`
4. `review_backlog.py` resets `[~]` → `[ ]` (lines 52–69)
5. Cron finds `[ ]` milestone → dispatches **second** subagent
6. First subagent completes → `tag_out()` with `status='completed'`
7. Second subagent runs

#### Result:
- **Two subagents complete for the same milestone**
- Both are marked `completed` in registry
- `BACKLOG.md` should have `[x]` marker (handled by `run_dispatch.sh` lines 39–52)

#### Fix Required:
- Don't reset `[~]` if subagent exists in **any** state (including `lost`, `completed`)
- Only reset `[~]` if subagent is `lost` AND older than timeout threshold

---

## Gap Summary

### Top 3 Reliability Gaps

#### Gap 1: Duplicate Dispatch Risk (HIGH)

**Root Cause**: Race condition between registry `tag_in()` and `BACKLOG.md` `[~]` write

**Evidence**:
- `spawn()` writes to registry (line 199), then `run_dispatch.sh` writes `[~]` (line 181)
- Cron can fire in this window and find `[ ]` milestone again

**Suggested Fix**:
1. Write `[~]` marker **before** calling `tag_in()` in `spawn()`
2. Or use SQLite-based milestone state tracking (add `milestone_status` column)
3. Or add file locking around `BACKLOG.md` operations

---

#### Gap 2: Stale `[~]` Reset for Legitimate Subagents (HIGH)

**Root Cause**: `review_backlog.py` resets `[~]` if subagent is not in `active_labels`, but `lost`/`failed` subagents are excluded

**Evidence**:
- `review_backlog.py` lines 10–25 only query `status IN ('running', 'pending')`
- `recover_on_startup()` marks subagents as `lost` → not in `active_labels`
- Next cron tick resets `[~]` to `[ ]`

**Suggested Fix**:
1. Include `lost`/`failed` subagents in `active_labels` check
2. Or only reset `[~]` if subagent is older than timeout threshold
3. Or keep `[~]` marker until manually cleared (by user or after timeout)

---

#### Gap 3: No Atomicity Between Registry and BACKLOG.md (MEDIUM)

**Root Cause**: Registry writes use SQLite transactions, but `BACKLOG.md` writes are plain file I/O

**Evidence**:
- `tag_in()`, `tag_out()` use `commit()` for atomicity
- `run_dispatch.sh` writes `BACKLOG.md` with no transaction
- If `BACKLOG.md` write fails, registry is updated but marker is not

**Suggested Fix**:
1. Add `milestone_status` column to `subagents` table
2. Query registry for milestone status instead of parsing `BACKLOG.md`
3. Or use atomic file write (write to temp, then rename)

---

### Additional Gaps

#### Gap 4: No Dispatch Checklist Enforcement (LOW)

**Root Cause**: Checklist is only in `SKILL.md`, not enforced in code

**Suggested Fix**:
1. Convert checklist to Python validation function
2. Call it in `SpawnTool.execute()` before dispatch
3. Log warnings or reject dispatch if checklist fails

---

#### Gap 5: No File Locking for BACKLOG.md (MEDIUM)

**Root Cause**: Multiple processes read/write `BACKLOG.md` without coordination

**Suggested Fix**:
1. Implement file locking via `fcntl.flock()`
2. Or use SQLite-based milestone state (see Gap 3)

---

## Final Recommendations

1. **Immediate**: Add file locking around `BACKLOG.md` operations
2. **Short-term**: Include `lost`/`failed` subagents in `[~]` reset logic
3. **Medium-term**: Add `milestone_status` column to registry for atomic state
4. **Long-term**: Enforce dispatch checklist via code validation
