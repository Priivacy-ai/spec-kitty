---
work_package_id: WP03
title: Migrate VCS, Merge, and Feature Creation Writes
dependencies: [WP01]
requirement_refs:
- FR-002
- FR-004
- FR-009
- NFR-004
base_branch: 051-canonical-state-authority-single-metadata-writer-WP01
base_commit: 620c971a1797bf16c0855f7a67edb72a5fbab49c
created_at: '2026-03-18T21:03:24.173978+00:00'
subtasks:
- T014
- T015
- T016
- T017
- T018
phase: Phase 1 - Core Implementation
history:
- timestamp: '2026-03-18T20:21:07Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
authoritative_surface: ''
execution_mode: code_change
mission_id: 01KN2371WVZGV7TH7WMR2CN9PX
owned_files:
- kitty-specs/051-canonical-state-authority-single-metadata-writer/plan.md
- kitty-specs/051-canonical-state-authority-single-metadata-writer/research.md
- src/specify_cli/cli/commands/agent/feature.py
- src/specify_cli/cli/commands/implement.py
- src/specify_cli/scripts/tasks/tasks_cli.py
- tests/specify_cli/test_feature_metadata.py
- tests/specify_cli/test_write_site_migrations.py
wp_code: WP03
---

# Work Package Prompt: WP03 – Migrate VCS, Merge, and Feature Creation Writes

## Objectives & Success Criteria

- Migrate 4 remaining non-acceptance meta.json write sites to `feature_metadata.py`.
- Fix 2 missing-trailing-newline bugs in `feature.py`.
- All migrated writes use standard formatting (`indent=2, ensure_ascii=False, sort_keys=True, trailing newline`).
- Smallest defensible diff per site — mechanical replacement, not logic change.

**Success gate**: After migration, `implement.py`, `tasks_cli.py`, and `feature.py` contain zero direct `json.dumps` + `write_text` calls for meta.json.

## Context & Constraints

- **Plan**: `kitty-specs/051-canonical-state-authority-single-metadata-writer/plan.md` — Phase 4 section
- **Research**: `kitty-specs/051-canonical-state-authority-single-metadata-writer/research.md` — Write site inventory
- **Prerequisite**: WP01 must be complete (`feature_metadata.py` with `write_meta()`, `set_vcs_lock()`, `record_merge()`, `finalize_merge()`)
- **Key files to modify**:
  - `src/specify_cli/cli/commands/implement.py` (~lines 591, 601)
  - `src/specify_cli/scripts/tasks/tasks_cli.py` (~lines 573, 592)
  - `src/specify_cli/cli/commands/agent/feature.py` (~lines 632, 658)
- **NFR-004**: Smallest defensible diff per migration site

**Implementation command**:
```bash
spec-kitty implement WP03 --base WP01
```

## Subtasks & Detailed Guidance

### Subtask T014 – Migrate implement.py VCS lock writes

**Purpose**: Replace 2 direct meta.json writes in the VCS detection/lock function with `set_vcs_lock()`.

**Steps**:
1. Open `src/specify_cli/cli/commands/implement.py`.
2. Find `_detect_and_lock_vcs()` (approximately lines 591 and 601).
3. **Line ~591** (jj → git conversion): Currently does:
   ```python
   meta["vcs"] = "git"
   meta_path.write_text(json.dumps(meta, indent=2) + "\n")
   ```
   Replace with:
   ```python
   from specify_cli.feature_metadata import set_vcs_lock
   set_vcs_lock(feature_dir, vcs_type="git")
   ```
4. **Line ~601** (initial VCS lock): Currently does:
   ```python
   meta["vcs"] = "git"
   meta["vcs_locked_at"] = now_iso
   meta_path.write_text(json.dumps(meta, indent=2) + "\n")
   ```
   Replace with:
   ```python
   set_vcs_lock(feature_dir, vcs_type="git", locked_at=now_iso)
   ```
5. Remove unused `json` import if no longer needed in this file.
6. Note: The function may load meta.json earlier in its flow. After migration, `set_vcs_lock()` handles the load internally, so the earlier load may become unused — check and clean up.

