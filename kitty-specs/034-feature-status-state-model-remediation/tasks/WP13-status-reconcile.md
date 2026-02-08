---
work_package_id: WP13
title: Status Reconcile
lane: planned
dependencies:
- WP03
subtasks:
- T064
- T065
- T066
- T067
- T068
- T069
phase: Phase 3 - Operational
assignee: ''
agent: ''
shell_pid: ''
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-02-08T14:07:18Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP13 -- Status Reconcile

## IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.
- **You must address all feedback** before your work is complete.
- **Mark as acknowledged**: When you understand the feedback and begin addressing it, update `review_status: acknowledged` in the frontmatter.

---

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Implementation Command

```bash
spec-kitty implement WP13 --base WP07
```

After workspace creation, merge the WP03 branch:

```bash
cd .worktrees/034-feature-status-state-model-remediation-WP13/
git merge 034-feature-status-state-model-remediation-WP03
```

This WP depends on WP03 (deterministic reducer) for snapshot inspection and on WP07 (emit orchestration) for the apply-mode pipeline.

---

## Objectives & Success Criteria

Create cross-repo drift detection and reconciliation event generation. This WP delivers:

1. `ReconcileResult` dataclass with suggested events, drift detection flag, and detail messages
2. `reconcile()` function that scans target repositories for WP-linked evidence and compares against canonical snapshot state
3. `scan_for_wp_commits()` to detect WP-linked branches and commit messages in target repositories
4. Reconciliation event generation that proposes `StatusEvent` objects to align planning with implementation reality
5. Dry-run mode returning a human-readable report without persisting anything
6. Apply mode emitting reconciliation events through the orchestration pipeline (2.x only; 0.1x dry-run only)
7. CLI `status reconcile` command with `--feature`, `--dry-run`, `--apply`, `--target-repo`, `--json` flags

**Success**: Given a feature with WPs in `in_progress` but whose branches are merged in a target repo, `reconcile --dry-run` proposes advancement events. `reconcile --apply` emits those events through the canonical pipeline. On 0.1x, `--apply` is rejected with a clear error.

---

## Context & Constraints

- **Spec**: `kitty-specs/034-feature-status-state-model-remediation/spec.md` -- User Story 7 (Cross-Repo Reconciliation), FR-016 through FR-018
- **Plan**: `kitty-specs/034-feature-status-state-model-remediation/plan.md` -- AD-6 (Unified Fan-Out), Phase 3 scope, Backport Strategy point 6
- **Data Model**: `kitty-specs/034-feature-status-state-model-remediation/data-model.md` -- StatusEvent entity (reconciliation events use `actor: "reconcile"`, `execution_mode: "direct_repo"`)
- **Contracts**: `kitty-specs/034-feature-status-state-model-remediation/contracts/event-schema.json` -- event schema that reconciliation events must conform to
- **Dependency WP03**: Provides `reduce()` and `materialize()` for computing current snapshot state from the event log
- **Dependency WP07**: Provides the `status.emit` orchestration pipeline that apply mode routes through

**Key constraints**:
- Python 3.11+
- `subprocess.run` for git operations in target repos (not gitpython -- direct CLI)
- No network dependencies -- reconciliation scans local filesystem git repos only
- Reconciliation events must pass the same validation as any other `StatusEvent`
- `actor` field on reconciliation events must be `"reconcile"` (distinct from human or agent actors)
- On the 0.1x branch line, `--apply` is permanently disabled; only `--dry-run` operates
- Phase gating: use `resolve_phase()` from `status/phase.py` to determine if apply is allowed
- No fallback mechanisms -- fail intentionally if target repo is inaccessible or malformed

---

## Subtasks & Detailed Guidance

### Subtask T064 -- Create `src/specify_cli/status/reconcile.py`

**Purpose**: Core reconciliation framework with result dataclass and main entry point.

**Steps**:
1. Create the file with these imports:
   ```python
   from __future__ import annotations
   import subprocess
   from dataclasses import dataclass, field
   from pathlib import Path
   from typing import Any

   from specify_cli.status.models import Lane, StatusEvent, StatusSnapshot
   from specify_cli.status.reducer import reduce
   from specify_cli.status.store import read_events
   from specify_cli.status.phase import resolve_phase
   ```

