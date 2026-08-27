---
name: spk-team-sync
description: "Operate Spec Kitty tracker sync (sync-pull/sync-push/sync-run for local providers) and hosted SaaS-backed mission data."
---

# spk-team-sync

Use this skill when a command touches `spec-kitty tracker sync-pull` /
`sync-push` / `sync-run` (local providers), `tracker bind` / `status`
(hosted SaaS binding), or otherwise SaaS-backed mission data. There is no
standalone sync daemon, offline queue, or sync diagnostics command — that
transport was removed (issue #5); sync is a tracker capability now.

## Flow

1. Determine whether the user needs local-provider sync (`sync-pull`/
   `sync-push`/`sync-run`) or hosted SaaS binding/status.
2. Run `spec-kitty tracker status` before repair commands.
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
