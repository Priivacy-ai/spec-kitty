---
work_package_id: WP01
title: Registry Skeleton and Glossary-Compliant Naming
dependencies: []
requirement_refs:
- FR-001
- FR-018
- C-001
- C-003
- C-005
tracker_refs: []
planning_base_branch: feat/tool-surface-contract
merge_target_branch: feat/tool-surface-contract
branch_strategy: Planning artifacts for this mission were generated on feat/tool-surface-contract. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/tool-surface-contract unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-tool-surface-contract-01KV2K2P
base_commit: a91cb36344cf3ed055304f4161514db98d8e2c66
created_at: '2026-06-14T09:49:26.582007+00:00'
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
- T007
agent: claude
shell_pid: '3474'
history:
- date: '2026-06-14'
  action: created
  actor: claude
agent_profile: architect-alphonso
authoritative_surface: src/specify_cli/tool_surface/
create_intent:
- src/specify_cli/tool_surface/__init__.py
- src/specify_cli/tool_surface/enums.py
- src/specify_cli/tool_surface/model.py
- src/specify_cli/tool_surface/registry.py
- src/specify_cli/tool_surface/builtins.py
- src/specify_cli/tool_surface/providers/__init__.py
- src/specify_cli/tool_surface/providers/base.py
- src/specify_cli/tool_surface/data/tool-surface-contract.schema.json
- src/specify_cli/tool_surface/data/surface-status.schema.json
- tests/specify_cli/tool_surface/__init__.py
- tests/specify_cli/tool_surface/test_enums.py
- tests/specify_cli/tool_surface/test_model.py
- tests/specify_cli/tool_surface/test_registry.py
- tests/specify_cli/tool_surface/providers/__init__.py
execution_mode: code_change
owned_files:
- src/specify_cli/tool_surface/__init__.py
- src/specify_cli/tool_surface/enums.py
- src/specify_cli/tool_surface/model.py
- src/specify_cli/tool_surface/registry.py
- src/specify_cli/tool_surface/builtins.py
- src/specify_cli/tool_surface/providers/__init__.py
- src/specify_cli/tool_surface/providers/base.py
- src/specify_cli/tool_surface/data/tool-surface-contract.schema.json
- src/specify_cli/tool_surface/data/surface-status.schema.json
- tests/specify_cli/tool_surface/__init__.py
- tests/specify_cli/tool_surface/test_enums.py
- tests/specify_cli/tool_surface/test_model.py
- tests/specify_cli/tool_surface/test_registry.py
- tests/specify_cli/tool_surface/providers/__init__.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, run:

```
/ad-hoc-profile-load architect-alphonso
```

This loads the Architect Alphonso profile which governs structural and vocabulary decisions for this work package.

## Objective

Introduce the `src/specify_cli/tool_surface/` bounded context with all type definitions, the registry stub, the provider protocol, and a 19-harness builtins stub. **This work package makes zero runtime behavior changes** — it is purely structural, establishing the vocabulary and type boundaries that all subsequent WPs build on.

**Child issue**: #1936
**Parent epic**: #1945

## Context

The ToolSurfaceContract registry is the central new concept of this epic. It answers "what surfaces should exist for a configured tool?" as policy, separately from manifests (which record what is installed). This WP introduces the bounded context and all its type vocabulary without wiring any providers or changing any existing behavior.

**Non-negotiable naming** (from C-003, C-005):
- `ToolSurfaceContract` — not `AgentSurfaceContract`
- `SurfaceKind`, `SurfaceDefinition`, `SurfaceInstance`, `SurfacePlan` — the data model uses these names
- Tool vs. Agent distinction must be preserved in all names and docstrings

**Prerequisite**: Verify PR #1935 (glossary pre-formalization) has merged or is in flight. Do not introduce naming that conflicts with its definitions.

## Branch Strategy

- Planning base branch: `feat/tool-surface-contract`
- Merge target: `feat/tool-surface-contract`
- Worktree: allocated from `lanes.json` after finalize-tasks
- Command: `spec-kitty agent action implement WP01 --agent claude`

