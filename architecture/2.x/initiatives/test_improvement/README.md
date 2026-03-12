# Test Improvement Initiative

> **Status:** In Progress  
> **Branch scope:** 2.x only  
> **Branch:** `fix/test-detection-remediation`  
> **Date:** 2026-03-12  
> **Last updated:** 2026-03-12

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
| Estimated test cases | ~800+ |
| conftest.py files | 7 |
| Estimated full run | 20–30 min |

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

### Fixture consolidation (low-hanging fruit)

- `isolated_env()` is defined identically in both `integration/conftest.py` and `e2e/conftest.py` → move to root `conftest.py`.
- `run_cli()` is duplicated the same way → consolidate.

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

**Current marker stats:**

| Marker | Tests | Runtime |
|--------|-------|---------|
| `fast` | 1,632 | 4.52s |
| `slow` | 583 | 73.51s |
| unmarked | 648 | ~15s |
| **Total** | **2,863** | **93.20s** |

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

### 7.3 test_core/ Profiling (next target identified)

| File | Tests | Time | Priority |
|------|-------|------|----------|
| `test_git_ops.py` | 42 | 23.00s | **HIGH** — same pattern as merge tests |
| `test_worktree.py` | 44 | 6.19s | MEDIUM |
| `test_create_feature_branch.py` | 8 | 14.92s | **HIGH** — 1.9s/test |
| `test_git_preflight.py` | 10 | 0.70s | LOW (already fast) |
| `test_config.py` | 5 | 0.35s | LOW |
| `test_project_resolver.py` | 3 | 0.36s | LOW |
| `test_tool_checker.py` | 4 | 0.35s | LOW |
| `test_utils.py` | 4 | 0.36s | LOW |

**Next highest ROI:** `test_git_ops.py` (42 tests, 23s) and `test_create_feature_branch.py` (8 tests, 15s) — together 50 tests, 38s. Same git-repo fixture pattern as the merge tests.
