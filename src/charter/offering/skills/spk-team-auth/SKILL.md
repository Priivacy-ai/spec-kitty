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

When testing hosted auth with tracker flows from the CLI on this computer,
hosted mode is already on — the launch default (#3980) is enabled unless
explicitly opted out; `SPEC_KITTY_ENABLE_SAAS_SYNC=0` is the opt-out. The
flag is the tracker-hosted rollout gate; it does not restore the removed
standalone sync transport. To keep hosted mode off on this machine, prefer
writing `SPEC_KITTY_ENABLE_SAAS_SYNC=0` once into
`.kittify/.kitty.env` (repo-scoped) or `${SPEC_KITTY_HOME}/.kitty.env`
(machine-wide) over a per-shell `export` — a shell export disarms every project
that shell subsequently touches, not just the one you're testing. Run
`spec-kitty doctor env-file` to confirm which tier is active.
