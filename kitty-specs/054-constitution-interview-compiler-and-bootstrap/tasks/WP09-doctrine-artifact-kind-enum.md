---
work_package_id: WP09
title: Extract Canonical ArtifactKind Enum and Consolidate Repetition
lane: "done"
dependencies:
- WP05
base_branch: feature/agent-profile-implementation
base_commit: 80f7975ea02e8bbb534b30d862315915a01f61e6
created_at: '2026-03-10T05:09:59.027730+00:00'
subtasks:
- T043
- T044
- T045
- T046
- T047
phase: Phase 3 - Doctrine Consolidation
assignee: ''
agent: copilot
shell_pid: '582404'
review_status: "approved"
reviewed_by: "Stijn Dejongh"
review_feedback: feedback://054-constitution-interview-compiler-and-bootstrap/WP09/20260310T065534Z-bd7c1754.md
history:
- timestamp: '2026-03-10T05:00:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated manually
requirement_refs: []
---

# Work Package Prompt: WP09 - Extract Canonical ArtifactKind Enum and Consolidate Repetition

## ⚠️ IMPORTANT: Review Feedback Status

- If review feedback exists, address it before treating this WP as complete.

---

## Review Feedback

*[Empty initially.]*

---

## Objectives & Success Criteria

- A single `ArtifactKind` `StrEnum` in `src/doctrine/artifact_kinds.py` defines all doctrine artifact types once.
- The enum provides derived properties: `plural` (e.g. `"directives"`), `glob_pattern` (e.g. `"*.directive.yaml"`), and `singular` (e.g. `"directive"`).
- The three duplicate reference-type enums (`DirectiveReferenceType`, `ReferenceType`, `ProcedureReferenceType`) are replaced by importing `ArtifactKind`.
- `ARTIFACT_TYPES` in `curation/state.py` is replaced by deriving from `ArtifactKind`.
- `_GLOB_PATTERNS` in `curation/engine.py` is replaced by deriving from `ArtifactKind.glob_pattern`.
- `_REF_TYPE_MAP` in `reference_resolver.py` is replaced by deriving from `ArtifactKind`.
- All existing tests continue to pass.

## Context & Constraints

- The doctrine codebase currently has **10+ locations** that independently enumerate artifact types, with inconsistent coverage and naming.
- Key inconsistencies to resolve:
  - `profiles` vs `agent_profiles` — standardize on `agent_profile` (singular enum value)
  - Three near-identical `ReferenceType` enums in `directives/models.py`, `tactics/models.py`, `procedures/models.py`
  - `ARTIFACT_TYPES` tuple in `curation/state.py` missing `agent_profiles`
  - `_REF_TYPE_MAP` in `reference_resolver.py` incomplete (missing `paradigm`)
  - `ReferenceType` (tactics) missing `paradigm` value

## Subtasks & Detailed Guidance

### Subtask T043 - Create `src/doctrine/artifact_kinds.py` with `ArtifactKind` enum

- **Purpose**: Single source of truth for all doctrine artifact types.
- **Steps**:
  1. Create `src/doctrine/artifact_kinds.py`.
  2. Define `ArtifactKind(StrEnum)` with values: `DIRECTIVE = "directive"`, `TACTIC = "tactic"`, `STYLEGUIDE = "styleguide"`, `TOOLGUIDE = "toolguide"`, `PARADIGM = "paradigm"`, `PROCEDURE = "procedure"`, `AGENT_PROFILE = "agent_profile"`, `TEMPLATE = "template"`.
  3. Add derived properties:
     - `plural` → `"directives"`, `"tactics"`, ..., `"agent_profiles"`, `"templates"`
     - `glob_pattern` → `"*.directive.yaml"`, etc. (return `""` for `TEMPLATE` which has no glob)
     - A classmethod or helper to go from plural form back to the enum value.
  4. Export from `src/doctrine/__init__.py`.
- **Files**: `src/doctrine/artifact_kinds.py`, `src/doctrine/__init__.py`
- **Notes**: Keep this module zero-dependency within doctrine (no imports from specify_cli).

### Subtask T044 - Replace the three duplicate ReferenceType enums

