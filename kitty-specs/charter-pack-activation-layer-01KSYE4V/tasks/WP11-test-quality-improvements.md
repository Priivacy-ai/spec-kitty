---
work_package_id: WP11
title: Test Quality Improvements
dependencies:
- WP02
- WP08
requirement_refs:
- FR-026
- FR-027
- FR-029
- FR-030
tracker_refs: []
planning_base_branch: pr/charter-doctrine-mission-type-configuration
merge_target_branch: pr/charter-doctrine-mission-type-configuration
branch_strategy: Planning artifacts for this mission were generated on pr/charter-doctrine-mission-type-configuration. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into pr/charter-doctrine-mission-type-configuration unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-charter-pack-activation-layer-01KSYE4V
base_commit: 205cc491fb4e0b37f9bebfa483913317e682c6fc
created_at: '2026-05-31T14:19:53.720479+00:00'
subtasks:
- T048
- T049
- T050
- T051
agent: "claude:sonnet-4-6:reviewer-renata:reviewer"
shell_pid: "64266"
history:
- at: '2026-05-31T11:44:22Z'
  event: created
  actor: claude
agent_profile: python-pedro
authoritative_surface: tests/
execution_mode: code_change
owned_files:
- tests/specify_cli/next/test_runtime_bridge_dispatch.py
- tests/charter/test_mission_type_activation.py
- tests/specify_cli/next/test_decision_dispatch.py
- tests/release/test_diff_coverage_policy.py
role: implementer
tags: []
---

## Do This First: Load Agent Profile

Before reading anything else, load the implementer profile:

```
/ad-hoc-profile-load python-pedro
```

You are implementing as **python-pedro** (Python implementer). Work precisely, make
only the changes described, validate after each subtask, and do not touch files
outside the `owned_files` list above.

---

## Objective

Four targeted test quality improvements addressing gaps in the test suite:

- **T048** (FR-026): Extend the NFR-001 performance test with a real-filesystem
  variant that measures `PackContext.from_config()` against actual YAML I/O.
- **T049** (FR-027): Add a three-state semantics test confirming that
  `mission_type_activations: [software-dev]` excludes `documentation`, `research`,
  and `plan`.
- **T050** (FR-029): Move a `subprocess.run` call out of a `@pytest.mark.fast`-marked
  test into an integration-marked test.
- **T051** (FR-030): Replace a vacuous `assert True` in the decision dispatch test
  with a meaningful invariant check.

WP02 must be `approved` or `done` before starting (T048 and T049 exercise the new
`activated_agent_profiles` field on `PackContext`). WP08 must be `approved` or
`done` before starting (T048 uses the real charter resolution path that WP08 wires).

---

## Context

### Existing NFR-001 test (T048 baseline)

`tests/specify_cli/next/test_runtime_bridge_dispatch.py` contains a `TestPerformance`
class starting at approximately line 257. That test mocks `MissionTypeRepository`
and measures Python function-call overhead only — it does not exercise filesystem
I/O. FR-026 requires adding a *second* test alongside it (do NOT replace the mock
test) that uses a real `tmp_path` filesystem layout.

### FR-027 target (T049)

`tests/charter/test_pack_context.py` already covers basic `from_config()` behavior
(`pytestmark = [pytest.mark.fast]`). The new test adds a three-state assertion:
when `mission_type_activations` restricts to `software-dev`, the other three
built-in types must be absent from `activated_mission_types`.

### FR-029 target (T050)

The offending test is in `tests/release/test_diff_coverage_policy.py`. The function
`test_close_with_evidence_does_not_modify_workflow` carries `@pytest.mark.fast`
(line 148) but calls `subprocess.run` twice (lines 160, 175) for real git operations.
The file-level `pytestmark` is `[pytest.mark.integration, pytest.mark.git_repo]`,
so removing `@pytest.mark.fast` from that one function is the minimal fix.

### FR-030 target (T051)

`tests/specify_cli/next/test_decision_dispatch.py` has a `TestWPIdSkipsComposedPath`
class with `test_wp_id_set_skips_composed_path`. The test body ends with:

```python
assert True  # No exception = pass; the WP-scoped path was taken
```

This is a vacuous assertion — it passes even if the function returns nonsense. The
test must be replaced with a meaningful invariant check on the dispatch outcome.

---

## Branch Strategy

```
planning_base_branch: pr/charter-doctrine-mission-type-configuration
merge_target_branch:  pr/charter-doctrine-mission-type-configuration
```

All commits go directly onto `pr/charter-doctrine-mission-type-configuration` in the
lane worktree allocated by `finalize-tasks`. Do not create additional git branches.

---

## Subtasks

### T048 — Extend NFR-001 to real filesystem I/O, p99 methodology (FR-026)

