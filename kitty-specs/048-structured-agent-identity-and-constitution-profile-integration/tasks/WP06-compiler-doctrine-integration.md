---
work_package_id: WP06
title: Compiler Integration with DoctrineService
lane: "done"
dependencies:
- WP04
- WP05
subtasks:
- T023
- T024
- T025
- T026
- T027
phase: Phase 3 - Compiler Wiring
assignee: ''
agent: "claude-sonnet-4-6"
shell_pid: '197461'
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
- FR-007
- FR-009
- NFR-003
- C-003
---

# Work Package Prompt: WP06 – Compiler Integration with DoctrineService

## ⚠️ IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check `review_status`. If it says `has_feedback`, read `review_feedback` first.
- **Mark as acknowledged**: When you understand the feedback, update `review_status: acknowledged`.

---

## Implementation Command

```bash
spec-kitty implement WP06 --base WP05
```

---

## Objectives & Success Criteria

- Inject `DoctrineService` into the constitution compiler as an optional parameter
- Replace raw YAML scanning with typed repository queries when DoctrineService is available
- Wire transitive reference resolution into the compilation pipeline
- Preserve the legacy YAML scanning fallback path with diagnostic warning (C-003)

**Success metrics**:
- `compile_constitution(doctrine_service=service)` uses repository queries and transitive resolution
- `compile_constitution(doctrine_service=None)` falls back to YAML scanning and emits diagnostic
- Output references include transitively resolved tactics, styleguides, toolguides, and procedures
- All existing compiler tests pass without modification when `doctrine_service=None`

## Context & Constraints

- **Spec**: FR-007 (DoctrineService-Backed Compiler), FR-009 (Graceful Fallback), C-003 (Compiler Fallback Required)
- **Contracts**: `contracts.md` — Contract 4 (resolve_governance_for_profile)
- **Research**: `research.md` — R5 (compiler fallback path)
- **Dependency**: WP04 (expanded catalog), WP05 (transitive resolver)
- **Key file**: `src/specify_cli/constitution/compiler.py` — `compile_constitution()` at line 52, `_index_yaml_assets()` at line 264, `_load_yaml_asset()` at line 280
- **Key file**: `src/doctrine/service.py` — `DoctrineService` with 7 repository properties
- **Pattern**: `_build_references()` currently creates `ConstitutionReference` objects from paradigms and directives only
- **Tools**: Use `rg` (ripgrep) for all code searches — do NOT use `grep`. Example: `rg "def _build_references" src/specify_cli/constitution/`

## Subtasks & Detailed Guidance

### Subtask T023 – Add doctrine_service Parameter

**Purpose**: Make DoctrineService available to the compiler without breaking existing callers.

**Steps**:
1. In `src/specify_cli/constitution/compiler.py`, update `compile_constitution()` signature (~line 52):
   ```python
   def compile_constitution(
       *,
       mission: str,
       interview: ConstitutionInterview,
       template_set: str | None = None,
       doctrine_catalog: DoctrineCatalog | None = None,
       doctrine_service: DoctrineService | None = None,  # NEW
   ) -> CompiledConstitution:
   ```
2. Add import: `from doctrine.service import DoctrineService`
3. Use lazy import to avoid import cycles if needed:
   ```python
   if TYPE_CHECKING:
       from doctrine.service import DoctrineService
   ```

**Files**: `src/specify_cli/constitution/compiler.py`
**Parallel?**: Yes — can proceed alongside T026

### Subtask T024 – DoctrineService-Backed Artifact Loading

**Purpose**: When DoctrineService is provided, use typed repository queries instead of `_index_yaml_assets()`.

**Steps**:
1. After the catalog and diagnostics setup (~line 62), add a branch:
   ```python
   if doctrine_service is not None:
       # Use DoctrineService for artifact loading
       # This replaces _index_yaml_assets() calls
       directive_models = {
           d.id: d for d in doctrine_service.directives.list_all()
       }
       tactic_models = {
           t.id: t for t in doctrine_service.tactics.list_all()
       }
       # ... similar for styleguides, toolguides
   else:
       # Legacy path: _index_yaml_assets() (existing code)
       diagnostics.append(
           "DoctrineService unavailable; using YAML scanning fallback"
       )
   ```
2. Check each repository for a `list_all()` or equivalent method:
   - Use `rg "def list" src/doctrine/directives/repository.py` to find the API
3. If repositories don't have `list_all()`, iterate over catalog IDs and call `get()` for each
4. Store loaded models in dicts keyed by ID for lookup during reference building

**Files**: `src/specify_cli/constitution/compiler.py`
**Parallel?**: No — depends on T023

### Subtask T025 – Wire Transitive Resolution into _build_references()

**Purpose**: When using DoctrineService, replace the current flat reference list with transitively resolved references.

