---
work_package_id: WP02
title: Canonical Acceptance Refactor
lane: "approved"
dependencies: [WP01]
base_branch: 051-canonical-state-authority-single-metadata-writer-WP01
base_commit: 620c971a1797bf16c0855f7a67edb72a5fbab49c
created_at: '2026-03-18T21:03:21.651733+00:00'
subtasks:
- T008
- T009
- T010
- T011
- T012
- T013
phase: Phase 1 - Core Implementation
assignee: ''
agent: codex
shell_pid: '82692'
review_status: "approved"
reviewed_by: "Robert Douglass"
review_feedback: feedback://051-canonical-state-authority-single-metadata-writer/WP02/20260318T215527Z-310aa000.md
history:
- timestamp: '2026-03-18T20:21:07Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
requirement_refs:
- FR-001
- FR-009
- FR-011
- NFR-002
- C-001
- C-004
---

# Work Package Prompt: WP02 – Canonical Acceptance Refactor

## Objectives & Success Criteria

- Acceptance validation reads canonical status snapshot (`materialize()`) instead of parsing Activity Log body text from WP markdown files.
- All acceptance meta.json writes (standard + orchestrator) go through `record_acceptance()` from `feature_metadata.py`.
- Orchestrator and standard acceptance produce identical metadata structure.
- Activity Log and frontmatter `lane` remain as compatibility views but are never consulted for workflow truth.

**Success gate**: Run acceptance on a feature where Activity Log sections are deleted from all WP files. Acceptance succeeds because canonical `status.events.jsonl` says all WPs are done.

## Context & Constraints

- **Spec**: `kitty-specs/051-canonical-state-authority-single-metadata-writer/spec.md` — User Story 1 (P1)
- **Plan**: `kitty-specs/051-canonical-state-authority-single-metadata-writer/plan.md` — Phase 3 section
- **Research**: `kitty-specs/051-canonical-state-authority-single-metadata-writer/research.md` — Research Question 2
- **Prerequisite**: WP01 must be complete (`feature_metadata.py` with `record_acceptance()` available)
- **Key files to modify**:
  - `src/specify_cli/acceptance.py` (~lines 355-392 for Activity Log reading, ~line 538 for meta.json write)
  - `src/specify_cli/scripts/tasks/acceptance_support.py` (~lines 457-492, ~line 620)
  - `src/specify_cli/orchestrator_api/commands.py` (~line 787)
- **Status model API**: `from specify_cli.status.reducer import materialize` returns `StatusSnapshot` dict
- **Constraint C-004**: Legacy features without event logs must get explicit error, not silent fallback

**Implementation command**:
```bash
spec-kitty implement WP02 --base WP01
```

## Subtasks & Detailed Guidance

### Subtask T008 – Replace Activity Log parsing in acceptance.py

**Purpose**: This is the core fix. Acceptance currently reads Activity Log entries from WP markdown body to determine lane state. Replace with `materialize()` which reads the canonical `status.events.jsonl`.

**Steps**:
1. Open `src/specify_cli/acceptance.py`.
2. Find the Activity Log validation block (approximately lines 355-392). It looks like:
   ```python
   entries = activity_entries(wp.body)
   lanes_logged = {entry["lane"] for entry in entries}
   latest_lane = entries[-1]["lane"] if entries else None
   # ... 3 validation rules checking entries
   ```
3. Replace with canonical state check:
   ```python
   from specify_cli.status.reducer import materialize

   # At the point where WP lane validation happens:
   snapshot = materialize(feature_dir)

   for wp_id in expected_wp_ids:
       wp_lane = snapshot.get(wp_id)
       if wp_lane is None:
           activity_issues.append(f"{wp_id}: no canonical state found in status.events.jsonl")
       elif wp_lane.lane != "done":
           activity_issues.append(f"{wp_id}: canonical lane is '{wp_lane.lane}', expected 'done'")
   ```
4. **Important**: Check how `materialize()` returns data — it returns a `StatusSnapshot` (a dict keyed by wp_id). Read `src/specify_cli/status/reducer.py` to understand the exact return shape before coding.
5. **Handle missing event log**: If `status.events.jsonl` doesn't exist, `materialize()` may return an empty snapshot. Check for this and raise a clear error: "No canonical state found for feature {slug}. Cannot validate acceptance without status.events.jsonl."
6. Remove the `activity_entries()` import if it's no longer used anywhere in this file.

**Files**: `src/specify_cli/acceptance.py`
**Notes**: Do NOT remove the Activity Log section from WP files — it remains as a human narrative view. Only stop reading it for workflow decisions.

### Subtask T009 – Replace Activity Log parsing in acceptance_support.py

