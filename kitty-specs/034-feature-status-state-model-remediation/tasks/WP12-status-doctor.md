---
work_package_id: "WP12"
title: "Status Doctor"
phase: "Phase 3 - Operational"
lane: "planned"
dependencies: ["WP03"]
subtasks:
  - "T059"
  - "T060"
  - "T061"
  - "T062"
  - "T063"
assignee: ""
agent: ""
shell_pid: ""
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2026-02-08T14:07:18Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP12 -- Status Doctor

## Review Feedback Status

> **IMPORTANT**: Before starting implementation, check the `review_status` field in this file's frontmatter.
> - If `review_status` is empty or `""`, proceed with implementation as described below.
> - If `review_status` is `"has_feedback"`, read the **Review Feedback** section below FIRST and address all feedback items before continuing.
> - If `review_status` is `"approved"`, this WP has been accepted -- no further implementation needed.

## Review Feedback

*(No feedback yet -- this section will be populated if the WP is returned from review.)*

## Objectives & Success Criteria

**Primary Objective**: Create a health check framework (`status doctor`) that detects operational hygiene issues: stale claims, orphan workspaces/worktrees, and unresolved materialization or derived-view drift. The doctor reports problems and recommends actions but does NOT automatically fix anything.

**Success Criteria**:
1. Stale claims (WPs in `claimed` or `in_progress` beyond a configurable threshold) are detected and reported.
2. Orphan workspaces (worktrees for features where all WPs are `done` or `canceled`) are detected.
3. Materialization drift and derived-view drift are detected (by delegating to the validation engine).
4. Each finding includes a recommended action.
5. CLI command `spec-kitty agent status doctor` produces a Rich-formatted report.
6. `--json` flag produces machine-readable output.

## Context & Constraints

**Architecture References**:
- `spec.md` User Story 8 defines the doctor scenarios and acceptance criteria.
- `plan.md` project structure places `status/doctor.py` in the status package.
- The doctor delegates drift detection to the validation engine from WP11. However, since WP12 and WP11 have different dependencies (WP12 depends only on WP03, WP11 depends on WP03 + WP06), the doctor should be designed to work even if the validation engine is not yet available. Use a try/except import for the validation functions.

**Dependency Artifacts Available**:
- WP03 provides `status/reducer.py` with `reduce()` for reading materialized state.
- WP03 provides `status/store.py` with `read_events()` for reading the event log.

**Constraints**:
- Doctor is a READ-ONLY operation. It never modifies files.
- Threshold values should be configurable via function parameters with sensible defaults.
- Worktree scanning should be limited to the feature being checked (not a full repo scan).
- The doctor should work even for features that have not been migrated to the event log yet -- it can inspect frontmatter directly as a fallback for staleness checks.

**Implementation Command**: `spec-kitty implement WP12 --base WP03`

## Subtasks & Detailed Guidance

### T059: Create Doctor Framework

**Purpose**: Build the foundational data model and framework for the doctor.

**Steps**:
1. Create `src/specify_cli/status/doctor.py`.
2. Define the data models:
   ```python
   from __future__ import annotations

   from dataclasses import dataclass, field
   from enum import StrEnum
   from pathlib import Path


   class Severity(StrEnum):
       WARNING = "warning"
       ERROR = "error"


   class Category(StrEnum):
       STALE_CLAIM = "stale_claim"
       ORPHAN_WORKSPACE = "orphan_workspace"
       MATERIALIZATION_DRIFT = "materialization_drift"
       DERIVED_VIEW_DRIFT = "derived_view_drift"


   @dataclass
   class Finding:
       """A single health check finding."""
       severity: Severity
       category: Category
       wp_id: str | None
       message: str
       recommended_action: str


   @dataclass
   class DoctorResult:
       """Aggregate result of all health checks."""
       feature_slug: str
       findings: list[Finding] = field(default_factory=list)

       @property
       def has_errors(self) -> bool:
           return any(f.severity == Severity.ERROR for f in self.findings)

       @property
       def has_warnings(self) -> bool:
           return any(f.severity == Severity.WARNING for f in self.findings)

       @property
       def is_healthy(self) -> bool:
           return len(self.findings) == 0

       def findings_by_category(self, category: Category) -> list[Finding]:
           return [f for f in self.findings if f.category == category]
   ```
