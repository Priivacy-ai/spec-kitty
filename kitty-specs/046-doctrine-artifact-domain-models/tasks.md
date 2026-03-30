# Work Packages: Doctrine Artifact Domain Models

**Inputs**: Design documents from `kitty-specs/046-doctrine-artifact-domain-models/`
**Prerequisites**: plan.md (required), spec.md (user stories), research.md, data-model.md, quickstart.md
**Organization**: Fine-grained subtasks (`Txxx`) roll up into work packages (`WPxx`). Each work package must be independently deliverable and testable. All WPs follow ATDD/TDD methodology.
**Invariant**: The test suite MUST be green after every WP merge. Each WP that moves files updates affected test paths.

---

## Work Package WP01: Directive Model, Repository & Schema Extension (Priority: P1)

**Goal**: Create the `Directive` Pydantic model (including enrichment fields), `DirectiveRepository`, schema validation, and extend `directive.schema.yaml` — all as one atomic unit. Move existing directive YAML files into `shipped/` subdirectory. Update existing tests that reference directive paths.
**Independent Test**: `DirectiveRepository().list_all()` returns all shipped directives as `Directive` objects; `get("004")` normalizes to `DIRECTIVE_004`; both minimal and enriched directive formats validate against the updated schema.
**Prompt**: `tasks/WP01-directive-model-and-repository.md`
**Estimated size**: ~550 lines

### Included Subtasks

- [x] T001 Update `src/doctrine/schemas/directive.schema.yaml`: remove `additionalProperties: false`, add optional fields (`scope`, `procedures`, `integrity_rules`, `validation_criteria`)
- [x] T002 Create `src/doctrine/directives/__init__.py` with public exports
- [x] T003 Create `src/doctrine/directives/models.py` with `Directive` (including enrichment fields), `Enforcement` enum
- [x] T004 Create `src/doctrine/directives/repository.py` with `DirectiveRepository`
- [x] T005 Create `src/doctrine/directives/validation.py` with schema validation utility
- [x] T006 Move directive YAML files into `src/doctrine/directives/shipped/`
- [x] T007 Update `tests/doctrine/test_directive_consistency.py`: change `DIRECTIVES_DIR` to point to `shipped/` subdirectory
- [x] T008 Update `tests/doctrine/test_artifact_compliance.py`: change directive entry in path mapping to `shipped/`
- [x] T009 Update `tests/doctrine/test_tactic_compliance.py`: change `"directive"` entry in `ARTIFACT_DIRS` dict to `shipped/`
- [x] T010 Write ATDD/TDD tests in `tests/doctrine/directives/` (model, repository, schema backward-compat + enriched format)

### Implementation Notes

- Follow `agent_profiles` pattern exactly for repository structure
- `DirectiveRepository.get()` must accept both `"004"` and `"DIRECTIVE_004"` and normalize
- Use `Draft202012Validator` (not Draft7) per research.md R-005
- The schema currently has `additionalProperties: false` — this MUST be removed in T001 before enrichment fields work
- All new enrichment fields are optional: `scope` (string), `procedures` (array of strings), `integrity_rules` (array of strings), `validation_criteria` (array of strings)
- Use YAML keys with underscores per existing schema convention (match `tactic_refs` pattern)
- Existing minimal directives must continue to validate unchanged after schema update
- Update `README.md` in `src/doctrine/directives/` to reflect subpackage status

### Dependencies

- None (starting package)

### Risks & Mitigations

- Schema change is backward-compatible (all new fields optional, `additionalProperties` removal is additive)

---

## Work Package WP02: Tactic Model & Repository (Priority: P1)

**Goal**: Create the `Tactic`, `TacticStep`, `TacticReference` Pydantic models and `TacticRepository`. Move tactic YAML files into `shipped/`. Update existing tests that reference tactic paths.
**Independent Test**: `TacticRepository().get("zombies-tdd")` returns a `Tactic` with 7 steps.
**Prompt**: `tasks/WP02-tactic-model-and-repository.md`
**Estimated size**: ~450 lines

### Included Subtasks

