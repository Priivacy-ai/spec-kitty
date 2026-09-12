---
name: spk-team-tracker
description: "Operate Spec Kitty tracker workflows, tracker service discovery, binding, hosted routing, and tracker recovery."
---

# spk-team-tracker

Use this skill when the user asks about tracker setup, tracker sync, tracker
binding, hosted tracker routing, or tracker diagnostics.

## Flow

1. Inspect tracker status and service discovery output.
2. Confirm the active project and tracker binding.
3. Use hosted sync only when the workflow requires it.
4. Route auth failures to `spk-team-auth`.
5. Route transport/offline replay failures to `spk-team-sync`.

## Local Dev Note

When testing tracker-hosted flows from the CLI on this computer, hosted mode
is already on — the launch default (#3980) is enabled unless explicitly opted
out; `SPEC_KITTY_ENABLE_SAAS_SYNC=0` is the opt-out. The flag gates tracker
invocation only; it does not restore the removed standalone sync transport.
To keep hosted mode off on this machine, prefer writing
`SPEC_KITTY_ENABLE_SAAS_SYNC=0` once into
`.kittify/.kitty.env` (repo-scoped) or `${SPEC_KITTY_HOME}/.kitty.env`
(machine-wide) over a per-shell `export` — a shell export disarms every project
that shell subsequently touches, not just the one you're testing. Run
`spec-kitty doctor env-file` to confirm which tier is active.