- **Purpose**: Eliminate the three near-identical enums that drift independently.
- **Steps**:
  1. In `src/doctrine/directives/models.py`, remove `DirectiveReferenceType` and replace usage with `ArtifactKind`.
  2. In `src/doctrine/tactics/models.py`, remove `ReferenceType` and replace usage with `ArtifactKind`.
  3. In `src/doctrine/procedures/models.py`, remove `ProcedureReferenceType` and replace usage with `ArtifactKind`.
  4. Update `DirectiveReference`, `TacticReference`, `ProcedureReference` model fields to use `ArtifactKind` as the type annotation.
  5. Verify Pydantic validation still works with `ArtifactKind` as a `StrEnum`.
- **Files**: `src/doctrine/directives/models.py`, `src/doctrine/tactics/models.py`, `src/doctrine/procedures/models.py`
- **Notes**: The YAML files store string values like `"directive"`, `"tactic"` — these must still deserialize correctly via Pydantic.

### Subtask T045 - Replace `ARTIFACT_TYPES` and `_GLOB_PATTERNS` constants

- **Purpose**: Derive these from the enum instead of maintaining separate lists.
- **Steps**:
  1. In `src/doctrine/curation/state.py`, replace `ARTIFACT_TYPES` with a derived tuple from `ArtifactKind` (excluding `TEMPLATE`).
  2. In `src/doctrine/curation/engine.py`, replace `_GLOB_PATTERNS` dict with a derived dict from `ArtifactKind.glob_pattern`.
  3. Ensure `agent_profiles` is now included (fixing the current gap).
- **Files**: `src/doctrine/curation/state.py`, `src/doctrine/curation/engine.py`

### Subtask T046 - Replace `_REF_TYPE_MAP` in reference_resolver

- **Purpose**: Derive the singular-to-plural mapping from the enum.
- **Steps**:
  1. In `src/specify_cli/constitution/reference_resolver.py`, replace `_REF_TYPE_MAP` with a mapping derived from `ArtifactKind`.
  2. This automatically fixes the missing `paradigm` → `paradigms` mapping.
- **Files**: `src/specify_cli/constitution/reference_resolver.py`

### Subtask T047 - Add tests and verify no regressions

- **Purpose**: Lock in the new enum behavior and verify all consuming code still works.
- **Steps**:
  1. Add unit tests for `ArtifactKind` properties (`plural`, `glob_pattern`, round-trip from plural).
  2. Run the full test suite to verify no regressions from the reference-type enum replacement.
  3. Verify Pydantic model deserialization still works for directives, tactics, procedures YAML files.
- **Files**: `tests/doctrine/test_artifact_kinds.py`, plus existing test suites

## Test Strategy

- `pytest -q tests/doctrine/test_artifact_kinds.py`
- `pytest -q tests/` (full suite — verify no regressions)
- `ruff check src/doctrine/ src/specify_cli/constitution/`

## Risks & Mitigations

- Pydantic models use `StrEnum` for validation; verify that `ArtifactKind` as a `StrEnum` serializes/deserializes identically to the old per-model enums.
- The `TEMPLATE` kind exists in reference enums but has no repository or shipped directory; keep it in the enum but exclude it from iteration helpers like `ARTIFACT_TYPES`.

## Review Guidance

- Confirm all three old reference-type enums are fully removed, not just aliased.
- Confirm `ARTIFACT_TYPES` now includes `agent_profiles`.
- Confirm `_REF_TYPE_MAP` now includes `paradigm`.
- Confirm no YAML deserialization regressions in directive/tactic/procedure loading.

## Activity Log

- 2026-03-10T05:00:00Z - system - lane=planned - Prompt created.
- 2026-03-10T06:50:19Z – unknown – shell_pid=539643 – lane=for_review – ArtifactKind enum extracted, all 3 duplicate enums replaced, ARTIFACT_TYPES fixed to include agent_profiles, _REF_TYPE_MAP fixed for paradigm
- 2026-03-10T06:50:46Z – copilot – shell_pid=582404 – lane=doing – Started review via workflow command
- 2026-03-10T06:55:34Z – copilot – shell_pid=582404 – lane=planned – Changes requested: remove backward-compat aliases from **init**.py files — spec requires full removal, not aliasing
- 2026-03-10T07:02:48Z – copilot – shell_pid=582404 – lane=for_review – Removed backward-compat aliases from all three **init**.py files; tests pass
- 2026-03-10T07:03:37Z – copilot – shell_pid=582404 – lane=done – Review passed after rework: aliases fully removed, 708 tests pass, ruff clean.
