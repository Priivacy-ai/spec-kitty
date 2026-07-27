---
work_package_id: WP03
title: Tool Surface Registry Infrastructure
dependencies: []
requirement_refs:
- FR-007
- FR-009
- FR-010
tracker_refs: []
planning_base_branch: fix/cli-bug-sweep-tool-surface-self-registration
merge_target_branch: fix/cli-bug-sweep-tool-surface-self-registration
branch_strategy: Planning artifacts for this mission were generated on fix/cli-bug-sweep-tool-surface-self-registration. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/cli-bug-sweep-tool-surface-self-registration unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-cli-bug-sweep-tool-surface-self-registration-01KV5AWE
base_commit: db0d66f23b8a678b0e2c21a79d02749d233f80cf
created_at: '2026-06-15T11:25:23.879779+00:00'
subtasks:
- T009
- T010
- T011
agent: claude
shell_pid: '18132'
history:
- date: '2026-06-15'
  event: created
agent_profile: python-pedro
authoritative_surface: src/specify_cli/tool_surface/
create_intent:
- src/specify_cli/tool_surface/providers/_registry.py
- src/specify_cli/tool_surface/providers/_discovery.py
execution_mode: code_change
owned_files:
- src/specify_cli/tool_surface/providers/_registry.py
- src/specify_cli/tool_surface/providers/_discovery.py
- src/specify_cli/tool_surface/service.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your assigned profile:

```
/ad-hoc-profile-load python-pedro
```

---

## Objective

Create the `SurfaceRegistration` dataclass, `SurfaceProviderRegistry` class store, and `_discovery.py` explicit import tuple. Refactor `service.py` to derive all provider configuration from the registry. WP04 migrates the individual providers; this WP establishes the infrastructure they will register against.

## Branch Strategy

- **Implementation branch**: allocated by `spec-kitty agent action implement WP03 --agent claude`
- **Planning/base branch**: `fix/cli-bug-sweep-tool-surface-self-registration`
- **Final merge target**: `fix/cli-bug-sweep-tool-surface-self-registration`

## Context

### Current structure in `service.py`

`src/specify_cli/tool_surface/service.py` has four hand-maintained literal regions:
1. **Imports** — ~15 symbols from 7 provider modules
2. **`_KIND_TOKENS`** — hard-coded dict of 12 CLI token strings → `SurfaceKind` values
3. **`build_providers()`** — constructs 7 provider instances in a list
4. **`build_registry()`** — calls 9 definition factory functions; handles the `plugin_bundle` synthetic-key case separately

Adding any provider requires editing all four regions simultaneously. This causes merge conflicts in parallel lanes.

### Reference pattern: `MigrationRegistry`

`src/specify_cli/upgrade/registry.py` has `MigrationRegistry` with a class-variable `_migrations` dict and a `@classmethod register()` that fires at module import time. Each migration module in `migrations/` applies the decorator at class definition time. `auto_discover_migrations()` uses pkgutil to import all `m_*.py` modules.

**For the tool surface seam, use the same conceptual pattern but an explicit import tuple instead of pkgutil** — required by the dead-symbol static analysis gate (C-001).

### Key special cases from the current `service.py`

- **`session_presence`**: contributes 3 definitions (`context_file_definition`, `hook_definition`, `rule_definition`). `SurfaceRegistration.definitions` must be a tuple, not a single field.
- **`plugin_bundle`**: registers under `PLUGIN_BUNDLE_TOOL_KEY` (a synthetic key), not the standard per-tool-key fan-out. `SurfaceRegistration.synthetic_key: str | None`.
- **Underscore aliases**: `_KIND_TOKENS` contains both `"context-file"` and `"context_file"` pointing to the same `SurfaceKind`. `SurfaceRegistration.kind_tokens: dict[str, SurfaceKind]` allows multiple tokens per provider.
- **`_BUNDLE_SOURCE_TOOL_KEYS`**: a tuple `("codex", "claude", "copilot", "vibe")` used in `build_plans_for_bundles()`. This is a projection scope filter, NOT provider identity. Leave it as a module-level constant in `service.py`; do not include it in `SurfaceRegistration`.
- **`plugin_bundle.py` lazy import**: `plugin_bundle.py` imports `build_plans_for_bundles` from `service.py` inside a method body to avoid a circular import. Do NOT change this workaround during WP03 or WP04.

