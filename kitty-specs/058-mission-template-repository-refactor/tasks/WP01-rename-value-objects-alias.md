---
work_package_id: WP01
title: Rename Class + Value Objects + Alias
lane: "done"
dependencies: []
requirement_refs:
- FR-001
- FR-013
- FR-014
- FR-015
- FR-016
- NFR-001
- NFR-002
- C-001
planning_base_branch: feature/agent-profile-implementation
merge_target_branch: feature/agent-profile-implementation
branch_strategy: Planning artifacts for this feature were generated on feature/agent-profile-implementation. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feature/agent-profile-implementation unless the human explicitly redirects the landing branch.
base_branch: feature/agent-profile-implementation
base_commit: aef99db5f1041002957292eeda0714ece7ef4e1f
created_at: '2026-03-28T04:42:52.035837+00:00'
subtasks:
- T001
- T002
- T003
- T004
- T005
- T016
phase: Phase 1 - New API Foundation
assignee: ''
agent: claude-opus-4-6
shell_pid: '21171'
review_status: "approved"
reviewed_by: "Stijn Dejongh"
approved_by: "Stijn Dejongh"
history:
- timestamp: '2026-03-27T04:37:32Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
agent_profile: implementer
---

# Work Package Prompt: WP01 – Rename Class + Value Objects + Alias

## Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.
- **You must address all feedback** before your work is complete.
- **Mark as acknowledged**: When you understand the feedback and begin addressing it, update `review_status: acknowledged` in the frontmatter.

---

## Review Feedback

> **Populated by `/spec-kitty.review`** – Reviewers add detailed feedback here when work needs changes.

Approved — rename consistent, value objects match contract, `Any` tier avoids circular import, alias works, 105 tests pass.

---

## Markdown Formatting

Wrap HTML/XML tags in backticks: `` `<div>` ``, `` `<script>` ``
Use language identifiers in code blocks: ````python`, ````bash`

---

## Objectives & Success Criteria

1. `MissionRepository` class in `src/doctrine/missions/repository.py` is renamed to `MissionTemplateRepository`
2. Two value objects (`TemplateResult`, `ConfigResult`) are added to `repository.py` following the API contract
3. All existing path-returning methods are renamed to private `_*_path()` names
4. A `default()` classmethod is added as convenience constructor
5. `__init__.py` exports `MissionTemplateRepository`, `TemplateResult`, `ConfigResult`, and has `MissionRepository = MissionTemplateRepository` alias
6. `from doctrine.missions import MissionRepository` still works (alias)
7. Existing `test_mission_repository.py` is updated minimally to account for method renames

**Success gate**: `pytest tests/doctrine/missions/ -v` passes.

## Context & Constraints

- **Spec**: `kitty-specs/058-mission-template-repository-refactor/spec.md` (FR-001, FR-013-016)
- **Contract**: `kitty-specs/058-mission-template-repository-refactor/contracts/mission-template-repository.md`
- **Plan**: `kitty-specs/058-mission-template-repository-refactor/plan.md` (Phase 1)
- **Constraint C-001**: Shipped migrations must NOT be modified (the alias handles this)
- **Constraint NFR-001**: No circular imports between `doctrine` and `specify_cli`
- **Source file**: `src/doctrine/missions/repository.py` (143 lines currently)
- **Init file**: `src/doctrine/missions/__init__.py` (14 lines currently)

## Branch Strategy

- **Strategy**: workspace-per-WP
- **Planning base branch**: feature/agent-profile-implementation
- **Merge target branch**: feature/agent-profile-implementation

**Implementation command**: `spec-kitty implement WP01`

## Subtasks & Detailed Guidance

### Subtask T001 – Rename class MissionRepository to MissionTemplateRepository

- **Purpose**: Establish the new canonical class name. The old name becomes an alias.
- **Steps**:
  1. In `src/doctrine/missions/repository.py`, change `class MissionRepository:` to `class MissionTemplateRepository:`
  2. Update the class docstring to reflect the new name and expanded role:
     ```python
     class MissionTemplateRepository:
         """Single authority for mission asset access.

         Provides content-returning public methods (via TemplateResult and
         ConfigResult value objects) and private _*_path() methods for
         internal callers that need filesystem access.  All query methods
         return None (rather than raising) when the requested asset does
         not exist, so callers can implement their own fallback logic.
         """
     ```
  3. Update the `default_missions_root` classmethod's docstring (no code change needed)
- **Files**: `src/doctrine/missions/repository.py`
- **Parallel?**: Must complete before T005 (method renames reference the class)

