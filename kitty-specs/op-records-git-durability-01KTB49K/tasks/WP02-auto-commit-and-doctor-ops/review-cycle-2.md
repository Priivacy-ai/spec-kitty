---
affected_files: []
cycle_number: 2
mission_slug: op-records-git-durability-01KTB49K
reproduction_command:
reviewed_at: '2026-06-05T06:47:02Z'
reviewer_agent: unknown
verdict: rejected
wp_id: WP02
---

# WP02 Review — Cycle 1

**Reviewer**: Claude (automated review)
**Date**: 2026-06-05
**Result**: REJECTED — 1 blocking test failure, 1 missing test

---

## Summary

23 of 26 tests pass. Implementation is substantially correct and well-structured. Two issues block approval:

1. **BLOCKER — Test failure**: `TestDoctorOpsCLI::test_orphans_found_exits_1` fails
2. **BLOCKER — Missing test**: No test for best-effort WARNING behavior (commit failure path)

---

## Blocking Issue 1: `test_orphans_found_exits_1` fails

**File**: `tests/specify_cli/invocation/test_doctor_ops.py:152`

**Root cause**: `ops_doctor` in `src/specify_cli/cli/commands/doctor.py` prints orphan paths as `str(path)` (absolute path). When the absolute path is long (as in pytest tmp dirs like `/private/var/folders/.../pytest-of-robert/pytest-0/test_orphans_found_exits_10/kitty-ops/AABBCCDD0000000000000007.jsonl`), Rich wraps the line at ~80 characters. The ID `AABBCCDD0000000000000007` is split across two lines as `AABBCCDD00000000000000\n07.jsonl`, so the assertion `assert "AABBCCDD0000000000000007" in result.output` fails.

**Actual output observed**:
```
Op Records — 1 orphan op record(s)

  ! 
/private/var/folders/gj/.../test_orphans_found_exits_10/kitty-ops/AABBCCDD00000000000000
07.jsonl

These op records were started but never completed. Run spec-kitty doctor ops --json for machine-readable output.
```

**Fix options** (pick one):

Option A — Use `path.name` instead of `str(path)` for display, and `path.relative_to(repo_root)` would be even better:
```python
# In ops_doctor, change:
console.print(f"  [yellow]![/yellow] {path}")
# to:
rel = path.relative_to(repo_root)
console.print(f"  [yellow]![/yellow] {rel}")
```
This makes paths relative to repo root (shorter, no wrapping), matches the spec's intent, and makes the test assertion reliable.

Option B — Keep the path display as-is but fix the test to assert on `path.name` instead of the full ID:
```python
# In the test, change:
assert "AABBCCDD0000000000000007" in result.output
# to:
assert "AABBCCDD0000000000000007.jsonl" in result.output.replace("\n", "")
# or assert on the filename only
```

**Recommended**: Option A (relative path display) — this is the better UX and matches the spec guidance that says `str(p.relative_to(repo_root))` in the reference implementation.

---

## Blocking Issue 2: Missing best-effort WARNING test

**Acceptance criterion**: "there must be a test verifying this best-effort behavior" (reviewer briefing) and "Commit failures must be logged at WARNING and must NOT raise" (AC-6).

**Status**: The implementation is correct (`except Exception` catches all, `logger.warning` logs it, never raises). But none of the 4 executor tests exercise the failure path. The spec (Definition of Done) requires tests covering T-003, T-004, T-005, T-006, T-007. There is no T for the WARNING path, but the reviewer briefing explicitly requires a test for best-effort.

**Fix**: Add a test to `TestAutoCommitOnCompleteInvocation` that patches subprocess to raise and asserts:
1. `complete_invocation()` does NOT raise
2. The returned `InvocationRecord` is valid
3. A WARNING is emitted (use `pytest.warns` or `caplog`)

Example:
```python
def test_commit_failure_does_not_raise(self, tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    """Best-effort: git failure must not block the invocation response."""
    import unittest.mock as mock
    _init_git_repo(tmp_path)
    executor = _make_executor(tmp_path)
    payload = executor.invoke("test request", profile_hint="implementer-fixture", actor="claude")
    
    with mock.patch("specify_cli.invocation.executor._subprocess.run", side_effect=OSError("git not found")):
        with caplog.at_level(logging.WARNING, logger="specify_cli.invocation.executor"):
            result = executor.complete_invocation(payload.invocation_id, outcome="done")
    
    assert result is not None  # did not raise
    assert any("auto-commit" in r.message.lower() for r in caplog.records)
```

---

## Non-blocking observations (no action required)

- **Placement of _commit_op_record call**: The spec says "Step 3a" (between write_completed and evidence promotion), but implementation places it as "Step 8" (after propagation, just before `return`). Functionally equivalent for this feature; the audit commit happens after all operations succeed, which is safe and correct. No change required.

- **`executor.py:276` ModeOfWork | None**: This is pre-existing code (not introduced by WP02). No action.

- **`src/specify_cli/doctor/__init__.py`**: Confirmed present and empty. Package imports correctly (tests prove it). Pyright false alarm was pre-commit.

- **CHANGELOG**: Well-written. Covers both the new feature and the `.kittify/events/` abandonment data loss notice.

---

## What passes

- `_commit_op_record()` implemented correctly with `--no-verify`, best-effort exception handling
- Commit message format `op(<profile_id>): <action> [<op_id[:8]>]` is correct
- `list_orphan_ops()` and `_has_completed_event()` implemented correctly
- `_NON_OP_FILENAMES` excludes all 3 required filenames
- `spec-kitty doctor ops` subcommand registered at line 1431, calls `list_orphan_ops(repo_root)`
- `src/specify_cli/doctor/__init__.py` exists
- T-003 (commit in log), T-004 (restorable after clean), T-005 (orphan not committed), T-007 (mission_id/wp_id) all pass
- 9/9 `TestListOrphanOps` tests pass
- `.gitignore` unchanged
- No changes to `InvocationSaaSPropagator` (scope boundary respected)

---

## Required fixes before re-review

1. Fix `ops_doctor` to display `path.relative_to(repo_root)` instead of `str(path)` so that `test_orphans_found_exits_1` passes
2. Add one test verifying that `complete_invocation()` does not raise when the subprocess git commit fails, and that a WARNING is logged
