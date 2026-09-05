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

When testing tracker-hosted flows from the CLI on this computer, opt into
hosted mode with `SPEC_KITTY_ENABLE_SAAS_SYNC=1`. The flag gates tracker
invocation only; it does not restore the removed standalone sync transport.
Prefer writing it once into
`.kittify/.kitty.env` (repo-scoped) or `${SPEC_KITTY_HOME}/.kitty.env`
(machine-wide) over a per-shell `export` — a shell export arms every project
that shell subsequently touches, not just the one you're testing. Run
`spec-kitty doctor env-file` to confirm which tier is active.
