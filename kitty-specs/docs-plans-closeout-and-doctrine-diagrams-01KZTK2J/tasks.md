# Tasks: docs/plans Tier 3 Closeout (Scope A)

**Mission**: docs-plans-closeout-and-doctrine-diagrams-01KZTK2J · **Branch**: `feat/docs-plans-tier3-closeout`
**Generated**: 2026-08-12 by `/spec-kitty.tasks` (post-plan-squad model). Docs-only mission.

Subtask completion is event-sourced — record with
`spec-kitty agent tasks mark-status Txxx --status done`. The rows below are reference rows,
not checkboxes.

## Implementation Concern → Work Package map

| IC | Concern | Work Packages |
|----|---------|---------------|
| IC-01 | Durable `doc_status` marker + validator propagation (**predecessor of all**) | WP01 |
| IC-03 | Two new domain plans with boundary seams | WP02 |
| IC-02 | Retire/archive shipped clusters (evidence-gated, fanned out) | WP03, WP04, WP05, WP06 |
| IC-04 | `domains/` migration (bulk edit) + top-level index merge | WP07 |

## Dependency graph

```
WP01 ── WP02 ──┐
WP03 ──────────┤
WP04 ──────────┼── WP07
WP05 ──────────┤
WP06 ──────────┘
```

WP02 needs WP01 (the new plans carry `doc_status: durable`). The four retire WPs (WP03–WP06)
are **independent from t0** — the post-tasks squad dropped the spurious WP01 edge because they
write `deprecated` (already in the enum), not `durable`, and their file scopes are disjoint from
WP01. WP07 (IC-04) runs last — it needs the new plans (WP02→WP01), all retirements (WP03–WP06,
so the top-level index reconciliation reflects final state), and owns the shared top-level
`docs/plans/index.md`. Critical path: WP01 → WP02 → WP07.

## Subtask Index (reference table — `[P]` = parallel-safe)

