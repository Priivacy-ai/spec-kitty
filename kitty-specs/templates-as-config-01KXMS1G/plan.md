# Implementation Plan: Templates as Mission Configuration

**Branch**: `feat/templates-as-config` | **Date**: 2026-07-16 | **Spec**: [spec.md](spec.md)
**Input**: Mission specification for issue #2658 in `kitty-specs/templates-as-config-01KXMS1G/spec.md`

## Summary

Project the doctrine-owned `MissionType.template_set` artifact-key-to-filename mapping through the activated `ResolvedMissionType` context, then migrate specification and planning template readers to a two-stage resolution contract. The resolved mission type selects the filename; the existing five-tier resolver selects the permitted file copy. Null mappings and missing artifact keys fail closed without borrowing software-development templates. A temporary parity scaffold proves the shipped software-development `spec` and `plan` results are unchanged and is deleted before merge; enduring doctrine and integration tests remain.

## Technical Context

**Language/Version**: Python 3.11+  
**Primary Dependencies**: Pydantic v2, Typer, ruamel.yaml, Spec Kitty doctrine/charter/core modules  
**Storage**: Repository YAML doctrine artifacts and filesystem template files; no database or schema migration  
**Testing**: pytest acceptance-first, targeted unit and integration tests, architectural guards, Ruff, mypy strict  
**Target Platform**: Cross-platform CLI on Linux, macOS, and Windows 10+  
**Project Type**: Single Python CLI/package repository  
**Performance Goals**: Preserve the existing resolved-mission-type hot-path budget of 100 ms for a typical local project; ordinary CLI operations remain below 2 seconds  
**Constraints**: Doctrine remains the single mapping authority; availability remains charter-activation-driven; retain five-tier per-file override precedence; remove the transitional parity scaffold before merge; do not add version commitments  
**Scale/Scope**: Four built-in mission-type artifacts, two current software-development content-template keys, two production reader paths, and focused doctrine/unit/integration test surfaces

## Charter Check

### Pre-research gate

- **Single canonical authority — PASS**: `MissionType.template_set` is the only authored mapping. No profile default or parallel registry will be introduced.
- **Architectural alignment — PASS**: data flows doctrine → charter activation/resolution → core reader. Filename selection and file-precedence resolution stay separate.
- **ATDD-first — PASS**: implementation begins with failing behavior tests through mission creation and plan setup, plus doctrine-boundary assertions.
- **Terminology — PASS**: the plan consistently uses Mission, mission type, template mapping, and activated.
- **Performance — PASS WITH MEASUREMENT**: the mapping projection uses the existing lazy/cached resolved context pattern and is measured against the 100 ms budget.
- **Scope discipline — PASS**: issues #2659–#2661 retain enumeration, runtime discovery, meta-less fallback removal, copy-step retirement, and derived-tree deletion.
- **Tracer files — PASS**: `traces/tooling-friction.md`, `traces/approach.md`, and `traces/design-decisions.md` are seeded during planning.
- **Campsite and architectural gates — PASS**: every code-changing WP begins with a distinct, behavior-preserving campsite subtask before acceptance or functional edits; existing non-vacuous gates are extended without broad cleanup.
- **Coverage gate — PASS**: each WP measures changed/new production code and requires at least 90% coverage; WP05 rechecks the aggregate changed-code result.
- **Mission hygiene — PASS**: issue #2658 has a coordination-owned issue-matrix row, is assigned to the operator, and receives a tracker comment naming this mission before implementation.
- **Tracer persistence — PASS**: WP05 produces copy-ready evidence, and mission acceptance is blocked until the primary-checkout coordinator appends it to all three tracer files and records acknowledgment.

### Post-design re-check

- Phase 1 introduces no new persistence, public network API, package boundary, or duplicate authority.
- The internal contract explicitly distinguishes mapping lookup from file lookup and names failure behavior for null, missing-key, and unresolved-file cases.
- Enduring verification covers the doctrine boundary and production reader integration; the temporary parity scaffold cannot survive the architectural gate.
- No charter violation requires a complexity exception.

## Project Structure

### Documentation (this mission)

```text
kitty-specs/templates-as-config-01KXMS1G/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── issue-matrix.md        # Coordination-owned issue ledger
├── contracts/
│   └── template-resolution-contract.md
├── traces/
│   ├── tooling-friction.md
│   ├── approach.md
│   └── design-decisions.md
└── tasks/                 # Populated only by /spec-kitty.tasks
```

### Source Code (repository root)

```text
src/
├── doctrine/
│   └── missions/
│       ├── models.py
│       ├── mission_type_repository.py
│       └── mission_types/*.yaml
├── charter/
│   └── mission_type_profiles.py
└── specify_cli/
    ├── core/
    │   └── mission_creation.py
    ├── runtime/
    │   └── resolver.py
    └── cli/commands/agent/
        └── mission_setup_plan.py

tests/
├── charter/
│   └── test_resolved_mission_type_context.py
├── doctrine/
├── specify_cli/
│   ├── core/
│   │   ├── test_feature_creation.py
│   │   └── test_mission_creation_specify_started.py
│   └── cli/commands/agent/
│       ├── test_mission_create*.py       # Read-only adjacent regression
│       └── test_mission_setup_plan_phases.py
├── integration/
│   └── test_specify_plan_commit_boundary.py
├── e2e/
│   └── test_cli_smoke.py
└── architectural/
    └── test_no_parity_scaffold.py
```

