---
work_package_id: WP05
title: Compatibility Wrapper & Codebase Sweep
lane: "done"
dependencies:
- WP02
- WP03
base_branch: 051-canonical-state-authority-single-metadata-writer-WP02
base_commit: fe74fed3b1aebb64aebc0800abf835bb85b0ae95
created_at: '2026-03-19T07:31:03.295456+00:00'
subtasks:
- T023
- T024
- T025
- T026
- T027
phase: Phase 2 - Integration & Validation
assignee: ''
agent: codex
shell_pid: '11885'
review_status: "approved"
reviewed_by: "Robert Douglass"
review_feedback: ''
history:
- timestamp: '2026-03-18T20:21:07Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
requirement_refs:
- FR-002
- FR-006
- FR-009
- NFR-002
- C-001
---

# Work Package Prompt: WP05 – Compatibility Wrapper & Codebase Sweep

## Objectives & Success Criteria

- Add thin compatibility re-exports in `upgrade/feature_meta.py` so existing migration callers work unchanged.
- Verify zero direct meta.json writes remain outside `feature_metadata.py` (codebase sweep).
- Add end-to-end integration tests proving the full canonical-state + single-writer system works.
- Prove that corrupted compatibility views do not affect workflow correctness.

**Success gate**: A grep-based test for direct meta.json writes outside `feature_metadata.py` passes (zero violations). Integration tests pass with corrupted Activity Log and frontmatter lane.

## Context & Constraints

- **Plan**: `kitty-specs/051-canonical-state-authority-single-metadata-writer/plan.md`
- **Prerequisite**: WP02, WP03, and WP04 must all be complete (all write sites migrated).
- **Key files**:
  - `src/specify_cli/upgrade/feature_meta.py` — add re-exports
  - `src/specify_cli/upgrade/migrations/m_2_0_6_consistency_sweep.py` — verify still works
- **Constraint C-001**: Compatibility views must not be removed, only downgraded.
- **Note**: Migration files (`m_*.py`) are frozen historical code — they should NOT be modified. The compatibility wrapper ensures they continue working.

**Implementation command**:
```bash
spec-kitty implement WP05 --base WP04
```
Note: Since WP05 depends on WP02, WP03, and WP04, and WP04 depends on WP01, use `--base WP04` and then merge WP02 and WP03:
```bash
cd .worktrees/051-...-WP05/
git merge 051-...-WP02
git merge 051-...-WP03
```

## Subtasks & Detailed Guidance

### Subtask T023 – Compatibility re-exports in upgrade/feature_meta.py

**Purpose**: Ensure existing callers of `load_feature_meta()` and `write_feature_meta()` continue working without modification.

**Steps**:
1. Open `src/specify_cli/upgrade/feature_meta.py`.
2. Replace the implementations of `load_feature_meta()` and `write_feature_meta()` with thin wrappers:

   ```python
   # At top of file, add:
   from specify_cli.feature_metadata import load_meta, write_meta

   def load_feature_meta(feature_dir: Path) -> dict[str, Any] | None:
       """Load meta.json. Delegates to feature_metadata.load_meta().

       Kept for backward compatibility with migration code.
       """
       return load_meta(feature_dir)

   def write_feature_meta(feature_dir: Path, meta: dict[str, Any]) -> None:
       """Write meta.json. Delegates to feature_metadata.write_meta().

       Kept for backward compatibility with migration code.
       Note: write_meta() adds sort_keys=True which the original did not have.
       This is a deliberate format improvement.
       """
       write_meta(feature_dir, meta)
   ```

3. **Keep all other functions** in `feature_meta.py`:
   - `infer_target_branch()` — upgrade-specific logic
   - `infer_mission()` — upgrade-specific logic
   - `infer_created_at()` — upgrade-specific logic
   - `build_baseline_feature_meta()` — upgrade-specific logic
   - `_normalize_branch_candidate()` — internal helper
   - `_set_if_blank()` — internal helper

4. These functions are NOT metadata write concerns — they're upgrade/inference utilities. They stay in `feature_meta.py`.

**Files**: `src/specify_cli/upgrade/feature_meta.py`

### Subtask T024 – Verify migration callers work through wrapper

**Purpose**: Ensure frozen migration code that calls `write_feature_meta()` still works.