**Purpose**: Mirror of T008. `acceptance_support.py` is the packaged script copy with identical logic.

**Steps**:
1. Open `src/specify_cli/scripts/tasks/acceptance_support.py`.
2. Find the Activity Log validation block (approximately lines 457-492).
3. Apply the exact same replacement as T008.
4. **Important**: The `acceptance_support.py` file may use different import paths. Check what imports are available — the status module should be importable as `from specify_cli.status.reducer import materialize`.
5. Remove unused `activity_entries()` import if applicable.

**Files**: `src/specify_cli/scripts/tasks/acceptance_support.py`
**Parallel?**: Yes — can proceed alongside T008 (different file).

### Subtask T010 – Migrate acceptance.py meta.json write to record_acceptance()

**Purpose**: Replace the direct `json.dumps` + `write_text` call in acceptance.py with the centralized `record_acceptance()` function.

**Steps**:
1. Find the meta.json write in `acceptance.py` (approximately line 538). It currently does:
   ```python
   meta["accepted_at"] = ...
   meta["accepted_by"] = ...
   meta["acceptance_mode"] = ...
   meta["accepted_from_commit"] = ...
   meta["accept_commit"] = ...
   # ... history manipulation ...
   meta_path.write_text(json.dumps(meta, indent=2, sort_keys=True) + "\n")
   ```
2. Replace with:
   ```python
   from specify_cli.feature_metadata import record_acceptance

   record_acceptance(
       feature_dir,
       accepted_by=accepted_by,
       mode=acceptance_mode,
       from_commit=from_commit,
       accept_commit=accept_commit,
   )
   ```
3. Remove the now-unused dict manipulation and direct file write.
4. Note: `record_acceptance()` handles the bounded history internally.

**Files**: `src/specify_cli/acceptance.py`
**Parallel?**: Yes — can proceed alongside T008/T009.

### Subtask T011 – Migrate acceptance_support.py meta.json write to record_acceptance()

**Purpose**: Same as T010 but for the packaged script copy.

**Steps**:
1. Find the meta.json write in `acceptance_support.py` (approximately line 620).
2. Apply the same replacement as T010.
3. Verify the function parameters match (both files should have the same acceptance metadata available).

**Files**: `src/specify_cli/scripts/tasks/acceptance_support.py`
**Parallel?**: Yes — can proceed alongside T010.

### Subtask T012 – Migrate orchestrator_api meta.json write to record_acceptance()

**Purpose**: The orchestrator currently writes only `accepted_at` and `accepted_by` — missing `acceptance_mode`, history, etc. After migration, it uses `record_acceptance()` which normalizes the output. This also fixes the missing trailing newline bug.

**Steps**:
1. Open `src/specify_cli/orchestrator_api/commands.py`.
2. Find `_handle_auto_accept_command()` (approximately line 787). It currently does:
   ```python
   meta["accepted_at"] = ...
   meta["accepted_by"] = ...
   meta_path.write_text(json.dumps(meta, indent=2, sort_keys=True))  # BUG: no newline
   ```
3. Replace with:
   ```python
   from specify_cli.feature_metadata import record_acceptance

   record_acceptance(
       feature_dir,
       accepted_by=accepted_by,
       mode="orchestrator",
   )
   ```
