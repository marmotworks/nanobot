# Task: Fix MiniMax M2.1 Reasoning Content Leak in bedrock_provider.py

## Problem

When using `minimax.minimax-m2.1` via AWS Bedrock, the model's internal reasoning (chain-of-thought) is leaking into the final response sent to Discord. The user sees the model's thinking process, not just the answer.

## Root Cause

In `nanobot/providers/bedrock_provider.py`, the `_parse_response` method has a bug introduced in Task 37.1. It was intended to use `reasoningContent` as a *fallback* if no `text` block was found, but MiniMax M2.1 **always** returns `reasoningContent` before the `text` block. So the fallback triggers every time, appending the reasoning to `text_parts` — then the actual `text` block is also appended. Both end up in the output.

## AWS Bedrock Converse API Response Format (Confirmed via CLI)

MiniMax M2.1 returns this structure:

```json
{
  "output": {
    "message": {
      "role": "assistant",
      "content": [
        {
          "reasoningContent": {
            "reasoningText": {
              "text": "The user wants me to say hi... I'll respond with Hello."
            }
          }
        },
        {
          "text": "\n\nHello"
        }
      ]
    }
  },
  "stopReason": "end_turn"
}
```

Key facts (confirmed via AWS CLI test `aws bedrock-runtime converse --model-id minimax.minimax-m2.1`):
- `reasoningContent` is always a **separate ContentBlock** — it does NOT appear inside the `text` block
- `reasoningContent` always comes **before** the `text` block
- The `text` block contains only the final answer
- `reasoningContent.reasoningText.text` is the chain-of-thought — should NEVER be shown to users

Source: https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/bedrock-runtime/client/converse.html
Source: https://docs.aws.amazon.com/bedrock/latest/userguide/conversation-inference-call.html

## The Buggy Code

File: `nanobot/providers/bedrock_provider.py`, method `_parse_response` (~line 230):

```python
for block in content_blocks:
    if "text" in block:
        text_parts.append(block["text"])
    elif "reasoningContent" in block:
        reasoning = block["reasoningContent"]
        # Use reasoning text as fallback if no text block found yet
        if not text_parts:                                      # ← always True (reasoning comes first)
            thinking = reasoning.get("reasoningText", {})
            text = thinking.get("text") if isinstance(thinking, dict) else None
            if text:
                text_parts.append(text)                        # ← reasoning gets added to output
    elif "toolUse" in block:
        ...
```

## The Fix

Remove the fallback reasoning extraction entirely. `reasoningContent` should always be silently skipped — it is never user-visible content. The `text` block will always be present in a valid response.

Replace the `elif "reasoningContent"` branch with:

```python
elif "reasoningContent" in block:
    pass  # skip reasoning/thinking blocks — never user-visible
```

If `text_parts` ends up empty (no `text` block at all), that's a legitimate edge case — return `None` for content and let the caller handle it. Do NOT fall back to reasoning content.

## File to Edit

`nanobot/providers/bedrock_provider.py`

## Verification

### Step 1: Confirm the fix
```bash
cd /Users/mhall/Workspaces/nanobot
python3 -m ruff check nanobot/providers/bedrock_provider.py
```
Expected: `All checks passed.`

### Step 2: Run tests
```bash
cd /Users/mhall/Workspaces/nanobot
python3 -m pytest tests/ -q -k "not integration" --timeout=30 2>&1 | tail -5
```
Expected: 829+ passed, 0 failed.

### Step 3: Live CLI test — confirm reasoning is NOT in text output
```bash
aws bedrock-runtime converse \
  --region us-east-1 \
  --model-id minimax.minimax-m2.1 \
  --messages '[{"role":"user","content":[{"text":"Say hi in one word"}]}]' \
  --output json 2>&1
```
The response will contain a `reasoningContent` block AND a `text` block. Confirm that after the fix, only the `text` block value ends up in the parsed response — NOT the reasoning.

Write a small inline test to verify:
```python
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
```

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
- Show the before/after diff of `_parse_response`
- Show inline test output (`PASS — reasoning correctly stripped`)
- Show full pytest output
- Commit hash
- PASS or FAIL
