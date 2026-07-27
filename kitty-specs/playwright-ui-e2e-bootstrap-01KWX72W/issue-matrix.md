# Issue matrix — playwright-ui-e2e-bootstrap-01KWX72W

Per FR-037 of the spec-kitty-mission-review skill Gate-4. One row per issue referenced in spec.md.

| Issue | Title | Verdict | Evidence ref |
|-------|-------|---------|--------------|
| #1008 | Bootstrap Playwright + one dashboard e2e regression guard | fixed | WP01 `653874745` (modal-scoped e2e guard) + WP02 `613cdba6` (CI job + CLAUDE.md link + docs) — closes #1008 |
| #970 | Witnessing bug: WP-modal dropped agent identity | verified-already-fixed | The modal renders agent/model/agent_profile/role on current code (the e2e passes green); this mission adds the regression GUARD, not the app re-fix (spec out-of-scope) |

Valid `Verdict` values: `fixed`, `verified-already-fixed`, `deferred-with-followup`, `in-mission` (being fixed by a later WP in this mission; must reach a terminal verdict before mission `done`).
