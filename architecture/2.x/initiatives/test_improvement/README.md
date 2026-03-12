# Test Improvement Initiative

> **Status:** In Progress  
> **Branch scope:** 2.x only  
> **Branch:** `fix/test-detection-remediation`  
> **Date:** 2026-03-12  
> **Last updated:** 2026-03-14

---

## 1. Legacy Tests Analysis (`tests/legacy/`)

### Overview

| Metric | Value |
|--------|-------|
| Files | 29 |
| Lines of code | ~6,464 |
| Branch-gating | All files use `IS_2X_BRANCH` skip marker |

### What's in there

- **Integration tests (13 files):** Auto-create target branch, status routing, feature lifecycle, task workflows, missions, research templates. Largest: `test_move_task_delegation.py` (~900 LOC).
- **specify_cli tests (4 files):** Review warnings, workflow auto-moves, event emission, init command.
- **Unit tests (4 files):** Mission schema (1.x format), task commands, workflow instructions, research missions.

### Module coverage

All 12 imported modules (`agent.feature`, `agent.tasks`, `agent.workflow`, `status.migrate`, `status.store`, `status.reducer`, `mission`, `frontmatter`, `tasks_support`, `core.vcs`, `core.context_validation`, `acceptance`) still exist in the 2.x codebase.

### Filename conflicts with current tests

| File | Locations | Risk |
|------|-----------|------|
| `test_event_emission.py` | 3 locations | LOW (branch-gated) |
| `test_mission_schema.py` | Legacy (1.x format) vs current | LOW |
| `test_mission_switching.py` | Legacy stub vs current full | LOW |
| `test_review_warnings.py` | Legacy references current | LOW |

### Verdict

**Safe to keep ignored.** All coverage is either duplicated or superseded by 2.x tests. The branch-gating works correctly. No dead code, no salvageable unique coverage.

**Recommendation:** Keep as-is. Consider renaming files with `_legacy` suffix to avoid IDE confusion if it becomes annoying.

---

## 2. Current Test Suite Profile

### Metrics

| Metric | Value |
|--------|-------|
| Test files (non-legacy) | 338 |
| Lines of test code | ~90,000 |
| Total test cases | 5,335 |
| conftest.py files | 7 |
| Full suite (fast+slow+unmarked) | ~5 min (local), ~20 min (CI) |

### Directory breakdown

| Directory | Files | LOC | Type | Cost |
|-----------|-------|-----|------|------|
| `specify_cli/` | 149 | 52.1K | CLI/Core/Mixed | MODERATE |
| `unit/` | 60 | 19.5K | Unit (mocked) | MINIMAL ✓ |
| `integration/` | 42 | 15.6K | Integration (git) | VERY HIGH |
| `sync/` | 23 | 8.7K | Async unit | MODERATE |
| root `tests/` | 25 | 5.8K | System integration | MODERATE–HIGH |
| `test_dashboard/` | 8 | 561 | Dashboard unit | MODERATE |
| `doctrine/` | 7 | 797 | Schema compliance | MINIMAL ✓ |
| `adversarial/` | 6 | 1.3K | Security/attack | MODERATE |
| `test_template/` | 5 | 557 | Template unit | MINIMAL ✓ |
| `e2e/` | 3 | 502 | CLI workflow | VERY HIGH |
| `release/` | 2 | 245 | Release validation | LOW |
| `concurrency/` | 2 | 184 | Concurrency | ? |
| `cross_branch/` | 2 | 157 | Branch compat | LOW |
| `contract/` | 2 | 352 | Handoff verify | LOW |
| `docs/` | 1 | 103 | Doc integrity | MINIMAL ✓ |

### Duplication verdict

**No significant duplication found.** Related tests across locations (dashboard ×3, encoding ×3, init ×3, gitignore ×2) test different aspects — unit vs CLI vs resilience. Architecture is sound.

---

## 3. Expensive Operations (ranked)

1. **subprocess.run() CLI calls** — 1–5+ sec per call, 60s timeout. Found in: `integration/`, `e2e/`, root, `test_dashboard/`.
2. **Git worktree creation** — 100–500ms per op. `conflicting_wps_repo` creates 3 worktrees, `git_stale_workspace` creates 1 + advance.
3. **Dashboard process spawning** — 500–1000ms per process.
4. **Async event loops** — 100–200ms overhead per test (23 files in `sync/`).
5. **File system scaffolding** — .kittify copying, mission dir copying. All tests using `tmp_path`.

