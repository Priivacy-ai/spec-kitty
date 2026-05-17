---
work_package_id: WP03
title: Charter Facade Modules (6 re-export modules + architectural test)
dependencies: []
requirement_refs:
- FR-012
- NFR-004
planning_base_branch: feat/org-doctrine-layer
merge_target_branch: feat/org-doctrine-layer
branch_strategy: Planning artifacts for this mission were generated on feat/org-doctrine-layer. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/org-doctrine-layer unless the human explicitly redirects the landing branch.
subtasks:
- T010
- T011
- T012
- T013
- T014
- T015
- T016
agent: claude
agent_profile: python-pedro
authoritative_surface: src/charter/profiles.py
execution_mode: code_change
owned_files:
- src/charter/profiles.py
- src/charter/mission_steps.py
- src/charter/drg.py
- src/charter/primitives.py
- src/charter/resolution.py
- src/charter/versioning.py
- tests/architectural/test_charter_facades_reexport_doctrine.py
role: implementer
history: []
tags: []
---

## Do This First: Load Agent Profile

```
/ad-hoc-profile-load python-pedro
```

---

## Objective

Create the 6 new charter facade modules under `src/charter/` that re-export the doctrine surfaces the runtime today imports directly. These are **pure re-export modules** — no behaviour, no abstractions, no thin wrappers. They exist solely to give runtime callers a `charter.*` import path that satisfies the runtime → charter → doctrine boundary rule.

This WP is independent of all schema work (WP01/WP02) and is a hard dependency for the boundary migration in WP07.

---

## Context

`docs/development/runtime-charter-doctrine-boundary.md` Appendix lists the 22 direct `from doctrine.*` imports across 13 runtime files. Each migrates to a `from charter.<facade> import ...` in WP07; this WP provides the facades.

See:
- [plan.md §1.3, §2.6](../plan.md)
- [data-model.md §8](../data-model.md)
- [contracts/charter-facade-modules.md](../contracts/charter-facade-modules.md)

---

## Branch Strategy

- **Planning/base**: `feat/org-doctrine-layer`
- **Merge target**: `feat/org-doctrine-layer`
- **Implement command**: `spec-kitty agent action implement WP03 --agent claude`

---

## Subtasks

### T010 — Create `src/charter/profiles.py`

```python
"""Charter facade for agent profile types.

Re-exports the doctrine.agent_profiles surface used by the runtime so callers
under src/specify_cli/ can import via the charter proxy (runtime → charter →
doctrine boundary per ADR 2026-03-27-1, tightened by mission
charter-mediated-doctrine-selection-01KRTZCA).
"""

from doctrine.agent_profiles.profile import AgentProfile, Role
from doctrine.agent_profiles.repository import AgentProfileRepository
from doctrine.agent_profiles.capabilities import DEFAULT_ROLE_CAPABILITIES

__all__ = [
    "AgentProfile",
    "Role",
    "AgentProfileRepository",
    "DEFAULT_ROLE_CAPABILITIES",
]
```

### T011 — Create `src/charter/mission_steps.py`

```python
"""Charter facade for mission-step-contract types."""

from doctrine.mission_step_contracts.models import (
    MissionStep,
    MissionStepContract,
)
from doctrine.mission_step_contracts.repository import (
    MissionStepContractRepository,
)

__all__ = [
    "MissionStep",
    "MissionStepContract",
    "MissionStepContractRepository",
]
```

### T012 — Create `src/charter/drg.py`

```python
"""Charter facade for DRG (Doctrine Reference Graph) types."""

from doctrine.drg import load_graph, merge_layers
from doctrine.drg.models import DRGEdge, DRGGraph, DRGNode, NodeKind, Relation
from doctrine.drg.query import ResolvedContext, resolve_context

__all__ = [
    "DRGEdge",
    "DRGGraph",
    "DRGNode",
    "NodeKind",
    "Relation",
    "load_graph",
    "merge_layers",
    "resolve_context",
    "ResolvedContext",
]
```

### T013 — Create `src/charter/primitives.py`

```python
"""Charter facade for mission primitive execution."""

from doctrine.missions import PrimitiveExecutionContext, execute_with_glossary

__all__ = [
    "PrimitiveExecutionContext",
    "execute_with_glossary",
]
```

### T014 — Create `src/charter/resolution.py`

```python
"""Charter facade for resolution-tier types."""

from doctrine.resolver import ResolutionResult, ResolutionTier

__all__ = [
    "ResolutionResult",
    "ResolutionTier",
]
```

### T015 — Create `src/charter/versioning.py`

