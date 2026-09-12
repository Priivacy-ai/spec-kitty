---
name: ad-hoc-profile-load
description: >-
  Legacy alias for resolver-backed profile loading. Use the canonical
  spk-doctrine-profile-load skill for identity, boundaries, and governance.
  Triggers: "act as the architect", "load the reviewer profile",
  "switch to researcher", "use the planner role", "adopt a profile".
argument-hint: "<profile-id>"
---

# ad-hoc-profile-load

This is the compatibility alias for `spk-doctrine-profile-load`. The
canonical skill owns the mechanics; do not maintain a second profile-loading
procedure here.

## Canonical Route

Resolve the requested profile and load action-scoped governance:

```bash
spec-kitty agent profile show <profile-id>
spec-kitty charter context --action <action> --json
```

Apply the resolved initialization declaration, specialization boundaries,
directive and tactic references, collaboration handoffs, and mode defaults.

Read
`../spk-doctrine-profile-load/references/profile-load-mechanics.md`
for the complete resolver-backed flow, including the explicitly degraded
fallback for a read-only harness that cannot invoke the CLI.

For a one-shot governed request outside a Mission, use:

```bash
spec-kitty dispatch "<request>" --profile <profile-id>
```
