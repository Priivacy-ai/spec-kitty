---
work_package_id: WP06
title: Legacy Bridge (Compatibility Views)
lane: "done"
dependencies:
- WP03
base_branch: 2.x
base_commit: dfc821d20f7b34ae18182b897bcc35720ca2c4e4
created_at: '2026-02-08T14:48:31.200239+00:00'
subtasks:
- T027
- T028
- T029
- T030
- T031
phase: Phase 1 - Canonical Log
assignee: ''
agent: ''
shell_pid: "50563"
review_status: "approved"
reviewed_by: "Robert Douglass"
history:
- timestamp: '2026-02-08T14:07:18Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP06 -- Legacy Bridge (Compatibility Views)

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
spec-kitty implement WP06 --base WP05
```

After branching from WP05, manually merge WP03's branch to get the reducer:

```bash
cd .worktrees/034-feature-status-state-model-remediation-WP06/
git merge 034-feature-status-state-model-remediation-WP03
```

This WP depends on WP03 (reducer/StatusSnapshot) and WP05 (expanded lane support in frontmatter).

---

## Objectives & Success Criteria

Create the legacy bridge -- the backward compatibility layer that generates human-readable views (WP frontmatter `lane` fields and `tasks.md` status sections) from the canonical `status.json` snapshot. These views are never authoritative; they are compatibility caches that existing tools (agents, dashboards, slash commands) read. This WP delivers:

1. `update_frontmatter_views()` -- regenerates WP frontmatter `lane` fields from StatusSnapshot
2. `update_tasks_md_views()` -- regenerates tasks.md status sections from StatusSnapshot
3. `update_all_views()` -- convenience function that calls both
4. Phase-aware behavior -- different behavior in Phase 0, 1, and 2
5. Comprehensive unit tests

**Success**: Given a StatusSnapshot showing WP01 in `for_review` and WP02 in `done`, the frontmatter `lane` fields in WP01.md and WP02.md are updated to match. The bridge operates correctly in all three phases. Round-trip consistency: generate views from snapshot, read views back, values match snapshot.

---

## Context & Constraints

- **Spec**: `kitty-specs/034-feature-status-state-model-remediation/spec.md` -- FR-012 (regenerate views after materialization), FR-013 (views are compatibility caches only, not authoritative after Phase 2)
- **Plan**: `kitty-specs/034-feature-status-state-model-remediation/plan.md` -- AD-7 (Legacy Bridge), AD-6 (Unified Fan-Out showing where legacy_bridge fits in pipeline)
- **Data Model**: `kitty-specs/034-feature-status-state-model-remediation/data-model.md` -- File Layout, Authority hierarchy

**Key constraints**:

- Use `FrontmatterManager` from `src/specify_cli/frontmatter.py` for reading/writing WP frontmatter
- WP task files are at: `kitty-specs/<feature>/tasks/WP##-*.md` (glob pattern for discovery)
- The `lane` field in frontmatter is a scalar string value
- Do NOT modify subtask checkboxes in tasks.md (those are for subtask tracking, separate from lane status)
- Phase 0: legacy_bridge is a no-op (no event log yet, frontmatter is still the authority)
- Phase 1: update views on every emit (dual-write mode)
- Phase 2: views are generated after materialize only, never read as authority
- Use `resolve_phase()` from `status/phase.py` to determine current phase
- No fallback mechanisms -- if frontmatter write fails, the error propagates

**Existing code references**:

- `src/specify_cli/frontmatter.py` -- `FrontmatterManager` class with `read_frontmatter()`, `write_frontmatter()`, `update_field()` methods
- `src/specify_cli/status/reducer.py` -- `StatusSnapshot` dataclass, `materialize()` function
- `src/specify_cli/status/phase.py` -- `resolve_phase()` function

---

## Subtasks & Detailed Guidance

### Subtask T027 -- Create `src/specify_cli/status/legacy_bridge.py`

