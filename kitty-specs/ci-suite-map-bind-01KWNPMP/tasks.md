# Tasks — CI suite-map bind (ci-suite-map-bind-01KWNPMP)

**Input**: spec.md rev 4 (squad-hardened: 3-state marker model, HiC rulings 7a/7b, Decision 8 authority rule) + plan.md IC map (IC-01..IC-08) + research R1-R8
**Topology**: sequential-ish DAG with one parallel head. Two single-owner spines (paula): `tests/architectural/_gate_coverage.py` (WP01 extends, read-only after) and the workflow pair + baseline (WP03 sole owner). The FR-011 decision logic is EXTRACTED into a standalone script (WP02, parallel with WP01) so the yml wiring stays thin. Invariants (WP04) land AFTER the surgery (WP03) — they define green against the fixed workflows; FR-001 + FR-002 are green together from WP04's landing onward.
**Verification doctrine**: every invariant needs its fault-injection red AND (for FR-010/FR-012) its reorder red-negative (stays green); all census numbers re-derived at implement (NFR-004); the C-007 probe PR is non-draft.

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|----|----------|
| T001 | Workflow-scope preflight probe (C-004) | WP01 | [P] with WP02 |
| T002 | `_gate_coverage.py` additive parse extensions | WP01 | [P] |
| T003 | WP01 gates | WP01 | [P] |
| T004 | Quality-gate decision script (paula's table) | WP02 | [P] with WP01 |
| T005 | Script fixture tests (draft/skip/supersede cases) | WP02 | [P] |
| T006 | WP02 gates | WP02 | [P] |
| T007 | Residual job + quality-gate needs/loop wiring | WP03 | — |
| T008 | FR-004 fixes + FR-006 drain/baseline regen + FR-007 widen | WP03 | — |
| T009 | FR-010 catch-all mechanism + FR-013 trigger + FR-012 two-layer + script wiring | WP03 | — |
| T010 | WP03 gates + probe branches | WP03 | — |
| T011 | Marker-completeness invariant (FR-001, 3-state) | WP04 | — |
| T012 | Coherence invariants (FR-003/FR-005/FR-008 + FR-011 mapping) | WP04 | — |
| T013 | Path-topology invariants (FR-010/FR-012/FR-013) + red-negatives | WP04 | — |
| T014 | WP04 gates | WP04 | — |
| T015 | Docs + tracker closeout (FR-009) | WP05 | — |
| T016 | Probes, re-derivations, closing sweep | WP05 | — |

## Work Packages

### WP01 — Substrate (preflight + parse model)

- **Goal**: IC-01 + IC-02 — prove the `.github/workflows/` push path (C-004), then extend `_gate_coverage.py` additively with every relation the invariants consume. Read-only after this WP.
- **Priority**: P1 · **Requirements**: FR-003, FR-008 · **Prompt**: [tasks/WP01-substrate.md](tasks/WP01-substrate.md)
- [x] T001 Workflow-scope preflight probe (WP01)
- [x] T002 Parse-model extensions (WP01)
- [x] T003 Gates (WP01)

### WP02 — Aggregator decision script

- **Goal**: FR-011's decision logic as a standalone, fixture-tested script (paula's table) — the yml wiring in WP03 stays a thin call.
- **Priority**: P1 · **Requirements**: FR-011 · **Prompt**: [tasks/WP02-aggregator-script.md](tasks/WP02-aggregator-script.md)
- [x] T004 Decision script (WP02)
- [x] T005 Fixture tests (WP02)
- [x] T006 Gates (WP02)

### WP03 — Workflow surgery (depends: WP01, WP02)

- **Goal**: IC-05 + IC-06 + IC-07 — ALL `ci-quality.yml`/`ci-windows.yml` edits in one owner: residual job (FR-002), bounded fixes (FR-004), orphan drain + baseline regen (FR-006), Windows widening (FR-007), the run_all catch-all mechanism (FR-010, HiC 7b), `ready_for_review` (FR-013, HiC 7a), two-layer self-mapping (FR-012), aggregator wiring (FR-011).
- **Priority**: P1 · **Requirements**: FR-002, FR-004, FR-006, FR-007, FR-010, FR-011, FR-012, FR-013 · **Dependencies**: WP01, WP02 · **Prompt**: [tasks/WP03-workflow-surgery.md](tasks/WP03-workflow-surgery.md)
- [x] T007 Residual job + gate wiring (WP03)
- [x] T008 Fixes + drain + widen (WP03)
- [x] T009 Catch-all + trigger + self-map + script wiring (WP03)
- [x] T010 Gates + probes (WP03)

### WP04 — Invariant suite (depends: WP01, WP03)

- **Goal**: IC-03 + IC-04 — the standing guards: 3-state marker completeness (FR-001), workflow coherence (FR-003/FR-005/FR-008), the FR-011 job→group mapping invariant, path-topology invariants (FR-010c/d, FR-012 mirror, FR-013 trigger) — every one with fault-injection red + (where specced) reorder red-negative.
- **Priority**: P1 · **Requirements**: FR-001, FR-003, FR-005, FR-008, FR-010, FR-011, FR-012, FR-013 · **Dependencies**: WP01, WP03 · **Prompt**: [tasks/WP04-invariants.md](tasks/WP04-invariants.md)
- [x] T011 Marker completeness (WP04)
- [x] T012 Coherence + mapping invariants (WP04)
- [x] T013 Path-topology invariants + red-negatives (WP04)
- [x] T014 Gates (WP04)

### WP05 — Closeout (depends: WP03, WP04)

- **Goal**: IC-08 — roadmap strike, tracker comments (#2297/#2296/#2034/#2333 close-by-PR; #2283 partial; #1933 reconciliation; #1868 WS5), C-007 probe evidence, NFR re-derivations, closing sweep.
- **Priority**: P2 · **Requirements**: FR-009 · **Dependencies**: WP03, WP04 · **Prompt**: [tasks/WP05-closeout.md](tasks/WP05-closeout.md)
- [ ] T015 Docs + tracker closeout (WP05)
- [ ] T016 Probes + sweep (WP05)

## Dependency notes

WP01 ∥ WP02 (disjoint files) → WP03 (sole owner of both workflow files + baseline) → WP04 (invariants define green against the fixed workflows; FR-001+FR-002 green together from here) → WP05. No standalone gate-drain WP; the two spines are single-owner by construction.