2. Define `CommitInfo` dataclass:
   ```python
   @dataclass(frozen=True)
   class CommitInfo:
       sha: str          # 7-40 hex chars
       branch: str       # Branch where found
       message: str      # Commit message (first line)
       author: str       # Author name
       date: str         # ISO 8601 UTC timestamp
   ```

3. Define `ReconcileResult` dataclass:
   ```python
   @dataclass
   class ReconcileResult:
       suggested_events: list[StatusEvent] = field(default_factory=list)
       drift_detected: bool = False
       details: list[str] = field(default_factory=list)
       errors: list[str] = field(default_factory=list)
       target_repos_scanned: int = 0
       wps_analyzed: int = 0
   ```

4. Implement `reconcile()` function:
   ```python
   def reconcile(
       feature_dir: Path,
       repo_root: Path,
       target_repos: list[Path],
       *,
       dry_run: bool = True,
   ) -> ReconcileResult:
       """Scan target repos for WP-linked commits and generate reconciliation events."""
   ```
   - Read the current snapshot from `status.json` or materialize from event log
   - Extract `feature_slug` from the feature directory name
   - For each target repo, call `scan_for_wp_commits()`
   - Compare discovered commit evidence with current snapshot lanes
   - Generate reconciliation events for detected drift
   - If `dry_run=False`, emit events through orchestration pipeline
   - If `dry_run=True`, return suggested events without persisting

**Files**: `src/specify_cli/status/reconcile.py` (new file)

**Validation**:
- `reconcile()` returns a `ReconcileResult` with populated `suggested_events` when drift is detected
- `reconcile()` returns `drift_detected=False` when planning matches implementation
- `reconcile()` with invalid target repo path populates `errors` list

**Edge Cases**:
- Target repo does not exist: add to `errors`, continue scanning other repos
- Target repo has no matching branches or commits: no drift for that repo
- Feature slug contains hyphens that could match unrelated branches: use precise regex `*{feature_slug}-WP\d{2}*`
- Multiple target repos with overlapping evidence: deduplicate by WP ID, use most recent commit
- Empty event log (no snapshot): all WPs are effectively `planned`, any commits suggest drift

---

### Subtask T065 -- WP-to-Commit Linkage Detection

**Purpose**: Scan a target repository for branches and commits linked to specific work packages.

**Steps**:
1. Implement `scan_for_wp_commits()`:
   ```python
   def scan_for_wp_commits(
       repo_path: Path,
       feature_slug: str,
   ) -> dict[str, list[CommitInfo]]:
       """Scan repo for WP-linked branches and commit messages.

       Returns mapping of WP ID -> list of CommitInfo found.
       """
   ```

2. Branch detection -- find branches matching `*{feature_slug}-WP##*`:
   ```python
   result = subprocess.run(
       ["git", "branch", "-a", "--list", f"*{feature_slug}*"],
       cwd=repo_path,
       capture_output=True,
       text=True,
       timeout=30,
   )
   ```
   Parse branch names, extract WP IDs using regex `WP(\d{2})`.

3. Commit message scanning -- search for commits mentioning WP IDs:
   ```python
   result = subprocess.run(
       ["git", "log", "--all", "--oneline", f"--grep=WP{wp_num}"],
       cwd=repo_path,
       capture_output=True,
       text=True,
       timeout=60,
   )
   ```
   Parse each line to extract SHA, message. Get full metadata with `git log --format`.

4. Merge detection -- check if WP branches are merged into main:
   ```python
   result = subprocess.run(
       ["git", "branch", "--merged", "main", "--list", f"*{feature_slug}-WP{wp_num}*"],
       cwd=repo_path,
       capture_output=True,
       text=True,
       timeout=30,
   )
   ```

5. Return a dict mapping each discovered WP ID to its list of `CommitInfo` objects.

**Files**: `src/specify_cli/status/reconcile.py` (same file, additional function)