**File**: `tests/specify_cli/next/test_runtime_bridge_dispatch.py`

Add a new test class `TestPerformanceRealIO` immediately after the existing
`TestPerformance` class (which ends at approximately line 293). Do NOT modify the
existing `TestPerformance` class.

1. Read the end of the existing `TestPerformance` class to find the exact insertion
   line:
   ```bash
   grep -n "class TestPerformance\|def test_resolve_action_sequence" \
     tests/specify_cli/next/test_runtime_bridge_dispatch.py | head -5
   ```

2. Check what imports are already at the top of the file:
   ```bash
   head -30 tests/specify_cli/next/test_runtime_bridge_dispatch.py
   ```
   Add `import time` if not present.

3. Add the new class after the existing `TestPerformance` block:

   ```python
   class TestPerformanceRealIO:
       """NFR-001: PackContext.from_config() ≤100ms p99 under real filesystem I/O."""

       @pytest.mark.slow
       def test_pack_context_from_config_p99_under_100ms(self, tmp_path: Path) -> None:
           """Real I/O: PackContext.from_config() p99 ≤ 100ms over 50 runs."""
           import time

           from charter.pack_context import PackContext

           kittify = tmp_path / ".kittify"
           kittify.mkdir()
           config_text = (
               "mission_type_activations:\n"
               "  - software-dev\n"
               "  - documentation\n"
               "  - research\n"
               "  - plan\n"
               "activated_kinds:\n"
               "  - directives\n"
               "  - tactics\n"
               "  - styleguides\n"
               "  - toolguides\n"
               "  - paradigms\n"
               "  - procedures\n"
               "  - agent_profiles\n"
               "  - mission_step_contracts\n"
               "activated_directives:\n"
               "  - python-style-guide\n"
               "  - clean-code\n"
               "activated_agent_profiles:\n"
               "  - python-pedro\n"
               "  - reviewer-renata\n"
           )
           (kittify / "config.yaml").write_text(config_text, encoding="utf-8")

           # Warm run — excludes import overhead from the measurement.
           PackContext.from_config(tmp_path)

           timings_ms: list[float] = []
           for _ in range(50):
               start = time.monotonic()
               PackContext.from_config(tmp_path)
               elapsed_ms = (time.monotonic() - start) * 1000
               timings_ms.append(elapsed_ms)

           timings_ms.sort()
           # Index 49 of 50 sorted values = 98th percentile proxy; use index 49
           # for the worst observed value in a 50-run sample as the p99 estimate.
           p99 = timings_ms[49]
           p50 = timings_ms[24]
           assert p99 <= 100, (
               f"PackContext.from_config() p99={p99:.2f}ms > 100ms NFR-001 budget. "
               f"p50={p50:.2f}ms, max={timings_ms[-1]:.2f}ms"
           )
   ```

4. Verify the test is NOT marked `@pytest.mark.fast` (it uses `@pytest.mark.slow`
   so it will not pollute the fast suite).

**Acceptance criterion**: `pytest tests/specify_cli/next/test_runtime_bridge_dispatch.py -x`
passes with both `TestPerformance` and `TestPerformanceRealIO` present. The new
test is excluded from `pytest -m fast`.

---

### T049 — Add FR-027 `mission_type_activations` filter test

**File**: `tests/charter/test_mission_type_activation.py`

**OWNERSHIP NOTE**: This WP owns `tests/charter/test_mission_type_activation.py`,
NOT `tests/charter/test_pack_context.py` (the latter is owned by WP02). Write
this test to the owned file. Create the file if it does not exist.

1. Check whether the file exists:
   ```bash
   ls tests/charter/test_mission_type_activation.py 2>/dev/null || echo "CREATE NEW"
   ```
   If it does not exist, create it with the standard header:
   ```python
   """FR-027 tests: mission_type_activations filtering semantics."""
   from __future__ import annotations
   from pathlib import Path
   import pytest
   from charter.pack_context import PackContext
   pytestmark = [pytest.mark.fast]
   ```

2. Add the test (to the existing file or at the end of the newly created one):

   ```python
   def test_only_specified_mission_type_is_activated(tmp_path: Path) -> None:
       """FR-027: mission_type_activations: [software-dev] excludes the other
       three built-in mission types from activated_mission_types."""
       kittify = tmp_path / ".kittify"
       kittify.mkdir()
       (kittify / "config.yaml").write_text(
           "mission_type_activations:\n  - software-dev\n",
           encoding="utf-8",
       )

       ctx = PackContext.from_config(tmp_path)

       assert ctx.activated_mission_types == frozenset({"software-dev"}), (
           f"Expected only 'software-dev', got: {ctx.activated_mission_types}"
       )
       assert "documentation" not in ctx.activated_mission_types, (
           "documentation must be excluded when not listed in mission_type_activations"
       )
       assert "research" not in ctx.activated_mission_types, (
           "research must be excluded when not listed in mission_type_activations"
       )
       assert "plan" not in ctx.activated_mission_types, (
           "plan must be excluded when not listed in mission_type_activations"
       )
   ```

