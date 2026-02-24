# Task: Fix MiniMax M2.1 Reasoning Content Leak in bedrock_provider.py

## Problem

When using `minimax.minimax-m2.1` via AWS Bedrock, the model's internal reasoning
(chain-of-thought) is leaking into the final response sent to Discord.

## Root Cause (Confirmed)

In `nanobot/providers/bedrock_provider.py`, the `_parse_response` method has a buggy
fallback in the `elif "reasoningContent"` branch:

```python
elif "reasoningContent" in block:
    reasoning = block["reasoningContent"]
    # Use reasoning text as fallback if no text block found yet
    if not text_parts:                          # ← ALWAYS True — reasoning comes first
        thinking = reasoning.get("reasoningText", {})
        text = thinking.get("text") if isinstance(thinking, dict) else None
        if text:
            text_parts.append(text)             # ← reasoning gets added to output
```

MiniMax M2.1 **always** returns `reasoningContent` before the `text` block:
```json
"content": [
  { "reasoningContent": { "reasoningText": { "text": "I should say Hello." } } },
  { "text": "Hello" }
]
```

So `if not text_parts` is always `True` when the reasoning block is encountered,
causing the reasoning to be appended first — then the actual `text` block is appended
after it. Both end up in the output.

## The Fix

Replace the `elif "reasoningContent"` branch with a simple `pass`. Reasoning content
is **never** user-visible. If there's no `text` block at all, return `None` — do NOT
fall back to reasoning.

### Exact change in `_parse_response`:

**Before:**
```python
elif "reasoningContent" in block:
    reasoning = block["reasoningContent"]
    # Use reasoning text as fallback if no text block found yet
    if not text_parts:
        thinking = reasoning.get("reasoningText", {})
        text = thinking.get("text") if isinstance(thinking, dict) else None
        if text:
            text_parts.append(text)
```

**After:**
```python
elif "reasoningContent" in block:
    pass  # skip reasoning/thinking blocks — never user-visible
```

## File to Edit

`/Users/mhall/Workspaces/nanobot/nanobot/providers/bedrock_provider.py`

Find the `_parse_response` method (~line 230) and apply the fix above.

## Verification

### Step 1: Inline test — confirm reasoning is NOT in output
Run this Python snippet to verify:
```bash
cd /Users/mhall/Workspaces/nanobot
python3 - <<'EOF'
from nanobot.providers.bedrock_provider import BedrockProvider

provider = BedrockProvider()
fake_response = {
    "output": {
        "message": {
            "role": "assistant",
            "content": [
                {
                    "reasoningContent": {
                        "reasoningText": {
                            "text": "I should say Hello."
                        }
                    }
                },
                {
                    "text": "Hello"
                }
            ]
        }
    },
    "stopReason": "end_turn",
    "usage": {"inputTokens": 10, "outputTokens": 5, "totalTokens": 15}
}

result = provider._parse_response(fake_response)
assert result.content == "Hello", f"Expected 'Hello', got: {result.content!r}"
assert "I should say Hello" not in (result.content or ""), "Reasoning leaked into output!"
print("PASS — reasoning correctly stripped")
EOF
```
Expected: `PASS — reasoning correctly stripped`

### Step 2: Ruff check
```bash
cd /Users/mhall/Workspaces/nanobot
python3 -m ruff check nanobot/providers/bedrock_provider.py
```
Expected: `All checks passed.`

### Step 3: Full test suite
```bash
cd /Users/mhall/Workspaces/nanobot
python3 -m pytest tests/ -q -k "not integration" --timeout=30 2>&1 | tail -5
```
Expected: 829+ passed, 0 failed.

### Step 4: Commit
```bash
cd /Users/mhall/Workspaces/nanobot
git add nanobot/providers/bedrock_provider.py
git commit -m "Fix: strip reasoningContent from MiniMax M2.1 response — was leaking chain-of-thought to users"
git push origin main
```

## Code Style
- Double quotes everywhere
- No unused imports
- Do NOT use ruff --fix

## Report
- Show the before/after diff of the changed lines
- Show inline test output (`PASS — reasoning correctly stripped`)
- Show full pytest output
- Commit hash
- PASS or FAIL