**Validation**:
- Given a repo with branch `034-feature-status-WP01`, returns `{"WP01": [CommitInfo(...)]}`
- Given a repo with commit message "Implement WP03 status models", returns `{"WP03": [...]}`
- Given a repo with no matching content, returns empty dict

**Edge Cases**:
- `subprocess.run` times out: catch `subprocess.TimeoutExpired`, add to errors, return partial results
- Branch name contains multiple WP references (e.g., `034-feature-WP01-WP02`): attribute to both WP01 and WP02
- Remote-only branches (e.g., `remotes/origin/...`): include them, strip the `remotes/origin/` prefix for display
- Repo has shallow clone (limited history): `git log --grep` may miss older commits; document this limitation

---

### Subtask T066 -- Reconciliation Event Generation

**Purpose**: Compare current snapshot lane state with discovered commit evidence and generate StatusEvents to align them.

**Steps**:
1. Implement `_generate_reconciliation_events()`:
   ```python
   def _generate_reconciliation_events(
       feature_slug: str,
       snapshot: StatusSnapshot,
       commit_map: dict[str, list[CommitInfo]],
       merged_wps: set[str],
   ) -> list[StatusEvent]:
       """Generate events to reconcile planning state with implementation evidence."""
   ```

2. For each WP found in `commit_map`:
   - Get current lane from snapshot (default `"planned"` if WP not in snapshot)
   - If WP has commits but is still `planned`: suggest `planned -> claimed -> in_progress`
   - If WP is `in_progress` but branch is merged to main: suggest `in_progress -> for_review`
   - If WP is `for_review` and merged to main with evidence: suggest `for_review -> done` (evidence auto-generated from commit metadata)
   - Each suggested event uses: `actor="reconcile"`, `execution_mode="direct_repo"`, `force=False`

3. Generate intermediate events when multiple lane transitions are needed (the state machine does not allow skipping lanes without force):
   ```python
   import ulid

   event = StatusEvent(
       event_id=str(ulid.new()),
       feature_slug=feature_slug,
       wp_id=wp_id,
       from_lane=current_lane,
       to_lane=suggested_lane,
       at=datetime.now(timezone.utc).isoformat(),
       actor="reconcile",
       force=False,
       execution_mode="direct_repo",
   )
   ```

4. Validate each generated event against the transition matrix before including it.

**Files**: `src/specify_cli/status/reconcile.py` (same file)

**Validation**:
- WP in `planned` with commits produces transition to `claimed`
- WP in `in_progress` with merged branch produces transition to `for_review`
- WP already at correct lane produces no events
- Generated events pass `validate_transition()` checks

**Edge Cases**:
- WP in `done` or `canceled` (terminal): no reconciliation events generated, even if new commits exist
- WP in `blocked`: no automatic advancement; add a detail message noting the block
- Multi-step advancement (planned -> done): generate chain of legal transitions, not a single illegal skip
- Commit evidence is ambiguous (WP ID in commit message but not in branch name): generate detail message, still suggest event

---

### Subtask T067 -- Dry-Run Mode

**Purpose**: Return suggested events and drift report without persisting anything, formatted as a human-readable table.

**Steps**:
1. Implement `format_reconcile_report()`:
   ```python
   from rich.console import Console
   from rich.table import Table

   def format_reconcile_report(result: ReconcileResult) -> None:
       """Print a human-readable reconciliation report using Rich."""
       console = Console()
   ```

2. Build a Rich table with columns:
   - WP ID
   - Current Lane
   - Suggested Lane
   - Evidence (branch/commit summary)
   - Action (what would happen on `--apply`)

3. Print summary statistics:
   - Target repos scanned
   - WPs analyzed
   - Drift detected (yes/no)
   - Suggested events count

4. If `--json` flag is set, output structured JSON instead:
   ```python
   def reconcile_result_to_json(result: ReconcileResult) -> dict[str, Any]:
       return {
           "drift_detected": result.drift_detected,
           "suggested_events": [e.to_dict() for e in result.suggested_events],
           "details": result.details,
           "errors": result.errors,
           "stats": {
               "target_repos_scanned": result.target_repos_scanned,
               "wps_analyzed": result.wps_analyzed,
           },
       }
   ```

