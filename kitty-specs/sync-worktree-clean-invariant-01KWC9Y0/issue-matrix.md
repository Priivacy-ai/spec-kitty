# Issue matrix — sync-worktree-clean-invariant-01KWC9Y0

Per FR-037 of the spec-kitty-mission-review skill Gate-4. One row per issue referenced in spec.md.

| Issue | Title | Verdict | Evidence ref |
|-------|-------|---------|--------------|
| #2263 | Sync worktree clean invariant (dry-run/read-path must not dirty tree) | in-mission | spec.md L7 (source issue); WP01 derive_build_id no-write read path, commit 43d3fa1e6 |
| #2262 | Dry-run inertness depends on this mission's INV-1 (downstream, unblocked here) | deferred-with-followup | spec.md L111, L116 — out of scope; this mission only *unblocks* #2262 |
| #2264 | Sync success-reporting honesty (independent companion) | deferred-with-followup | Follow-up: #2264 — spec.md L100, L112, L117 explicit non-goal; independent, proceeds in parallel |

Valid `Verdict` values: `fixed`, `verified-already-fixed`, `deferred-with-followup`, `in-mission` (being fixed by a later WP in this mission; must reach a terminal verdict before mission `done`).