| ID | Description | WP | Parallel |
|----|-------------|----|----------|
| T001 | Red-first ATDD test: durable accepted at every enumerated site | WP01 | |
| T002 | Edit AUTHORITY: directive 042 doc_status vocabulary | WP01 | |
| T003 | Mirror in DocStatus enum (DURABLE) | WP01 | |
| T004 | common-docs styleguide vocab prose + durable ∉ point_in_time_markers | WP01 | |
| T005 | docs-freshness-sla: durable never-stale | WP01 | |
| T006 | Turn suite green + confirm no regressions | WP01 | |
| T007 | Author packs-extraction-domain-plan.md (§3.2 boundary) | WP02 | [P] |
| T008 | Author api-dashboard-domain-plan.md (§3.6 boundary) | WP02 | [P] |
| T009 | Validate frontmatter + links + terminology | WP02 | |
| T010 | Auto-retire trio (open-core plan evidence) | WP03 | |
| T011 | Version-tagged bug/surface research retire (#2007, 3.2.3) | WP03 | |
| T012 | Mission-scoped closeout records retire (01KSF9HJ, #2841, #2173) | WP03 | |
| T013 | Verdict/design-refinement records retire (#2342, 01KV8NPC) | WP03 | |
| T014 | Secondary active clusters retire (#2917, #883) | WP03 | |
| T015 | Reconcile engineering-notes/index.md + verify | WP03 | |
| T016 | Creed/manifesto RECORD + squad-reports retire | WP04 | |
| T017 | Org-layering blueprint reviews retire (+ HOLD flag) | WP04 | |
| T018 | Reachability/relocation/public-API scoping retire | WP04 | |
| T019 | Reconcile doctrine/index.md + verify | WP04 | |
| T020 | High-confidence shipped investigations retire (#2658, 01KP5R6K) | WP05 | |
| T021 | 2684 runtime-state eviction cluster retire | WP05 | |
| T022 | Moderate-certainty items — gh issue view gate (#1040/#1111/#2581) | WP05 | |
| T023 | Reconcile investigations/index.md + verify | WP05 | |
| T024 | reviews/ whole cluster retire (PR #305) | WP06 | |
| T025 | refactor/ shipped subset retire (Slice-F, #2308) | WP06 | |
| T026 | 3-2-doc-publication retire (01KS4KSZ) + HOLD taxonomy | WP06 | |
| T027 | Reconcile 3 section indexes + verify | WP06 | |
| T028 | git mv two existing plans into domains/ + flip durable | WP07 | |
| T029 | Author domains/index.md | WP07 | |
| T030 | Top-level index: domains cluster + retire-index merge | WP07 | |
| T031 | Release-doc cross-refs + roadmap links (C-001-safe) | WP07 | |
| T032 | Regenerate lockfiles + prove zero dead links | WP07 | |

---

## WP01 — Durable doc_status marker + validator propagation (IC-01) · prompt: `tasks/WP01-durable-doc-status-marker.md`

- **Goal**: Add `durable` as a reserved never-retire `doc_status` value across the authority chain (directive 042 first, then enum + styleguides), proven by a red-first "accepted everywhere" test.
- **Priority**: P1 · **Requirements**: FR-002, NFR-001, C-004 · **Dependencies**: none · **execution_mode**: code_change (~230 lines)
- **Independent test**: `tests/docs/test_doc_status_durable.py` red on base, green on final; `tests/docs/` + schema-integrity green.
- Subtasks: T001, T002, T003, T004, T005, T006.

## WP02 — Two new domain plans with boundary seams (IC-03) · prompt: `tasks/WP02-two-new-domain-plans.md`

- **Goal**: Author packs-extraction + api-dashboard domain plans under `docs/plans/domains/` (`doc_status: durable`), each with an explicit non-goal against doctrine-charter §3.2 / §3.6.
- **Priority**: P1 · **Requirements**: FR-003, FR-004, C-003 · **Dependencies**: WP01 · **execution_mode**: code_change (~260 lines)
- **Independent test**: both plans pass related-validator + description-length + structural-lint; terminology guard green; boundaries concrete.
- Subtasks: T007 [P], T008 [P], T009.

## WP03 — Retire engineering-notes clusters (IC-02) · prompt: `tasks/WP03-retire-engineering-notes.md`

- **Goal**: Retire the auto trio + evidence-gated engineering-notes clusters (`doc_status: deprecated` in place + evidence banner); reconcile `engineering-notes/index.md`.
- **Priority**: P1 · **Requirements**: FR-001, NFR-002 · **Dependencies**: none · **execution_mode**: code_change (~200 lines)
- **Independent test**: every retired page `deprecated` with a resolvable evidence citation; zero deletions; lint + terminology green.
- Subtasks: T010, T011, T012, T013, T014, T015.

## WP04 — Retire doctrine working-notes (IC-02) · prompt: `tasks/WP04-retire-doctrine-notes.md`

- **Goal**: Retire shipped/superseded doctrine notes (creed RECORD/evidence, org-layering reviews, reachability/public-API scoping); flag `layered-doctrine-resolution-design.md` as HOLD-for-ruling.
- **Priority**: P1 · **Requirements**: FR-001, NFR-002 · **Dependencies**: none · **execution_mode**: code_change (~210 lines)
- **Independent test**: retired pages `deprecated` with merged-mission evidence; AUTHORITY docs + `test_quality/` + HOLD item untouched; lint green.
- Subtasks: T016, T017, T018, T019.

## WP05 — Retire investigations records (IC-02) · prompt: `tasks/WP05-retire-investigations.md`

- **Goal**: Retire shipped investigations records; gate the 3 moderate-certainty items behind a `gh issue view` check; leave the live/unshipped corpus alone.
- **Priority**: P1 · **Requirements**: FR-001, NFR-002 · **Dependencies**: none · **execution_mode**: code_change (~190 lines)
- **Independent test**: high-confidence records `deprecated`; each gated item carries a recorded gh decision; live corpus untouched; lint green.
- Subtasks: T020, T021, T022, T023.

## WP06 — Retire refactor + reviews + 3-2-doc-publication (IC-02) · prompt: `tasks/WP06-retire-refactor-reviews-docpub.md`

- **Goal**: Retire reviews/ (whole), the refactor shipped-subset, and 3-2-doc-publication notes; keep the degod roadmap/inventory live; flag `3-2-version-taxonomy.md` HOLD.
- **Priority**: P1 · **Requirements**: FR-001, NFR-002 · **Dependencies**: none · **execution_mode**: code_change (~200 lines)
- **Independent test**: retired pages `deprecated`; refactor not bulk-flipped (roadmap/inventory active); HOLD taxonomy untouched; lint green.
- Subtasks: T024, T025, T026, T027.

## WP07 — domains/ migration + top-level index merge (IC-04) · prompt: `tasks/WP07-domains-migration.md`

- **Goal**: Move all four plans into `docs/plans/domains/` (moved two → durable), author `domains/index.md`, merge the domains-cluster + IC-02 retire-index edits into the one top-level `index.md`, update release-doc cross-refs, regenerate lockfiles, prove zero dead links.
- **Priority**: P1 · **Requirements**: FR-005, C-001, C-002 · **Dependencies**: WP01, WP02, WP03, WP04, WP05, WP06 · **execution_mode**: code_change (~230 lines)
- **Independent test**: four plans one-hop reachable; zero dead links (relative-link-fixer + related-validator + lockfile freshness); roadmap still live; occurrence map conformant.
- Subtasks: T028, T029, T030, T031, T032.

---

## MVP scope

WP01 is the foundational MVP slice (the vocabulary change everything else rests on). The
smallest coherent user-visible outcome is WP01 + WP07 (durable marker + a cleanly-homed
`domains/` cluster), with the retire sweep (WP03–WP06) delivering the trust-the-surface value.

## Sizing

7 WPs, ~190–260 estimated lines each — all within the ideal 200–500 range. No WP exceeds 10
subtasks (max is WP01/WP03 at 6). Retire WPs are file-count-heavy but per-file work is a
one-line `doc_status` flip, so subtask cognitive load stays low.
