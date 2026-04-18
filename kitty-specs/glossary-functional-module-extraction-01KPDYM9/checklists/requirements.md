# Specification Quality Checklist: Glossary Functional-Module Extraction

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-04-17
**Mission**: [spec.md](../spec.md)

## Content Quality

- [x] No implementation details (languages, frameworks, APIs) beyond the artefacts under reshape
      *Caveat: this is an internal Python package extraction, so `src/glossary/`, `src/specify_cli/glossary/`, `rich.*`, `typer.*`, `DeprecationWarning`, and `stacklevel=2` are named as the subject of the work. The repo-root `glossary/` term-content directory is also named (C-009) to avoid collision confusion.*
- [x] Focused on user value and business needs
      *Users: glossary consumers, CLI users, external importers of `specify_cli.glossary.*`, #461 Phase 5 DRG middleware authors. Value: clean extraction enables the runtime-terminology middleware without further surgery.*
- [x] Written for non-technical stakeholders
      *Acceptance scenarios describe outcomes (CLI output unchanged, architectural rule holds, entanglement audit landed before code move).*
- [x] All mandatory sections completed

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain
- [x] Requirements are testable and unambiguous
- [x] Requirement types are separated (Functional / Non-Functional / Constraints)
- [x] IDs are unique across FR-001..FR-014, NFR-001..NFR-005, C-001..C-009
- [x] All requirement rows include a non-empty Status value
- [x] Non-functional requirements include measurable thresholds (±10% CLI latency, <=15 s regression suite, <=3 s architectural pytest, zero regression)
- [x] Success criteria are measurable
- [x] Success criteria are technology-agnostic where possible (exceptions: `rich.*`, `typer.*`, `DeprecationWarning`, JSON emission — named only where they are the subject of the requirement)
- [x] All acceptance scenarios are defined
- [x] Edge cases are identified
- [x] Scope is clearly bounded (Out of Scope enumerates deferred work)
- [x] Dependencies and assumptions identified (upstream #610 + #615 rulebook; downstream #461 Phase 5 runtime middleware)

## Mission Readiness

- [x] All functional requirements have clear acceptance criteria
- [x] User scenarios cover primary flows (entanglement audit first, code move, adapter conversion, shim + registry entry, regression fixtures hold, architectural rule enforced)
- [x] Mission meets measurable outcomes defined in Success Criteria
- [x] No implementation details leak beyond artefacts under reshape

## Bulk-Edit Classification Readiness (DIRECTIVE_035)

- [x] `meta.json` has `change_mode: bulk_edit`
- [x] Spec explicitly names the rename target (imports `specify_cli.glossary.*` -> `glossary.*`; see FR-009 and C-005)
- [x] FR-009 requires `occurrence_map.yaml` covering every import migration, authored in plan phase
- [ ] `occurrence_map.yaml` authored — **deferred to `/spec-kitty.plan` phase** (correct; plan-phase artefact per the bulk-edit skill, FR-009 captures the obligation)

## Extraction-Specific Readiness

- [x] Canonical package path pinned at spec time (`src/glossary/`, FR-001)
- [x] Canonical/term-content directory collision addressed (C-009: repo-root `glossary/` is untouched; Python package goes to `src/glossary/`)
- [x] Entanglement-audit work package required **before** the code move (FR-008)
- [x] Regression-fixture approach defined (FR-010, FR-011)
- [x] Presentation separation invariant stated (FR-003, FR-004, C-007)
- [x] Shim contract aligns with #615 rulebook (FR-006, FR-007)
- [x] Graph-backed addressing seam **skipped** by explicit user decision (C-002) — this is a deliberate scope cut, not an omission
- [x] DRG-resident runtime middleware deferred to #461 Phase 5 (C-003)
- [x] No version bump (C-008)

## Notes

- FR-008 is deliberately the first work package in execution order: the entanglement inventory must commit before any code moves, so the audit can surface surprises the extraction plan has to absorb.
- C-002 (no graph seam) is explicitly pinned from discovery; plan phase must not scaffold a protocol that anticipates DRG addressing.
- Plan phase will pin: final CLI command module layout, the entanglement-audit table template, and whether the architectural test lives in `tests/architecture/` or a glossary-scoped equivalent.