```python
"""Charter facade for charter-bundle versioning helpers."""

from doctrine.versioning import check_bundle_compatibility, get_bundle_schema_version

__all__ = [
    "check_bundle_compatibility",
    "get_bundle_schema_version",
]
```

### T016 — Add architectural test

**File**: `tests/architectural/test_charter_facades_reexport_doctrine.py`

```python
"""Architectural guard — charter facades re-export doctrine symbols by identity.

Each facade module under src/charter/ that exists to proxy a doctrine surface
MUST re-export the exact doctrine object (object identity), not a custom
wrapper. This prevents a future PR from silently replacing a re-export with
a sneaky shim that drifts from doctrine.
"""

from __future__ import annotations

import pytest

pytestmark = [pytest.mark.architectural]


_FACADE_TABLE = {
    "charter.profiles": [
        ("AgentProfile", "doctrine.agent_profiles.profile"),
        ("Role", "doctrine.agent_profiles.profile"),
        ("AgentProfileRepository", "doctrine.agent_profiles.repository"),
        ("DEFAULT_ROLE_CAPABILITIES", "doctrine.agent_profiles.capabilities"),
    ],
    "charter.mission_steps": [
        ("MissionStep", "doctrine.mission_step_contracts.models"),
        ("MissionStepContract", "doctrine.mission_step_contracts.models"),
        ("MissionStepContractRepository", "doctrine.mission_step_contracts.repository"),
    ],
    "charter.drg": [
        ("DRGEdge", "doctrine.drg.models"),
        ("DRGGraph", "doctrine.drg.models"),
        ("DRGNode", "doctrine.drg.models"),
        ("NodeKind", "doctrine.drg.models"),
        ("Relation", "doctrine.drg.models"),
        ("load_graph", "doctrine.drg"),
        ("merge_layers", "doctrine.drg"),
        ("resolve_context", "doctrine.drg.query"),
        ("ResolvedContext", "doctrine.drg.query"),
    ],
    "charter.primitives": [
        ("PrimitiveExecutionContext", "doctrine.missions"),
        ("execute_with_glossary", "doctrine.missions"),
    ],
    "charter.resolution": [
        ("ResolutionResult", "doctrine.resolver"),
        ("ResolutionTier", "doctrine.resolver"),
    ],
    "charter.versioning": [
        ("check_bundle_compatibility", "doctrine.versioning"),
        ("get_bundle_schema_version", "doctrine.versioning"),
    ],
}


@pytest.mark.parametrize(
    "facade_module,symbol,doctrine_module",
    [
        (facade, symbol, doctrine)
        for facade, items in _FACADE_TABLE.items()
        for symbol, doctrine in items
    ],
)
def test_facade_reexports_doctrine_symbol_by_identity(
    facade_module: str, symbol: str, doctrine_module: str
) -> None:
    facade = __import__(facade_module, fromlist=[symbol])
    doctrine = __import__(doctrine_module, fromlist=[symbol])
    assert getattr(facade, symbol) is getattr(doctrine, symbol), (
        f"{facade_module}.{symbol} must be the same object as "
        f"{doctrine_module}.{symbol}. Facade modules are pure re-exports — "
        "no wrappers, no aliases, no shims."
    )
```

---

## Definition of Done

- ✅ All 6 facade modules exist and import cleanly
- ✅ `tests/architectural/test_charter_facades_reexport_doctrine.py` passes (parametrised × ~22 symbols)
- ✅ `tests/architectural/test_layer_rules.py` — 8/8 stays green (charter is allowed to import doctrine)
- ✅ `tests/architectural/test_runtime_charter_doctrine_boundary.py` stays green (no runtime files migrated yet — happens in WP07)
- ✅ `from charter.profiles import AgentProfile` (and the other 5 facades) works in a Python repl

---

## Risks

| Risk | Mitigation |
|------|------------|
| A facade re-exports a symbol that does not exist in the named doctrine module | The architectural test catches this at parametrise time. |
| A facade introduces logic beyond re-export | Reviewer guidance + the identity-check test (object IS doctrine object). |
| Symbol name conflict between two `from doctrine.<sub> import` lines | Use explicit imports per source module; never `from doctrine import *`. |

---

## Reviewer Guidance

- Read each facade — confirm it's pure re-export, no logic.
- Run the new architectural test; confirm it parametrises ~22 cases (matches the import inventory in the boundary audit).
- Confirm no facade file exceeds 20 lines (signal of accidental logic creep).
- These modules MUST land before WP07; verify the dependency is honoured by `lanes.json`.