**Steps**:
1. Locate `_build_references()` in compiler.py
2. When `doctrine_service` is available, use the transitive resolver:
   ```python
   from specify_cli.constitution.reference_resolver import resolve_references_transitively
   
   if doctrine_service is not None:
       graph = resolve_references_transitively(
           directive_ids=selected_directives,
           doctrine_service=doctrine_service,
       )
       # Build ConstitutionReference objects from graph
       references = []
       for d_id in graph.directives:
           references.append(ConstitutionReference(type="directive", id=d_id, ...))
       for t_id in graph.tactics:
           references.append(ConstitutionReference(type="tactic", id=t_id, ...))
       for s_id in graph.styleguides:
           references.append(ConstitutionReference(type="styleguide", id=s_id, ...))
       for tg_id in graph.toolguides:
           references.append(ConstitutionReference(type="toolguide", id=tg_id, ...))
       for p_id in graph.procedures:
           references.append(ConstitutionReference(type="procedure", id=p_id, ...))
       
       # Report unresolved
       for ref_type, ref_id in graph.unresolved:
           diagnostics.append(f"Unresolved reference: {ref_type}/{ref_id}")
   ```
3. Preserve the existing `_build_references()` for the fallback path
4. Ensure `ConstitutionReference` type can handle the new reference types (tactic, styleguide, toolguide, procedure)

**Files**: `src/specify_cli/constitution/compiler.py`
**Parallel?**: No — depends on T024

### Subtask T026 – Implement Fallback Path with Diagnostic Warning

**Purpose**: Ensure the compiler works without DoctrineService, emitting a single diagnostic warning.

**Steps**:
1. The fallback is the existing code path — no new code needed, just guard it:
   ```python
   if doctrine_service is None:
       diagnostics.append(
           "DoctrineService unavailable; using YAML scanning fallback. "
           "Profile-aware compilation requires DoctrineService."
       )
       # ... existing _index_yaml_assets() / _load_yaml_asset() code ...
   ```
2. Verify that `CompiledConstitution.diagnostics` includes the warning
3. Test: call `compile_constitution(doctrine_service=None)` → check diagnostics list

**Files**: `src/specify_cli/constitution/compiler.py`
**Parallel?**: Yes — can proceed alongside T023

### Subtask T027 – Update _sanitize_catalog_selection for New Types

**Purpose**: If the compiler validates selections against the catalog, extend validation for tactics, styleguides, etc.

**Steps**:
1. Check if `_sanitize_catalog_selection()` is called for any of the new artifact types
2. When `doctrine_service` is available, the transitive resolver handles validation (unresolved tracking)
3. For the fallback path, add sanitization calls if the interview exposes new selection fields:
   ```python
   # Only needed if interview allows selecting tactics/styleguides directly
   # Currently, these are resolved transitively from directives
   # May be a no-op in initial implementation
   ```
4. Ensure the expanded `DoctrineCatalog` (from WP04) is used consistently

**Files**: `src/specify_cli/constitution/compiler.py`
**Parallel?**: No — final integration step

## Test Strategy

- Existing tests must pass with `doctrine_service=None` (fallback path)
- New tests in `tests/specify_cli/constitution/test_compiler.py`:
  - Mock `DoctrineService` with known directives/tactics/guides → verify transitive output
  - `doctrine_service=None` → verify diagnostic warning emitted
  - Empty directive selection → no crash, empty references
  - Unresolved reference → appears in diagnostics
- Regression: `pytest tests/specify_cli/constitution/ -v`

## Risks & Mitigations

- **Compiler complexity**: File is ~300 lines with many helpers → make changes surgical, well-guarded
- **Import cycles**: `compiler.py` importing from `doctrine.service` → use `TYPE_CHECKING` guard
- **Repository API uncertainty**: Verify each repository's API before implementing T024

## Review Guidance

- Verify fallback path is identical to existing behaviour
- Verify diagnostic warning is emitted exactly once on fallback
- Verify transitive resolution output appears in compiled constitution
- Verify no import cycles between `specify_cli.constitution` and `doctrine`
- Run `pytest tests/specify_cli/constitution/test_compiler.py -v` — 0 failures

## Activity Log

- 2026-03-08T10:13:04Z – system – lane=planned – Prompt created.
- 2026-03-09T04:36:32Z – unknown – lane=for_review – T023-T027 complete, existing tests pass, diagnostic warning implemented
- 2026-03-09T04:36:55Z – claude-sonnet-4-6 – shell_pid=197461 – lane=doing – Started review via workflow command
- 2026-03-09T04:37:36Z – claude-sonnet-4-6 – shell_pid=197461 – lane=done – Review passed: T023-T027 complete, 6/6 tests passing, ruff clean, mypy clean. Fallback diagnostic correct, TYPE_CHECKING guard prevents import cycle.
