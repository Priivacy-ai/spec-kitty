# Work Packages: Doctrine Governance Layer Refactor

**Inputs**: Design documents from `kitty-specs/053-doctrine-governance-layer-refactor/`
**Prerequisites**: `spec.md`, `plan.md`, `research.md`, `contracts/governance-layer-contracts.md`

**Tests**: Constitution requires test-first; each WP includes concrete validation work.

**Organization**: Fine-grained subtasks (`Txxx`) roll up into work packages (`WPxx`). Each WP is independently testable.

**Prompt Files**: Each work package maps to a prompt file in `tasks/`.

---

## Work Package WP01: Governance Schema Baseline (Priority: P1) MVP

**Goal**: Introduce the minimal governance schema set and schema-validation tests for doctrine artifacts.
**Independent Test**: Run doctrine schema tests with valid and invalid fixtures; validate pass/fail behavior is explicit and stable.
**Prompt**: `tasks/WP01-governance-schema-baseline.md`

### Included Subtasks
- [x] T001 Create schema directory scaffold for governance/domain artifacts
- [x] T002 Add mission schema (`mission.schema.yaml`)
- [x] T003 Add directive schema (`directive.schema.yaml`)
- [x] T004 Add tactic schema (`tactic.schema.yaml`)
- [x] T005 Add import candidate schema (`import-candidate.schema.yaml`)
- [x] T006 Add agent profile schema (`agent-profile.schema.yaml`)
- [x] T007 Add valid/invalid fixture set per schema
- [x] T008 Implement test loader/validator utilities in `tests/doctrine/`
- [x] T009 Implement schema validation tests with actionable failure messages

### Implementation Notes
- MVP schema scope is intentionally limited to the agreed minimal set.
- Defer template-set and constitution-selection schemas to follow-up work.
- Keep schemas focused on required fields first; avoid speculative optional complexity.

### Dependencies
- None.

### Risks & Mitigations
- Over-strict schemas cause churn: start minimal and tighten incrementally.
- Weak test diagnostics slow adoption: include fixture path + field-level error in failures.

---

## Work Package WP02: Constitution-Centric Governance Resolution (Priority: P1) MVP

**Goal**: Enforce constitution as activation authority for governance, with hard-fail on missing tools/profiles and optional template-set fallback.
**Independent Test**: Resolve active governance from constitution fixtures and verify failure/success cases against contracts.
**Prompt**: `tasks/WP02-constitution-centric-resolution.md`

### Included Subtasks
- [x] T010 Implement governance resolution module reading constitution selections first
- [x] T011 Enforce hard-fail when constitution references unknown selected agent profiles
- [x] T012 Enforce hard-fail when constitution references unavailable tools
- [x] T013 Implement optional template-set resolution with explicit fallback path
- [x] T014 Add contract tests for activation behavior and error semantics
- [x] T015 Add CLI-usable validation helper to surface constitution resolution issues

### Implementation Notes
- Mission remains orchestration-only and must not activate doctrine directly.
- Constitution is project-level authority; no mission-level constitution behavior.
- Keep resolver output deterministic to simplify planning/runtime adoption.

### Dependencies
- Depends on WP01.

### Risks & Mitigations
- Boundary drift between mission and constitution: codify in tests and module API.
- Silent fallback confusion: log explicit fallback reason and selected defaults.

---

## Work Package WP03: Doctrine Structure and Curation Scaffold (Priority: P2)

**Goal**: Materialize the governance directory model (`schemas`, `agent-profiles`, `curation` with README) and curation record flow scaffolding.
**Independent Test**: Validate expected folder/files exist and sample import-candidate records pass schema checks.
**Prompt**: `tasks/WP03-doctrine-structure-and-curation.md`

### Included Subtasks
- [x] T016 Create doctrine directory scaffolding for paradigms/directives/tactics/templates/agent-profiles/schemas/curation
- [x] T017 Add `README.md` in curation directory documenting pull-based assimilation intent and flow
- [x] T018 Add canonical import-candidate sample documenting source, mapping, adaptation, status
- [x] T019 Add schema-aware checks for curation record completeness and traceability links
- [x] T020 Add tests ensuring curated candidate adoption links to resulting doctrine artifacts