---

## 4. Proposed Subdivision (test tiers)

### Tier 1 — Fast (target: <60s)

```bash
pytest tests/unit tests/doctrine tests/test_template tests/docs
```

Pure unit tests, schema compliance, template validation. No git, no subprocess, no network. Run on every save / pre-commit.

### Tier 2 — Medium (target: 3–8 min)

```bash
pytest -m "not slow and not e2e" tests/specify_cli tests/sync tests/adversarial tests/release tests/contract
```

Core CLI logic, async unit tests, adversarial tests. Some `tmp_path` scaffolding but no subprocess CLI calls. Run before commit.

### Tier 3 — Integration (target: 10–15 min)

```bash
pytest tests/integration tests/cross_branch tests/concurrency tests/test_dashboard tests/*.py
```

Real git repos, subprocess CLI invocations, dashboard spawning. Run in CI on every push.

### Tier 4 — E2E / Smoke (target: 5–10 min)

```bash
pytest -m e2e tests/e2e
```

Full workflow: specify → plan → tasks → implement → review → merge. Run in CI on PR only.

---

## 5. Improvement Opportunities

### Fixture consolidation ✓ done

- `isolated_env()` and `run_cli()` moved to root `conftest.py` (commit `969b5746`).
- `temp_repo` fixture restored in root conftest.

### Expensive fixture optimization

- `conflicting_wps_repo` creates 3 worktrees but is only used in a few tests → consider session-scoping or lazy creation.
- `git_stale_workspace` could use a builder pattern for reuse across test modules.

### Root test organization

25 loose files in `tests/` root test cross-cutting concerns (dashboard, encoding, gitignore, packaging, versioning). They could be grouped into:

```
tests/cross_cutting/
  ├── dashboard/      (3 files)
  ├── encoding/       (3 files)
  ├── packaging/      (2 files)
  └── versioning/     (3 files)
```

This is cosmetic but would improve navigability.

### Marker enrichment

Currently only `e2e`, `slow`, `jj`, `adversarial`, `asyncio` are used as markers. Adding a `subprocess` or `git_repo` marker to integration tests would allow finer exclusion:

```bash
pytest -m "not subprocess" tests/  # Skip anything spawning spec-kitty CLI
```

---

## 6. Execution Strategy Summary

| Context | What to run | Time |
|---------|-------------|------|
| Dev loop (on save) | Tier 1 | <60s |
| Pre-commit | Tier 1 + 2 | 3–8 min |
| CI push | Tier 1 + 2 + 3 | 10–15 min |
| CI PR gate | All tiers | 20–30 min |

### Key pytest invocations

```bash
# Fast feedback (development)
pytest -m fast tests/specify_cli/

# Before commit
pytest -m "not slow and not e2e" tests/

# Full CI run
PWHEADLESS=1 pytest tests/ -m "not legacy"

# Async/sync module only
pytest -m asyncio tests/sync/
```

---

## 7. Work Completed

### 7.1 Pytest Marker Annotations (commit `a1ad4367`)

Added `fast` and `slow` pytest markers to all profiled `specify_cli/` subdirectories using `pytest_collection_modifyitems` hooks in conftest.py files. This enables `pytest -m fast` for rapid dev-loop feedback.

**Marker assignment (based on measured timing):**

| Directory | Tests | Time | Marker |
|-----------|-------|------|--------|
| `status/` | 632 | 1.25s | `fast` |
| `glossary/` | 689 | 0.64s | `fast` |
| `upgrade/` | 168 | 1.73s | `fast` |
| `constitution/` | 114 | 0.62s | `fast` |
| `cli/` | 190 | 12.88s | `slow` |
| `core/` | 153+57skip | 16.05s | `slow` |
| `test_cli/` | 101 | 29.42s | `slow` |
| `test_core/` | 120 | 25.04s | `slow` |

**Implementation note:** `pytestmark` in conftest.py does NOT propagate in pytest 9.0.2. Used `pytest_collection_modifyitems` hook scoped with `Path(__file__).parent` instead.

