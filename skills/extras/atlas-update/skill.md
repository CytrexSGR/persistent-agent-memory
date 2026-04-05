---
name: atlas-update
description: Update infrastructure documentation after service changes — optional skill for multi-server setups
---

# Atlas Update

Use after infrastructure changes (new services, ports, VMs, network changes) to update central documentation.

## Steps

1. **Identify what changed:**
   - New service deployed? Port changed? VM created/destroyed?
   - Note the specific change and affected systems

2. **Update local service docs:**
   - Update the service's own documentation (README, config docs)

3. **Update central atlas:**
   - Infrastructure map (network topology, IPs, ports)
   - Service catalog (what runs where, health endpoints)
   - MCP catalog (if MCP tools were added/changed)

4. **Remember the change:**
   - Store via `remember` with category "project" and tags ["atlas", "infrastructure", "{service}"]
   - Include: what changed, when, why

## Notes

- This skill is optional — only relevant for multi-server setups
- Skip if the change is purely code-level with no infrastructure impact
