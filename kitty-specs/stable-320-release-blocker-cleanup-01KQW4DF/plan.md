# Implementation Plan: 3.2.0 Release Blocker Cleanup

**Branch**: `main` | **Date**: 2026-05-05 | **Spec**: [spec.md](spec.md)
**Mission**: `stable-320-release-blocker-cleanup-01KQW4DF` (`01KQW4DF`)
**Input**: `kitty-specs/stable-320-release-blocker-cleanup-01KQW4DF/spec.md`

---

## Summary

Fix four CLI release blockers (#952, #783, #975, #976) discovered during the
Stable 3.2.0 P1 Release Confidence smoke run. Each blocker is an isolated,
self-contained bug fix with focused regression tests. The mission spans two
repositories: `spec-kitty` (primary — three blockers) and
`spec-kitty-end-to-end-testing` (one blocker). All changes are Python, all are
CLI-side, and none require `spec-kitty-saas` or `spec-kitty-tracker` changes.

---

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: typer (CLI framework), rich (console output), ruamel.yaml (YAML/frontmatter), spec-kitty-events (external PyPI — event models), pytest (tests), mypy (strict type checking)
**Storage**: Filesystem only — JSONL event log (`status.events.jsonl`), YAML config, Markdown task artifacts; no database
**Testing**: pytest with mypy --strict; 90%+ coverage required for all new code; integration tests for every modified CLI command; unit tests for new helper modules
**Target Platform**: macOS and Linux (CI: GitHub Actions); no Windows requirement for the E2E scenario (uv-managed Python issue is macOS-specific)
**Project Type**: Python CLI package (single-repo for three blockers; cross-repo E2E for Blocker 3)
**Performance Goals**: Sync fast-path overhead < 5 ms for deduplication logic (NFR-003); all other changes have standard CLI latency expectations
**Constraints**: mypy --strict must pass on all modified files; no new code in `spec-kitty-tracker` (C-001/C-003); all smoke verification commands use `SPEC_KITTY_ENABLE_SAAS_SYNC=1` (C-002)

---

## Charter Check

**Charter**: `/Users/robert/spec-kitty-dev/spec-kitty-20260505-090055-4etGRd/spec-kitty/.kittify/doctrine`

| Check | Status | Notes |
|-------|--------|-------|
| Template set (software-dev-default) | ✅ Pass | Correct template applied |
| Toolchain: typer, rich, ruamel.yaml, pytest, mypy | ✅ Pass | All in use; no new framework additions |
| 90%+ test coverage for new code | ✅ Pass | Each blocker fix includes targeted regression tests |
| mypy --strict | ✅ Pass | Must pass; new modules and modifications are typed |
| Integration tests for CLI commands | ✅ Pass | mark-status and merge dry-run changes include integration tests |
| DIRECTIVE_003: Material decisions documented | ✅ Pass | DM-01KQW556RAG1N0QF7PVSTP08P7 captured; ADR below |
| DIRECTIVE_010: Spec fidelity | ✅ Pass | All 19 FRs addressed; no deviations |
| No tracker rollout machinery (C-001/C-003) | ✅ Pass | Zero changes to spec-kitty-tracker |
| No SaaS-side changes required | ✅ Pass | All four fixes are CLI-side; auth-refresh contention is local process-coordination |

**No charter violations.** No Complexity Tracking entries required.

---

## Engineering Alignment

### Resolved Planning Decision

**DM-01KQW556RAG1N0QF7PVSTP08P7** — `merge --dry-run` missing-branch behavior:
- **Chosen**: `always_blocker` — dry-run reports `ready: false` with `blocker: missing_mission_branch`, `expected_branch`, and `remediation`. User creates the branch manually.
- **Rationale**: `merge --dry-run` must be read-only. A write side-effect (auto-creating a branch) in a nominally read-only path would violate the contract of dry-run, introduce non-idempotent behavior, and risk silent branch creation in multi-worktree environments where the branch should originate from worktree allocation. The added manual step (one `git branch` command) is an acceptable tradeoff.
- **Real merge**: applies the same preflight check and blocks before any irreversible operation.

### Confirmed Assumptions

1. **SaaS scope (Blocker 1)**: Fix is CLI-side only. The `sync.final_sync_lock_unavailable` error is a local daemon `fcntl`/`flock` timeout; the auth-refresh contention is a local process-coordination issue (another `spec-kitty` process holds the session lock). No changes to `spec-kitty-saas`.

2. **mark-status WP ID delegation (Blocker 2)**: When `mark-status WP02 --status done` is invoked, the command resolves `WP02` against the mission's status event log via `emit_status_transition()` in `src/specify_cli/status/emit.py`. If the WP is already in the target lane, it returns `already-satisfied`. If the transition is invalid, it returns `not-found` with the reason.

3. **E2E helper (Blocker 3)**: `uv` detection uses `shutil.which("uv")` and inspects whether the outer Python was launched by uv (`sys.executable` path heuristic). The helper lives in `spec-kitty-end-to-end-testing/support/nested_env.py` and is accessible to all scenarios in that repo.

4. **Retry count (FR-005)**: Bounded retry for final sync is 3 attempts with 1-second backoff. This is sufficient for a normally reachable server on a development network and stays well under the 5 ms fast-path overhead budget.

---

## Architectural Decision Record

### ADR: Sync Diagnostic Routing (Blocker 1)

**Context**: Final-sync errors currently flow through `batch.py`'s `format_sync_summary()` and `daemon.py`'s startup outcome, reaching the console via whatever output path the CLI command uses — including stdout, which pollutes `--json` output.

**Decision**: Introduce `src/specify_cli/sync/diagnostics.py` as the single authority for final-sync diagnostic emission. It holds:
- `SyncDiagnosticCode` (5-category enum)
- `emit_sync_diagnostic(code, detail)` — writes exactly one structured line to stderr per invocation; uses a per-invocation seen-set for deduplication; never writes to stdout
- `classify_sync_error(exc_or_msg)` — maps raw error signals to `SyncDiagnosticCode`

All call sites in `daemon.py` and `batch.py` that currently emit final-sync error text are refactored to call `emit_sync_diagnostic()`. No red failure prefixes are used for non-fatal sync errors.

**Alternatives rejected**:
- Logging module: would require reconfiguring log routing per command; too broad.
- Patching individual output sites: fragile, no deduplication guarantee.

**Invariant**: `emit_sync_diagnostic()` is the only function allowed to write to stderr for final-sync failures. All other sync-related output stays on stdout (or in `--json` payloads).

### ADR: mark-status Resolution Strategy Stack (Blocker 2)

**Context**: `mark_status()` in `tasks.py` currently uses two search patterns (checkbox, pipe-table). Adding inline `Subtasks:` and WP ID resolution requires extending the strategy without breaking the existing patterns.

**Decision**: Introduce a resolution strategy stack executed in order:
1. Checkbox row (`- [ ] T001`) — existing, mutates file
2. Pipe-table row — existing, mutates file
3. Inline `Subtasks:` reference (`Subtasks: T001, T002`) — new, mutates file if a backing checkbox can be found; otherwise returns `already-satisfied` if the task is done per event log
4. WP ID (`WP02`) — new, delegates to `emit_status_transition()` from the status event log; returns `updated`, `already-satisfied`, or `not-found`

Each strategy returns a `TaskIdResult` (see data-model.md). The first strategy that resolves the ID wins. If no strategy resolves the ID, the result is `not-found`.

**Invariant**: The WP ID strategy never mutates task artifact files — it only interacts with the status event log. The checkbox/pipe-table strategies never touch the event log.

---

## Per-Blocker Implementation Design

### Blocker 1 — Sync Final-Sync Diagnostic Hygiene (#952)

**Root cause**: `sync/daemon.py` (lock timeout) and `sync/batch.py` (error categorization + format) emit error text directly to the console output stream, which can be stdout in `--json` mode and always includes red failure prefixes via Rich markup.

**Files to change**:

| File | Change |
|------|--------|
| `src/specify_cli/sync/diagnostics.py` | **NEW** — `SyncDiagnosticCode`, `emit_sync_diagnostic()`, `classify_sync_error()` |
| `src/specify_cli/sync/daemon.py` | Replace final-sync lock-error console output with `emit_sync_diagnostic(LOCK_UNAVAILABLE, ...)` |
| `src/specify_cli/sync/batch.py` | Replace final-sync error output with `emit_sync_diagnostic(classified_code, ...)` |
| `tests/sync/test_final_sync_diagnostics.py` | **NEW** — 6 regression test cases (see test plan below) |
| `tests/e2e/test_mission_create_clean_output.py` | **EXTEND** — assert JSON stdout is valid, stderr carries at most one diagnostic |

**Deduplication mechanism**: `emit_sync_diagnostic()` keeps a `threading.local` or module-level `set` of already-emitted codes within the process lifetime of the current command invocation. On process exit the set is reset. This is safe for the single-process CLI lifecycle.

**Test plan**:
1. `test_lock_held_during_successful_transition` — mock lock held; assert: exit 0, stdout valid JSON, stderr contains `sync.final_sync_lock_unavailable` exactly once
2. `test_auth_refresh_contention` — mock auth refresh in progress; assert: stderr contains `sync.auth_refresh_in_progress` exactly once
3. `test_websocket_offline` — mock WebSocket unavailable; assert: stderr `sync.websocket_offline` exactly once
4. `test_event_loop_unavailable` — mock RuntimeError on event loop; assert: stderr `sync.event_loop_unavailable` exactly once
5. `test_server_auth_failure` — mock 401 from server; assert: stderr `sync.server_auth_failure` exactly once
6. `test_deduplication` — trigger the same error twice in one invocation; assert: stderr diagnostic appears exactly once

---

### Blocker 2 — mark-status Non-Checkbox ID Resolution (#783)

**Root cause**: `mark_status()` in `tasks.py` only searches for checkbox-row and pipe-table patterns. `Subtasks:` inline references and bare WP IDs are not handled; the command returns "No task IDs found" instead of resolving them.

**Files to change**:

| File | Change |
|------|--------|
| `src/specify_cli/cli/commands/agent/tasks.py` | Add `_resolve_inline_subtasks()`, `_resolve_wp_id()`, `TaskIdResult` dataclass; update `mark_status()` to use strategy stack and return per-ID results |
| `tests/git_ops/test_mark_status_pipe_table.py` | **EXTEND** — add inline `Subtasks:` and bare WP ID test cases |
| `tests/specify_cli/cli/commands/agent/test_tasks_mark_status.py` | **NEW or EXTEND** — full per-ID result JSON schema tests |

**New types** (see data-model.md for full definitions):
- `TaskIdResolutionOutcome` enum: `updated`, `already_satisfied`, `not_found`
- `TaskIdResult` dataclass: `id`, `outcome`, `format`, `message`

**JSON output schema** (see `contracts/mark-status-result.schema.json`):
```json
{
  "results": [
    {"id": "T001", "outcome": "updated", "format": "inline_subtasks", "message": "..."},
    {"id": "WP02", "outcome": "already_satisfied", "format": "wp_id", "message": "..."}
  ],
  "summary": {"updated": 1, "already_satisfied": 1, "not_found": 0}
}
```

**Test plan**:
1. `test_inline_subtasks_single` — tasks.md has `Subtasks: T001`; assert: T001 resolved, outcome=updated, format=inline_subtasks
2. `test_inline_subtasks_multiple` — tasks.md has `Subtasks: T001, T002, T003`; all three resolved
3. `test_wp_id_mark_done` — `mark-status WP02 --status done --mission <slug>`; assert: event log updated, outcome=updated
4. `test_wp_id_already_done` — WP02 is already `done`; assert: outcome=already_satisfied
5. `test_unknown_id_not_found` — ID `T999` absent from all formats; assert: outcome=not_found, other IDs unaffected
6. `test_mixed_formats` — one checkbox, one inline, one WP ID in same invocation; assert: all three processed, partial results returned correctly
7. `test_existing_checkbox_unchanged` — existing checkbox T001 still works; assert: backwards compatible
8. `test_existing_pipe_table_unchanged` — existing pipe-table T001 still works; assert: backwards compatible

---

### Blocker 3 — Cross-Repo E2E uv-Managed Python (#975)

**Root cause**: `contract_drift_caught.py` uses `venv.create(venv_dir, with_pip=True, clear=True)` which calls `ensurepip` internally. uv-managed Python builds do not provide `libpython3.x.dylib` at the venv copy path, causing `ensurepip` to fail before any product behavior is reached.

**Files to change**:

| File | Change |
|------|--------|
| `spec-kitty-end-to-end-testing/support/nested_env.py` | **NEW** — `create_nested_env(venv_dir)` helper: detect uv, use `uv venv` if available, fall back to stdlib `venv`, skip/xfail if neither works |
| `spec-kitty-end-to-end-testing/scenarios/contract_drift_caught.py` | Replace `venv.create(...)` call with `create_nested_env(venv_dir)` from support module |
| `spec-kitty-end-to-end-testing/tests/test_nested_env_helper.py` | **NEW** — unit tests for the helper |

**Helper interface**:
```python
class NestedEnvResult:
    venv_dir: Path
    python: Path
    pip: Path
    method: str  # "uv_venv" | "stdlib_venv"

def create_nested_env(venv_dir: Path) -> NestedEnvResult:
    """
    Create a nested Python environment suitable for cross-repo E2E scenarios.
    Prefers uv venv when uv is available and the outer runner is uv-managed.
    Falls back to stdlib venv when safe.
    Raises pytest.skip.Exception with a precise reason when neither method works.
    """
```

**uv detection heuristic**: `shutil.which("uv") is not None` AND (`"uv" in sys.executable` OR `".uv" in sys.executable` OR `os.environ.get("UV_MANAGED_PYTHON")`). If uv is available, always prefer it for portability.

**Test plan**:
1. `test_prefers_uv_when_available` — mock `shutil.which("uv")` returning a path; assert: helper calls `uv venv`
2. `test_stdlib_fallback_when_uv_absent` — mock `shutil.which("uv")` returning None; assert: helper calls `venv.create()`
3. `test_skip_when_neither_works` — mock both failing; assert: `pytest.skip.Exception` raised with environment reason
4. `test_contract_drift_assertions_still_run` — integration: helper creates env successfully; scenario reaches and passes drift assertions

---

### Blocker 4 — merge --dry-run Missing Mission Branch (#976)

**Root cause**: The dry-run path in `merge.py` (lines 1447–1509) computes lane assignments and outputs a JSON preview but does not check whether `kitty/mission-<slug>` exists as a local branch. Real merge discovers the missing branch late (inside `merge_lane_to_mission()`), after which the dry-run/real-merge agreement invariant is violated.

**Files to change**:

| File | Change |
|------|--------|
| `src/specify_cli/cli/commands/merge.py` | Add `_check_mission_branch(mission_slug, repo_root)` function; call from dry-run path before JSON output; call from real merge path in `_run_lane_based_merge()` before first irreversible operation |
| `tests/merge/test_merge_preflight_mission_branch.py` | **NEW** — preflight regression tests |

**New function**:
```python
def _check_mission_branch(
    mission_slug: str,
    repo_root: Path,
) -> tuple[bool, dict[str, str] | None]:
    """
    Returns (exists, None) if the mission branch exists.
    Returns (False, blocker_payload) if the branch is missing.
    blocker_payload keys: ready, blocker, expected_branch, remediation.
    """
```

**Dry-run output when missing branch detected**:
```json
{
  "ready": false,
  "blocker": "missing_mission_branch",
  "expected_branch": "kitty/mission-stable-320-release-blocker-cleanup-01KQW4DF",
  "remediation": "git branch kitty/mission-stable-320-release-blocker-cleanup-01KQW4DF <base-commit>"
}
```

**Existing preflight order after change**:
1. `_enforce_git_preflight()` — clean working tree
2. `_enforce_target_branch_sync_preflight()` — target not behind origin
3. **`_check_mission_branch()`** — mission branch exists ← new, added here
4. `_enforce_review_artifact_consistency()` — no rejected reviews
5. Conflict forecasting (dry-run) / lane merge execution (real merge)

**Test plan**:
1. `test_dry_run_json_missing_branch` — fresh repo, no mission branch; assert: `ready=false`, `blocker=missing_mission_branch`, `expected_branch` correct, `remediation` present
2. `test_dry_run_human_missing_branch` — same, no `--json`; assert: human output names missing branch and remediation
3. `test_real_merge_blocked_missing_branch` — same setup for real merge; assert: merge blocked before any irreversible git operation
4. `test_dry_run_ready_with_branch_present` — happy path: branch exists; assert: existing preflight behavior unaffected
5. `test_missing_branch_does_not_mask_other_blockers` — both missing branch AND dirty worktree; assert: both blockers reported (or at minimum, missing branch does not silently suppress dirty-worktree blocker)

---

## Project / Source Structure

### spec-kitty (primary repo)

```
src/specify_cli/
├── sync/
│   ├── __init__.py                   # existing — lazy import registry
│   ├── diagnostics.py                # NEW — SyncDiagnosticCode, emit_sync_diagnostic(), classify_sync_error()
│   ├── daemon.py                     # MODIFIED — replace final-sync error output with emit_sync_diagnostic()
│   └── batch.py                      # MODIFIED — replace final-sync error output with emit_sync_diagnostic()
├── cli/commands/agent/
│   └── tasks.py                      # MODIFIED — add inline/WP resolution, TaskIdResult, per-ID JSON output
└── cli/commands/
    └── merge.py                      # MODIFIED — add _check_mission_branch(), call from dry-run + real merge

tests/
├── sync/
│   └── test_final_sync_diagnostics.py    # NEW — 6 regression test cases
├── e2e/
│   └── test_mission_create_clean_output.py  # EXTEND — JSON stdout + stderr diagnostic assertion
├── git_ops/
│   └── test_mark_status_pipe_table.py    # EXTEND — inline Subtasks + WP ID cases
└── merge/
    └── test_merge_preflight_mission_branch.py  # NEW — 5 regression test cases
```

### spec-kitty-end-to-end-testing

```
support/
└── nested_env.py                         # NEW — create_nested_env() uv-aware helper

scenarios/
└── contract_drift_caught.py              # MODIFIED — replace venv.create() with create_nested_env()

tests/
└── test_nested_env_helper.py             # NEW — 4 unit tests for helper
```

### Documentation (this mission)

```
kitty-specs/stable-320-release-blocker-cleanup-01KQW4DF/
├── plan.md              # This file
├── research.md          # Phase 0 research findings
├── data-model.md        # Key new data structures
├── contracts/           # CLI output JSON schemas
│   ├── merge-dry-run-blocker.schema.json
│   └── mark-status-result.schema.json
└── decisions/
    └── DM-01KQW556RAG1N0QF7PVSTP08P7.md  # missing-branch-behavior decision
```

---

## Implementation Order (suggested for tasks)

The four blockers are independent and can be parallelized across lanes:

| Blocker | Repo | Risk | Suggested Lane |
|---------|------|------|----------------|
| #952 — Sync diagnostics | spec-kitty | Medium (touches sync internals) | Lane A |
| #783 — mark-status | spec-kitty | Low (additive change) | Lane B |
| #975 — E2E venv | spec-kitty-end-to-end-testing | Low (additive helper) | Lane B or C |
| #976 — merge dry-run | spec-kitty | Medium (touches merge preflight) | Lane A or C |

All four can be developed in parallel. Integration smoke runs require `SPEC_KITTY_ENABLE_SAAS_SYNC=1`.

---

## Risk Assessment (Premortem)

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Sync deduplication accidentally suppresses a fatal sync error | Low | High | `emit_sync_diagnostic()` only deduplicates by code; a new code always emits; fatal errors are handled separately |
| mark-status WP ID delegation emits an invalid transition | Medium | Medium | Strategy validates transition via `validate_transition()` before calling `emit_status_transition()`; invalid transitions return `not-found` with reason |
| uv detection heuristic false-positive on non-uv runners | Low | Low | Fallback to stdlib venv is always attempted; xfail only when both fail |
| `_check_mission_branch()` check added to real merge breaks existing happy path | Low | High | Regression test 4 (`test_dry_run_ready_with_branch_present`) and pre-existing merge tests provide coverage |
| mypy --strict failures in new diagnostic module | Medium | Low | Type annotations required from the start; mypy run before commit |
