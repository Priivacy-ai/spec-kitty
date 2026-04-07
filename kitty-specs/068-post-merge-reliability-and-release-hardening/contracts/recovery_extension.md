# Contract: WP05 Recovery Extension + Verification + Mission Close Ledger

**Owns**: FR-016, FR-017, FR-018, FR-021

## scan_recovery_state extension (FR-021)

**File**: `src/specify_cli/lanes/recovery.py` (existing function, lines 174-267)

### Current behavior

`scan_recovery_state(repo_root, mission_slug)` iterates branches matching `kitty/mission-{slug}*` returned by `_list_mission_branches`. If no live branches exist (because they were merged-and-deleted), the function returns "nothing to recover" — leaving the user with an unblockable workflow.

### New behavior (FR-021)

```python
from pathlib import Path
from specify_cli.lanes.recovery import scan_recovery_state, RecoveryState
from specify_cli.status.reducer import materialize

def scan_recovery_state(
    repo_root: Path,
    mission_slug: str,
    *,
    consult_status_events: bool = True,   # NEW parameter, defaults True
) -> RecoveryState:
    """Scan for in-progress lane workspaces and orphan claims.

    When consult_status_events=True (default after FR-021), the function:
      1. Reads kitty-specs/<mission>/status.events.jsonl
      2. Materializes the lane snapshot for every WP
      3. For WPs whose lane is `done` and whose branches are absent, marks
         them as `merged_and_deleted` rather than `missing`
      4. For downstream WPs whose dependencies are all `done`, returns
         "ready to start from target branch tip"

    Backwards compatibility: callers that pass `consult_status_events=False`
    get the legacy live-branch-only behavior, which still exists for any
    in-progress mission where branches haven't been deleted yet.
    """
```

### New `RecoveryState` field

`RecoveryState` (existing dataclass in `recovery.py`) gains a new field:

```python
@dataclass(frozen=True)
class RecoveryState:
    # ... existing fields ...
    ready_to_start_from_target: list[str] = field(default_factory=list)
    """List of WP IDs whose dependencies are all `done` and whose lane
    branches are merged-and-deleted. These WPs can be started fresh from
    the target branch tip via `spec-kitty implement WP## --base main`."""
```

## --base flag for `spec-kitty implement` (FR-021)

**File**: `src/specify_cli/cli/commands/implement.py`

```python
import typer
from typing import Optional

@app.command()
def implement(
    wp_id: str,
    base: Optional[str] = typer.Option(
        None,
        "--base",
        help="Explicit base ref for the lane workspace (default: auto-detect)",
    ),
) -> None:
    """Implement a work package, optionally from an explicit base branch."""

    if base is not None:
        # Validate the ref exists locally
        validated_base = _resolve_git_ref(base, repo_root)
        # Create the lane workspace from the explicit base
        workspace = create_lane_workspace_from_base(wp_id, validated_base, repo_root)
    else:
        # Existing auto-detect path (unchanged)
        workspace = create_lane_workspace(wp_id, repo_root)

    # ... rest of implement logic unchanged ...
```

**Validation**:
- `--base` accepts any local git ref (branch name, tag, commit SHA, `HEAD`).
- If the ref does not resolve, the command fails with a clear error pointing at `git fetch` and `git branch -a`.
- When omitted, the existing auto-detect logic runs unchanged.

## Verification report (FR-016)

**File**: `kitty-specs/068-post-merge-reliability-and-release-hardening/wp05-verification-report.md`

```markdown
# WP05 Recovery Verification Report

**Authored**: <date>
**Validated against**: commit `<sha>`

## Coverage

This report accounts for every documented failure shape from issues #415 and #416, including the two pre-identified gaps from the Mission 067 Failure-Mode Evidence sections.

## Pre-identified gap 1 (#416 status-events loss)

**Failure shape**: `_run_lane_based_merge` writes `done` events to disk but never commits them. External merge rebuild discards them.

**Status**: `fixed_by_this_mission`