---

## Subtask T009 — Create `_registry.py`

**Purpose**: Define `SurfaceRegistration` (the per-provider declaration unit) and `SurfaceProviderRegistry` (the class-variable aggregator).

**Steps**:

1. Read `src/specify_cli/tool_surface/providers/` to understand existing module names and the import paths. Read `src/specify_cli/upgrade/registry.py` for the `MigrationRegistry` pattern to use as structural reference.

2. Read `src/specify_cli/tool_surface/service.py` in full to understand the exact types used: `ReportingSurfaceProvider`, `SurfaceDefinition`, `SurfaceKind`, `ToolSurfaceRegistry`. Find where these are defined.

3. Create `src/specify_cli/tool_surface/providers/_registry.py`:

```python
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..registry import ToolSurfaceRegistry
    from ..protocol import ReportingSurfaceProvider, SurfaceDefinition, SurfaceKind


@dataclass(frozen=True)
class SurfaceRegistration:
    """Declaration unit produced by each provider module at import time."""

    provider_class: type[ReportingSurfaceProvider]
    definitions: tuple[SurfaceDefinition, ...]
    kind_tokens: dict[str, SurfaceKind]
    synthetic_key: str | None = None
    order: int = 0
```

   Adapt the exact imports to match the actual module structure (the type names and paths above are representative — confirm by reading the existing source).

4. Add `SurfaceProviderRegistry` to the same file:

```python
class SurfaceProviderRegistry:
    """Aggregates SurfaceRegistration instances; providers register at import time."""

    _registrations: list[SurfaceRegistration] = []

    @classmethod
    def register(cls, reg: SurfaceRegistration) -> None:
        orders = {r.order for r in cls._registrations}
        if reg.order in orders:
            raise ValueError(f"Duplicate SurfaceRegistration order: {reg.order}")
        cls._registrations.append(reg)

    @classmethod
    def _sorted(cls) -> list[SurfaceRegistration]:
        return sorted(cls._registrations, key=lambda r: r.order)

    @classmethod
    def build_kind_tokens(cls) -> dict[str, SurfaceKind]:
        result: dict[str, SurfaceKind] = {}
        for reg in cls._sorted():
            result.update(reg.kind_tokens)
        return result

    @classmethod
    def build_providers(cls) -> list[ReportingSurfaceProvider]:
        return [reg.provider_class() for reg in cls._sorted()]

    @classmethod
    def build_registry(cls, tool_keys: ..., project_root: ...) -> ToolSurfaceRegistry:
        # Read the current service.py build_registry() in full before writing this.
        # Key invariants:
        #   1. For providers WITHOUT synthetic_key: call their definition factories
        #      once per entry in tool_keys, keyed by tool_key.
        #   2. For providers WITH synthetic_key (plugin_bundle): register definitions
        #      ONCE under synthetic_key — unconditionally, NOT gated on tool_keys.
        #      This mirrors the current `build_registry()` lines 149–154 exactly.
        #
        # Pseudocode:
        #   registry = ToolSurfaceRegistry(...)
        #   for reg in cls._sorted():
        #       if reg.synthetic_key is not None:
        #           # unconditional single registration
        #           for defn in reg.definitions:
        #               registry.register(reg.synthetic_key, defn(...))
        #       else:
        #           for tool_key in tool_keys:
        #               for defn in reg.definitions:
        #                   registry.register(tool_key, defn(tool_key=tool_key, ...))
        #   return registry
        ...
```

   **Critical**: match the exact signature of `build_registry()` in `service.py` — read it before writing this method. The `tool_keys` and `project_root` types are already declared there. The `plugin_manifest_definition()` registration under `PLUGIN_BUNDLE_TOOL_KEY` must remain unconditional.