**Purpose**: Main module for generating compatibility views from canonical StatusSnapshot.

**Steps**:

1. Create `src/specify_cli/status/legacy_bridge.py` with imports:

   ```python
   from __future__ import annotations

   import logging
   from pathlib import Path
   from typing import Any

   from specify_cli.frontmatter import FrontmatterManager
   from specify_cli.status.models import StatusSnapshot
   from specify_cli.status.phase import resolve_phase

   logger = logging.getLogger(__name__)
   ```

2. Implement the three public functions:

   ```python
   def update_all_views(
       feature_dir: Path,
       snapshot: StatusSnapshot,
       *,
       repo_root: Path | None = None,
   ) -> None:
       """Update all compatibility views from the canonical snapshot.

       Checks the current phase and adjusts behavior:
       - Phase 0: No-op (no event log, frontmatter is still authority)
       - Phase 1: Update views (dual-write mode)
       - Phase 2: Update views (views are generated-only)

       Args:
           feature_dir: Path to the feature directory (kitty-specs/<feature>/)
           snapshot: The StatusSnapshot to generate views from
           repo_root: Repository root for phase resolution. If None, derived from feature_dir.
       """
       if repo_root is None:
           # Derive repo_root: feature_dir is typically kitty-specs/<slug>/
           repo_root = feature_dir.parent.parent

       phase, source = resolve_phase(repo_root, snapshot.feature_slug)

       if phase == 0:
           logger.debug(
               "Phase 0 (%s): legacy bridge is no-op", source
           )
           return

       # Phase 1 and Phase 2: update views
       update_frontmatter_views(feature_dir, snapshot)
       update_tasks_md_views(feature_dir, snapshot)

       logger.debug(
           "Legacy views updated for %s (phase %d: %s)",
           snapshot.feature_slug, phase, source,
       )
   ```

3. Export all three functions in `status/__init__.py`

**Files**: `src/specify_cli/status/legacy_bridge.py` (new file)

**Validation**:

- `update_all_views()` with Phase 0 does nothing (verify frontmatter unchanged)
- `update_all_views()` with Phase 1 updates both frontmatter and tasks.md
- `update_all_views()` with Phase 2 also updates both (views are regenerated, just not read as authority)

**Edge Cases**:

- `repo_root` is None: derive from feature_dir path structure
- Feature directory does not exist: functions should handle gracefully (no WP files to update)
- Snapshot has WPs that don't have corresponding task files: log warning, skip

---

### Subtask T028 -- Frontmatter lane field regeneration

**Purpose**: For each WP in the snapshot, find the corresponding task file and update its frontmatter `lane` field.

**Steps**:

1. Implement `update_frontmatter_views()`:

   ```python
   def update_frontmatter_views(
       feature_dir: Path,
       snapshot: StatusSnapshot,
   ) -> None:
       """Update WP frontmatter lane fields from StatusSnapshot.

       For each WP in the snapshot, finds the corresponding
       tasks/WP##-*.md file and updates its 'lane' field.
       """
       tasks_dir = feature_dir / "tasks"
       if not tasks_dir.exists():
           logger.warning("Tasks directory not found: %s", tasks_dir)
           return

       fm = FrontmatterManager()

       for wp_id, wp_state in snapshot.work_packages.items():
           lane_value = wp_state.get("lane")
           if lane_value is None:
               continue

           # Find the WP file by glob pattern
           wp_files = list(tasks_dir.glob(f"{wp_id}-*.md"))
           if not wp_files:
               logger.warning(
                   "No task file found for %s in %s", wp_id, tasks_dir
               )
               continue
           if len(wp_files) > 1:
               logger.warning(
                   "Multiple task files for %s: %s (using first)",
                   wp_id, wp_files,
               )

           wp_file = wp_files[0]

           try:
               frontmatter, body = fm.read(wp_file)
               current_lane = frontmatter.get("lane")

               if current_lane == lane_value:
                   # Already in sync, skip write
                   continue

               frontmatter["lane"] = lane_value
               fm.write(wp_file, frontmatter, body)
               logger.debug(
                   "Updated %s lane: %s -> %s",
                   wp_id, current_lane, lane_value,
               )
           except Exception as exc:
               logger.error(
                   "Failed to update frontmatter for %s: %s",
                   wp_file, exc,
               )
               raise
   ```

