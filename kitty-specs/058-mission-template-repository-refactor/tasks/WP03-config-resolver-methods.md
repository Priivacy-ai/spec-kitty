---
work_package_id: WP03
title: Config + Resolver Public Methods
lane: planned
dependencies:
- WP01
requirement_refs:
- FR-004
- FR-005
- FR-009
- FR-010
- FR-011
- FR-012
- FR-018
- NFR-003
- NFR-004
planning_base_branch: feature/agent-profile-implementation
merge_target_branch: feature/agent-profile-implementation
branch_strategy: Planning artifacts for this feature were generated on feature/agent-profile-implementation. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feature/agent-profile-implementation unless the human explicitly redirects the landing branch.
subtasks:
- T010
- T011
- T012
- T013
- T014
- T015
phase: Phase 1 - New API Foundation
assignee: ''
agent: ''
agent_profile: implementer
shell_pid: ''
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-03-27T04:37:32Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP03 – Config + Resolver Public Methods

## Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.
- **You must address all feedback** before your work is complete.
- **Mark as acknowledged**: When you understand the feedback and begin addressing it, update `review_status: acknowledged` in the frontmatter.

---

## Review Feedback

> **Populated by `/spec-kitty.review`**

*[This section is empty initially.]*

---

## Markdown Formatting

Wrap HTML/XML tags in backticks: `` `<div>` ``, `` `<script>` ``
Use language identifiers in code blocks: ````python`, ````bash`

---

## Objectives & Success Criteria

1. `get_action_index(mission, action)` returns `ConfigResult | None` with parsed YAML dict — on `MissionTemplateRepository` (doctrine)
2. `get_action_guidelines(mission, action)` returns `TemplateResult | None` with markdown content — on `MissionTemplateRepository` (doctrine)
3. `get_mission_config(mission)` returns `ConfigResult | None` with parsed mission.yaml — on `MissionTemplateRepository` (doctrine)
4. `get_expected_artifacts(mission)` returns `ConfigResult | None` with parsed expected-artifacts.yaml — on `MissionTemplateRepository` (doctrine)
5. `ConstitutionTemplateResolver.resolve_command_template(mission, name, project_dir?)` returns `TemplateResult` through 5-tier chain — NEW class in `src/constitution/template_resolver.py`
6. `ConstitutionTemplateResolver.resolve_content_template(mission, name, project_dir?)` returns `TemplateResult` through 5-tier chain — on `ConstitutionTemplateResolver`
7. All YAML parsing uses `ruamel.yaml` with `YAML(typ="safe")` (NFR-004)
8. **Package boundary invariant**: `MissionTemplateRepository` (doctrine) has ZERO imports from `specify_cli` or `constitution`. `ConstitutionTemplateResolver` (constitution) may import from `specify_cli.runtime`.
9. `resolve_*` raises `FileNotFoundError` when template not found at any tier

**Success gate**: `repo.get_action_index("software-dev", "implement")` returns `ConfigResult` with parsed dict. `ConstitutionTemplateResolver(repo).resolve_command_template("software-dev", "implement")` returns `TemplateResult`.

## Context & Constraints

- **Contract**: `kitty-specs/058-mission-template-repository-refactor/contracts/mission-template-repository.md`
- **Prerequisite**: WP01 (value objects, private methods), WP02 (established pattern for template methods)
- **Resolver location**: `src/specify_cli/runtime/resolver.py` -- has `resolve()` function, `ResolutionTier` enum, `ResolutionResult` dataclass
- **YAML library**: `ruamel.yaml` (already a dependency, used in `action_index.py`)
- **Constraint FR-018 / 2.x invariant**: `MissionTemplateRepository` in `doctrine` depends only on `kernel`. ZERO imports from `specify_cli` or `constitution`. The `resolve_*` methods live on `ConstitutionTemplateResolver` in `src/constitution/template_resolver.py`.
- **Constraint NFR-003**: No caching -- each call reads fresh from disk
- **Constraint NFR-004**: YAML(typ="safe") only -- no unsafe deserialization

## Branch Strategy

- **Strategy**: workspace-per-WP
- **Planning base branch**: feature/agent-profile-implementation
- **Merge target branch**: feature/agent-profile-implementation

**Implementation command**: `spec-kitty implement WP03 --base WP02`

## Subtasks & Detailed Guidance

### Subtask T010 – Add get_action_index() config method