## Subtask Details

### T001 -- Create `src/specify_cli/tool_surface/` package

**Purpose**: Bootstrap the bounded context as a proper Python package.

**Steps**:
1. Create `src/specify_cli/tool_surface/__init__.py` — empty or with a brief module docstring.
2. Create `src/specify_cli/tool_surface/providers/__init__.py` — empty.
3. Do NOT add any imports in `__init__.py` yet; leave re-export decisions for after the module stabilizes.

**Files**:
- `src/specify_cli/tool_surface/__init__.py` (new)
- `src/specify_cli/tool_surface/providers/__init__.py` (new)

**Validation**:
- [ ] `python -c "import specify_cli.tool_surface"` succeeds with no errors

---

### T002 -- Implement `enums.py`

**Purpose**: Define all classification enumerations for the bounded context using `StrEnum` (Python 3.11+).

**Enumerations to implement**:

```python
class SurfaceKind(StrEnum):
    # Full 13-value enum — do NOT add a SESSION_PRESENCE value;
    # session_presence is a provider name, not a SurfaceKind.
    CONTEXT_FILE = "context_file"       # always-on orientation/context file (CLAUDE.md, AGENTS.md)
    RULE = "rule"                        # rules/steering file
    COMMAND_FILE = "command_file"        # slash-command file in global command directory
    COMMAND_SKILL = "command_skill"      # slash-command invocation skill
    DOCTRINE_SKILL = "doctrine_skill"    # managed knowledge/mission-step skill
    WORKFLOW = "workflow"                # workflow definition file
    AGENT_PROFILE = "agent_profile"      # host-native agent/subagent file
    PLUGIN_MANIFEST = "plugin_manifest"  # plugin bundle manifest
    MCP_SERVER = "mcp_server"            # MCP server config entry
    HOOK = "hook"                        # tool hook entry
    NATIVE_CONFIG = "native_config"      # tool-specific config glue
    MEMORY = "memory"                    # persistent memory file
    SETTING = "setting"                  # tool settings entry

class SourceKind(StrEnum):
    CHECKED_IN = "checked_in"
    GENERATED = "generated"
    USER_GLOBAL = "user_global"
    TEAM_GLOBAL = "team_global"
    PACKAGE = "package"
    PLUGIN = "plugin"
    EXTERNAL_REGISTRY = "external_registry"

class InstallScope(StrEnum):
    PROJECT = "project"
    USER_GLOBAL = "user_global"
    TEAM = "team"
    PLUGIN_BUNDLE = "plugin_bundle"

class ActivationMode(StrEnum):
    ALWAYS = "always"
    GLOB = "glob"
    MODEL_DECISION = "model_decision"
    MANUAL = "manual"
    USER_INVOKED = "user_invoked"
    SKILLS_INVOKABLE = "skills_invocable"
    EVENT = "event"
    DISABLED = "disabled"

class CommandSurfaceCapability(StrEnum):
    ADAPTER = "adapter"
    SKILLS_INVOKABLE = "skills_invocable"
    NONE = "none"

class MutabilityPolicy(StrEnum):
    GENERATED_OVERWRITE_IF_HASH_MATCHES = "generated_overwrite_if_hash_matches"
    PRESERVE_USER_EDITS = "preserve_user_edits"
    USER_EDITABLE = "user_editable"
    READ_ONLY_PACKAGE = "read_only_package"

class RequiredPolicy(StrEnum):
    REQUIRED = "required"
    REPAIRABLE_REQUIRED = "repairable_required"
    OPTIONAL = "optional"
    RESEARCH_GAP = "research_gap"
```

**Files**: `src/specify_cli/tool_surface/enums.py` (new, ~90 lines)

**Validation**:
- [ ] All enums have `StrEnum` base (Python 3.11+)
- [ ] `SurfaceKind` has exactly 13 values; `SESSION_PRESENCE` is NOT one of them
- [ ] `mypy --strict` passes on this file
- [ ] No imports from other `specify_cli` modules (this file has zero runtime dependencies)

