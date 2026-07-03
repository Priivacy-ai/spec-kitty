# Tasks — Unshim Wave 2 (unshim-wave2-01KWMCAX)

**Input**: spec.md rev 2 (binding census + adjudicated decisions) + plan.md IC map (IC-01..IC-08) + occurrence_map.yaml (the BINDING site ledger: 195 patch-string sites, 417 plain imports/70 files for next)
**Topology**: sequential DAG (paula post-spec verdict): A-chain WP01→(WP02∥WP03)→WP04; C-chain WP05→WP06→WP07; WP08 independent; WP09 last. Spine files (`shim-registry.yaml` + `test_shim_registry_schema.py` in WP04; `_baselines.yaml` + `test_no_dead_symbols.py` in WP07) are single-owner — no cross-WP races.
**Ledger protocol**: patch-string interception proofs recorded in each WP's Activity Log table; the orchestrator syncs them into `occurrence_map.yaml`'s `interception_proof` fields on the planning branch at approval (lane guard blocks kitty-specs edits on lanes).

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|----|----------|
| T001 | Re-point 2 plain src imports | WP01 | — |
| T002 | Re-key injection seam + 2 injectors + consumption proof | WP01 | — |
| T003 | WP01 gates | WP01 | — |
| T004 | tests/next plain re-points (243 refs) | WP02 | [P] with WP03 |
| T005 | tests/next 125 patch-site proofs + ledger | WP02 | [P] |
| T006 | WP02 gates | WP02 | [P] |
| T007 | Remaining 53-file plain re-points (173 refs) | WP03 | [P] with WP02 |
| T008 | 36 next patch-proofs + 3 unledgered charter setattr/import refs (special-case file) | WP03 | [P] |
| T009 | WP03 gates | WP03 | [P] |
| T010 | Delete next + glossary + shim self-test (pre-check first) | WP04 | — |
| T011 | Registry rows + schema-test asserts, same commit | WP04 | — |
| T012 | WP04 gates + ModuleNotFoundError + CLI smoke | WP04 | — |
| T013 | Charter src callers incl. runner.py:36+:41 defect | WP05 | [P] with A-chain |
| T014 | 20 charter test files + 32 patch-site proofs | WP05 | [P] |
| T015 | CI-only shards locally + WP05 gates | WP05 | [P] |
| T016 | Delete 3 charter packages (pre-check first) | WP06 | — |
| T017 | Lock-gate retirement: 6-row disposition table | WP06 | — |
| T018 | charter_activate documented-canonical + WP06 gates | WP06 | — |
| T019 | Verify + delete update_field surface (3 pieces) | WP07 | — |
| T020 | Drain :235 row + honest category_b re-derive (≈215) | WP07 | — |
| T021 | WP07 gates | WP07 | — |
| T022 | Derive WS1 allowed set + record decision | WP08 | [P] anytime |
| T023 | LayerRule + committed CI-selected negative test | WP08 | [P] |
| T024 | WP08 gates + #2327 progress | WP08 | [P] |
| T025 | Governance-doc scrubs + CHANGELOG (FR-011) | WP09 | — |
| T026 | Tracker closeout comments + issue-matrix terminal | WP09 | — |
| T027 | NFR-002 grep + closing sweep | WP09 | — |

## Work Packages

### WP01 — A-seam: next src callers + injection seam

- **Goal**: IC-01/FR-001 — the 3 src callers re-pointed; the monkeypatch seam + its 2 injector tests move together with a consumption proof.
- **Priority**: P1 · **Requirements**: FR-001 · **Prompt**: [tasks/WP01-a-seam.md](tasks/WP01-a-seam.md)
- [x] T001 Re-point 2 plain src imports (WP01)
- [x] T002 Re-key seam + injectors + consumption proof (WP01)
- [x] T003 Gates (WP01)

### WP02 — A-repoint cluster 1: tests/next/ (depends: WP01)

- **Goal**: IC-02 — 18 files / 243 refs / **125 patch-proofs** (the proof-heavy block).
- **Priority**: P1 · **Requirements**: FR-002 · **Dependencies**: WP01 · **Prompt**: [tasks/WP02-a-repoint-tests-next.md](tasks/WP02-a-repoint-tests-next.md)
- [x] T004 Plain re-points (WP02)
- [x] T005 125 patch-proofs + ledger (WP02)
- [x] T006 Gates (WP02)

### WP03 — A-repoint cluster 2: remaining next surface (depends: WP01)

