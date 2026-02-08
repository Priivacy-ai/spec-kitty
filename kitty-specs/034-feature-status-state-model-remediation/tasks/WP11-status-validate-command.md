---
work_package_id: WP11
title: Status Validate Command
lane: planned
dependencies:
- WP03
subtasks:
- T053
- T054
- T055
- T056
- T057
- T058
phase: Phase 2 - Read Cutover
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

# Work Package Prompt: WP11 -- Status Validate Command

## Review Feedback Status

> **IMPORTANT**: Before starting implementation, check the `review_status` field in this file's frontmatter.
> - If `review_status` is empty or `""`, proceed with implementation as described below.
> - If `review_status` is `"has_feedback"`, read the **Review Feedback** section below FIRST and address all feedback items before continuing.
> - If `review_status` is `"approved"`, this WP has been accepted -- no further implementation needed.

## Review Feedback

*(No feedback yet -- this section will be populated if the WP is returned from review.)*

## Objectives & Success Criteria

**Primary Objective**: Create a comprehensive validation engine and CLI command (`spec-kitty agent status validate`) that checks event schema validity, transition legality, done-evidence completeness, materialization drift, and derived-view drift. This is the enforcement mechanism for the canonical status model.

**Without validation, the canonical model is advisory only.** Validation turns it into an enforceable contract that CI can gate on.

**Success Criteria**:
1. `status validate` detects ALL categories of violations: schema errors, illegal transitions, missing evidence, materialization drift, and derived-view drift.
2. Each violation includes the specific event_id and human-readable context.
3. Exit code 0 for pass, exit code 1 for failures (CI-friendly).
4. `--json` flag produces machine-readable validation report.
5. Phase-aware behavior: Phase 1 reports drift as warnings; Phase 2 reports drift as errors.
6. A fully valid feature passes with zero errors and zero warnings.

## Context & Constraints

**Architecture References**:
- `spec.md` User Story 6 defines the validation scenarios.
- `plan.md` AD-5 specifies phase behavior: Phase 1 drift is warning, Phase 2 drift is error.
- `data-model.md` StatusEvent validation rules define the schema checks.
- `contracts/event-schema.json` is the JSON Schema for events (reference for T053).
- `contracts/transition-matrix.json` defines legal transitions (reference for T054).

**Dependency Artifacts Available**:
- WP03 provides `status/reducer.py` with `reduce()` and `materialize()` for drift detection.
- WP06 provides `status/legacy_bridge.py` for view comparison.
- WP04 provides `status/phase.py` with `resolve_phase()` for phase-aware behavior.

**Constraints**:
- The validation engine should be a library module (`status/validate.py`), not tightly coupled to the CLI.
- Each validation check is a separate function returning a list of findings.
- The CLI command aggregates all findings and formats the output.
- No automatic fixes. Validation reports problems; fixing is a separate operation.

**Implementation Command**: `spec-kitty implement WP11 --base WP06` (merge WP03 branch if needed)

## Subtasks & Detailed Guidance

### T053: Create Validation Engine

**Purpose**: Build the foundational validation framework with the `ValidationResult` dataclass and event schema validator.

**Steps**:
1. Create `src/specify_cli/status/validate.py`.
2. Define the result dataclass:
   ```python
   from dataclasses import dataclass, field

   @dataclass
   class ValidationResult:
       """Aggregate result of all validation checks."""
       errors: list[str] = field(default_factory=list)
       warnings: list[str] = field(default_factory=list)
       phase_source: str = ""

       @property
       def passed(self) -> bool:
           return len(self.errors) == 0
   ```
