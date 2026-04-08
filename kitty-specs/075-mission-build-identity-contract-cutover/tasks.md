# Tasks: Mission & Build Identity Contract Cutover

**Mission**: 075-mission-build-identity-contract-cutover
**Branch**: `main` → merge target: `main`
**Generated**: 2026-04-08

## Overview

Closes three remaining gaps from the prior mission/feature identity cutover:
1. **Inbound read-path fallbacks** — five runtime files still accept `feature_slug` on inbound reads
2. **Per-worktree build identity** — `build_id` is shared across worktrees via committed config
3. **Tracker bind** — `bind_mission_origin` does not include `build_id` in its SaaS payload

Five work packages across two parallel lanes plus a dependent regression suite.

```
Lane A:  WP01 (status model cleanup) → WP02 (domain model cleanup) ──────────┐
                                                                               ├── WP05 (regression)
Lane B:  WP03 (per-worktree build.id) → WP04 (tracker bind + contract) ───────┘
```

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|----|---------:|
| T001 | Create `tests/cross_branch/fixtures/legacy_feature_slug_event.jsonl` | WP01 | | [D] | [D] |
| T002 | Write failing test: `StatusEvent.from_dict(legacy)` → `KeyError` | WP01 | | [D] |
| T003 | Remove `feature_slug` fallback from `status/models.py` (StatusEvent) | WP01 | | [D] |
| T004 | Write failing test: `StatusSnapshot.from_dict(legacy)` → `KeyError` | WP01 | | [D] |
| T005 | Remove `feature_slug` fallback from `status/models.py` (StatusSnapshot) | WP01 | | [D] |
| T006 | Write failing test: `validate_event_schema` rejects missing `mission_slug` without legacy mention | WP01 | | [D] |
| T007 | Remove `feature_slug` branch from `status/validate.py` | WP01 | | [D] |
| T008 | Remove `with_tracked_mission_slug_aliases` import + usage from `status/models.py` | WP01 | | [D] |
| T009 | Write failing test: `WPMetadata.model_dump()` has no `feature_slug` key | WP02 | | [D] |
| T010 | Remove `feature_slug` field from `status/wp_metadata.py` | WP02 | | [D] |
| T011 | Write failing test: `identity_aliases` no longer backfills `mission_slug` | WP02 | | [D] |
| T012 | Remove `identity_aliases` import from `status/progress.py`; delete `core/identity_aliases.py` | WP02 | | [D] |
| T013 | Write failing test: `core/worktree.py` reads `mission_slug` not `feature_slug` | WP02 | | [D] |
| T014 | Update `core/worktree.py:123` — `.feature_slug or ""` → `.mission_slug or ""` | WP02 | | [D] |
| T015 | Full test + mypy --strict pass for all WP01+WP02 changes | WP02 | | [D] |
| T016 | Add `_build_id_path() -> Path` to `sync/project_identity.py` | WP03 | [P] |
| T017 | Add `load_build_id(git_dir: Path) -> str` | WP03 | [P] |
| T018 | Add `_migrate_build_id_from_config(config_path, git_dir)` | WP03 | [P] |
| T019 | Update `ensure_identity(repo_root)` to use new build.id functions | WP03 | |
| T020 | Update `atomic_write_config` to exclude `build_id` from `config.yaml` | WP03 | |
| T021 | Write test: two monkeypatched git-dir paths → distinct `build_id` values | WP03 | |
| T022 | Write test: 100 invocations of `load_build_id()` → stable value | WP03 | |
| T023 | Write test: `_migrate_build_id_from_config` idempotency | WP03 | |
| T024 | Write test: `BuildIdentityError` when `git rev-parse --git-dir` fails | WP03 | |
| T025 | Extend `SaaSTrackerClient.bind_mission_origin()` signature to accept `build_id: str` | WP04 | |
| T026 | Load `ProjectIdentity` in `bind_mission_origin()`; pass `build_id` to client | WP04 | |
| T027 | Write test: captured bind call payload contains `build_id` (Scenario 3) | WP04 | |
| T028 | Write test: `_load_contract()` provenance fields (Scenario 4) | WP04 | [P] |
| T029 | Write CLI integration test (CliRunner): mission create → events.jsonl clean | WP05 | |
| T030 | Write orchestrator API contract test via `upstream_contract.json` + Typer introspection | WP05 | [P] |
| T031 | Write body sync test: mock `SaaSBodyClient`; assert canonical namespace | WP05 | [P] |
| T032 | Write tracker bind non-regression: no `feature_slug` in bind kwargs | WP05 | [P] |
| T033 | Full test suite run; ≥90% coverage on modified modules; mypy --strict | WP05 | |

