---
work_package_id: WP10
title: Migrate Remaining Consumers to ArtifactKind Enum
lane: "done"
dependencies:
- WP09
base_branch: 054-constitution-interview-compiler-and-bootstrap-WP09
base_commit: 1f992162c8bd9e1ca200e2e5a81e13deb62710d1
created_at: '2026-03-10T07:03:37.828820+00:00'
subtasks:
- T048
- T049
- T050
- T051
phase: Phase 3 - Doctrine Consolidation
assignee: ''
agent: ''
shell_pid: '599084'
review_status: "approved"
reviewed_by: "Stijn Dejongh"
history:
- timestamp: '2026-03-10T05:00:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated manually
requirement_refs: []
---

# Work Package Prompt: WP10 - Migrate Remaining Consumers to ArtifactKind Enum

## ⚠️ IMPORTANT: Review Feedback Status

- If review feedback exists, address it before treating this WP as complete.

---

## Review Feedback

*[Empty initially.]*

---

## Objectives & Success Criteria

- `ActionIndex` fields are validated/typed against `ArtifactKind` values.
- `DoctrineCatalog` field names are consistent with `ArtifactKind.plural` (e.g. `agent_profiles` not `profiles`).
- `DoctrineService` property names align with `ArtifactKind.plural`.
- `GovernanceResolution` and `ResolvedReferenceGraph` field names are consistent.
- The doctrine CLI help text derives artifact type names from the enum.
- All naming inconsistencies identified in the audit are resolved.

## Context & Constraints

- WP09 introduces `ArtifactKind` and replaces the core duplicate enums/constants.
- This WP handles the remaining consumer-side alignment: dataclass field naming, service properties, catalog fields, and CLI surfaces.
- Some renames (e.g. `profiles` → `agent_profiles` in `DoctrineCatalog`) are breaking changes within this codebase — update all callers.

## Subtasks & Detailed Guidance

### Subtask T048 - Align `DoctrineCatalog` and catalog loading

- **Purpose**: Make catalog field names consistent with `ArtifactKind.plural`.
- **Steps**:
  1. In `src/specify_cli/constitution/catalog.py`, rename `profiles` field to `agent_profiles` in `DoctrineCatalog`.
  2. Update `load_doctrine_catalog()` and `_load_yaml_id_catalog_with_presence()` calls that reference `profiles`.
  3. Update all callers of `DoctrineCatalog.profiles` across the codebase.
- **Files**: `src/specify_cli/constitution/catalog.py`, callers
- **Notes**: grep for `.profiles` to find all callers. The `domains_present` set already uses `"profiles"` — update to `"agent_profiles"`.

### Subtask T049 - Align `ActionIndex`, `GovernanceResolution`, and `ResolvedReferenceGraph`

- **Purpose**: Ensure field names and iteration match the canonical enum.
- **Steps**:
  1. Consider whether `ActionIndex` should store `ArtifactKind` keys or remain string-typed — string-typed is fine as long as the field names match `ArtifactKind.plural`.
  2. Verify `GovernanceResolution` field names match (they already do for the most part).
  3. Verify `ResolvedReferenceGraph` field names match.
  4. Add a helper or property on `ActionIndex` that returns artifact IDs by `ArtifactKind`, for cleaner iteration in `context.py`.
- **Files**: `src/doctrine/missions/action_index.py`, `src/specify_cli/constitution/resolver.py`, `src/specify_cli/constitution/reference_resolver.py`

### Subtask T050 - Update doctrine CLI help text

- **Purpose**: Derive the list of valid artifact types from `ArtifactKind` in CLI help.
- **Steps**:
  1. In `src/specify_cli/cli/commands/doctrine.py`, replace hardcoded artifact type lists in help text with values derived from `ArtifactKind`.
- **Files**: `src/specify_cli/cli/commands/doctrine.py`

### Subtask T051 - Run full test suite and fix regressions

- **Purpose**: Verify the field renames don't break anything.
- **Steps**:
  1. Run full test suite.
  2. Fix any test failures from the `profiles` → `agent_profiles` rename or other alignment changes.
  3. Run ruff and mypy checks.
- **Files**: Various test files

## Test Strategy

- `pytest -q tests/` (full suite)
- `ruff check src/`
- `mypy src/specify_cli/constitution/catalog.py src/doctrine/missions/action_index.py --ignore-missing-imports`

## Risks & Mitigations

- The `profiles` → `agent_profiles` rename in `DoctrineCatalog` touches multiple callers; use a thorough grep to catch them all.
- Some downstream code may use attribute access patterns that don't show up in simple string searches.

## Review Guidance

- Confirm `DoctrineCatalog.profiles` no longer exists (fully renamed).
- Confirm `domains_present` uses `"agent_profiles"` not `"profiles"`.
- Confirm CLI help text no longer hardcodes artifact type lists.

## Activity Log

- 2026-03-10T05:00:00Z - system - lane=planned - Prompt created.
- 2026-03-10T07:13:43Z – unknown – shell_pid=599084 – lane=for_review – DoctrineCatalog.profiles renamed to agent_profiles, CLI help derives from ArtifactKind, all tests pass
- 2026-03-10T07:17:00Z – unknown – shell_pid=599084 – lane=done – Moved to done