3. Implement `validate_event_schema(event: dict) -> list[str]`:
   ```python
   def validate_event_schema(event: dict) -> list[str]:
       """Validate a single event dict against the StatusEvent schema.

       Checks:
       - All required fields present: event_id, feature_slug, wp_id,
         from_lane, to_lane, at, actor, force, execution_mode
       - event_id is valid ULID format (26 chars, Crockford base32)
       - from_lane and to_lane are canonical lane values (never aliases)
       - at is valid ISO 8601 timestamp
       - force is boolean
       - execution_mode is "worktree" or "direct_repo"
       - If force=True, reason must be non-empty string
       - If from_lane=for_review and to_lane=in_progress, review_ref must be present
       """
       findings = []
       required_fields = [
           "event_id", "feature_slug", "wp_id",
           "from_lane", "to_lane", "at", "actor",
           "force", "execution_mode",
       ]
       for f in required_fields:
           if f not in event:
               findings.append(f"Missing required field: {f}")

       # ULID format check
       event_id = event.get("event_id", "")
       if event_id and not _is_valid_ulid(event_id):
           findings.append(f"Invalid ULID format: {event_id}")

       # Canonical lane check
       canonical = {"planned", "claimed", "in_progress", "for_review", "done", "blocked", "canceled"}
       for lane_field in ("from_lane", "to_lane"):
           val = event.get(lane_field)
           if val and val not in canonical:
               findings.append(f"{lane_field} is not canonical: {val}")

       # Force audit check
       if event.get("force") is True and not event.get("reason"):
           findings.append(f"Event {event_id}: force=true without reason")

       # Review ref check
       if event.get("from_lane") == "for_review" and event.get("to_lane") == "in_progress":
           if not event.get("review_ref"):
               findings.append(f"Event {event_id}: for_review->in_progress without review_ref")

       return findings
   ```
4. Implement the ULID format helper:
   ```python
   import re
   _ULID_PATTERN = re.compile(r"^[0-9A-HJKMNP-TV-Z]{26}$")

   def _is_valid_ulid(value: str) -> bool:
       return bool(_ULID_PATTERN.match(value))
   ```
5. Export from `status/__init__.py`: `validate_event_schema`, `ValidationResult`.

**Files**: `src/specify_cli/status/validate.py`

**Validation**: Test with valid event dicts and various malformed events.

**Edge Cases**:
- Event with extra unknown fields: should NOT be flagged (forward-compatible).
- Event with `from_lane: "doing"` (alias): SHOULD be flagged as non-canonical.
- Event with `null` event_id: caught by required field check.

### T054: Validate Transition Legality

**Purpose**: Replay all events and check that each transition is legal according to the transition matrix.

**Steps**:
1. Implement `validate_transition_legality(events: list[dict]) -> list[str]`:
   ```python
   def validate_transition_legality(events: list[dict]) -> list[str]:
       """Replay events in order and check each transition is legal.

       Uses ALLOWED_TRANSITIONS from status/transitions.py.
       Force transitions are always legal (but reported as info).
       """
       from specify_cli.status.transitions import ALLOWED_TRANSITIONS

       findings = []
       for event in events:
           from_lane = event.get("from_lane")
           to_lane = event.get("to_lane")
           event_id = event.get("event_id", "unknown")
           force = event.get("force", False)

           if force:
               # Forced transitions are legal but noteworthy
               continue

           if (from_lane, to_lane) not in ALLOWED_TRANSITIONS:
               findings.append(
                   f"Event {event_id}: illegal transition {from_lane} -> {to_lane}"
               )

       return findings
   ```
2. Sort events by (at, event_id) before checking, to ensure correct replay order.
3. Do NOT check state consistency (i.e., whether the from_lane matches the expected current state). That is the reducer's job. This function checks each event independently against the matrix.

**Files**: `src/specify_cli/status/validate.py`

**Validation**:
- Test: all legal transitions produce zero findings.
- Test: `planned -> done` (illegal without force) produces a finding.
- Test: forced `planned -> done` does NOT produce a finding.

**Edge Cases**:
- Events out of timestamp order: sort before checking.
- Missing from_lane or to_lane: caught by schema validator (T053), not duplicated here.

### T055: Validate Done-Evidence Completeness

**Purpose**: Check that every event transitioning to `done` has proper evidence or is force-flagged.