- [ ] T011 Create `src/doctrine/tactics/__init__.py` with public exports
- [ ] T012 Create `src/doctrine/tactics/models.py` with `Tactic`, `TacticStep`, `TacticReference`, `ReferenceType` enum
- [ ] T013 Create `src/doctrine/tactics/repository.py` with `TacticRepository`
- [ ] T014 Create `src/doctrine/tactics/validation.py` with schema validation utility
- [ ] T015 Move tactic YAML files into `src/doctrine/tactics/shipped/`
- [ ] T016 Update `tests/doctrine/test_tactic_compliance.py`: change `TACTICS_DIR` and `"tactic"` entry in `ARTIFACT_DIRS` to point to `shipped/`
- [ ] T017 Update `tests/doctrine/test_artifact_compliance.py`: change tactic path references to `shipped/`
- [ ] T018 Write ATDD/TDD tests in `tests/doctrine/tactics/`

### Implementation Notes

- `TacticStep` has optional `description`, `examples`, and `references` fields
- `TacticReference` has `name`, `type` (enum), `id`, `when` — all required per schema
- Schema uses `definitions` for reference objects (valid in Draft 2020-12); model `references` field at both tactic and step level
- `test_tactic_compliance.py` has a comprehensive `ARTIFACT_DIRS` dict — update the `"tactic"` entry path, and if WP01 hasn't already updated `"directive"`, update that too

### Dependencies

- None (parallel with WP01)

---

## Work Package WP03: Styleguide Model & Repository (Priority: P1)

**Goal**: Create `Styleguide`, `AntiPattern` models and `StyleguideRepository`. Move styleguide YAML files into `shipped/`. Update existing tests.
**Independent Test**: `StyleguideRepository().get("kitty-glossary-writing")` returns a `Styleguide` with `scope == "glossary"`.
**Prompt**: `tasks/WP03-styleguide-model-and-repository.md`
**Estimated size**: ~400 lines

### Included Subtasks

- [ ] T019 Create `src/doctrine/styleguides/__init__.py` with public exports
- [ ] T020 Create `src/doctrine/styleguides/models.py` with `Styleguide`, `AntiPattern`, `StyleguideScope` enum
- [ ] T021 Create `src/doctrine/styleguides/repository.py` with `StyleguideRepository`
- [ ] T022 Create `src/doctrine/styleguides/validation.py` with schema validation utility
- [ ] T023 Move styleguide YAML files into `src/doctrine/styleguides/shipped/` (including `writing/` subdirectory)
- [ ] T024 Update `tests/doctrine/test_artifact_compliance.py`: change styleguide path references to `shipped/`
- [x] T025 Update `tests/doctrine/test_tactic_compliance.py`: change `"styleguide"` entry in `ARTIFACT_DIRS` to `shipped/`
- [x] T026 Write ATDD/TDD tests in `tests/doctrine/styleguides/`

### Implementation Notes

- `writing/kitty-glossary-writing.styleguide.yaml` lives in a subdirectory — repository must scan recursively using `**/*.styleguide.yaml`
- `AntiPattern` has 4 required fields: `name`, `description`, `bad_example`, `good_example`
- `Scope` enum: `code | docs | architecture | testing | operations | glossary`

### Dependencies

- None (parallel with WP01, WP02)

---

## Work Package WP04: Toolguide & Paradigm Models (Priority: P1)

**Goal**: Create `Toolguide` and `Paradigm` models with repositories. Create `paradigm.schema.yaml` (does not currently exist). Move files into `shipped/`. Update existing tests.
**Independent Test**: `ToolguideRepository().get("powershell-syntax")` returns a `Toolguide`; `ParadigmRepository().get("test-first")` returns a `Paradigm`.
**Prompt**: `tasks/WP04-toolguide-and-paradigm-models.md`
**Estimated size**: ~500 lines

### Included Subtasks

- [x] T027 Create `src/doctrine/schemas/paradigm.schema.yaml` (new schema: `schema_version`, `id`, `name`, `summary` — all required)
- [x] T028 Create `src/doctrine/toolguides/__init__.py`, `models.py`, `repository.py`, `validation.py`
- [x] T029 Move toolguide YAML and companion MD files into `src/doctrine/toolguides/shipped/`
- [x] T030 Create `src/doctrine/paradigms/__init__.py`, `models.py`, `repository.py`, `validation.py`
- [x] T031 Move paradigm YAML files into `src/doctrine/paradigms/shipped/`
- [x] T032 Update `tests/doctrine/test_artifact_compliance.py`: change toolguide path references to `shipped/`
- [x] T033 Update `tests/doctrine/test_tactic_compliance.py`: change `"toolguide"` entry in `ARTIFACT_DIRS` to `shipped/`
- [x] T034 Create paradigm test fixtures in `tests/doctrine/fixtures/paradigm/{valid,invalid}/`
- [x] T035 Write ATDD/TDD tests in `tests/doctrine/toolguides/` and `tests/doctrine/paradigms/`