**Current marker stats (2026-03-14):**

| Marker | Tests | Runtime (local) | Notes |
|--------|-------|-----------------|-------|
| `fast` | 1,659 | 5.2s | Pure logic, no subprocess/git |
| `slow` | 684 | 25.9s | subprocess/git, specify_cli/test_cli + test_core |
| unmarked | 2,992 | ~4 min | integration, sync, legacy, root, e2e |
| **Total** | **5,335** | **~5 min** | Local machine ~3× faster than CI reference |

> **Note:** The reference machine times in the original spec (73.51s for slow) were measured on a slower CI-equivalent machine. Local timings are ~3× faster. Use the reference times for CI budgeting.

### 7.2 Merge Test Unit Extraction (commit `c816d247`)

**Target:** `tests/specify_cli/test_cli/test_merge_workspace_per_wp.py` — the single slowest file (101 tests, 29.42s). Every test created real git repos + worktrees (1.3–1.5s fixture cost per test).

**Action:** Extracted pure-logic and mock-boundary tests into `test_merge_workspace_per_wp_unit.py`. Removed 13 integration tests now covered by unit mocks.

| File | Tests | Runtime | Change |
|------|-------|---------|--------|
| `test_merge_workspace_per_wp.py` (before) | 101 | 29.42s | — |
| `test_merge_workspace_per_wp.py` (after) | 17 + 3 xfail | 23.64s | −6s |
| `test_merge_workspace_per_wp_unit.py` (new) | 29 | 0.33s | — |
| **Net** | **49** | **23.97s** | **−5.5s, +29 fast tests** |

**Unit test coverage (29 tests, 0.33s):**

| Function | Unit tests | Approach |
|----------|-----------|----------|
| `extract_feature_slug` | 3 | Pure string parsing |
| `extract_wp_id` | 3 | Pure Path parsing |
| `detect_worktree_structure` | 7 | Mocked `get_main_repo_root` + `_list_wp_branches` |
| `find_wp_worktrees` | 4 | Mocked filesystem + branch listing |
| `validate_wp_ready_for_merge` | 4 | Mocked `subprocess.run` |
| `_build_workspace_per_wp_merge_plan` | 4 | Mocked `_branch_is_ancestor` + `_order_wp_workspaces` |
| `merge_workspace_per_wp` (dry-run) | 2 | Fully mocked internals |
| VCS detection | 2 | Mocked availability checks |

**Integration tests kept (17 + 3 xfail):** Tests requiring real git repos — worktree detection from within worktrees, full merge workflows, ancestry chain planning, jj backend detection (xfail).

### 7.3 test_core/ Unit Extraction (commits `3ed22b5a`, `b402d17f`)

Extracted pure-logic and mock-boundary tests from the two most expensive `test_core/` files.

**`test_git_ops.py` → `test_git_ops_unit.py` (17 new fast tests, 0.29s):**

| Function | Unit tests | Approach |
|----------|-----------|----------|
| `run_command` | 3 | Pure subprocess mock |
| `resolve_target_branch` | 8 | Mocked `resolve_primary_branch` |
| `resolve_primary_branch` | 6 | Mocked `subprocess.run` heuristics |

**`test_create_feature_branch.py` → `test_create_feature_branch_unit.py` (9 new fast tests, 0.57s):**

| Function | Unit tests | Approach |
|----------|-----------|----------|
| `create_feature` | 9 | Mocked `locate_project_root`, `is_git_repo`, `is_worktree_context`, `get_current_branch`, `get_next_feature_number`, `safe_commit` |

**Discovery:** `create_feature()` calls `safe_commit()` after writing `meta.json` — mocking git I/O requires patching `specify_cli.cli.commands.agent.feature.safe_commit` in addition to the root/branch guard mocks.

---

### 7.4 Fixture Consolidation, Lint + Type Cleanup (2026-03-14)

#### Fixture consolidation (commit `969b5746`)

