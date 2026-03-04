---
work_package_id: WP05
title: Transitive Reference Resolver
lane: "done"
dependencies: [WP04]
subtasks:
- T019
- T020
- T021
- T022
phase: Phase 2 - Constitution Integration
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
- FR-006
- NFR-002
---

# Work Package Prompt: WP05 – Transitive Reference Resolver

## ⚠️ IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check `review_status`. If it says `has_feedback`, read `review_feedback` first.
- **Mark as acknowledged**: When you understand the feedback, update `review_status: acknowledged`.

---

## Implementation Command

```bash
spec-kitty implement WP05 --base WP04
```

---

## Objectives & Success Criteria

- Build a transitive reference resolver that follows directive → tactic → styleguide/toolguide chains
- Produce a `ResolvedReferenceGraph` containing the full transitive closure of artifacts
- Detect and break cycles without infinite loops
- Record unresolved references as `(type, id)` pairs

**Success metrics**:
- Given directives D1, D2 where D1 references tactic T1 and T1 references styleguide S1: resolve returns `{directives: [D1, D2], tactics: [T1], styleguides: [S1], unresolved: []}`
- Given a directive referencing a non-existent tactic: `unresolved: [("tactics", "missing-tactic")]`
- Given a cycle (T1 → T2 → T1): resolution terminates and includes both tactics once

## Context & Constraints

- **Spec**: FR-006 (Transitive Reference Resolution), NFR-002 (Cycle Safety)
- **Data model**: `data-model.md` — ResolvedReferenceGraph entity
- **Contracts**: `contracts.md` — Contract 3 (resolve_references_transitively)
- **Research**: `research.md` — R4 (transitive resolution algorithm)
- **Pattern to follow**: `src/doctrine/curation/engine.py` — `extract_refs()` (lines 150-181) and `depth_first_order()` (lines 184-225)
- **DoctrineService**: `src/doctrine/service.py` — provides `.directives`, `.tactics`, `.styleguides`, `.toolguides`, `.procedures` repository properties
- **Reference format in directives**: `tactic_refs: ["tactic-id-1", "tactic-id-2"]` (list of string IDs)
- **Reference format in tactics**: `references: [{type: "styleguide", id: "python-style"}, ...]` (list of typed references)

## Subtasks & Detailed Guidance

### Subtask T019 – Create ResolvedReferenceGraph Dataclass

**Purpose**: Define the output structure for transitive resolution — what artifacts were resolved and what was missing.

**Steps**:
1. Create new file `src/specify_cli/constitution/reference_resolver.py`
2. Define the dataclass:
   ```python
   from dataclasses import dataclass, field

   @dataclass(frozen=True)
   class ResolvedReferenceGraph:
       """Transitive closure of governance artifacts from a set of starting directives."""
       directives: list[str] = field(default_factory=list)
       tactics: list[str] = field(default_factory=list)
       styleguides: list[str] = field(default_factory=list)
       toolguides: list[str] = field(default_factory=list)
       procedures: list[str] = field(default_factory=list)
       unresolved: list[tuple[str, str]] = field(default_factory=list)
   ```
3. Lists preserve resolution order (depth-first traversal order)
4. `unresolved` contains `(artifact_type, artifact_id)` pairs for missing artifacts

**Files**: `src/specify_cli/constitution/reference_resolver.py` (NEW)
**Parallel?**: Yes — can start while T020-T022 are being designed

### Subtask T020 – Implement resolve_references_transitively()

**Purpose**: Core algorithm — depth-first traversal of directive → tactic → guide reference chains using DoctrineService repositories.

**Steps**:
1. In `src/specify_cli/constitution/reference_resolver.py`, implement:
   ```python
   from doctrine.service import DoctrineService

   def resolve_references_transitively(
       directive_ids: list[str],
       doctrine_service: DoctrineService,
   ) -> ResolvedReferenceGraph:
       """Resolve directive references transitively via DFS.
       
       Algorithm:
       1. Start from each directive ID
       2. Load directive from repository
       3. Extract tactic_refs from directive
       4. Load each tactic, extract its references
       5. Follow references to styleguides/toolguides
       6. Track visited set to break cycles
       7. Record unresolved references
       """
       visited: set[tuple[str, str]] = set()
       directives: list[str] = []
       tactics: list[str] = []
       styleguides: list[str] = []
       toolguides: list[str] = []
       procedures: list[str] = []
       unresolved: list[tuple[str, str]] = []
       
       def _walk(artifact_type: str, artifact_id: str) -> None:
           key = (artifact_type, artifact_id)
           if key in visited:
               return
           visited.add(key)
           
           if artifact_type == "directives":
               directive = _load_directive(artifact_id, doctrine_service)
               if directive is None:
                   unresolved.append(key)
                   return
               directives.append(artifact_id)
               # Follow tactic_refs
               for tactic_id in _extract_tactic_refs(directive):
                   _walk("tactics", tactic_id)
           
           elif artifact_type == "tactics":
               tactic = _load_tactic(artifact_id, doctrine_service)
               if tactic is None:
                   unresolved.append(key)
                   return
               tactics.append(artifact_id)
               # Follow references to guides
               for ref_type, ref_id in _extract_references(tactic):
                   _walk(ref_type, ref_id)
           
           elif artifact_type == "styleguides":
               guide = _load_styleguide(artifact_id, doctrine_service)
               if guide is None:
                   unresolved.append(key)
                   return
               styleguides.append(artifact_id)
           
           elif artifact_type == "toolguides":
               guide = _load_toolguide(artifact_id, doctrine_service)
               if guide is None:
                   unresolved.append(key)
                   return
               toolguides.append(artifact_id)
           
           elif artifact_type == "procedures":
               procedure = _load_procedure(artifact_id, doctrine_service)
               if procedure is None:
                   unresolved.append(key)
                   return
               procedures.append(artifact_id)
       
       for directive_id in directive_ids:
           _walk("directives", directive_id)
       
       return ResolvedReferenceGraph(
           directives=directives,
           tactics=tactics,
           styleguides=styleguides,
           toolguides=toolguides,
           procedures=procedures,
           unresolved=unresolved,
       )
   ```