**Evidence**:
- Fix landed in WP02 via FR-019 (`safe_commit` call between mark-done loop and worktree-removal)
- Regression test: `tests/cli/commands/test_merge_status_commit.py::test_done_events_committed_to_git` (FR-020)
- Verified by reading `git show HEAD:kitty-specs/<mission>/status.events.jsonl` after a synthetic merge

## Pre-identified gap 2 (#415 post-merge recovery deadlock)

**Failure shape**: `scan_recovery_state` ignores merged-and-deleted dependency branches; `implement` does not accept `--base main`.

**Status**: `fixed_by_this_mission`

**Evidence**:
- `scan_recovery_state` extended (FR-021)
- `--base` flag added to `implement` (FR-021)
- Regression tests: `tests/lanes/test_recovery_post_merge.py`, `tests/cli/commands/test_implement_base_flag.py`
- Verified by reproducing the WP07-after-deps-merged scenario from #415 and observing it now succeeds

## Other failure shapes from #415/#416

| Shape | Source | Status | Evidence |
|---|---|---|---|
| (additional shapes added during verification, if any) | | | |
```

## Mission close ledger (FR-018, C-005)

**File**: `kitty-specs/068-post-merge-reliability-and-release-hardening/mission-close-ledger.md`

```markdown
# Mission 068 Close Ledger

**Authored at mission close**: <date>
**Validated DoD**: every issue from the Tracked GitHub Issues table appears below.

## Primary scope (must implement)

| Issue | Decision | Reference | Notes |
|---|---|---|---|
| Priivacy-ai/spec-kitty#454 | closed_with_evidence | <PR/commit link> | WP01 stale-assertion analyzer shipped |
| Priivacy-ai/spec-kitty#456 | closed_with_evidence | <PR/commit link> | WP02 strategy wiring + squash default + push-error parser |
| Priivacy-ai/spec-kitty#455 | closed_with_evidence | <PR/commit link or wp03-validation-report.md> | WP03 validation: <close_with_evidence | tighten_workflow> |
| Priivacy-ai/spec-kitty#457 | closed_with_evidence | <PR/commit link> | WP04 release-prep CLI; FR-023 scope-cut documented |

## Verification-and-close scope

| Issue | Decision | Reference | Notes |
|---|---|---|---|
| Priivacy-ai/spec-kitty#415 | closed_with_evidence | <PR/commit link> | FR-021 fix landed (scan_recovery_state + --base) |
| Priivacy-ai/spec-kitty#416 | closed_with_evidence | <PR/commit link> | FR-019/FR-020 fix landed in WP02; verified by WP05 |

## Carve-outs filed as follow-ups

| Original concern | Follow-up issue | Notes |
|---|---|---|
| FSEvents debounce / `_worktree_removal_delay()` empirical timing | <new issue link> | Carved out per spec Assumptions section |
| Dirty classifier `git check-ignore` consultation | <new issue link> | Filed per spec Out-of-Scope; `--force` workaround documented |
```

## Test surface

| Test | FR | Asserts |
|---|---|---|
| `test_scan_recovery_state_finds_merged_deleted_deps` | FR-021 | a synthetic mission with WP01–WP05 done-and-deleted lets WP06 be marked ready |
| `test_implement_base_flag_creates_workspace_from_ref` | FR-021 | `spec-kitty implement WP06 --base main` creates a worktree at the main branch tip |
| `test_implement_base_flag_invalid_ref_fails_clearly` | FR-021 | `--base bogus-ref` fails with a clear error pointing at remediation |
| `test_post_merge_unblocking_scenario_end_to_end` | FR-021, Scenario 7 | full Scenario 7: WP01–WP05 merged, WP06 starts cleanly without manual state edits |
| `test_verification_report_authored_at_mission_close` | FR-016 | `wp05-verification-report.md` exists with all required sections |
| `test_mission_close_ledger_complete` | FR-018, DoD-4 | every issue in the Tracked GitHub Issues table has exactly one ledger row |

## NFR coverage

- NFR-005: all FR-021 tests run without network access (uses local synthetic git repos via fixture)
- NFR-006: `mypy --strict` passes on the new function signatures and dataclass field
