# Tasks: Single-Authority Resolution Gates

**Mission:** `single-authority-resolution-gates-01KW1P0F` · **Branch:** `design/infra-logic-separation-2173` (flattened)
**Spec:** [spec.md](./spec.md) · **Plan:** [plan.md](./plan.md) · **Contracts:** [contracts/resolution-gates.md](./contracts/resolution-gates.md)

8 work packages from IC-01…IC-07. **Lane discipline:** `tasks.py` + `implement.py` (both runtime + canon sites) are owned solely by **WP02** — no other WP edits them. The shared gate allowlist `tests/architectural/resolution_gate_allowlist.yaml` is owned by **WP01** (seeds the pre-sweep baseline); shrunk **once** by **WP08** (the final routed-count + shrink pass, T040); the sweep WPs (WP02–WP05) **route code only** and record their routed sites for WP08's manifest — dissolving any parallel-lane allowlist contention (NFR-003, SC-004).

## Dependency graph

```
WP01 (gate machinery + discriminators, seed baseline)  ── foundation
  ├── WP02 (#2154/#2155 runtime + tasks.py/implement.py canon)
  ├── WP03 (seam-module canon sweep)
  ├── WP04 (consumer canon sweep: merge/core/coordination)
  ├── WP05 (consumer canon sweep: status/runtime/agent)
  └── WP07 (test-hygiene folds)
WP06 (convergence test)            ← deps WP02,03,04,05
WP08 (pre-condition + gate reconciliation) ← deps WP02,03,04,05
```

## Subtask Index (reference only — tracking is the per-WP checkboxes)

