---
work_package_id: WP06
title: DoctrineService
<<<<<<< HEAD
lane: "done"
=======
lane: "for_review"
>>>>>>> 046-doctrine-artifact-domain-models-WP10
dependencies: [WP01, WP02, WP03, WP04]
base_branch: feature/agent-profile-implementation
base_commit: 90feaf5c16d01c9d6ac526ce2f72538bc9e17226
created_at: '2026-02-28T08:30:29.886028+00:00'
subtasks:
- T029
- T030
- T031
phase: Phase 1 - Foundation
assignee: ''
<<<<<<< HEAD
agent: claude-sonnet
shell_pid: '1519834'
review_status: "approved"
reviewed_by: "Stijn Dejongh"
review_feedback: "feedback://046-doctrine-artifact-domain-models/WP06/20260304T042932Z-6dcf5804.md"
=======
agent: "codex"
shell_pid: '112867'
review_status: ''
reviewed_by: ''
>>>>>>> 046-doctrine-artifact-domain-models-WP10
history:
- timestamp: '2026-02-26T04:36:22Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP06 – DoctrineService

## ⚠️ IMPORTANT: Review Feedback Status

- **Has review feedback?**: Check the `review_status` field above.

---

## Review Feedback

*[This section is empty initially.]*

---

## Objectives & Success Criteria

- Create `DoctrineService` as the lazy aggregation point for all doctrine repositories
- Repositories instantiated on first attribute access (lazy initialization — DD-005)
- Reuse existing `AgentProfileRepository` (FR-016)
- `DoctrineService().directives.list_all()` returns directives
- `DoctrineService().tactics.get("zombies-tdd")` returns a tactic
- `DoctrineService().agent_profiles.get("implementer")` reuses existing repository

## Context & Constraints

- **Depends on WP01-WP04**: All 5 repository types must exist
- **DD-005**: Lazy aggregation — don't load all repositories eagerly
- **Constructor**: `DoctrineService(shipped_root: Path | None = None, project_root: Path | None = None)`
- **Quickstart examples**: See `kitty-specs/046-doctrine-artifact-domain-models/quickstart.md` for API usage

## Subtasks & Detailed Guidance

### Subtask T029 – Create `src/doctrine/service.py`

- **Purpose**: Implement the DoctrineService aggregation point.
- **Steps**:
  1. Create `src/doctrine/service.py`
  2. Define `DoctrineService` class:
     ```python
     class DoctrineService:
         def __init__(
             self,
             shipped_root: Path | None = None,
             project_root: Path | None = None,
         ) -> None:
             self._shipped_root = shipped_root
             self._project_root = project_root
             self._cache: dict[str, Any] = {}
     ```
  3. Add lazy properties for each repository type:
     ```python
     @property
     def directives(self) -> DirectiveRepository:
         if "directives" not in self._cache:
             shipped = self._shipped_root / "directives" / "shipped" if self._shipped_root else None
             project = self._project_root / "directives" if self._project_root else None
             self._cache["directives"] = DirectiveRepository(
                 shipped_dir=shipped, project_dir=project
             )
         return self._cache["directives"]
     ```
  4. Repeat for: `tactics`, `styleguides`, `toolguides`, `paradigms`, `agent_profiles`
  5. For `agent_profiles`, import and use the existing `AgentProfileRepository` from `doctrine.agent_profiles`
  6. When `shipped_root` is `None`, each repository falls back to its own default (using `importlib.resources`)
