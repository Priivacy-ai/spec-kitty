# Implementation Plan: Structured Agent Identity & Constitution-Profile Integration

**Branch**: `feature/agent-profile-implementation` | **Date**: 2026-03-08 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `kitty-specs/048-structured-agent-identity-and-constitution-profile-integration/spec.md`

## Summary

Replace bare-string agent identifiers with a structured 4-part identity (`tool:model:profile:role`) and wire the constitution compiler to doctrine domain models for profile-aware governance compilation. The feature is split into two parallel tracks:

- **Track A** (WP01–WP03): Introduce `ActorIdentity` dataclass, update frontmatter read/write, and add CLI flags for structured identity.
- **Track B** (WP04–WP07): Expand `DoctrineCatalog` to cover all artifact types, build a transitive reference resolver, inject `DoctrineService` into the compiler, and add profile-aware governance compilation.
- **Convergence** (WP08): End-to-end integration tests validating both tracks.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: typer, rich, ruamel.yaml, pydantic (doctrine models)
**Storage**: Filesystem only — JSONL event log, YAML frontmatter, YAML doctrine assets
**Testing**: pytest (90%+ coverage for new code), mypy --strict
**Target Platform**: Cross-platform (Linux, macOS, Windows 10+)
**Project Type**: Single project — existing `src/specify_cli/` and `src/doctrine/` packages
**Performance Goals**: CLI operations < 2 seconds for typical projects
**Constraints**: No event log migration (C-001), no frontmatter migration (C-002), compiler fallback required (C-003)
**Scale/Scope**: Touches ~15 source files across `status/`, `constitution/`, `doctrine/`, and `cli/` packages

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Constitution Gate | Status | Notes |
|---|---|---|
| Python 3.11+ | ✅ Pass | All new code targets Python 3.11+ |
| typer / rich / ruamel.yaml | ✅ Pass | No new framework dependencies |
| pytest 90%+ coverage | ✅ Pass | Each WP has dedicated test file; WP08 adds integration tests |
| mypy --strict | ✅ Pass | All new dataclasses and functions will be fully typed |
| CLI < 2s | ✅ Pass | No new heavy operations; transitive resolution is bounded by doctrine asset count |
| Cross-platform | ✅ Pass | No platform-specific code |
| `rg` preferred over `grep` | ✅ Pass | No search operations in feature code |
| No `pip -e` local deps | ✅ Pass | No new external dependencies |
| 2.x branch target | ✅ Pass | Feature branch merges to 2.x development line |
| No event log migration (C-001) | ✅ Pass | Backwards-compatible serialisation; old JSONL files read as-is |
| No frontmatter migration (C-002) | ✅ Pass | Scalar `agent:` values coerced at read boundary |
| Compiler fallback (C-003) | ✅ Pass | Legacy YAML-scanning path retained when `DoctrineService` unavailable |

**No violations. No complexity tracking required.**

## Project Structure

### Documentation (this feature)

```
kitty-specs/048-structured-agent-identity-and-constitution-profile-integration/
├── spec.md              # Feature specification (complete)
├── plan.md              # This file
├── research.md          # Phase 0 output — design decisions and rationale
├── data-model.md        # Phase 1 output — entity definitions and relationships
├── quickstart.md        # Phase 1 output — implementation quick reference
├── contracts.md         # Phase 1 output — internal API contracts (Python protocols)
└── tasks.md             # Phase 2 output (/spec-kitty.tasks — NOT created by /spec-kitty.plan)
```

### Source Code (repository root)