- Moved `isolated_env` and `run_cli` from `tests/e2e/conftest.py` and `tests/integration/conftest.py` to root `tests/conftest.py`
- Restored accidentally-removed `temp_repo` fixture in root conftest
- Re-added missing `import tomllib` to `tests/integration/conftest.py`
- Removed 9 stale `@pytest.mark.xfail` markers across 4 files (`test_distribution.py`, `test_implement_multi_parent.py`, `test_merge_workflow_complete.py`, `test_multi_parent_merge.py`) — all now pass unconditionally

#### Ruff lint sweep (commit `e7a3781c`)

Applied `ruff check --fix` and `--unsafe-fixes` across the full `tests/` tree. **687 violations → 0.**

Key rules resolved: F401 (249 unused imports), UP017/UP006/UP035 (deprecated typing), SIM117 (51 nested `with`), W293 (trailing whitespace), F841 (60 unused variables), E501 (38 long lines), E741 (ambiguous names), E402 (imports not at top), F811 (redefined names), SIM105/SIM102 (simplifications), E722 (bare except), B018/SIM115 (misc).

#### Mypy type annotations (commit `a9d77b3d`)

Added strict-mode type annotations to all test files authored during this initiative:
- `test_git_ops_unit.py`, `test_create_feature_branch_unit.py`: `-> None` on all test functions, typed helper closures
- `tests/conftest.py`: `-> None` on `ensure_imports`, corrected `git_stale_workspace` return type to `dict[str, Path | str]`
- `tests/adversarial/test_distribution.py`: `-> None` on all test methods, typed `tmp_path_factory` parameters

---

## 8. Remaining Opportunities

### 8.1 Marker enrichment ✓ done (commit `git_repo marker`)

Added `git_repo` pytest marker to all tests that create real git repositories.

**Implementation:**
- Registered `git_repo` marker in `pytest.ini`
- Added `pytest_collection_modifyitems` hook to `tests/integration/conftest.py` (covers all 17 integration tests)
- Added file-level `pytestmark = pytest.mark.git_repo` to 29 files across `unit/`, `specify_cli/`, `adversarial/`, `release/`, and root `tests/`

**Result:** `pytest -m git_repo` now collects 973 tests — a useful mid-tier filter between `fast` (1,659 tests, 5s) and the full suite (~5 min).

### 8.2 Root test reorganisation ✓ done (commit `refactor(tests): reorganise`)

Moved 20 test files from the `tests/` root into `tests/cross_cutting/` subdirectories:

```
tests/cross_cutting/
  dashboard/   — test_dashboard_{cli_accuracy,bug_117_lifecycle,encoding_resilience}
  encoding/    — test_encoding_validation_{cli,functional}, test_contextive_traceability
  packaging/   — test_package_bundling, test_packaging_safety, test_manifest_cli_filtering
  versioning/  — test_version_{detection,fallback}, test_upgrade_version_update
  misc/        — test_{acceptance_support,gitignore_management,gitignore_manager_simple,
                  performance,plan_validation,task_helpers,tasks_cli_commands,template_compliance}
```

Fixed hardcoded `Path(__file__).parent.parent` path calculations in 6 files (now 4 levels deep). All 5,335 tests still collected; fast suite passes.

### 8.3 Expensive fixture optimisation ✓ analysed (no action)

Candidates reviewed: `conflicting_wps_repo` (3 worktrees), `git_stale_workspace` (1 worktree + advance), `dirty_worktree_repo`.

**Verdict: module-scope not safe.** The tests that use these fixtures mutate the repos (e.g. `git rebase`, writing files in-place). Sharing fixtures across tests in the same module would cause inter-test interference. Builder pattern or snapshot restore would be required for any speedup — not worth the complexity given the low count (2–4 tests per fixture).

---

## 9. Test Structure Redesign — Vertical Slices

**Status:** Complete (`unit/` and `integration/` migrated) ✓  
**ADR:** `architecture/2.x/adr/2026-03-15-1-vertical-slice-test-organisation.md`

### Problem

The test tree has two competing top-level axes that are never reconciled:

- `unit/` and `integration/` are organised by **test type**, but their internals are flat bags of files with no relation to system capabilities. You cannot look at either directory and understand what the system does.
- `specify_cli/` mirrors the **source package tree**, but mixes unit and integration tests indiscriminately. Test type is invisible.

Neither axis is consistently applied. Neither gives a readable picture of the system.

### Decision

