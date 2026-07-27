# Tasks: Remove hidden --feature alias from user-facing CLI commands

**Mission**: `feature-alias-removal-01KW0N87`
**Branch**: `feat/feature-alias-removal`
**Date**: 2026-06-26
**Spec**: `kitty-specs/feature-alias-removal-01KW0N87/spec.md`
**Plan**: `kitty-specs/feature-alias-removal-01KW0N87/plan.md`

---

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|-----|----------|
| T001 | Remove `--feature` Typer option from `implement()` entrypoint signature | WP01 | N |
| T002 | Rename `feature`→`mission` param in `implement()` and `_run_recover_mode()`; rename `feature_flag`→`mission_flag` in `detect_feature_context()`; rename `_feature_number`→`_mission_number` locals | WP01 | N |
| T003 | Update `detect_feature_context()` signature to remove `feature_flag` param; update both call sites | WP01 | N |
| T004 | Remove `--feature` Typer option from `merge()` entrypoint signature | WP01 | N |
| T005 | Rename `feature`→`mission` in `merge()`, `_resolve_slug_or_exit()`, `_dispatch_abort()`, `_dispatch_resume()`; rename all `resolved_feature`→`resolved_mission` occurrences | WP01 | N |
| T006 | Standardize `merge` no-selector path to exit code 2 (update `typer.Exit(1)` → `typer.Exit(2)` in `_resolve_slug_or_exit`) | WP01 | N |
| T007 | Remove `--feature` Typer option from `next()` signature; remove `feature` param from `_resolve_mission_slug()`; inline whitespace-normalization guard; remove unused `resolve_selector` import | WP02 | N |
| T008 | Remove `--feature` Typer option from `research()` signature; replace `resolve_selector` call at :67 with inline guard; remove `resolve_selector` import | WP02 | N |
| T009 | Remove `--feature` Typer option from `mission_resolve_command()` in `context.py`; replace `resolve_selector` call at :269 with inline guard; remove `resolve_selector` import | WP02 | N |
| T010 | Remove `--feature` Typer option from `accept()` signature; collapse `raw_handle = mission or feature` → `raw_handle = mission`; update `typer.Exit(1)` → `typer.Exit(2)` on no-handle path | WP02 | N |
| T011 | Rename `feature_slug` param → `mission_slug` in `_spec_artifact_dirty_paths()` and `_commit_residual_acceptance_artifacts()` in `accept.py` | WP02 | N |
| T012 | Verify no external callers pass `feature_slug=` as a keyword argument to the two accept.py helpers (grep check); confirm `resolve_selector` import gone from research.py, context.py, next_cmd.py | WP02 | N |
| T013 | Remove `--feature` Typer option from `plan()` in `lifecycle.py`; replace `resolve_selector(alias_flag="--feature")` call at :176 with inline guard | WP03 | N |
| T014 | Remove `--feature` Typer option from `tasks()` in `lifecycle.py`; replace `resolve_selector(alias_flag="--feature")` call at :266 with inline guard; keep `resolve_selector` import (still used by `specify()` at :136) | WP03 | N |
| T015 | Rename positional `feature`→`mission` in `lifecycle.specify()` (line :126); update metavar FEATURE→MISSION; update `_slugify_feature_input(mission)` call site | WP03 | N |
| T016 | Remove `--feature` Typer option from `current_cmd()` in `mission_type.py`; replace `resolve_selector` call at :246 with inline guard; remove `resolve_selector` import | WP03 | N |
| T017 | Confirm `src/specify_cli/missions/_legacy_aliases.py` is absent (FR-005 verification); run `grep -rn "_legacy_aliases" src/` and record result | WP03 | N |
| T018 | Extend `INSCOPE_FEATURE_FREE_FILES` in `tests/contract/test_terminology_guards.py` with all 8 in-scope file paths | WP04 | N |
| T019 | Flip three merge assertions in `tests/contract/test_feature_alias_scope.py` (merge now REJECTS `--feature`); update `_INSCOPE_FILES` tuple to include all 8 in-scope files | WP04 | N |
| T020 | Add `test_zero_feature_flags_exist_cli_wide` to `tests/specify_cli/cli/test_no_visible_feature_alias.py` asserting zero `--feature` Typer params across the entire CLI tree | WP04 | N |
| T021 | Create `tests/contract/test_no_selector_guard.py`; scaffold file with CliRunner fixture; add tests for `implement WP01` (no `--mission`) and `merge` (no `--mission`) | WP05 | N |
| T022 | Add tests for `next` (no `--mission`) and `research` (no `--mission`) to the new test file | WP05 | N |
| T023 | Add tests for `context mission-resolve` (no `--mission`) and `accept` (no `--mission`) | WP05 | N |
| T024 | Add tests for `lifecycle plan` (no `--mission`), `lifecycle tasks` (no `--mission`), and `mission-type current` (no `--mission`, run from `tmp_path`) | WP05 | N |
| T025 | Update `docs/status-model.md` — rewrite any live-usage example that shows `--feature`; leave migration/ docs untouched | WP06 | N |
| T026 | Update `docs/reference/environment-variables.md` — mark `SPEC_KITTY_SUPPRESS_FEATURE_DEPRECATION` as now inert after this release | WP06 | N |
| T027 | Update `docs/reference/orchestrator-api.md` — remove `--feature` from listed options | WP06 | N |
| T028 | Update `docs/engineering_notes/3-2-0-training-bugs-2007/pedro-command-drift.md` — fix implement opts section to remove `--feature` | WP06 | N |
| T029 | Add CHANGELOG.md unreleased entry for hard removal of `--feature` alias from all 8 in-scope user-facing commands | WP06 | N |

