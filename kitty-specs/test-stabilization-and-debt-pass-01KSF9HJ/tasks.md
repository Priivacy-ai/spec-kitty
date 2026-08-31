# Tasks — Test Stabilization & Architectural Debt Pass

**Mission**: `test-stabilization-and-debt-pass-01KSF9HJ`
**Mission ID**: `01KSF9HJBFKRBC617JVHKZXNE2`
**Planning base branch**: `kitty/mission-test-stabilization-and-debt-pass-01KSF9HJ`
**Merge target branch**: `main`
**Total WPs**: 11 (WP11 is the stretch from FR-008; numbered out-of-sequence to flag its stretch status. Counts against the NFR-004 ≤10 cap by 1 — accepted because LD-2 is mechanical test-only work)
**Total subtasks**: 41

## Wave map → Work-package map

| Wave | WP IDs | Theme |
|---|---|---|
| T — Test triage + targeted fixes | WP01, WP02, WP03, WP04 | Close #1298 by 70% |
| A — Architectural debt repayment | WP05, WP06, WP07, WP08, WP11 | LD-1, MS-1, LD-3, LD-5, LD-2 |
| Q — Small quality fixes | WP09, WP10, WP12 | #1163 + F-04 + F-10 + F-01 + finalize-tasks fix locks |

## Subtask Index