- **Purpose**: Read and parse an action's `index.yaml`. Replaces manual path construction + `load_action_index()` calls in `constitution/context.py`.
- **Steps**:
  1. Add `ruamel.yaml` import at the top of `repository.py`:
     ```python
     from ruamel.yaml import YAML
     ```
  2. Add method:
     ```python
     def get_action_index(self, mission: str, action: str) -> ConfigResult | None:
         """Read and parse an action's index.yaml from doctrine assets.

         Looks for ``<missions_root>/<mission>/actions/<action>/index.yaml``.

         Args:
             mission: Mission name.
             action: Action name (e.g. ``"implement"``).

         Returns:
             ConfigResult with raw YAML text and parsed dict, or ``None`` if not found.
         """
         path = self._action_index_path(mission, action)
         if path is None:
             return None
         try:
             content = path.read_text(encoding="utf-8")
             yaml = YAML(typ="safe")
             parsed = yaml.load(content)
             if parsed is None:
                 return None
             origin = f"doctrine/{mission}/actions/{action}/index.yaml"
             return ConfigResult(content=content, origin=origin, parsed=parsed)
         except Exception:
             return None
     ```
  3. **Note**: `YAML(typ="safe").load()` returns `None` for empty files -- we return `None` in that case. `parsed` is typically a `dict` with keys like `action`, `directives`, `tactics`, `styleguides`, etc.
  4. **Important**: This returns the raw parsed dict, NOT an `ActionIndex` dataclass. The `ActionIndex` type is a separate concern handled by `load_action_index()`. Consumers that need `ActionIndex` should continue using that function. This method is for consumers that just need the raw config data.
- **Files**: `src/doctrine/missions/repository.py`
- **Parallel?**: Yes, independent of T011-T015

### Subtask T011 – Add get_action_guidelines() method

- **Purpose**: Read an action's `guidelines.md` content. Replaces manual path construction in `constitution/context.py` (line 249).
- **Steps**:
  1. Add method:
     ```python
     def get_action_guidelines(self, mission: str, action: str) -> TemplateResult | None:
         """Read an action's guidelines.md from doctrine assets.

         Looks for ``<missions_root>/<mission>/actions/<action>/guidelines.md``.

         Args:
             mission: Mission name.
             action: Action name.

         Returns:
             TemplateResult with content and origin, or ``None`` if not found.
         """
         path = self._action_guidelines_path(mission, action)
         if path is None:
             return None
         try:
             content = path.read_text(encoding="utf-8")
             origin = f"doctrine/{mission}/actions/{action}/guidelines.md"
             return TemplateResult(content=content, origin=origin)
         except (OSError, UnicodeDecodeError):
             return None
     ```
  2. Returns `TemplateResult` (not `ConfigResult`) because guidelines are markdown, not YAML
- **Files**: `src/doctrine/missions/repository.py`
- **Parallel?**: Yes

### Subtask T012 – Add get_mission_config() config method

- **Purpose**: Read and parse a mission's `mission.yaml`. Replaces manual path construction in `catalog.py` files.
- **Steps**:
  1. Add method:
     ```python
     def get_mission_config(self, mission: str) -> ConfigResult | None:
         """Read and parse a mission's mission.yaml from doctrine assets.

         Args:
             mission: Mission name.

         Returns:
             ConfigResult with raw YAML text and parsed dict, or ``None`` if not found.
         """
         path = self._mission_config_path(mission)
         if path is None:
             return None
         try:
             content = path.read_text(encoding="utf-8")
             yaml = YAML(typ="safe")
             parsed = yaml.load(content)
             if parsed is None:
                 return None
             origin = f"doctrine/{mission}/mission.yaml"
             return ConfigResult(content=content, origin=origin, parsed=parsed)
         except Exception:
             return None
     ```
- **Files**: `src/doctrine/missions/repository.py`
- **Parallel?**: Yes

### Subtask T013 – Add get_expected_artifacts() config method