---

### T003 -- Implement `model.py`

**Purpose**: Define frozen dataclasses for the bounded context's core data structures.

**Dataclasses to implement** (see `data-model.md` for the full canonical field lists):

The authoritative field list is in `data-model.md`. Implement each of these:

- `ManifestRef` (5 fields: id, path, owner, schema_version, manifest_kind)
- `InvocationSpec` (4 fields: pattern, examples, command_surface, argument_delivery)
- `ProfileProjectionSpec` (5 fields: source_layers, native_format, path_template, include_sentinel_profiles, name_template)
- `SurfaceDefinition` (20+ fields — see data-model.md; key: id, tool_key, variant, kind, provider, source_kind, install_scope, activation, required, path_template, expected_set, manifest, invocation, profile_projection, mutability, package_id, projection_id, docs_refs, test_refs, depends_on, plugin_components)
- `SurfaceInstance` (12 fields — see data-model.md)
- `SurfaceStatus` (3 fields: instance, state, findings)
- `SurfaceFinding` (9 fields — see data-model.md; finding codes are kebab-case)
- `SurfacePlan` (3 fields: config, definitions, instances)
- `SurfaceReport` (7 fields: ok, schema_version, project_root, configured_tools, summary, surfaces, findings)
- `SurfaceSummary` (6 fields: surfaces, present, missing, drifted, warnings, errors)
- `RepairResult` (5 fields: repaired, skipped, failed, dry_run, findings_after)
- `ToolHarness` (7 fields: key, display_name, variants, supported, docs_url, requires_cli, product_family)

**Files**: `src/specify_cli/tool_surface/model.py` (new, ~180 lines)

**Important**: Use `tuple` not `list` for sequence fields in frozen dataclasses. Use `Path` from `pathlib`. All fields must be type-annotated. `mypy --strict` must pass. Do NOT use `SESSION_PRESENCE` as a SurfaceKind value anywhere in this file.

**Validation**:
- [ ] All dataclasses are `frozen=True`
- [ ] No mutable default arguments
- [ ] `mypy --strict` passes
- [ ] Can be imported without side effects

---

### T004 -- Implement `registry.py` stub

**Purpose**: Define `ToolSurfaceRegistry` as the policy registry. In this WP it is a stub — the `register_provider()` method exists but providers are not wired yet.

**Interface**:
```python
class ToolSurfaceRegistry:
    """Authoritative registry for what tool surfaces should exist.

    Registry is policy; manifests are state.
    """
    def __init__(self) -> None: ...

    def register_definition(
        self,
        tool_key: str,
        definition: SurfaceDefinition,
    ) -> None: ...

    def get_definitions(self, tool_key: str) -> list[SurfaceDefinition]: ...

    def all_tool_keys(self) -> list[str]: ...
```

The registry holds `dict[str, list[SurfaceDefinition]]` internally. No provider dispatch yet — that is added in WP03.

**Files**: `src/specify_cli/tool_surface/registry.py` (new, ~60 lines)

**Validation**:
- [ ] `ToolSurfaceRegistry` is importable
- [ ] `register_definition` + `get_definitions` roundtrip works
- [ ] `mypy --strict` passes

---

### T005 -- Implement `providers/base.py`

**Purpose**: Define the `AbstractSurfaceProvider` protocol that all providers must satisfy.

```python
from collections.abc import Sequence
from typing import Protocol, runtime_checkable

@runtime_checkable
class AbstractSurfaceProvider(Protocol):
    """Protocol for surface providers.

    A provider wraps an existing installer to expand, probe, repair,
    and remove one surface kind for a given tool.
    """
    provider_key: str

    def can_handle(self, definition: SurfaceDefinition) -> bool: ...

    def expand(
        self,
        definition: SurfaceDefinition,
        tool_key: str,
        project_root: Path,
    ) -> list[SurfaceInstance]: ...

    def probe(self, instance: SurfaceInstance) -> SurfaceStatus: ...

    def repair(
        self,
        project_root: Path,
        statuses: Sequence[SurfaceStatus],
        *,
        dry_run: bool = False,
    ) -> RepairResult: ...

    def remove(self, instance: SurfaceInstance) -> bool: ...
```

