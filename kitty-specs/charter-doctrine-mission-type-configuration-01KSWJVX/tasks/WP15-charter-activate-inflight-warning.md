---
work_package_id: WP15
title: spec-kitty charter activate in-flight warning
dependencies:
- WP07
- WP14
requirement_refs:
- FR-008
tracker_refs: []
planning_base_branch: feat/doctrine-mission-type-spec-01KSWJVX
merge_target_branch: feat/doctrine-mission-type-spec-01KSWJVX
branch_strategy: Planning artifacts for this mission were generated on feat/doctrine-mission-type-spec-01KSWJVX. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/doctrine-mission-type-spec-01KSWJVX unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-charter-doctrine-mission-type-configuration-01KSWJVX
base_commit: 55baad874e87199ebf61f172671b3979cfe12607
created_at: '2026-05-30T21:11:10.176380+00:00'
subtasks:
- T087
- T088
- T089
- T090
- T091
- T092
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "3462566"
history:
- at: '2026-05-30T17:21:57Z'
  event: created
  note: Initial task breakdown
agent_profile: python-pedro
authoritative_surface: src/specify_cli/charter_activate.py
execution_mode: code_change
owned_files:
- src/specify_cli/charter_activate.py
- tests/cli/test_charter_activate_warning.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your agent profile:

/ad-hoc-profile-load python-pedro

This profile contains the coding standards, testing requirements, and
architectural constraints you must follow throughout this work package.

---

# Work Package Prompt: WP15 — spec-kitty charter activate in-flight warning

## Context

FR-008 specifies that when `spec-kitty charter activate` loads a mission-type override that removes a step, it must emit a structured warning for each in-flight mission that currently has a WP in the lane corresponding to the removed step — before completing activation.

"Removing a step" means: the incoming `action_sequence` does not contain a step ID that the current active `action_sequence` contains.

The warning is **non-blocking**: activation completes after warning emission. The operator is informed but is not prevented from activating the override.

## Objective

Hook into the `spec-kitty charter activate` execution path. Compute the set of removed steps. Query `status.events.jsonl` for in-flight missions in those lanes. Emit structured warnings. Activation proceeds.

## Warning Format

```
⚠ Step 'review' removed by mission-type override.
  Affected missions:
  - 083-my-feature (WP03, currently in lane 'in_review')
  - 083-my-feature (WP05, currently in lane 'for_review')
Activation complete.
```

## Structured Warning Data

Each warning entry:
```python
@dataclass
class StepRemovalWarning:
    removed_step_id: str
    affected_missions: list[AffectedMission]

@dataclass
class AffectedMission:
    mission_slug: str
    wp_id: str
    current_lane: str
```

## Subtasks

### T087 — Hook into spec-kitty charter activate

Find `spec-kitty charter activate` in the CLI. It is likely in `src/specify_cli/cli/commands/charter_cmd.py` or a related module.

Identify the point where:
1. The incoming override is loaded (the new `action_sequence` is available)
2. The current active `action_sequence` is available for comparison
3. **Before** the override is written to disk

This is the insertion point for the step-removal check.

### T088 — Compute removed step IDs

```python
def _find_removed_steps(
    current_sequence: list[str],
    incoming_sequence: list[str],
) -> list[str]:
    """Return step IDs that are in current but not in incoming."""
    return [step for step in current_sequence if step not in incoming_sequence]
```

Call this with:
- `current_sequence` = `charter.resolve_action_sequence(mission_type_id, repo_root)` (current active)
- `incoming_sequence` = the `action_sequence` from the override being activated

### T089 — Query in-flight missions for removed steps

For each removed step ID, scan all in-flight missions:

1. Find all feature directories in `kitty-specs/` (or wherever mission specs live)
2. For each feature directory, read `status.events.jsonl` using `read_events(feature_dir)` from `specify_cli.status.store`
3. Materialize the current snapshot using `materialize(feature_dir)` from `specify_cli.status.reducer`
4. For each WP in the snapshot, check if the WP's current lane corresponds to the removed step:
   - Removed step `review` → check for WPs in lanes `for_review` or `in_review`
   - Removed step `implement` → check for WPs in lane `in_progress`
   - Removed step `specify` → check for WPs in lane `in_progress` (if specify is the active step)

The lane-to-step mapping uses the mission's current position in the `action_sequence`. A WP is "in the lane corresponding to step X" if the WP's lane is a progress lane and the active step for that WP (based on the action_sequence) is step X.

If the mapping is complex, use a simplified heuristic: any WP in a non-terminal lane (`in_progress`, `for_review`, `in_review`) is considered potentially affected by any step removal.

### T090 — Emit structured warnings

Before completing activation, for each removed step with affected missions:

```python
def _emit_step_removal_warnings(
    warnings: list[StepRemovalWarning],
    console: rich.console.Console,
) -> None:
    for warning in warnings:
        console.print(f"[yellow]⚠ Step '{warning.removed_step_id}' removed by mission-type override.[/yellow]")
        if warning.affected_missions:
            console.print("  Affected missions:")
            for mission in warning.affected_missions:
                console.print(
                    f"  - {mission.mission_slug} ({mission.wp_id}, currently in lane '{mission.current_lane}')"
                )
```

Use `rich` for consistent output formatting with the rest of the CLI.

### T091 — Activation completes non-blockingly

After emitting all warnings, activation proceeds normally. The override is written to disk.

If there are no removed steps, or no affected missions, no warning is emitted and activation proceeds silently (no change to existing behavior).

Add a brief "Activation complete." message after warnings to confirm success.

### T092 — Tests for in-flight warning

Write `tests/cli/test_charter_activate_warning.py`:

Test cases:
- **Warning emitted**: Mission override removes step `review`; one in-flight WP is in `for_review` → warning includes that WP
- **No warning when no in-flight WPs**: Override removes step `review`; no WPs in `for_review`/`in_review` → no warning, activation completes
- **Activation completes**: In both cases above, activation completes successfully (override written to disk)
- **Multiple removed steps**: Override removes both `review` and `tasks`; warnings emitted for each
- **No removed steps**: Incoming override adds a step (no removals) → no warning

Use `tmp_path` and write synthetic `status.events.jsonl` to simulate in-flight missions.

## Acceptance Criteria

- [ ] Warning emitted when removed step has in-flight WPs in the corresponding lane
- [ ] No warning when no in-flight WPs for removed step
- [ ] Activation completes in both cases (warning is non-blocking)
- [ ] Warning output includes mission_slug, wp_id, and current_lane
- [ ] All tests pass
- [ ] `mypy --strict` clean on modified files

## References

- FR-008: Step removal / live action_sequence / activate warning
- spec.md §"Scenario 2" — override with step removal
- `specify_cli.status.store.read_events()` — event log access
- `specify_cli.status.reducer.materialize()` — snapshot access

## Activity Log

- 2026-05-30T21:11:11Z – claude:sonnet:python-pedro:implementer – shell_pid=3447930 – Assigned agent via action command
- 2026-05-30T21:19:48Z – claude:sonnet:python-pedro:implementer – shell_pid=3447930 – Ready for review: charter activate in-flight warning fully implemented and tested (34 tests, 0 failures)
- 2026-05-30T21:20:13Z – claude:opus:reviewer-renata:reviewer – shell_pid=3462566 – Started review via action command