| ID | Description | WP | Parallel |
|----|-------------|----|----------|
| T001 | Composite-key `(qualname, token_line)` allowlist machinery + loader (net-new) | WP01 | |
| T002 | Canonicalizer def-use discriminator (scan-by-name + intra-function provenance) | WP01 | |
| T003 | Coord-authority discriminator (explicit write-vs-read predicate) | WP01 | |
| T004 | Seed pre-sweep baseline allowlist (bypasses + `:454` + decision_log/widen coord-writes) | WP01 | |
| T005 | Self-mutation tests (both discriminators, injection at distinct sites) | WP01 | |
| T006 | Concrete floor (≥38) + shrink-only staleness twin-guard (pre-sweep baseline) | WP01 | |
| T007 | Wire gates into fast tier; verify <30 s on full `src/` | WP01 | |
| T008 | Route `mark_status` write-leg (`tasks.py:1807`) → `resolve_planning_read_dir(kind=TASKS_INDEX)` | WP02 | |
| T009 | Red-first 3-leg convergence assertion (coord AND flat topologies) | WP02 | |
| T010 | Route `move_task` mixed bundle (`tasks.py:1555`) via `BookkeepingTransaction`; surface (un-swallow) errors | WP02 | |
| T011 | Route claim mixed bundle (`implement.py:1311`) via `BookkeepingTransaction`; un-swallow | WP02 | |
| T012 | Route/sanction `tasks.py` (2) + `implement.py` (4) canon sites | WP02 | |
| T013 | Coord-topology integration test (#2155: commits clean, wrong-surface still refused) | WP02 | |
| T014 | Record WP02's routed sites for WP08's shrink manifest (no allowlist edit) | WP02 | |
| T015 | Sanction `_read_path_resolver.py` seam-internal sites; pin `:454` bare probe (C-001) | WP03 | [P] |
| T016 | Route/sanction `mission_type.py` (`:592` route, `:1048` already-canonical) | WP03 | [P] |
| T017 | Route/sanction `retrospective/writer.py` | WP03 | [P] |
| T018 | Record WP03's routed sites for WP08's manifest (no allowlist edit) | WP03 | [P] |
| T019 | Route `merge/bookkeeping_projection.py` (2) + `merge/executor.py` (1) | WP04 | [P] |
| T020 | Route `core/paths.py` (2) + `core/git_ops.py` (1) | WP04 | [P] |
| T021 | Route `coordination/surface_resolver.py` (1) + `commit_router.py` (1) | WP04 | [P] |
| T022 | Record WP04's routed sites for WP08's manifest (no allowlist edit) | WP04 | [P] |
| T023 | Route `status/aggregate.py` (4) | WP05 | [P] |
| T024 | Route `mission_runtime/resolution.py` (4) | WP05 | [P] |
| T025 | Route `runtime_bridge.py` (`:98`, `:177`) | WP05 | [P] |
| T026 | Route `agent/workflow.py` + `mission_finalize.py` + `mission_feature_resolution.py` + `acceptance/__init__.py` | WP05 | [P] |
| T027 | Record WP05's routed sites for WP08's manifest (no allowlist edit) | WP05 | [P] |
| T028 | Stub resolver with distinguishable P1–P5 per-form outputs | WP06 | |
| T029 | Parametrize all handle forms; assert read-seam ≡ write/placement-seam | WP06 | |
| T030 | Ambiguity-raises + cold-miss fail-closed cases | WP06 | |
| T031 | Negative control: a pre-fix-divergent form (red-first) | WP06 | |
| T032 | Constant-stub-rejected guard | WP06 | |
| T033 | Frozen-baseline `/tmp` ratchet (census ~82 baseline; block new only) | WP07 | [P] |
| T034 | `/tmp` ratchet self-mutation test | WP07 | [P] |
| T035 | FR-008 empirical re-derive (`--collect-only` before/after diff); co-tag or verify-only | WP07 | [P] |
| T036 | Record FR-008 verification outcome | WP07 | [P] |
| T037 | C-003 verify #2161 read-leg present on base | WP08 | |
| T038 | Reconcile existing surface-resolver gate floors/allowlists post-sweep | WP08 | |
| T039 | Full `tests/architectural/` sweep green | WP08 | |
| T040 | Final allowlist shrink + `test_routed_count_floor` (≥27 routed) + ≤ pre-sweep baseline | WP08 | |

---

## WP01 — Gate machinery + both discriminators (IC-01, IC-02a, IC-03)

- **Goal:** Build the reusable AST-gate module + the two discriminators (canonicalizer def-use + coord-authority write-vs-read), seeded with the **full pre-sweep baseline** allowlist so the gate is GREEN at landing. The foundation both lanes consume. (FR-003, FR-004; NFR-001/002/003/004; C-005)
- **Priority:** P0 (foundation) · **Independent test:** `pytest tests/architectural/test_resolution_authority_gates.py -q` green; both self-mutation tests red-on-inject.
- **Depends on:** none.
- **Subtasks:**
  - [x] T001 Composite-key `(qualname, token_line)` allowlist machinery + loader (WP01)
  - [x] T002 Canonicalizer def-use discriminator (scan-by-name + intra-function provenance) (WP01)
  - [x] T003 Coord-authority discriminator (explicit write-vs-read predicate) (WP01)
  - [x] T004 Seed pre-sweep baseline allowlist (WP01)
  - [x] T005 Self-mutation tests (both discriminators, distinct injection sites) (WP01)
  - [x] T006 Concrete floor (≥38) + shrink-only staleness twin-guard (WP01)
  - [x] T007 Wire into fast tier; verify <30 s (WP01)
- **Risks:** composite-key is net-new (not a copy — don't under-budget); floor must be the live census; the coord-authority write-vs-read predicate has no name proxy (must allowlist decision_log/widen).

## WP02 — #2154 + #2155 runtime routing + tasks.py/implement.py canon (IC-04a, IC-04b)

- **Goal:** Route the `mark_status` write-leg through the kind-aware authority (#2154) and the two mixed-bundle auto-commits through `BookkeepingTransaction` (#2155), surfacing not swallowing errors; route the 6 canon sites in these two files. **Guard untouched (C-006).** (FR-001, FR-002, FR-005; C-002, C-006)
- **Priority:** P0 · **Independent test:** the #2154 + #2155 reproductions pass; `git/commit_helpers.py` unchanged.
- **Depends on:** WP01.
- **Subtasks:**
  - [x] T008 Route `mark_status` write-leg (`tasks.py:1807`) (WP02)
  - [x] T009 Red-first 3-leg convergence (coord AND flat) (WP02)
  - [x] T010 Route `move_task` mixed bundle (`tasks.py:1555`); un-swallow (WP02)
  - [x] T011 Route claim mixed bundle (`implement.py:1311`); un-swallow (WP02)
  - [x] T012 Route/sanction `tasks.py` (2) + `implement.py` (4) canon sites (WP02)
  - [x] T013 Coord-topology integration test (#2155) (WP02)
  - [x] T014 Record WP02's routed sites for WP08's manifest; no allowlist edit (WP02)
- **Risks:** the intra-function write/commit split; the swallow hides failure — the fix must surface a genuine failure; do NOT touch the guard (C-006, merge-blocker); reachable only under coord-topology + unprotected branch.

## WP03 — Canonicalizer seam-module sweep (IC-02b)

- **Goal:** Sanction/route the seam-internal sites (`_read_path_resolver.py` ×7, `mission_type.py` ×2, `retrospective/writer.py` ×1) — mostly already-canonical → allowlist-with-rationale; **pin `_read_path_resolver.py:454` as the sanctioned bare probe (C-001 merge-blocker).** (FR-005; C-001)
- **Priority:** P1 · **Independent test:** the canonicalizer gate green for these files; `:454` pinned.
- **Depends on:** WP01.
- **Subtasks:**
  - [x] T015 Sanction `_read_path_resolver.py` seam sites; pin `:454` (WP03)
  - [x] T016 Route/sanction `mission_type.py` (WP03)
  - [x] T017 Route/sanction `retrospective/writer.py` (WP03)
  - [x] T018 Shrink allowlist for routed seam sites (WP03)
- **Risks:** don't double-fold already-canonical sites; `:454` must be allowlisted not "fixed" (FR-011 recursion).

## WP04 — Canonicalizer consumer sweep: merge/core/coordination (IC-02c part 1)

- **Goal:** Route the consumer sites in `merge/` (×3), `core/` (×3), `coordination/` (×2) through `_canonicalize_primary_read_handle` — **routing is the default**. (FR-005; C-002)
- **Priority:** P1 · **Independent test:** gate green for these files; routed-count contributes to SC-004.
- **Depends on:** WP01.
- **Subtasks:**
  - [x] T019 Route `merge/bookkeeping_projection.py` (2) + `executor.py` (1) (WP04)
  - [x] T020 Route `core/paths.py` (2) + `core/git_ops.py` (1) (WP04)
  - [x] T021 Route `coordination/surface_resolver.py` (1) + `commit_router.py` (1) (WP04)
  - [x] T022 Shrink allowlist for WP04 sites (WP04)
- **Risks:** ambiguity propagation (C-002); avoid double-fold; some coordination sites may be legitimate coord-writes (verify before routing).

## WP05 — Canonicalizer consumer sweep: status/runtime/agent (IC-02c part 2)

- **Goal:** Route the consumer sites in `status/aggregate.py` (×4), `mission_runtime/resolution.py` (×4), `runtime_bridge.py` (`:98`/`:177`), the 3 `agent/` helpers, `acceptance/__init__.py`. (FR-005; C-002)
- **Priority:** P1 · **Independent test:** gate green for these files.
- **Depends on:** WP01.
- **Subtasks:**
  - [x] T023 Route `status/aggregate.py` (4) (WP05)
  - [x] T024 Route `mission_runtime/resolution.py` (4) (WP05)
  - [x] T025 Route `runtime_bridge.py` (`:98`, `:177`) (WP05)
  - [x] T026 Route `agent/workflow.py` + `mission_finalize.py` + `mission_feature_resolution.py` + `acceptance/__init__.py` (WP05)
  - [x] T027 Shrink allowlist for WP05 sites (WP05)
- **Risks:** the judgment-heavy cluster; ambiguity propagation; `runtime_bridge.py` is the corrected latent path (`src/runtime/next/`).

## WP06 — Convergence test (IC-05)

- **Goal:** Stub-driven parametrized test asserting read-seam ≡ write/placement-seam for every handle form, with distinguishable per-form stub outputs, the ambiguity/cold-miss cases, and a red-first negative control. (FR-006)
- **Priority:** P1 · **Independent test:** the convergence test passes; a constant-stub variant fails the guard.
- **Depends on:** WP02, WP03, WP04, WP05.
- **Subtasks:**
  - [ ] T028 Stub resolver, distinguishable P1–P5 per-form outputs (WP06)
  - [ ] T029 Parametrize handle forms; assert read≡write (WP06)
  - [ ] T030 Ambiguity-raises + cold-miss fail-closed (WP06)
  - [ ] T031 Negative control (pre-fix-divergent form, red-first) (WP06)
  - [ ] T032 Constant-stub-rejected guard (WP06)
- **Risks:** a tautological stub; missing the negative control; skipping the divergent cases.

## WP07 — Test-hygiene folds (IC-06)

- **Goal:** Frozen-baseline `/tmp` ratchet (FR-007) + empirical FR-008 re-derivation (collect-only diff; co-tag only proven-excluded files, else verify-only). (FR-007, FR-008)
- **Priority:** P2 · **Independent test:** ratchet reds on a new `/tmp` literal; FR-008 verification recorded.
- **Depends on:** WP01.
- **Subtasks:**
  - [x] T033 Frozen-baseline `/tmp` ratchet (WP07)
  - [x] T034 `/tmp` ratchet self-mutation test (WP07)
  - [x] T035 FR-008 empirical re-derive (collect-only diff) (WP07)
  - [x] T036 Record FR-008 verification outcome (WP07)
- **Risks:** scope discipline (no #1842 sweep, no `ci-quality.yml` matrix); FR-008 must not add redundant markers to already-running files.

## WP08 — Pre-condition verify + existing-gate reconciliation (IC-07)

- **Goal:** Verify the #2161 read-leg pre-condition (C-003) and reconcile the existing surface-resolver gates' floors/allowlists after WP02–WP05 move sites; full `tests/architectural/` sweep green. (C-003; NFR-002/003)
- **Priority:** P1 (gate) · **Independent test:** full `tests/architectural/` green; no existing gate left red by site moves.
- **Depends on:** WP02, WP03, WP04, WP05.
- **Subtasks:**
  - [ ] T037 C-003 verify #2161 read-leg present on base (WP08)
  - [ ] T038 Reconcile existing surface-resolver gate floors/allowlists (WP08)
  - [ ] T039 Full `tests/architectural/` sweep green (WP08)
  - [ ] T040 Final allowlist shrink + routed-count floor (≥27) + ≤ pre-sweep baseline (WP08)
- **Risks:** a site move silently breaking a pre-existing gate's floor (easy to miss in per-WP review; the full sweep catches it).