- **Files**: `src/doctrine/service.py` (new, ~100 lines)
- **Notes**:
  - Use `@property` with `_cache` dict pattern (NOT `functools.cached_property` — it doesn't work well with `__init__` params)
  - Each repository handles its own default `shipped_dir` via `importlib.resources` when `None` is passed
  - The `shipped_root` parameter allows overriding all shipped directories at once (useful for testing)
  - When `shipped_root` is provided, derive each repository's shipped dir as `shipped_root / <type> / "shipped"`

### Subtask T030 – Update `src/doctrine/__init__.py`

- **Purpose**: Export `DoctrineService` from the doctrine package root.
- **Steps**:
  1. Read current `src/doctrine/__init__.py`
  2. Add import and export of `DoctrineService`
  3. Add to `__all__` if present
- **Files**: `src/doctrine/__init__.py` (update)
- **Notes**: Keep existing exports unchanged; only add `DoctrineService`

### Subtask T031 – Write ATDD/TDD tests

- **Purpose**: Test the DoctrineService aggregation and lazy loading.
- **Steps**:
  1. Create `tests/doctrine/test_service.py`
  2. **Acceptance tests**:
     - `DoctrineService().directives.list_all()` returns non-empty list
     - `DoctrineService().tactics.get("zombies-tdd")` returns a Tactic
     - `DoctrineService().styleguides.get("kitty-glossary-writing")` returns a Styleguide
     - `DoctrineService().toolguides.list_all()` returns non-empty list
     - `DoctrineService().paradigms.get("test-first")` returns a Paradigm
     - `DoctrineService().agent_profiles.list_all()` returns non-empty list
  3. **Lazy loading tests**:
     - Access `.directives` twice — same object returned (cached)
     - Access `.directives` without accessing `.tactics` — tactics repository not instantiated
  4. **Constructor tests**:
     - Default constructor (no args) works with shipped data
     - Custom `shipped_root` overrides shipped directories
     - Custom `project_root` enables project overrides
  5. **Cross-repository test**:
     - Load a directive, extract `tactic_refs`, resolve each via `service.tactics.get()`
     - Verify resolved tactics exist (at least for `test-first` directive)
- **Files**: `tests/doctrine/test_service.py` (new, ~120 lines)

## Test Strategy

```bash
pytest tests/doctrine/test_service.py -v
mypy src/doctrine/service.py --strict
```

## Risks & Mitigations

- **Circular imports**: `service.py` imports from all subpackages — ensure no subpackage imports from `service.py`
- **AgentProfileRepository API differences**: Verify that `AgentProfileRepository` constructor signature is compatible with the pattern used for other repositories

## Review Guidance

- Verify lazy loading — repositories should NOT be instantiated until accessed
- Verify `agent_profiles` reuses existing repository (not a new implementation)
- Verify cross-repository resolution works (directive → tactic via tactic_refs)

## Activity Log

- 2026-02-26T04:36:22Z – system – lane=planned – Prompt created.

---

### Implementation Command

Depends on WP01-WP04 (use latest completed as base):
```bash
spec-kitty implement WP06 --base WP01
```
Then merge WP02, WP03, WP04 branches:
```bash
cd .worktrees/046-doctrine-artifact-domain-models-WP06/
git merge feature/agent-profile-implementation-WP02
git merge feature/agent-profile-implementation-WP03
git merge feature/agent-profile-implementation-WP04
```
- 2026-02-28T08:30:29Z – codex – shell_pid=112867 – lane=doing – Assigned agent via workflow command
- 2026-02-28T08:33:48Z – codex – shell_pid=112867 – lane=for_review – Ready for review: directives 001-010 enriched and doctrine checks passing
<<<<<<< HEAD
- 2026-03-04T04:27:02Z – claude-sonnet – shell_pid=1519834 – lane=doing – Started review via workflow command
- 2026-03-04T04:29:32Z – claude-sonnet – shell_pid=1519834 – lane=planned – Moved to planned
=======
>>>>>>> 046-doctrine-artifact-domain-models-WP10
- 2026-03-04T04:45:31Z – claude-sonnet – shell_pid=1519834 – lane=done – Deliverables present via WP05 branch merge: service.py (lazy @property +_cache), **init**.py export, 4 tests passing. DoctrineService fully aligned with Doctrine Catalog Loader pattern. | Done override: DoctrineService was implemented in the WP05 codex branch and merged via WP10. All 3 deliverables (service.py, **init**.py export, test_service.py) are present and tested.