**Steps**:
1. Check `src/specify_cli/upgrade/migrations/m_2_0_6_consistency_sweep.py` line ~154.
2. It calls:
   ```python
   from specify_cli.upgrade.feature_meta import write_feature_meta
   write_feature_meta(feature_dir, meta)
   ```
3. After T023, this import now routes through the thin wrapper to `feature_metadata.write_meta()`.
4. Write a focused test:
   ```python
   def test_migration_write_feature_meta_still_works(tmp_path):
       """write_feature_meta() wrapper delegates to feature_metadata.write_meta()."""
       from specify_cli.upgrade.feature_meta import write_feature_meta

       feature_dir = tmp_path / "001-test"
       feature_dir.mkdir()
       meta = {
           "feature_number": "001", "slug": "001-test",
           "feature_slug": "001-test", "friendly_name": "Test",
           "mission": "software-dev", "target_branch": "main",
           "created_at": "2026-01-01T00:00:00+00:00",
       }
       write_feature_meta(feature_dir, meta)

       content = (feature_dir / "meta.json").read_text()
       assert content.endswith("\n")
       parsed = json.loads(content)
       assert list(parsed.keys()) == sorted(parsed.keys())  # sort_keys
   ```
5. Also verify `load_feature_meta()` wrapper:
   ```python
   def test_migration_load_feature_meta_still_works(tmp_path):
       """load_feature_meta() wrapper delegates to feature_metadata.load_meta()."""
       from specify_cli.upgrade.feature_meta import load_feature_meta

       feature_dir = tmp_path / "001-test"
       feature_dir.mkdir()
       (feature_dir / "meta.json").write_text('{"feature_number": "001"}')

       result = load_feature_meta(feature_dir)
       assert result == {"feature_number": "001"}
   ```

**Files**: `tests/specify_cli/test_feature_metadata.py` (extend)

### Subtask T025 – Codebase sweep test

**Purpose**: Automated guard that catches any future direct meta.json writes outside `feature_metadata.py`.

**Steps**:
1. Create a test that scans `src/specify_cli/` for direct meta.json write patterns:

   ```python
   import re
   from pathlib import Path

   # Patterns that indicate direct meta.json writes
   WRITE_PATTERNS = [
       # json.dump to file handle
       r'json\.dump\s*\(.*meta',
       # json.dumps + write_text for meta
       r'json\.dumps\s*\(.*meta.*\).*\n.*write_text',
       # meta_path.write_text with json
       r'meta_path\.write_text\s*\(',
       # Direct write_text to meta.json
       r'meta\.json.*write_text',
   ]

   ALLOWED_FILES = {
       "feature_metadata.py",  # The single writer
   }

   # Migration files are frozen code — exclude from sweep
   EXCLUDED_DIRS = {
       "migrations",
   }

   def test_no_direct_meta_json_writes_outside_feature_metadata():
       """No code outside feature_metadata.py writes meta.json directly."""
       src_dir = Path("src/specify_cli")
       violations = []

       for py_file in src_dir.rglob("*.py"):
           if py_file.name in ALLOWED_FILES:
               continue
           if any(d in py_file.parts for d in EXCLUDED_DIRS):
               continue

           content = py_file.read_text()
           for pattern in WRITE_PATTERNS:
               if re.search(pattern, content, re.MULTILINE):
                   violations.append(f"{py_file}: matches pattern '{pattern}'")

       assert not violations, (
           f"Direct meta.json writes found outside feature_metadata.py:\n"
           + "\n".join(violations)
       )
   ```

2. This test should be placed in `tests/specify_cli/test_codebase_sweep.py`.
3. The regex patterns may need tuning — start with the obvious patterns and refine if there are false positives.
4. **Exclude migration files** — they're frozen historical code that uses the compatibility wrapper.
5. Run: `python -m pytest tests/specify_cli/test_codebase_sweep.py -v`

**Files**: `tests/specify_cli/test_codebase_sweep.py` (new file)
**Parallel?**: Yes — independent from T023/T024.

### Subtask T026 – End-to-end acceptance integration test

**Purpose**: Prove the full acceptance flow works with canonical state and single metadata writer.

