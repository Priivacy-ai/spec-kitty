# Research: Doctrine Artifact Domain Models

**Date**: 2026-02-25
**Feature**: 046-doctrine-artifact-domain-models

## R-001: Existing Schema Field Coverage

**Decision**: Map each JSON schema to a Pydantic model that covers all required and optional fields.

**Findings**:

| Artifact | Schema Draft | Required Fields | Optional Fields |
|----------|-------------|-----------------|-----------------|
| Directive | 2020-12 | schema_version, id, title, intent, enforcement | tactic_refs + new enrichment fields |
| Tactic | 2020-12 | schema_version, id, name, steps | purpose, references |
| Styleguide | 2020-12 | schema_version, id, title, scope, principles | anti_patterns, quality_test, references |
| Toolguide | 2020-12 | schema_version, id, tool, title, guide_path, summary | commands |
| Paradigm | (none) | schema_version, id, name, summary | (none) |
| Agent Profile | draft-07 | profile-id, name, purpose, specialization | all other 6-section fields |

**Rationale**: Pydantic models mirror schema required/optional distinction via `Field(default=...)` for optional and no-default for required.

**Alternatives considered**: dataclasses (rejected — no built-in validation, no alias support), attrs (rejected — less ecosystem integration with YAML serialization).

## R-002: Directive Enrichment Field Design

**Decision**: Add 4 optional multiline string/list fields to the directive schema: `scope`, `procedures`, `integrity_rules`, `validation_criteria`.

**Findings from doctrine_ref analysis**:

The `doctrine_ref` directives consistently use these sections:
- **Scope** (present in 30/34 directives): Defines when the directive applies and exceptions
- **Workflow/Procedures** (present in 28/34): Ordered steps to follow
- **Integrity Rules** (present in 20/34): Hard constraints that must not be violated
- **Validation Criteria** (present in 25/34): How to verify compliance

Additional sections found but deferred:
- **Integration notes** (how directive interacts with other directives) — deferred to cross-artifact resolution
- **Non-compliance** (consequences) — captured in `enforcement` field semantics
- **Benefits** (why follow this) — captured in `intent` field

**Rationale**: 4 fields cover the most common sections without over-engineering. `procedures` and `integrity_rules` as `list[str]` for ordered items. `scope` and `validation_criteria` as multiline strings for prose.

## R-003: doctrine_ref Directive Mapping

**Decision**: Create new shipped directives for unrepresented `doctrine_ref` concepts.

**Mapping analysis**:

| doctrine_ref Directive | Existing Shipped | Action |
|------------------------|-----------------|--------|
| 014 Worklog Creation | None | Create new (020) |
| 015 Store Prompts | None | Create new (021) |
| 016 ATDD | 004 (partial) | Enrich 004 |
| 017 TDD | 004 (partial) | Enrich 004 |
| 018 Traceable Decisions | 003 (partial) | Enrich 003 |
| 026 Commit Protocol | None | Create new (022) |
| 034 Spec-Driven Development | 010 (partial) | Enrich 010 |
| 023 Clarification Before Execution | None | Create new (023) |
| 021 Locality of Change | None | Create new (024) |
| 036 Boy Scout Rule | None | Create new (025) |
| 040 HiC Escalation Protocol | None | Create new (026) |

**Rationale**: Only concepts with clear governance value and no overlap with existing directives become new shipped directives. Overlapping concepts (ATDD, TDD, traceable decisions, spec-driven dev) enrich existing directives instead.

## R-004: File Relocation Strategy

**Decision**: Move YAML files into `shipped/` subdirectories as part of subpackage creation.

**Risk analysis**:
- `importlib.resources.files()` resolves from the installed package, so `shipped/` paths work in both development and installed mode
- Existing tests that reference file paths will need updating
- The `test_schema_validation.py` and `test_artifact_compliance.py` tests scan directories — they need path updates

**Rationale**: Consistent with `agent_profiles/shipped/` pattern. Separation of code and data within each subpackage.

## R-005: Schema Validator Selection

**Decision**: Use `Draft202012Validator` for all new schemas (matching existing directive/tactic/styleguide/toolguide schemas). Only `agent-profile.schema.yaml` uses `Draft7Validator`.

**Rationale**: Consistency with existing schema conventions. The agent profile schema predates the others and uses draft-07; new code should use the same validator as the schema declares.