**Steps**:
1. Implement `validate_done_evidence(events: list[dict]) -> list[str]`:
   ```python
   def validate_done_evidence(events: list[dict]) -> list[str]:
       """Check all done-transitions have evidence or force flag."""
       findings = []
       for event in events:
           if event.get("to_lane") != "done":
               continue
           event_id = event.get("event_id", "unknown")
           force = event.get("force", False)

           if force:
               continue  # Forced done transitions bypass evidence requirement

           evidence = event.get("evidence")
           if not evidence:
               findings.append(
                   f"Event {event_id}: done without evidence (not forced)"
               )
               continue

           # Check evidence structure
           review = evidence.get("review") if isinstance(evidence, dict) else None
           if not review:
               findings.append(
                   f"Event {event_id}: done evidence missing review section"
               )
           elif not review.get("reviewer"):
               findings.append(
                   f"Event {event_id}: done evidence missing reviewer identity"
               )
           elif not review.get("verdict"):
               findings.append(
                   f"Event {event_id}: done evidence missing verdict"
               )
       return findings
   ```

**Files**: `src/specify_cli/status/validate.py`

**Validation**:
- Test: event to done with full evidence -> no findings.
- Test: event to done without evidence, not forced -> finding reported.
- Test: event to done with force, no evidence -> no findings.
- Test: event to done with evidence missing reviewer -> finding reported.

**Edge Cases**:
- Evidence is present but has unexpected structure (e.g., `evidence: "string"` instead of dict): caught by isinstance check.
- Evidence with extra fields: no finding (forward-compatible).

### T056: Validate Materialization Drift

**Purpose**: Compare the `status.json` file on disk with what the reducer would produce from the event log.

**Steps**:
1. Implement `validate_materialization_drift(feature_dir: Path) -> list[str]`:
   ```python
   def validate_materialization_drift(feature_dir: Path) -> list[str]:
       """Compare status.json on disk vs reducer output."""
       import json
       from specify_cli.status.store import read_events
       from specify_cli.status.reducer import reduce

       findings = []

       status_path = feature_dir / "status.json"
       events_path = feature_dir / "status.events.jsonl"

       if not events_path.exists():
           if status_path.exists():
               findings.append(
                   "status.json exists but status.events.jsonl is missing"
               )
           return findings

       if not status_path.exists():
           findings.append(
               "status.events.jsonl exists but status.json is missing "
               "(run 'status materialize' to generate)"
           )
           return findings

       # Read on-disk snapshot
       disk_snapshot = json.loads(status_path.read_text())

       # Compute expected snapshot from events
       events = read_events(feature_dir)
       expected_snapshot = reduce(events, feature_slug=disk_snapshot.get("feature_slug", ""))

       # Compare serialized forms (deterministic)
       disk_json = json.dumps(disk_snapshot, sort_keys=True, indent=2, ensure_ascii=False) + "\n"
       expected_json = json.dumps(expected_snapshot, sort_keys=True, indent=2, ensure_ascii=False) + "\n"

       if disk_json != expected_json:
           findings.append(
               "Materialization drift: status.json does not match reducer output. "
               "Run 'spec-kitty agent status materialize' to fix."
           )

       return findings
   ```

**Files**: `src/specify_cli/status/validate.py`

**Validation**:
- Test: status.json matches reducer output -> no findings.
- Test: status.json differs from reducer output -> drift reported.
- Test: events exist but no status.json -> finding reported.
- Test: status.json exists but no events -> finding reported.

**Edge Cases**:
- status.json has different indentation but same content: the deterministic serialization (sort_keys, indent=2) normalizes this.
- Empty event log (zero events): reducer should produce an empty snapshot; status.json should match.

### T057: Validate Derived-View Drift

**Purpose**: Compare WP frontmatter lane values against the canonical status snapshot.

