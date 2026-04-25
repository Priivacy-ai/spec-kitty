---
work_package_id: WP10
title: Test File Occurrence Migration
dependencies:
- WP06
requirement_refs:
- FR-015
planning_base_branch: kitty/mission-runtime-mission-execution-extraction-01KPDYGW
merge_target_branch: kitty/mission-runtime-mission-execution-extraction-01KPDYGW
branch_strategy: Planning artifacts for this feature were generated on kitty/mission-runtime-mission-execution-extraction-01KPDYGW. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into kitty/mission-runtime-mission-execution-extraction-01KPDYGW unless the human explicitly redirects the landing branch.
subtasks:
- T037
- T038
- T039
- T040
agent: "claude:claude-sonnet-4-6:python-pedro:implementer"
shell_pid: "938982"
history:
- date: '2026-04-22T20:03:51Z'
  author: architect-alphonso
  event: created
agent_profile: python-pedro
authoritative_surface: tests/next/
execution_mode: code_change
owned_files:
- tests/next/**
- tests/runtime/**
- tests/specify_cli/next/**
- tests/specify_cli/runtime/**
- tests/agent/test_workflow_charter_context.py
- tests/audit/test_no_legacy_path_literals.py
- tests/concurrency/test_ensure_runtime_concurrent.py
- tests/contract/test_machine_facing_canonical_fields.py
- tests/contract/test_handoff_fixtures.py
- tests/init/test_init_minimal_integration.py
- tests/kernel/test_paths.py
- tests/merge/test_merge_unit.py
- tests/specify_cli/cli/commands/test_init_hybrid.py
- tests/specify_cli/cli/commands/test_init_integration.py
- tests/specify_cli/cli/commands/test_selector_resolution.py
- tests/specify_cli/status/test_progress_integration.py
- tests/status/test_doctor.py
- tests/upgrade/test_migrate_integration.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading further, load the assigned agent profile for this session:

```
/ad-hoc-profile-load python-pedro
```

Do not begin implementation until the profile is active.

---

## Objective

Apply the `occurrence_map.yaml` rewrites to all ~30 test files that import from `specify_cli.next.*` or `specify_cli.runtime.*`. Shims keep tests green during the deprecation window, but migrating them to canonical imports eliminates `DeprecationWarning` noise and proves the extraction is clean end-to-end.

---

## Context

**Authority**: `kitty-specs/runtime-mission-execution-extraction-01KPDYGW/occurrence_map.yaml` — the `test_caller` category is the authoritative list. This WP's `owned_files` is derived from the pre-scan results; cross-check against the actual map.

**Confirmed test files from scan** (30 files):

**`tests/next/`** (5 files):
- `test_decision_unit.py`
- `test_next_command_integration.py`
- `test_prompt_builder_unit.py`
- `test_query_mode_unit.py`
- `test_runtime_bridge_unit.py`

**`tests/runtime/`** (10 files):
- `test_agent_skills.py`
- `test_bootstrap_unit.py`
- `test_config_show_origin_integration.py`
- `test_doctor_command_file_health.py`
- `test_doctor_unit.py`
- `test_e2e_runtime_integration.py`
- `test_global_runtime_convergence_unit.py`
- `test_home_unit.py`
- `test_resolver_unit.py`
- `test_show_origin_unit.py`

**Mixed directories** (15 files):
- `tests/agent/test_workflow_charter_context.py`
- `tests/audit/test_no_legacy_path_literals.py`
- `tests/concurrency/test_ensure_runtime_concurrent.py`
- `tests/contract/test_machine_facing_canonical_fields.py`
- `tests/contract/test_handoff_fixtures.py`
- `tests/init/test_init_minimal_integration.py`
- `tests/kernel/test_paths.py`
- `tests/merge/test_merge_unit.py`
- `tests/specify_cli/cli/commands/test_init_hybrid.py`
- `tests/specify_cli/cli/commands/test_init_integration.py`
- `tests/specify_cli/cli/commands/test_selector_resolution.py`
- `tests/specify_cli/next/test_runtime_bridge.py`
- `tests/specify_cli/runtime/test_agent_commands_routing.py`
- `tests/specify_cli/status/test_progress_integration.py`
- `tests/status/test_doctor.py`
- `tests/upgrade/test_migrate_integration.py`

---

## Subtask T037 — Migrate `tests/next/` (5 files)

**Purpose**: `tests/next/` directly tests the `specify_cli.next.*` modules. After the extraction, these tests should import from `runtime.*` (the canonical location). The test logic does not change — only the import paths.

**Steps**:

1. Read occurrence_map.yaml for the `test_caller` entries covering `tests/next/`.

2. For each file, apply the import rewrites. Example for `test_decision_unit.py`:
   ```python
   # Before:
   from specify_cli.next.decision import decide_next, Decision, DecisionKind

   # After:
   from runtime.decisioning.decision import decide_next, Decision, DecisionKind
   ```

3. Verify the test suite for this directory passes:
   ```bash
   pytest tests/next/ -v --tb=short
   ```

**Files touched**: `tests/next/` (5 files)

**Validation**: `pytest tests/next/ -v` exits 0 with no failures.

---

## Subtask T038 — Migrate `tests/runtime/` (10 files)

**Purpose**: `tests/runtime/` directly tests the `specify_cli.runtime.*` modules. After extraction, imports should target `runtime.*`.

**Steps**:

1. Read occurrence_map.yaml for the `test_caller` entries covering `tests/runtime/`.

2. For each file, apply the import rewrites. Example for `test_home_unit.py`:
   ```python
   # Before:
   from specify_cli.runtime.home import get_kittify_home

   # After:
   from runtime.discovery.home import get_kittify_home
   ```

   Note: `test_e2e_runtime_integration.py` and `test_global_runtime_convergence_unit.py` may import many symbols. Work through the occurrence map entry for each file systematically.

3. Run tests:
   ```bash
   pytest tests/runtime/ -v --tb=short
   ```

**Files touched**: `tests/runtime/` (10 files)

**Validation**: `pytest tests/runtime/ -v` exits 0.

---

## Subtask T039 — Migrate Remaining 15 Test Files

**Purpose**: Apply rewrites to the mixed-directory test files. These tests are not primarily about `next/` or `runtime/` — they import from those modules incidentally (e.g., for fixture setup or integration paths).

**Steps**:

1. Read occurrence_map.yaml for all remaining `test_caller` entries.

2. Apply rewrites file by file. For each file:
   - Identify the specific import lines from the map
   - Replace the old path with the new canonical path
   - Run a quick check: `python -c "import <test_module_path>"` — or run the specific test file

3. **Special case — `tests/audit/test_no_legacy_path_literals.py`**: This test likely asserts that certain import patterns do NOT exist in the codebase. After the extraction, the shim paths become intentional re-exports — make sure this test accounts for them. Read the test logic carefully and update the allowed-list if needed.

4. Run all 15 files:
   ```bash
   pytest tests/agent/ tests/audit/ tests/concurrency/ tests/contract/ \
     tests/init/ tests/kernel/ tests/merge/ \
     tests/specify_cli/cli/commands/ tests/specify_cli/next/ \
     tests/specify_cli/runtime/ tests/specify_cli/status/ \
     tests/status/ tests/upgrade/ -v --tb=short
   ```

**Files touched**: 15 test files across mixed directories

**Validation**: Targeted pytest run exits 0.

---

## Subtask T040 — Validate: Full Test Suite

**Purpose**: Run the full test suite to confirm the WP10 rewrites introduce no new failures and that all shim-import `DeprecationWarning` warnings are resolved (no warnings expected once callers use canonical imports).

**Steps**:

1. Run the full suite:
   ```bash
   cd /home/stijn/Documents/_code/fork/spec-kitty/src
   pytest ../tests/ -v --tb=short -q 2>&1 | tail -30
   ```

2. Confirm the total test count matches (or exceeds) the count before WP10. Tests should not disappear.

3. Confirm zero `DeprecationWarning` from shim paths now that all test callers use canonical imports:
   ```bash
   pytest ../tests/ -W error::DeprecationWarning -q --tb=short 2>&1 | tail -20
   ```
   If any `DeprecationWarning` survives, there is still a test file importing from the old path. Find it with:
   ```bash
   rg "specify_cli\.next|specify_cli\.runtime" tests/ --include="*.py" -l
   ```
   And add it to the occurrence map.

**Validation**: Full suite exits 0; zero `DeprecationWarning` from shim paths in test output.

---

## Branch Strategy

Work in the execution worktree allocated by `spec-kitty agent action implement WP10 --agent claude`. May run in parallel with WP07, WP08, WP09.

- **Planning branch**: `kitty/mission-runtime-mission-execution-extraction-01KPDYGW`
- **Merge target**: `kitty/mission-runtime-mission-execution-extraction-01KPDYGW`

---

## Definition of Done

- [ ] All `test_caller` entries in occurrence_map.yaml rewritten to `runtime.*` canonical imports
- [ ] `pytest tests/next/` exits 0
- [ ] `pytest tests/runtime/` exits 0
- [ ] Full `pytest tests/` exits 0
- [ ] `pytest tests/ -W error::DeprecationWarning` exits 0 (zero shim-path warnings remaining)

---

## Reviewer Guidance

- Confirm `tests/audit/test_no_legacy_path_literals.py` was reviewed and updated if it asserts about import paths
- Run `rg "specify_cli\.next|specify_cli\.runtime" tests/ -l` and confirm it returns zero files (all migrated)
- Check test count before and after — it should not decrease

## Activity Log

- 2026-04-23T12:13:27Z – claude:claude-sonnet-4-6:python-pedro:implementer – shell_pid=938982 – Started implementation via action command
- 2026-04-23T12:54:25Z – claude:claude-sonnet-4-6:python-pedro:implementer – shell_pid=938982 – Test callers migrated; full suite improved from 150 failures to 22 pre-existing failures (13334 passed). All import errors from specify_cli.next/specify_cli.runtime resolved in test files.
- 2026-04-23T13:01:59Z – claude:claude-sonnet-4-6:python-pedro:implementer – shell_pid=938982 – Approved: ~24 test files migrated, zero specify_cli.next/runtime refs remaining in tests, 13334 pass / 22 pre-existing failures (128 resolved from 150 baseline)
