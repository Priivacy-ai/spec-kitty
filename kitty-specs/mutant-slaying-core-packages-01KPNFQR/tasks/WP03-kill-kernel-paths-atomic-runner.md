---
work_package_id: WP03
title: Kill kernel.paths + kernel.atomic + kernel.glossary_runner survivors
dependencies: []
requirement_refs:
- FR-003
- FR-004
- FR-013
- FR-014
- FR-015
- NFR-002
- NFR-003
- NFR-004
- NFR-005
- NFR-006
planning_base_branch: feature/711-mutant-slaying
merge_target_branch: feature/711-mutant-slaying
branch_strategy: Planning artifacts for this feature were generated on feature/711-mutant-slaying. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feature/711-mutant-slaying unless the human explicitly redirects the landing branch.
subtasks:
- T011
- T012
- T013
- T014
- T015
- T016
phase: Phase 1 - Narrow-surface foundation
history:
- at: '2026-04-20T13:10:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
authoritative_surface: tests/kernel/
execution_mode: code_change
owned_files:
- tests/kernel/test_paths.py
- tests/kernel/test_atomic.py
- tests/kernel/test_glossary_runner.py
tags: []
task_type: implement
---

# Work Package Prompt: WP03 – Kill kernel.paths + atomic + glossary_runner survivors

## Objectives & Success Criteria

- Drive mutation scores to **≥ 60 %** on `kernel.paths`, `kernel.atomic`, and `kernel.glossary_runner` (FR-003, FR-004, NFR-002). Current baseline: 17 + 13 + 1 = 31 survivors.
- Each sub-module target independently verified with scoped mutmut runs.

## Context & Constraints

- **Sources under test**: `src/kernel/paths.py`, `src/kernel/atomic.py`, `src/kernel/glossary_runner.py`.
- **Test files**: `tests/kernel/test_paths.py`, `tests/kernel/test_atomic.py`, `tests/kernel/test_glossary_runner.py` (all exist).
- **Why this matters**: Filesystem helpers and atomic writes are used on every mission boot. A silent regression in path resolution or atomic-write invariant can corrupt `.kittify/` state.

## Branch Strategy

- **Strategy**: lane-per-WP
- **Planning base branch**: `feature/711-mutant-slaying`
- **Merge target branch**: `feature/711-mutant-slaying`

## Subtasks & Detailed Guidance

### Subtask T011 – Kill `paths.render_runtime_path` survivors (6)

- **Purpose**: `render_runtime_path` produces the user-visible path for runtime artefacts (mission workspace, dossier output).
- **Mutant IDs in scope**:
  - `kernel.paths.x_render_runtime_path__mutmut_1`, `__mutmut_3`, `__mutmut_10`, `__mutmut_11`, `__mutmut_21`, `__mutmut_22`
- **Steps**:
  1. Inspect diffs — expect branch mutations on platform checks (Windows vs Unix) and fallback paths.
  2. Apply **Bi-Directional Logic** to platform-detection branches: test with mocked `sys.platform = "linux"` and `sys.platform = "win32"` independently, verify different outputs.
  3. For relative-vs-absolute path handling, apply **Boundary Pair**: test at the platform's path-separator boundary (`/` vs `\\`).

### Subtask T012 – Kill `paths.get_kittify_home` survivors (10)

- **Purpose**: Resolves the `.kittify/` home directory with env-var override + default fallback.
- **Mutant IDs in scope**:
  - `kernel.paths.x_get_kittify_home__mutmut_7` through `__mutmut_16` (10 mutants).
- **Steps**:
  1. Likely mutations: env-var-presence checks, default-path fallback, path-expansion (`~` → home dir).
  2. **Boundary Pair** on env-var presence: test with env var **unset**, **set to empty string**, **set to a valid path**, **set to a non-existent path**.
  3. **Non-Identity Inputs** on default path: mock `Path.home()` to a non-default location and assert the resolution uses it.
  4. If mutants survive around conditional `~` expansion, add a test with a path containing `~` mid-string (should NOT be expanded) and a path starting with `~/` (should be expanded).
