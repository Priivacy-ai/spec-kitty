# Tasks: Write-Side Context-Factory Adoption (Mission B)

**Branch**: `feat/write-side-context-factory-adoption` (stacked on `feat/read-path-error-fidelity` / Mission A) · **Merge target**: same · **Date**: 2026-06-17

Pure consumer-routing of the WRITE execution path onto Mission A's frozen `build_execution_context`
factory + its projected fragments (C-001 — no new authority). Discipline (binding, every WP):
function-over-form + **verification-by-deletion**, **topology-true fixtures** (full 26-char ULID + REAL
coord-worktree + real submodule — no fabricated short ids), **TDD-first**, **idempotency-preserving**
(NFR-004 — no on-disk worktree/coord churn), ruff+mypy clean ≤15 no suppressions, **C-008 Fix-don't-litigate**
(fix adjacent breakage in the same change, don't litigate pre-existing-vs-introduced).

**Clean-before-touch sequencing (D-9):** WP01 (characterization net) + WP02's internal de-dup land the
groundwork that makes every later deletion provable; adoption WPs then each consume the already-merged
factory (an import, not a shared edit); WP08 (keystone + ratchet) lands last.

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|----|----------|
| T001 | Build shared topology-true fixture module (full ULID + real coord-worktree + real submodule) | WP01 | |
| T002 | FR-004 before/after write-target divergence characterization (RED-on-HEAD, drives WITHOUT explicit repo_root) | WP01 | [P] |
| T003 | Coord-topology root/surface parity characterization for all 5 root-walk sites | WP01 | [P] |
| T004 | Submodule-topology characterization | WP01 | [P] |
| T005 | `store.py::_find_mission_specs_root` + real-coord lanes-placement characterization | WP01 | [P] |
| T006 | Public lock-root behavioral invariant (replaces paula S-4/S-9 private-by-name coverage) | WP01 | [P] |
| T007 | Extract byte-identical lock-root resolver (emit ≡ wpl) into one `workspace/root_resolver.py` helper | WP02 | |
| T008 | Route `emit.py::_feature_status_lock_root` to consume `workspace.primary_root` via the helper; delete the `.parent.parent` walk | WP02 | |
| T009 | Route `work_package_lifecycle.py` 3× root walk to `workspace.primary_root` via the helper; delete the walk | WP02 | |
| T010 | Retire the private-helper by-name tests in test_emit.py / test_work_package_lifecycle.py (public invariant now in the net) | WP02 | |
| T011 | Verification-by-deletion: net + status/lifecycle suite green | WP02 | |
| T012 | ruff/mypy clean, complexity ≤15 (WP02 surface) | WP02 | |
| T013 | Route `lifecycle_events.py` `.parent.parent`/`.parent.parent.parent` walks to `workspace.primary_root`; delete | WP03 | [P] |
| T014 | Route `store.py` `KITTY_SPECS_DIR` ancestor scan to `workspace.primary_root`; delete (PR-3 early-return tidy in-WP boy-scout) | WP03 | [P] |
| T015 | Verification-by-deletion: net + store/lifecycle suite green | WP03 | |
| T016 | ruff/mypy clean (WP03 surface) | WP03 | |
| T017 | PR-5 pre-refactor: extract the placement-compose helper (collapse the `:384` reuse + `:396` create joins) | WP04 | [P] |
| T018 | Route the placement join to the factory placement projection (`CommitTarget`/`resolve_placement_only`); naming stays via `mission_dir_name` | WP04 | |
| T019 | Idempotency: before/after on-disk placement path identical (no worktree churn) | WP04 | |
| T020 | ruff/mypy clean (WP04 surface); optional boy-scout the orthogonal `:304` DeprecationWarning if due | WP04 | |
| T021 | Route `_repo_root_for_feature` (R5) `.parent.parent` walk to `workspace.primary_root` | WP05 | |
| T022 | Route the status write **surface** to `status_surface.status_write_dir` (coord authority — C-007; never `primary_root`) | WP05 | |
| T023 | Route the write-**target** (`coord_branch or _current_branch`) to `branch_ref.destination_ref` (FR-004) | WP05 | |
| T024 | Reduce the `_identity_for_request` second-factory body to consume the projection (FR-007); defer the S2 selection ladder (#1716) | WP05 | |
| T025 | Idempotency before/after on-disk-target test + D-5 read==write equivalence (primary/coord/submodule) | WP05 | |
| T026 | ruff/mypy clean ≤15 (WP05 surface — the highest-risk file) | WP05 | |
| T027 | Route the lanes-dir write (`_lanes_feature_dir` C-LANES-1 region) through `resolve_lanes_dir(<coord feature dir from status_surface>)` (FR-008) | WP06 | [P] |
| T028 | Thin lanes projection in `lanes/persistence.py` only if needed (prefer deriving from `status_surface` + the existing seam — C-001) | WP06 | |
| T029 | Verify lanes.json still lands on the coord authority under coord topology; flat under no-coord (net S-8) | WP06 | |
| T030 | ruff/mypy clean (WP06 surface) | WP06 | |
| T031 | Delete the `prompt_source` fragment (`resolution.py:761-778,908,929` + `context.py:181,246,254`) | WP07 | [P] |
| T032 | Delete the dead `StatusSurfaceFragment.surface=` read-param wiring (`aggregate.py:199` + the `if surface is not None` branch) | WP07 | |
| T033 | Atomically retire the S-2/S-3 tests that encode the FR-006 deletion targets as contracts | WP07 | |
| T034 | Verification-by-deletion: suite green after deletion; ruff/mypy clean | WP07 | |
| T035 | KEYSTONE simple-case test: all-targets-base on a real single-branch repo (full ULID, no coord, no lanes) | WP08 | |
| T036 | Assert every adopted fragment == base; ZERO `.worktrees/`/coord paths read or written; byte-identical to pre-lane flat | WP08 | |
| T037 | FR-005 boundary ratchet (optional): extend `tests/architectural/` to flag write-side re-derivation in the adopted modules | WP08 | |
| T038 | Confirm SC-007/SC-008 green on the merged adoption tree | WP08 | |
| T039 | Author the user Explanation page: branch-target routing table + the simple case (SOURCE `docs/`) | WP09 | [P] |
| T040 | Add the docs-freshness page-inventory row; docs-freshness green | WP09 | |
| T041 | Cross-link from the lanes/coordination explanation surface; verify Divio "Explanation" classification | WP09 | |

---

## WP01 — Characterization net (clean-before-touch, FIRST)

**Goal**: Build the topology-true characterization net that makes every later deletion provable, fixing
paula's **live-evidence trap** — the strongest write-path suite passes `repo_root=` everywhere so it is
BLIND to the swap, and the FR-004 write-target divergence has **zero** witnessing test today.
**Priority**: P0 (gate). **Independent test**: the net is RED where the latent FR-004 divergence lives and
GREEN elsewhere on HEAD; it drives **without** explicit `repo_root` on real coord + submodule topologies.
**Dependencies**: none. **Sequence**: FIRST — all adoption WPs depend on it.

- [x] T001 Build shared topology-true fixture module (WP01)
- [x] T002 FR-004 before/after write-target divergence characterization, RED-on-HEAD (WP01)
- [x] T003 Coord-topology root/surface parity for all 5 root-walk sites (WP01)
- [x] T004 Submodule-topology characterization (WP01)
- [x] T005 store._find_mission_specs_root + real-coord lanes-placement characterization (WP01)
- [x] T006 Public lock-root behavioral invariant (WP01)

Owns the new `tests/specify_cli/write_side/` net + fixtures only — no src, no existing per-site test files.

## WP02 — Lock-root consolidation + primary_root adoption (IC-DEDUP + IC-EMIT + IC-WPL)

**Goal**: Collapse the byte-identical `emit::_feature_status_lock_root` ≡ `wpl::_repo_root_for_lock` into one
shared helper (D-4/D-9 PR-1), then route it to `workspace.primary_root` — deleting both `.parent.parent`
walks. Merged into ONE WP because both edits touch `emit.py` + `work_package_lifecycle.py` (separate WPs
would overlap ownership). **Priority**: P1. **Independent test**: the net (WP01) stays green after the helper
extraction (behavior-preserving) and after the walk deletion (adoption). **Dependencies**: WP01.

- [x] T007 Extract the shared lock-root helper into `workspace/root_resolver.py` (WP02)
- [x] T008 Route emit.py to `workspace.primary_root` via the helper; delete the walk (WP02)
- [x] T009 Route work_package_lifecycle.py to `workspace.primary_root`; delete the walk (WP02)
- [x] T010 Retire the private-helper by-name tests (public invariant now in the net) (WP02)
- [x] T011 Verification-by-deletion: net + status/lifecycle suite green (WP02)
- [x] T012 ruff/mypy clean ≤15 (WP02)

## WP03 — Status root-walk adoption (IC-LE + IC-STORE)

**Goal**: Route the `lifecycle_events.py` + `store.py` root walks/ancestor-scan to `workspace.primary_root`,
deleting them. Merged (two tiny same-concern status sites). **Priority**: P1. **Independent test**: net green
after deletion. **Dependencies**: WP01.

- [x] T013 Route lifecycle_events.py walks to `workspace.primary_root`; delete (WP03)
- [x] T014 Route store.py ancestor scan to `workspace.primary_root`; delete (+ PR-3 early-return tidy) (WP03)
- [x] T015 Verification-by-deletion: net + store/lifecycle suite green (WP03)
- [x] T016 ruff/mypy clean (WP03)

## WP04 — Placement adoption (IC-WT)

**Goal**: Replace the two `core/worktree.py` placement joins with the factory placement projection; naming
stays via the `mission_dir_name` seam. **Priority**: P1. **Independent test**: before/after on-disk placement
path identical (idempotency). **Dependencies**: WP01.

- [x] T017 PR-5 pre-refactor: extract the placement-compose helper (WP04)
- [x] T018 Route the join to the factory placement projection (WP04)
- [x] T019 Idempotency: before/after on-disk placement path identical (WP04)
- [x] T020 ruff/mypy clean; optional boy-scout the orthogonal :304 DeprecationWarning if due (WP04)

## WP05 — Coordination root + surface + write-target (IC-COORD) [highest risk]

**Goal**: In `coordination/status_transition.py`: route R5 root → `workspace.primary_root`; the status write
**surface** → `status_surface.status_write_dir` (coord authority, C-007 — never `primary_root`); the write-**target**
→ `branch_ref.destination_ref` (FR-004); reduce the `_identity_for_request` second factory to consume the
projection (FR-007). DEFER only the S2 selection ladder (#1716). **Priority**: P1 (med-high). **Independent
test**: D-5 read==write equivalence across primary/coord/submodule + before/after on-disk-target idempotency.
**Dependencies**: WP01.

- [x] T021 Route _repo_root_for_feature (R5) to `workspace.primary_root` (WP05)
- [x] T022 Route the status write surface to `status_surface.status_write_dir` (coord authority) (WP05)
- [x] T023 Route the write-target to `branch_ref.destination_ref` (FR-004) (WP05)
- [x] T024 Reduce _identity_for_request to consume the projection (FR-007); defer S2 (WP05)
- [x] T025 Idempotency before/after on-disk-target + D-5 equivalence test (WP05)
- [x] T026 ruff/mypy clean ≤15 (WP05)

## WP06 — Lanes/coord adoption (IC-LANES, FR-008)

**Goal**: Route the lanes-dir write (`_lanes_feature_dir` C-LANES-1 region in `cli/commands/implement.py`)
through `resolve_lanes_dir(<coord feature dir from status_surface>)` so `lanes.json` resolves from the coord
authority (C-LANES-1/#1991). Prefer deriving from the existing `status_surface` + the `resolve_lanes_dir`
seam over a raw factory field (C-001). **Priority**: P2. **Independent test**: lanes.json lands on coord under
coord topology, flat under no-coord (net S-8). **Dependencies**: WP01.

- [x] T027 Route the lanes-dir write through `resolve_lanes_dir(<coord feature dir>)` (WP06)
- [x] T028 Thin lanes projection in persistence.py only if needed (WP06)
- [x] T029 Verify lanes.json coord-vs-flat placement (WP06)
- [x] T030 ruff/mypy clean (WP06)

## WP07 — Fragment-scaffolding retirement (IC-RETIRE, FR-006)

**Goal**: Delete the genuinely-dead `prompt_source` fragment + the dead `StatusSurfaceFragment.surface=`
read-param wiring (0 readers, grep-proved). Retire the S-2/S-3 tests that encode these deletion targets as
contracts **atomically** in the same change. **Priority**: P2. **Independent test**: suite green after
deletion (deletion is its own proof). **Dependencies**: WP01.

- [x] T031 Delete the prompt_source fragment (resolution.py + context.py) (WP07)
- [x] T032 Delete the surface= read-param wiring (aggregate.py) (WP07)
- [x] T033 Atomically retire the S-2/S-3 contract-encoding tests (WP07)
- [x] T034 Verification-by-deletion: suite green; ruff/mypy clean (WP07)

## WP08 — Keystone simple-case test + boundary ratchet (IC-SIMPLECASE, FR-005)

**Goal**: The binding "all-targets-base → flat" keystone (NFR-006/SC-007) + the optional FR-005 boundary
ratchet (lands last so it doesn't flag not-yet-adopted sites). On a real single-branch repo (full ULID, no
coord, no lanes): every adopted fragment resolves to base, ZERO `.worktrees/`/coord paths read or written,
byte-identical to pre-lane flat. **Priority**: P1 (final guard). **Independent test**: the keystone itself.
**Dependencies**: WP02, WP03, WP04, WP05, WP06 (it integration-tests the adoptions).

- [x] T035 KEYSTONE simple-case test: all-targets-base on a real single-branch repo (WP08)
- [x] T036 Assert every fragment == base; ZERO coord/lane paths; byte-identical to flat (WP08)
- [x] T037 FR-005 boundary ratchet (optional): flag write-side re-derivation in adopted modules (WP08)
- [x] T038 Confirm SC-007/SC-008 green on the merged adoption tree (WP08)

## WP09 — Branch-target user documentation (IC-DOCS, FR-009)

**Goal**: Author the user-facing Explanation page (Divio "Explanation") presenting the branch-target routing
table ("this is where everything goes") + the simple case, demystifying lane behaviour. SOURCE `docs/`;
docs-freshness page-inventory row. **Priority**: P2. **Independent test**: docs-freshness green; the page
classifies as Explanation. **Dependencies**: none (describes the finalized behaviour from the spec; land any time).

- [x] T039 Author the Explanation page: routing table + simple case (WP09)
- [x] T040 Add the docs-freshness page-inventory row; docs-freshness green (WP09)
- [x] T041 Cross-link from the lanes/coordination explanation surface (WP09)

---

## Dependencies & Parallelization

```
WP01 (net, FIRST) ──┬─> WP02 (lock-root)   ─┐
                    ├─> WP03 (le+store)     │
                    ├─> WP04 (placement)    ├─> WP08 (keystone + ratchet, LAST)
                    ├─> WP05 (coord) ───────┘
                    ├─> WP06 (lanes) ───────┘
                    └─> WP07 (retire)
WP09 (docs) ── independent, any time
```

- After WP01: WP02–WP07 run in parallel (disjoint owned files); WP09 anytime.
- WP08 lands last (integration keystone + the ratchet that must post-date adoption).
- **MVP**: WP01 + WP02 + WP05 (the net + the lock-root family + the highest-risk coordination
  root/surface/target) prove read/write symmetry end-to-end.

## Requirement Coverage

| WP | FRs |
|----|-----|
| WP01 | (NFR-001/002 enabler) |
| WP02 | FR-001 |
| WP03 | FR-001 |
| WP04 | FR-002 |
| WP05 | FR-001, FR-003, FR-004, FR-007 |
| WP06 | FR-008 |
| WP07 | FR-006 |
| WP08 | FR-005 |
| WP09 | FR-009 |

**Cross-cutting NFRs (no single owning WP — embedded in every WP's DoD + the acceptance-matrix negative
invariants NI-1..5):** NFR-003 (function-over-form / verification-by-deletion — the method of every adoption
WP), NFR-004 (idempotency — WP04/WP05/WP06 before/after assertions), NFR-005 (ruff/mypy ≤15, no suppressions —
every WP). NFR-001/002 (symmetry / topology-true fixtures) are owned by WP01.