**Acceptance criterion**: `pytest tests/charter/test_mission_type_activation.py -x -k "test_only_specified_mission_type"` passes.

---

### T050 — Fix FR-029: remove `@pytest.mark.fast` from subprocess test

**File**: `tests/release/test_diff_coverage_policy.py`

The function `test_close_with_evidence_does_not_modify_workflow` at line 148 is
marked `@pytest.mark.fast` but calls `subprocess.run` twice for live git operations.
The file-level `pytestmark` is already `[pytest.mark.integration, pytest.mark.git_repo]`,
which is the correct mark for this test.

1. Confirm the exact line number and function body:
   ```bash
   grep -n "@pytest.mark.fast\|def test_close_with_evidence" \
     tests/release/test_diff_coverage_policy.py | head -5
   ```

2. Remove only the `@pytest.mark.fast` decorator from `test_close_with_evidence_does_not_modify_workflow`.
   Do not change any other decorator or the function body.

   Before:
   ```python
   @pytest.mark.fast
   def test_close_with_evidence_does_not_modify_workflow() -> None:
   ```

   After:
   ```python
   def test_close_with_evidence_does_not_modify_workflow() -> None:
   ```

3. Verify no other `@pytest.mark.fast` tests in the file call subprocess:
   ```bash
   grep -n "@pytest.mark.fast" tests/release/test_diff_coverage_policy.py
   ```
   For each remaining `@pytest.mark.fast` function, confirm it does not call
   `subprocess.run` or `subprocess.check_call` directly (mocked calls via `patch`
   are acceptable).

**Acceptance criterion**: `pytest tests/ -m fast -x -q` completes without invoking
any live `subprocess.run` calls from `test_diff_coverage_policy.py`.

---

### T051 — Fix FR-030: vacuous assertion in decision dispatch test

**File**: `tests/specify_cli/next/test_decision_dispatch.py`

The test `test_wp_id_set_skips_composed_path` in class `TestWPIdSkipsComposedPath`
currently ends with:

```python
assert True  # No exception = pass; the WP-scoped path was taken
```

This assertion is vacuous — it passes regardless of what `_build_prompt_or_error`
returns.

1. Read the full test body to understand what it actually returns:
   ```bash
   grep -n "def test_wp_id_set_skips_composed_path" \
     tests/specify_cli/next/test_decision_dispatch.py
   ```
   Then read the function from that line to understand `path` and `_error`.

2. Understand what `_build_prompt_or_error` is expected to return when `wp_id` is
   set and the template builder fails gracefully:
   ```bash
   grep -n "def _build_prompt_or_error\|return.*path\|return.*error" \
     src/specify_cli/next/_internal_runtime/*.py \
     tests/specify_cli/next/test_decision_dispatch.py 2>/dev/null | head -10
   ```

3. The test comment says: "Either a real prompt path or an error message — but NOT
   a composed marker." The meaningful invariant is that the WP-scoped path was taken
   (i.e. `resolve_action_sequence` was NOT called, because the composed path was
   skipped). The mock patches `resolve_action_sequence` — we can assert it was NOT
   called:

   Replace:
   ```python
   # The key assertion is that the function handled this without crashing.
   # If the template builder fails, path is None and error is set.
   # Either is acceptable as long as we didn't produce a marker for a WP-scoped action.
   assert True  # No exception = pass; the WP-scoped path was taken
   ```

   With:
   ```python
   # The WP-scoped path skips the composed marker entirely.
   # resolve_action_sequence must NOT have been called (that call belongs to
   # the composed path, which WP-scoped actions bypass).
   # If the template builder fails gracefully, path is None and error is set.
   # Both are acceptable; the key invariant is no composed marker was produced.
   from unittest.mock import MagicMock
   # The patch inside the `with` block mocks resolve_action_sequence.
   # After the `with` exits, verify the mock was NOT called for the WP path:
   # (Restructure: capture the mock and assert call_count == 0, OR assert that
   # the result is not a composed-marker path.)
   # Minimal fix: assert the result is not a composed-marker path.
   if path is not None:
       assert ".spec-kitty-composed-marker" not in str(path), (
           "WP-scoped actions must not produce a composed marker; "
           f"got path: {path}"
       )
   else:
       # path is None = template builder failed gracefully; that is acceptable,
       # but _error must explain why (not be an empty string).
       assert _error, (
           "When _build_prompt_or_error returns path=None, error must be non-empty"
       )
   ```

   Alternatively, if the mock object for `resolve_action_sequence` is accessible
   after the `with` block, assert `mock_resolve.call_count == 0`.

   Choose the approach that best matches the test structure after reading the actual
   code.

