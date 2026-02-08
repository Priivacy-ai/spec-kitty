---
work_package_id: WP14
title: Legacy Migration Command
lane: "done"
dependencies:
- WP02
base_branch: 2.x
base_commit: 618c104baa0af49b476bd2c6dc374be4cdfa83e6
created_at: '2026-02-08T14:49:10.900642+00:00'
subtasks:
- T070
- T071
- T072
- T073
- T074
phase: Phase 1 - Canonical Log
assignee: ''
agent: ''
shell_pid: "51278"
review_status: "approved"
reviewed_by: "Robert Douglass"
history:
- timestamp: '2026-02-08T14:07:18Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP14 -- Legacy Migration Command

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
spec-kitty implement WP14 --base WP05
```

After workspace creation, merge the WP02 and WP03 branches:

```bash
cd .worktrees/034-feature-status-state-model-remediation-WP14/
git merge 034-feature-status-state-model-remediation-WP02
git merge 034-feature-status-state-model-remediation-WP03
```

This WP depends on WP02 (event store for appending bootstrap events), WP03 (reducer for verifying materialized state), and WP05 (lane expansion and alias mapping in existing modules).

---

## Objectives & Success Criteria

Create a migration command that bootstraps canonical event logs from existing frontmatter lane state. This WP delivers:

1. `migrate_feature()` function that reads existing WP frontmatter lanes and generates bootstrap `StatusEvent` objects
2. Alias mapping during migration (`doing` resolved to `in_progress` before event creation)
3. Idempotency -- features with existing `status.events.jsonl` are skipped
4. `MigrationResult` dataclass reporting per-feature outcomes (migrated/skipped/failed)
5. CLI `status migrate` command with `--feature`, `--all`, `--dry-run`, and `--json` flags
6. Integration tests verifying the full migration pipeline

**Success**: Given a feature with 4 WPs at lanes `planned`, `doing`, `for_review`, `done`, the migration command creates `status.events.jsonl` with 4 bootstrap events (with `doing` mapped to `in_progress`), `status materialize` produces a matching snapshot, and running migrate again is a no-op.

---

## Context & Constraints

- **Spec**: `kitty-specs/034-feature-status-state-model-remediation/spec.md` -- User Story 9 (Migration from Legacy State), FR-019 through FR-021
- **Plan**: `kitty-specs/034-feature-status-state-model-remediation/plan.md` -- AD-7 (Legacy Bridge, migration section), Phase 1 scope point 6
- **Data Model**: `kitty-specs/034-feature-status-state-model-remediation/data-model.md` -- StatusEvent entity (bootstrap events use `from_lane: null` for the initial state)
- **Contracts**: `kitty-specs/034-feature-status-state-model-remediation/contracts/event-schema.json` -- note that `from_lane` is required; for bootstrap events, use the special sentinel approach described below
- **Dependency WP02**: Provides `append_event()` for writing bootstrap events to JSONL
- **Dependency WP03**: Provides `reduce()` and `materialize()` for verifying that the migrated event log produces the expected snapshot
- **Dependency WP05**: Provides the expanded 7-lane set and `LANE_ALIASES` mapping in `tasks_support.py`

**Key constraints**:
- Python 3.11+
- Bootstrap events use `from_lane` set to the Lane value representing the initial state. For a WP currently at `in_progress`, the bootstrap event has `from_lane=Lane.PLANNED` and `to_lane=Lane.IN_PROGRESS` (or a single event with `from_lane` representing "no prior state"). The contract requires `from_lane` to be a valid Lane value -- use `"planned"` as the sentinel for "no prior state" since all WPs conceptually start at `planned`.
- Alias `doing` MUST be resolved to `in_progress` before creating the bootstrap event -- never persist `doing` in the event log
- Migration must be idempotent: if `status.events.jsonl` already exists and is non-empty, skip that feature entirely
- Frontmatter reading uses existing `read_frontmatter()` from `specify_cli/frontmatter.py`
- ULID generation uses the same pattern as `sync/emitter.py`: `import ulid`
- No fallback mechanisms -- if a WP file cannot be read, report the error and fail that feature

---

## Subtasks & Detailed Guidance

### Subtask T070 -- Create Migration Function

**Purpose**: Read existing frontmatter lanes from all WP files in a feature directory and generate bootstrap StatusEvents.

**Steps**:
1. Create `src/specify_cli/status/migrate.py` (or add to `status/legacy_bridge.py` -- prefer a separate file for clarity):
   ```python
   from __future__ import annotations
   import ulid
   from dataclasses import dataclass, field
   from datetime import datetime, timezone
   from pathlib import Path
   from typing import Any

   from specify_cli.frontmatter import read_frontmatter
   from specify_cli.status.models import Lane, StatusEvent
   from specify_cli.status.store import append_event, read_events
   from specify_cli.status.transitions import LANE_ALIASES, resolve_lane_alias
   ```

2. Define `MigrationResult` dataclass:
   ```python
   @dataclass
   class WPMigrationDetail:
       wp_id: str
       original_lane: str      # Raw value from frontmatter (may be alias)
       canonical_lane: str     # Resolved canonical value
       alias_resolved: bool    # True if original != canonical
       event_id: str           # ULID of bootstrap event

   @dataclass
   class FeatureMigrationResult:
       feature_slug: str
       status: str             # "migrated", "skipped", "failed"
       wp_details: list[WPMigrationDetail] = field(default_factory=list)
       error: str | None = None

   @dataclass
   class MigrationResult:
       features: list[FeatureMigrationResult] = field(default_factory=list)
       total_migrated: int = 0
       total_skipped: int = 0
       total_failed: int = 0
       aliases_resolved: int = 0
   ```

3. Implement `migrate_feature()`:
   ```python
   def migrate_feature(
       feature_dir: Path,
       *,
       actor: str = "migration",
       dry_run: bool = False,
   ) -> FeatureMigrationResult:
       """Bootstrap canonical event log from existing frontmatter lanes."""
   ```

4. Algorithm:
   - Extract `feature_slug` from `feature_dir.name`
   - Check if `feature_dir / "status.events.jsonl"` exists and is non-empty -> skip
   - Scan `feature_dir / "tasks/"` for `WP*.md` files
   - For each WP file:
     a. Read frontmatter using `read_frontmatter()`
     b. Extract `lane` field (raw value)
     c. Resolve alias: `canonical = resolve_lane_alias(raw_lane)`
     d. Extract timestamp from frontmatter `history` list (last entry's timestamp) or use `datetime.now(UTC)`
     e. Create bootstrap `StatusEvent`:
        ```python
        event = StatusEvent(
            event_id=str(ulid.new()),
            feature_slug=feature_slug,
            wp_id=wp_id,
            from_lane=Lane.PLANNED,  # Sentinel: all WPs conceptually start here
            to_lane=Lane(canonical),
            at=timestamp,
            actor=actor,
            force=False,
            execution_mode="direct_repo",
        )
        ```
     f. If `to_lane == Lane.PLANNED`, skip creating an event (WP is already at initial state -- no transition occurred)
     g. If not `dry_run`, append the event via `append_event()`
   - Return `FeatureMigrationResult` with details

**Files**: `src/specify_cli/status/migrate.py` (new file)

**Validation**:
- Feature with 4 WPs at `planned`, `doing`, `for_review`, `done` produces 3 events (planned WP skipped -- no transition needed)
- `doing` is resolved to `in_progress` in the event's `to_lane`
- All events have `actor="migration"` and `execution_mode="direct_repo"`
- Events have valid ULID event_ids

**Edge Cases**:
- WP file with no `lane` field in frontmatter: treat as `planned` (no event needed)
- WP file with unrecognized lane value (not in canonical set or aliases): report error for this WP, continue with others
- Feature directory with no `tasks/` subdirectory: report error, return failed result
- WP file with empty or malformed frontmatter: report error for this WP, continue
- Feature with `status.events.jsonl` containing only whitespace or empty lines: treat as non-empty (skip)
- History timestamps in non-UTC format: normalize to UTC before use

---

### Subtask T071 -- Alias Mapping in Bootstrap Events

**Purpose**: Ensure `doing` and any future aliases are resolved to canonical lane values before event creation.

**Steps**:
1. In `migrate_feature()`, before creating the StatusEvent:
   ```python
   raw_lane = frontmatter.get("lane", "planned")
   canonical_lane = resolve_lane_alias(raw_lane)
   alias_was_resolved = raw_lane.strip().lower() != canonical_lane
   ```

2. Track alias resolution in `WPMigrationDetail`:
   ```python
   detail = WPMigrationDetail(
       wp_id=wp_id,
       original_lane=raw_lane,
       canonical_lane=canonical_lane,
       alias_resolved=alias_was_resolved,
       event_id=event.event_id if event else "",
   )
   ```

3. Aggregate alias resolution count in `MigrationResult`:
   ```python
   result.aliases_resolved = sum(
       1 for f in result.features
       for wp in f.wp_details
       if wp.alias_resolved
   )
   ```

**Files**: `src/specify_cli/status/migrate.py` (same file)

**Validation**:
- WP with `lane: doing` produces event with `to_lane=Lane.IN_PROGRESS` and `alias_resolved=True`
- WP with `lane: in_progress` produces event with `alias_resolved=False`
- MigrationResult correctly counts total aliases resolved

**Edge Cases**:
- Case sensitivity: `lane: Doing` or `lane: DOING` should all resolve to `in_progress`
- Whitespace: `lane: " doing "` (with spaces) should resolve correctly via `resolve_lane_alias()` which strips
- Future aliases: if new aliases are added to `LANE_ALIASES`, migration automatically handles them

---

### Subtask T072 -- Idempotency

**Purpose**: Ensure migration is safe to run multiple times without creating duplicate events.

**Steps**:
1. At the start of `migrate_feature()`, check for existing event log:
   ```python
   events_file = feature_dir / "status.events.jsonl"
   if events_file.exists():
       content = events_file.read_text().strip()
       if content:
           return FeatureMigrationResult(
               feature_slug=feature_slug,
               status="skipped",
               error=None,
           )
   ```

2. The check must be strict: only skip if the file has actual content (not just empty lines or whitespace).

3. After migration, verify the created event log by reading it back:
   ```python
   if not dry_run:
       events = read_events(feature_dir)
       if len(events) != expected_count:
           # This should never happen -- fail loudly
           raise RuntimeError(
               f"Migration verification failed: expected {expected_count} events, "
               f"found {len(events)} in {events_file}"
           )
   ```

**Files**: `src/specify_cli/status/migrate.py` (same file)

**Validation**:
- First run: creates `status.events.jsonl` with bootstrap events, returns `status="migrated"`
- Second run: detects existing file, returns `status="skipped"` with no new events
- File with only whitespace: treated as non-empty, returns `status="skipped"`

**Edge Cases**:
- Race condition: two agents run migration simultaneously. Both check file existence, both see "no file". First creates events, second appends duplicates. Mitigation: this is acceptable for now; the reducer's deduplication by `event_id` prevents state corruption. Document this in the migration output.
- File with invalid JSON lines (corrupted prior migration): skip with warning, do not attempt to "fix" the file. Direct user to `status doctor`.

---

### Subtask T073 -- CLI `status migrate` Command

**Purpose**: Create the CLI entry point for legacy migration.

**Steps**:
1. Add the migrate command to `src/specify_cli/cli/commands/agent/status.py`:
   ```python
   @app.command()
   def migrate(
       feature: str = typer.Option(None, "--feature", "-f", help="Single feature slug to migrate"),
       all_features: bool = typer.Option(False, "--all", help="Migrate all features in kitty-specs/"),
       dry_run: bool = typer.Option(False, "--dry-run", help="Preview migration without writing"),
       json_output: bool = typer.Option(False, "--json", help="JSON output"),
       actor: str = typer.Option("migration", "--actor", help="Actor name for bootstrap events"),
   ):
       """Bootstrap canonical event logs from existing frontmatter state."""
   ```

2. Feature resolution:
   - If `--feature` provided: migrate single feature at `kitty-specs/{feature}/`
   - If `--all` provided: scan `kitty-specs/` for all feature directories
   - If neither: error with "Specify --feature or --all"
   - If both: error with "Cannot use both --feature and --all"

3. For each feature, call `migrate_feature()` and collect results into `MigrationResult`.

4. Output formatting -- default (Rich):
   ```python
   from rich.console import Console
   from rich.table import Table
   from rich.panel import Panel

   console = Console()
   table = Table(title="Migration Results")
   table.add_column("Feature", style="cyan")
   table.add_column("Status", style="green")
   table.add_column("WPs", justify="right")
   table.add_column("Aliases Resolved", justify="right")
   table.add_column("Notes")
   ```

5. Output formatting -- JSON:
   ```python
   def migration_result_to_json(result: MigrationResult) -> dict[str, Any]:
       return {
           "features": [
               {
                   "feature_slug": f.feature_slug,
                   "status": f.status,
                   "wp_count": len(f.wp_details),
                   "wp_details": [
                       {
                           "wp_id": wp.wp_id,
                           "original_lane": wp.original_lane,
                           "canonical_lane": wp.canonical_lane,
                           "alias_resolved": wp.alias_resolved,
                       }
                       for wp in f.wp_details
                   ],
                   "error": f.error,
               }
               for f in result.features
           ],
           "summary": {
               "total_migrated": result.total_migrated,
               "total_skipped": result.total_skipped,
               "total_failed": result.total_failed,
               "aliases_resolved": result.aliases_resolved,
           },
       }
   ```

6. Exit codes:
   - 0: all features migrated or skipped successfully
   - 1: one or more features failed
   - 0: dry-run always succeeds (reports what would happen)

**Files**: `src/specify_cli/cli/commands/agent/status.py` (modified)

**Validation**:
- `spec-kitty agent status migrate --feature 034-feature-status-state-model-remediation --dry-run` previews without writing
- `spec-kitty agent status migrate --all` migrates all features
- `--json` flag produces valid JSON
- Exit code is 1 when any feature fails

**Edge Cases**:
- `kitty-specs/` directory does not exist: error with "No kitty-specs/ directory found"
- `kitty-specs/` is empty (no feature directories): report "No features found to migrate"
- Feature directory exists but has no `tasks/` subdirectory: report as failed for that feature
- `--all` with 50+ features: should complete in reasonable time; no progress bar needed for migration (each feature is fast)

---

### Subtask T074 -- Integration Tests

**Purpose**: End-to-end verification of the migration pipeline.

**Steps**:
1. Create `tests/integration/test_migration_e2e.py` (or `tests/specify_cli/status/test_migrate.py` for unit tests):

2. Test cases:
   - **test_migrate_feature_four_wps_various_lanes**: Create temp feature with 4 WPs at `planned`, `doing`, `for_review`, `done`. Run `migrate_feature()`. Verify:
     a. `status.events.jsonl` has 3 events (planned WP skipped)
     b. `doing` mapped to `in_progress` in event
     c. `materialize()` produces snapshot matching pre-migration state
     d. All events have `actor="migration"`

   - **test_migrate_idempotent_second_run**: Run `migrate_feature()` twice. Second call returns `status="skipped"`.

   - **test_migrate_dry_run_no_files**: Run with `dry_run=True`. Verify no `status.events.jsonl` created.

   - **test_migrate_all_features**: Create 3 temp features. Run with `--all`. Verify all three migrated.

   - **test_migrate_skips_already_migrated**: Create feature, manually create `status.events.jsonl` with one event. Run migrate. Verify skipped.

   - **test_migrate_alias_resolution_count**: Create feature with 2 WPs at `doing`. Verify `aliases_resolved == 2`.

   - **test_migrate_wp_with_no_lane_field**: WP file with no `lane` in frontmatter. Verify treated as `planned` (no event created).

   - **test_migrate_wp_with_invalid_lane**: WP file with `lane: "nonexistent"`. Verify reported as error for that WP.

   - **test_migrate_feature_result_json_output**: Verify JSON output structure matches expected schema.

   - **test_migrate_cli_via_runner**: Use typer `CliRunner` to invoke `migrate --feature test-feature --dry-run`. Verify CLI output.

3. Fixture helpers:
   ```python
   @pytest.fixture
   def feature_with_wps(tmp_path):
       """Create a feature directory with WP files at various lanes."""
       feature_dir = tmp_path / "kitty-specs" / "099-test-feature"
       tasks_dir = feature_dir / "tasks"
       tasks_dir.mkdir(parents=True)

       lanes = {"WP01": "planned", "WP02": "doing", "WP03": "for_review", "WP04": "done"}
       for wp_id, lane in lanes.items():
           wp_file = tasks_dir / f"{wp_id}-test.md"
           wp_file.write_text(
               f"---\nwork_package_id: \"{wp_id}\"\nlane: \"{lane}\"\n"
               f"history:\n  - timestamp: \"2026-02-08T10:00:00Z\"\n    lane: \"{lane}\"\n---\n"
               f"# {wp_id}\n"
           )
       return feature_dir
   ```

**Files**: `tests/specify_cli/status/test_migrate.py` (new), `tests/integration/test_migration_e2e.py` (new)

**Validation**: All tests pass with `python -m pytest tests/specify_cli/status/test_migrate.py tests/integration/test_migration_e2e.py -v`

**Edge Cases**:
- Ensure temp directories are fully isolated (no cross-test contamination via `tmp_path`)
- Verify that `read_frontmatter()` is called correctly for test WP files (frontmatter format must match what the real reader expects)
- Test with both `---` delimited YAML frontmatter and potential edge cases in YAML parsing

---

## Test Strategy

**Required per user requirements**: Integration tests for migration (explicitly listed in spec.md User Story 9).

- **Coverage target**: 95%+ of `migrate.py`
- **Test runner**: `python -m pytest tests/specify_cli/status/test_migrate.py -v`
- **Unit tests**: Mock `read_frontmatter()`, `append_event()`, `read_events()` for isolated testing
- **Integration tests**: Use real temporary feature directories with actual YAML frontmatter files
- **Parametrized tests**: Use `@pytest.mark.parametrize` for different lane values including aliases
- **Fixtures**: Factory functions for creating feature directories with configurable WP lanes
- **Negative tests**: Invalid lanes, missing directories, corrupted frontmatter, non-empty event logs

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| `read_frontmatter()` API changes between WP05 and WP14 | Migration reads wrong fields | Pin to the `read_frontmatter()` signature from WP05; add defensive checks |
| Bootstrap event `from_lane=planned` is misleading for WPs that went through multiple transitions | Audit trail incomplete | Document that bootstrap events represent "current snapshot", not full history; migration log records this |
| ULID generation produces non-monotonic IDs during fast migration | Sort order issues in reducer | ULIDs are time-based with sub-millisecond precision; for same-millisecond events, the random component provides uniqueness. Reducer sorts by `(at, event_id)` which handles this |
| `doing` alias in YAML frontmatter has inconsistent casing | Alias not resolved | `resolve_lane_alias()` handles case-insensitive matching via `.strip().lower()` |
| Large feature with 50+ WPs | Migration takes too long | Each WP is a single file read + event append; should complete in <1 second total |
| Concurrent migration on same feature | Duplicate events | Acceptable: reducer deduplicates by `event_id`. Document in migration output |

---

## Review Guidance

- **Check MigrationResult structure**: All fields present, per-feature and per-WP detail levels
- **Check migrate_feature algorithm**: Reads all WP files, resolves aliases, creates events with correct fields
- **Check bootstrap event fields**: `from_lane=planned`, `to_lane=<current>`, `actor="migration"`, `execution_mode="direct_repo"`, `force=false`
- **Check idempotency**: Existing non-empty `status.events.jsonl` causes skip, not re-migration
- **Check alias resolution**: `doing` -> `in_progress` before event creation, tracked in WPMigrationDetail
- **Check planned WP handling**: WPs already at `planned` produce no events (no transition from planned to planned)
- **Check CLI flags**: `--feature` vs `--all` mutual exclusivity, `--dry-run` prevents writes, `--json` output valid
- **Check error handling**: Per-WP errors don't fail the entire feature; per-feature errors don't fail `--all`
- **No fallback mechanisms**: Unrecognized lanes fail explicitly, not silently mapped to defaults

---

## Activity Log

- 2026-02-08T14:07:18Z -- system -- lane=planned -- Prompt created.
- 2026-02-08T15:00:47Z – unknown – shell_pid=51278 – lane=for_review – Moved to for_review
- 2026-02-08T15:01:05Z – unknown – shell_pid=51278 – lane=done – Moved to done
