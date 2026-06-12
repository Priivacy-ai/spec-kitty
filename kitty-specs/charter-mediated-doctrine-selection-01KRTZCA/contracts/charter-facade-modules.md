# Contract — Charter Facade Modules

> Mission: `charter-mediated-doctrine-selection-01KRTZCA`
> Companions: [selection-schema.md](selection-schema.md), [activation-registry.md](activation-registry.md), [mission-type-profile.md](mission-type-profile.md)

Six new modules under `src/charter/` that re-export the doctrine surfaces today's runtime imports directly. The facades exist to satisfy the runtime → charter → doctrine boundary (C-001) without forcing the runtime to learn new APIs.

---

## Input Contract

### File-system layout

```
src/charter/
  profiles.py         (NEW)
  mission_steps.py    (NEW)
  drg.py              (NEW)
  primitives.py       (NEW)
  resolution.py       (NEW)
  versioning.py       (NEW)
```

### Module shape (uniform across all six)

Each facade module is a re-export-only Python file:

```python
"""<one-line purpose>.

This module is the charter-layer proxy for runtime callers that historically
imported from doctrine.<sub> directly. The runtime → charter → doctrine
boundary (ADR 2026-03-27-1, tightened by mission
charter-mediated-doctrine-selection-01KRTZCA) requires runtime modules
under src/specify_cli/ to reach doctrine artifacts only through such
charter facades.
"""

from doctrine.<sub> import (
    <SymbolA>,
    <SymbolB>,
    ...
)

__all__ = [
    "<SymbolA>",
    "<SymbolB>",
    ...
]
```

No additional logic. No thin wrappers. No type aliases. Pure re-exports.

### Symbol tables

| Facade | Re-exported symbols |
|--------|---------------------|
| `charter/profiles.py` | `AgentProfile`, `AgentProfileRepository`, `Role`, `DEFAULT_ROLE_CAPABILITIES` |
| `charter/mission_steps.py` | `MissionStep`, `MissionStepContract`, `MissionStepContractRepository` |
| `charter/drg.py` | `DRGEdge`, `DRGGraph`, `DRGNode`, `Relation`, `NodeKind`, `load_graph`, `merge_layers`, `resolve_context`, `ResolvedContext` |
| `charter/primitives.py` | `PrimitiveExecutionContext`, `execute_with_glossary` |
| `charter/resolution.py` | `ResolutionResult`, `ResolutionTier` |
| `charter/versioning.py` | `check_bundle_compatibility`, `get_bundle_schema_version` |

---

## Output Contract

### What the runtime calls

Before:

```python
# src/specify_cli/invocation/registry.py
from doctrine.agent_profiles.profile import AgentProfile
from doctrine.agent_profiles.repository import AgentProfileRepository
```

After:

```python
# src/specify_cli/invocation/registry.py
from charter.profiles import AgentProfile, AgentProfileRepository
```

The symbol is the same object (`charter.profiles.AgentProfile is doctrine.agent_profiles.profile.AgentProfile`). Type annotations, `isinstance()` checks, and subclass relationships behave identically.

### Boundary ratchet allowlist update

Each migration removes one entry from `tests/architectural/test_runtime_charter_doctrine_boundary.py::_BASELINE_ALLOWLIST`. The test fails on stale allowlist entries (entries whose underlying import has been migrated), so the allowlist stays honest.

Final state: at most 2 documented exceptions in the allowlist (C-004 cap), with the rationale documented in the test docstring.

---

## Failure Modes

| Failure | Behaviour |
|---------|-----------|
| Facade module missing a symbol the runtime expects | `ImportError` at runtime caller load time. Add the missing symbol to the facade's `__all__` + import block. |
| Doctrine renames or removes a symbol the facade re-exports | Facade `ImportError` at module load. Adjust the doctrine import or fork a stable surface in charter. |
| Runtime caller adds a new `from doctrine.*` import outside the allowlist | `test_runtime_charter_doctrine_boundary.py::test_runtime_has_no_new_direct_doctrine_imports` fails with the file name + fix recipe. |
| Runtime caller migrates but forgets to update the allowlist | Same test fails: "Stale boundary allowlist entries" — the message tells the maintainer to remove the entry. |
| Runtime caller imports a doctrine symbol the facade doesn't re-export | Add the symbol to the facade's `__all__` AND import block. The boundary test stays green. |
| Facade introduces logic beyond re-export | Architectural smell — facades are by-design re-exports. Implementation in WP03 review MUST reject any non-re-export logic landing in a facade module. |

---

## Backward Compatibility Guarantee

- Pre-migration runtime callers continue to work — `doctrine.<sub>` modules remain importable and the boundary test allows current direct imports via the baseline allowlist.
- Migration is per-file. WP07 migrates the 13 baseline files in sequence; each migration is independently verifiable (per-file tests + the boundary ratchet).
- Charter internal modules that today import `from doctrine.*` (e.g. `charter.context`, `charter.template_resolver`) are **unaffected**. The boundary rule applies only to `src/specify_cli/`, not to `src/charter/`. Facades and direct doctrine imports coexist within `src/charter/` without contradiction.
- The 8 layer-rule tests in `tests/architectural/test_layer_rules.py` continue to pass — the ADR layering of `kernel ← doctrine ← charter ← specify_cli` is preserved (charter is allowed to import doctrine; facades re-export from there).

---

## Architectural Test Gates

- `tests/architectural/test_runtime_charter_doctrine_boundary.py::test_runtime_has_no_new_direct_doctrine_imports` (boundary ratchet)
- `tests/architectural/test_layer_rules.py` — 8/8 (layer dependency rules)

Optional test (recommended for WP03):

- `tests/architectural/test_charter_facades_reexport_doctrine.py` (NEW): asserts each facade module's `__all__` symbols resolve to objects equal to their `doctrine.*` counterparts. Pinning this prevents a future PR from silently replacing a facade re-export with a custom wrapper.

---

## Note on the `SchemaUtilities` Exception

`bulk_edit/occurrence_map.py` consumes `SchemaUtilities` from `doctrine.shared.schema_utils`. Per the boundary audit, this is promoted to `kernel/schema_utils.py` rather than routed through charter — `SchemaUtilities` is a generic schema helper that belongs in the lowest layer.

The migration sequence:

1. Add `src/kernel/schema_utils.py` re-exporting / hosting `SchemaUtilities`.
2. Update `src/specify_cli/bulk_edit/occurrence_map.py` to `from kernel.schema_utils import SchemaUtilities`.
3. Remove `src/specify_cli/bulk_edit/occurrence_map.py` from the boundary allowlist.
4. (Optional follow-up) Remove the `doctrine.shared.schema_utils` re-export, leaving `kernel/` as the canonical home.

Step 4 is **not in scope** for this mission; step 1-3 are sufficient to drop the file from the allowlist.

---

## Addendum (2026-06-11, append-only)

`MissionStep` is retired from the `charter/mission_steps.py` facade `__all__` contract: the last `src/`
consumer (`mission_step_contracts/executor.py`) was correctly retyped to `MissionStepContractStep` during
the typing debt pass, leaving the facade entry unimported (dead-symbol gate). The symbol remains available
as an explicit PEP 484 re-export (`import ... as ...`) for direct importers (one test consumer). The live
symbol table is `tests/architectural/test_charter_facades_reexport_doctrine.py::_FACADE_TABLE`.