`expand()` returns the concrete list of `SurfaceInstance` objects (with actual paths substituted into the `path_pattern`). `probe()` checks on-disk state for one instance and returns a `SurfaceStatus` (containing the instance + `state` string + zero-or-more `SurfaceFinding`). `repair()` takes `Sequence[SurfaceStatus]` — NOT raw paths or findings — so it preserves manifest/source/hash/refcount context; returns `RepairResult`. `remove()` removes one instance.

**Files**: `src/specify_cli/tool_surface/providers/base.py` (new, ~50 lines)

**Validation**:
- [ ] `AbstractSurfaceProvider` is a `runtime_checkable` Protocol
- [ ] `mypy --strict` passes
- [ ] No imports from outside `tool_surface` except stdlib and `pathlib`

---

### T006 -- Implement `builtins.py` stub

**Purpose**: Provide an empty (stub) set of surface definitions for all 19 supported harnesses. WP03-WP09 will populate these; this WP just establishes the structure.

**Pattern**:
```python
def register_builtin_definitions(registry: ToolSurfaceRegistry) -> None:
    """Register built-in surface definitions for all supported tools.

    Populated incrementally by WP03-WP09.
    """
    # Command skills -- registered in WP03
    # Session presence -- registered in WP04
    # Doctrine skills -- registered in WP05
    # Agent profiles -- registered in WP06
    # Plugin bundles -- registered in WP09
    pass  # stub: providers register their own definitions on init
```

Use the tool keys from `specify_cli.core.config.AI_CHOICES` (or the equivalent canonical list) to understand what `tool_key` values are valid. Do not hardcode them; import from the existing config.

**WP01 builtins scope**: `builtins.py` registers `ToolHarness` stubs for all `AI_CHOICES` keys. It does NOT register `SurfaceDefinition` objects — those are added by WP03-WP09 providers. The registry must support this two-level structure:
- `registry.get_harness(key)` — looks up a `ToolHarness` by tool key
- `registry.get_definitions(key)` — looks up `SurfaceDefinition` objects; returns `[]` if none registered yet (not an error)

