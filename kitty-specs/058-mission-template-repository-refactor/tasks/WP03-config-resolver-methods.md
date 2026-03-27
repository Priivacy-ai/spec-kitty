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

1. `get_action_index(mission, action)` returns `ConfigResult | None` with parsed YAML dict
2. `get_action_guidelines(mission, action)` returns `TemplateResult | None` with markdown content
3. `get_mission_config(mission)` returns `ConfigResult | None` with parsed mission.yaml
4. `get_expected_artifacts(mission)` returns `ConfigResult | None` with parsed expected-artifacts.yaml
5. `resolve_command_template(mission, name, project_dir?)` returns `TemplateResult` through 5-tier chain
6. `resolve_content_template(mission, name, project_dir?)` returns `TemplateResult` through 5-tier chain
7. All YAML parsing uses `ruamel.yaml` with `YAML(typ="safe")` (NFR-004)
8. No circular imports at module load time (NFR-001) -- resolver imported lazily inside method body
9. `resolve_*` raises `FileNotFoundError` when template not found at any tier

**Success gate**: `repo.get_action_index("software-dev", "implement")` returns `ConfigResult` with parsed dict.

## Context & Constraints

- **Contract**: `kitty-specs/058-mission-template-repository-refactor/contracts/mission-template-repository.md`
- **Prerequisite**: WP01 (value objects, private methods), WP02 (established pattern for template methods)
- **Resolver location**: `src/specify_cli/runtime/resolver.py` -- has `resolve()` function, `ResolutionTier` enum, `ResolutionResult` dataclass
- **YAML library**: `ruamel.yaml` (already a dependency, used in `action_index.py`)
- **Constraint NFR-001**: No `from specify_cli...` imports at module level in `repository.py`
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

### Subtask T014 – Add resolve_command_template() with lazy resolver import

- **Purpose**: Resolve a command template through the 5-tier override chain (OVERRIDE > LEGACY > GLOBAL_MISSION > GLOBAL > PACKAGE_DEFAULT). This is the project-aware version of `get_command_template()`.
- **Steps**:
  1. First, study the resolver API. Read `src/specify_cli/runtime/resolver.py` to understand:
     - The `resolve()` function signature and return type (`ResolutionResult`)
     - How it handles the `subdir` parameter for command-templates vs. content-templates
     - How `ResolutionTier` enum values map to origin labels
  2. Add method with lazy import:
     ```python
     def resolve_command_template(
         self,
         mission: str,
         name: str,
         project_dir: Path | None = None,
     ) -> TemplateResult:
         """Resolve a command template through the 5-tier override chain.

         Resolution order: OVERRIDE > LEGACY > GLOBAL_MISSION > GLOBAL > PACKAGE_DEFAULT.

         Args:
             mission: Mission name.
             name: Template name without ``.md`` extension.
             project_dir: Project root for override/legacy lookups.
                          If ``None``, only GLOBAL and PACKAGE_DEFAULT tiers are checked.

         Returns:
             TemplateResult with content, origin, and tier.

         Raises:
             FileNotFoundError: If template not found at any tier.
         """
         # Lazy import to avoid circular dependency (doctrine -> specify_cli)
         from specify_cli.runtime.resolver import resolve as _resolve

         result = _resolve(
             mission=mission,
             subdir="command-templates",
             name=f"{name}.md",
             project_dir=project_dir,
         )
         content = result.path.read_text(encoding="utf-8")
         origin = self._tier_to_origin(result.tier, mission, "command-templates", f"{name}.md")
         return TemplateResult(content=content, origin=origin, tier=result.tier)
     ```
  3. Add a private helper for origin label construction from tier:
     ```python
     @staticmethod
     def _tier_to_origin(tier: Any, mission: str, asset_type: str, filename: str) -> str:
         """Map a ResolutionTier to a human-readable origin label."""
         # Import locally to get enum values for comparison
         from specify_cli.runtime.resolver import ResolutionTier
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
  4. **Critical**: The `resolve()` function in `resolver.py` raises `FileNotFoundError` when nothing is found. Let this propagate (per contract).
  5. **Critical**: The lazy import is INSIDE the method body, not at module level. This prevents circular imports at import time.
- **Files**: `src/doctrine/missions/repository.py`
- **Parallel?**: Independent of T015 but must understand resolver first
- **Notes**: Read `resolver.py` carefully before implementing. The `resolve()` function signature may differ from what's shown here. Check the actual parameter names and return type.

### Subtask T015 – Add resolve_content_template() with lazy resolver import

- **Purpose**: Same as T014 but for content templates (`templates/` subdirectory).
- **Steps**:
  1. Add method with the same lazy-import pattern as T014:
     ```python
     def resolve_content_template(
         self,
         mission: str,
         name: str,
         project_dir: Path | None = None,
     ) -> TemplateResult:
         """Resolve a content template through the 5-tier override chain.

         Args:
             mission: Mission name.
             name: Template filename with extension.
             project_dir: Project root for override/legacy lookups.

         Returns:
             TemplateResult with content, origin, and tier.

         Raises:
             FileNotFoundError: If template not found at any tier.
         """
         from specify_cli.runtime.resolver import resolve as _resolve

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
- **Files**: `src/doctrine/missions/repository.py`
- **Parallel?**: Yes, same pattern as T014