5. Ensure the module passes `mypy --strict` with zero errors and `ruff check` with zero issues.

**Validation**:
- `python -c "from specify_cli.tool_surface.providers._registry import SurfaceRegistration, SurfaceProviderRegistry; print('ok')"` succeeds.
- `mypy src/specify_cli/tool_surface/providers/_registry.py --strict` passes.

---

## Subtask T010 — Create `_discovery.py`

**Purpose**: Provide an explicit import tuple of all 7 provider modules so that importing `_discovery` fires all registration calls, while remaining traceable by the dead-symbol static analysis gate.

**Steps**:

1. Create `src/specify_cli/tool_surface/providers/_discovery.py`:

```python
"""Explicit provider discovery — imports all provider modules to fire their registrations.

This module must use an explicit import tuple, not pkgutil, to remain
compatible with the project's dead-symbol static analysis gate.
"""

from . import (
    agent_profiles,
    command_skills,
    managed_skills,
    native_config,
    plugin_bundle,
    session_presence,
    slash_commands,
)

# Explicit tuple ensures each module is traceable as a referenced symbol.
_PROVIDERS = (
    agent_profiles,
    command_skills,
    managed_skills,
    native_config,
    plugin_bundle,
    session_presence,
    slash_commands,
)
```

2. **At this point in WP03, provider modules have not yet been updated** (that is WP04's job). The imports will succeed because the provider modules already exist; they just won't call `SurfaceProviderRegistry.register()` yet. That is expected — WP03 establishes infrastructure; WP04 wires providers.

3. **Placement constraint**: each provider module's `SurfaceProviderRegistry.register(...)` call (added in WP04) must appear at **module scope** — i.e., at the top level of the `.py` file, after the class and function definitions but not inside any function or conditional block. Importing a module from `_discovery.py` fires module-level code only; code inside functions is not executed at import time.

3. `mypy src/specify_cli/tool_surface/providers/_discovery.py --strict` must pass.

**Validation**:
- `python -c "from specify_cli.tool_surface.providers._discovery import _PROVIDERS; print(len(_PROVIDERS))"` prints `7`.
- No import errors.

---

## Subtask T011 — Refactor `service.py` to Consume Registry

**Purpose**: Remove the four central literal regions from `service.py` and replace them with registry-derived calls.

**Steps**:

1. Read `src/specify_cli/tool_surface/service.py` carefully in full before making any changes. Understand every region: the import block, `_KIND_TOKENS`, `build_providers()`, `build_registry()`, and `_BUNDLE_SOURCE_TOOL_KEYS`.

2. **Replace the import block** (region 1):
   - Remove the ~15 multi-symbol imports from provider modules.
   - Add: `from .providers._discovery import _PROVIDERS  # noqa: F401 — imported for side-effects (registration)`
   - Add: `from .providers._registry import SurfaceProviderRegistry`
   - (The `noqa: F401` is acceptable here since `_PROVIDERS` is imported solely to fire registrations, not used directly in this module. Alternatively, reference `_PROVIDERS` in `__all__` or in a docstring.)

3. **Replace `_KIND_TOKENS`** (region 2):
   ```python
   _KIND_TOKENS: dict[str, SurfaceKind] = SurfaceProviderRegistry.build_kind_tokens()
   ```
   Note: at module load time (WP03 only, before WP04 wires providers), this will return an empty dict. That is expected and temporary.

4. **Replace `build_providers()`** (region 3):
   ```python
   def build_providers() -> list[ReportingSurfaceProvider]:
       return SurfaceProviderRegistry.build_providers()
   ```

5. **Replace `build_registry()` body** (region 4): delegate to `SurfaceProviderRegistry.build_registry(tool_keys, project_root)`. The public signature of `build_registry()` must remain unchanged.

6. **Keep `_BUNDLE_SOURCE_TOOL_KEYS` unchanged** — it is a projection scope filter used by `build_plans_for_bundles()`, not provider identity.

7. **Keep all other functions and classes in `service.py` unchanged** (`run_tool_surfaces()`, `SurfaceStatusService`, etc.).

8. After the refactor, `service.py` must contain NO list/dict literals that enumerate provider-specific data. This is the Directive-030 invariant that WP04's conformance test will assert.

**Validation**:
- `mypy src/specify_cli/tool_surface/service.py --strict` → zero errors.
- `ruff check src/specify_cli/tool_surface/service.py` → zero issues.
- `pytest tests/specify_cli/tool_surface/ -v` → all pre-existing tests pass (some may need minor adaptation if they mock `build_providers()` directly — update mocks to use the registry, do not weaken them).

---

## Definition of Done

- [ ] `_registry.py` created with `SurfaceRegistration` dataclass and `SurfaceProviderRegistry` class, both mypy-clean.
- [ ] `_discovery.py` created with explicit 7-module import tuple, mypy-clean.
- [ ] `service.py` refactored: no central provider imports, no `_KIND_TOKENS` literal, `build_providers()` and `build_registry()` delegating to registry.
- [ ] All existing `tool_surface` tests pass — tests that previously relied on the hardcoded provider list (e.g. `test_managed_skills.py::surface_kind_from_token` calls, `test_drift_policy.py` mocks of `build_providers`) must be updated to either pre-populate the registry in a fixture or mock the registry output. Do not skip or weaken them; the empty-registry state is expected and temporary.
- [ ] Branch coverage on `_registry.py` and `_discovery.py` is ≥ 90%: `pytest tests/specify_cli/tool_surface/ --cov=src/specify_cli/tool_surface/providers/_registry --cov=src/specify_cli/tool_surface/providers/_discovery --cov-report=term-missing --cov-fail-under=90` passes.
- [ ] `mypy src/specify_cli/tool_surface/ --strict` → zero errors.
- [ ] `ruff check src/specify_cli/tool_surface/` → zero issues.

## Risks for Reviewer

- At the end of WP03, `SurfaceProviderRegistry._registrations` is empty (providers haven't registered yet — that's WP04). This means `build_providers()` returns `[]` and `_KIND_TOKENS` is `{}`. The existing tests that test `build_providers()` or `surface_kind_from_token()` must be updated to pre-populate the registry in their fixture — do NOT mock them away or mark them as xfail. Document the fixture pattern used; WP04's conformance test will rely on the same approach.
- The `build_registry()` refactor must handle the `plugin_bundle` synthetic-key case exactly as the current implementation does. **The `plugin_manifest_definition()` call for `plugin_bundle` is registered unconditionally — it is NOT gated on membership in `tool_keys`.** Read lines 149–154 of the current `build_registry()` carefully: the plugin-manifest entry is added via a separate code path from the per-tool-key fan-out. The registry's `build_registry()` must preserve this unconditional behavior, or `plugin_bundle` provider data will be silently absent from sessions that don't include the synthetic key in their tool set.
- `service.py` must import `_discovery` at module scope (e.g. `from .providers._discovery import _PROVIDERS  # noqa: F401`) before any call to `SurfaceProviderRegistry.build_providers()` or `build_registry()`. If `_discovery` is only imported lazily or inside a function, the registry will be empty when `service.py`'s module-level `_KIND_TOKENS` assignment evaluates.
- Each provider module's `SurfaceProviderRegistry.register(...)` call must appear at module scope (not inside a function, class, or `if __name__ == "__main__"` block). Importing the provider module from `_discovery.py` fires module-level code only; code inside functions is not executed at import time.
- Do not attempt to resolve the `plugin_bundle.py` ↔ `service.py` circular import during this WP. The lazy import inside the method body is the correct workaround; leave it as-is.
- **Test isolation**: any unit test that touches `SurfaceProviderRegistry` in isolation (e.g. tests of `_registry.py` alone) must reset `SurfaceProviderRegistry._registrations = []` in a fixture teardown or use `monkeypatch.setattr` to avoid state leaking from other tests that import `_discovery`.
