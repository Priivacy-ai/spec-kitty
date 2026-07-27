# Issue Traceability Matrix — execution-state-canonical-surface-01KTG6P9

**Mission:** Execution-State Canonical Domain Surface (#1666 Strangler Slice 2)
**Branch:** feat/execution-state-strangler

One row per GitHub issue referenced in `spec.md`. Mandatory columns: `issue`,
`verdict`, `evidence_ref`. Verdict allow-list: `fixed`, `verified-already-fixed`,
`deferred-with-followup`, `in-mission` (being closed by a later WP in *this*
mission; must reach a terminal verdict before the mission merges to `done`).

| issue | title | verdict | wp | evidence_ref |
|-------|-------|---------|----|--------------|
| #1673 | ExecutionContext hardening (+ inherited #1681 path-builder residue) | fixed | WP02, WP03, WP04, WP05, WP06 | `mission_runtime` umbrella + ADR; ExecutionContext relocated and `core/execution_context.py` deleted; residue routing + dup-resolver collapse + path-builder elimination all approved and merged to feat (lane-b → feat, commit 406bd9527) |
| #1664 | status/ public API not enforced (~225 deep-import bypasses) | fixed | WP07, WP08, WP09 | facade promotion + deep-import routing (219→21) + repo-wide `test_status_module_boundary.py` widened to all of src/specify_cli+src/runtime; green on feat |
| #1667 | MissionStatus aggregate | verified-already-fixed | WP10 | aggregate landed by mission 01KT6HVH; this slice only routes consumers onto it (WP10) — issue itself already closed |
| #1672 | e2e full-sequence parity ratchet | fixed | WP01 | `test_execution_context_parity.py` extended to the full next→implement→move-task→review→status sequence across 3 modes + negative control; 9/9 green on feat |
| #1663 | MissionRun → Mission back-reference (field-drop) | fixed | WP11 | snapshot mission-identity carry-through landed in `runtime_bridge.py`; approved and merged to feat |
| #1666 | Execution-state unification parent epic | deferred-with-followup | n/a | Follow-up: #1666 remains the multi-slice umbrella epic; this mission is Strangler Slice 2 and does not close the epic |
| #1757 | scope not backfill-aware + half-pure seam + dict asymmetry (#1756 review) | fixed | WP12 | ownership `FrontmatterSource` port (`resolve_wp_manifests`) folds resolve→validate into one seam; approved and merged to feat |
| #1754 | legacy migration `rebuild_event_log` vs `repair_repo` (#1756 follow-up) | fixed | WP13 | `rebuild_mission_event_log()` canonical single-port rebuild entry landed in `migration/mission_state.py`; approved and merged to feat |
| #1756 | finalize-tasks WPMetadata `scope` tooling gap | verified-already-fixed | n/a | fixed upstream and merged to upstream/main 2026-06-07; this mission was rebased onto it |
| #1753 | WPMetadata `scope` gap (filed this slice) | verified-already-fixed | n/a | resolved by #1756 (merged upstream/main 2026-06-07) — the rebase makes `scope: codebase-wide` declarations valid at finalize |
| #1772 | coord-topology merge fails + silently skips code integration | fixed | WP14 | `path_is_under_worktrees` predicate + staging guard, `_lane_already_integrated` tree-diff gate (fail-loud on zero-diff squash), in-branch validation, doctor check; ATDD RED-first regression `test_merge_coord_topology_1772.py`; approved and merged to feat |
| #1619 | Runtime/state overhaul (grounding epic) | deferred-with-followup | n/a | Follow-up: #1619 is the broad runtime/state overhaul epic referenced as background; not closed by this slice |

---

## Reverse coverage — every FR maps to a source issue

(prose, not a second table — the validator allows exactly one Markdown table)

- **FR-001..FR-006** (canonical module + ADR + layer guard) → #1673 + #1666 (doc 06 §4)
- **FR-007..FR-012** (residue routing, dup-resolver deletion, mode-correct branch) → #1673 (inherited #1681)
- **FR-013..FR-016** (facade promotion + repo-wide boundary test) → #1664
- **FR-017..FR-019** (MissionStatus consistent usage) → #1667
- **FR-020..FR-024** (full-sequence ratchet + de-overclaim) → #1672
- **FR-025..FR-027** (snapshot mission-identity carry-through) → #1663
- **FR-028..FR-031** (scope backfill-awareness, dict symmetry, frontmatter-source port) → #1757 + #1666
- **FR-032..FR-034** (canonical per-mission event-rebuild, migrate legacy callers, fixtures) → #1754 + #1666
- **FR-035..FR-038** (no `.worktrees/` staging + doctor; single coord-aware resolver; merge gated on tree-state not done-status; in-branch status validation) → #1772 + #1666

No orphan FRs: every FR-001..FR-038 traces to a source issue, and every source issue has ≥1 FR.

## Notes

- **All in-mission rows are now terminal (`fixed`).** #1673, #1664, #1672, #1663, #1757, #1754, #1772 were each closed by their owning WPs; all 14 WPs are approved and merged (lane-b → feat, commit 406bd9527), so every previously-`in-mission` verdict is flipped to `fixed`. The mission is clear of the per-WP `in-mission` accept gate for merge to `done`.
- **#1667 / #1756 / #1753** are already resolved (`verified-already-fixed`) — included for traceability, not re-opened or re-claimed.
- **#1666 / #1619** are epics (`deferred-with-followup`) — not closed by this slice.
- **#1681** (closed) tracked the path-builder residue inherited by #1673's workstream; not re-opened.