2. Use `FrontmatterManager.read()` and `FrontmatterManager.write()` for consistent formatting
3. Only write if the lane value actually changed (avoid unnecessary git diffs)
4. Error handling: if a write fails, propagate the error (no silent skip)

**Files**: `src/specify_cli/status/legacy_bridge.py` (same file)

**Validation**:

- Create WP01.md with `lane: planned`, set snapshot WP01 to `for_review`, call update, verify frontmatter reads `for_review`
- If frontmatter already matches snapshot, no file write occurs (verify via file modification time)
- If WP file does not exist, warning logged but no error raised

**Edge Cases**:

- WP file has `lane: doing` (old alias): update to canonical value from snapshot (e.g., `in_progress`)
- WP file has extra frontmatter fields: preserve them (FrontmatterManager handles this)
- WP file has no frontmatter at all: FrontmatterManager.read() may raise -- let it propagate
- Multiple WP files matching pattern (e.g., WP01-old.md and WP01-new.md): use first, warn about ambiguity
- Snapshot contains WP IDs not found in tasks dir: log warning, continue with other WPs

---

### Subtask T029 -- tasks.md status section regeneration

**Purpose**: Update the status sections in tasks.md to reflect the canonical snapshot state.

**Steps**:

1. Implement `update_tasks_md_views()`:

   ```python
   def update_tasks_md_views(
       feature_dir: Path,
       snapshot: StatusSnapshot,
   ) -> None:
       """Update tasks.md status sections from StatusSnapshot.

       Updates WP section headers or status metadata to reflect
       canonical lane values. Does NOT modify subtask checkboxes
       (those are for subtask tracking, separate from lane status).
       """
       tasks_md = feature_dir / "tasks.md"
       if not tasks_md.exists():
           logger.debug("tasks.md not found: %s", tasks_md)
           return

       content = tasks_md.read_text(encoding="utf-8")
       updated = _update_wp_status_in_tasks_md(content, snapshot)

       if updated != content:
           tasks_md.write_text(updated, encoding="utf-8")
           logger.debug("Updated tasks.md status sections")
   ```

2. Implement `_update_wp_status_in_tasks_md()`:

   ```python
   import re

   def _update_wp_status_in_tasks_md(
       content: str,
       snapshot: StatusSnapshot,
   ) -> str:
       """Update WP status references in tasks.md content.

       Strategy: Find WP section headers and update any inline
       status indicators. Preserves all other content unchanged.

       Does NOT modify:
       - Subtask checkboxes ([ ] or [x])
       - Non-WP sections
       - Content within WP sections (only headers/metadata)
       """
       # For each WP in the snapshot, find its section and update
       # status markers if present.
       #
       # WP sections typically look like:
       #   ## Work Package WP01: Title (Priority: P0)
       #
       # We do not modify these headers (they don't contain lane info).
       # The status is tracked in the individual WP files, not in
       # tasks.md section content.
       #
       # For now, this is a lightweight implementation that does not
       # modify tasks.md content. The canonical source is the event
       # log, the WP frontmatter is updated by update_frontmatter_views(),
       # and tasks.md serves as a human reference that does not need
       # automated lane updates (it has checkboxes for subtask tracking).
       #
       # If future requirements add lane indicators to tasks.md,
       # this function will be extended.
       return content
   ```

