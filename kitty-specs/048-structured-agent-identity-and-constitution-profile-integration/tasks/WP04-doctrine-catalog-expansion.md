---
work_package_id: WP04
title: DoctrineCatalog Expansion
lane: "done"
dependencies: []
subtasks:
- T015
- T016
- T017
- T018
phase: Phase 1 - Foundation
assignee: ''
agent: "claude-sonnet-4-6"
shell_pid: ''
review_status: "approved"
reviewed_by: "Stijn Dejongh"
review_feedback: ''
history:
- timestamp: '2026-03-08T10:13:04Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
requirement_refs:
- FR-005
---

# Work Package Prompt: WP04 – DoctrineCatalog Expansion

## ⚠️ IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check `review_status`. If it says `has_feedback`, read `review_feedback` first.
- **Mark as acknowledged**: When you understand the feedback, update `review_status: acknowledged`.

---

## Implementation Command

```bash
spec-kitty implement WP04
```

No `--base` flag needed (no dependencies).

---

## Objectives & Success Criteria

- Expand `DoctrineCatalog` to include all doctrine artifact types: tactics, styleguides, toolguides, procedures, and agent profiles
- Reuse the proven `_load_yaml_id_catalog()` function for loading each new type
- Handle the profile-specific `profile-id` field (distinct from the standard `id` field)

**Success metrics**:
- `DoctrineCatalog` has 8 frozenset fields (3 existing + 5 new)
- `load_doctrine_catalog()` populates all 8 fields from a doctrine directory
- Empty directories result in empty frozensets (no errors)
- Profiles loaded using `profile-id` field from `*.agent.yaml` files

## Context & Constraints

- **Spec**: FR-005 (Expanded Doctrine Catalog)
- **Data model**: `data-model.md` — DoctrineCatalog (extended) section
- **Research**: `research.md` — R3 (catalog expansion loading)
- **Key file**: `src/specify_cli/constitution/catalog.py` — current 3-field DoctrineCatalog with `_load_yaml_id_catalog()` helper
- **Existing pattern**: `_load_yaml_id_catalog(directory, pattern)` returns `set[str]` by scanning glob and extracting `id` field
- **Profile convention**: Agent profiles use `profile-id` field, not `id` — see `src/doctrine/agent_profiles/profile.py`

## Subtasks & Detailed Guidance

### Subtask T015 – Add New Frozenset Fields to DoctrineCatalog

**Purpose**: Extend the dataclass to represent the full doctrine asset inventory.

**Steps**:
1. In `src/specify_cli/constitution/catalog.py`, update the dataclass (~lines 17-24):
   ```python
   @dataclass(frozen=True)
   class DoctrineCatalog:
       """Deterministic doctrine catalog derived from on-disk doctrine assets."""
       paradigms: frozenset[str]
       directives: frozenset[str]
       tactics: frozenset[str]           # NEW
       styleguides: frozenset[str]       # NEW
       toolguides: frozenset[str]        # NEW
       procedures: frozenset[str]        # NEW
       profiles: frozenset[str]          # NEW
       template_sets: frozenset[str]
   ```
2. Ensure field order: group existing fields, then new fields, then template_sets
3. All new fields should be documented with their artifact YAML pattern

**Files**: `src/specify_cli/constitution/catalog.py` (~line 17)
**Parallel?**: Yes — can proceed in parallel with T016

### Subtask T016 – Update load_doctrine_catalog()

**Purpose**: Populate the 5 new fields by calling `_load_yaml_id_catalog()` with appropriate glob patterns.

