# Tasks — Unshim Wave 1 (unshim-wave1-01KWKVHB)

**Input**: spec.md rev 2 (squad-hardened census = binding facts) + plan.md IC map (IC-01..IC-04)
**Topology**: single sequential lane (WP01 → WP02 → WP03), per the paula × alphonso convergence — the 3 co-tenant gate files make 2-lane parallelism cost more than it buys on deletion work.
**Prerequisite already on branch**: #2258 prune (commit `c194f8d`, governed op, closes via this PR).

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|----|----------|
| T001 | Delete 3 zero-importer shims + drain their gate rows | WP01 | — |
| T002 | Delete acceptance_matrix + re-anchor its sites | WP01 | — |
| T003 | Delete doc_analysis trio shims + re-anchor + pyproject overrides | WP01 | — |
| T004 | Baseline category_4 8→1 + WP-level gate sweep | WP01 | — |
| T005 | Re-anchor tasks_support plain import sites (~25) | WP02 | — |
| T006 | Rewrite 10 patch() strings + per-site interception proofs | WP02 | — |
| T007 | Delete tasks_support + final category_4 drain (1→0) + gates | WP02 | — |
| T008 | Delete 4 orphans + 3 test shields + queue.py docstring scrub | WP03 | — |
| T009 | Drain category_7 6→2 + 12 category_b rows + baselines + C-001 check | WP03 | — |
| T010 | Doc hygiene: documentation-mission.md re-point + inventory strike | WP03 | — |
| T011 | Adjudication records: policy.audit follow-up + auth.transport verdict + new debt issues | WP03 | — |
| T012 | Tracker closeout + NFR-002 merge grep + closing sweep | WP03 | — |

## Work Packages

### WP01 — Category_4 core sweep (7 shims minus tasks_support)

- **Goal**: IC-01 — delete the 7 non-tasks_support category_4 shims, re-anchor their ~14 test sites to the spec's verified canonical homes, drain their gate rows atomically (C-006).
- **Priority**: P1 · **Requirements**: FR-001, FR-002, FR-003
- **Independent test**: `pytest tests/architectural/test_no_dead_modules.py test_no_dead_symbols.py` green with `_CATEGORY_4` at exactly 1 row (`tasks_support`) and `_baselines.yaml category_4: 1`; the 7 modules gone; full suite green.
- **Prompt**: [tasks/WP01-cat4-core-sweep.md](tasks/WP01-cat4-core-sweep.md)
- [x] T001 Delete 3 zero-importer shims + drain rows (WP01)
- [x] T002 Delete acceptance_matrix + re-anchor (WP01)
- [x] T003 Delete doc trio + re-anchor + overrides (WP01)
- [x] T004 Baseline 8→1 + gate sweep (WP01)
- **Risks**: missed re-anchor makes a canonical home flag as dead mid-WP; doc_state dynamic `import … as mod` sites need module-object re-anchoring.

### WP02 — tasks_support risk-isolated re-anchor (depends: WP01)

- **Goal**: IC-02 — delete `tasks_support` after re-anchoring its ~35 sites / ~14 files; the 10 `patch()` rewrites each carry a provable interception check (AC 1.2). Reviewer's whole surface: "did every re-pointed mock still intercept."
- **Priority**: P1 · **Requirements**: FR-001, FR-002, FR-003 · **Dependencies**: WP01
- **Independent test**: `_CATEGORY_4_BACKCOMPAT_SHIMS == frozenset()`, `category_4: 0`, tasks_support pyproject override gone; per-site interception evidence in the Activity Log; full suite green.
- **Prompt**: [tasks/WP02-tasks-support-reanchor.md](tasks/WP02-tasks-support-reanchor.md)
- [x] T005 Re-anchor plain import sites (WP02)
- [x] T006 Rewrite 10 patch() strings + proofs (WP02)
- [x] T007 Delete module + final drain + gates (WP02)
- **Risks**: silent no-op mocks (bare return-value redirects have no call assertions today); patch target = consumer lookup namespace, not the definition module.

### WP03 — Category_7 execution + adjudication records + closeout (depends: WP02)

- **Goal**: IC-03 + IC-04 — delete the 4 adjudicated orphans with shields and doc hygiene; drain category_7/category_b; make the non-executed verdicts durable (policy.audit follow-up, auth.transport ADR-deferred + #2292 correction); tracker closeout.
- **Priority**: P2 · **Requirements**: FR-004, FR-005, FR-006, FR-007, FR-008 · **Dependencies**: WP02
- **Independent test**: 4 orphans + 3 shield files gone; `_CATEGORY_7` = exactly {auth.transport, policy.audit}; baselines 2/224; C-001 diff check clean; follow-up + debt issues filed; #2292 correction posted; NFR-002 grep empty.
- **Prompt**: [tasks/WP03-cat7-execution-closeout.md](tasks/WP03-cat7-execution-closeout.md)
- [ ] T008 Delete 4 orphans + shields + docstring scrub (WP03)
- [ ] T009 Gate drains + C-001 check (WP03)
- [ ] T010 Doc hygiene (WP03)
- [ ] T011 Adjudication records + new issues (WP03)
- [ ] T012 Tracker closeout + closing sweep (WP03)
- **Risks**: C-001 hard boundary (auth/transport.py + singleton test in NO diff); category_b arithmetic needs WP01's −1 already landed (it is, by dependency); premature issue closure (PR closes them).

## Dependency notes

WP02 depends on WP01 (monotone category_4 count keeps every tip green). WP03 depends on WP02 (final counts + category_b split arithmetic). Single lane; no standalone gate-drain WP exists anywhere (C-006).