**Files**: `src/specify_cli/cli/commands/implement.py`
**Parallel?**: Yes — independent file.

### Subtask T015 – Migrate tasks_cli.py merge metadata write

**Purpose**: Replace the merge metadata write in `_save_merge_metadata()` with `record_merge()`.

**Steps**:
1. Open `src/specify_cli/scripts/tasks/tasks_cli.py`.
2. Find `_save_merge_metadata()` (approximately line 573). It currently does:
   ```python
   meta["merged_at"] = now
   meta["merged_by"] = merged_by
   meta["merged_into"] = target_branch
   meta["merged_strategy"] = strategy
   meta["merged_push"] = push
   # ... history manipulation with cap 20 ...
   meta_path.write_text(json.dumps(meta, indent=2, sort_keys=True) + "\n")
   ```
3. Replace with:
   ```python
   from specify_cli.feature_metadata import record_merge
   record_merge(
       feature_dir,
       merged_by=merged_by,
       merged_into=target_branch,
       strategy=strategy,
       push=push,
   )
   ```
4. The `record_merge()` function handles bounded history internally (cap 20).
5. Remove the now-unused dict manipulation and direct file write.

**Files**: `src/specify_cli/scripts/tasks/tasks_cli.py`
**Parallel?**: Yes — independent function.

### Subtask T016 – Migrate tasks_cli.py finalize merge write

**Purpose**: Replace the finalize merge write in `_finalize_merge_metadata()` with `finalize_merge()`.

**Steps**:
1. Find `_finalize_merge_metadata()` (approximately line 592). It currently does:
   ```python
   meta["merged_commit"] = commit_hash
   history = meta.get("merge_history", [])
   if history:
       history[-1]["merged_commit"] = commit_hash
   meta_path.write_text(json.dumps(meta, indent=2, sort_keys=True) + "\n")
   ```
2. Replace with:
   ```python
   from specify_cli.feature_metadata import finalize_merge
   finalize_merge(feature_dir, merged_commit=commit_hash)
   ```
3. The `finalize_merge()` function handles the history[-1] mutation internally.

**Files**: `src/specify_cli/scripts/tasks/tasks_cli.py`
**Parallel?**: Yes — independent function from T015.

### Subtask T017 – Migrate feature.py creation writes (fixes newline bugs)

**Purpose**: Replace the 2 direct writes in `specify_command()` with `write_meta()` and `set_documentation_state()`. Fixes 2 missing-trailing-newline bugs.

**Steps**:
1. Open `src/specify_cli/cli/commands/agent/feature.py`.
2. Find the first write (approximately line 632). It creates the initial meta.json:
   ```python
   meta = {
       "feature_number": feature_number,
       "slug": slug,
       "feature_slug": slug,
       ...
   }
   meta_path.write_text(json.dumps(meta, indent=2))  # BUG: missing newline
   ```
   Replace with:
   ```python
   from specify_cli.feature_metadata import write_meta
   write_meta(feature_dir, meta)
   ```
   Note: This is a fresh write (no existing file), so `write_meta()` is used directly, not a mutation helper.

3. Find the second write (approximately line 658). It adds documentation state:
   ```python
   meta["documentation_state"] = { ... }
   meta_path.write_text(json.dumps(meta, indent=2))  # BUG: missing newline
   ```
   Replace with:
   ```python
   from specify_cli.feature_metadata import set_documentation_state
   set_documentation_state(feature_dir, state=doc_state)
   ```

4. Both fixes resolve the missing trailing newline bug since `write_meta()` always appends `"\n"`.

**Files**: `src/specify_cli/cli/commands/agent/feature.py`
**Parallel?**: Yes — independent file.

### Subtask T018 – Tests for migrated write sites

**Purpose**: Verify each migrated write site produces correctly formatted meta.json.