- **Parallel?**: `[P]` with T011.

### Subtask T013 – Kill `paths.get_package_asset_root` survivor (1)

- **Purpose**: Finds bundled asset root for the installed package.
- **Mutant IDs in scope**:
  - `kernel.paths.x_get_package_asset_root__mutmut_17`
- **Steps**:
  1. Single mutant — inspect the diff. Likely a fallback-to-repo-root branch mutation.
  2. Test both installed-package mode (mock `__file__` to a site-packages path) and dev-mode (repo-root). Assert different outputs.
- **Parallel?**: `[P]` with T011, T012.

### Subtask T014 – Kill `atomic.atomic_write` survivors (13)

- **Purpose**: `atomic_write` guarantees a file is either fully written or not written at all — used by every state-persistence operation.
- **Mutant IDs in scope**:
  - `kernel.atomic.x_atomic_write__mutmut_1`, `__mutmut_11`, `__mutmut_13` through `__mutmut_22`, `__mutmut_34` (13 mutants).
- **Steps**:
  1. The atomic-write pattern: write to temp file in the same directory → `fsync` → `rename` to final path. Each step has a failure mode worth asserting.
  2. **Boundary Pair** on success-path: test with exactly-0-byte payload, exactly-1-byte payload, large payload (>1MB).
  3. **Bi-Directional Logic** on the exception path: simulate failure at write step → no file should exist at final path. Simulate failure at rename step → temp file should still exist for post-mortem.
  4. **Non-Identity Inputs** on mode flags: assert that `mode="w"` vs `mode="wb"` produce the expected file type (text vs binary). Don't use `mode="w"` with bytes payload in the kill test.
  5. Test the rename-atomicity: write a file with `atomic_write`, verify the final file's content matches expectation even if the temp file is still present (race-condition simulation).
- **Parallel?**: `[P]` with T011, T012, T013.

### Subtask T015 – Kill `glossary_runner.register` survivor (1)

- **Purpose**: Registers a glossary runner for the kernel's glossary subsystem.
- **Mutant IDs in scope**:
  - `kernel.glossary_runner.x_register__mutmut_3`
- **Steps**:
  1. Inspect diff — likely a default-argument or registry-dict update mutation.
  2. Write a test that registers two runners and asserts both are present and retrievable in the order specified.
- **Parallel?**: `[P]`.

### Subtask T016 – Rescope mutmut, verify per-sub-module, append findings residuals

- **Steps**:
  1. Invalidate: `rm mutants/src/kernel/{paths,atomic,glossary_runner}.py.meta`
  2. Run scoped mutmut for each sub-module separately:
     - `uv run mutmut run "kernel.paths*"`
     - `uv run mutmut run "kernel.atomic*"`
     - `uv run mutmut run "kernel.glossary_runner*"`
  3. Verify each ≥ 60 %.
  4. Append three residuals subheadings (one per sub-module) to `docs/development/mutation-testing-findings.md`.

## Test Strategy

Scoped mutmut runs in T016 are acceptance. All tests are sandbox-compatible.

## Risks & Mitigations

- **Risk**: Mocking `sys.platform` leaks between tests.
  - **Mitigation**: Use `monkeypatch.setattr(sys, "platform", ...)` from the pytest fixture — auto-restored on test teardown.
- **Risk**: Atomic-write tests create real files that leak to the test environment.
  - **Mitigation**: Use `tmp_path` fixture exclusively.
- **Risk**: `get_kittify_home` env-var tests interact with the developer's real `SPEC_KITTY_HOME` setting.
  - **Mitigation**: Always `monkeypatch.delenv("SPEC_KITTY_HOME", raising=False)` before each test, then set as needed.

## Review Guidance

- Each sub-module's scoped mutmut score ≥ 60 % (three independent verifications).
- No `tmp_path` leakage; no real filesystem mutations outside test sandboxes.
- Mock-based tests patch at the narrowest scope (function-level `monkeypatch`, not module-level).

## Activity Log

- 2026-04-20T13:10:00Z – system – Prompt created.