### Implementation Notes

- Toolguide `guide_path` pattern: `^src/doctrine/.+\.md$` — companion markdown files move into `shipped/` too
- Paradigm schema is new (DD-003): `schema_version`, `id`, `name`, `summary` — all required
- Both are simple models with no nested value objects
- No existing `paradigm.schema.yaml` or paradigm test fixtures exist — T027 and T034 create them from scratch
- After T027, update `test_schema_validation.py` if it has a `SCHEMA_FILES` dict to include paradigm

### Dependencies

- None (parallel with WP01-WP03)

---

## Work Package WP05: DoctrineService (Priority: P1)

**Goal**: Create `DoctrineService` as the lazy aggregation point that holds references to all repositories.
**Independent Test**: `DoctrineService().directives.list_all()` returns directives; `service.agent_profiles.get("implementer")` reuses existing `AgentProfileRepository`.
**Prompt**: `tasks/WP05-doctrine-service.md`
**Estimated size**: ~300 lines

### Included Subtasks

- [x] T036 Create `src/doctrine/service.py` with `DoctrineService` class
- [x] T037 Update `src/doctrine/__init__.py` to export `DoctrineService`
- [x] T038 Write ATDD/TDD tests in `tests/doctrine/test_service.py`

### Implementation Notes

- Lazy initialization: repositories instantiated on first attribute access (use `@property` with `_cache` dict or `functools.cached_property`)
- Constructor: `DoctrineService(shipped_root: Path | None = None, project_root: Path | None = None)`
- Must reuse existing `AgentProfileRepository` (FR-016)
- Each repository's `shipped_dir` derived from `shipped_root / <artifact_type> / shipped`
- Each repository's `project_dir` derived from `project_root / <artifact_type>`

### Dependencies

- Depends on WP01, WP02, WP03, WP04 (all repositories must exist)

---

## Work Package WP06: Enrich Existing Directives 001-010 (Priority: P2)

**Goal**: Enrich shipped directives 001-010 with substantive content (scope, procedures, integrity_rules, validation_criteria, populated tactic_refs).
**Independent Test**: Loading directive 004 returns a `Directive` with non-empty `scope`, `procedures`, and `tactic_refs` fields.
**Prompt**: `tasks/WP06-enrich-directives-001-010.md`
**Estimated size**: ~500 lines

### Included Subtasks

- [x] T039 Enrich 001-architectural-integrity-standard
- [x] T040 Enrich 002-accessibility-first-principle
- [x] T041 Enrich 003-decision-documentation-requirement (incorporate doctrine_ref/018 traceable decisions)
- [x] T042 Enrich 004-test-driven-implementation-standard (incorporate doctrine_ref/016 ATDD + 017 TDD)
- [x] T043 Enrich 005-design-system-consistency-standard
- [x] T044 Enrich 006-coding-standards-adherence
- [x] T045 Enrich 007-scalability-assessment-protocol
- [x] T046 Enrich 008-security-review-protocol
- [x] T047 Enrich 009-user-centered-validation-requirement
- [x] T048 Enrich 010-specification-fidelity-requirement (incorporate doctrine_ref/034 spec-driven dev)

### Implementation Notes

- Use `doctrine_ref/directives/` as reference material — adapt content, don't copy verbatim
- Each directive must have: expanded `intent` (>1 sentence), `scope`, at least `procedures` or `validation_criteria`
- Wire `tactic_refs` to existing tactics where applicable (e.g., 004 → acceptance-test-first, tdd-red-green-refactor, zombies-tdd)
- Maintain `enforcement` values unchanged
- All enriched files must validate against updated schema (already extended in WP01)
- Files are already in `shipped/` directory (moved in WP01)

### Dependencies

- Depends on WP01 (schema extended + YAML files in `shipped/`)

---

## Work Package WP07: Enrich Existing Directives 011-019 + test-first (Priority: P2)

**Goal**: Enrich shipped directives 011-019 and `test-first` with substantive content.
**Independent Test**: Loading any directive returns non-stub content; all directives validate against schema.
**Prompt**: `tasks/WP07-enrich-directives-011-019.md`
**Estimated size**: ~450 lines

