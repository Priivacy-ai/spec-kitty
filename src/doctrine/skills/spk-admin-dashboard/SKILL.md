---
name: spk-admin-dashboard
description: "Open or report the Spec Kitty dashboard. Use for dashboard URL, localhost daemon metadata in .kittify/.dashboard, --open, --kill, or status views."
---

# spk-admin-dashboard

Open the dashboard directly or show the user its URL. Do not treat the
dashboard as a generic status abstraction.

## Flow

1. Prefer `spec-kitty dashboard --open` so lifecycle validation checks project,
   token, health, and daemon state before showing a URL.
2. If `.kittify/.dashboard` exists, treat it as diagnostic metadata only; do
   not show the URL until validation succeeds.
3. Use `spec-kitty dashboard --json` only for machine-readable mission rows.
4. Use `spec-kitty dashboard --kill` only when the user asks to stop it.

## Reference

Read `references/dashboard-daemon.md` before diagnosing dashboard metadata,
ports, tokens, or stale PID behavior.

## Rule

The dashboard is a localhost daemon, not a cloud page. Prefer
`spec-kitty dashboard --open` over manually trusting recorded metadata.
