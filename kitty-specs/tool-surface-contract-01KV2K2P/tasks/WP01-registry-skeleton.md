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
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
- T007
agent: claude
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
    COMMAND_SKILL = "command_skill"
    DOCTRINE_SKILL = "doctrine_skill"
    SESSION_PRESENCE = "session_presence"
    AGENT_PROFILE = "agent_profile"
    PLUGIN_MANIFEST = "plugin_manifest"
    NATIVE_CONFIG = "native_config"
    COMMAND_FILE = "command_file"

class SourceKind(StrEnum):
    CHECKED_IN = "checked_in"
    GENERATED = "generated"
    USER_GLOBAL = "user_global"
    PACKAGE = "package"
    PLUGIN = "plugin"

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

**Files**: `src/specify_cli/tool_surface/enums.py` (new, ~60 lines)

**Validation**:
- [ ] All enums have `StrEnum` base (Python 3.11+)
- [ ] `mypy --strict` passes on this file
- [ ] No imports from other `specify_cli` modules (this file has zero runtime dependencies)

---

### T003 -- Implement `model.py`

**Purpose**: Define frozen dataclasses for the bounded context's core data structures.

**Dataclasses to implement**:

```python
@dataclass(frozen=True)
class SurfaceDefinition:
    kind: SurfaceKind
    source_kind: SourceKind
    install_scope: InstallScope
    path_pattern: str          # e.g. ".agents/skills/spec-kitty.{command}/SKILL.md"
    required_policy: RequiredPolicy
    activation_mode: ActivationMode
    provider_key: str
    repair_hint: str

@dataclass(frozen=True)
class SurfaceInstance:
    definition: SurfaceDefinition
    path: Path
    exists: bool
    file_hash: str | None      # SHA-256 of file content, or None if absent/unhashable
    owner: str

@dataclass(frozen=True)
class SurfacePlan:
    tool_key: str
    instances: tuple[SurfaceInstance, ...]   # tuple for hashability
    computed_at: str                          # ISO timestamp

@dataclass(frozen=True)
class SurfaceFinding:
    code: str
    tool_key: str
    surface_kind: SurfaceKind
    severity: str              # "error" | "warning" | "info" | "research_gap"
    path: Path | None
    repair_command: str | None
    detail: str

@dataclass(frozen=True)
class NativeAgentProfile:
    profile_urn: str
    source_layer: str          # "builtin" | "org" | "project"
    tool_key: str
    output_path: Path
    format: str
    file_hash: str | None
```

**Files**: `src/specify_cli/tool_surface/model.py` (new, ~80 lines)

**Important**: Use `tuple` not `list` for sequence fields in frozen dataclasses. Use `Path` from `pathlib`. All fields must be type-annotated. `mypy --strict` must pass.

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

    def probe(self, instance: SurfaceInstance) -> SurfaceInstance: ...

    def repair(self, instance: SurfaceInstance) -> bool: ...

    def remove(self, instance: SurfaceInstance) -> bool: ...
```

`expand()` returns the concrete list of `SurfaceInstance` objects (with actual paths substituted into the `path_pattern`). `probe()` re-checks `exists` and `file_hash` for a known instance. `repair()` runs the underlying installer to create/restore the file. `remove()` removes it.

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

**Builtins test requirement**: The test for builtins.py (T007) MUST assert:
1. Every key in `AI_CHOICES` (from `specify_cli.core.config`) has a corresponding `ToolHarness` entry in the registry.
2. Every supported tool (where `harness.supported == True`) exposes at least one `SurfaceDefinition` with `required=RequiredPolicy.REPAIRABLE_REQUIRED`.
3. The registry raises a structured error (not a KeyError) when asked for an unknown tool key.
An empty builtins.py stub that does not fail these assertions is not a passing WP01.

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
- `SurfaceInstance` with `exists=False` has `file_hash=None`
- `SurfacePlan` with an empty `instances` tuple is valid
- `SurfaceFinding` with `path=None` and `repair_command=None` is valid

**Test file**: `tests/specify_cli/tool_surface/test_registry.py`
- `ToolSurfaceRegistry()` starts empty
- `register_definition` + `get_definitions` roundtrips correctly
- `get_definitions` for an unknown key returns empty list (not raises)
- `all_tool_keys()` returns registered keys

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
- [ ] `builtins.py` has at minimum stub harness entries for all keys in `AI_CHOICES`; tests assert all `AI_CHOICES` keys resolve to a `ToolHarness`
- [ ] Registry raises a structured error for unknown tool keys (tested in T007)

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