### Implementation Notes
- Curation README must include the ZOMBIES-TDD example journey.
- Keep scaffolding backward-compatible with existing doctrine missions/templates.
- Prefer small, composable files over one large governance artifact.

### Dependencies
- Depends on WP01.

### Risks & Mitigations
- Folder model mismatch with docs: include tree assertions in tests.
- Curation ambiguity: require source + target mapping + adaptation notes in schema.

---

## Work Package WP04: Canonical Terminology and Compiled Glossary Sync (Priority: P2)

**Goal**: Finalize canonical glossary alignment for governance terminology and ensure Contextive compilation is reproducible.
**Independent Test**: Run `scripts/chores/glossary-compilation.py` and verify generated `.kittify/memory` outputs parse cleanly and reflect canonical terms.
**Prompt**: `tasks/WP04-glossary-and-contextive-sync.md`

### Included Subtasks
- [x] T021 Confirm glossary canonical terms reflect governance model and contracts
- [x] T022 Add/adjust glossary entries for Research and Contracts linkage semantics
- [x] T023 Align glossary terminology references in feature `053` artifacts
- [x] T024 Execute glossary compilation script in venv and verify generated output integrity
- [x] T025 Add regression checks for known Contextive YAML parsing pitfalls

### Implementation Notes
- Canonical glossary is source of truth; compiled Contextive files are generated artifacts.
- Keep definitions aligned with ADR and journey terminology.

### Dependencies
- Depends on WP02 and WP03.

### Risks & Mitigations
- Canonical/generated drift: rerun compiler and verify in CI/test.
- YAML format regressions: include parser-level validation tests.

---

## Dependency & Execution Summary

- **Sequence**: `WP01 -> (WP02 + WP03) -> WP04`
- **MVP**: `WP01 + WP02`
- **Full Scope**: `WP01 + WP02 + WP03 + WP04`

## Subtask Index (Reference)

| Subtask ID | Summary | Work Package | Priority |
|------------|---------|--------------|----------|
| T001 | Create schema scaffold | WP01 | P1 |
| T002 | Add mission schema | WP01 | P1 |
| T003 | Add directive schema | WP01 | P1 |
| T004 | Add tactic schema | WP01 | P1 |
| T005 | Add import-candidate schema | WP01 | P1 |
| T006 | Add agent-profile schema | WP01 | P1 |
| T007 | Add valid/invalid fixtures | WP01 | P1 |
| T008 | Add test loader/validator utilities | WP01 | P1 |
| T009 | Add schema validation tests | WP01 | P1 |
| T010 | Add constitution-first resolver | WP02 | P1 |
| T011 | Hard-fail unknown profiles | WP02 | P1 |
| T012 | Hard-fail unavailable tools | WP02 | P1 |
| T013 | Optional template-set fallback | WP02 | P1 |
| T014 | Add resolver contract tests | WP02 | P1 |
| T015 | Add validation helper for resolver | WP02 | P1 |
| T016 | Create doctrine structure scaffold | WP03 | P2 |
| T017 | Add curation README with intent + flow | WP03 | P2 |
| T018 | Add import-candidate sample | WP03 | P2 |
| T019 | Add curation completeness checks | WP03 | P2 |
| T020 | Add adoption traceability tests | WP03 | P2 |
| T021 | Align canonical governance terms | WP04 | P2 |
| T022 | Add Research/Contracts glossary semantics | WP04 | P2 |
| T023 | Align terminology across feature artifacts | WP04 | P2 |
| T024 | Run glossary compilation and verify outputs | WP04 | P2 |
| T025 | Add YAML parsing regression checks | WP04 | P2 |

<!-- status-model:start -->
## Canonical Status (Generated)
- WP01: done
- WP02: done
- WP03: done
- WP04: done
<!-- status-model:end -->