4. The `mode="orchestrator"` ensures the acceptance is tagged correctly.
5. `from_commit` and `accept_commit` may not be available in the orchestrator context — pass `None` (they're optional in `record_acceptance()`).
6. This migration fixes the missing trailing newline bug and adds acceptance_history tracking that was previously missing from the orchestrator path.

**Files**: `src/specify_cli/orchestrator_api/commands.py`
**Parallel?**: Yes — can proceed alongside T010/T011.

### Subtask T013 – Integration tests for canonical acceptance

**Purpose**: Prove that canonical state is the sole authority for acceptance, and that orchestrator and standard acceptance produce identical metadata.

**Steps**:
1. Create `tests/specify_cli/test_canonical_acceptance.py`.
2. Test cases:

   **Canonical state authority**:
   ```python
   def test_acceptance_succeeds_with_deleted_activity_log(tmp_path):
       """Activity Log deleted from all WP files — acceptance still works."""
       # Setup: feature with status.events.jsonl showing all WPs done
       # Create WP files WITHOUT Activity Log sections
       # Run acceptance validation
       # Assert: succeeds (canonical state is authoritative)

   def test_acceptance_fails_despite_falsified_activity_log(tmp_path):
       """Activity Log says 'done' but canonical state says 'for_review'."""
       # Setup: status.events.jsonl has WP02 in for_review
       # WP02 Activity Log manually says "lane=done"
       # Run acceptance validation
       # Assert: fails with "WP02: canonical lane is 'for_review'"

   def test_acceptance_fails_with_missing_event_log(tmp_path):
       """No status.events.jsonl — explicit error, not Activity Log fallback."""
       # Setup: feature dir with WP files but no status.events.jsonl
       # Run acceptance validation
       # Assert: fails with clear error about missing canonical state
   ```

   **Orchestrator parity (FR-011)**:
   ```python
   def test_orchestrator_and_standard_acceptance_identical_structure(tmp_path):
       """Both acceptance paths produce the same meta.json fields."""
       # Setup: two identical features
       # Run standard acceptance on one, orchestrator on the other
       # Compare meta.json: same fields present (accepted_at, accepted_by,
       #   acceptance_mode, acceptance_history)
       # Ignore: timestamps, commit hashes (will differ)
   ```

   **Compatibility views preserved**:
   ```python
   def test_compatibility_views_still_generated(tmp_path):
       """Lane transitions still update frontmatter and Activity Log."""
       # Setup: feature with status model
       # Emit a transition via emit_status_transition()
       # Verify: WP frontmatter lane updated, Activity Log entry added
       # But: acceptance reads materialize(), not these views
   ```

3. Helper fixtures:
   - Create a `_make_feature()` fixture that scaffolds a complete feature directory with meta.json, status.events.jsonl, WP files.
   - Use `append_event()` from `status.store` to create canonical events.
   - Use `materialize()` to create status.json.

4. Run: `python -m pytest tests/specify_cli/test_canonical_acceptance.py -v`

**Files**: `tests/specify_cli/test_canonical_acceptance.py` (new file)

## Risks & Mitigations

- **Risk**: Legacy features without `status.events.jsonl` will break.
  **Mitigation**: Explicit error message guides users to run status migration. This is the correct behavior per C-004.
- **Risk**: `materialize()` return shape differs from what we expect.
  **Mitigation**: Read `src/specify_cli/status/reducer.py` before implementing — verify the snapshot dict structure.
- **Risk**: Acceptance logic changes subtly break existing tests.
  **Mitigation**: Run full test suite after changes: `python -m pytest tests/ -x -q`.

## Review Guidance

- **Critical check**: Verify that NO code path in acceptance reads `activity_entries()` for workflow decisions. The import can remain if used elsewhere (e.g., for generating Activity Log entries), but it must not be used to determine lane state.
- **Parity check**: Compare meta.json output from standard and orchestrator acceptance — fields should be identical (same set of keys, same structure).
- **Error messages**: Legacy features should get a clear, actionable error — not a traceback or silent incorrect behavior.
- **Backward compatibility**: Compatibility views (frontmatter, Activity Log, tasks.md status) must still be generated. Only stop reading them for decisions.

## Activity Log

- 2026-03-18T20:21:07Z – system – lane=planned – Prompt created.
- 2026-03-18T21:03:21Z – coordinator – shell_pid=51422 – lane=doing – Assigned agent via workflow command
- 2026-03-18T21:21:06Z – coordinator – shell_pid=51422 – lane=for_review – Ready for review: canonical acceptance reads materialize() instead of Activity Log; all meta.json writes via record_acceptance(); 10 integration tests; 133 related tests passing
- 2026-03-18T21:21:31Z – codex – shell_pid=74384 – lane=doing – Started review via workflow command
- 2026-03-18T21:42:42Z – codex – shell_pid=74384 – lane=planned – Moved to planned
- 2026-03-18T21:42:54Z – coordinator – shell_pid=79664 – lane=doing – Started implementation via workflow command
- 2026-03-18T21:46:00Z – coordinator – shell_pid=79664 – lane=for_review – Fixed frontmatter lane gate per Codex feedback (cycle 2/3)
- 2026-03-18T21:46:19Z – codex – shell_pid=80590 – lane=doing – Started review via workflow command
- 2026-03-18T21:55:28Z – codex – shell_pid=80590 – lane=planned – Moved to planned
- 2026-03-18T21:55:37Z – coordinator – shell_pid=82037 – lane=doing – Started implementation via workflow command
- 2026-03-18T21:57:48Z – coordinator – shell_pid=82037 – lane=for_review – Fixed empty events edge case per Codex feedback (cycle 3/3)
- 2026-03-18T21:58:03Z – codex – shell_pid=82692 – lane=doing – Started review via workflow command
- 2026-03-19T07:30:43Z – codex – shell_pid=82692 – lane=approved – Arbiter-approved after 3 Codex cycles. Empty-events edge case fixed directly. 12/12 tests pass. All functional issues addressed across 3 cycles.