**Top level = vertical slices (system capabilities).** Test type is expressed orthogonally via pytest markers (`fast`, `git_repo`, `slow`) and filename suffixes (`*_unit.py` / `*_integration.py`).

Target structure:

```
tests/
  missions/       merge/        agent/        tasks/
  git_ops/        status/       upgrade/      init/
  sync/           runtime/      research/     next/
  cross_cutting/  doctrine/     adversarial/  e2e/
  docs/           release/      legacy/
```

`tests/README.md` has been rewritten to document this intent, the desiderata, and
the conventions for writing new tests.

### Stale work-tracking artefacts

The following files were written during earlier ad-hoc test sprints. They describe
work that is now complete or superseded. They have been moved here for archival:

- `IMPLEMENTATION_COMPLETE.md` — encoding & plan validation test suite completion report (Nov 2025)
- `TESTING_PROGRESS.md` — per-suite progress tracker for the same sprint
- `TESTING_REQUIREMENTS_ENCODING_AND_PLAN_VALIDATION.md` — original requirements spec for that sprint

### Migration plan (completed 2026-03-15)

The following directories were migrated to the slice layout:

| Source | Target slice(s) | Status |
|--------|----------------|--------|
| `unit/` (54 files) | Various slices | ✓ Done — `_unit` suffix, git mv |
| `integration/` (39 files) | Various slices | ✓ Done — `_integration` suffix, `pytestmark` added |
| `specify_cli/` (141 files) | Various slices | Follow-up — not part of this phase |

Fixtures `test_project`, `clean_project`, `dirty_project`, `project_with_worktree`,
`dual_branch_repo` were promoted from `integration/conftest.py` to the root
`tests/conftest.py` so they are visible across all slice directories.

**Final state (2026-03-15):**
- Collection: 5582 tests, 0 errors
- `fast` suite: 1658 passed, 1 skipped
- `git_repo` suite: 898 passed — 10 pre-existing failures unchanged

**Per-file slice classification for `unit/` and `integration/`:**