**Acceptance criterion**: `pytest tests/specify_cli/next/test_decision_dispatch.py -x -v`
passes and the replaced assertion is non-trivially connected to the function's
return value.

---

## Validation Commands

After completing all subtasks, run these in order:

```bash
# 1. Static analysis on all owned test files
cd /home/stijn/Documents/_code/SDD/fork/spec-kitty && \
  ruff check \
    tests/specify_cli/next/test_runtime_bridge_dispatch.py \
    tests/charter/test_pack_context.py \
    tests/specify_cli/next/test_decision_dispatch.py \
    tests/release/test_diff_coverage_policy.py

# 2. T048 — real I/O performance test (marked slow, so run explicitly)
cd /home/stijn/Documents/_code/SDD/fork/spec-kitty && \
  pytest tests/specify_cli/next/test_runtime_bridge_dispatch.py \
    -x -v -m "slow or not fast"

# 3. T049 — FR-027 three-state test
cd /home/stijn/Documents/_code/SDD/fork/spec-kitty && \
  pytest tests/charter/test_pack_context.py -x -v

# 4. T051 — decision dispatch
cd /home/stijn/Documents/_code/SDD/fork/spec-kitty && \
  pytest tests/specify_cli/next/test_decision_dispatch.py -x -v

# 5. Fast suite — must contain zero subprocess calls from the patched file
cd /home/stijn/Documents/_code/SDD/fork/spec-kitty && \
  pytest tests/ -m fast -x -q

# 6. Confirm T050: the modified test is NOT collected under fast
cd /home/stijn/Documents/_code/SDD/fork/spec-kitty && \
  pytest tests/release/test_diff_coverage_policy.py \
    --collect-only -q -m fast | grep "test_close_with_evidence" \
  && echo "FAIL: test still marked fast" || echo "PASS: test not in fast suite"
```

All commands must complete without errors or test failures.

---

## Definition of Done

- `TestPerformanceRealIO` added to `test_runtime_bridge_dispatch.py`; exercises
  real YAML I/O via `PackContext.from_config()` over 50 runs, asserts p99 ≤ 100ms;
  marked `@pytest.mark.slow`, excluded from `pytest -m fast`.
- `test_only_specified_mission_type_is_activated` added to `test_pack_context.py`;
  asserts that `mission_type_activations: [software-dev]` excludes `documentation`,
  `research`, and `plan`; automatically picked up by `pytest -m fast`.
- `@pytest.mark.fast` removed from `test_close_with_evidence_does_not_modify_workflow`
  in `test_diff_coverage_policy.py`; `pytest tests/ -m fast -x -q` no longer
  invokes live git subprocesses from that file.
- Vacuous `assert True` in `test_wp_id_set_skips_composed_path` replaced with a
  meaningful invariant; `pytest tests/specify_cli/next/test_decision_dispatch.py -x`
  passes.
- `ruff check` passes on all four owned files.
- `pytest tests/ -m fast -x -q` passes with no regressions.

## Activity Log

- 2026-05-31T14:19:54Z – claude:sonnet-4-6:python-pedro:implementer – shell_pid=6774 – Assigned agent via action command
- 2026-05-31T14:26:07Z – claude:sonnet-4-6:python-pedro:implementer – shell_pid=6774 – Ready for review: T048 adds TestPerformanceRealIO (real filesystem p99 NFR-001 test), T049 adds test_mission_type_activation.py with FR-027 three-state semantics, T050 removes @pytest.mark.fast from subprocess-using test, T051 replaces vacuous assert True with meaningful composed-marker exclusion invariant
- 2026-05-31T14:26:30Z – claude:sonnet-4-6:reviewer-renata:reviewer – shell_pid=64266 – Started review via action command
- 2026-05-31T14:38:02Z – claude:sonnet-4-6:reviewer-renata:reviewer – shell_pid=64266 – Review passed: test quality improvements complete. T048 adds TestPerformanceRealIO with real filesystem p99 NFR-001 test (marked slow, excluded from fast suite). T049 adds test_mission_type_activation.py with FR-027 three-state semantics confirming software-dev exclusivity. T050 removes @pytest.mark.fast from subprocess-using test (verified not in fast suite). T051 replaces vacuous assert True with meaningful composed-marker exclusion invariant tied to production code return value. All owned files only. ruff clean. 8438 fast tests pass.
