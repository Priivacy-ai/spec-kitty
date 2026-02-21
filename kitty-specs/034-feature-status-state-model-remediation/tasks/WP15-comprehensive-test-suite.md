---
work_package_id: WP15
title: Comprehensive Test Suite
lane: "done"
dependencies:
- WP09
base_branch: 2.x
base_commit: 4c8c145ec01452056991065a4c6e605f4d3a96d4
created_at: '2026-02-08T15:25:13.415453+00:00'
subtasks:
- T075
- T076
- T077
- T078
- T079
- T080
phase: Phase 2 - Read Cutover
assignee: ''
agent: ''
shell_pid: "76040"
review_status: "approved"
reviewed_by: "Robert Douglass"
history:
- timestamp: '2026-02-08T14:07:18Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP15 -- Comprehensive Test Suite

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
spec-kitty implement WP15 --base WP11
```

After workspace creation, merge the WP09 branch:

```bash
cd .worktrees/034-feature-status-state-model-remediation-WP15/
git merge 034-feature-status-state-model-remediation-WP09
```

This WP depends on WP09 (move-task delegation, which validates the full emit pipeline is wired up) and WP11 (status validate command, which provides drift detection used in several test scenarios).

---

## Objectives & Success Criteria

Create integration tests covering dual-write, read-cutover, end-to-end CLI, cross-branch parity, conflict resolution, and migration. This WP delivers:

1. Dual-write integration tests verifying Phase 1 behavior (event + frontmatter + snapshot consistency)
2. Read-cutover integration tests verifying Phase 2 behavior (canonical reads from status.json)
3. End-to-end CLI integration tests exercising the full pipeline via `CliRunner`
4. Cross-branch parity fixtures with deterministic events and expected snapshots
5. Conflict resolution integration tests validating rollback precedence in merge scenarios
6. Migration integration tests exercising the legacy-to-canonical pipeline

**Success**: All tests pass. Cross-branch fixtures produce byte-identical output. Dual-write tests confirm three-way consistency (event log + snapshot + frontmatter). Read-cutover tests confirm canonical authority. Rollback beats forward progression in merge scenarios.

**Success Criteria References**:

- SC-003: "Unit tests for transition legality, Reducer determinism/idempotency, Conflict resolution"
- SC-004: "Integration tests for dual-write and read-cutover, Cross-branch compatibility tests"

---

## Context & Constraints

- **Spec**: `kitty-specs/034-feature-status-state-model-remediation/spec.md` -- Success Criteria SC-003, SC-004; User Stories 1-6 (which define the behaviors these tests verify)
- **Plan**: `kitty-specs/034-feature-status-state-model-remediation/plan.md` -- Test file locations in Project Structure section; AD-2 (Reducer Algorithm), AD-4 (Rollback-Aware Conflict Resolution), AD-5 (Phase Configuration)
- **Data Model**: `kitty-specs/034-feature-status-state-model-remediation/data-model.md` -- StatusEvent, StatusSnapshot, DoneEvidence schemas
- **Contracts**: `kitty-specs/034-feature-status-state-model-remediation/contracts/` -- `event-schema.json`, `snapshot-schema.json`, `transition-matrix.json` for fixture validation
- **Dependency WP09**: Confirms `move_task()` delegates to `status.emit`, meaning the full pipeline (validate -> append -> materialize -> update views -> SaaS) is operational
- **Dependency WP11**: Provides `status validate` which is exercised in E2E tests and drift detection scenarios

**Key constraints**:

- Python 3.11+, pytest
- All tests must use `tmp_path` fixtures for full isolation (no shared state between tests)
- Cross-branch parity fixtures must use fixed timestamps and event_ids (no ULID generation -- use predetermined values)
- Tests must not depend on network access or real git repositories (mock subprocess for git operations)
- Phase switching must be testable: tests set phase via temporary config files, not environment variables
- All integration tests must complete within 30 seconds individually (no long-running operations)
- No fallback mechanisms in tests -- assert explicit failure modes, never assert on graceful degradation

---

## Subtasks & Detailed Guidance

### Subtask T075 -- Dual-Write Integration Tests

**Purpose**: Verify that Phase 1 (dual-write) behavior maintains three-way consistency: event log, snapshot, and frontmatter.

**Steps**:

1. Create `tests/integration/test_dual_write.py`:

2. Test fixture -- set up Phase 1 environment:

   ```python
   @pytest.fixture
   def phase1_feature(tmp_path):
       """Create a feature directory configured for Phase 1 (dual-write)."""
       # Create kitty-specs feature directory
       feature_dir = tmp_path / "kitty-specs" / "099-test-dual-write"
       tasks_dir = feature_dir / "tasks"
       tasks_dir.mkdir(parents=True)

       # Create WP file with planned lane
       wp_file = tasks_dir / "WP01-test.md"
       wp_file.write_text(
           "---\nwork_package_id: \"WP01\"\nlane: \"planned\"\n"
           "history: []\n---\n# WP01\n"
       )

       # Configure phase 1
       kittify_dir = tmp_path / ".kittify"
       kittify_dir.mkdir()
       config = kittify_dir / "config.yaml"
       config.write_text("status:\n  phase: 1\n")

       return tmp_path, feature_dir
   ```

3. Test cases:

   **test_dual_write_event_and_frontmatter_consistent**:
   - Emit transition: `planned -> claimed` with actor
   - Verify: event exists in `status.events.jsonl`
   - Verify: `status.json` shows WP01 at `claimed`
   - Verify: frontmatter `lane` field updated to `claimed`
   - All three representations agree

   **test_dual_write_multiple_transitions**:
   - Emit: `planned -> claimed -> in_progress -> for_review`
   - Verify: 3 events in JSONL (chronologically ordered)
   - Verify: snapshot shows `for_review` as final lane
   - Verify: frontmatter lane is `for_review`

   **test_dual_write_alias_resolved_everywhere**:
   - Emit transition using `doing` as target lane
   - Verify: event `to_lane` is `in_progress` (not `doing`)
   - Verify: snapshot lane is `in_progress`
   - Verify: frontmatter lane is `in_progress`

   **test_dual_write_force_transition_recorded**:
   - Force transition `done -> in_progress` with actor and reason
   - Verify: event has `force=true`, `reason` non-null
   - Verify: snapshot `force_count` incremented
   - Verify: frontmatter reflects `in_progress`

**Files**: `tests/integration/test_dual_write.py` (new)

**Validation**: `python -m pytest tests/integration/test_dual_write.py -v` all pass

**Edge Cases**:

- Event append succeeds but frontmatter write fails: verify the operation is atomic (or document that event log is canonical and frontmatter is recoverable)
- Multiple WPs in same feature: verify each WP's frontmatter is independently updated
- Rapid sequential transitions: verify event ordering is preserved

---

### Subtask T076 -- Read-Cutover Integration Tests

**Purpose**: Verify that Phase 2 (read-cutover) reads from `status.json` as sole authority and treats frontmatter as a generated view.

**Steps**:

1. Create `tests/integration/test_read_cutover.py`:

2. Test fixture -- set up Phase 2 environment:

   ```python
   @pytest.fixture
   def phase2_feature(tmp_path):
       """Create a feature with Phase 2 configuration and pre-existing events."""
       feature_dir = tmp_path / "kitty-specs" / "099-test-cutover"
       tasks_dir = feature_dir / "tasks"
       tasks_dir.mkdir(parents=True)

       # Configure phase 2
       kittify_dir = tmp_path / ".kittify"
       kittify_dir.mkdir()
       config = kittify_dir / "config.yaml"
       config.write_text("status:\n  phase: 2\n")

       return tmp_path, feature_dir
   ```

3. Test cases:

   **test_read_cutover_status_json_is_authority**:
   - Set up feature with events and materialized snapshot
   - Read WP status via the status API
   - Verify: reads from `status.json`, not from frontmatter
   - Manually edit frontmatter to a different lane
   - Read again: still returns `status.json` value

   **test_read_cutover_frontmatter_is_generated_view**:
   - Emit transition in Phase 2
   - Verify: frontmatter is regenerated from snapshot (matches `status.json`)
   - Manually edit frontmatter to `done`
   - Run `status validate`
   - Verify: drift error reported (frontmatter disagrees with canonical state)

   **test_read_cutover_validate_detects_manual_edit**:
   - Materialize snapshot
   - Manually overwrite frontmatter `lane` to a different value
   - Run `status validate`
   - Verify: returns drift error with specific WP ID and lane mismatch details

   **test_read_cutover_materialize_regenerates_views**:
   - Emit transitions
   - Delete frontmatter `lane` field manually
   - Run `status materialize`
   - Verify: frontmatter is regenerated with correct lane

   **test_phase2_validate_fails_on_drift**:
   - In Phase 2, drift is an error (not just a warning like Phase 1)
   - Verify: validate returns non-zero exit code on drift

**Files**: `tests/integration/test_read_cutover.py` (new)

**Validation**: `python -m pytest tests/integration/test_read_cutover.py -v` all pass

**Edge Cases**:

- `status.json` does not exist in Phase 2: materialize should create it; reading before materialization should trigger explicit error (not fallback to frontmatter)
- `status.json` is corrupted: fail with explicit error message, not silent fallback
- Phase transitions mid-test: verify that switching from Phase 1 to Phase 2 (via config change) changes read behavior

---

### Subtask T077 -- E2E CLI Integration Tests

**Purpose**: Exercise the full CLI pipeline via `CliRunner`, covering create -> migrate -> emit -> validate -> materialize -> doctor.

**Steps**:

1. Create `tests/integration/test_status_e2e.py`:

2. Import typer test utilities:

   ```python
   from typer.testing import CliRunner
   from specify_cli.cli.commands.agent.status import app as status_app
   ```

3. Test cases:

   **test_e2e_full_pipeline**:
   - Create feature with WP files
   - Run `status migrate --feature test-feature`
   - Verify: events created, no errors
   - Run `status emit` for a transition
   - Verify: event appended
   - Run `status materialize --feature test-feature`
   - Verify: `status.json` created/updated
   - Run `status validate --feature test-feature`
   - Verify: zero errors reported
   - Run `status doctor --feature test-feature`
   - Verify: no issues reported (all clean)

   **test_e2e_emit_invalid_transition**:
   - Run `status emit` with illegal transition (e.g., `planned -> done`)
   - Verify: exit code non-zero, error message includes "Illegal transition"

   **test_e2e_emit_force_transition**:
   - Run `status emit --force --actor admin --reason "emergency"` with terminal exit
   - Verify: exit code 0, event recorded with force flag

   **test_e2e_validate_catches_corruption**:
   - Create feature with events
   - Manually corrupt one line in `status.events.jsonl` (invalid JSON)
   - Run `status validate`
   - Verify: error reported with specific line number

   **test_e2e_json_output_format**:
   - Run each CLI command with `--json` flag
   - Verify: output is valid JSON for each command

   **test_e2e_materialize_idempotent**:
   - Run `status materialize` twice on same event log
   - Read `status.json` after each
   - Verify: byte-identical output

**Files**: `tests/integration/test_status_e2e.py` (new)

**Validation**: `python -m pytest tests/integration/test_status_e2e.py -v` all pass

**Edge Cases**:

- CLI runner captures both stdout and stderr: verify error messages go to stderr
- Exit codes: 0 for success, 1 for validation failures, 2 for runtime errors
- Feature auto-detection: tests must set working directory or use `--feature` flag explicitly

---

### Subtask T078 -- Cross-Branch Parity Fixtures

**Purpose**: Create deterministic fixtures that both 2.x and 0.1x reducers must produce identical output from.

**Steps**:

1. Create `tests/cross_branch/` directory structure:

   ```
   tests/cross_branch/
   ├── __init__.py
   ├── fixtures/
   │   ├── sample_events.jsonl    # 10 diverse events
   │   └── expected_snapshot.json  # Deterministic expected output
   └── test_parity.py             # Parity verification test
   ```

2. Create `sample_events.jsonl` with 10 diverse events covering:
   - Event 1: `planned -> claimed` (basic transition)
   - Event 2: `claimed -> in_progress` (with workspace context)
   - Event 3: `planned -> claimed` for WP02 (second WP)
   - Event 4: `in_progress -> for_review` (submit for review)
   - Event 5: `for_review -> in_progress` with `review_ref` (rollback)
   - Event 6: `in_progress -> for_review` (resubmit after changes)
   - Event 7: `for_review -> done` with evidence (completed with evidence)
   - Event 8: `claimed -> in_progress` for WP02
   - Event 9: `in_progress -> blocked` for WP02 (blocked state)
   - Event 10: `done -> in_progress` with `force=true` (force exit from terminal)

   **All events use fixed, predetermined values**:

   ```json
   {"event_id": "01HXY0000000000000000001", "feature_slug": "099-parity-test", "wp_id": "WP01", "from_lane": "planned", "to_lane": "claimed", "at": "2026-02-01T10:00:00Z", "actor": "agent-1", "force": false, "execution_mode": "worktree", "reason": null, "review_ref": null, "evidence": null}
   ```

3. Create `expected_snapshot.json` -- the deterministic output from reducing the 10 events:

   ```json
   {
     "feature_slug": "099-parity-test",
     "materialized_at": "<will be set at test time>",
     "event_count": 10,
     "last_event_id": "01HXY0000000000000000010",
     "work_packages": {
       "WP01": {
         "lane": "in_progress",
         "actor": "agent-1",
         "last_transition_at": "2026-02-01T19:00:00Z",
         "last_event_id": "01HXY0000000000000000010",
         "force_count": 1
       },
       "WP02": {
         "lane": "blocked",
         "actor": "agent-2",
         "last_transition_at": "2026-02-01T18:00:00Z",
         "last_event_id": "01HXY0000000000000000009",
         "force_count": 0
       }
     },
     "summary": {
       "planned": 0,
       "claimed": 0,
       "in_progress": 1,
       "for_review": 0,
       "done": 0,
       "blocked": 1,
       "canceled": 0
     }
   }
   ```

4. Create `test_parity.py`:

   ```python
   import json
   from pathlib import Path
   from specify_cli.status.reducer import reduce
   from specify_cli.status.store import read_events_from_file

   FIXTURES_DIR = Path(__file__).parent / "fixtures"

   def test_reducer_produces_expected_snapshot():
       events = read_events_from_file(FIXTURES_DIR / "sample_events.jsonl")
       snapshot = reduce(events, feature_slug="099-parity-test")

       expected = json.loads((FIXTURES_DIR / "expected_snapshot.json").read_text())

       # Compare all fields except materialized_at (timestamp varies)
       assert snapshot.work_packages == expected["work_packages"]
       assert snapshot.summary == expected["summary"]
       assert snapshot.event_count == expected["event_count"]

   def test_reducer_deterministic_byte_identical():
       events = read_events_from_file(FIXTURES_DIR / "sample_events.jsonl")
       snap1 = reduce(events, feature_slug="099-parity-test")
       snap2 = reduce(events, feature_slug="099-parity-test")

       json1 = json.dumps(snap1.to_dict(), sort_keys=True, indent=2, ensure_ascii=False) + "\n"
       json2 = json.dumps(snap2.to_dict(), sort_keys=True, indent=2, ensure_ascii=False) + "\n"
       assert json1 == json2

   def test_reducer_handles_rollback_event():
       events = read_events_from_file(FIXTURES_DIR / "sample_events.jsonl")
       snapshot = reduce(events, feature_slug="099-parity-test")
       # WP01 had done -> in_progress force rollback as last event
       assert snapshot.work_packages["WP01"]["lane"] == "in_progress"
       assert snapshot.work_packages["WP01"]["force_count"] == 1
   ```

**Files**: `tests/cross_branch/__init__.py` (new), `tests/cross_branch/fixtures/sample_events.jsonl` (new), `tests/cross_branch/fixtures/expected_snapshot.json` (new), `tests/cross_branch/test_parity.py` (new)

**Validation**: `python -m pytest tests/cross_branch/test_parity.py -v` all pass

**Edge Cases**:

- The `materialized_at` field varies per run: exclude from byte comparison (compare all other fields)
- ULID-like event_ids in fixtures must be valid 26-char Crockford base32 strings
- Fixture file must use `\n` line endings (not `\r\n`) for cross-platform consistency
- Events in fixture must be in insertion order (not necessarily time order) to test the reducer's sort behavior

---

### Subtask T079 -- Conflict Resolution Integration Tests

**Purpose**: Simulate git merge scenarios with diverging event logs and verify rollback-aware precedence.

**Steps**:

1. Create `tests/integration/test_conflict_resolution.py`:

2. Test cases:

   **test_rollback_beats_forward_progression**:
   - Create base event log: WP01 at `for_review`
   - Branch A events: `for_review -> done` (approved)
   - Branch B events: `for_review -> in_progress` with `review_ref` (changes requested)
   - Merge: concatenate both event sets
   - Reduce merged log
   - Verify: WP01 final state is `in_progress` (rollback wins)

   **test_non_conflicting_events_for_different_wps**:
   - Branch A: WP01 `planned -> claimed`
   - Branch B: WP02 `planned -> claimed`
   - Merge logs
   - Verify: WP01 is `claimed`, WP02 is `claimed`

   **test_duplicate_event_ids_deduplicated**:
   - Create log with same event appearing twice (same event_id)
   - Reduce
   - Verify: event counted once, final state correct

   **test_concurrent_forward_events_timestamp_wins**:
   - Two non-rollback events from same `from_lane` for same WP
   - Event A at T1, Event B at T2 (T2 > T1)
   - Merge logs
   - Verify: later timestamp wins

   **test_mixed_conflicting_and_nonconflicting**:
   - WP01: conflicting (rollback scenario)
   - WP02: non-conflicting (independent progress)
   - Merge and reduce
   - Verify: WP01 rollback wins, WP02 progresses normally

   **test_deduplication_preserves_determinism**:
   - Same events in different order
   - Reduce both orderings
   - Verify: identical snapshots

**Files**: `tests/integration/test_conflict_resolution.py` (new)

**Validation**: `python -m pytest tests/integration/test_conflict_resolution.py -v` all pass

**Edge Cases**:

- Three-way merge (3 branches with conflicting events): verify rollback still wins
- Rollback without `review_ref` (force transition): does not get rollback priority
- Same timestamp events: `event_id` ULID ordering breaks the tie deterministically

---

### Subtask T080 -- Migration Integration Tests

**Purpose**: End-to-end migration from legacy frontmatter to canonical event log with full verification.

**Steps**:

1. Create `tests/integration/test_migration_e2e.py` (if not already created in WP14 tests -- this may extend it):

2. Test cases:

   **test_legacy_feature_full_migration_pipeline**:
   - Create feature with WPs at: `planned`, `doing`, `for_review`, `done`
   - Run `migrate_feature()`
   - Run `materialize()`
   - Run validate
   - Verify: all green (no errors, no drift)

   **test_migration_then_transition**:
   - Migrate legacy feature
   - Emit a new transition (e.g., `planned -> claimed` for a WP)
   - Materialize
   - Verify: event log has bootstrap events + new event, snapshot reflects new state

   **test_migration_alias_end_to_end**:
   - Feature with `doing` lanes
   - Migrate
   - Verify: events have `in_progress`, not `doing`
   - Materialize
   - Verify: snapshot shows `in_progress`
   - Validate
   - Verify: no alias leakage detected

   **test_migration_preserves_history_timestamps**:
   - WP files with `history` entries containing timestamps
   - Migrate
   - Verify: bootstrap events use the frontmatter history timestamp, not current time

   **test_migration_dry_run_then_real**:
   - Run migrate with `dry_run=True`
   - Verify: no files created
   - Run migrate with `dry_run=False`
   - Verify: files created, events correct

**Files**: `tests/integration/test_migration_e2e.py` (new or extended)

**Validation**: `python -m pytest tests/integration/test_migration_e2e.py -v` all pass

**Edge Cases**:

- Feature migrated from a very old version with only 4 lanes: verify 4-lane features migrate cleanly
- Feature with mixed old-format and new-format WP files: handle both

---

## Test Strategy

**This WP is the test strategy.** It implements the tests explicitly required by the user:

- **Unit tests for transition legality**: Covered by WP01/WP03 unit tests (referenced by these integration tests)
- **Reducer determinism/idempotency**: Covered by cross-branch parity fixtures (T078)
- **Conflict resolution**: Covered by conflict resolution integration tests (T079)
- **Integration tests for dual-write and read-cutover**: T075 and T076
- **Cross-branch compatibility tests**: T078

**Test organization**:

```
tests/
├── integration/
│   ├── test_dual_write.py          # T075
│   ├── test_read_cutover.py        # T076
│   ├── test_status_e2e.py          # T077
│   ├── test_conflict_resolution.py # T079
│   └── test_migration_e2e.py       # T080
└── cross_branch/
    ├── fixtures/
    │   ├── sample_events.jsonl     # T078
    │   └── expected_snapshot.json  # T078
    └── test_parity.py              # T078
