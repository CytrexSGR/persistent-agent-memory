---
name: session-handoff
description: Structured handoff at session end — stores context for next agent/session
---

# Session Handoff

Write a structured handoff at session end using `remember` with category=handoff.

## Format

```
SESSION-HANDOFF {date}
FROM: {agent} on {machine}
FOR: {recipient — next session, specific agent, or "any"}
PROJECT: {project name}
STATUS: DONE | IN_PROGRESS | BLOCKED

CONTEXT:
{1-2 sentences — what was the task}

DONE:
- {completed items, include commit hashes where relevant}

OPEN:
- {remaining items with priority}

BLOCKED_BY: (only for BLOCKED status)
- {what prevents progress}

ENTRY:
{recall query or command for next session to pick up}
```

## Steps

1. Review what was accomplished this session
2. Identify what remains open or blocked
3. Write the handoff using the format above
4. Store via `remember` tool:
   - `category`: "handoff"
   - `tags`: ["session-handoff", "{project}", "{status}"]
   - `importance`: 5
5. Confirm to user: "Handoff stored for {project} — status: {status}"