### Subtask T002 – Add TemplateResult value object

- **Purpose**: Wrap template content with origin metadata. Consumers get content + provenance without needing filesystem paths.
- **Steps**:
  1. Add the `TemplateResult` class to `repository.py` ABOVE the `MissionTemplateRepository` class definition
  2. Follow the contract exactly:
     ```python
     from __future__ import annotations
     from pathlib import Path
     from typing import Any

     class TemplateResult:
         """Value object wrapping template content with origin metadata."""

         __slots__ = ("_data",)

         def __init__(self, content: str, origin: str, tier: Any = None) -> None:
             self._data: dict[str, Any] = {
                 "content": content,
                 "origin": origin,
                 "tier": tier,
             }

         @property
         def content(self) -> str:
             """Raw template text (UTF-8)."""
             return self._data["content"]

         @property
         def origin(self) -> str:
             """Human-readable origin label (e.g. 'doctrine/software-dev/command-templates/implement.md')."""
             return self._data["origin"]

         @property
         def tier(self) -> Any:
             """Resolution tier (ResolutionTier enum or None for doctrine-level lookups)."""
             return self._data["tier"]

         def __repr__(self) -> str:
             return f"TemplateResult(origin={self.origin!r}, tier={self.tier})"
     ```
  3. **Important**: Use `Any` for the `tier` type, NOT `ResolutionTier`. The `ResolutionTier` enum lives in `specify_cli.runtime.resolver` and importing it here would create a circular dependency (NFR-001). The actual `ResolutionTier` enum value is passed at runtime by the `resolve_*` methods (added in WP03).
- **Files**: `src/doctrine/missions/repository.py`
- **Parallel?**: Yes, independent of T003

### Subtask T003 – Add ConfigResult value object

- **Purpose**: Wrap parsed YAML config with origin metadata. Consumers get pre-parsed data + raw text + provenance.
- **Steps**:
  1. Add the `ConfigResult` class to `repository.py` after `TemplateResult`:
     ```python
     class ConfigResult:
         """Value object wrapping parsed YAML config with origin metadata."""

         __slots__ = ("_data",)

         def __init__(self, content: str, origin: str, parsed: dict | list) -> None:
             self._data: dict[str, Any] = {
                 "content": content,
                 "origin": origin,
                 "parsed": parsed,
             }

         @property
         def content(self) -> str:
             """Raw YAML text (UTF-8)."""
             return self._data["content"]

         @property
         def origin(self) -> str:
             """Human-readable origin label (e.g. 'doctrine/software-dev/mission.yaml')."""
             return self._data["origin"]

         @property
         def parsed(self) -> dict | list:
             """Pre-parsed YAML data (parsed with ruamel.yaml YAML(typ='safe'))."""
             return self._data["parsed"]

         def __repr__(self) -> str:
             return f"ConfigResult(origin={self.origin!r})"
     ```
- **Files**: `src/doctrine/missions/repository.py`
- **Parallel?**: Yes, independent of T002

### Subtask T004 – Add default() classmethod

- **Purpose**: Convenience constructor that eliminates the verbose `MissionTemplateRepository(MissionTemplateRepository.default_missions_root())` pattern.
- **Steps**:
  1. Add a `default` classmethod after `default_missions_root`:
     ```python
     @classmethod
     def default(cls) -> MissionTemplateRepository:
         """Return a repository instance for the doctrine-bundled missions."""
         return cls(cls.default_missions_root())
     ```
- **Files**: `src/doctrine/missions/repository.py`
- **Parallel?**: Yes, after T001 is done

### Subtask T005 – Rename existing path methods to private _*_path() names

- **Purpose**: Make path-returning methods private. The public API will return content via value objects (added in WP02/WP03).
- **Steps**:
  1. Rename the following methods in `repository.py`:
     | Old Name | New Name |
     |----------|----------|
     | `get_command_template(mission, command)` | `_command_template_path(mission, name)` |
     | `get_template(mission, template)` | `_content_template_path(mission, name)` |
     | `get_action_index_path(mission, action)` | `_action_index_path(mission, action)` |
     | `get_action_guidelines_path(mission, action)` | `_action_guidelines_path(mission, action)` |
     | `get_mission_config_path(mission)` | `_mission_config_path(mission)` |
     | `get_expected_artifacts(mission)` | `_expected_artifacts_path(mission)` |
  2. Also rename parameter names where they changed (e.g., `command` → `name` in `_command_template_path`, `template` → `name` in `_content_template_path`)
  3. Add `_missions_root` property:
     ```python
     @property
     def _missions_root(self) -> Path:
         """Return the missions root directory (internal use only)."""
         return self._root
     ```
  4. Update docstrings to reflect "internal use" / "private" status