**Steps**:
1. Add tests to `tests/specify_cli/test_feature_metadata.py` (or a new file `tests/specify_cli/test_write_site_migrations.py`).
2. Test cases:

   **VCS lock**:
   ```python
   def test_vcs_lock_produces_standard_format(tmp_path):
       """set_vcs_lock() writes meta.json with standard formatting."""
       # Create initial meta.json with required fields
       # Call set_vcs_lock()
       # Read file, verify: sort_keys, ensure_ascii=False, trailing newline
       # Verify: vcs and vcs_locked_at fields present
   ```

   **Merge metadata**:
   ```python
   def test_record_merge_bounded_history(tmp_path):
       """record_merge() caps merge_history at 20 entries."""
       # Create meta.json
       # Call record_merge() 25 times
       # Verify: merge_history has exactly 20 entries (most recent 20)

   def test_finalize_merge_updates_latest_history(tmp_path):
       """finalize_merge() sets merged_commit on latest history entry."""
       # Create meta.json, call record_merge()
       # Call finalize_merge(merged_commit="abc123")
       # Verify: meta["merged_commit"] == "abc123"
       # Verify: meta["merge_history"][-1]["merged_commit"] == "abc123"
   ```

   **Feature creation**:
   ```python
   def test_feature_creation_has_trailing_newline(tmp_path):
       """write_meta() on fresh creation includes trailing newline."""
       # Create meta dict with all required fields
       # Call write_meta()
       # Read raw file content
       # Verify: ends with "\n"
       # Verify: json.loads() succeeds (valid JSON)
   ```

3. Run: `python -m pytest tests/specify_cli/test_feature_metadata.py -v`

**Files**: `tests/specify_cli/test_feature_metadata.py` (extend from WP01)

## Risks & Mitigations

- **Risk**: Feature creation path in `feature.py` constructs meta dict inline — after migration, `write_meta()` validates required fields which may fail if the dict is incomplete at that point.
  **Mitigation**: Ensure the inline dict construction includes all required fields before calling `write_meta()`.
- **Risk**: `tasks_cli.py` functions may have additional side effects beyond the write.
  **Mitigation**: Read the full function context before migrating — only replace the JSON write, not surrounding logic.

## Review Guidance

- Verify each migration is mechanical: the same fields are written, just through the centralized API.
- Check that no direct `json.dumps` + `write_text` calls remain in `implement.py`, `tasks_cli.py`, or `feature.py` for meta.json.
- Verify the trailing newline bugs in `feature.py` are fixed (check raw file content in tests).
- Confirm `feature.py` initial creation works with `write_meta()` (fresh file, not read-modify-write).

## Activity Log

- 2026-03-18T20:21:07Z – system – lane=planned – Prompt created.
- 2026-03-18T21:03:24Z – coordinator – shell_pid=51500 – lane=doing – Assigned agent via workflow command
- 2026-03-18T21:10:53Z – coordinator – shell_pid=51500 – lane=for_review – Ready for review: Migrated 4 write sites to feature_metadata.py API. Fixed 2 trailing-newline bugs. 10 new tests. All 54 tests pass.
- 2026-03-18T21:11:12Z – codex – shell_pid=56111 – lane=doing – Started review via workflow command
- 2026-03-18T21:17:46Z – codex – shell_pid=56111 – lane=planned – Moved to planned
- 2026-03-18T21:18:03Z – coordinator – shell_pid=69719 – lane=doing – Started implementation via workflow command
- 2026-03-18T21:20:12Z – coordinator – shell_pid=69719 – lane=for_review – Fixed merge tolerance per Codex feedback (cycle 2/3): wrapped record_merge/finalize_merge in try/except, 4 new tests, all 58 tests pass
- 2026-03-18T21:20:32Z – codex – shell_pid=73586 – lane=doing – Started review via workflow command
- 2026-03-18T21:24:35Z – codex – shell_pid=73586 – lane=approved – Review passed: migrated write sites use feature_metadata helpers, no direct meta.json writes remain, focused tests passed
- 2026-03-19T08:46:57Z – codex – shell_pid=73586 – lane=done – Moved to done