---

## WP01 — Status Model Read-Path Cleanup

**Goal**: Remove `feature_slug` fallbacks from `status/models.py` and `status/validate.py`; create legacy event fixture; remove dead `identity_aliases` usage from `status/models.py`.
**Priority**: High — unblocks WP02 (no file conflict, but sets clean baseline for mypy)
**Estimated prompt size**: ~380 lines
**Dependencies**: none
**Prompt file**: `tasks/WP01-status-model-read-path-cleanup.md`

- [x] T001 Create `tests/cross_branch/fixtures/legacy_feature_slug_event.jsonl` (WP01)
- [x] T002 Write failing test: `StatusEvent.from_dict(legacy)` → `KeyError` (WP01)
- [x] T003 Remove `feature_slug` fallback from `status/models.py` (StatusEvent) (WP01)
- [x] T004 Write failing test: `StatusSnapshot.from_dict(legacy)` → `KeyError` (WP01)
- [x] T005 Remove `feature_slug` fallback from `status/models.py` (StatusSnapshot) (WP01)
- [x] T006 Write failing test: `validate_event_schema` rejects missing `mission_slug` without legacy mention (WP01)
- [x] T007 Remove `feature_slug` branch from `status/validate.py` (WP01)
- [x] T008 Remove `with_tracked_mission_slug_aliases` import + usage from `status/models.py` (WP01)

**Implementation sketch**: Create fixture first (prerequisite for T002, T004). Work models.py top-to-bottom: StatusEvent deserialization (lines 221+), StatusSnapshot deserialization (lines 264+), then the to_dict() alias wrapper (line 251). Fix validate.py last. All changes in one commit per concern.

**Risks**: Any test that currently passes a legacy-shaped dict (with `feature_slug` only) will break when fallbacks are removed — that's the goal. Scan `tests/` for any such inputs before removing the production code.

---

## WP02 — Domain Model Cleanup

**Goal**: Remove `feature_slug` from `WPMetadata`; delete `core/identity_aliases.py`; fix `core/worktree.py` reader; ensure full mypy pass.
**Priority**: High
**Estimated prompt size**: ~360 lines
**Dependencies**: none
**Prompt file**: `tasks/WP02-domain-model-cleanup.md`

- [x] T009 Write failing test: `WPMetadata.model_dump()` has no `feature_slug` key (WP02)
- [x] T010 Remove `feature_slug` field from `status/wp_metadata.py` (WP02)
- [x] T011 Write failing test: `identity_aliases` no longer backfills `mission_slug` (WP02)
- [x] T012 Remove `identity_aliases` import from `status/progress.py`; delete `core/identity_aliases.py` (WP02)
- [x] T013 Write failing test: `core/worktree.py` reads `mission_slug` not `feature_slug` (WP02)
- [x] T014 Update `core/worktree.py:123` — `.feature_slug or ""` → `.mission_slug or ""` (WP02)
- [x] T015 Full test + mypy --strict pass for all WP01+WP02 changes (WP02)

**Implementation sketch**: T009-T010 (WPMetadata field removal) first — after WP01 removes the WPMetadata.feature_slug access in identity_aliases, the model field is the only remaining use. T011-T012 (delete module) second — remove progress.py import, then delete the file. T013-T014 (worktree reader) last — trivially follows from WPMetadata field removal.

**Risks**: Deleting `core/identity_aliases.py` will surface any remaining caller not yet cleaned. Run `grep -r "identity_aliases" src/` before deletion — expect zero hits outside migration paths.

---

## WP03 — Per-Worktree Build.id Storage

