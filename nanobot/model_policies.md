# Model Usage Policies

## Overview

This document defines operational rules for model selection and subagent usage based on the capabilities of available models.

## Model Capabilities

### 1. Main Agent Loop: `zai-org/glm-4.7-flash`
- **Primary Purpose**: Main agent loop
- **Capabilities**: Reasoning, administrative actions
- **Role**: Advisory/second-opinion capacity for development tasks
- **Constraint**: Do NOT invoke subagents using this model
- **Concurrency**: 4 concurrent subagents max

### 2. Subagent - Technical Tasks: `qwen3-coder-next`
- **Primary Purpose**: Technical development, tool use, agentic problem solving
- **When to Use**: Subagents for coding tasks, technical operations, complex problem-solving
- **Constraint**: None (except concurrency limit)
- **Concurrency**: 4 concurrent subagents max

### 3. Subagent - Vision Tasks: `glm-4.6v-flash`
- **Primary Purpose**: Image and vision-based tasks
- **When to Use**: Only when vision/image analysis is required
- **Constraint**: Must provide descriptive instructions to ensure accuracy
- **Concurrency**: 4 concurrent subagents max

## Subagent Selection Rules

### Default Selection
1. **Technical tasks** → Use `qwen3-coder-next`
2. **Vision tasks** → Use `glm-4.6v-flash` with descriptive instructions
3. **No model specified** → Use `qwen3-coder-next` as default

### Model-Specific Constraints

| Model | Usage | Subagent Use | Reasoning |
|-------|-------|--------------|-----------|
| `zai-org/glm-4.7-flash` | Main agent loop | ❌ Never | Reserved for main loop |
| `qwen3-coder-next` | Technical tasks | ✅ Yes | Best for development |
| `glm-4.6v-flash` | Vision tasks | ✅ Yes | Only for vision work |

## Concurrency Management

- **Maximum concurrent subagents**: 4 per model
- **Total subagents**: Up to 12 (4 per model)
- **When limit reached**: Agent should queue or prioritize based on urgency

## Example Usage

### Main Agent Loop
```python
# Main agent uses zai-org/glm-4.7-flash
agent.run(model="zai-org/glm-4.7-flash")
```

### Subagent for Technical Task
```python
# Use Qwen3-Coder-Next for development
await spawn(
    task="Implement API endpoint",
    label="API Development",
    model="qwen3-coder-next"
)
```

### Subagent for Vision Task
```python
# Use GLM-4.6v-Flash for image analysis with descriptive instructions
await spawn(
    task="Analyze this screenshot for UI bugs. Pay special attention to alignment, spacing, and button states.",
    label="UI Analysis",
    model="glm-4.6v-flash"
)
```

### No Model Specified (Default)
```python
# Agent will default to qwen3-coder-next for technical tasks
await spawn("Refactor this code", label="Code Refactor")
```

## Validation

The agent should validate model selection:
- ✅ Main model + subagent with qwen3-coder-next → Allowed
- ✅ Main model + subagent with glm-4.6v-flash → Allowed (vision tasks only)
- ❌ Main model + subagent with zai-org/glm-4.7-flash → Blocked
- ❌ Subagent with wrong model for task type → Warn and suggest alternative

## Error Handling

If model selection violates policies:
1. Return error message explaining the constraint
2. Suggest appropriate model for the task
3. Optionally offer to use default (qwen3-coder-next)