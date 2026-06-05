# Issue matrix — status-writepath-profile-surface-remediation-01KTB6AN

Per FR-037 of the spec-kitty-mission-review skill Gate-4. One row per issue referenced in spec.md.

| Issue | Title | Verdict | Evidence ref |
|-------|-------|---------|--------------|
| #1667 | Introduce MissionStatus aggregate (residual write-path) | fixed | WP01 — route `agent status emit` through `MissionStatus.transition()/.save()` + slug guard (FR-004/007), commit `f19dbf1e7` |
| #1636 | Missing `agent profile show`; activation-blind profile surfaces | fixed | WP03/04/05/06 — factory + activation-aware `list` + `show` + charter `--include` gate + skill reconciliation, commits `d696c1e8c` `8f92a5fe2` `f4145f3fe` `657eba762` |
| #1672 | Strangler step 1: e2e parity ratchet (CWD-invariance) | fixed | WP02 — narrow slice: ratchet extended over the status write path, commit `87c1f32a9` (full ratchet remains owned by the issue) |
| #1682 | PR: transition/save tests + `_read_meta` fail-closed | verified-already-fixed | Landed pre-mission in `cdc258002`; surfaced by the dialectic review |
| #1619 | Execution-state CWD-derivation root cause (Strangler Fig) | deferred-with-followup | Parent epic; this mission delivers only the #1667 ownership slice — broader Strangler continues |
| #1673 | ExecutionContext hardening — route residue surfaces | deferred-with-followup | WP01 wires the one concrete write surface (FR-004, D-1 fork Y); the broad residue sweep remains #1673 |
| #1663 | MissionRun → Mission back-reference | deferred-with-followup | Explicitly out of scope (spec.md Out of Scope) |
| #1664 | status/ import-boundary enforcement test | deferred-with-followup | Explicitly out of scope (sibling follow-up) |

Valid `Verdict` values: `fixed`, `verified-already-fixed`, `deferred-with-followup`.