3. Define the main entry point:
   ```python
   def run_doctor(
       feature_dir: Path,
       feature_slug: str,
       repo_root: Path,
       *,
       stale_claimed_days: int = 7,
       stale_in_progress_days: int = 14,
   ) -> DoctorResult:
       """Run all health checks for a feature."""
       result = DoctorResult(feature_slug=feature_slug)

       # Load snapshot (from status.json or reduce from events)
       snapshot = _load_or_reduce_snapshot(feature_dir, feature_slug)

       if snapshot:
           result.findings.extend(
               check_stale_claims(
                   feature_dir, snapshot,
                   claimed_threshold_days=stale_claimed_days,
                   in_progress_threshold_days=stale_in_progress_days,
               )
           )
           result.findings.extend(
               check_orphan_workspaces(repo_root, feature_slug, snapshot)
           )
           result.findings.extend(
               check_drift(feature_dir)
           )

       return result
   ```
4. Export from `status/__init__.py`: `DoctorResult`, `Finding`, `Severity`, `Category`, `run_doctor`.

**Files**: `src/specify_cli/status/doctor.py`, `src/specify_cli/status/__init__.py`

**Validation**: DoctorResult and Finding dataclasses can be constructed and serialized.

**Edge Cases**:
- No status.json and no events file: snapshot is None, skip all checks (feature not migrated yet).
- Feature directory does not exist: raise a clear error before running checks.

### T060: Stale Claim Detection

**Purpose**: Detect WPs that have been in `claimed` or `in_progress` for longer than a configurable threshold.

**Steps**:
1. Implement `check_stale_claims()`:
   ```python
   from datetime import datetime, timezone, timedelta

   def check_stale_claims(
       feature_dir: Path,
       snapshot: dict,
       *,
       claimed_threshold_days: int = 7,
       in_progress_threshold_days: int = 14,
   ) -> list[Finding]:
       """Check for WPs stuck in claimed or in_progress."""
       findings = []
       now = datetime.now(timezone.utc)

       work_packages = snapshot.get("work_packages", {})
       for wp_id, wp_state in work_packages.items():
           lane = wp_state.get("lane")
           last_transition_at = wp_state.get("last_transition_at")

           if not last_transition_at:
               continue

           try:
               transition_time = datetime.fromisoformat(last_transition_at)
           except (ValueError, TypeError):
               continue

           age_days = (now - transition_time).days

           if lane == "claimed" and age_days > claimed_threshold_days:
               findings.append(Finding(
                   severity=Severity.WARNING,
                   category=Category.STALE_CLAIM,
                   wp_id=wp_id,
                   message=(
                       f"{wp_id} has been in 'claimed' for {age_days} days "
                       f"(threshold: {claimed_threshold_days} days). "
                       f"Actor: {wp_state.get('actor', 'unknown')}"
                   ),
                   recommended_action=(
                       f"Either begin work on {wp_id} (move to in_progress) "
                       f"or release the claim (move back to planned)."
                   ),
               ))

           if lane == "in_progress" and age_days > in_progress_threshold_days:
               findings.append(Finding(
                   severity=Severity.WARNING,
                   category=Category.STALE_CLAIM,
                   wp_id=wp_id,
                   message=(
                       f"{wp_id} has been in 'in_progress' for {age_days} days "
                       f"(threshold: {in_progress_threshold_days} days). "
                       f"Actor: {wp_state.get('actor', 'unknown')}"
                   ),
                   recommended_action=(
                       f"Check if {wp_id} is blocked (move to blocked with reason) "
                       f"or complete the work (move to for_review)."
                   ),
               ))

       return findings
   ```
2. The thresholds are configurable per call and via CLI flags (default 7 for claimed, 14 for in_progress).
3. Actor identity is included in the finding message for actionability.

**Files**: `src/specify_cli/status/doctor.py`