### Included Subtasks

- [x] T049 Enrich 011-feedback-clarity-standard
- [x] T050 Enrich 012-work-package-granularity-standard
- [x] T051 Enrich 013-dependency-validation-requirement
- [x] T052 Enrich 014-acceptance-criteria-completeness
- [x] T053 Enrich 015-research-time-boxing-requirement
- [x] T054 Enrich 016-finding-documentation-standard
- [x] T055 Enrich 017-glossary-integrity-standard
- [x] T056 Enrich 018-doctrine-versioning-requirement
- [x] T057 Enrich 019-documentation-gap-prioritization
- [x] T058 Verify test-first.directive.yaml enrichment (already has tactic_refs; add scope/procedures)

### Implementation Notes

- Same enrichment approach as WP06
- Directive 017 already links to glossary-related tactics/styleguides; expand those references
- `test-first.directive.yaml` already has populated `tactic_refs` — add `scope` and `procedures` only

### Dependencies

- Depends on WP01 (schema extended + YAML files in `shipped/`)

### Parallel Opportunities

- WP06 and WP07 can run in parallel (different directive files, no overlap)

---

## Work Package WP08: Create New Shipped Directives (Priority: P2)

**Goal**: Create new shipped directives (020-026) for `doctrine_ref` concepts not yet represented.
**Independent Test**: `DirectiveRepository().list_all()` returns 27+ directives (19 existing + `test-first` + 7 new).
**Prompt**: `tasks/WP08-create-new-directives.md`
**Estimated size**: ~500 lines

### Included Subtasks

- [ ] T059 Create 020-worklog-creation.directive.yaml (from doctrine_ref/014)
- [ ] T060 Create 021-prompt-storage.directive.yaml (from doctrine_ref/015)
- [ ] T061 Create 022-commit-protocol.directive.yaml (from doctrine_ref/026)
- [ ] T062 Create 023-clarification-before-execution.directive.yaml (from doctrine_ref/023)
- [ ] T063 Create 024-locality-of-change.directive.yaml (from doctrine_ref/021)
- [ ] T064 Create 025-boy-scout-rule.directive.yaml (from doctrine_ref/036)
- [ ] T065 Create 026-hic-escalation-protocol.directive.yaml (from doctrine_ref/040)

### Implementation Notes

- Each new directive uses the enriched format from the start (scope, procedures, integrity_rules, validation_criteria)
- Adapt `doctrine_ref` content to fit YAML schema; strip markdown formatting, convert to structured fields
- Wire `tactic_refs` where applicable — may require creating new tactics (see WP10)
- IDs follow pattern: `DIRECTIVE_020`, `DIRECTIVE_021`, etc.
- Files placed in `src/doctrine/directives/shipped/`

### Dependencies

- Depends on WP01 (schema extended + repository exists)

### Parallel Opportunities

- Can run parallel with WP06, WP07 (different files)

---

## Work Package WP09: Consistency Tests & Enriched Directive Validation (Priority: P2)

**Goal**: Extend existing cross-artifact consistency tests with tactic_ref resolution; create enriched directive content validation tests.
**Independent Test**: `pytest tests/doctrine/test_directive_consistency.py` passes; every `tactic_ref` in every shipped directive resolves to an existing tactic.
**Prompt**: `tasks/WP09-consistency-tests.md`
**Estimated size**: ~300 lines

### Included Subtasks

- [ ] T066 Extend `tests/doctrine/test_directive_consistency.py` with tactic_ref resolution tests (scan all shipped directives, verify each `tactic_ref` resolves to an existing tactic file in `shipped/`)
- [ ] T067 Create `tests/doctrine/test_enriched_directives.py` — verify no shipped directive has single-sentence `intent`, all have `scope` field
- [ ] T068 Verify all existing doctrine tests pass with relocated files (full test suite run)

### Implementation Notes

- **Do NOT create a new `test_consistency.py`** — extend the existing `test_directive_consistency.py` which already tests profile-to-directive cross-references and schema validation
- The existing file has `DIRECTIVES_DIR` pointing to `shipped/` (updated in WP01) — add new test functions for tactic_ref resolution
- Enriched directive test: parametrize over all shipped directive files, assert `intent` is multi-sentence and `scope` is present

### Dependencies

- Depends on WP01-WP04 (file relocation must be complete)
- Depends on WP06, WP07, WP08 (enriched directives must exist)