---

## Work Package 1: Flag removal in implement.py and merge.py

**Goal**: Remove `--feature` Typer option from `implement` and `merge` commands; rename all internal `feature`-prefixed identifiers to `mission`-prefixed; standardize no-selector exits to code 2.
**Priority**: High
**Independent Test**: `spec-kitty implement WP01 --feature some-slug` → exit 2, "No such option: --feature". `spec-kitty merge --feature some-slug` → exit 2, same. Both commands without `--mission` → exit 2, readable error.
**Dependencies**: none
**Prompt file**: `tasks/WP01-flag-removal-implement-merge.md`
**Estimated size**: ~330 lines

### Subtasks

- [ ] T001 Remove `--feature` Typer option from `implement()` entrypoint signature (WP01)
- [ ] T002 Rename `feature`→`mission` in `implement()` and `_run_recover_mode()`; rename `feature_flag`→`mission_flag` in `detect_feature_context()`; rename `_feature_number`→`_mission_number` locals (WP01)
- [ ] T003 Update `detect_feature_context()` signature to remove `feature_flag` param; update both call sites (WP01)
- [ ] T004 Remove `--feature` Typer option from `merge()` entrypoint signature (WP01)
- [ ] T005 Rename `feature`→`mission` in `merge()`, `_resolve_slug_or_exit()`, `_dispatch_abort()`, `_dispatch_resume()`; rename `resolved_feature`→`resolved_mission` throughout (WP01)
- [ ] T006 Standardize `merge` no-selector path to exit code 2 (WP01)

---

## Work Package 2: Flag removal in next_cmd.py, research.py, context.py, accept.py

**Goal**: Remove `--feature` Typer option from four remaining in-scope commands; inline whitespace-normalization guard in each; rename `feature_slug` params in accept.py helpers; standardize accept.py exit to code 2; clean up now-unused `resolve_selector` imports.
**Priority**: High
**Independent Test**: All four commands with `--feature foo` → exit 2 "No such option". All four without `--mission` → exit 2, readable error, no TypeError.
**Dependencies**: WP01
**Prompt file**: `tasks/WP02-flag-removal-next-research-context-accept.md`
**Estimated size**: ~360 lines

### Subtasks

- [ ] T007 Remove `--feature` from `next()`; remove `feature` from `_resolve_mission_slug()`; inline guard; remove unused `resolve_selector` import (WP02)
- [ ] T008 Remove `--feature` from `research()`; replace `resolve_selector` call with inline guard; remove import (WP02)
- [ ] T009 Remove `--feature` from `mission_resolve_command()` in `context.py`; replace `resolve_selector` call with inline guard; remove import (WP02)
- [ ] T010 Remove `--feature` from `accept()`; collapse `raw_handle = mission or feature`; update exit to code 2 on no-handle path (WP02)
- [ ] T011 Rename `feature_slug`→`mission_slug` in `_spec_artifact_dirty_paths()` and `_commit_residual_acceptance_artifacts()` in `accept.py` (WP02)
- [ ] T012 Verification grep: confirm no external callers use `feature_slug=` kwarg on the two accept.py helpers; confirm imports cleaned up in research.py, context.py, next_cmd.py (WP02)

---

## Work Package 3: Flag removal in lifecycle.py and mission_type.py

**Goal**: Remove `--feature` from `plan()` and `tasks()` in lifecycle; rename positional `feature`→`mission` in `lifecycle.specify()`; remove `--feature` from `mission_type current`; confirm `_legacy_aliases.py` is absent (FR-005).
**Priority**: High
**Independent Test**: `spec-kitty lifecycle plan --feature foo`, `lifecycle tasks --feature foo`, `mission-type current --feature foo` → all exit 2 "No such option". `spec-kitty lifecycle specify my-slug` still works.
**Dependencies**: WP02
**Prompt file**: `tasks/WP03-flag-removal-lifecycle-mission-type.md`
**Estimated size**: ~290 lines