3. Design decision: tasks.md does not currently contain lane status fields that need updating. The WP sections in tasks.md have subtask checkboxes (`[ ]`/`[x]`) and descriptive text, not frontmatter-style lane fields. The authoritative lane display is in the individual WP files' frontmatter. This function is a placeholder that will be extended if tasks.md adds lane indicators in the future.

**Files**: `src/specify_cli/status/legacy_bridge.py` (same file)

**Validation**:

- Calling `update_tasks_md_views()` does not modify tasks.md content (current implementation is pass-through)
- If tasks.md does not exist, function returns without error
- If tasks.md exists, it is read and compared but not modified (no unnecessary writes)

**Edge Cases**:

- tasks.md does not exist: no-op, debug log
- tasks.md is empty: no-op
- tasks.md has unexpected format: no modifications made (safe pass-through)

---

### Subtask T030 -- Phase-aware behavior

**Purpose**: Ensure the legacy bridge behaves correctly in each of the three phases.

**Steps**:

1. Phase behavior is already implemented in `update_all_views()` (T027). This subtask ensures the behavior is correct and documents the phase semantics:

   **Phase 0 (Hardening)**:
   - `update_all_views()` is a no-op
   - The event log does not exist yet
   - Frontmatter is still the sole authority for lane status
   - The transition matrix is enforced, but no events are written
   - Reason: phase 0 is about hardening validation, not introducing new persistence

   **Phase 1 (Dual-Write)**:
   - `update_all_views()` updates frontmatter from snapshot
   - Every `status.emit` call triggers: append event -> materialize -> update_all_views
   - Both the event log AND frontmatter are kept in sync
   - Existing tools continue reading from frontmatter (no behavior change for consumers)
   - The event log is the canonical source but frontmatter is the practical authority for reads
   - Drift detection (`status validate`) warns on discrepancies

   **Phase 2 (Read Cutover)**:
   - `update_all_views()` still updates frontmatter from snapshot (views are still generated)
   - But consumers now read from `status.json` instead of frontmatter
   - Frontmatter is purely a compatibility cache
   - Drift detection (`status validate`) errors on discrepancies (not just warnings)
   - Manual frontmatter edits are overwritten on next materialization

2. Import `resolve_phase` from `status/phase.py` -- this is already done in T027.

3. The phase value is determined at the start of `update_all_views()` and controls the early-return logic for Phase 0.

**Files**: `src/specify_cli/status/legacy_bridge.py` (same file)

**Validation**:

- Mock `resolve_phase()` to return each phase value (0, 1, 2) and verify behavior:
  - Phase 0: no file modifications
  - Phase 1: frontmatter updated
  - Phase 2: frontmatter updated (same as Phase 1 in terms of view generation)

**Edge Cases**:

- Phase value changes between calls: each `update_all_views()` call checks current phase
- `resolve_phase()` fails (e.g., config file corrupted): error propagates, no view updates

---

### Subtask T031 -- Unit tests for legacy bridge

**Purpose**: Comprehensive testing of view generation, phase behavior, and round-trip consistency.

**Steps**:

1. Create `tests/specify_cli/status/test_legacy_bridge.py`
2. Use `tmp_path` fixture to create test feature directory structure
3. Create helper functions to set up WP files with frontmatter
4. Test cases:

   **Frontmatter view tests**:
   - `test_update_frontmatter_changes_lane` -- WP01.md has `lane: planned`, snapshot says `for_review`, after update frontmatter reads `for_review`
   - `test_update_frontmatter_no_change_when_matching` -- WP01.md already has correct lane, no file write occurs
   - `test_update_frontmatter_multiple_wps` -- snapshot has WP01, WP02, WP03 at different lanes, all frontmatter files updated correctly
   - `test_update_frontmatter_missing_wp_file` -- snapshot has WP04 but no WP04-*.md file exists, warning logged, other WPs still updated
   - `test_update_frontmatter_preserves_other_fields` -- frontmatter has title, assignee, etc.; only lane is updated, everything else preserved

   **Tasks.md view tests**:
   - `test_update_tasks_md_no_file` -- tasks.md does not exist, no error
   - `test_update_tasks_md_no_modification` -- tasks.md exists, content unchanged (current implementation)

   **Phase-aware behavior tests**:
   - `test_phase_0_noop` -- mock resolve_phase to return 0, verify no file modifications
   - `test_phase_1_updates_views` -- mock resolve_phase to return 1, verify frontmatter updated
   - `test_phase_2_updates_views` -- mock resolve_phase to return 2, verify frontmatter updated

   **Round-trip consistency tests**:
   - `test_round_trip_consistency` -- create snapshot, update views, read frontmatter back, verify lane values match snapshot
   - `test_idempotent_update` -- call update_all_views twice with same snapshot, verify no changes on second call

   **Error handling tests**:
   - `test_frontmatter_write_error_propagates` -- simulate write failure, verify error is raised (not silently swallowed)
   - `test_tasks_dir_missing` -- feature_dir has no tasks/ subdirectory, warning logged

5. Create fixture helpers: `create_wp_file(tasks_dir, wp_id, lane)` that writes a minimal WP markdown file with frontmatter, and `create_snapshot(wps: dict[str, str])` that builds a StatusSnapshot from a WP ID to lane mapping with fixed timestamps and event IDs for deterministic testing.

**Files**: `tests/specify_cli/status/test_legacy_bridge.py` (new file)

**Validation**: `python -m pytest tests/specify_cli/status/test_legacy_bridge.py -v` -- all pass

**Edge Cases**:

- Test with WP file that has no body (only frontmatter)
- Test snapshot with empty work_packages dict (no WPs to update)

---

## Test Strategy

**Required per user requirements**: Tests verifying view generation and phase behavior.

- **Coverage target**: 100% of legacy_bridge.py
- **Test runner**: `python -m pytest tests/specify_cli/status/test_legacy_bridge.py -v`
- **Mocking**: Mock `resolve_phase()` to control phase behavior in tests
- **File-based tests**: Use `tmp_path` to create real feature directory structures with WP files
- **FrontmatterManager integration**: Use the real FrontmatterManager (not mocked) to verify correct file I/O
- **Idempotency**: Verify that calling update twice does not produce unnecessary file writes

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| FrontmatterManager API changes | Write failures | Use existing API methods (read/write); test with actual FrontmatterManager |
| WP file glob pattern mismatches | WP files not found | Pattern `WP##-*.md` matches existing convention; log warnings for misses |
| tasks.md format changes | Update logic breaks | Current implementation is pass-through; extend only when format is stable |
| Phase resolution failure | No views updated | Error propagates; no silent fallback to wrong phase |
| Partial update (some WPs updated, others fail) | Inconsistent views | Error on first failure propagates; caller can re-run after fix |

---

## Review Guidance

- **Check update_frontmatter_views()**: Uses FrontmatterManager for reads/writes, skips writes when lane already matches, logs warnings for missing files
- **Check update_tasks_md_views()**: Current implementation is a lightweight pass-through; does NOT modify subtask checkboxes
- **Check phase behavior**: Phase 0 is no-op, Phases 1 and 2 both update views
- **Check error handling**: Write failures propagate as exceptions, not silently swallowed
- **Check idempotency**: Same snapshot applied twice produces no additional file writes
- **No fallback mechanisms**: Missing WP files logged as warnings (not errors) because the canonical source is the event log, not the views. But write failures ARE errors.
- **FrontmatterManager usage**: Uses `read()` and `write()` methods, not direct YAML parsing

---

## Activity Log

- 2026-02-08T14:07:18Z -- system -- lane=planned -- Prompt created.
- 2026-02-08T15:00:34Z – unknown – shell_pid=50563 – lane=for_review – Moved to for_review
- 2026-02-08T15:00:53Z – unknown – shell_pid=50563 – lane=done – Moved to done
