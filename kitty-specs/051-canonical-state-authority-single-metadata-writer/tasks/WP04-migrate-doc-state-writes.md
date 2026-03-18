---
work_package_id: WP04
title: Migrate doc_state.py Write Sites
lane: "doing"
dependencies: [WP01]
base_branch: 051-canonical-state-authority-single-metadata-writer-WP01
base_commit: 620c971a1797bf16c0855f7a67edb72a5fbab49c
created_at: '2026-03-18T21:03:26.581676+00:00'
subtasks:
- T019
- T020
- T021
- T022
phase: Phase 1 - Core Implementation
assignee: ''
agent: "codex"
shell_pid: "75463"
review_status: has_feedback
reviewed_by: Robert Douglass
review_feedback: feedback://051-canonical-state-authority-single-metadata-writer/WP04/20260318T211849Z-91fd956d.md
history:
- timestamp: '2026-03-18T20:21:07Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
requirement_refs:
- FR-002
- FR-009
- NFR-004
---

# Work Package Prompt: WP04 – Migrate doc_state.py Write Sites

## Objectives & Success Criteria

- Refactor `doc_state.py`'s 8 write functions to delegate file I/O to `feature_metadata.py`.
- Keep all validation logic in `doc_state.py` — only delegate the read/write layer.
- All doc_state writes produce consistent formatting (sorted keys, `ensure_ascii=False`, trailing newline).

**Success gate**: Call each doc_state setter — verify the resulting meta.json matches the standard format. No `json.dump(meta, f, indent=2)` calls remain in `doc_state.py`.

## Context & Constraints

- **Research**: `kitty-specs/051-canonical-state-authority-single-metadata-writer/research.md` — doc_state write pattern analysis
- **Prerequisite**: WP01 must be complete (`feature_metadata.py` with `load_meta()` and `write_meta()`)
- **Key file**: `src/specify_cli/doc_state.py`
- **Current pattern**: All 8 functions use `json.dump(meta, f, indent=2)` via file handle
- **Important**: `meta_file` parameter in doc_state functions is a `Path` to `meta.json` directly, not to the feature directory. Need to derive `feature_dir` as `meta_file.parent`.

**Implementation command**:
```bash
spec-kitty implement WP04 --base WP01
```

## Subtasks & Detailed Guidance

### Subtask T019 – Refactor doc_state.py I/O pattern

**Purpose**: Replace the common read/write pattern used across all 8 functions with calls to `load_meta()` and `write_meta()`.

**Steps**:
1. Open `src/specify_cli/doc_state.py`.
2. Identify the common I/O pattern used by all write functions:
   ```python
   # Current pattern (repeated in each function):
   meta: dict[str, Any] = {}
   if meta_file.exists():
       with open(meta_file, "r", encoding="utf-8") as f:
           meta = json.load(f)

   # ... validation and mutation ...

   with open(meta_file, "w", encoding="utf-8") as f:
       json.dump(meta, f, indent=2)
   ```
3. Replace with centralized I/O:
   ```python
   from specify_cli.feature_metadata import load_meta, write_meta

   # New pattern:
   feature_dir = meta_file.parent
   meta = load_meta(feature_dir) or {}

   # ... validation and mutation (UNCHANGED) ...

   write_meta(feature_dir, meta)
   ```
4. **Important**: The `meta_file` parameter is `Path("...meta.json")` — derive `feature_dir = meta_file.parent` for `load_meta()`/`write_meta()`.
5. Add the import at the top of the file:
   ```python
   from specify_cli.feature_metadata import load_meta, write_meta
   ```
6. Remove the `json` import if no longer used in the file (keep if `json` is used for other purposes like `json.loads`).

**Files**: `src/specify_cli/doc_state.py`
**Notes**: This subtask establishes the pattern. T020 and T021 apply it to specific functions.

### Subtask T020 – Update individual field setters

**Purpose**: Apply the new I/O pattern to the 4 individual field setter functions.

**Steps**:
1. **`set_iteration_mode()` (~lines 71-103)**:
   - Keep: validation (`mode in {"initial", "gap_filling", "feature_specific"}`)
   - Replace: `json.load(f)` → `load_meta(feature_dir) or {}`
   - Replace: `json.dump(meta, f, indent=2)` → `write_meta(feature_dir, meta)`

2. **`set_divio_types_selected()` (~lines 106-137)**:
   - Keep: validation (each type in `{"tutorial", "how-to", "reference", "explanation"}`)
   - Replace: I/O calls same as above

3. **`set_generators_configured()` (~lines 140-181)**:
   - Keep: validation (each generator has name/language/config_path, name in valid set)
   - Replace: I/O calls same as above

4. **`set_audit_metadata()` (~lines 184-219)**:
   - Keep: validation (coverage_percentage 0.0-1.0)
   - Replace: I/O calls same as above

5. For each function:
   - The `meta_file` parameter stays the same (callers pass Path to meta.json)
   - Derive `feature_dir = meta_file.parent` internally
   - Validation logic is completely unchanged
   - Only the file read/write mechanism changes

**Files**: `src/specify_cli/doc_state.py`
**Parallel?**: Yes — independent from T021 (different functions).