**Steps**:
1. In `load_doctrine_catalog()` (~lines 26-40), add calls for each new type:
   ```python
   def load_doctrine_catalog(doctrine_dir: Path | None = None) -> DoctrineCatalog:
       base = doctrine_dir or _default_doctrine_dir()
       return DoctrineCatalog(
           paradigms=frozenset(sorted(_load_yaml_id_catalog(base / "paradigms", "*.paradigm.yaml"))),
           directives=frozenset(sorted(_load_yaml_id_catalog(base / "directives", "*.directive.yaml"))),
           tactics=frozenset(sorted(_load_yaml_id_catalog(base / "tactics", "*.tactic.yaml"))),
           styleguides=frozenset(sorted(_load_yaml_id_catalog(base / "styleguides", "*.styleguide.yaml"))),
           toolguides=frozenset(sorted(_load_yaml_id_catalog(base / "toolguides", "*.toolguide.yaml"))),
           procedures=frozenset(sorted(_load_yaml_id_catalog(base / "procedures", "*.procedure.yaml"))),
           profiles=frozenset(sorted(_load_yaml_id_catalog(
               base / "agent_profiles", "*.agent.yaml", id_field="profile-id"
           ))),
           template_sets=frozenset(sorted(_load_template_sets(base))),
       )
   ```
2. Note: profiles need special handling — see T018

**Files**: `src/specify_cli/constitution/catalog.py`
**Parallel?**: Yes — can proceed in parallel with T015

### Subtask T017 – Update Catalog Tests

**Purpose**: Ensure expanded catalog fields are properly tested.

**Steps**:
1. In `tests/specify_cli/constitution/test_catalog.py`:
   - Update existing tests to include new fields in assertions
   - Add test: directory with all artifact types → all fields populated
   - Add test: empty directories → all fields empty frozensets
   - Add test: missing directories → empty frozensets (no errors)
2. Create fixture directories with sample YAML files for tactics, styleguides, toolguides, procedures, profiles
3. Each sample YAML should have an `id:` field (or `profile-id:` for profiles)

**Files**: `tests/specify_cli/constitution/test_catalog.py`
**Parallel?**: No — depends on T015/T016

### Subtask T018 – Handle Profiles with profile-id Field

**Purpose**: Agent profile YAML files use `profile-id` instead of `id` — ensure `_load_yaml_id_catalog()` can handle this.

**Steps**:
1. Examine `_load_yaml_id_catalog()` (~lines 65-88):
   - Currently looks for `data.get("id")` field
   - Falls back to filename stem
2. Option A (preferred): Add `id_field` parameter:
   ```python
   def _load_yaml_id_catalog(
       directory: Path,
       pattern: str,
       id_field: str = "id",
   ) -> set[str]:
       # ... existing logic ...
       yaml_id = data.get(id_field) or data.get("id")
       # ... fallback to filename stem ...
   ```
3. Option B: Let profiles fall back to filename stem (less precise)
4. Verify with a sample `*.agent.yaml` file that has `profile-id: reviewer`

**Files**: `src/specify_cli/constitution/catalog.py` (modify `_load_yaml_id_catalog`)
**Parallel?**: No — needed by T016

## Test Strategy

- Existing tests must still pass with new fields added (empty frozensets for dirs that don't exist)
- New tests: populated doctrine dir → verify each field has expected IDs
- Edge case: YAML with missing `id` field → filename stem fallback
- Edge case: profile with `profile-id` field → correctly extracted
- Regression: `pytest tests/specify_cli/constitution/test_catalog.py -v`

## Risks & Mitigations

- **Breaking existing callers**: Adding fields to a frozen dataclass may break code that constructs `DoctrineCatalog` with positional args → search for all constructors: `rg "DoctrineCatalog(" src/ tests/`
- **Profile ID field**: `profile-id` uses hyphen, not underscore → ensure YAML parsing handles this
- **Directory structure**: Doctrine assets may not always be in expected subdirectories → `_load_yaml_id_catalog` already returns empty set for missing dirs

## Review Guidance

- Verify all 8 fields are populated correctly from a full doctrine directory
- Verify `_load_yaml_id_catalog()` `id_field` parameter works for profiles
- Check no existing code breaks from the dataclass expansion
- Run `pytest tests/specify_cli/constitution/test_catalog.py -v` — 0 failures

## Activity Log

- 2026-03-08T10:13:04Z – system – lane=planned – Prompt created.
- 2026-03-09T04:29:03Z – claude-sonnet-4-6 – lane=done – Implementation complete and merged | Done override: History was rebased; branch ancestry tracking not applicable