**Steps**:
1. Create an integration test in `tests/specify_cli/test_canonical_acceptance.py` (extend from WP02):

   ```python
   def test_end_to_end_acceptance_canonical_flow(tmp_path):
       """Full acceptance flow: canonical state → single writer → valid meta.json."""
       # 1. Scaffold feature directory with:
       #    - meta.json (via write_meta)
       #    - status.events.jsonl with all WPs in done lane
       #    - WP files (with or without Activity Log)

       # 2. Run acceptance validation
       #    - Should read materialize() for lane state
       #    - Should NOT read Activity Log

       # 3. Run record_acceptance()
       #    - Should write through feature_metadata.py
       #    - Should produce standard format

       # 4. Verify meta.json:
       #    - accepted_at, accepted_by, acceptance_mode present
       #    - acceptance_history has 1 entry
       #    - Standard format (sorted keys, trailing newline)

       # 5. Verify NO fallback to Activity Log occurred
       #    (check that activity_entries was not called)
   ```

2. This test validates the full pipeline from SC-001 through SC-005.

**Files**: `tests/specify_cli/test_canonical_acceptance.py` (extend from WP02)

### Subtask T027 – Corrupted compatibility views integration test

**Purpose**: Prove that corrupting compatibility views doesn't change canonical truth (SC-004).

**Steps**:
1. Create tests:

   ```python
   def test_corrupted_activity_log_no_effect(tmp_path):
       """Deleting Activity Log from WP files doesn't affect acceptance."""
       # Setup: feature with canonical state showing all WPs done
       # Action: Delete Activity Log section from all WP files
       # Assert: acceptance validation still passes

   def test_corrupted_frontmatter_lane_no_effect(tmp_path):
       """Wrong frontmatter lane doesn't affect materialize()."""
       # Setup: canonical state has WP01 in done lane
       # Action: Change WP01 frontmatter lane to "planned"
       # Assert: materialize() still returns "done" for WP01
       # Assert: acceptance validation still passes

   def test_corrupted_tasks_md_status_no_effect(tmp_path):
       """Wrong tasks.md status block doesn't affect canonical state."""
       # Setup: canonical state has all WPs done
       # Action: Delete or corrupt tasks.md status block
       # Assert: materialize() returns correct state
       # Assert: acceptance validation passes
   ```

2. These tests are the core proof that compatibility views are truly non-authoritative.
3. Place in `tests/specify_cli/test_canonical_acceptance.py`.

**Files**: `tests/specify_cli/test_canonical_acceptance.py` (extend)

## Risks & Mitigations

- **Risk**: Compatibility wrapper introduces circular import (`feature_meta.py` imports from `feature_metadata.py`, and something in `feature_metadata.py` might import from `upgrade/`).
  **Mitigation**: `feature_metadata.py` has no imports from `upgrade/` — the dependency is one-way.
- **Risk**: Codebase sweep regex has false positives.
  **Mitigation**: Start with conservative patterns, add exclusions for known false positives. Document any exclusions in the test.
- **Risk**: Migration files break due to format change (`sort_keys=True` addition).
  **Mitigation**: T024 specifically tests this. The format change is harmless — JSON is valid either way.

## Review Guidance

- **Critical**: Verify the codebase sweep test catches direct writes. Manually grep `src/specify_cli/` to confirm zero violations.
- **Integration tests**: Check that test fixtures create realistic feature directories (not minimal stubs that skip edge cases).
- **Compatibility**: Verify `upgrade/feature_meta.py` still exports all its original functions. Only `load_feature_meta` and `write_feature_meta` are wrapped; inference functions stay as-is.
- **No removal**: Confirm that Activity Log generation, frontmatter lane updates, and tasks.md status block generation are all still working (just not read for decisions).

## Activity Log

- 2026-03-18T20:21:07Z – system – lane=planned – Prompt created.
- 2026-03-19T07:31:03Z – coordinator – shell_pid=9737 – lane=doing – Assigned agent via workflow command
- 2026-03-19T07:37:07Z – coordinator – shell_pid=9737 – lane=for_review – Ready for review: compatibility wrappers, codebase sweep (zero violations), and integration tests (86 tests passing)
- 2026-03-19T07:37:35Z – codex – shell_pid=11885 – lane=doing – Started review via workflow command
- 2026-03-19T07:44:09Z – codex – shell_pid=11885 – lane=approved – Codex cycle 1 finding fixed (load_feature_meta ValueError compat). 86/86 tests pass. Arbiter-approved with fix applied.
- 2026-03-19T08:47:00Z – codex – shell_pid=11885 – lane=done – Moved to done