- **Purpose**: Read and parse a mission's `expected-artifacts.yaml`. Replaces `dossier/manifest.py`'s manual path usage.
- **Steps**:
  1. Add method (NOTE: the old `get_expected_artifacts` returned `Path | None` and was renamed to `_expected_artifacts_path` in WP01):
     ```python
     def get_expected_artifacts(self, mission: str) -> ConfigResult | None:
         """Read and parse a mission's expected-artifacts.yaml.

         Args:
             mission: Mission name (e.g. ``"software-dev"``).

         Returns:
             ConfigResult with raw YAML text and parsed data, or ``None`` if not found.
         """
         path = self._expected_artifacts_path(mission)
         if path is None:
             return None
         try:
             content = path.read_text(encoding="utf-8")
             yaml = YAML(typ="safe")
             parsed = yaml.load(content)
             if parsed is None:
                 return None
             origin = f"doctrine/{mission}/expected-artifacts.yaml"
             return ConfigResult(content=content, origin=origin, parsed=parsed)
         except Exception:
             return None
     ```
  2. **Note**: The old `get_expected_artifacts` was renamed to `_expected_artifacts_path` in WP01. This new method shares the same public name but returns `ConfigResult` instead of `Path`. Callers that used to call `repo.get_expected_artifacts(mission)` and got a `Path` will now get a `ConfigResult` -- the alias means old callers break intentionally to surface migration needs.
- **Files**: `src/doctrine/missions/repository.py`
- **Parallel?**: Yes

### Subtask T014 – Create `ConstitutionTemplateResolver` with `resolve_command_template()`

- **Purpose**: Resolve a command template through the 5-tier override chain. This class lives in `src/constitution/` (NOT in doctrine) because the override chain is "how project context modifies doctrine defaults" — that's constitution by definition. Doctrine is the abstract law; constitution is the local legislation.
- **Steps**:
  1. First, study the resolver API. Read `src/specify_cli/runtime/resolver.py` to understand:
     - The `resolve()` function signature and return type (`ResolutionResult`)
     - How it handles the `subdir` parameter for command-templates vs. content-templates
     - How `ResolutionTier` enum values map to origin labels
  2. Create `src/constitution/template_resolver.py`:
     ```python
     """Project-aware template resolution through the 5-tier override chain.

     Composes MissionTemplateRepository (doctrine-level, tier 5) with the
     specify_cli runtime resolver (tiers 1-4). Constitution is the
     concretization of doctrine into local context-aware legislation.
     """
     from __future__ import annotations

     from pathlib import Path
     from typing import Any

     from doctrine.missions.repository import MissionTemplateRepository, TemplateResult
     from specify_cli.runtime.resolver import (
         ResolutionTier,
         resolve as _resolve,
     )


     class ConstitutionTemplateResolver:
         """5-tier project-aware template resolution.

         Resolution order: OVERRIDE > LEGACY > GLOBAL_MISSION > GLOBAL > PACKAGE_DEFAULT.
         """

         def __init__(self, repo: MissionTemplateRepository | None = None) -> None:
             self._repo = repo or MissionTemplateRepository.default()

         def resolve_command_template(
             self,
             mission: str,
             name: str,
             project_dir: Path | None = None,
         ) -> TemplateResult:
             """Resolve a command template through the 5-tier override chain.

             Args:
                 mission: Mission name.
                 name: Template name without ``.md`` extension.
                 project_dir: Project root for override/legacy lookups.

             Returns:
                 TemplateResult with content, origin, and tier.

             Raises:
                 FileNotFoundError: If template not found at any tier.
             """
             result = _resolve(
                 mission=mission,
                 subdir="command-templates",
                 name=f"{name}.md",
                 project_dir=project_dir,
             )
             content = result.path.read_text(encoding="utf-8")
             origin = self._tier_to_origin(result.tier, mission, "command-templates", f"{name}.md")
             return TemplateResult(content=content, origin=origin, tier=result.tier)

         @staticmethod
         def _tier_to_origin(tier: Any, mission: str, asset_type: str, filename: str) -> str:
             tier_prefix = {
                 ResolutionTier.OVERRIDE: "override",
                 ResolutionTier.LEGACY: "legacy",
                 ResolutionTier.GLOBAL_MISSION: "global",
                 ResolutionTier.GLOBAL: "global",
                 ResolutionTier.PACKAGE_DEFAULT: "doctrine",
             }
             prefix = tier_prefix.get(tier, "unknown")
             return f"{prefix}/{mission}/{asset_type}/{filename}"
     ```
  3. **Critical**: This file lives in `src/constitution/`, NOT in `src/doctrine/`. The import from `specify_cli.runtime.resolver` is at module level — this is fine because constitution may depend on `specify_cli.runtime` per the 2.x landscape.
  4. Update `src/constitution/__init__.py` to export `ConstitutionTemplateResolver`.
- **Files**: `src/constitution/template_resolver.py` (NEW), `src/constitution/__init__.py`
- **Parallel?**: Independent of T015 but must understand resolver first
- **Notes**: Read `resolver.py` carefully. The `resolve()` function signature may differ from what's shown. Check actual parameter names and return type.