**Registry behavior for unknown keys**:
- `get_definitions(unknown_key)` → returns `[]` (unknown key is valid here; providers simply haven't registered any definitions for it)
- `get_harness(unknown_key)` → raises `UnknownToolKey` structured error (not `KeyError`)

**Builtins test requirement** (T007): MUST assert:
1. Every key in `AI_CHOICES` (from `specify_cli.core.config`) resolves to a `ToolHarness` via `registry.get_harness(key)`.
2. `registry.get_harness(unknown_key)` raises `UnknownToolKey` (a structured exception, not a bare `KeyError`).
3. `registry.get_definitions(any_key)` returns a `list` (empty is fine at WP01 — providers populate this in WP03-WP09).
4. `registry.get_definitions(unknown_key)` returns `[]` (not raises).
An empty builtins.py that doesn't register ToolHarness entries for all AI_CHOICES keys is not a passing WP01. Absent SurfaceDefinitions are expected at this stage.

**Files**: `src/specify_cli/tool_surface/builtins.py` (new, ~30 lines)

**Validation**:
- [ ] `register_builtin_definitions` can be called without error
- [ ] Imports from `specify_cli.core` only for the tool key list, no other cross-module imports

---

### T007 -- Write unit tests for enums and model

**Purpose**: Cover the new type definitions with direct unit tests.

**Test file**: `tests/specify_cli/tool_surface/test_enums.py`
- All `SurfaceKind` values are distinct strings
- All `RequiredPolicy` values are distinct strings
- `StrEnum` comparison works: `SurfaceKind.COMMAND_SKILL == "command_skill"`

**Test file**: `tests/specify_cli/tool_surface/test_model.py`
- `SurfaceDefinition` is hashable (frozen dataclass)
- `SurfaceInstance` with `expected_hash=None` is valid for untracked/generated surfaces
- `SurfaceStatus` wraps a `SurfaceInstance`, a state string, and a findings tuple
- `SurfacePlan` with an empty `instances` tuple is valid
- `SurfaceFinding` with `path=None` and `repair_command=None` is valid

**Test file**: `tests/specify_cli/tool_surface/test_registry.py`
- `ToolSurfaceRegistry()` starts empty (no harnesses, no definitions)
- `register_harness` + `get_harness` roundtrips correctly
- `register_definition` + `get_definitions` roundtrips correctly
- `get_definitions` for an unknown key returns `[]` (not raises — unknown definitions are valid)
- `get_harness` for an unknown key raises `UnknownToolKey` (not a bare `KeyError`)
- `all_tool_keys()` returns registered harness keys

**Files**:
- `tests/specify_cli/tool_surface/__init__.py` (new, empty)
- `tests/specify_cli/tool_surface/providers/__init__.py` (new, empty)
- `tests/specify_cli/tool_surface/test_enums.py` (new, ~40 lines)
- `tests/specify_cli/tool_surface/test_model.py` (new, ~60 lines)
- `tests/specify_cli/tool_surface/test_registry.py` (new, ~50 lines)

**Validation**:
- [ ] `pytest tests/specify_cli/tool_surface/test_enums.py tests/specify_cli/tool_surface/test_model.py tests/specify_cli/tool_surface/test_registry.py` passes
- [ ] `mypy --strict src/specify_cli/tool_surface/` passes with zero warnings

## Definition of Done

- [ ] All files listed in `owned_files` exist
- [ ] `pytest tests/specify_cli/tool_surface/test_enums.py tests/specify_cli/tool_surface/test_model.py tests/specify_cli/tool_surface/test_registry.py` passes
- [ ] `mypy --strict src/specify_cli/tool_surface/` passes with zero warnings
- [ ] `ruff check src/specify_cli/tool_surface/` passes (zero issues, max complexity 15)
- [ ] No existing tests broken: `pytest tests/` passes
- [ ] No changes to `core.config`, `agent.config`, or `doctor.py`
- [ ] Naming convention verified: `ToolSurfaceContract`, `SurfaceKind`, not any `Agent*` variants
- [ ] All file path operations use `pathlib.Path`; no hardcoded path separators (C-010 cross-platform gate)
- [ ] `src/specify_cli/tool_surface/data/tool-surface-contract.schema.json` and `surface-status.schema.json` created with minimal but valid JSON Schema skeletons
- [ ] `builtins.py` registers `ToolHarness` stubs for all keys in `AI_CHOICES`; tests assert `get_harness(key)` succeeds for every `AI_CHOICES` key
- [ ] `registry.get_harness(unknown_key)` raises `UnknownToolKey` structured error (not bare `KeyError`); tested in T007
- [ ] `registry.get_definitions(any_key)` returns `[]` for unknown keys (not raises); tested in T007

## Risks

- **Glossary PR #1935**: If it has not merged, verify its in-flight names before committing. Record any deviation in a PR comment.
- **StrEnum availability**: Python 3.11+ only. Confirm the test environment uses Python 3.11+.
- **mypy strict**: The Protocol with `runtime_checkable` may require `from __future__ import annotations` in some environments. Test explicitly.

## Reviewer Guidance (Codex)

- Verify all new identifiers follow glossary (Tool vs. Agent distinction, `ToolSurface*` prefix)
- Verify no logic leaked into `core.config` or `doctor.py`
- Verify `frozen=True` on all dataclasses
- Verify `StrEnum` (not `Enum`) used for all enumerations
- Verify `AbstractSurfaceProvider` is `runtime_checkable`