### Subtasks

- [ ] T013 Remove `--feature` from `plan()` in `lifecycle.py`; replace `resolve_selector(alias_flag="--feature")` call with inline guard (WP03)
- [ ] T014 Remove `--feature` from `tasks()` in `lifecycle.py`; replace `resolve_selector(alias_flag="--feature")` call with inline guard; keep `resolve_selector` import (WP03)
- [ ] T015 Rename positional `feature`→`mission` in `lifecycle.specify()` (line :126); update metavar; update `_slugify_feature_input(mission)` call (WP03)
- [ ] T016 Remove `--feature` from `current_cmd()` in `mission_type.py`; inline guard; remove `resolve_selector` import (WP03)
- [ ] T017 Confirm `src/specify_cli/missions/_legacy_aliases.py` is absent; run `grep -rn "_legacy_aliases" src/` (WP03)

---

## Work Package 4: Terminology guard extension and existing test updates

**Goal**: Extend `INSCOPE_FEATURE_FREE_FILES` with all 8 in-scope paths; flip merge assertions in `test_feature_alias_scope.py`; add zero-feature-flags assertion to `test_no_visible_feature_alias.py`.
**Priority**: High
**Independent Test**: `pytest tests/contract/test_terminology_guards.py tests/contract/test_feature_alias_scope.py tests/specify_cli/cli/test_no_visible_feature_alias.py` — all pass. Adding `"--feature"` back to any in-scope file causes guard failure.
**Dependencies**: WP03
**Prompt file**: `tasks/WP04-terminology-guard-updates.md`
**Estimated size**: ~250 lines

### Subtasks

- [ ] T018 Extend `INSCOPE_FEATURE_FREE_FILES` in `tests/contract/test_terminology_guards.py` with all 8 in-scope file paths (WP04)
- [ ] T019 Flip merge assertions in `tests/contract/test_feature_alias_scope.py`; update `_INSCOPE_FILES` tuple (WP04)
- [ ] T020 Add `test_zero_feature_flags_exist_cli_wide` to `tests/specify_cli/cli/test_no_visible_feature_alias.py` (WP04)

---

## Work Package 5: No-selector regression tests

**Goal**: Create `tests/contract/test_no_selector_guard.py` with 8 focused tests — one per in-scope command — locking the no-selector exit-code-2 / no-TypeError contract (FR-008 / no-selector-error-contract.md).
**Priority**: High
**Independent Test**: `pytest tests/contract/test_no_selector_guard.py -v` — all 8 tests pass green.
**Dependencies**: WP04
**Prompt file**: `tasks/WP05-no-selector-regression-tests.md`
**Estimated size**: ~280 lines

### Subtasks

- [ ] T021 Create `tests/contract/test_no_selector_guard.py`; add tests for `implement WP01` no-mission and `merge` no-mission (WP05)
- [ ] T022 Add tests for `next` no-mission and `research` no-mission (WP05)
- [ ] T023 Add tests for `context mission-resolve` no-mission and `accept` no-mission (WP05)
- [ ] T024 Add tests for `lifecycle plan` no-mission, `lifecycle tasks` no-mission, and `mission-type current` no-mission (WP05)

---

## Work Package 6: Docs and CHANGELOG

**Goal**: Remove all stale `--feature` references from live docs; mark `SPEC_KITTY_SUPPRESS_FEATURE_DEPRECATION` as inert; add CHANGELOG unreleased entry.
**Priority**: Medium
**Independent Test**: `pytest tests/contract/test_terminology_guards.py` passes with `test_no_feature_flag_in_live_first_party_docs`. CHANGELOG unreleased section has the removal note.
**Dependencies**: WP05
**Prompt file**: `tasks/WP06-docs-changelog.md`
**Estimated size**: ~230 lines

### Subtasks

- [ ] T025 Update `docs/status-model.md` — remove/rewrite stale `--feature` live-usage references (WP06)
- [ ] T026 Update `docs/reference/environment-variables.md` — mark `SPEC_KITTY_SUPPRESS_FEATURE_DEPRECATION` as now inert (WP06)
- [ ] T027 Update `docs/reference/orchestrator-api.md` — remove `--feature` from listed options (WP06)
- [ ] T028 Update `docs/engineering_notes/3-2-0-training-bugs-2007/pedro-command-drift.md` — fix implement opts section (WP06)
- [ ] T029 Add CHANGELOG.md unreleased entry for hard removal of `--feature` from all 8 in-scope commands (WP06)