**Validation**:
- Test: WP in claimed for 3 days with threshold 7 -> no finding.
- Test: WP in claimed for 10 days with threshold 7 -> finding.
- Test: WP in in_progress for 20 days with threshold 14 -> finding.
- Test: WP in done -> no finding (terminal state, not stale).
- Test: custom thresholds are respected.

**Edge Cases**:
- `last_transition_at` is missing or malformed: skip this WP, do not crash.
- WP in `blocked`: not checked for staleness (blocking is intentional, not stale).
- Timezone handling: all timestamps should be UTC. Use `datetime.fromisoformat()` which handles `Z` suffix in Python 3.11+.

### T061: Orphan Workspace Detection

**Purpose**: Detect worktrees that exist for a feature where all WPs are done or canceled.

**Steps**:
1. Implement `check_orphan_workspaces()`:
   ```python
   def check_orphan_workspaces(
       repo_root: Path,
       feature_slug: str,
       snapshot: dict,
   ) -> list[Finding]:
       """Detect orphan worktrees for completed/canceled features."""
       findings = []

       # Check if all WPs are in terminal states
       work_packages = snapshot.get("work_packages", {})
       if not work_packages:
           return findings

       terminal_lanes = {"done", "canceled"}
       all_terminal = all(
           wp.get("lane") in terminal_lanes
           for wp in work_packages.values()
       )

       if not all_terminal:
           return findings  # Feature still has active WPs, worktrees are legitimate

       # Scan for worktrees matching this feature
       worktrees_dir = repo_root / ".worktrees"
       if not worktrees_dir.exists():
           return findings

       feature_pattern = f"{feature_slug}-WP*"
       orphan_dirs = list(worktrees_dir.glob(feature_pattern))

       for orphan_dir in orphan_dirs:
           if orphan_dir.is_dir():
               findings.append(Finding(
                   severity=Severity.WARNING,
                   category=Category.ORPHAN_WORKSPACE,
                   wp_id=None,
                   message=(
                       f"Worktree '{orphan_dir.name}' exists but all WPs in "
                       f"'{feature_slug}' are terminal ({', '.join(terminal_lanes)}). "
                       f"Path: {orphan_dir}"
                   ),
                   recommended_action=(
                       f"Remove the orphan worktree: git worktree remove {orphan_dir.name}"
                   ),
               ))

       return findings
   ```
2. Only report orphans when ALL WPs are terminal. If even one WP is active, the worktrees are legitimate.
3. Scan only the `.worktrees/` directory for the specific feature slug pattern.

**Files**: `src/specify_cli/status/doctor.py`

**Validation**:
- Test: all WPs done + worktree exists -> finding.
- Test: some WPs still in_progress + worktree exists -> no finding.
- Test: all WPs done + no worktrees -> no finding.
- Test: no `.worktrees/` directory -> no finding.

**Edge Cases**:
- Feature slug contains regex special characters: `glob()` uses fnmatch, not regex, so this should be safe.
- Worktree directory exists but is a file (not a directory): `is_dir()` filters this out.
- Mixed terminal states (some done, some canceled): all are terminal, so report orphans.

### T062: Drift Detection Delegation

**Purpose**: Run the validation engine's drift checks as part of the doctor report.