```
src/specify_cli/
├── identity.py                          # NEW — ActorIdentity dataclass, parse_agent_identity()
├── status/
│   ├── models.py                        # MODIFIED — StatusEvent.actor becomes ActorIdentity
│   └── transitions.py                   # MODIFIED — _guard_actor_required() accepts ActorIdentity
├── constitution/
│   ├── catalog.py                       # MODIFIED — DoctrineCatalog expanded with 5 new fields
│   ├── compiler.py                      # MODIFIED — DoctrineService injection, transitive resolution
│   ├── interview.py                     # MODIFIED — agent_profile/agent_role optional fields
│   ├── reference_resolver.py            # NEW — transitive ref resolution, ResolvedReferenceGraph
│   └── resolver.py                      # MODIFIED — GovernanceResolution extended, generate-for-agent
├── frontmatter.py                       # MODIFIED — structured agent read/write
├── tasks_support.py                     # MODIFIED — WorkPackage.agent returns ActorIdentity
└── cli/commands/agent/
    ├── tasks.py                         # MODIFIED — --tool/--model/--profile/--role flags
    └── workflow.py                      # MODIFIED — --tool/--model/--profile/--role flags

src/doctrine/
└── service.py                           # CONSUMED — DoctrineService lazy properties (no changes)

tests/
├── specify_cli/
│   ├── test_identity.py                 # NEW — ActorIdentity unit tests
│   ├── status/
│   │   └── test_models.py              # MODIFIED — structured actor serialisation tests
│   └── constitution/
│       ├── test_catalog.py             # MODIFIED — expanded catalog tests
│       ├── test_reference_resolver.py  # NEW — transitive resolution tests
│       ├── test_compiler.py            # MODIFIED — DoctrineService injection tests
│       └── test_resolver.py            # MODIFIED — GovernanceResolution extension tests
└── integration/
    ├── test_structured_identity_e2e.py  # NEW — Track A end-to-end
    └── test_profile_constitution_e2e.py # NEW — Track B end-to-end
```

## Planning Decisions (from interviews)

| # | Decision | Rationale |
|---|----------|-----------|
| 1 | `StatusEvent.actor` is always `ActorIdentity` internally; coerce bare strings at boundary | Avoids union-type complexity; single code path for identity handling |
| 2 | `--agent` compound flag and `--tool/--model/--profile/--role` individual flags are mutually exclusive | Clear error message; avoids precedence ambiguity |
| 3 | Partial compound strings infer missing parts from context, fall back to `"unknown"` | Ergonomic for agents that don't know all four parts |
| 4 | New subcommand `spec-kitty constitution generate-for-agent` (not a flag on `generate`) | Different semantics — profile-aware compilation with transitive resolution |
| 5 | Frontmatter writes always use structured YAML mapping when value is `ActorIdentity` | Forward-looking; maintains backward-read compatibility |
| 6 | `DoctrineService` exists but is NOT yet injected into compiler; WP06 adds the wiring | Confirmed by codebase research — `compile_constitution()` takes `doctrine_catalog` not `doctrine_service` |

## Dependency Graph

```
Wave 1 (parallel):   WP01 (ActorIdentity)         WP04 (Catalog expansion)
                        │                              │
Wave 2 (parallel):   WP02 (Frontmatter)            WP05 (Transitive resolver)
                        │                              │
Wave 3 (parallel):   WP03 (CLI flags)              WP06 (Compiler + DoctrineService)
                        │                              │
Wave 4:                 │                           WP07 (Profile governance)
                        │                              │
Wave 5:              WP08 (E2E tests) ←────────────────┘
```

## Key Reuse Points

| Existing Code | Location | Reuse For |
|---|---|---|
| `extract_refs()` | `src/doctrine/curation/engine.py:150-181` | Pattern for transitive ref resolution (WP05) |
| `depth_first_order()` | `src/doctrine/curation/engine.py:184-225` | DFS with cycle detection pattern (WP05) |
| `DoctrineService` lazy properties | `src/doctrine/service.py:39-100` | Direct repository access in compiler (WP06) |
| `AgentProfile.directive_references` | `src/doctrine/agent_profiles/profile.py` | Profile directive extraction (WP07) |
| `AgentProfileRepository.resolve_profile()` | `src/doctrine/agent_profiles/repository.py` | Profile inheritance resolution (WP07) |
| `_load_yaml_id_catalog()` | `src/specify_cli/constitution/catalog.py:65-88` | Catalog expansion for new artifact types (WP04) |
| `_sanitize_catalog_selection()` | `src/specify_cli/constitution/compiler.py` | Validating expanded selections (WP06) |
| `StatusEvent.to_dict()/from_dict()` | `src/specify_cli/status/models.py:154-189` | Backwards-compatible serialisation pattern (WP01) |

## Verification Strategy

1. **Unit tests**: Each WP has dedicated test file covering happy path, edge cases, and error conditions
2. **Regression**: `pytest tests/specify_cli/constitution/ tests/specify_cli/status/ -v` must pass after each WP
3. **Type checking**: `ruff check src/ && mypy src/` must be clean
4. **Integration**: WP08 validates both tracks end-to-end
5. **Manual smoke test**: `spec-kitty agent tasks move-task WP01 --to doing --agent claude:opus-4:implementer:implementer` → verify structured actor in JSONL