- **Goal**: IC-02 — the other 53 files / 173 refs / 36 ledgered proofs + 3 unledgered charter refs across 8 directories; owns the dual-namespace special case (`test_next_no_implicit_success.py`; its setattr strings are invisible to every gate — the in-file grep is the only check).
- **Priority**: P1 · **Requirements**: FR-002 · **Dependencies**: WP01 · **Prompt**: [tasks/WP03-a-repoint-remaining.md](tasks/WP03-a-repoint-remaining.md)
- [x] T007 Plain re-points (WP03)
- [x] T008 Patch-proofs + ledger + cross-stream site (WP03)
- [x] T009 Gates (WP03)

### WP04 — A+B delete + registry drain (depends: WP02, WP03)

- **Goal**: IC-03/FR-003+FR-004 — delete both shims; registry rows + schema-test presence-asserts in one atomic commit (C-005).
- **Priority**: P1 · **Requirements**: FR-003, FR-004 · **Dependencies**: WP02, WP03 · **Prompt**: [tasks/WP04-ab-delete-registry.md](tasks/WP04-ab-delete-registry.md)
- [x] T010 Deletions after empty-grep pre-check (WP04)
- [x] T011 Spine drain same commit (WP04)
- [x] T012 Gates + smoke (WP04)

### WP05 — C-repoint: charter callers + tests

- **Goal**: IC-04/FR-005+FR-006p1 — 4-5 src caller lines (incl. the runner.py defect) + 20 test files + 32 charter patch-proofs; CI-only shards run locally.
- **Priority**: P2 · **Requirements**: FR-005, FR-006 · **Prompt**: [tasks/WP05-c-repoint.md](tasks/WP05-c-repoint.md)
- [x] T013 Src callers + defect fix (WP05)
- [x] T014 Test re-points + proofs (WP05)
- [x] T015 CI-only shards + gates (WP05)

### WP06 — C-delete + lock-gate retirement (depends: WP05)

- **Goal**: IC-05/FR-006p2+FR-007 — 3 packages deleted; 6-row per-test disposition table; charter_activate documented-canonical; :517-518 rows NO-TOUCH.
- **Priority**: P2 · **Requirements**: FR-006, FR-007 · **Dependencies**: WP05 · **Prompt**: [tasks/WP06-c-delete-lockgate.md](tasks/WP06-c-delete-lockgate.md)
- [x] T016 Deletions after pre-check (WP06)
- [x] T017 Disposition table + retirement (WP06)
- [x] T018 charter_activate record + gates (WP06)

### WP07 — D: #2326 wrapper prune + honest baseline (depends: WP06)

- **Goal**: IC-06/FR-008 — the 3 dead update_field pieces deleted; :235 row drained; category_b re-derived honest (≈215).
- **Priority**: P3 · **Requirements**: FR-008 · **Dependencies**: WP06 · **Prompt**: [tasks/WP07-d-wrapper-prune.md](tasks/WP07-d-wrapper-prune.md)
- [x] T019 Verify + delete (WP07)
- [x] T020 Drain + honest re-derive (WP07)
- [x] T021 Gates (WP07)

### WP08 — E: WS1 LayerRule bind (independent)

- **Goal**: IC-07/FR-009 (#2327) — the missing mission_runtime outbound rule with named allowed-exception set + committed CI-selected negative test.
- **Priority**: P3 · **Requirements**: FR-009 · **Prompt**: [tasks/WP08-e-ws1-layerrule.md](tasks/WP08-e-ws1-layerrule.md)
- [x] T022 Allowed set + decision record (WP08)
- [x] T023 Rule + negative test (WP08)
- [x] T024 Gates + #2327 progress (WP08)

### WP09 — Closeout (depends: WP04, WP06, WP07, WP08)

- **Goal**: IC-08/FR-010+FR-011 — governance-doc scrubs, CHANGELOG breaking-removal entry, tracker closeout, NFR-002 proof, closing sweep.
- **Priority**: P2 · **Requirements**: FR-010, FR-011 · **Dependencies**: WP04, WP06, WP07, WP08 · **Prompt**: [tasks/WP09-closeout.md](tasks/WP09-closeout.md)
- [x] T025 Doc scrubs + CHANGELOG (WP09)
- [x] T026 Tracker closeout (WP09)
- [x] T027 Closing sweep (WP09)

## Dependency notes

A-chain: WP01 → (WP02 ∥ WP03, disjoint file sets) → WP04 (C-001: delete only after every reference is gone). C-chain: WP05 → WP06 → WP07 (baseline honest re-derive last). WP08 independent (spine-free, zero next/glossary edges). WP09 terminal. Spine files are single-owner (WP04: registry+schema-test; WP07: baselines+dead-symbols) — no standalone gate-drain WP exists (C-005).