**Steps**:
1. Implement `validate_derived_views(feature_dir: Path, snapshot: dict, phase: int) -> list[str]`:
   ```python
   def validate_derived_views(
       feature_dir: Path,
       snapshot: dict,
       phase: int,
   ) -> list[str]:
       """Compare frontmatter lanes with canonical snapshot.

       Phase 1: drift reported as warnings (informational).
       Phase 2: drift reported as errors (blocking).
       """
       findings = []
       tasks_dir = feature_dir / "tasks"
       if not tasks_dir.exists():
           return findings

       work_packages = snapshot.get("work_packages", {})

       for wp_id, wp_state in work_packages.items():
           canonical_lane = wp_state.get("lane")

           # Find the corresponding WP file
           wp_files = list(tasks_dir.glob(f"{wp_id}-*.md"))
           if not wp_files:
               findings.append(
                   f"{wp_id}: no WP file found in tasks/ (canonical state: {canonical_lane})"
               )
               continue

           wp_file = wp_files[0]
           content = wp_file.read_text()

           # Extract lane from frontmatter
           import re
           lane_match = re.search(r'^lane:\s*["\']?(\w+)["\']?\s*$', content, re.MULTILINE)
           if not lane_match:
               findings.append(
                   f"{wp_id}: no lane field in frontmatter (canonical state: {canonical_lane})"
               )
               continue

           frontmatter_lane = lane_match.group(1)

           # Resolve alias for comparison
           if frontmatter_lane == "doing":
               frontmatter_lane = "in_progress"

           if frontmatter_lane != canonical_lane:
               severity = "ERROR" if phase >= 2 else "WARNING"
               findings.append(
                   f"{severity}: {wp_id} frontmatter lane={frontmatter_lane} "
                   f"but canonical state={canonical_lane}"
               )

       return findings
   ```
2. The `phase` parameter determines severity: Phase 1 warnings are informational; Phase 2 errors are blocking.

**Files**: `src/specify_cli/status/validate.py`

**Validation**:
- Test: frontmatter matches snapshot -> no findings.
- Test: frontmatter diverges from snapshot, Phase 1 -> WARNING finding.
- Test: frontmatter diverges from snapshot, Phase 2 -> ERROR finding.
- Test: frontmatter has "doing", canonical has "in_progress" -> no finding (alias resolved).
- Test: WP file missing -> finding about missing file.

**Edge Cases**:
- WP file with malformed frontmatter (no YAML block): lane_match returns None, finding reported.
- Snapshot has WPs not in tasks/ directory: these are reported as missing.
- tasks/ has WPs not in snapshot: not checked here (that would be an orphan check for doctor).

### T058: CLI `status validate` Command + Tests

**Purpose**: Create the CLI command that runs all validation checks and reports results.

**Steps**:
1. Add the `validate` command to `src/specify_cli/cli/commands/agent/status.py`:
   ```python
   @app.command()
   def validate(
       feature: Annotated[Optional[str], typer.Option("--feature", help="Feature slug")] = None,
       json_output: Annotated[bool, typer.Option("--json", help="Machine-readable output")] = False,
   ) -> None:
       """Validate canonical status model integrity."""
       from specify_cli.status.validate import (
           ValidationResult,
           validate_event_schema,
           validate_transition_legality,
           validate_done_evidence,
           validate_materialization_drift,
           validate_derived_views,
       )
       from specify_cli.status.store import read_events_raw
       from specify_cli.status.phase import resolve_phase

       # ... resolve feature_dir, repo_root ...

       result = ValidationResult()
       phase, source = resolve_phase(repo_root, feature_slug)
       result.phase_source = source

       # 1. Read raw events
       events = read_events_raw(feature_dir)

       # 2. Schema validation
       for event in events:
           result.errors.extend(validate_event_schema(event))

       # 3. Transition legality
       result.errors.extend(validate_transition_legality(events))

       # 4. Done-evidence completeness
       result.errors.extend(validate_done_evidence(events))

       # 5. Materialization drift
       drift_findings = validate_materialization_drift(feature_dir)
       if phase >= 2:
           result.errors.extend(drift_findings)
       else:
           result.warnings.extend(drift_findings)

       # 6. Derived-view drift
       # ... load snapshot, call validate_derived_views ...

       # Output
       if json_output:
           # ... JSON report ...
           pass
       else:
           # ... Rich formatted report ...
           pass

       raise typer.Exit(0 if result.passed else 1)
   ```
