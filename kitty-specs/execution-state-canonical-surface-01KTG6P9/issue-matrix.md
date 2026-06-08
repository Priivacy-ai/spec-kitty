# Issue Traceability Matrix — execution-state-canonical-surface-01KTG6P9

**Mission:** Execution-State Canonical Domain Surface (#1666 Strangler Slice 2)
**Branch:** feat/execution-state-strangler
**Created:** 2026-06-07
**WP column status:** filled (tasks authored 2026-06-07; #1754/#1757 folded in 2026-06-07 after #1756 landed). 13 WPs (WP01–WP13); `finalize-tasks` tooling gap #1753 **resolved** by #1756 (merged to upstream/main 2026-06-07), so the broad strangler WPs now declare `scope: codebase-wide` and the set is finalize-ready. **2026-06-08:** rebased onto the WP-lane FSM branch + plan revised for the new code shape; **#1772 folded in (US9 / FR-035..038 / IC-10)**. The WP files are now stale vs. the revised plan — **re-run `/spec-kitty.tasks`** to regenerate (expect a new WP14 for #1772 plus IC-04/IC-06 WP extensions) before finalize.

---

## Source issue → requirement → scenario → success criterion → WP

| Source issue | State | Workstream | Functional reqs | Scenario(s) | Success criteria | Work package(s) |
|--------------|-------|------------|-----------------|-------------|------------------|-----------------|
| **#1673** ExecutionContext hardening (+ inherited #1681 residue) | OPEN | Canonical surface + path-builder strangling | FR-001 … FR-012 | C, E, F | SC-1, SC-3, SC-4, SC-7 | WP02, WP03, WP04, WP05, WP06 |
| **#1664** status/ public API not enforced (~225 bypasses) | OPEN | Repo-wide facade enforcement | FR-013 … FR-016 | B | SC-3 | WP07, WP08, WP09 |
| **#1667** MissionStatus aggregate (landed) | CLOSED | Consistent MissionStatus usage | FR-017 … FR-019 | F | SC-5 | WP10 |
| **#1672** e2e parity ratchet | OPEN | Full-sequence ratchet | FR-020 … FR-024 | A | SC-2 | WP01 |
| **#1663** MissionRun → Mission back-reference (field-drop) | OPEN | Mission-identity fold-in | FR-025 … FR-027 | D | SC-6 | WP11 |
| **#1666** parent epic | OPEN | Umbrella / design authority | (all) | (all) | (all) | n/a (epic) |
| **#1757** scope not backfill-aware + half-pure seam + dict asymmetry (#1756 review) | OPEN | Ownership single-ownership fold-in | FR-028 … FR-031 | US7 | SC-9 | WP12 |
| **#1754** legacy migration `rebuild_event_log` vs `repair_repo` (#1756 follow-up) | OPEN | Migration single-port fold-in | FR-032 … FR-034 | US8 | SC-10 | WP13 |
| **#1753** WPMetadata `scope` gap (filed this slice) | **CLOSED** (fixed in #1756) | Tooling — unblocked finalize-tasks | n/a | n/a | n/a | n/a (tooling fix, merged upstream/main) |
| **#1772** coord-topology merge fails + silently skips code integration | OPEN | Coord-topology merge & path/status-surface hardening | FR-035 … FR-038 | US9 | SC-011 | WP14 (+ extends IC-04/IC-06 WPs) |

---

## Reverse check — every FR maps to a source issue (coverage)

| FR range | Mapped issue |
|----------|--------------|
| FR-001..FR-006 (canonical module + ADR + layer guard) | #1673 + #1666 (doc 06 §4) |
| FR-007..FR-012 (residue routing, dup-resolver deletion, mode-correct branch) | #1673 (inherited #1681) |
| FR-013..FR-016 (facade promotion + repo-wide boundary test) | #1664 |
| FR-017..FR-019 (MissionStatus consistent usage) | #1667 |
| FR-020..FR-024 (full-sequence ratchet + de-overclaim) | #1672 |
| FR-025..FR-027 (snapshot mission-identity carry-through) | #1663 |
| FR-028..FR-031 (scope backfill-awareness, dict symmetry, frontmatter-source port) | #1757 + #1666 (one owning port) |
| FR-032..FR-034 (canonical per-mission event-rebuild, migrate legacy callers, fixtures) | #1754 + #1666 (one owning port) |
| FR-035..FR-038 (no `.worktrees/` staging + doctor; single coord-aware resolver; merge gated on tree-state not done-status; in-branch status validation) | #1772 + #1666 (Bugs 1/2/4 are the duplicated resolution this slice strangles; Bug 0/3 folded in) |

**No orphan FRs.** Every FR-001..FR-038 traces to a source issue. Every source issue has ≥1 FR.

---

## Double-check notes

- **#1667 is CLOSED** — included for the consumption workstream (route bypasses onto the landed aggregate); it is not re-opened or re-claimed.
- **#1681 is CLOSED** — it tracked the path-builder residue; that residue (~125 sites / ~160 files) is inherited by #1673's workstream here, not re-opened.
- **#1666 is the epic** — design authority, not an implementation ticket to claim.
- **#1753 is CLOSED** — the WPMetadata `scope` gap was fixed by #1756 (merged to upstream/main 2026-06-07); this mission was rebased onto that fix, which is what makes the `scope: codebase-wide` declarations on the broad strangler WPs (WP04/05/06/08/10) valid at finalize.
- **#1757 and #1754 are folded in** — both surfaced from the #1756 adversarial review as natural extensions of the execution-environment / one-owning-port theme (epic #1666). They are claimed/assigned for this mission alongside the original open issues.
- Tickets being actively claimed/assigned for this mission: **#1672, #1664, #1673, #1663, #1757, #1754** (the open implementation issues).
- Persona ICs (Randy Reducer / Paula Patterns) attach to the shaping WPs at `/spec-kitty.tasks`; they enforce NFR-002 (leanness) and NFR-003 (single ownership), which trace to SC-7.
