# Tasks: Read-Path / Error-Fidelity Adoption

**Mission**: `read-path-error-fidelity-adoption-01KV8NPC`
**Branch**: `feat/read-path-error-fidelity` (PRs to `main`)
**Source**: `plan.md` (IC-01..IC-07 + decisions D-1..D-7), `spec.md` (FR-001..FR-012), `contracts/behavioral-contracts.md`, `research/` (incl. `investigation-2/`, `investigation-3-readwrite/`), `docs/engineering_notes/context-factory-readwrite-symmetry/00-SYNTHESIS.md`

9 work packages, 43 subtasks. **C-001: adopt the existing resolver, do not build.** Zero `owned_files`
overlap. Function-over-form + verification-by-deletion; TDD-first for the five bugs that reproduce on
HEAD (`research/live-repro.md` + `investigation-2/debbie-reverify-missed.md`); topology-true fixtures
only (full 26-char ULID + real coord-worktree + real submodule — NO fabricated short ids). **WP01 lays
the single context-factory seam (D-6) so the deferred write-side (#1716/#1878) adopts against a frozen
seam.** Net-new surfaces M1/M2/M3 folded (D-7).

## Dependency graph / sequencing

```
WP01 (single context FACTORY + freeze + invariant + write-projection boundary — precondition)
  ├─> WP02 (next typed-error + M1 context-resolve)  ┐
  ├─> WP03 (mission.py entry)                        ├─ parallel (disjoint files)
  ├─> WP04 (decision authority)                      │
  ├─> WP05 (implement + #1993)                       │
  └─> WP09 (orchestrator typed-error + M3 fail-closed)┘
WP06 (root resolver)  — no dep, start anytime
WP07 (charter no-op)  — no dep, start anytime
WP08 (#1827 regression test, test-only) — no dep, start anytime
```

Immediately startable: **WP01, WP06, WP07, WP08**. After WP01 approved: **WP02, WP03, WP04, WP05, WP09**.

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|----|----------|
| T001 | TDD: build-time CONTEXT_INVARIANT_VIOLATION test | WP01 | |
| T002 | TDD: ExecutionContext immutability test | WP01 | |
| T003 | Freeze the ExecutionContext composite | WP01 | |
| T004 | Assert target_branch == branch_ref.target_branch at build | WP01 | |
| T005 | Assemble WP-bearing context in one shot (no post-freeze write) | WP01 | |
| T006 | Full-suite sweep; fix any mutator the freeze surfaces | WP01 | |
| T007 | TDD: next read-path-miss → typed code, not MISSION_NOT_FOUND | WP02 | |
| T008 | Preserve code+paths at runtime_bridge.py query_current_state | WP02 | |
| T009 | Preserve code+paths at runtime_bridge.py answer_decision_via_runtime | WP02 | |
| T010 | Preserve code at next_cmd.py _find_mission_slug | WP02 | |
| T011 | Emitter surfaces typed code+paths (mirror QueryModeValidationError) | WP02 | |
| T012 | Verification-by-deletion: collapse removed, suite green | WP02 | |
| T013 | TDD: setup-plan exact-one auto-select; >1 structured error | WP03 | |
| T014 | Add exact-one auto-select in setup_plan (not the shared helper) | WP03 | |
| T015 | TDD: is_committed true on primary-target-branch commit | WP03 | |
| T016 | Add primary-target-branch leg to is_committed + diagnostics | WP03 | |
| T017 | TDD: _commit_to_branch hash report + no-op-vs-wrong-surface | WP03 | |
| T018 | Fix _commit_to_branch (hash; distinguish no-op classes) | WP03 | |
| T019 | finalize-tasks: anchor read on primary root (#11 fail-closed) | WP03 | |
| T020 | TDD: decision open accepts coord handle; traversal token rejected | WP04 | |
| T021 | Delete escape-walk for resolved paths; repo_root from canonical authority | WP04 | |
| T022 | Structure the typed error (no raw traceback) at decision.py:103 | WP04 | |
| T023 | Keep _SAFE_SLUG_RE on raw token; confirm cmd_verify unaffected | WP04 | |
| T024 | TDD: implement consumes claim's resolved context (no "no workspace") | WP05 | |
| T025 | Route implement to single resolution path (workflow.py) | WP05 | |
| T026 | Extract resolve_lanes_dir(feature_dir) pure seam | WP05 | |
| T027 | Route ad-hoc lanes.json derivations through the seam | WP05 | |
| T028 | Unit test the seam + verification-by-deletion | WP05 | |
| T029 | TDD: resolve_canonical_root returns submodule root (real submodule) | WP06 | [P] |
| T030 | Fix paths.py submodule boundary (mirror locate_project_root) | WP06 | [P] |
| T031 | Equivalence test {primary, coord, submodule}: both resolvers agree | WP06 | [P] |
| T032 | TDD: charter status side-effect-free + JSON-safe hash | WP07 | [P] |
| T033 | Make status collectors side-effect-free | WP07 | [P] |
| T034 | Emit one normalized JSON-serializable hash | WP07 | [P] |
| T035 | #1827 full record→commit→assert + resume regression test (passes) | WP08 | [P] |
| T036 | #1827 falsification guard (broken ordering would fail) | WP08 | [P] |
| T037 | Name build_execution_context factory + write-projection boundary contract | WP01 | |
| T038 | M1: context mission-resolve typed-error pass-through | WP02 | |
| T039 | TDD: orchestrator endpoint emits typed code, not MISSION_NOT_FOUND (M2) | WP09 | [P] |
| T040 | M2: stop flattening StatusReadPathNotFound across the 8 endpoints | WP09 | [P] |
| T041 | TDD: coord-topology fail-closed guard fires for orchestrator status read (M3) | WP09 | [P] |
| T042 | M3: resolve identity via factory boundary; stop empty-mid8 seed | WP09 | [P] |
| T043 | M5: structure the typed error on cmd_verify (verify's own :421/:425 seam) | WP04 | |
| T044 | M4: decide on _find_first_for_review_wp parent-walk re-deriver (route or defer) — **DECISION: CONSCIOUS DEFERRAL.** Review-mode discovery helper (not operator-facing read-path fidelity), low blast radius; its worktree-local-first/walk/repo_root read intent is not preserved by the coord-aware resolver, so routing would change read-anchor semantics beyond #1832's fragment-adopt scope (D-1 minimal carry). Recorded in-code at `workflow.py` `_find_first_for_review_wp`. | WP05 | |

## FR Coverage

| WP | Spec FRs |
|----|----------|
| WP01 | FR-009 |
| WP02 | FR-001, FR-002 |
| WP03 | FR-004, FR-005, FR-006 |
| WP04 | FR-003 |
| WP05 | FR-008, FR-011 |
| WP06 | FR-007 |
| WP07 | FR-010 |
| WP08 | FR-012 |
| WP09 | FR-001, FR-011 |

---

## WP01 — Single context factory + freeze + build-invariant + write-projection boundary (IC-01)
- **Goal**: Name the single context factory (`build_execution_context`), freeze the composite, assert the build-invariant, and declare the write-projection boundary contract (D-6) — the trustworthy-context precondition + the read/write-symmetry seam.
- **Priority**: P0 (precondition for WP02–WP05, WP09). **Dependencies**: none.
- **Independent test**: building a context with `target_branch != branch_ref.target_branch` raises `CONTEXT_INVARIANT_VIOLATION`; mutating a built context raises; `resolve_action_context` delegates to the factory.
- **Prompt**: `tasks/WP01-context-factory-invariant.md`

- [x] T001 TDD: build-time CONTEXT_INVARIANT_VIOLATION test (WP01)
- [x] T002 TDD: ExecutionContext immutability test (WP01)
- [x] T003 Freeze the ExecutionContext composite (WP01)
- [x] T004 Assert target_branch == branch_ref.target_branch at build (WP01)
- [x] T005 Assemble WP-bearing context in one shot via the factory (no post-freeze write) (WP01)
- [x] T006 Full-suite sweep; fix any mutator the freeze surfaces (WP01)
- [x] T037 Name build_execution_context factory (sole door; resolve_action_context delegates) + write-projection boundary contract docstring/__all__ (WP01)

## WP02 — `next` typed-error pass-through + M1 context-resolve (IC-02)
- **Goal**: Preserve `ActionContextError.code`+checked-paths across the three `next`-family catch-sites AND `context mission-resolve` (M1); closes #12/#14/#15 (+M1) with no resolver change.
- **Priority**: P0. **Dependencies**: WP01.
- **Independent test**: `next` and `context mission-resolve` on a read-path miss emit the resolver's real code + checked paths, never `MISSION_NOT_FOUND`/"check the slug".
- **Prompt**: `tasks/WP02-next-typed-error-passthrough.md`

- [x] T007 TDD: next read-path-miss → typed code, not MISSION_NOT_FOUND (WP02)
- [x] T008 Preserve code+paths at runtime_bridge query_current_state (WP02)
- [x] T009 Preserve code+paths at runtime_bridge answer_decision_via_runtime (WP02)
- [x] T010 Preserve code at next_cmd _find_mission_slug (WP02)
- [x] T011 Emitter surfaces typed code+paths (WP02)
- [x] T012 Verification-by-deletion: collapse removed, suite green (WP02)
- [x] T038 M1: context mission-resolve preserves the typed code (resolver.py:164) (WP02)

## WP03 — `mission.py` planning-entry adoption (IC-03)
- **Goal**: setup-plan exact-one auto-select; is_committed primary-target-branch leg; _commit_to_branch hash + no-op-vs-wrong-surface; finalize-tasks primary-anchored read.
- **Priority**: P0. **Dependencies**: WP01. **Sole owner** of `agent/mission.py` + `_substantive.py`.
- **Independent test**: single-mission repo → setup-plan needs no `--mission`; spec committed on primary target branch → `spec_committed: true`.
- **Prompt**: `tasks/WP03-mission-planning-entry.md`

- [x] T013 TDD: setup-plan exact-one auto-select; >1 structured error (WP03)
- [x] T014 Add exact-one auto-select in setup_plan (not the shared helper) (WP03)
- [x] T015 TDD: is_committed true on primary-target-branch commit (WP03)
- [x] T016 Add primary-target-branch leg to is_committed + diagnostics (WP03)
- [x] T017 TDD: _commit_to_branch hash + no-op-vs-wrong-surface (WP03)
- [x] T018 Fix _commit_to_branch (hash; distinguish no-op classes) (WP03)
- [x] T019 finalize-tasks: anchor read on primary root (#11) (WP03)

## WP04 — `decision` single authority (IC-04)
- **Goal**: Delete the primary-anchored escape-walk for resolved paths; structure the typed error.
- **Priority**: P1. **Dependencies**: WP01.
- **Independent test**: valid coord-aware handle → `decision open` succeeds; raw traversal token still rejected; no raw traceback.
- **Prompt**: `tasks/WP04-decision-single-authority.md`

- [x] T020 TDD: decision open accepts coord handle; traversal rejected (WP04)
- [x] T021 Delete escape-walk for resolved paths; repo_root from canonical authority (WP04)
- [x] T022 Structure the typed error at decision.py:103 (WP04)
- [x] T023 Keep _SAFE_SLUG_RE on raw token; confirm cmd_verify unaffected (WP04)
- [x] T043 M5: structure the typed error on cmd_verify (its own :421/:425 seam) (WP04)

## WP05 — implement single-resolution + #1993 lanes-dir seam (IC-05)
- **Goal**: `agent action implement` consumes the claim's resolved context; extract+route `resolve_lanes_dir`.
- **Priority**: P1. **Dependencies**: WP01.
- **Independent test**: implement after a verified claim never fails "no workspace could be resolved"; the lanes dir has one derivation.
- **Prompt**: `tasks/WP05-implement-single-resolution-lanes-seam.md`

- [x] T024 TDD: implement consumes claim's resolved context (WP05)
- [x] T025 Route implement to single resolution path (workflow.py) (WP05)
- [x] T026 Extract resolve_lanes_dir(feature_dir) pure seam (WP05)
- [x] T027 Route ad-hoc lanes.json derivations through the seam (WP05)
- [x] T028 Unit test the seam + verification-by-deletion (WP05)
- [x] T044 M4: decide on _find_first_for_review_wp parent-walk re-deriver (route or defer) (WP05)

## WP06 — root-resolver submodule unification (IC-06)
- **Goal**: `resolve_canonical_root` stops at the submodule boundary, agreeing with `locate_project_root`.
- **Priority**: P0 (launch-blocker #6/#2011). **Dependencies**: none.
- **Independent test**: from inside a real submodule, `resolve_canonical_root` returns the submodule root and `assert_initialized` does not raise.
- **Prompt**: `tasks/WP06-root-resolver-submodule.md`

- [x] T029 TDD: resolve_canonical_root returns submodule root (real submodule) (WP06)
- [x] T030 Fix paths.py submodule boundary (mirror locate_project_root) (WP06)
- [x] T031 Equivalence test {primary, coord, submodule} (WP06)

## WP07 — charter status side-effect-free + JSON-safe (IC-07)
- **Goal**: charter status/sync status is side-effect-free; one normalized JSON-serializable hash.
- **Priority**: P2. **Dependencies**: none.
- **Independent test**: `git status` unchanged across a `charter status` run; the emitted hash serializes.
- **Prompt**: `tasks/WP07-charter-status-no-op.md`

- [x] T032 TDD: charter status side-effect-free + JSON-safe hash (WP07)
- [x] T033 Make status collectors side-effect-free (WP07)
- [x] T034 Emit one normalized JSON-serializable hash (WP07)

## WP08 — #1827 baseline regression test (FR-012, test-only)
- **Goal**: Lock #1827 as verified-already-fixed with a full record→commit→assert + resume regression test (D-3 — NO code fix).
- **Priority**: P2. **Dependencies**: none.
- **Independent test**: the full sequence (incl. resume/re-run) passes; a falsification guard proves the broken ordering would fail.
- **Prompt**: `tasks/WP08-1827-baseline-regression.md`

- [x] T035 #1827 full record→commit→assert + resume regression test (WP08)
- [x] T036 #1827 falsification guard (WP08)

## WP09 — orchestrator-api typed-error + fail-closed identity (IC-02b: M2 + M3)
- **Goal**: M2 — stop flattening `StatusReadPathNotFound`→`MISSION_NOT_FOUND` across the 8 orchestrator endpoints (`commands.py:263-266`); M3 — stop seeding `resolve_mid8(slug, mission_id=None)`→empty mid8 (`:261`) which suppresses the coord-aware fail-closed guard. Resolve identity via the factory boundary (D-6).
- **Priority**: P1 (read-path SAFETY). **Dependencies**: WP01 (consumes the factory identity boundary).
- **Independent test**: an orchestrator status read on a read-path miss emits the typed code; on a coord topology the fail-closed guard fires (no stale primary read). Legacy `{slug}-{lane}` `mission_id=None` grammar (`:484/:787`) is untouched.
- **Prompt**: `tasks/WP09-orchestrator-typed-error-fail-closed.md`

- [x] T039 TDD: orchestrator endpoint emits typed code, not MISSION_NOT_FOUND (M2) (WP09)
- [x] T040 M2: stop flattening StatusReadPathNotFound across the 8 endpoints (WP09)
- [x] T041 TDD: coord-topology fail-closed guard fires for orchestrator status read (M3) (WP09)
- [x] T042 M3: resolve identity via factory boundary; stop empty-mid8 seed (WP09)