### Subtask T015 – Add `resolve_content_template()` on `ConstitutionTemplateResolver`

- **Purpose**: Same as T014 but for content templates (`templates/` subdirectory).
- **Steps**:
  1. Add method to `ConstitutionTemplateResolver` in `src/constitution/template_resolver.py`:
     ```python
     def resolve_content_template(
         self,
         mission: str,
         name: str,
         project_dir: Path | None = None,
     ) -> TemplateResult:
         """Resolve a content template through the 5-tier override chain."""
         result = _resolve(
             mission=mission,
             subdir="templates",
             name=name,
             project_dir=project_dir,
         )
         content = result.path.read_text(encoding="utf-8")
         origin = self._tier_to_origin(result.tier, mission, "templates", name)
         return TemplateResult(content=content, origin=origin, tier=result.tier)
     ```
  2. Reuses the `_tier_to_origin()` helper from T014
- **Files**: `src/constitution/template_resolver.py`
- **Parallel?**: Yes, same pattern as T014

## Test Strategy

After implementing all 6 methods (4 on repository, 2 on resolver), verify:
```bash
source .venv/bin/activate && python -c "
from doctrine.missions import MissionTemplateRepository
repo = MissionTemplateRepository.default()
# Config methods (doctrine-level)
idx = repo.get_action_index('software-dev', 'implement')
assert idx is not None, 'action index not found'
assert isinstance(idx.parsed, dict), f'expected dict, got {type(idx.parsed)}'
print(f'get_action_index: OK')

gl = repo.get_action_guidelines('software-dev', 'implement')
print(f'get_action_guidelines: {\"OK\" if gl else \"None\"}')

mc = repo.get_mission_config('software-dev')
assert mc is not None, 'mission config not found'
print(f'get_mission_config: OK')

ea = repo.get_expected_artifacts('software-dev')
print(f'get_expected_artifacts: {\"OK\" if ea else \"None\"}')

# Resolver methods (constitution-level, 5-tier)
from constitution.template_resolver import ConstitutionTemplateResolver
resolver = ConstitutionTemplateResolver(repo)
rt = resolver.resolve_command_template('software-dev', 'implement')
assert len(rt.content) > 0
assert rt.tier is not None
print(f'resolve_command_template: OK (tier={rt.tier})')

print('All smoke tests passed!')
"
```

**Package boundary verification** (CRITICAL):
```bash
# Doctrine must have ZERO imports from specify_cli or constitution
rg 'from specify_cli|import specify_cli|from constitution|import constitution' src/doctrine/ --type py
# Expected: no matches
```

Also run:
```bash
source .venv/bin/activate && .venv/bin/python -m pytest tests/doctrine/missions/ tests/constitution/ -v
```

## Risks & Mitigations

1. ~~**Circular import**~~: **Eliminated by AR-1 decision**. `resolve_*` methods now live in `src/constitution/template_resolver.py`, not in doctrine. Constitution's dependency on `specify_cli.runtime` is architecturally permitted.
2. **Resolver API mismatch**: The `resolve()` function signature may differ from what's shown. Read `resolver.py` before implementing T014/T015.
3. **ruamel.yaml parse failure**: The try/except returns `None` for any parse error. Consider logging a warning.
4. **get_expected_artifacts name collision**: The old `get_expected_artifacts()` returned `Path | None` (now `_expected_artifacts_path()`). The new one returns `ConfigResult | None`. Callers using the alias `MissionRepository(root).get_expected_artifacts()` will get different behavior -- this is intentional but will break `dossier/manifest.py` until rerouted in WP05-WP07.

## Review Guidance

- Verify `ruamel.yaml` import is at module level in `repository.py` (it's fine — `ruamel.yaml` is in `doctrine`'s dependency tree)
- **CRITICAL**: Verify `src/doctrine/missions/repository.py` has ZERO imports from `specify_cli` or `constitution`
- Verify `ConstitutionTemplateResolver` lives in `src/constitution/template_resolver.py` (not in doctrine)
- Verify `resolve_*` methods raise `FileNotFoundError` (not catch it)
- Verify origin labels match the contract convention
- Verify no caching of YAML parse results
- Run the smoke test, package boundary check, and `pytest`

## Activity Log

- 2026-03-27T04:37:32Z – system – lane=planned – Prompt created.
