# Specification Quality Checklist: Runtime / Mission-Execution Extraction

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-04-17
**Mission**: [spec.md](../spec.md)

## Content Quality

- [x] No implementation details (languages, frameworks, APIs) beyond the artefacts that are the subject of the refactor
      *Caveat: the mission is an internal Python package extraction, so `src/runtime/`, `src/specify_cli/next/`, `src/specify_cli/cli/commands/agent/`, `rich.*`, `typer.*`, and `DeprecationWarning` appear as the nouns the mission acts upon — not as implementation leakage. The `PresentationSink` protocol is named because it is an explicit seam deliverable.*
- [x] Focused on user value and business needs
      *Users: mission authors, runtime consumers, external importers of `specify_cli.next.*`, CI, Phase 4/6 executor authors. Value: clean separation enables profile/action executors and step-contract executors to land without further runtime surgery.*
- [x] Written for non-technical stakeholders
      *Acceptance scenarios phrased in outcome terms (CLI output unchanged, tests pass, architectural rule holds).*
- [x] All mandatory sections completed

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain
- [x] Requirements are testable and unambiguous
- [x] Requirement types are separated (Functional / Non-Functional / Constraints)
- [x] IDs are unique across FR-001..FR-016, NFR-001..NFR-005, C-001..C-009
- [x] All requirement rows include a non-empty Status value
- [x] Non-functional requirements include measurable thresholds (<=30 s regression suite, ±10% CLI latency, <=5 s dependency-rules pytest, zero regression)
- [x] Success criteria are measurable
- [x] Success criteria are technology-agnostic where possible (exceptions named where the artefact is the subject: JSON snapshot, `DeprecationWarning`, `pytest`, `rich.*`, `typer.*`)
- [x] All acceptance scenarios are defined
- [x] Edge cases are identified
- [x] Scope is clearly bounded (Out of Scope enumerates deferred work, pointing to Phase 4/5/6 follow-ups)
- [x] Dependencies and assumptions identified (upstream #610 + #615 rulebook; downstream #461 Phase 4 and 6 executors)

## Mission Readiness

- [x] All functional requirements have clear acceptance criteria
- [x] User scenarios cover primary flows (extraction lands without CLI UX change, dependency rule holds, regression fixtures match, scaffolding seams expose typed interfaces)
- [x] Mission meets measurable outcomes defined in Success Criteria
- [x] No implementation details leak beyond the artefacts under reshape

## Bulk-Edit Classification Readiness (DIRECTIVE_035)

- [x] `meta.json` has `change_mode: bulk_edit`
- [x] Spec explicitly names the rename target (imports from `specify_cli.next.*` -> canonical runtime package path; see FR-015 and C-007)
- [x] FR-015 requires `occurrence_map.yaml` covering every internal caller migration, authored in plan phase
- [ ] `occurrence_map.yaml` authored — **deferred to `/spec-kitty.plan` phase** (correct; it is a plan-phase artefact per the bulk-edit skill, and FR-015 captures the obligation)

## Extraction-Specific Readiness

- [x] Canonical package path decision policy stated (FR-001: defers to the #610 ownership map, working candidate `src/runtime/`, plan phase pins final path)
- [x] Dependency-rules enforcement strategy stated (FR-008: prefer #395 tooling, pytest fallback; mission not blocked on #395)
- [x] Regression-fixture approach defined (FR-011, FR-012: JSON snapshot capture before extraction, dict-equal assertion after)
- [x] Presentation/CLI separation invariant stated (FR-013, C-009: runtime cannot import `rich.*` or `specify_cli.cli.*`)
- [x] Scaffolding seams for Phase 4/6 named and contracted (FR-009, FR-010)
- [x] Shim contract aligns with #615 rulebook (FR-005, FR-006)
- [x] No version bump (C-006)

## Notes

- The mission is explicitly structural: C-001 forbids semantic changes to state-machine decisioning.
- The "what is next step" authoring stays in mission artefacts; runtime owns the transition *logic* only. This boundary is captured in FR-002 vs FR-003.
- Plan phase will pin: final canonical package path, the concrete scaffolding-seam interfaces (protocol signatures), and the `PresentationSink` protocol shape.
