---
work_package_id: WP04
title: Fix Bug
lane: "done"
dependencies: []
base_branch: main
base_commit: 3ae4069aee1f86fe87f26e486b67e0f0521a13e5
created_at: '2026-02-11T15:22:37.846898+00:00'
subtasks: [T020, T021, T022, T023, T024, T025, T026, T027, T028]
phase: Phase 1 - Bug Fixes
shell_pid: "30491"
agent: "codex"
reviewed_by: "Robert Douglass"
review_status: "approved"
---

# Work Package Prompt: WP04 – Fix Bug #117 - Dashboard False-Failure Detection

## Objectives

- Dashboard accurately detects running state (no false failures)
- Process detection works even when health check times out
- Specific error messages for missing metadata, port conflicts
- 10 tests passing (4 lifecycle + 6 dashboard errors)
- Focused fix (1-2 hours, NOT full lifecycle refactor)

**Command**: `spec-kitty implement WP04`

## Context

- **Issue**: #117 by @digitalanalyticsdeveloper
- **Files**: `src/specify_cli/dashboard/lifecycle.py:407,423`, `cli/commands/dashboard.py:45-46`
- **Bug**: Dashboard hangs 30s, reports failure, but actually accessible
- **Scope**: Focused fix for false-failure detection (NOT comprehensive refactor)

## Test-First Subtasks

### T020-T023: Write Failing Tests

1. **T020**: Test process running + health timeout → should report SUCCESS (not failure)
2. **T021**: Test missing .kittify → should report specific error with init suggestion
3. **T022**: Test port conflict → should report "Port X unavailable"
4. **T023**: Test `dashboard --kill` works after startup fallback

### T024-T026: Implement Focused Fix

**T024**: Add process detection in lifecycle.py
```python
def detect_dashboard_process(port: int) -> bool:
    """Check if dashboard process is running on port."""
    # Check PID file or port listener
    # Return True if process exists, False otherwise
```

**T025**: Improve health check timeout handling
```python
# In lifecycle.py around line 407:
# Before declaring failure, check if process exists
if process_exists(port):
    # Process is running, health check just slow
    return DashboardState.RUNNING
else:
    # Process actually failed
    raise RuntimeError(...)
```

**T026**: Add specific error messages in dashboard.py:45-46
```python
except FileNotFoundError:
    console.print("[red]Dashboard metadata not found[/red]")
    console.print("Run: spec-kitty init .")
except OSError as e:
    if "port" in str(e).lower():
        console.print(f"[red]Port conflict[/red]: {e}")
```

### T027-T028: Verify and Commit

- Run all 4 tests, verify ✅ GREEN
- Commit: `fix: improve dashboard lifecycle and error diagnostics (fixes #117)`

## Implementation Notes

**Key Change**: Check process existence BEFORE declaring startup failure.

**Process detection methods**:
1. Check PID file in `.kittify/.dashboard`
2. Check port listener: `lsof -i :8080` or `netstat`
3. If either shows process exists → RUNNING (even if health check timed out)

**Error message improvements**:
- Generic "Unable to start" → Specific error per failure mode
- Include actionable next steps (run init, check port, fix permissions)

## Activity Log

- 2026-02-11T15:20:53Z – unknown – lane=planned – Moved to planned
- 2026-02-11T15:25:56Z – claude-sonnet-4.5 – shell_pid=5113 – lane=doing – Assigned agent via workflow command
- 2026-02-11T15:37:05Z – claude-sonnet-4.5 – shell_pid=5113 – lane=for_review – Ready for review: Fixed Bug #117 - Dashboard false-failure detection. Process detection added before declaring startup failure. Specific error messages for common failure modes. 5 new tests, all passing. No regressions.
- 2026-02-11T15:37:20Z – codex – shell_pid=16312 – lane=doing – Started review via workflow command
- 2026-02-11T15:48:05Z – codex – shell_pid=16312 – lane=for_review – Moved to for_review
- 2026-02-11T15:48:14Z – codex – shell_pid=30491 – lane=doing – Started review via workflow command
- 2026-02-11T15:58:54Z – codex – shell_pid=30491 – lane=done – Review passed: Bug #117 fix correctly handles health-check timeout false failures via process-alive fallback; added specific CLI errors for missing metadata/port conflicts; added and passing 10 WP04 tests plus passing broader dashboard lifecycle/CLI coverage.