---

## Work Package WP10: New Tactics & Supporting Artifacts (Priority: P3)

**Goal**: Create new tactic, styleguide, or toolguide YAML files where directive enrichment or new directives reference operational patterns not yet captured.
**Independent Test**: Every `tactic_ref` in every shipped directive resolves to a tactic file in `src/doctrine/tactics/shipped/`.
**Prompt**: `tasks/WP10-new-tactics-and-supporting-artifacts.md`
**Estimated size**: ~400 lines

### Included Subtasks

- [ ] T069 Audit all enriched and new directives for unresolved `tactic_refs`
- [ ] T070 [P] Create new tactic YAML files in `src/doctrine/tactics/shipped/` for unresolved references
- [ ] T071 [P] Create new styleguide YAML files in `src/doctrine/styleguides/shipped/` if needed
- [ ] T072 [P] Create new toolguide YAML files in `src/doctrine/toolguides/shipped/` if needed
- [ ] T073 Validate all new artifacts against their respective schemas

### Implementation Notes

- Audit output from WP06/WP07/WP08 drives this WP
- New tactics follow `doctrine_ref/tactics/` as reference material — adapt to existing tactic schema
- Minimum viable tactic: `schema_version`, `id`, `name`, `steps` (at least 1 step)
- Only create artifacts that are actually referenced by a directive — don't speculatively create unused artifacts

### Dependencies

- Depends on WP06, WP07, WP08 (enriched directives must be finalized to know which refs are needed)
- Depends on WP02, WP03, WP04 (repositories must exist for validation)

---

## Dependency & Execution Summary

```
Phase 1 (Foundation - parallel):
  WP01 ─┐  (directive model + schema extension + file move + test path updates)
  WP02 ─┤  (tactic model + file move + test path updates)
  WP03 ─┼──→ WP05 (DoctrineService, needs all repos)
  WP04 ─┘  (toolguide/paradigm models + paradigm schema + file move + test path updates)

Phase 2 (Content - parallel after WP01):
  WP06 ─┐
  WP07 ─┼──→ WP09 (Consistency tests, needs enriched content)
  WP08 ─┘──→ WP10 (New tactics, needs directive audit)

Execution order:
  [WP01, WP02, WP03, WP04] → [WP05] → [WP06, WP07, WP08] → [WP09, WP10]
```

**Key changes from v1**:
- WP05 (schema extension) merged into WP01 — eliminates the gap where enriched directives can't validate
- Each WP updates affected test paths — test suite stays green after every merge
- WP09 extends existing `test_directive_consistency.py` instead of creating a new file
- WP numbers shifted: old WP06→WP05, old WP07→WP06, old WP08→WP07, old WP09→WP08, old WP10→WP09, old WP11→WP10

**Parallelization**: WP01-WP04 can all run simultaneously. WP06-WP08 can run simultaneously. WP05 can start as soon as WP01-04 complete. WP06-08 only need WP01 (not WP05).

**MVP Scope**: WP01-WP05 deliver the core domain models, repositories, and service (User Stories 1-4, 6).
**Content Scope**: WP06-WP10 deliver directive enrichment and consistency (User Stories 5, 7).

---

## Subtask Index (Reference)

