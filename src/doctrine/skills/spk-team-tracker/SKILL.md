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

When testing tracker flows from the CLI on this computer, set
`SPEC_KITTY_ENABLE_SAAS_SYNC=1`.
