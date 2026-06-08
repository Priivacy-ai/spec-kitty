# Issue Traceability Matrix — execution-state-canonical-surface-01KTG6P9

**Mission:** Execution-State Canonical Domain Surface (#1666 Strangler Slice 2)
**Branch:** feat/execution-state-strangler

One row per GitHub issue referenced in `spec.md`. Mandatory columns: `issue`,
`verdict`, `evidence_ref`. Verdict allow-list: `fixed`, `verified-already-fixed`,
`deferred-with-followup`, `in-mission` (being closed by a later WP in *this*
mission; must reach a terminal verdict before the mission merges to `done`).

| issue | title | verdict | wp | evidence_ref |
|-------|-------|---------|----|--------------|
| #1673 | ExecutionContext hardening (+ inherited #1681 path-builder residue) | in-mission | WP02, WP03, WP04, WP05, WP06 | WP02 landed the canonical `mission_runtime` umbrella + ADR (commit 9398cca0a); relocation/strangling continues in WP03–WP06 |
| #1664 | status/ public API not enforced (~225 deep-import bypasses) | in-mission | WP07, WP08, WP09 | facade promotion + repo-wide boundary test; closed when WP09 widened-boundary test is green |
| #1667 | MissionStatus aggregate | verified-already-fixed | WP10 | aggregate landed by mission 01KT6HVH; this slice only routes consumers onto it (WP10) — issue itself already closed |
| #1672 | e2e full-sequence parity ratchet | in-mission | WP01 | WP01 extends the ratchet to the full next→implement→move-task→review→status sequence (commit 55a83e38f, in review) |
| #1663 | MissionRun → Mission back-reference (field-drop) | in-mission | WP11 | snapshot mission-identity carry-through; closed when WP11 lands |
| #1666 | Execution-state unification parent epic | deferred-with-followup | n/a | Follow-up: #1666 remains the multi-slice umbrella epic; this mission is Strangler Slice 2 and does not close the epic |
| #1757 | scope not backfill-aware + half-pure seam + dict asymmetry (#1756 review) | in-mission | WP12 | ownership single-ownership fold-in; closed when WP12 lands |
| #1754 | legacy migration `rebuild_event_log` vs `repair_repo` (#1756 follow-up) | in-mission | WP13 | migration single-port fold-in; closed when WP13 lands |
| #1756 | finalize-tasks WPMetadata `scope` tooling gap | verified-already-fixed | n/a | fixed upstream and merged to upstream/main 2026-06-07; this mission was rebased onto it |
| #1753 | WPMetadata `scope` gap (filed this slice) | verified-already-fixed | n/a | resolved by #1756 (merged upstream/main 2026-06-07) — the rebase makes `scope: codebase-wide` declarations valid at finalize |
| #1772 | coord-topology merge fails + silently skips code integration | in-mission | WP14 | coord-topology merge & path/status-surface hardening; closed when WP14 lands (depends on WP04 resolver) |
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

- **`in-mission`** rows (#1673, #1664, #1672, #1663, #1757, #1754, #1772) are being closed by their owning WPs in this mission. They pass the per-WP `approved` gate; each must be flipped to a terminal verdict (`fixed`) as its WP lands, and **all** must be terminal before the mission merges to `done`.
- **#1667 / #1756 / #1753** are already resolved (`verified-already-fixed`) — included for traceability, not re-opened or re-claimed.
- **#1666 / #1619** are epics (`deferred-with-followup`) — not closed by this slice.
- **#1681** (closed) tracked the path-builder residue inherited by #1673's workstream; not re-opened.
