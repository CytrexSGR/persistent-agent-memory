---
name: memory-bootstrap
description: Session start protocol — loads identity, decisions, rules, and pending handoffs
---

# Memory Bootstrap

Run at the start of every session to load persistent context.

## Steps

1. **Detect environment:**
   - Run `hostname` and check IP to know where you are
   - Note the working directory

2. **Load bootstrap context:**
   - Call `get_bootstrap_context` — returns decisions, rules, handoffs, and recent memories
   - This is cached (1h TTL), so it's fast on repeated calls

3. **Check for pending handoffs:**
   - Call `recall` with query "session-handoff IN_PROGRESS OR BLOCKED" and limit=5
   - These are tasks from previous sessions that need attention

4. **Summarize to user:**
   - Where you are (hostname, IP)
   - Key decisions and rules loaded
   - Any pending handoffs that need attention
   - "No pending handoffs" if none found

## Notes

- Bootstrap should complete in under 5 seconds
- Don't recall everything — bootstrap context + handoff check is enough
- Topic-specific recalls happen on demand during the session
