---
work_package_id: WP04
title: Regression Coverage and Copy-Parity Sweep
lane: "for_review"
dependencies: [WP03]
base_branch: 052-acceptance-pipeline-regression-fixes-WP03
base_commit: 80e1da9f381882629d974cbf25af003791cd3b39
created_at: '2026-03-19T17:24:07.240529+00:00'
subtasks:
- T012
- T013
- T014
- T015
- T016
phase: Phase 3 - Verification
assignee: ''
agent: coordinator
shell_pid: '16978'
review_status: ''
reviewed_by: ''
review_feedback: ''
history:
- timestamp: '2026-03-19T16:39:32Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
requirement_refs:
- NFR-002
- NFR-003
- C-001
- C-003
---

# Work Package Prompt: WP04 – Regression Coverage and Copy-Parity Sweep

## ⚠️ IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check `review_status`. If it says `has_feedback`, read `review_feedback` first.
- **You must address all feedback** before your work is complete.
- **Mark as acknowledged**: Update `review_status: acknowledged` when you begin addressing feedback.

---

## Objectives & Success Criteria

- Each of the 4 regressions has at least one dedicated test.
- All new tests pass after WP01-WP03 fixes are applied.
- `acceptance.py` and `acceptance_support.py` are verified to stay behaviorally aligned.
- Existing test suite continues to pass (C-003).

**Success gate**: `python -m pytest tests/specify_cli/test_acceptance_regressions.py -v` — all 5 tests pass.

## Context & Constraints

- **Spec**: `kitty-specs/052-acceptance-pipeline-regression-fixes/spec.md` — all 4 user stories
- **Plan**: `kitty-specs/052-acceptance-pipeline-regression-fixes/plan.md` — all bug analyses
- **Constraint C-003**: No modifications to existing tests — only new tests
- **NFR-002**: Each bug must have at least one dedicated test
- **NFR-003**: Standalone entrypoint test required

## Implementation Command

```bash
spec-kitty implement WP04 --base WP03
```

## Subtasks & Detailed Guidance

### Subtask T012 – Test: `collect_feature_summary()` does not dirty repo via `materialize()`

- **Purpose**: Regression test for P0 — proves the verification path no longer dirties the repo.
- **File**: `tests/specify_cli/test_acceptance_regressions.py` (new file)
- **Steps**:
  1. Create a temp directory with a git repo (`git init`).
  2. Create a minimal feature structure:
     - `kitty-specs/099-test-feature/meta.json` with required fields
     - `kitty-specs/099-test-feature/spec.md`, `plan.md`, `tasks.md` (minimal content)
     - `kitty-specs/099-test-feature/tasks/WP01-test.md` with frontmatter: `lane: "done"`, `work_package_id: "WP01"`, plus required fields (`agent`, `shell_pid`, `assignee`)
     - `kitty-specs/099-test-feature/status.events.jsonl` with a valid event transitioning WP01 to `done`
  3. Commit everything so the repo is clean.
  4. Call `collect_feature_summary(repo_root, "099-test-feature")`.
  5. Assert `summary.git_dirty` is an empty list.
  6. Also assert that calling it a SECOND time still reports clean (no cumulative drift).
- **Parallel?**: No
- **Notes**:
  - Use `specify_cli.status.models.StatusEvent` and `specify_cli.status.store.append_event` to create a valid event.
  - The `materialize()` call WILL still write `status.json`, but `git_status_lines()` is now called BEFORE it.
  - Use `tmp_path` pytest fixture for the temp directory.
  - The feature needs all required fields in WP frontmatter to avoid metadata_issues blocking `summary.ok`.

### Subtask T013 – Test: `perform_acceptance()` persists `accept_commit` to `meta.json`

- **Purpose**: Regression test for P1 — proves the commit SHA is written to `meta.json`.
- **File**: `tests/specify_cli/test_acceptance_regressions.py`
- **Steps**:
  1. Create a temp git repo with a clean, fully-done feature (same setup as T012).
  2. Call `collect_feature_summary()` to get the summary.
  3. Call `perform_acceptance(summary, mode="local", actor="test-agent")`.
  4. Read `meta.json` from the feature directory.
  5. Assert `meta["accept_commit"]` is not None and is a valid git SHA (40 hex chars).
  6. Assert `meta["acceptance_history"][-1]["accept_commit"]` matches the top-level value.
  7. Assert `result.accept_commit` matches the value in `meta.json`.
- **Parallel?**: No
- **Notes**:
  - The meta.json will have an uncommitted change after acceptance (the SHA write-back). This is expected.
  - Make sure the test repo has at least one commit before acceptance, otherwise `rev-parse HEAD` will fail.

### Subtask T014 – Test: standalone `tasks_cli.py --help` succeeds via subprocess

- **Purpose**: Regression test for P1 — proves the standalone entrypoint works without pip install.
- **File**: `tests/specify_cli/test_acceptance_regressions.py`
- **Steps**:
  1. Determine the path to `src/specify_cli/scripts/tasks/tasks_cli.py` relative to the repo root.
  2. Run `subprocess.run()`:
     ```python
     result = subprocess.run(
         [sys.executable, str(script_path), "--help"],
         capture_output=True,
         text=True,
         timeout=30,
         env={**os.environ, "PYTHONPATH": ""},  # Clear PYTHONPATH to simulate no pip install
     )
     ```
  3. Assert `result.returncode == 0`.
  4. Assert `"ModuleNotFoundError"` not in `result.stderr`.
  5. Assert `"usage"` in `result.stdout.lower()` or `"--help"` in `result.stdout` (confirms help text rendered).