**Files**: `src/specify_cli/status/reconcile.py` (same file)

**Validation**:
- Dry-run produces Rich table output with correct columns
- JSON output is valid JSON matching the ReconcileResult structure
- No files are modified during dry-run (no JSONL append, no status.json write)

**Edge Cases**:
- Empty ReconcileResult (no drift): print "No drift detected" message
- Many suggested events (>20 WPs): table should remain readable; consider pagination hint
- Errors during scanning: display errors section separately from suggestions

---

### Subtask T068 -- Apply Mode

**Purpose**: Emit each reconciliation event through the orchestration pipeline with phase gating.

**Steps**:
1. Implement apply logic in the `reconcile()` function:
   ```python
   if not dry_run:
       phase, source = resolve_phase(repo_root, feature_slug)
       # On 0.1x (or when phase < 3), apply is disabled
       if phase < 1:
           raise ValueError(
               "Cannot apply reconciliation events at Phase 0. "
               "Upgrade to Phase 1+ to enable event persistence."
           )

       from specify_cli.status import emit_status_transition

       for event in result.suggested_events:
           emit_status_transition(
               feature_dir=feature_dir,
               repo_root=repo_root,
               wp_id=event.wp_id,
               to_lane=str(event.to_lane),
               actor="reconcile",
               force=False,
               execution_mode="direct_repo",
           )
   ```

2. Phase gating for 0.1x:
   - Import `resolve_phase()` from `status/phase.py`
   - On 0.1x, the phase cap ensures reconcile --apply is rejected
   - Add explicit check: if branch is 0.1x-derived and `--apply` requested, raise error with message directing user to use `--dry-run`

3. After applying all events, re-materialize the snapshot and return the updated result.

**Files**: `src/specify_cli/status/reconcile.py` (same file)

**Validation**:
- Apply mode on 2.x: events are appended to JSONL, snapshot is updated
- Apply mode on 0.1x: raises error with clear message
- Each applied event passes validation (no illegal transitions emitted)
- Partial failure: if event N fails, events 1..N-1 are still persisted (append-only log)

**Edge Cases**:
- Apply mode with zero suggested events: no-op, return result with details message
- Apply mode with event that fails validation: skip that event, add to errors, continue with remaining
- Phase resolution failure (no config found): default to Phase 1 behavior (allow apply with warning)

---

### Subtask T069 -- CLI `status reconcile` Command

**Purpose**: Create the CLI entry point for reconciliation.

**Steps**:
1. Add the reconcile command to `src/specify_cli/cli/commands/agent/status.py`:
   ```python
   @app.command()
   def reconcile(
       feature: str = typer.Option(None, "--feature", "-f", help="Feature slug"),
       dry_run: bool = typer.Option(True, "--dry-run/--apply", help="Preview vs persist"),
       target_repo: list[Path] = typer.Option([], "--target-repo", "-t", help="Target repo path(s)"),
       json_output: bool = typer.Option(False, "--json", help="JSON output"),
   ):
       """Detect planning-vs-implementation drift and suggest reconciliation events."""
   ```

2. Feature detection: if `--feature` not provided, use `detect_feature_slug()` from current directory context.

3. Target repo resolution: if no `--target-repo` provided, default to the current repo root (self-reconcile).

4. Call `reconcile()` from `status/reconcile.py` with parsed arguments.

5. Output formatting:
   - Default: Rich table via `format_reconcile_report()`
   - `--json`: structured JSON via `reconcile_result_to_json()`

6. Exit code:
   - 0: no drift detected (or dry-run completed successfully)
   - 1: drift detected and `--apply` not used
   - 2: errors during scanning

**Files**: `src/specify_cli/cli/commands/agent/status.py` (modified)

**Validation**:
- `spec-kitty agent status reconcile --dry-run --feature 034-feature-status-state-model-remediation` runs without error
- `--json` flag produces valid JSON output
- `--apply` on 0.1x branch produces clear error message
- `--target-repo /path/to/repo` scans the specified repo

