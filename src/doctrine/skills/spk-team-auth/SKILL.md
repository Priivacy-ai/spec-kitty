---
name: spk-team-auth
description: "Handle Spec Kitty team authentication, hosted credentials, account selection, and auth-related recovery."
---

# spk-team-auth

Use this skill when the user asks about login, hosted auth, team account access,
or auth failures in sync/tracker workflows.

## Flow

1. Identify whether the command uses local-only mode or hosted team mode.
2. Run the relevant auth/status command and capture exact output.
3. Route tracker-specific failures to `spk-team-tracker`.
4. Route sync transport failures to `spk-team-sync`.
5. Ask the user only for credentials or account decisions that cannot be
   inferred.

## Local Dev Note

When testing hosted auth from the CLI on this computer, opt into hosted mode
with `SPEC_KITTY_ENABLE_SAAS_SYNC=1`. Prefer writing it once into
`.kittify/.kitty.env` (repo-scoped) or `${SPEC_KITTY_HOME}/.kitty.env`
(machine-wide) over a per-shell `export` — a shell export arms every project
that shell subsequently touches, not just the one you're testing. Run
`spec-kitty doctor env-file` to confirm which tier is active.