**Goal**: Move `build_id` from committed `config.yaml` to `{git-dir}/spec-kitty-build-id`. Distinct per worktree, stable per checkout.
**Priority**: High (WP04 depends on this)
**Estimated prompt size**: ~430 lines
**Dependencies**: none
**Prompt file**: `tasks/WP03-per-worktree-build-id.md`

- [ ] T016 Add `_build_id_path() -> Path` to `sync/project_identity.py` (WP03)
- [ ] T017 Add `load_build_id(git_dir: Path) -> str` (WP03)
- [ ] T018 Add `_migrate_build_id_from_config(config_path, git_dir)` (WP03)
- [ ] T019 Update `ensure_identity(repo_root)` to use migration + `load_build_id` (WP03)
- [ ] T020 Update `atomic_write_config` to exclude `build_id` from output (WP03)
- [ ] T021 Write test: two git-dir paths → distinct `build_id` values (WP03)
- [ ] T022 Write test: 100 invocations → stable `build_id` (WP03)
- [ ] T023 Write test: migration idempotency (WP03)
- [ ] T024 Write test: `BuildIdentityError` when `git rev-parse --git-dir` fails (WP03)

**Implementation sketch**: Write T016-T018 as pure functions first (easy to test in isolation). Then wire into `ensure_identity` (T019) and `atomic_write_config` (T020). Write tests against monkeypatched git-dir paths — no real worktrees needed in CI.

**Risks**: `atomic_write_config` is called from multiple places — audit all call sites to ensure none are broken by the `build_id` exclusion. The existing `.kittify/config.yaml` in this repo has `project.build_id` — migration will run once and remove it.

---

## WP04 — Tracker Bind Build-Id + Contract Provenance Tests

**Goal**: Add `build_id` to the tracker bind SaaS call; write Scenario 3 and Scenario 4 acceptance tests.
**Priority**: High
**Estimated prompt size**: ~250 lines
**Dependencies**: WP03
**Prompt file**: `tasks/WP04-tracker-bind-and-contract-tests.md`

- [ ] T025 Extend `SaaSTrackerClient.bind_mission_origin()` to accept `build_id: str` (WP04)
- [ ] T026 Load `ProjectIdentity` in `bind_mission_origin()`; pass `build_id` to client (WP04)
- [ ] T027 Write test: captured bind call payload contains `build_id` (Scenario 3) (WP04)
- [ ] T028 Write test: `_load_contract()` provenance fields (Scenario 4) (WP04)

**Implementation sketch**: T025 is a signature change — extend `SaaSTrackerClient.bind_mission_origin()` with `build_id: str`. T026 threads `ProjectIdentity` into `bind_mission_origin()` in `origin.py` using the already-resolved `repo_root`. T027 and T028 are straightforward unit tests.

**Risks**: `SaaSTrackerClient.bind_mission_origin()` may be used by other callers outside `origin.py` — check for all call sites and update signatures throughout.

---

## WP05 — Regression and Non-Regression Test Suite

**Goal**: End-to-end smoke tests that already-clean surfaces haven't regressed. Depends on all prior WPs completing.
**Priority**: Medium (cannot proceed without other WPs)
**Estimated prompt size**: ~300 lines
**Dependencies**: WP02, WP04
**Prompt file**: `tasks/WP05-regression-test-suite.md`

- [ ] T029 Write CLI integration test (CliRunner): mission create → events.jsonl clean (WP05)
- [ ] T030 Write orchestrator API contract test via `upstream_contract.json` + Typer introspection (WP05)
- [ ] T031 Write body sync test: mock `SaaSBodyClient`; assert canonical namespace (WP05)
- [ ] T032 Write tracker bind non-regression: no `feature_slug` in bind kwargs (WP05)
- [ ] T033 Full test suite run; ≥90% coverage on modified modules; mypy --strict (WP05)

**Implementation sketch**: T029-T032 each create a new test file (no modifications to existing files). T033 is a gate task — run `pytest --cov` and `mypy --strict`; do not mark WP05 done until both pass.

**Risks**: CliRunner-based integration test (T029) requires a minimal project fixture with `.kittify/config.yaml`. Check existing CLI test fixtures for a reusable base.