| Subtask | Summary | WP |
|---------|---------|-----|
| T001 | Update `directive.schema.yaml` (remove `additionalProperties: false`, add enrichment fields) | WP01 |
| T002 | Create `directives/__init__.py` | WP01 |
| T003 | Create `directives/models.py` (Directive with enrichment fields, Enforcement) | WP01 |
| T004 | Create `directives/repository.py` (DirectiveRepository) | WP01 |
| T005 | Create `directives/validation.py` | WP01 |
| T006 | Move directive YAML files into `shipped/` | WP01 |
| T007 | Update `test_directive_consistency.py` paths | WP01 |
| T008 | Update `test_artifact_compliance.py` directive paths | WP01 |
| T009 | Update `test_tactic_compliance.py` directive entry in `ARTIFACT_DIRS` | WP01 |
| T010 | Write ATDD/TDD tests for directives (model + schema backward-compat + enriched) | WP01 |
| T011 | Create `tactics/__init__.py` | WP02 |
| T012 | Create `tactics/models.py` (Tactic, TacticStep, TacticReference) | WP02 |
| T013 | Create `tactics/repository.py` (TacticRepository) | WP02 |
| T014 | Create `tactics/validation.py` | WP02 |
| T015 | Move tactic YAML files into `shipped/` | WP02 |
| T016 | Update `test_tactic_compliance.py` tactic paths | WP02 |
| T017 | Update `test_artifact_compliance.py` tactic paths | WP02 |
| T018 | Write ATDD/TDD tests for tactics | WP02 |
| T019 | Create `styleguides/__init__.py` | WP03 |
| T020 | Create `styleguides/models.py` (Styleguide, AntiPattern, StyleguideScope) | WP03 |
| T021 | Create `styleguides/repository.py` (StyleguideRepository) | WP03 |
| T022 | Create `styleguides/validation.py` | WP03 |
| T023 | Move styleguide YAML files into `shipped/` (including `writing/`) | WP03 |
| T024 | Update `test_artifact_compliance.py` styleguide paths | WP03 |
| T025 | Update `test_tactic_compliance.py` styleguide entry in `ARTIFACT_DIRS` | WP03 |
| T026 | Write ATDD/TDD tests for styleguides | WP03 |
| T027 | Create `paradigm.schema.yaml` | WP04 |
| T028 | Create `toolguides/__init__.py`, `models.py`, `repository.py`, `validation.py` | WP04 |
| T029 | Move toolguide YAML + companion MD into `shipped/` | WP04 |
| T030 | Create `paradigms/__init__.py`, `models.py`, `repository.py`, `validation.py` | WP04 |
| T031 | Move paradigm YAML files into `shipped/` | WP04 |
| T032 | Update `test_artifact_compliance.py` toolguide paths | WP04 |
| T033 | Update `test_tactic_compliance.py` toolguide entry in `ARTIFACT_DIRS` | WP04 |
| T034 | Create paradigm test fixtures | WP04 |
| T035 | Write ATDD/TDD tests for toolguides and paradigms | WP04 |
| T036 | Create `service.py` with DoctrineService | WP05 |
| T037 | Update `doctrine/__init__.py` exports | WP05 |
| T038 | Write ATDD/TDD tests for DoctrineService | WP05 |
| T039 | Enrich directive 001 | WP06 |
| T040 | Enrich directive 002 | WP06 |
| T041 | Enrich directive 003 | WP06 |
| T042 | Enrich directive 004 | WP06 |
| T043 | Enrich directive 005 | WP06 |
| T044 | Enrich directive 006 | WP06 |
| T045 | Enrich directive 007 | WP06 |
| T046 | Enrich directive 008 | WP06 |
| T047 | Enrich directive 009 | WP06 |
| T048 | Enrich directive 010 | WP06 |
| T049 | Enrich directive 011 | WP07 |
| T050 | Enrich directive 012 | WP07 |
| T051 | Enrich directive 013 | WP07 |
| T052 | Enrich directive 014 | WP07 |
| T053 | Enrich directive 015 | WP07 |
| T054 | Enrich directive 016 | WP07 |
| T055 | Enrich directive 017 | WP07 |
| T056 | Enrich directive 018 | WP07 |
| T057 | Enrich directive 019 | WP07 |
| T058 | Verify test-first directive enrichment | WP07 |
| T059 | Create directive 020 (worklog creation) | WP08 |
| T060 | Create directive 021 (prompt storage) | WP08 |
| T061 | Create directive 022 (commit protocol) | WP08 |
| T062 | Create directive 023 (clarification before execution) | WP08 |
| T063 | Create directive 024 (locality of change) | WP08 |
| T064 | Create directive 025 (boy scout rule) | WP08 |
| T065 | Create directive 026 (HiC escalation protocol) | WP08 |
| T066 | Extend `test_directive_consistency.py` with tactic_ref resolution | WP09 |
| T067 | Create `test_enriched_directives.py` | WP09 |
| T068 | Verify all existing tests pass | WP09 |
| T069 | Audit directives for unresolved tactic_refs | WP10 |
| T070 | Create new tactic YAML files | WP10 |
| T071 | Create new styleguide YAML files | WP10 |
| T072 | Create new toolguide YAML files | WP10 |
| T073 | Validate all new artifacts against schemas | WP10 |

<!-- status-model:start -->
## Canonical Status (Generated)

- WP01: done
- WP02: done
- WP03: done
- WP04: for_review
- WP05: for_review
- WP06: for_review
- WP07: for_review
<!-- status-model:end -->