- **Files**: `src/doctrine/missions/repository.py`
- **Parallel?**: Must follow T001

**Note on existing callers**: Only 2 production files call these methods directly:
- `dossier/manifest.py` calls `get_expected_artifacts()` → will break (fixed in WP05-WP07)
- `runtime_bridge.py` calls `default_missions_root()` → unchanged (it's a classmethod)

However, `tests/doctrine/missions/test_mission_repository.py` calls the old method names. Update the test file to use the new private names (or verify the tests need updating in T017/WP04).

### Subtask T016 – Update __init__.py exports and alias

- **Purpose**: Make `MissionTemplateRepository`, `TemplateResult`, and `ConfigResult` importable from `doctrine.missions`. Keep `MissionRepository` as a backward-compatible alias.
- **Steps**:
  1. Update `src/doctrine/missions/__init__.py`:
     ```python
     """Mission framework package."""

     from .action_index import ActionIndex, load_action_index
     from .primitives import PrimitiveExecutionContext
     from .glossary_hook import execute_with_glossary
     from .repository import MissionTemplateRepository, TemplateResult, ConfigResult

     # Backward-compat alias for shipped migrations and existing imports
     MissionRepository = MissionTemplateRepository

     __all__ = [
         "ActionIndex",
         "load_action_index",
         "PrimitiveExecutionContext",
         "execute_with_glossary",
         "MissionTemplateRepository",
         "MissionRepository",  # alias
         "TemplateResult",
         "ConfigResult",
     ]
     ```
  2. Verify: `from doctrine.missions import MissionRepository` resolves to `MissionTemplateRepository`
  3. Verify: `isinstance(MissionTemplateRepository.default(), MissionRepository)` is `True`
- **Files**: `src/doctrine/missions/__init__.py`
- **Parallel?**: Must follow T001-T003

## Test Strategy

Run before starting:
```bash
source .venv/bin/activate && .venv/bin/python -m pytest tests/doctrine/missions/test_mission_repository.py -v
```

Run after all subtasks:
```bash
source .venv/bin/activate && .venv/bin/python -m pytest tests/doctrine/missions/ -v
```

**Expected**: Existing tests may fail due to method renames (old method names no longer exist). This is expected -- the test file will need to be updated to use the new private method names. Do this update as part of T005 (same commit). The alias keeps the CLASS name working, but individual METHOD names changed.

Also verify the alias works:
```python
from doctrine.missions import MissionRepository, MissionTemplateRepository
assert MissionRepository is MissionTemplateRepository
```

## Risks & Mitigations

1. **Method rename breaks existing tests**: Expected. Update test assertions to use `_*_path()` names. The alias handles class name only.
2. **Circular import from `ResolutionTier`**: Avoided by using `Any` type annotation for `TemplateResult.tier`.
3. **Production callers break**: Only `dossier/manifest.py` calls a renamed method (`get_expected_artifacts`). This will break until WP05-WP07 reroute it. Accept this -- the user prefers "break stuff to surface issues."

## Review Guidance

- Verify class rename is consistent throughout `repository.py`
- Verify all 6 path methods are renamed to private `_*_path()` names
- Verify `TemplateResult` and `ConfigResult` match the contract exactly
- Verify `__init__.py` has proper alias and all exports
- Verify no `ResolutionTier` import at module level in `repository.py`
- Run `pytest tests/doctrine/missions/ -v` and confirm it passes

## Activity Log

- 2026-03-27T04:37:32Z – system – lane=planned – Prompt created.
- 2026-03-28T04:42:52Z – claude – shell_pid=9762 – lane=doing – Assigned agent via workflow command
- 2026-03-28T04:46:31Z – claude – shell_pid=9762 – lane=for_review – Ready for review: renamed MissionRepository→MissionTemplateRepository, added TemplateResult/ConfigResult value objects, private _*_path() methods, default() classmethod, backward-compat alias. 37 tests pass.
- 2026-03-28T05:39:25Z – claude-opus-4-6 – shell_pid=21171 – lane=doing – Started review via workflow command
- 2026-03-28T05:41:30Z – claude-opus-4-6 – shell_pid=21171 – lane=approved – Review passed: class rename, value objects, private methods, alias, tests all correct. 105 tests pass.
- 2026-03-28T10:02:04Z – claude-opus-4-6 – shell_pid=21171 – lane=done – Done override: Merged to feature/agent-profile-implementation, branch deleted post-merge