- **Parallel?**: No
- **Notes**:
  - Use `sys.executable` (not `"python3"`) to match the current Python interpreter.
  - The `PYTHONPATH=""` environment override prevents the installed package from being found via PYTHONPATH. However, the pip-installed package may still be found via site-packages. For a true standalone test, you'd need a virtualenv without spec-kitty installed — but that's overkill for a regression test. The key assertion is no `ModuleNotFoundError`.
  - If the test environment does have spec-kitty pip-installed, the test still validates the script starts up — it just can't distinguish sys.path bootstrap from pip install. That's acceptable.

### Subtask T015 – Test: malformed `status.events.jsonl` raises `AcceptanceError`

- **Purpose**: Regression test for P2 — proves malformed event logs produce structured errors.
- **File**: `tests/specify_cli/test_acceptance_regressions.py`
- **Steps**:
  1. Create a temp git repo with a feature structure (similar to T012, but with a malformed event log).
  2. Write invalid JSON to `status.events.jsonl`:
     ```python
     events_path = feature_dir / "status.events.jsonl"
     events_path.write_text("this is not valid json\n")
     ```
  3. Commit everything so the repo is clean.
  4. Call `collect_feature_summary(repo_root, "099-test-feature")` inside `pytest.raises(AcceptanceError)`.
  5. Assert the exception message contains `"corrupted"` (from the StoreError-to-AcceptanceError conversion).
  6. Assert the exception is NOT a `StoreError` (import `StoreError` from `specify_cli.status.store` and verify the caught exception type).
- **Parallel?**: No
- **Notes**:
  - Also test with partially valid JSONL (first line valid, second line invalid) — the error should still be `AcceptanceError`.
  - Test with an empty file (zero bytes) — `read_events()` returns `[]`, so `materialize()` should succeed with an empty snapshot (no error expected).

### Subtask T016 – Copy-parity assertions

- **Purpose**: Verify that the key functions in `acceptance.py` and `acceptance_support.py` remain behaviorally aligned.
- **File**: `tests/specify_cli/test_acceptance_regressions.py`
- **Steps**:
  1. Import both modules:
     ```python
     from specify_cli import acceptance
     from specify_cli.scripts.tasks import acceptance_support
     ```
  2. Compare `__all__` exports — the standalone copy may have extras (e.g., `ArtifactEncodingError`, `normalize_feature_encoding`), but the core set must be a subset:
     ```python
     core_exports = set(acceptance.__all__)
     standalone_exports = set(acceptance_support.__all__)
     assert core_exports.issubset(standalone_exports), (
         f"Missing from standalone: {core_exports - standalone_exports}"
     )
     ```
  3. Compare function signatures for key functions using `inspect.signature()`:
     ```python
     import inspect
     for fn_name in ["collect_feature_summary", "perform_acceptance", "choose_mode", "detect_feature_slug"]:
         sig_core = inspect.signature(getattr(acceptance, fn_name))
         sig_standalone = inspect.signature(getattr(acceptance_support, fn_name))
         assert sig_core == sig_standalone, (
             f"{fn_name} signature mismatch: {sig_core} vs {sig_standalone}"
         )
     ```
  4. Note: `detect_feature_slug` may have a different signature between the two copies (the standalone copy doesn't use centralized detection). Only compare functions that are meant to be identical.
- **Parallel?**: No
- **Notes**: This test is structural — it doesn't test behavior, just that the two copies haven't drifted apart in their public API. If signatures diverge intentionally in the future, update the test to reflect the expected differences.

## Risks & Mitigations

- **Risk**: T014 may pass even without the sys.path fix if spec-kitty is pip-installed. **Mitigation**: The test is a safety net, not a guarantee. In CI (where spec-kitty may not be installed), it provides stronger coverage.
- **Risk**: T012/T013 require a realistic feature setup with valid event logs and WP frontmatter — complex fixture. **Mitigation**: Extract a shared `_create_test_feature()` helper within the test file.
- **Risk**: ~50 pre-existing test failures. **Mitigation**: New tests run in isolation (`-k test_acceptance_regressions`). They must not depend on or be affected by other test state.

## Review Guidance

- Verify each test targets exactly one regression (no test covers multiple bugs).
- Verify T012 creates a genuinely clean repo before calling `collect_feature_summary()`.
- Verify T013 checks both `accept_commit` (top-level) and `acceptance_history[-1]["accept_commit"]`.
- Verify T014 uses `subprocess.run()` (not an in-process import test).
- Verify T015 asserts `AcceptanceError`, NOT `StoreError`.
- Verify T016 compares the correct function set (skip `detect_feature_slug` if signatures intentionally differ).
- Run: `python -m pytest tests/specify_cli/test_acceptance_regressions.py -v`

## Activity Log

- 2026-03-19T16:39:32Z – system – lane=planned – Prompt created.
- 2026-03-19T17:24:07Z – coordinator – shell_pid=16978 – lane=doing – Assigned agent via workflow command
- 2026-03-19T17:31:24Z – coordinator – shell_pid=16978 – lane=for_review – Ready for review: 7 tests (5 regression + 2 edge case) all passing
