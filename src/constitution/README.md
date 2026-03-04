# Constitution Package

The `constitution` package is the **Governance Onboarding and Action Context** system for Spec Kitty. It is a standalone peer package alongside `doctrine` and `specify_cli`.

## Purpose

Constitution sits at the boundary between the Human in Charge (HiC) and the doctrine knowledge stack. It:

1. **Captures governance intent** — guides the HiC through a structured interview to record their project's operating constraints, quality rules, and doctrine preferences.
2. **Compiles governance bundles** — resolves the HiC's selections transitively through the doctrine graph (directive → tactic → styleguide/toolguide chains) and produces `.kittify/constitution/` output files.
3. **Injects action-scoped context** — at every execution boundary, resolves which governance applies to the current action (specify/plan/implement/review) using a two-stage intersection: Action Index ∩ project selections.

## Architectural Position

`constitution` is a **peer container** to `doctrine` in the Spec Kitty 2.x landscape. It consumes `doctrine` (reads artifact repositories via `DoctrineService`) but is not part of it. The separation enforces the principle that Doctrine is a standalone knowledge library, while Constitution is application-layer orchestration.

```
spec-kitty 2.x landscape

  specify_cli  ──────────────────────────────────────────┐
  (control plane, kitty-core, event store, orchestration) │
                                                          │
  constitution  ────────────────────► doctrine            │
  (governance onboarding, context bootstrap)  (artifacts) │
                                                          │
  └──────────────────────────────────────────────────────┘
```

**Dependency direction:** `constitution` → `doctrine` and `specify_cli.runtime`. Neither `doctrine` nor `specify_cli` should import from `constitution`.

## Module Map

| Module | Responsibility |
|---|---|
| `catalog.py` | Discovers available doctrine artifacts; provides `DoctrineCatalog` for interview and compiler use |
| `interview.py` | `ConstitutionInterview` — guided Q&A that writes `answers.yaml` |
| `compiler.py` | `compile_constitution()` — transitive resolution producing `constitution.md` + `references.yaml` |
| `reference_resolver.py` | DFS walker building `ResolvedReferenceGraph`; raises `DoctrineResolutionCycleError` on cycles |
| `context.py` | `build_constitution_context()` — action-scoped governance injection with depth semantics (1=compact, 2=bootstrap, 3=extended) |
| `resolver.py` | `resolve_governance()` — profile-aware governance resolution, `GovernanceResolution` output |
| `generator.py` | High-level `ConstitutionDraft` builder wrapping interview + compiler |
| `sync.py` | `sync()` — parses `constitution.md` and writes structured YAML sidecars |
| `parser.py` | `ConstitutionParser` — markdown section extraction |
| `extractor.py` | Structured field extraction from parsed sections |
| `schemas.py` | Pydantic models for governance configuration |
| `hasher.py` | Content fingerprinting for staleness detection |

## Key Entry Points

### Governance setup (CLI)

```bash
spec-kitty constitution interview   # Capture HiC governance preferences
spec-kitty constitution generate    # Compile answers into governance bundle
```

### Runtime context injection (Agent tools)

```bash
spec-kitty constitution context --action implement --depth 2
```

### Python API

```python
from constitution.compiler import compile_constitution
from constitution.context import build_constitution_context
from constitution.interview import ConstitutionInterview
from constitution.resolver import resolve_governance
```

## Cycle Detection

`reference_resolver.py` raises `DoctrineResolutionCycleError` (from `doctrine.shared.exceptions`) when a cycle is detected in the artifact reference graph. Cycles are always configuration errors — they indicate a misconfigured doctrine artifact set.

See `tests/doctrine/test_cycle_detection.py` for acceptance tests.

## Related Documentation

- Architecture: `architecture/2.x/03_components/README.md` — `ConstitutionContainer` section
- Implementation mapping: `architecture/2.x/04_implementation_mapping/README.md` — Loop C (Governance)
- Glossary: `glossary/contexts/governance.md` — Constitution terms
- Source of doctrine it consumes: `src/doctrine/`
