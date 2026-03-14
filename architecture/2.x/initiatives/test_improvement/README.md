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

### 8.1 Marker enrichment (medium effort, high CI value)

Add a `subprocess` or `git_repo` marker to integration tests to allow finer exclusion without path-based `--ignore`:

```bash
pytest -m "not subprocess" tests/  # Skip anything spawning spec-kitty CLI
```

Currently only `fast`, `slow`, `e2e`, `jj`, `adversarial`, `asyncio` are in active use. The 2,992 unmarked tests include everything from fast async unit tests to multi-worktree integration tests — a `git_repo` marker on the latter would enable a useful mid-tier filter.

### 8.2 Root test reorganisation (cosmetic)

25 loose files in `tests/` root cover cross-cutting concerns. Grouping into subdirectories would improve navigability:

```
tests/cross_cutting/
  ├── dashboard/      (test_dashboard_*.py — 3 files)
  ├── encoding/       (test_encoding_*.py — 3 files)
  ├── packaging/      (test_package_bundling.py, test_packaging_safety.py)
  └── versioning/     (test_version_*.py — 3 files)
```

### 8.3 Expensive fixture optimisation

- `conflicting_wps_repo` creates 3 git worktrees per test — consider `scope="module"` or a builder pattern
- `git_stale_workspace` creates 1 worktree + advances main — same candidate for module-scoping
- `dual_branch_repo` in `tests/integration/conftest.py` — same pattern