**Steps**:
1. Implement `check_drift()`:
   ```python
   def check_drift(feature_dir: Path) -> list[Finding]:
       """Delegate to validation engine for drift detection.

       Uses try/except import to handle the case where WP11
       (validate) is not yet implemented.
       """
       findings = []
       try:
           from specify_cli.status.validate import (
               validate_materialization_drift,
               validate_derived_views,
           )
       except ImportError:
           # Validation engine not available yet (WP11 not merged)
           return findings

       # Materialization drift
       drift_findings = validate_materialization_drift(feature_dir)
       for msg in drift_findings:
           findings.append(Finding(
               severity=Severity.WARNING,
               category=Category.MATERIALIZATION_DRIFT,
               wp_id=None,
               message=msg,
               recommended_action=(
                   "Run 'spec-kitty agent status materialize' to regenerate "
                   "status.json from the canonical event log."
               ),
           ))

       # Derived-view drift (need snapshot and phase)
       try:
           import json
           status_path = feature_dir / "status.json"
           if status_path.exists():
               snapshot = json.loads(status_path.read_text())
               from specify_cli.status.phase import resolve_phase
               phase, _ = resolve_phase(feature_dir.parent.parent, "")
               view_findings = validate_derived_views(feature_dir, snapshot, phase)
               for msg in view_findings:
                   findings.append(Finding(
                       severity=Severity.WARNING,
                       category=Category.DERIVED_VIEW_DRIFT,
                       wp_id=None,
                       message=msg,
                       recommended_action=(
                           "Run 'spec-kitty agent status materialize' to regenerate "
                           "derived views from status.json."
                       ),
                   ))
       except Exception:
           import logging
           logging.getLogger(__name__).debug(
               "Could not check derived-view drift", exc_info=True
           )

       return findings
   ```
2. The try/except import allows the doctor to work even when the validation engine (WP11) is not yet available.
3. Drift findings from validation are wrapped in Finding objects with recommended actions.

**Files**: `src/specify_cli/status/doctor.py`

**Validation**:
- Test: with validation engine available and drift present -> findings reported.
- Test: with validation engine NOT available (mock ImportError) -> empty findings, no crash.
- Test: with no status.json -> materialization drift reported.

**Edge Cases**:
- Validation engine raises an unexpected exception: caught by broad except, logged, not propagated.
- Phase resolution fails: caught by except, doctor continues without drift check.

### T063: CLI `status doctor` Command + Tests

**Purpose**: Create the CLI command and comprehensive test suite.

**Steps**:
1. Add the `doctor` command to `src/specify_cli/cli/commands/agent/status.py`:
   ```python
   @app.command()
   def doctor(
       feature: Annotated[Optional[str], typer.Option("--feature", help="Feature slug")] = None,
       stale_claimed: Annotated[int, typer.Option("--stale-claimed-days", help="Threshold for stale claims")] = 7,
       stale_in_progress: Annotated[int, typer.Option("--stale-in-progress-days", help="Threshold for stale in-progress")] = 14,
       json_output: Annotated[bool, typer.Option("--json", help="Machine-readable output")] = False,
   ) -> None:
       """Run health checks for status hygiene."""
       from specify_cli.status.doctor import run_doctor

       # ... resolve feature_dir, repo_root, feature_slug ...

       result = run_doctor(
           feature_dir=feature_dir,
           feature_slug=feature_slug,
           repo_root=repo_root,
           stale_claimed_days=stale_claimed,
           stale_in_progress_days=stale_in_progress,
       )

       if json_output:
           import json as json_mod
           report = {
               "feature_slug": result.feature_slug,
               "healthy": result.is_healthy,
               "findings": [
                   {
                       "severity": f.severity,
                       "category": f.category,
                       "wp_id": f.wp_id,
                       "message": f.message,
                       "recommended_action": f.recommended_action,
                   }
                   for f in result.findings
               ],
           }
           console.print_json(json_mod.dumps(report))
       else:
           if result.is_healthy:
               console.print(f"[green]Healthy[/green]: {result.feature_slug}")
           else:
               console.print(f"[yellow]Issues found[/yellow]: {result.feature_slug}")
               from rich.table import Table
               table = Table(title="Doctor Findings")
               table.add_column("Severity", style="bold")
               table.add_column("Category")
               table.add_column("WP")
               table.add_column("Message")
               table.add_column("Action")
               for f in result.findings:
                   severity_style = "red" if f.severity == "error" else "yellow"
                   table.add_row(
                       f"[{severity_style}]{f.severity}[/{severity_style}]",
                       f.category,
                       f.wp_id or "-",
                       f.message,
                       f.recommended_action,
                   )
               console.print(table)

       raise typer.Exit(0 if result.is_healthy else 1)
   ```
2. Rich table output with color-coded severity for terminal display.
3. JSON output for machine consumption and CI integration.
4. Exit code: 0 = healthy, 1 = issues found.