2. The `_load_*` helper functions use the DoctrineService repositories:
   ```python
   def _load_directive(directive_id: str, service: DoctrineService):
       try:
           return service.directives.get(directive_id)
       except Exception:
           return None
   ```

3. The `_extract_tactic_refs` and `_extract_references` functions follow the patterns from `extract_refs()` in `engine.py`:
   - Directives have `tactic_refs: list[str]` (simple ID list)
   - Tactics have `references: list[dict]` with `{type: "styleguide", id: "python-style"}`

**Files**: `src/specify_cli/constitution/reference_resolver.py`
**Parallel?**: No — core algorithm, T021/T022 build on it

### Subtask T021 – Handle Unresolved References

**Purpose**: When a referenced artifact doesn't exist in the repository, record it as unresolved without failing.

**Steps**:
1. Already handled in the `_walk()` function (T020) — when `_load_*` returns None, append to `unresolved`
2. Add a helper method to check resolution completeness:
   ```python
   @property
   def is_complete(self) -> bool:
       """True when all references were resolved."""
       return len(self.unresolved) == 0
   ```
   (Add to `ResolvedReferenceGraph` dataclass — but since frozen, use a standalone function instead)
3. Verify that unresolved references don't block other branches of the traversal
4. Test case: directive D1 → tactic T1 (exists) + tactic T2 (missing) → T1 resolved, T2 in unresolved

**Files**: `src/specify_cli/constitution/reference_resolver.py`
**Parallel?**: No — integrated with T020

### Subtask T022 – Follow DoctrineService Repository Patterns

**Purpose**: Ensure the resolver correctly interacts with each DoctrineService repository's API.

**Steps**:
1. Investigate each repository's `get()` or lookup method:
   - `service.directives` → `DirectiveRepository` — check `get(id)` signature
   - `service.tactics` → `TacticRepository` — check how to get by ID
   - `service.styleguides` → `StyleguideRepository`
   - `service.toolguides` → `ToolguideRepository`
2. Use `rg "def get" src/doctrine/directives/repository.py src/doctrine/tactics/repository.py src/doctrine/styleguides/repository.py src/doctrine/toolguides/repository.py src/doctrine/procedures/repository.py` to find the API
3. Verify the attribute names for reference fields:
   - Directive model: `tactic_refs` or similar — check `src/doctrine/directives/models.py`
   - Tactic model: `references` or similar — check `src/doctrine/tactics/models.py`
4. Adapt `_extract_tactic_refs()` and `_extract_references()` to match actual model attributes
5. Handle both Pydantic models and raw dicts (some repositories may return either)

**Files**: `src/specify_cli/constitution/reference_resolver.py`, read from `src/doctrine/*/models.py`
**Parallel?**: No — informs T020 implementation

## Test Strategy

- Unit tests in `tests/specify_cli/constitution/test_reference_resolver.py` (NEW):
  - Simple chain: directive → tactic → styleguide → all resolved
  - Missing reference: directive → missing tactic → in unresolved
  - Cycle: tactic T1 references tactic T2, T2 references T1 → both resolved once, no infinite loop
  - Empty input: `[]` → empty graph
  - Multiple directives: D1, D2 sharing a tactic → tactic appears once
- Mock `DoctrineService` in tests (no disk I/O)

## Risks & Mitigations

- **Repository API differences**: Different repositories may have different `get()` signatures → investigate before implementing
- **Deep chains**: Could theoretically be slow → bounded by doctrine asset count (<100)
- **Model attribute naming**: `tactic_refs` vs `tactic_references` etc. → verify from actual model files

## Review Guidance

- Verify cycle detection: construct a cycle and assert termination
- Verify unresolved tracking: assert missing artifacts appear in `unresolved`
- Verify DFS order: directives before their tactics, tactics before their guides
- Run `pytest tests/specify_cli/constitution/test_reference_resolver.py -v`

## Activity Log

- 2026-03-08T10:13:04Z – system – lane=planned – Prompt created.
- 2026-03-09T04:29:04Z – claude-sonnet-4-6 – lane=done – Implementation complete and merged | Done override: History was rebased; branch ancestry tracking not applicable