**Edge Cases**:
- No feature detected and no `--feature` flag: print error "Could not detect feature. Use --feature flag."
- Target repo path does not exist: print error per repo, continue with remaining repos
- Multiple `--target-repo` flags: scan all repos, aggregate results

---

### Tests for WP13

Create `tests/specify_cli/status/test_reconcile.py`:

1. **test_scan_for_wp_commits_finds_branches** -- mock `subprocess.run` to return branch list containing WP references, verify parsed output
2. **test_scan_for_wp_commits_finds_commit_messages** -- mock git log output with WP IDs in messages
3. **test_scan_for_wp_commits_empty_repo** -- no matching branches or commits, returns empty dict
4. **test_scan_for_wp_commits_timeout** -- mock `subprocess.TimeoutExpired`, verify error handling
5. **test_reconcile_detects_drift** -- mock scan results showing WP in `planned` with commits, verify `drift_detected=True`
6. **test_reconcile_no_drift** -- WP lanes match commit evidence, verify `drift_detected=False`
7. **test_reconcile_dry_run_no_persistence** -- verify no file writes during dry-run
8. **test_reconcile_apply_emits_events** -- mock emit pipeline, verify events are emitted
9. **test_reconcile_apply_rejected_on_01x** -- mock phase resolution returning 0.1x cap, verify error
10. **test_generate_reconciliation_events_terminal_wp** -- WP in `done` produces no events
11. **test_generate_reconciliation_events_blocked_wp** -- WP in `blocked` produces detail message, no events
12. **test_commit_info_dataclass** -- verify CommitInfo creation and field access
13. **test_reconcile_result_json_serialization** -- verify `reconcile_result_to_json()` output structure

---

## Test Strategy

**Required per user requirements**: Integration tests for reconciliation (part of the comprehensive test suite in WP15).

- **Coverage target**: 90%+ of `reconcile.py`
- **Test runner**: `python -m pytest tests/specify_cli/status/test_reconcile.py -v`
- **Mocking strategy**: Mock `subprocess.run` for all git operations (no real git repos in unit tests)
- **Integration tests**: Create real temporary git repos with test branches and commits in WP15
- **Parametrized tests**: Use `@pytest.mark.parametrize` for different WP lane states
- **Fixtures**: Create a `conftest.py` factory for `CommitInfo`, `ReconcileResult`

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| `subprocess.run` git commands differ across platforms | Reconcile fails on Windows | Use `--format` flags for deterministic git output; test on CI with multiple OS |
| False positive WP detection in commit messages | Incorrect reconciliation suggestions | Require WP IDs to match pattern `WP\d{2}` with word boundaries in regex |
| Target repo is very large (slow scanning) | CLI hangs | Set timeout on subprocess calls (30s per command); scan only recent branches |
| Reconciliation events bypass human review | Unintended state changes | Default to `--dry-run`; `--apply` requires explicit flag; no `--force` on reconciliation events |
| Phase gating bypass on misconfigured repo | Apply on 0.1x when it should be blocked | Double-check: both phase cap and explicit branch detection |
| Shallow clones missing history | Incomplete commit scanning | Document limitation; suggest `git fetch --unshallow` in error message |

---

## Review Guidance

- **Check ReconcileResult fields**: All fields from spec present, `suggested_events` contains valid `StatusEvent` objects
- **Check CommitInfo dataclass**: Matches the fields needed for evidence generation
- **Check scan_for_wp_commits**: Uses `subprocess.run` with timeouts, captures errors, parses output correctly
- **Check reconciliation event generation**: Events have `actor="reconcile"`, `execution_mode="direct_repo"`, pass transition validation
- **Check dry-run isolation**: No file writes, no event persistence, no snapshot modification
- **Check apply mode gating**: Phase check prevents apply on 0.1x; clear error message
- **Check CLI flags**: `--dry-run` is default, `--apply` is opt-in, `--target-repo` is repeatable, `--json` works
- **Check Rich output**: Table columns match spec, summary statistics present
- **No fallback mechanisms**: Invalid target repos fail with errors, not silent skips

---

## Activity Log

- 2026-02-08T14:07:18Z -- system -- lane=planned -- Prompt created.