### Subtask T021 – Update composite writers

**Purpose**: Apply the new I/O pattern to the 4 composite writer functions.

**Steps**:
1. **`write_documentation_state()` (~lines 252-285)**:
   - Keep: validation (all 6 required fields present)
   - Replace: I/O calls
   - Note: This is the most important one — called by `initialize_*` and `update_*`

2. **`initialize_documentation_state()` (~line 319)**:
   - This calls `write_documentation_state()` — if T021.1 is done, this inherits the fix
   - Check if it also has its own direct I/O — if so, replace that too

3. **`update_documentation_state()` (~line 352)**:
   - Same as above — delegates to `write_documentation_state()`
   - Check for any direct I/O

4. **`ensure_documentation_state()` (~lines 392-394)**:
   - Migration/backward-compat function that adds missing state with defaults
   - Replace: I/O calls
   - Keep: default value logic

5. For each function, apply the same pattern as T020.

**Files**: `src/specify_cli/doc_state.py`
**Parallel?**: Yes — independent from T020 (different functions).

### Subtask T022 – Tests for doc_state formatting consistency

**Purpose**: Verify that all doc_state writes now produce consistent formatting matching the standard.

**Steps**:
1. Create tests in `tests/specify_cli/test_doc_state_formatting.py` (or extend existing doc_state tests).
2. Test cases:

   ```python
   def test_set_iteration_mode_standard_format(tmp_path):
       """set_iteration_mode() produces standard meta.json format."""
       feature_dir = tmp_path / "kitty-specs" / "001-test"
       feature_dir.mkdir(parents=True)
       # Create minimal valid meta.json
       meta = {
           "feature_number": "001", "slug": "001-test",
           "feature_slug": "001-test", "friendly_name": "Test",
           "mission": "documentation", "target_branch": "main",
           "created_at": "2026-01-01T00:00:00+00:00",
       }
       (feature_dir / "meta.json").write_text(
           json.dumps(meta, indent=2) + "\n"
       )

       meta_file = feature_dir / "meta.json"
       set_iteration_mode(meta_file, "gap_filling")

       content = meta_file.read_text()
       # Verify standard format
       assert content.endswith("\n")
       parsed = json.loads(content)
       # Verify sorted keys (check first few keys are alphabetical)
       keys = list(parsed.keys())
       assert keys == sorted(keys)
       # Verify documentation_state.iteration_mode
       assert parsed["documentation_state"]["iteration_mode"] == "gap_filling"

   def test_all_doc_state_setters_produce_sorted_keys(tmp_path):
       """Every doc_state write function produces sorted keys."""
       # Test each function and verify json keys are sorted
       # Functions: set_iteration_mode, set_divio_types_selected,
       #           set_generators_configured, set_audit_metadata,
       #           write_documentation_state, ensure_documentation_state

   def test_doc_state_preserves_unknown_fields(tmp_path):
       """doc_state writes don't strip unknown meta.json fields."""
       # Create meta.json with extra field "custom_field": "value"
       # Call any doc_state setter
       # Verify "custom_field" is still present
   ```

3. Run: `python -m pytest tests/specify_cli/test_doc_state_formatting.py -v`

**Files**: `tests/specify_cli/test_doc_state_formatting.py` (new file)

## Risks & Mitigations

- **Risk**: `doc_state.py` functions take `meta_file` (Path to meta.json) but `load_meta()`/`write_meta()` take `feature_dir` (parent directory).
  **Mitigation**: Derive `feature_dir = meta_file.parent` at the start of each function. Document this in a code comment.
- **Risk**: Some doc_state functions may handle missing meta.json differently (create vs error).
  **Mitigation**: Use `load_meta(feature_dir) or {}` to handle missing files the same way the current `json.load()` pattern does.

## Review Guidance

- Verify NO `json.dump(meta, f, ...)` or `json.dumps(meta, ...)` + `write_text()` calls remain in `doc_state.py`.
- Verify all validation logic is unchanged — only I/O is replaced.
- Check that `meta_file.parent` correctly derives the feature directory in all cases.
- Run existing doc_state tests to verify no regression.

## Activity Log

- 2026-03-18T20:21:07Z – system – lane=planned – Prompt created.
- 2026-03-18T21:03:26Z – coordinator – shell_pid=51576 – lane=doing – Assigned agent via workflow command
- 2026-03-18T21:12:07Z – coordinator – shell_pid=51576 – lane=for_review – Ready for review: All 8 doc_state write functions migrated to feature_metadata I/O, 47 tests passing (31 existing + 16 new formatting tests)
- 2026-03-18T21:12:24Z – codex – shell_pid=57780 – lane=doing – Started review via workflow command
- 2026-03-18T21:18:50Z – codex – shell_pid=57780 – lane=planned – Moved to planned
- 2026-03-18T21:19:03Z – coordinator – shell_pid=70918 – lane=doing – Started implementation via workflow command
- 2026-03-18T21:22:52Z – coordinator – shell_pid=70918 – lane=for_review – Fixed validation tolerance + reverted read scope creep (cycle 2/3)
- 2026-03-18T21:23:10Z – codex – shell_pid=75463 – lane=doing – Started review via workflow command