## Test Strategy

After implementing all 6 methods, verify:
```bash
source .venv/bin/activate && python -c "
from doctrine.missions import MissionTemplateRepository
repo = MissionTemplateRepository.default()
# Config methods
idx = repo.get_action_index('software-dev', 'implement')
assert idx is not None, 'action index not found'
assert isinstance(idx.parsed, dict), f'expected dict, got {type(idx.parsed)}'
print(f'get_action_index: {idx}')

gl = repo.get_action_guidelines('software-dev', 'implement')
print(f'get_action_guidelines: {gl}')

mc = repo.get_mission_config('software-dev')
assert mc is not None, 'mission config not found'
print(f'get_mission_config: {mc}')

ea = repo.get_expected_artifacts('software-dev')
print(f'get_expected_artifacts: {ea}')

# Resolver methods (without project_dir -- package default only)
rt = repo.resolve_command_template('software-dev', 'implement')
assert len(rt.content) > 0
assert rt.tier is not None
print(f'resolve_command_template: {rt}')

print('All smoke tests passed!')
"
```

Also run:
```bash
source .venv/bin/activate && .venv/bin/python -m pytest tests/doctrine/missions/ -v
```

## Risks & Mitigations

1. **Circular import**: The `from specify_cli.runtime.resolver import resolve` is inside the method body. Verify it doesn't trigger at module load time by running `python -c "from doctrine.missions import MissionTemplateRepository"` successfully.
2. **Resolver API mismatch**: The `resolve()` function signature may differ from what's shown. Read `resolver.py` before implementing T014/T015.
3. **ruamel.yaml parse failure**: The try/except returns `None` for any parse error. Consider logging a warning.
4. **get_expected_artifacts name collision**: The old `get_expected_artifacts()` returned `Path | None` (now `_expected_artifacts_path()`). The new one returns `ConfigResult | None`. Callers using the alias `MissionRepository(root).get_expected_artifacts()` will get different behavior -- this is intentional but will break `dossier/manifest.py` until rerouted in WP05-WP07.

## Review Guidance

- Verify `ruamel.yaml` import is at module level (it's fine -- `ruamel.yaml` is in `doctrine`'s dependency tree)
- Verify `specify_cli` imports are ONLY inside method bodies (lazy)
- Verify `resolve_*` methods raise `FileNotFoundError` (not catch it)
- Verify origin labels match the contract convention
- Verify no caching of YAML parse results
- Run the smoke test and `pytest tests/doctrine/missions/ -v`

## Activity Log

- 2026-03-27T04:37:32Z – system – lane=planned – Prompt created.
