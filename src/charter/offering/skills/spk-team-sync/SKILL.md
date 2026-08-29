---
name: spk-team-sync
description: "Operate Spec Kitty team sync, hosted SaaS sync, offline queue, diagnostics, and recovery flows."
---

# spk-team-sync

Use this skill when a command touches hosted sync, team state, offline queue,
sync diagnostics, or SaaS-backed mission data.

## Flow

1. Determine whether the user needs local state, hosted sync, or recovery.
2. Run sync status/diagnostics before repair commands.
3. Preserve machine-readable output when the user requested JSON.
4. For tracker-bound sync, route to `spk-team-tracker`.
5. For auth failures, route to `spk-team-auth`.

## Local Dev Note

When testing sync flows from the CLI on this computer, opt into hosted mode
with `SPEC_KITTY_ENABLE_SAAS_SYNC=1`. Prefer writing it once into
`.kittify/.kitty.env` (repo-scoped) or `${SPEC_KITTY_HOME}/.kitty.env`
(machine-wide) over a per-shell `export` — a shell export arms every project
that shell subsequently touches, not just the one you're testing. Run
`spec-kitty doctor env-file` to confirm which tier is active.
