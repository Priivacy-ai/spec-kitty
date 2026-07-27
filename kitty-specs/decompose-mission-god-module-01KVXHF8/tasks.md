---
description: "Work package task list for decomposing agent/mission.py (remainder) — #2056"
---

# Work Packages: Decompose `agent/mission.py` god-module (remainder) (#2056)

**Inputs**: Design documents from `kitty-specs/decompose-mission-god-module-01KVXHF8/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/cli-surface-contract.md, quickstart.md

**Tests**: Tests are integral to this mission (FR-004 / FR-005 / NFR-002) — every seam and every extracted
phase helper ships focused tests in the same WP.

**Organization**: STRICTLY-LINEAR chain — WP02 depends on WP01, WP03 on WP02, … WP09 on WP08. Each seam WP
owns its new module(s) + test(s); `agent/mission.py` is owned SOLELY by the final WP (WP09). The
commit_router relocation WP (WP08) owns `coordination/commit_router.py` + the relocated code and touches
`tasks.py`'s single import line (out-of-map, documented).

**Profile**: all WPs use `randy-reducer` (semantic compression — behavior-preserving reduction).

## Subtask Format: `[Txxx] Description`

- Include precise file paths or modules. Tests live beside the seam they cover.

---

## Work Package WP01: Golden CLI characterization harness (Priority: P0)

**Goal**: Capture the byte-for-byte `agent mission` CLI surface (8 commands × all flags + JSON envelopes)
as an executable golden test BEFORE any extraction.
**Independent Test**: `pytest tests/specify_cli/cli/commands/agent/test_mission_cli_golden_contract.py` is
green against the base; asserts 8 commands, exact flags, representative success/error envelopes.
**Prompt**: `/tasks/WP01-golden-cli-characterization.md`
**Requirement Refs**: FR-001, C-001, C-005

### Included Subtasks

- [x] T001 Author `tests/specify_cli/cli/commands/agent/test_mission_cli_golden_contract.py` (CliRunner): assert `app --help` lists exactly the 8 commands.
- [x] T002 Assert each subcommand `--help` lists its exact flags + defaults per `contracts/cli-surface-contract.md`.
- [x] T003 Assert representative success JSON envelopes (`branch-context --json`, `check-prerequisites --json`) keys.
- [x] T004 Assert representative error JSON envelope (`setup-plan` `PLAN_CONTEXT_UNRESOLVED`) keys + extend `tests/integration/test_json_envelope_strict.py` cross-reference.

### Dependencies

- None (starting package).

---

## Work Package WP02: Feature-dir resolution seam (Seam D) (Priority: P0)

**Goal**: Extract the shared resolution surface (`_find_feature_directory` & friends) into
`mission_feature_resolution.py` FIRST so later seams import a stable surface.
**Independent Test**: `pytest tests/specify_cli/cli/commands/agent/test_mission_feature_resolution.py` —
direct resolution tests ≥90%; golden test (WP01) still green.
**Prompt**: `/tasks/WP02-feature-resolution-seam.md`
**Requirement Refs**: FR-003, FR-004, FR-006, NFR-001, NFR-005

### Included Subtasks

- [x] T005 Create `mission_feature_resolution.py`; move `_find_feature_directory`, `_resolve_mission_dir_name_primary_anchored`, `_primary_anchored_feature_dir`, `_list_feature_spec_candidates`, `_sole_mission_slug_or_none`, `_build_setup_plan_detection_error`, `_safe_load_meta`, `_read_feature_meta`.
- [x] T006 Repoint in-module references in `mission.py` to import from the new seam (out-of-map import edit, documented).
- [x] T007 Author `test_mission_feature_resolution.py` with DIRECT unit tests for the resolvers (≥90%).
- [x] T008 Run golden test + ruff/mypy on touched files; confirm one-way imports (seam → lower layers only).

### Dependencies

- Depends on WP01.

---

## Work Package WP03: Parsing & validation seam (Seam C) (Priority: P0)

**Goal**: Extract tasks.md/spec.md parsers, owned-files validation, and JSON emit shims into
`mission_parsing.py`; give the pure parsers DIRECT unit tests (current coverage gap).
**Independent Test**: `pytest tests/specify_cli/cli/commands/agent/test_mission_parsing.py` ≥90%; golden
test green; `tasks.py` still resolves `_parse_requirement_refs_from_tasks_md`.
**Prompt**: `/tasks/WP03-parsing-validation-seam.md`
**Requirement Refs**: FR-003, FR-004, FR-006, NFR-001, NFR-002

### Included Subtasks

- [x] T009 Create `mission_parsing.py`; move the 6 parsers, the 5 owned-files validators, and the 5 JSON emit shims (`_emit_json`/`_with_cli_version`/`_with_mission_aliases`/`_emit_console_or_json_error`/`_utc_now_iso`).
- [x] T010 Repoint `mission.py` in-module references to the new seam (documented import edits).
- [x] T011 Author `test_mission_parsing.py` with DIRECT unit tests per parser/validator/shim.
- [x] T012 Confirm JSON-envelope keys unchanged (golden + `test_json_envelope_strict.py`); ruff/mypy clean.

### Dependencies

- Depends on WP02.

---

## Work Package WP04: Record-analysis seam (Seam A) (Priority: P1)

**Goal**: Extract `record_analysis` + its 2 dedicated helpers into `mission_record_analysis.py` (lowest-risk command slice).
**Independent Test**: `pytest tests/specify_cli/cli/commands/agent/test_mission_record_analysis.py` and the
existing `test_record_analysis_coord_worktree.py` green; golden test green.
**Prompt**: `/tasks/WP04-record-analysis-seam.md`
**Requirement Refs**: FR-003, FR-004, FR-006, NFR-001

### Included Subtasks

- [x] T013 Create `mission_record_analysis.py`; move `record_analysis`, `_enforce_analysis_report_write_preflight`, `_resolve_record_analysis_placement_ref`; keep `commit_for_mission` import lazy.
- [x] T014 Register the command via the seam in the shim path (documented); repoint references.
- [x] T015 Author `test_mission_record_analysis.py`; extend (do not replace) `test_record_analysis_coord_worktree.py` coverage.
- [x] T016 Golden test + ruff/mypy clean on touched files.

### Dependencies

- Depends on WP03.

---

## Work Package WP05: Lifecycle families I — branch_context + create_mission + check_prerequisites (Priority: P1)

**Goal**: Move `branch_context`, `create_mission`, `check_prerequisites` into per-family modules,
internally decomposing `create_mission` (281 LOC) into `<=15`-CC phase helpers, each with a focused test.
**Independent Test**: `pytest` of the new family tests + existing `test_mission_create.py`,
`test_create_feature_branch*.py`; golden test green.
**Prompt**: `/tasks/WP05-lifecycle-families-create.md`
**Requirement Refs**: FR-003, FR-004, FR-005, FR-006, NFR-001, NFR-002

### Included Subtasks

- [x] T017 Create `mission_branch_context.py`; move `branch_context` + `_inject_branch_contract` + branch helpers (`_resolve_primary_branch_for_recommendation`, `_git_local_or_remote_branch_exists`, `_switch_to_start_branch`, `_show_branch_context`, `_resolve_planning_branch`, `_resolve_feature_target_branch`, `_get_current_branch`).
- [x] T018 Create `mission_create.py`; move `create_mission` and decompose into phase helpers (scaffold → meta write → coordination-branch creation → branch-contract injection → event emit), each `<=15` CC.
- [x] T019 Create `mission_check_prerequisites.py`; move `check_prerequisites` + emit helpers (`_emit_check_prerequisites_detection_error`, `_emit_check_prerequisites_result`, `_paths_only_payload`) + `_read_meta_for_pr_bound`/`_read_meta_for_emission`.
- [x] T020 Author focused tests for each new phase helper; extend existing create/branch tests; documented import edits in `mission.py`.
- [x] T021 Golden test + ruff/mypy clean; confirm no function over CC 15.

### Dependencies

- Depends on WP04.

---

## Work Package WP06: Lifecycle families II — setup_plan + accept/merge (Priority: P1)

**Goal**: Move `setup_plan` (decomposing its 507 LOC into phase helpers) into `mission_setup_plan.py`
(with `_commit_to_branch`, `CommitToBranchResult`, `_kind_for_artifact`, `_artifact_*` helpers), and move
the thin delegators `accept_feature`/`merge_feature` into `mission_accept_merge.py`.
**Independent Test**: `pytest` of new tests + `test_agent_mission_commit_to_branch.py`,
`test_kind_for_artifact.py`, accept/merge tests; golden test green.
**Prompt**: `/tasks/WP06-lifecycle-families-setup-plan-accept-merge.md`
**Requirement Refs**: FR-003, FR-004, FR-005, FR-006, NFR-001, NFR-002

### Included Subtasks

- [x] T022 Create `mission_setup_plan.py`; move `setup_plan` + decompose into phase helpers (preflight → resolution → branch-contract injection → plan commit → coord commits), each `<=15` CC.
- [x] T023 Move `_commit_to_branch`, `CommitToBranchResult`, `_kind_for_artifact`, `_artifact_has_no_git_changes`, `_artifact_absent_at_placement`, `_print_artifact_unchanged`, `_warn_commit_failed` into the setup-plan seam; keep `commit_for_mission` lazy.
- [x] T024 Create `mission_accept_merge.py`; move `accept_feature`, `merge_feature`, `_find_latest_feature_worktree`, `_find_feature_worktree`; confirm thin-delegator imports stay function-local (A-3).
- [x] T025 Author focused tests per phase helper; extend commit_to_branch/kind_for_artifact/accept/merge tests.
- [x] T026 Golden test + ruff/mypy clean; CC check.

### Dependencies

- Depends on WP05.

---

## Work Package WP07: finalize_tasks seam + mega-function decomposition (Priority: P1)

**Goal**: Move `finalize_tasks` (1227 LOC, ~8× ceiling) + its finalize helpers into `mission_finalize.py`,
decomposing the body into `<=15`-CC phase helpers, each with a focused test; preserve the
`--validate-only` zero-mutation invariant (INV-6).
**Independent Test**: existing finalize suite (`test_mission_finalize_tasks.py`,
`test_finalize_tasks_owned_files_validation.py`, `test_finalize_tasks_validate_only_readonly.py`,
`test_finalize_tasks_explicit_empty_owned_files.py`, `test_feature_finalize_bootstrap.py`,
`test_finalize_coord_staging.py`, `test_finalize_clobber_e2e.py`, `tests/tasks/test_finalize_*`) green +
new phase-helper tests; golden test green.
**Prompt**: `/tasks/WP07-finalize-tasks-seam.md`
**Requirement Refs**: FR-003, FR-004, FR-005, FR-006, NFR-001, NFR-002

### Included Subtasks

- [x] T027 Create `mission_finalize.py`; move `finalize_tasks` + finalize helpers (`_collect_finalize_artifacts`, `_extract_wp_ids_from_task_files`, `_branch_tree_relative_path`) — note `_stage_finalize_artifacts_in_coord_worktree` is relocated to commit_router in WP08, not here.
- [x] T028 Decompose `finalize_tasks` into phase helpers: preflight → feature-dir resolution → branch resolution → conflict detection (T004 disagree-loud) → charter-activation gate (FR-017) → dependency resolution preserve-existing → 8-field bootstrap-mutation loop → manifest build/ownership-overlap validation → commit (`commit_for_mission`) → SaaS emit/dossier. Each `<=15` CC.
- [x] T029 Add an explicit assertion that the write phase is unreachable when `validate_only` (reinforces INV-6); extend `test_finalize_tasks_validate_only_readonly.py`.
- [x] T030 Author focused tests per phase helper (the previously-indirect Seam C parsers now get direct + phase coverage).
- [x] T031 Golden test + full finalize suite + ruff/mypy clean; CC check (no function over 15).

### Dependencies

- Depends on WP06.

---

## Work Package WP08: Relocate planning-commit residue to commit_router + repoint tasks.py (Priority: P0)

**Goal**: RELOCATE `_planning_commit_worktree`, `_resolve_planning_placement`,
`_stage_finalize_artifacts_in_coord_worktree` into `coordination/commit_router.py`, reconcile against the
existing near-duplicate `_stage_artifacts_in_coord_worktree`, and repoint `tasks.py`'s import. LIVE on this
base — relocate, never delete (FR-007).
**Independent Test**: `pytest tests/tasks/` + `tests/specify_cli/coordination/test_commit_router*.py` +
`test_write_surface_coherence.py` green; `grep` confirms the symbols live in commit_router and tasks.py
imports them from there.
**Prompt**: `/tasks/WP08-relocate-planning-commit-residue.md`
**Requirement Refs**: FR-007, C-002, NFR-005

### Included Subtasks

- [x] T032 Move `_planning_commit_worktree`, `_resolve_planning_placement` from `mission.py` into `coordination/commit_router.py`; carry their dependency `_stage_finalize_artifacts_in_coord_worktree`.
- [x] T033 Reconcile `_stage_finalize_artifacts_in_coord_worktree` against commit_router's existing `_stage_artifacts_in_coord_worktree` (collapse the near-duplicate; do not fork).
- [x] T034 Repoint `tasks.py`'s function-local import of `_planning_commit_worktree`/`_resolve_planning_placement` to `coordination.commit_router` (single out-of-map line, documented).
- [x] T035 Confirm one-way imports — `commit_router` does NOT import from `mission`/seams (INV-8); keep `commit_for_mission`/`CoordinationWorkspace` lazy.
- [x] T036 Add/extend commit_router tests covering the relocated functions; run tasks suite + write-surface coherence; ruff/mypy clean.

### Dependencies

- Depends on WP07.

---

## Work Package WP09: Shim finalization — pointer comment + ~100 re-export sweep + full gate (Priority: P0)

**Goal**: Reduce `mission.py` to a thin shim: `app` + 8 command registrations + the complete re-export
block (every test-patched name) + the #2056 decomposition pointer comment. Run the full gate sweep.
**Independent Test**: the ENTIRE mission-touching suite passes with ZERO patch-target rewrites; a re-export
presence test asserts every name in the patch survey is importable from `mission`; ruff C901 reports no
function over 15; mypy --strict clean.
**Prompt**: `/tasks/WP09-shim-finalization.md`
**Requirement Refs**: FR-001, FR-002, FR-006, NFR-001, NFR-002, NFR-003, NFR-004

### Included Subtasks

- [ ] T037 Reduce `mission.py` to the shim: `app`, 8 `@app.command` registrations delegating to the seams, and the full re-export block.
- [ ] T038 Enumerate the ~100 test-patched names (research §5: `locate_project_root` 76×, `_find_feature_directory` 39×, `_show_branch_context` 22×, `run_command`, `get_emitter`, `is_saas_sync_enabled`, `validate_feature_structure`, `CommitToBranchResult`, all 8 command fns) and re-export every one.
- [ ] T039 Add the #2056 top-of-file decomposition pointer comment (matching the #1623 / existing god-module-pointer convention) documenting shim role + seam map.
- [ ] T040 Author a re-export presence test asserting every surveyed patch target resolves via `mission.<name>`.
- [ ] T041 Full gate sweep: entire mission-touching suite (zero patch-target churn), golden test, ruff (C901 ≤15 everywhere), mypy --strict, coverage ≥90% on new code, zero new suppressions.

### Dependencies

- Depends on WP08.