2. Output format (non-JSON):
   ```
   Status Validation: 034-test-feature (Phase 1)
   -----------------------------------------------
   Errors: 2
     - Event 01HXYZ: illegal transition planned -> done
     - Event 01HXYW: done without evidence (not forced)
   Warnings: 1
     - Materialization drift: status.json does not match reducer output
   Result: FAIL
   ```
3. Output format (JSON):
   ```json
   {
     "feature_slug": "034-test-feature",
     "phase": 1,
     "phase_source": "built-in default",
     "passed": false,
     "errors": ["Event 01HXYZ: illegal transition planned -> done", "..."],
     "warnings": ["Materialization drift: ..."],
     "error_count": 2,
     "warning_count": 1
   }
   ```
4. Create tests in `tests/specify_cli/cli/commands/test_status_validate.py` or extend `test_status_cli.py`:

   **test_validate_clean_feature**: valid log, matching snapshot -> exit 0, no errors.
   **test_validate_illegal_transition**: log with planned -> done -> exit 1, error reported.
   **test_validate_missing_evidence**: done event without evidence -> exit 1.
   **test_validate_materialization_drift**: status.json manually modified -> Phase 1: warning, Phase 2: error.
   **test_validate_frontmatter_drift**: frontmatter lane manually changed -> drift reported.
   **test_validate_json_output**: `--json` produces valid JSON with all fields.
   **test_validate_no_events**: no event log -> no errors (nothing to validate).

**Files**: `src/specify_cli/cli/commands/agent/status.py`, `tests/specify_cli/cli/commands/test_status_validate.py`

**Validation**: All tests pass. Validation engine coverage reaches 90%+.

**Edge Cases**:
- Feature with no events file: should not error (nothing to validate), exit 0.
- Feature with events but no WP files: schema validation runs, derived view drift reports missing files.

## Test Strategy

**Unit Tests** (in `tests/specify_cli/status/test_validate.py`):
- Test each validation function independently with crafted event dicts.
- Test ValidationResult.passed property.

**CLI Tests** (in `tests/specify_cli/cli/commands/test_status_validate.py`):
- Use CliRunner to invoke the validate command.
- Verify exit codes and output format.

**Integration Tests** (in `tests/integration/`):
- Full pipeline: emit events, introduce violations, run validate, verify detection.

**Running Tests**:
```bash
python -m pytest tests/specify_cli/status/test_validate.py -x -q
python -m pytest tests/specify_cli/cli/commands/test_status_validate.py -x -q
```

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Validation too strict blocks legitimate workflows | Users frustrated, bypass validation | Phase 1 reports as warnings, not errors; force transitions are accepted |
| Validation too lenient misses real issues | False confidence in status integrity | Test with every known violation type; schema checks match contracts/ schemas |
| Large event logs slow validation | CLI timeout | Optimize with early termination option; typical logs are small (<100 events) |
| Phase resolution incorrect | Wrong severity for drift findings | Validate against resolve_phase() unit tests from WP04 |
| Regex frontmatter parsing fails | Drift detection misses mismatches | Use the same regex patterns as status_resolver.py; test with real WP files |

## Review Guidance

When reviewing this WP, verify:
1. **All violation categories covered**: schema, transitions, evidence, materialization drift, derived-view drift.
2. **Phase-aware severity**: Phase 1 drift is WARNING, Phase 2 is ERROR. Verify the conditional logic.
3. **Exit codes**: 0 for pass (no errors), 1 for fail (any errors). Warnings do not cause failure.
4. **Event_id in findings**: Every finding references the specific event_id for debuggability.
5. **Schema validation matches contracts/**: Compare `validate_event_schema()` checks against `contracts/event-schema.json` fields and rules.
6. **JSON output is valid**: Parse the --json output and verify all expected fields are present.
7. **No automatic fixes**: Validate reports problems, never modifies data.
8. **Forward compatibility**: Extra fields in events are not flagged as errors.

## Activity Log

- 2026-02-08T14:07:18Z -- system -- lane=planned -- Prompt created.
