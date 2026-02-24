# Task 39: Fix Double-Message on Subagent Completion

## Problem

When a subagent completes, two messages are sent to Discord:

1. `_announce_result` in `subagent.py` publishes an `InboundMessage` to the bus with `channel="system"`.
2. `loop.py` `_process_message` receives that system message, runs the LLM, and returns an `OutboundMessage` back to the origin channel (Discord).

That `OutboundMessage` is the **main agent's response** — the one the user should see.

**But `_announce_result` also sends the "Suggested summary" line directly via `announce_content`** — which gets delivered as a second, separate message.

Wait — actually re-read the flow:

```
_announce_result publishes InboundMessage(channel="system", chat_id="discord:1234", content=announce_content)
    → bus delivers to loop._process_message
    → loop runs LLM with announce_content (which includes "Suggested summary: ...")
    → loop returns OutboundMessage(channel="discord", chat_id="1234", content=<LLM response>)
    → that OutboundMessage is sent to Discord ✅ (this is the one message we want)
```

So the `announce_content` is the *input* to the LLM — not a separate outbound message itself. The LLM sees "Suggested summary: X" as a hint and uses it to craft its reply.

**The real bug**: The `announce_content` includes:
```
Summarize this naturally for the user. Keep it brief (1-2 sentences). Do not mention technical details like "subagent" or task IDs.

Suggested summary: {narrative}
```

This instructs the LLM to summarize — and the LLM does. That's ONE message to Discord.

But the user is seeing TWO messages. The second one is likely coming from somewhere else. Possible causes:

1. **`_trigger_dispatch`** fires after completion — does it cause a second message?
2. **The cron job** fires independently and also processes the completion?
3. **`_announce_result` is called twice** (once for ok, once in finally block)?
4. **The `message` tool** is being called by the main agent as part of its response (the LLM decides to call `message` in addition to returning text)?

## Investigation Steps

### Step 1: Read the full `_run_subagent` method
```bash
sed -n '560,770p' /Users/mhall/Workspaces/nanobot/nanobot/agent/subagent.py
```

Look for:
- Is `_announce_result` called more than once?
- Is there any other outbound message path?
- What does `_trigger_dispatch` do?

### Step 2: Read `_announce_result` fully
```bash
sed -n '763,820p' /Users/mhall/Workspaces/nanobot/nanobot/agent/subagent.py
```

### Step 3: Read `loop.py` system message handling
```bash
sed -n '430,470p' /Users/mhall/Workspaces/nanobot/nanobot/agent/loop.py
```

Look for: does `_process_message` for system messages ALSO publish an outbound message via the bus? Or does it return it?

### Step 4: Read how the gateway delivers outbound messages
```bash
grep -n "publish_outbound\|OutboundMessage\|on_outbound\|send_message" /Users/mhall/Workspaces/nanobot/nanobot/agent/loop.py | head -20
grep -n "publish_outbound\|OutboundMessage\|on_outbound" /Users/mhall/Workspaces/nanobot/nanobot/channels/manager.py | head -20
```

### Step 5: Check if the main agent calls `message` tool
Look at whether the LLM's response to the subagent completion notification includes a `message` tool call AND a text response — both of which get delivered.

```bash
grep -n "MessageTool\|message.*tool\|send.*message" /Users/mhall/Workspaces/nanobot/nanobot/agent/loop.py | head -20
grep -rn "class MessageTool" /Users/mhall/Workspaces/nanobot/nanobot/
```

### Step 6: Check dispatch_runner
```bash
cat /Users/mhall/Workspaces/nanobot/nanobot/skills/dispatch/scripts/dispatch_runner.py
```

Does `dispatch_runner` trigger any message delivery?

## Expected Root Cause

Most likely: the LLM agent, when responding to the subagent completion notification, **both**:
1. Returns a text response (which gets sent to Discord as the `OutboundMessage`)
2. Calls the `message` tool (which ALSO sends a message to Discord)

The fix would be: when the main agent is responding to a `[System: subagent]` message, suppress `MessageTool` calls (or ignore them), since the text response is already being delivered.

## Fix Strategy

Once root cause is confirmed, implement the minimal fix:

**Option A** (if LLM is calling `message` tool): In `_process_message` for system messages, temporarily remove `MessageTool` from the tool registry before running the agent loop, then restore it after.

**Option B** (if `_announce_result` is called twice): Remove the duplicate call.

**Option C** (if dispatch_runner causes a second delivery): Suppress outbound delivery in dispatch_runner context.

## Files to Read First
1. `nanobot/agent/subagent.py` — full `_run_subagent` and `_announce_result`
2. `nanobot/agent/loop.py` — system message handling + tool registration
3. `nanobot/agent/tools/message.py` (if it exists) — MessageTool implementation
4. `nanobot/skills/dispatch/scripts/dispatch_runner.py`

## Verification
After fix:
```bash
cd /Users/mhall/Workspaces/nanobot
python3 -m pytest tests/ -q -k "not integration" --timeout=30 2>&1 | tail -5
python3 -m ruff check nanobot/agent/subagent.py nanobot/agent/loop.py
```
Expected: 850+ passed, ruff clean.

## Code Style
- Double quotes everywhere
- Type annotations on all functions
- Do NOT use ruff --fix
- Follow existing patterns in subagent.py and loop.py

## Report
- Root cause identified (which option A/B/C)
- Fix applied
- Ruff clean
- Tests passing
- PASS or FAIL