5. Create tests in `tests/specify_cli/status/test_doctor.py`:

   **test_stale_claimed_detected**:
   - Create snapshot with WP01 in claimed, last_transition_at 10 days ago.
   - Run `check_stale_claims()` with threshold 7.
   - Verify finding with correct wp_id, category, message.

   **test_stale_in_progress_detected**:
   - Create snapshot with WP02 in in_progress, last_transition_at 20 days ago.
   - Run with threshold 14.
   - Verify finding.

   **test_no_stale_within_threshold**:
   - WP in claimed for 3 days, threshold 7.
   - No finding.

   **test_done_not_stale**:
   - WP in done for 100 days.
   - No finding (terminal states are not stale).

   **test_orphan_worktree_detected**:
   - Create `.worktrees/034-test-feature-WP01/` directory.
   - Snapshot: all WPs done.
   - Verify orphan finding.

   **test_no_orphan_active_wps**:
   - Worktree exists, but WP01 is still in_progress.
   - No orphan finding.

   **test_clean_feature_healthy**:
   - All WPs in valid active states, within thresholds, no worktrees.
   - DoctorResult.is_healthy is True.

   **test_doctor_cli_json_output**:
   - Use CliRunner to invoke doctor with `--json`.
   - Parse output as JSON.
   - Verify structure.

   **test_doctor_cli_healthy_exit_0**:
   - Healthy feature -> exit code 0.

   **test_doctor_cli_issues_exit_1**:
   - Stale claim -> exit code 1.

**Files**: `src/specify_cli/cli/commands/agent/status.py`, `tests/specify_cli/status/test_doctor.py`

**Validation**: All tests pass. Doctor module coverage reaches 90%+.

**Edge Cases**:
- Feature with zero WPs in snapshot: all checks skip gracefully.
- Snapshot loading fails: `_load_or_reduce_snapshot` should return None, and run_doctor should handle it.

## Test Strategy

**Unit Tests** (in `tests/specify_cli/status/test_doctor.py`):
- Test each check function independently: `check_stale_claims`, `check_orphan_workspaces`, `check_drift`.
- Test DoctorResult properties: `is_healthy`, `has_errors`, `has_warnings`, `findings_by_category`.
- Test Finding construction and serialization.

**CLI Tests** (in `tests/specify_cli/status/test_doctor.py` or `test_status_cli.py`):
- CliRunner tests for the doctor command.
- Verify JSON output and exit codes.

**Running Tests**:
```bash
python -m pytest tests/specify_cli/status/test_doctor.py -x -q
```

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Stale claim false positives during holidays/weekends | Noise in doctor reports | Thresholds are configurable via CLI flags; users can adjust |
| Worktree scanning slow on large repos | CLI timeout | Scan only `.worktrees/` for feature-specific patterns, not full repo |
| Drift delegation fails when WP11 not available | Doctor crashes | try/except import; drift checks gracefully skipped |
| Timezone mismatches in staleness calculation | Wrong age calculation | All timestamps assumed UTC; use timezone-aware datetime |
| Snapshot not available (no events, no status.json) | Doctor cannot run any checks | Return empty result with is_healthy=True (nothing to check) |

## Review Guidance

When reviewing this WP, verify:
1. **Read-only**: Doctor never modifies any files. All findings include RECOMMENDATIONS, not automatic fixes.
2. **Threshold configurability**: Both stale claim thresholds are configurable via CLI flags and function parameters.
3. **Graceful degradation**: Doctor works even when validation engine (WP11) is not available (try/except import).
4. **Orphan detection correctness**: Only reports orphans when ALL WPs are terminal. One active WP means worktrees are legitimate.
5. **Finding quality**: Each finding has severity, category, wp_id (where applicable), message, and recommended_action.
6. **JSON output validity**: `--json` produces parseable JSON with all finding fields.
7. **Exit codes**: 0 for healthy, 1 for issues.
8. **No fallback mechanisms**: If something fails during a check, it fails clearly, not silently.

## Activity Log

- 2026-02-08T14:07:18Z -- system -- lane=planned -- Prompt created.