**Structure Decision**: Keep the existing single-package architecture. Extend the doctrine-to-charter projection in `src/charter`, put any shared artifact-key selection adapter beside the existing template-resolution seam rather than creating a registry, and migrate the two production readers in place. Tests follow their current module and integration boundaries.

## Complexity Tracking

No charter violations or complexity exceptions are required.

## Implementation Concern Map

### IC-01 — Canonical mapping projection

- **Purpose**: Expose each activated doctrine mission type's complete `template_set` mapping through the resolved context without eager I/O regression or profile-default substitution.
- **Relevant requirements**: FR-001, FR-002, NFR-001, NFR-002, C-001, C-002, C-003
- **Affected surfaces**: `src/doctrine/missions/models.py`, `src/doctrine/missions/mission_type_repository.py`, `src/charter/mission_type_profiles.py`, `tests/charter/test_resolved_mission_type_context.py`, doctrine tests
- **Sequencing/depends-on**: none
- **Risks**: Mutable mapping leakage, loss of deterministic ordering, or eager repository access could violate context semantics and the 100 ms budget.

### IC-02 — Artifact-key selection contract

- **Purpose**: Provide one typed seam that selects a mapped filename by mission type and artifact kind, with actionable failures for neutral, null, missing-key, and unresolved-file states.
- **Relevant requirements**: FR-003, FR-004, FR-005, FR-006, NFR-002, C-001, C-002
- **Affected surfaces**: `src/specify_cli/runtime/resolver.py` and/or a narrowly scoped adjacent adapter, focused unit tests
- **Sequencing/depends-on**: IC-01
- **Risks**: Combining filename selection with path precedence would obscure authority; accidentally using `software-dev` as a default would recreate the defect. The configured-template seam rejects a neutral/typeless context with `TemplateConfigurationError`; existing readers route typeless missions through the unchanged legacy compatibility boundary outside that seam until #2660.

### IC-03 — Specification scaffold reader migration

- **Purpose**: Make mission creation select `spec-template.md` from the activated mission type before applying established override precedence.
- **Relevant requirements**: FR-003, FR-004, FR-005, FR-006, FR-007, NFR-003, NFR-004
- **Affected surfaces**: `src/specify_cli/core/mission_creation.py`, canonical core tests `tests/specify_cli/core/test_feature_creation.py` and `tests/specify_cli/core/test_mission_creation_specify_started.py`; existing CLI `test_mission_create*.py` suites remain read-only adjacent regression coverage; integration/e2e mission-create coverage
- **Sequencing/depends-on**: IC-01, IC-02
- **Risks**: Mission creation currently touches an empty spec when project templates are absent; migration must preserve transaction and commit behavior while changing only template authority.

### IC-04 — Plan scaffold and pristine-check reader migration

- **Purpose**: Make plan setup and pristine detection use the activated mission type's `plan` mapping while comparing against the same effective selected file.
- **Relevant requirements**: FR-003, FR-004, FR-005, FR-006, FR-007, NFR-003, NFR-004
- **Affected surfaces**: `src/specify_cli/cli/commands/agent/mission_setup_plan.py`, `tests/specify_cli/cli/commands/agent/test_mission_setup_plan_phases.py`, `tests/integration/test_specify_plan_commit_boundary.py`
- **Sequencing/depends-on**: IC-01, IC-02
- **Risks**: Scaffolding and pristine comparison can drift if they do not share the exact selection path; branch/commit boundary behavior must remain unchanged.

### IC-05 — Compatibility proof and enduring behavior checks

- **Purpose**: Demonstrate exact software-development parity during migration, then remove the temporary scaffold while retaining doctrine and integration behavior tests.
- **Relevant requirements**: FR-007, FR-008, FR-009, NFR-003, NFR-004, C-004
- **Affected surfaces**: temporary parity test/scaffold, `tests/charter/`, affected CLI/integration tests, `tests/architectural/test_no_parity_scaffold.py`
- **Sequencing/depends-on**: IC-01, IC-03, IC-04
- **Risks**: A permanent dual-path comparison would preserve obsolete authority; an overly mocked test could miss real file precedence.

### IC-06 — Quality, performance, and scope gates

- **Purpose**: Verify type safety, style, at least 90% changed/new-code coverage, targeted behavior, performance, terminology, and absence of magic defaults or parity artifacts.
- **Relevant requirements**: SC-001, SC-002, SC-003, SC-004, SC-005, NFR-001, C-004, C-005, C-006
- **Affected surfaces**: targeted pytest packages with changed/new-code coverage measurement, Ruff, mypy strict, architectural and terminology checks, changed-file inventory
- **Sequencing/depends-on**: IC-01 through IC-05
- **Risks**: Broad suite execution wastes resources, while tests limited to isolated helpers could miss the production reader paths.
