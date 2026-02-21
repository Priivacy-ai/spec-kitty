# Implementation Plan: Explicit Governance Layer Refactor

**Branch**: `053-doctrine-governance-layer-refactor` | **Date**: 2026-02-17 | **Spec**: `kitty-specs/053-doctrine-governance-layer-refactor/spec.md`
**Input**: Feature specification from `kitty-specs/053-doctrine-governance-layer-refactor/spec.md`

## Summary

Refactor Spec Kitty’s governance model so missions stay orchestration-only while constitution becomes the explicit project-level selector for active doctrine assets. Deliver aligned glossary updates, architecture artifacts, doctrine structure proposal scaffolding, and schema-validation-ready planning artifacts.

## Technical Context

**Language/Version**: Python 3.11+ (repository standard)  
**Primary Dependencies**: Typer, Rich, ruamel.yaml, pytest, mypy, ruff  
**Storage**: Markdown/YAML artifacts in repository files  
**Testing**: pytest + schema validation tests (new `tests/doctrine/*`)  
**Target Platform**: Linux/macOS/Windows CLI environments  
**Project Type**: Monorepo CLI toolkit with doctrine/governance assets  
**Performance Goals**: Validation checks complete within normal CI runtime budget (<2 minutes for doctrine tests)  
**Constraints**: Preserve existing mission command behavior while introducing explicit governance model; no destructive migration in this feature  
**Scale/Scope**: Governance vocabulary + architecture docs + feature artifacts + initial test scaffolding

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- Test-first discipline required: plan includes validation-first checkpoints.
- Type/lint/test quality gates: all new Python changes (if any) must pass mypy/ruff/pytest.
- Locality of change: scope limited to doctrine/governance artifacts and supporting tests/docs.
- No violations currently required for this feature plan.

## Project Structure

### Documentation (this feature)

```text
kitty-specs/053-doctrine-governance-layer-refactor/
├── spec.md
├── plan.md
├── research.md
├── contracts/
│   └── governance-layer-contracts.md
└── tasks/
```

### Source Code (repository root)

```text
src/doctrine/
├── missions/
├── templates/
└── (planned additions in follow-up implementation)

architecture/
├── adrs/
├── journeys/
└── diagrams/

glossary/
└── contexts/

.kittify/memory/contexts/
└── *.glossary.yml (compiled)

tests/
└── doctrine/ (planned in implementation)
```

**Structure Decision**: Use existing monorepo layout and extend doctrine/governance assets in place. No package split or large filesystem migration in this phase.

## Phase Plan

### Phase 0: Validation and Baseline Alignment

1. Validate spec/research/contracts consistency for feature `053`.
2. Confirm glossary terminology baseline (`Mission`, `Constitution`, `Paradigm`, `Directive`, `Tactic`, `TemplateSet`, `ImportCandidate`, `Schema`).
3. Confirm architecture artifacts (ADR + Journey + Diagram) are linked from spec.

**Outputs**:
- Stabilized feature artifacts (`spec.md`, `research.md`, `contracts/*`)
- Confirmed baseline for implementation tasks

### Phase 1: Governance Model Implementation (Docs + Structure + Contracts)

1. Finalize glossary canonical definitions and related-term graph.
2. Introduce/align doctrine structure contract (missions/paradigms/directives/tactics/templates/agent-profiles/schemas/curation model).
3. Ensure constitution-centric selection semantics are explicit in artifacts and docs.
4. Keep mission orchestration contract cleanly separated from governance behavior details.

**Outputs**:
- Updated glossary source in `glossary/contexts/*.md`
- Compiled Contextive outputs in `.kittify/memory/contexts/*.glossary.yml`
- Architecture model docs in `architecture/adrs/`, `architecture/journeys/`, `architecture/diagrams/`

### Phase 2: Validation Infrastructure (Implementation-Ready)

1. Add schema artifacts for governance entities (mission/directive/tactic/import-candidate/agent-profile).
2. Add `tests/doctrine/` validation suite for schema compliance.
3. Add invalid fixtures to verify CI failures for broken artifacts.

**Outputs**:
- `src/doctrine/schemas/*.schema.yaml` for minimal MVP set
- `tests/doctrine/*.py` with positive/negative validation coverage
- Deferred: template-set and constitution-selection schemas (future refinement feature)

### Phase 3: Operationalization

1. Ensure feature metadata and target branch (`develop`) are explicit.
2. Verify dashboard artifact visibility for research/contracts.
3. Prepare tasks decomposition for implementation work packages.

**Outputs**:
- Feature metadata correctness (`meta.json`)
- Ready-to-generate tasks plan

## Risks and Mitigations

- **Risk**: Terminology drift between glossary, ADR, and journey.
  - **Mitigation**: Treat glossary as canonical and cross-check references before task generation.
- **Risk**: Mission and constitution responsibilities blur during implementation.
  - **Mitigation**: Enforce mission-orchestration-only contract in tests and review checklist.
- **Risk**: Schema validation too strict early on.
  - **Mitigation**: Start with minimal required fields; tighten iteratively.
- **Risk**: Constitution references unavailable tools/profiles.
  - **Mitigation**: Hard-fail activation with actionable errors.

## Implementation Readiness Checklist

- [x] Spec is populated and linked to architecture artifacts.
- [x] Research artifact exists and summarizes rationale.
- [x] Contracts artifact exists with governance boundary contracts.
- [x] Plan is concrete and implementation-oriented.
- [ ] Tasks decomposition generated (`tasks.md` + WP files).

## Next Command

Proceed with task decomposition:

```bash
spec-kitty agent feature finalize-tasks --feature 053-doctrine-governance-layer-refactor --json
```

(If tasks.md is not yet generated, run `/spec-kitty.tasks` workflow in your primary assistant UI first.)