| File | Slice |
|------|-------|
| `unit/test_agent_config.py` | `agent/` |
| `unit/test_atomic_status_commits.py` | `git_ops/` |
| `unit/test_base_branch_tracking.py` | `git_ops/` |
| `unit/test_branch_contract.py` | `git_ops/` |
| `unit/test_context_validation.py` | `agent/` |
| `unit/test_doctrine_curation.py` | `cross_cutting/` (doctrine) |
| `unit/test_dossier_timezone_defaults.py` | `sync/` |
| `unit/test_gitignore_manager.py` | `cross_cutting/` |
| `unit/test_guards.py` | `missions/` |
| `unit/test_implement_merged_deps.py` | `merge/` |
| `unit/test_lane_directory_removal.py` | `tasks/` |
| `unit/test_m_0_12_0_documentation_mission.py` | `upgrade/` |
| `unit/test_merge_forecast.py` | `merge/` |
| `unit/test_merge_preflight.py` | `merge/` |
| `unit/test_merge_state.py` | `merge/` |
| `unit/test_migration_constitution_cleanup.py` | `upgrade/` |
| `unit/test_migration_python_only.py` | `upgrade/` |
| `unit/test_mission_schema.py` | `missions/` |
| `unit/test_move_task_git_validation.py` | `tasks/` |
| `unit/test_multi_parent_merge.py` | `merge/` |
| `unit/test_multi_parent_merge_adversarial.py` | `merge/` |
| `unit/test_multi_parent_merge_empty_branches.py` | `merge/` |
| `unit/test_paths.py` | `runtime/` |
| `unit/test_pre_commit_wp_guard.py` | `tasks/` |
| `unit/test_research_deliverables.py` | `research/` |
| `unit/test_stale_detection.py` | `git_ops/` |
| `unit/test_status_resolver.py` | `status/` |
| `unit/test_upgrade_auto_commit.py` | `upgrade/` |
| `unit/test_validators.py` | `agent/` |
| `unit/test_workspace_context.py` | `runtime/` |
| `unit/agent/test_context.py` | `agent/` |
| `unit/agent/test_context_resolve.py` | `agent/` |
| `unit/agent/test_feature_lifecycle.py` | `missions/` |
| `unit/agent/test_git_state_detection.py` | `git_ops/` |
| `unit/agent/test_review_feedback_pointer_2x.py` | `agent/` |
| `unit/agent/test_review_validation.py` | `agent/` |
| `unit/agent/test_tasks_2x.py` | `tasks/` |
| `unit/agent/test_workflow_feedback_pointer_2x.py` | `agent/` |
| `unit/mission_v1/test_compat.py` | `missions/` |
| `unit/mission_v1/test_events.py` | `missions/` |
| `unit/mission_v1/test_guards.py` | `missions/` |
| `unit/mission_v1/test_runner.py` | `missions/` |
| `unit/mission_v1/test_schema.py` | `missions/` |
| `unit/next/test_decision.py` | `next/` |
| `unit/next/test_prompt_builder.py` | `next/` |
| `unit/next/test_runtime_bridge.py` | `next/` |
| `unit/orchestrator_api/test_envelope.py` | `agent/` |
| `unit/runtime/test_bootstrap.py` | `runtime/` |
| `unit/runtime/test_doctor.py` | `runtime/` |
| `unit/runtime/test_global_runtime_convergence.py` | `runtime/` |
| `unit/runtime/test_home.py` | `runtime/` |
| `unit/runtime/test_merge.py` | `merge/` |
| `unit/runtime/test_resolver.py` | `runtime/` |
| `unit/runtime/test_show_origin.py` | `runtime/` |
| `integration/test_auto_merge_dependencies.py` | `merge/` |
| `integration/test_bug_124_branch_routing.py` | `git_ops/` |
| `integration/test_config_show_origin.py` | `runtime/` |
| `integration/test_conflict_resolution.py` | `merge/` |
| `integration/test_constitution_runtime.py` | `init/` |
| `integration/test_dual_write.py` | `sync/` |
| `integration/test_e2e_mission_v1.py` | `missions/` |
| `integration/test_e2e_runtime.py` | `runtime/` |
| `integration/test_gitignore_isolation.py` | `cross_cutting/` |
| `integration/test_implement_multi_parent.py` | `merge/` |
| `integration/test_init_flow.py` | `init/` |
| `integration/test_init_minimal.py` | `init/` |
| `integration/test_merge_no_remote.py` | `merge/` |
| `integration/test_merge_workflow_complete.py` | `merge/` |
| `integration/test_merged_dependency_workflow.py` | `merge/` |
| `integration/test_migrate.py` | `upgrade/` |
| `integration/test_migration_e2e.py` | `upgrade/` |
| `integration/test_mission_guards.py` | `missions/` |
| `integration/test_mission_loading.py` | `missions/` |
| `integration/test_mission_software_dev.py` | `missions/` |
| `integration/test_mission_switching.py` | `missions/` |
| `integration/test_next_command.py` | `next/` |
| `integration/test_next_replay_parity.py` | `next/` |
| `integration/test_planning_workflow.py` | `tasks/` |
| `integration/test_read_cutover.py` | `upgrade/` |
| `integration/test_research_plan_missions.py` | `research/` |
| `integration/test_research_workflow.py` | `research/` |
| `integration/test_safe_commit_helper.py` | `git_ops/` |
| `integration/test_specify_metadata_explicit.py` | `missions/` |
| `integration/test_status_e2e.py` | `status/` |
| `integration/test_sync_e2e.py` | `sync/` |
| `integration/test_sync_staleness.py` | `git_ops/` |
| `integration/test_two_branch_strategy.py` | `git_ops/` |
| `integration/test_version_isolation.py` | `cross_cutting/` |
| `integration/test_workspace_per_wp_workflow.py` | `tasks/` |
| `integration/test_worktree_exclusion.py` | `git_ops/` |
| `integration/orchestrator_api/test_commands.py` | `agent/` |
| `integration/orchestrator_api/test_json_envelope_contract.py` | `agent/` |
| `integration/test_agent_command_wrappers.py` | `agent/` |

### Legacy directory (follow-up, not part of this migration)

`tests/legacy/` will be addressed separately:
1. Audit each file for knowledge that is still valid in 2.x but not covered by current tests.
2. Extract any such tests into the appropriate slice.
3. Delete `tests/legacy/` entirely.