| ID | Description | WP | Parallel |
|---|---|---|---|
| T001 | DIR-012 assign #1298 to HiC | WP01 | |
| T002 | Run `pytest tests/ -q --tb=no` capturing all FAILED lines into a file | WP01 | |
| T003 | Cluster failures by test-file + by `tail`-truncated FAILED list; categorise root causes | WP01 | |
| T004 | Author `triage.md` enumerating clusters with hypothesised root cause + resolution (fix-here / sub-issue / skip) | WP01 | |
| T005 | Investigate `tests/sync/test_events.py::test_*` ModuleNotFoundError pattern; identify the missing import path | WP02 | |
| T006 | Apply the import fix (likely vendored-events path drift); add a regression test that asserts the import resolves | WP02 | |
| T007 | Verify all ~27 affected tests pass after fix | WP02 | |
| T008 | Fix `tests/test_dashboard/test_scanner.py::test_build_event_log_kanban_stats_tolerates_weighted_progress_failure` (tolerance window) | WP03 | [P] |
| T009 | Fix `tests/tasks/test_move_task_git_validation_unit.py::test_move_for_review_from_worktree_does_not_mirror_commit_to_lane_branch` (commit-message assertion) | WP03 | [P] |
| T010 | Run full `pytest tests/ -q` and capture the post-fix failure count | WP04 | |
| T011 | File follow-up sub-issues (#1298a, #1298b, ...) for residual clusters per triage.md | WP04 | |
| T012 | Verify NFR-001: post-mission failure count ≤ 75 | WP04 | |
| T013 | Update #1298 with a final delta comment + cross-references to sub-issues | WP04 | |
| T014 | Author the `_apply_overlay_layer(dirs, layer_name, *, built_in)` method in `src/doctrine/base.py` | WP05 | |
| T015 | Migrate `_apply_org_overrides` caller(s) to use `_apply_overlay_layer(self._org_dirs, "org", built_in=built_in)` | WP05 | |
| T016 | Migrate `_apply_project_overrides` caller(s) similarly with `dirs=[self._project_dir] if self._project_dir else []` | WP05 | |
| T017 | Delete the two old methods | WP05 | |
| T018 | Verify behaviour-preservation tests: `tests/doctrine/test_doctrine_layered_resolution.py` + `tests/doctrine/test_doctrine_layer_collision_warnings.py` green | WP05 | |
| T019 | Create `src/specify_cli/cli/commands/charter/__init__.py` (new package) with charter_app + the typer-app registration shim | WP06 | |
| T020 | Move `status`, `sync`, `synthesize`, `lint`, `preflight`, `bundle`, `resynthesize` handlers into per-file modules in the new package | WP06 | [P] |
| T021 | Leave `src/specify_cli/cli/commands/charter.py` as a ≤150-line re-export shim OR delete it if all imports redirect through the package | WP06 | |
| T022 | Verify charter integration tests green: `tests/specify_cli/cli/commands/test_charter_lint.py` + `tests/integration/test_charter_status_freshness.py` + `tests/integration/test_charter_lint_lints_all_layers.py` | WP06 | |
| T023 | Identify the canonical `ensure_charter_bundle_fresh` API surface in `charter.compiler` | WP07 | |
| T024 | Route `charter_freshness/computer.py:281` (`_safe_load_yaml(manifest_path)`) through the chokepoint | WP07 | |
| T025 | Route `charter_freshness/computer.py:280` (`_DOCTRINE_DIR / _GRAPH_FILENAME` direct read) through the chokepoint | WP07 | |
| T026 | Verify `compute_freshness(repo_root) -> CharterFreshness` public API unchanged (C-007) | WP07 | |
| T027 | Verify the data-model §6 conflict-resolution case: `tests/specify_cli/charter_freshness/test_computer.py::test_invalid_state_when_built_in_only_and_graph_yaml_both_exist` green | WP07 | |
| T028 | Create `src/specify_cli/charter_runtime/__init__.py` + 4 submodule directories (`lint/`, `freshness/`, `preflight/`, `facade/`) | WP08 | |
| T029 | Move package contents: `charter_lint/` → `charter_runtime/lint/`; `charter_freshness/` → `.../freshness/`; `charter_preflight/` → `.../preflight/`; `charter/` → `.../facade/` | WP08 | |
| T030 | Add shim re-export `__init__.py` at each of the four old paths so `from specify_cli.charter_lint import LintEngine` (etc.) still resolves | WP08 | |
| T031 | Add CHANGELOG entry under `[Unreleased]` naming the canonical new import paths + the deprecation window (C-008) | WP08 | |
| T032 | Add architectural regression test `tests/architectural/test_charter_runtime_shim_paths.py` asserting the 4 shim paths resolve | WP08 | |
| T033 | Verify the ~120-test charter-runtime smoke suite still green via the new + old import paths | WP08 | |
| T034 | (stretch) Author `tests/doctrine/test_augmentation_fields.py` with a parametrised matrix `(model_class, sample_yaml, kind_name)` and the 4 cases (neither/enhances-only/overrides-only/both) | WP11 | |
| T035 | (stretch) Delete the 5 per-kind test files; verify total test count ≥ 20 | WP11 | |
| T036 | DIR-012 assign #1163 to HiC | WP09 | |
| T037 | Detect GH issue references in `spec.md` (e.g. `#NNNN`) during `/spec-kitty.tasks` execution | WP09 | |
| T038 | Scaffold `kitty-specs/<slug>/issue-matrix.md` with a row per detected issue; columns matching the Gate-4 contract from spec-kitty-mission-review skill | WP09 | |
| T039 | F-04: Extend `spec-kitty retrospect create` generator to mine `status.events.jsonl` for `--force` / arbiter / cycle-N transitions; each becomes a `helped`/`not_helpful`/`gaps` entry | WP10 | [P] |
| T040 | F-10: Add optional `tracker_refs: list[str]` field to `WPMetadata` Pydantic model; accept in `map-requirements` and `move-task` | WP10 | [P] |
| T041 | F-01: Author `docs/reference/bulk-edit-gate.md` documenting the 4-value action enum + the required `target:` block; update `.kittify/doctrine/skills/spec-kitty-bulk-edit-classification/SKILL.md` to link there | WP10 | [P] |

---

## WP01 — Wave T triage (FR-001)

**Priority**: P0 (blocks Wave T's other WPs)
**Independent test**: `triage.md` exists, lists all failure clusters, each cluster has a resolution.
**Estimated prompt size**: ~140 lines
**Linked issue**: #1298
**Prompt file**: `tasks/WP01-wave-t-triage.md`

Subtasks:
- [x] T001 DIR-012 assign #1298 to HiC (WP01)
- [x] T002 Capture all FAILED lines into a file (WP01)
- [x] T003 Cluster failures by file + cause (WP01)
- [x] T004 Author `triage.md` (WP01)

Dependencies: none.

---

## WP02 — Wave T `tests/sync/test_events.py` fix (FR-002)

**Priority**: P0
**Independent test**: `pytest tests/sync/test_events.py -q` reports 0 failures.
**Estimated prompt size**: ~180 lines
**Linked issue**: #1298
**Prompt file**: `tasks/WP02-wave-t-sync-events-fix.md`

Subtasks:
- [x] T005 Investigate ModuleNotFoundError (WP02)
- [x] T006 Apply import fix + regression test (WP02)
- [x] T007 Verify ~27 affected tests pass (WP02)

Dependencies: WP01 (triage may reveal sub-clusters).

---

## WP03 — Wave T surgical fixes (FR-003, FR-004)

**Priority**: P0
**Independent test**: both targeted tests pass.
**Estimated prompt size**: ~150 lines
**Linked issue**: #1298
**Prompt file**: `tasks/WP03-wave-t-surgical-fixes.md`

Subtasks:
- [x] T008 [P] Dashboard scanner tolerance fix (WP03)
- [x] T009 [P] Move-task commit-message contract fix (WP03)

Dependencies: WP01.

---

## WP04 — Wave T triage closeout (FR-005)

**Priority**: P0
**Independent test**: `pytest tests/ -q` ≤ 75 failures; sub-issues filed for residual clusters; #1298 commented.
**Estimated prompt size**: ~120 lines
**Linked issue**: #1298
**Prompt file**: `tasks/WP04-wave-t-closeout.md`

Subtasks:
- [x] T010 Capture post-fix failure count (WP04)
- [x] T011 File follow-up sub-issues (WP04)
- [x] T012 Verify NFR-001 ceiling (WP04)
- [x] T013 Update #1298 (WP04)

Dependencies: WP02, WP03.

---

## WP05 — Wave A LD-1 overlay-layer consolidation (FR-006)

**Priority**: P1
**Independent test**: `tests/doctrine/test_doctrine_layered_resolution.py` + `tests/doctrine/test_doctrine_layer_collision_warnings.py` green; `git grep "def _apply_.*_overrides" src/doctrine/base.py` returns ≤ 1 hit.
**Estimated prompt size**: ~190 lines
**Prompt file**: `tasks/WP05-wave-a-overlay-layer-consolidation.md`

Subtasks:
- [x] T014 Author `_apply_overlay_layer` (WP05)
- [x] T015 Migrate org caller (WP05)
- [x] T016 Migrate project caller (WP05)
- [x] T017 Delete the two old methods (WP05)
- [x] T018 Verify behaviour-preservation tests (WP05)

Dependencies: none (doctrine package is independent of charter*).

---

## WP06 — Wave A MS-1 charter.py per-subcommand split (FR-007)

**Priority**: P1
**Independent test**: `wc -l src/specify_cli/cli/commands/charter.py` ≤ 150; each new per-subcommand module ≤ 500 lines; integration tests still green.
**Estimated prompt size**: ~220 lines
**Prompt file**: `tasks/WP06-wave-a-charter-split.md`

Subtasks:
- [x] T019 Create new `charter/` package + typer-app shim (WP06)
- [x] T020 [P] Move 7 subcommand handlers (WP06)
- [x] T021 Reduce/delete old `charter.py` (WP06)
- [x] T022 Verify charter integration tests (WP06)

Dependencies: WP05 (sequenced within Wave A per plan).

---

## WP07 — Wave A LD-3 chokepoint routing (FR-013)

**Priority**: P1
**Independent test**: `compute_freshness()` public API unchanged; data-model §6 conflict-resolution test green; no direct `_safe_load_yaml` of manifest/graph paths in `charter_freshness/`.
**Estimated prompt size**: ~180 lines
**Prompt file**: `tasks/WP07-wave-a-chokepoint-routing.md`

Subtasks:
- [x] T023 Identify `ensure_charter_bundle_fresh` API surface (WP07)
- [x] T024 Route manifest read through chokepoint (WP07)
- [x] T025 Route graph read through chokepoint (WP07)
- [x] T026 Verify public API unchanged (WP07)
- [x] T027 Verify data-model §6 conflict-case test (WP07)

Dependencies: WP06.

---

## WP08 — Wave A LD-5 charter_runtime/ umbrella (FR-014)

**Priority**: P1
**Independent test**: 4 new submodule directories under `charter_runtime/`; 4 shim `__init__.py` at old paths re-export canonical symbols; ~120-test charter-runtime suite green via both old and new import paths; CHANGELOG entry present.
**Estimated prompt size**: ~230 lines
**Prompt file**: `tasks/WP08-wave-a-charter-runtime-umbrella.md`

Subtasks:
- [x] T028 Create `charter_runtime/` package (WP08)
- [x] T029 Move 4 package directories (WP08)
- [x] T030 Add shim re-exports at old paths (WP08)
- [x] T031 CHANGELOG entry (C-008) (WP08)
- [x] T032 New architectural shim-path test (WP08)
- [x] T033 Verify ~120-test smoke suite (WP08)

Dependencies: WP07.

---

## WP11 — Wave A LD-2 augmentation-test parametrisation (FR-008, stretch)

**Priority**: P2 (stretch — droppable per NFR-004 if WP count creeps)
**Independent test**: 5 old test files removed; 1 new parametrised file passes; total assertion count ≥ 20.
**Estimated prompt size**: ~140 lines
**Prompt file**: `tasks/WP11-wave-a-augmentation-test-parametrisation.md`

Subtasks:
- [x] T034 Author parametrised `test_augmentation_fields.py` (WP11)
- [x] T035 Delete 5 per-kind test files (WP11)

Dependencies: none — independent from WP05-08 surfaces.

---

## WP09 — Wave Q issue-matrix scaffold (FR-009)

**Priority**: P2
**Independent test**: `/spec-kitty.tasks` on a fixture mission whose spec references `#NNNN` emits a populated `issue-matrix.md`.
**Estimated prompt size**: ~160 lines
**Linked issue**: #1163
**Prompt file**: `tasks/WP09-wave-q-issue-matrix-scaffold.md`

Subtasks:
- [x] T036 DIR-012 assign #1163 to HiC (WP09)
- [x] T037 Detect GH issue references in spec.md (WP09)
- [x] T038 Scaffold issue-matrix.md (WP09)

Dependencies: none (independent of Wave A; parallel-safe).

---

## WP10 — Wave Q composite small fixes (FR-010, FR-011, FR-012)

**Priority**: P2
**Independent test**: each of the three sub-fixes has a regression test exercising the new behaviour.
**Estimated prompt size**: ~200 lines
**Prompt file**: `tasks/WP10-wave-q-composite-small-fixes.md`

Subtasks:
- [x] T039 [P] F-04 retro-generator event-log mining (WP10)
- [x] T040 [P] F-10 `tracker_refs` field on `WPMetadata` (WP10)
- [x] T041 [P] F-01 bulk-edit-gate docs (WP10)

Dependencies: none.

---

## WP12 — Wave Q finalize-tasks fix locks (FR-015)

**Priority**: P2
**Independent test**: regression tests for explicit `owned_files: []` honouring + cycle-safe `_compute_lane_depths`; new reference doc at `docs/reference/finalize-tasks-internals.md`.
**Estimated prompt size**: ~250 lines
**Prompt file**: `tasks/WP12-wave-q-finalize-tasks-fixes-lock.md`

Subtasks:
- [x] T042 [P] Linter explicit-empty regression test (WP12)
- [x] T043 [P] Lane-depth cycle-safety regression test (WP12)
- [x] T044 [P] Reference doc at docs/reference/finalize-tasks-internals.md (WP12)

Dependencies: none. The two production fixes already landed on main (commits `0f4e1a383` and `72ff0d723`); this WP locks them with tests so a future refactor can't silently undo them.

---

## Parallelisation highlights

- **Wave T**: WP02, WP03 are independent after WP01 lands triage.md. WP04 is the closeout gate.
- **Wave A**: WP05 (doctrine) is independent of WP06/WP07/WP08 (charter package surface). WP11 is independent of WP05-08. WP06 → WP07 → WP08 MUST sequence.
- **Wave Q**: WP09 and WP10 fully independent.
- **Cross-wave**: Wave T must complete before Wave A and Wave Q because Wave T's test-fix work establishes the baseline against which architectural-refactor regressions can be measured (NFR-002). Wave A and Wave Q can run in parallel with each other.

## MVP scope recommendation

If the mission needs to ship something before all 10 WPs land, the MVP is **Wave T (WP01-04)** — that closes #1298 sufficient enough to mark NFR-001 met. Wave A and Wave Q are deliberately bounded "while we're in here" debt repayment; they can ship in a follow-up if release pressure mounts.