```

**Coverage target**: These integration tests, combined with WP01-WP14 unit tests, should bring the `status/` package to 90%+ coverage.

**Performance**: Each integration test file should complete in <10 seconds. Total suite <60 seconds.

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Integration tests depend on WP01-WP14 implementations | Tests may fail if dependencies are buggy | Test against the public API only; use fixtures to isolate from implementation details |
| Cross-branch fixture drift | 0.1x and 2.x produce different output | Fixtures are checked into both branches; parity test is the canary |
| Test isolation failure | Tests interfere with each other | Every test uses `tmp_path`; no global state modification |
| Phase configuration in tests | Hard to simulate Phase 1 vs Phase 2 | Create config files in `tmp_path` fixtures; never modify system-level config |
| Large fixture files | Slow test startup | 10 events is small; keep fixtures minimal but diverse |
| CliRunner limitations | Cannot test all CLI edge cases | Supplement with subprocess-based tests for critical paths |

---

## Review Guidance

- **Check test coverage**: Every user story from spec.md has at least one integration test
- **Check fixture determinism**: All events in `sample_events.jsonl` use fixed, non-random values
- **Check three-way consistency**: Dual-write tests verify event log AND snapshot AND frontmatter
- **Check Phase behavior**: Phase 1 tests verify dual-write; Phase 2 tests verify canonical-only reads
- **Check rollback precedence**: Conflict resolution tests verify reviewer rollback beats forward progression
- **Check deduplication**: Duplicate event_ids are handled correctly in merge scenarios
- **Check byte-identical output**: Parity test compares serialized JSON output character-by-character
- **Check migration round-trip**: Legacy -> migrate -> materialize -> validate produces zero errors
- **No fallback mechanisms**: Tests assert on explicit error messages, not silent fallbacks
- **Test naming**: Each test name clearly describes the scenario being tested

---

## Activity Log

- 2026-02-08T14:07:18Z -- system -- lane=planned -- Prompt created.
- 2026-02-08T15:34:58Z – unknown – shell_pid=76040 – lane=done – Comprehensive test suite: 39 tests, 6 test files, all passing
