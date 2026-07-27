# Specification Quality Checklist: Migration and Shim Ownership Rules

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-04-17
**Mission**: [spec.md](../spec.md)

## Content Quality

- [x] No implementation details (languages, frameworks, APIs)
      *Caveat: the rulebook governs Python shim modules so `__deprecated__`, `__canonical_import__`, `__removal_release__`, `DeprecationWarning`, and `stacklevel=2` appear — they are the subject of the rule, not implementation leakage. The new CLI subcommand `spec-kitty doctor shim-registry` is named because the subcommand is itself a deliverable.*
- [x] Focused on user value and business needs
      *Users: extraction authors, reviewers, release managers, CI, external Python importers. Value: deterministic shim lifecycles replacing human archaeology.*
- [x] Written for non-technical stakeholders
      *Acceptance scenarios describe outcomes (CI passes/fails, registry entries exist, reader finds the rule) rather than code.*
- [x] All mandatory sections completed

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain
- [x] Requirements are testable and unambiguous
- [x] Requirement types are separated (Functional / Non-Functional / Constraints)
- [x] IDs are unique across FR-001..FR-015, NFR-001..NFR-005, C-001..C-007
- [x] All requirement rows include a non-empty Status value
- [x] Non-functional requirements include measurable thresholds (<=2s doctor run, <=500 ms schema test, <=15 min read time)
- [x] Success criteria are measurable (6 criteria)
- [x] Success criteria are technology-agnostic where possible (exceptions: YAML, pytest, and `spec-kitty doctor` are named only where they are the subject of the requirement)
- [x] All acceptance scenarios are defined (8 scenarios + 4 edge cases)
- [x] Edge cases are identified (shim canonical rename, extension, umbrella shims, unregistered shims)
- [x] Scope is clearly bounded (Out of Scope enumerates 6 deferred items)
- [x] Dependencies and assumptions identified (A1-A5, upstream #610, downstream #612/#613/#614/doctrine port)

## Mission Readiness

- [x] All functional requirements have clear acceptance criteria
- [x] User scenarios cover primary flows (rulebook consumption, registry update, CI block, CI pass, grandfathering, schema alignment, charter citation, schema validation)
- [x] Mission meets measurable outcomes defined in Success Criteria
- [x] No implementation details leak beyond the artefacts the mission produces

## Bulk-Edit Classification Readiness (DIRECTIVE_035)

- [x] `meta.json` has `change_mode: standard` (not bulk_edit — new artefacts + CI check, no cross-file rename)
- [x] Spec documents the classification rationale (C-005)
- [N/A] `occurrence_map.yaml` — not required for `standard` mode

## Rulebook/Registry Readiness

- [x] Rulebook path pinned (`architecture/2.x/06_migration_and_shim_rules.md`)
- [x] Registry path pinned (`architecture/2.x/shim-registry.yaml`)
- [x] Enforcement subcommand named (`spec-kitty doctor shim-registry`)
- [x] Grandfathering mechanism defined (FR-008) with explicit `grandfathered: true` flag and rationale field
- [x] Forward-only policy on retrofits stated (C-003, A5)
- [x] Mission explicitly does not add/modify/remove any live shim (C-001)

## Notes

- All four rule families (schema/version gating, bundle/runtime migration, shim lifecycle, removal plans) are named in FR-002 and each gets a worked-example mapping in FR-012.
- The CI-check requirement (FR-009) is fully specified with inputs, validations, failure conditions, and output format.
- Plan phase will pin: YAML schema key shape for `canonical_import` (string-or-list), doctor subcommand integration point, and test directory for the unregistered-shim scanner.
