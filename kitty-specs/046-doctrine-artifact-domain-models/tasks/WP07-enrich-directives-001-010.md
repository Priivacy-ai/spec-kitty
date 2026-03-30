---
work_package_id: WP07
title: Enrich Existing Directives 001-010
<<<<<<< HEAD
lane: "done"
=======
lane: "for_review"
>>>>>>> 046-doctrine-artifact-domain-models-WP10
dependencies: [WP01, WP05]
base_branch: feature/agent-profile-implementation
base_commit: 79cfabb61acb3e08614228c4bd7ae0a7b95c5bab
created_at: '2026-02-28T08:33:57.728017+00:00'
subtasks:
- T032
- T033
- T034
- T035
- T036
- T037
- T038
- T039
- T040
- T041
phase: Phase 2 - Content
assignee: ''
<<<<<<< HEAD
agent: claude-sonnet
shell_pid: '1519962'
review_status: "approved"
reviewed_by: "Stijn Dejongh"
review_feedback: "feedback://046-doctrine-artifact-domain-models/WP07/20260304T042931Z-9ac15c08.md"
=======
agent: "codex"
shell_pid: '112867'
review_status: ''
reviewed_by: ''
>>>>>>> 046-doctrine-artifact-domain-models-WP10
history:
- timestamp: '2026-02-26T04:36:22Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP07 – Enrich Existing Directives 001-010

## ⚠️ IMPORTANT: Review Feedback Status

- **Has review feedback?**: Check the `review_status` field above.

---

## Review Feedback

*[This section is empty initially.]*

---

## Objectives & Success Criteria

- Enrich all 10 shipped directives (001-010) with substantive content using the enriched YAML format
- Each enriched directive has: expanded `intent` (>1 sentence), `scope`, and at least `procedures` or `validation-criteria`
- Wire `tactic-refs` to existing tactics where applicable
- All enriched directives validate against the updated schema (WP05)
- `DirectiveRepository().get("004")` returns a Directive with non-empty `scope`, `procedures`, and `tactic-refs`

## Context & Constraints

- **Depends on WP01**: YAML files must be in `shipped/` directory
- **Depends on WP05**: Schema must support enrichment fields
- **Reference material**: Use `src/doctrine/doctrine_ref/directives/` as reference — adapt content, don't copy verbatim
- **Research R-003**: Maps doctrine_ref directives to existing shipped directives (003←018, 004←016+017, 010←034)
- **DD-002**: Pure YAML with multiline string fields (`|` block scalar)

## Subtasks & Detailed Guidance

### Subtask T032 – Enrich 001-architectural-integrity-standard

- **Purpose**: Add scope, procedures, and validation criteria for architectural integrity.
- **Steps**:
  1. Read current `001-architectural-integrity-standard.directive.yaml` in `shipped/`
  2. Expand `intent` to 2-3 sentences explaining behavioral context
  3. Add `scope`: when this directive applies (all architectural decisions, all refactoring beyond cosmetic changes)
  4. Add `procedures`: ordered steps (e.g., "Review existing architecture documentation before proposing changes", "Document rationale for architectural deviations", "Validate changes against established patterns")
  5. Add `validation-criteria`: how to verify compliance (e.g., "Architecture decisions are documented", "No undocumented deviations from established patterns")
  6. Wire `tactic-refs` if applicable
  7. Validate against schema
- **Files**: `src/doctrine/directives/shipped/001-architectural-integrity-standard.directive.yaml`

### Subtask T033 – Enrich 002-accessibility-first-principle

- **Purpose**: Add scope and procedures for accessibility requirements.
- **Steps**: Same enrichment pattern as T032
  - `scope`: All user-facing interfaces, documentation, and output
  - `procedures`: Steps for ensuring accessibility (semantic HTML, WCAG guidelines, screen reader testing)
  - `validation-criteria`: WCAG 2.1 AA compliance checks, automated accessibility scanning
- **Files**: `src/doctrine/directives/shipped/002-accessibility-first-principle.directive.yaml`

### Subtask T034 – Enrich 003-decision-documentation-requirement

- **Purpose**: Incorporate doctrine_ref/018 (Traceable Decisions) into directive 003.
- **Steps**:
  1. Read `src/doctrine/doctrine_ref/directives/018-traceable-decisions.md` for reference
  2. Enrich directive 003 with decision logging procedures from doctrine_ref/018
  3. Add `scope`: all technical decisions, architecture choices, and trade-off resolutions
  4. Add `procedures`: decision log format, when to document, where to store
  5. Add `integrity-rules`: decisions must include rationale and alternatives considered
  6. Wire `tactic-refs` if applicable
- **Files**: `src/doctrine/directives/shipped/003-decision-documentation-requirement.directive.yaml`
- **Notes**: This is a merge of existing directive 003 with doctrine_ref 018 content

### Subtask T035 – Enrich 004-test-driven-implementation-standard

- **Purpose**: Incorporate doctrine_ref/016 (ATDD) + 017 (TDD) into directive 004.
- **Steps**:
  1. Read `src/doctrine/doctrine_ref/directives/016-*.md` and `017-*.md`
  2. This is the most important enrichment — the exemplar shown in plan.md DD-002
  3. Add `scope`: all features, bug fixes, refactors that alter observable behavior; exceptions for trivial scripts
  4. Add `procedures`:
     - "Capture behavior as an acceptance test before coding"
     - "Reference scenario ID inside test metadata"
     - "Keep acceptance tests close to real workflows"
     - "Delegate detailed work to TDD cycles once acceptance tests fail"
  5. Add `integrity-rules`:
     - "Failing acceptance test must exist before implementation begins"
     - "Acceptance tests must include clear Arrange/Act/Assert narrative"
  6. Add `validation-criteria`:
     - "All new code has corresponding test coverage"
     - "Tests pass in CI before merge"
     - "Test names describe the behavior being verified"
  7. Wire `tactic-refs`: `["acceptance-test-first", "tdd-red-green-refactor", "zombies-tdd"]`
- **Files**: `src/doctrine/directives/shipped/004-test-driven-implementation-standard.directive.yaml`
- **Notes**: Follow the exact enriched format from plan.md DD-002 example

### Subtask T036 – Enrich 005-design-system-consistency-standard

- **Purpose**: Add scope and procedures for design system adherence.
- **Steps**: Same enrichment pattern
  - `scope`: All UI components, layout patterns, color/typography usage
  - `procedures`: Reference design tokens, use component library, review against design spec
  - `validation-criteria`: Components match design system, no custom one-off styles
- **Files**: `src/doctrine/directives/shipped/005-design-system-consistency-standard.directive.yaml`

### Subtask T037 – Enrich 006-coding-standards-adherence

- **Purpose**: Add scope and procedures for coding standards.
- **Steps**: Same enrichment pattern
  - `scope`: All source code changes, configuration files, scripts
  - `procedures`: Follow language-specific style guides, use linters, automated formatting
  - `validation-criteria`: Linting passes, no style violations in CI
- **Files**: `src/doctrine/directives/shipped/006-coding-standards-adherence.directive.yaml`

### Subtask T038 – Enrich 007-scalability-assessment-protocol

- **Purpose**: Add scope and procedures for scalability reviews.
- **Steps**: Same enrichment pattern
  - `scope`: Features handling data at scale, API endpoints, background jobs
  - `procedures`: Load testing, capacity planning, bottleneck analysis
  - `integrity-rules`: No O(n²) algorithms without documented justification
- **Files**: `src/doctrine/directives/shipped/007-scalability-assessment-protocol.directive.yaml`

### Subtask T039 – Enrich 008-security-review-protocol

- **Purpose**: Add scope and procedures for security reviews.
- **Steps**: Same enrichment pattern
  - `scope`: All authentication, authorization, data handling, external API integration
  - `procedures`: OWASP top 10 review, dependency vulnerability scan, secrets management
  - `integrity-rules`: No plaintext secrets, no SQL injection vectors, HTTPS enforced
  - `validation-criteria`: Security scan passes, no critical/high vulnerabilities
- **Files**: `src/doctrine/directives/shipped/008-security-review-protocol.directive.yaml`

### Subtask T040 – Enrich 009-user-centered-validation-requirement

- **Purpose**: Add scope and procedures for user validation.
- **Steps**: Same enrichment pattern
  - `scope`: All user-facing features, workflow changes, UI/UX modifications
  - `procedures`: User story validation, usability testing, feedback collection
  - `validation-criteria`: User acceptance criteria met, no usability regressions
- **Files**: `src/doctrine/directives/shipped/009-user-centered-validation-requirement.directive.yaml`

### Subtask T041 – Enrich 010-specification-fidelity-requirement

- **Purpose**: Incorporate doctrine_ref/034 (Spec-Driven Development) into directive 010.
- **Steps**:
  1. Read `src/doctrine/doctrine_ref/directives/034-*.md`
  2. Enrich directive 010 with spec-driven development practices
  3. Add `scope`: all feature implementations, all code changes with a spec
  4. Add `procedures`: implement from spec, verify against acceptance criteria, flag spec deviations
  5. Add `integrity-rules`: no implementation without specification, deviations documented
  6. Wire `tactic-refs` if applicable
- **Files**: `src/doctrine/directives/shipped/010-specification-fidelity-requirement.directive.yaml`

## Test Strategy

After enriching all 10 directives:
```bash
# Validate all enriched directives against schema
pytest tests/doctrine/directives/ -v -k "schema"

# Load all directives via repository
python -c "from doctrine.directives import DirectiveRepository; r = DirectiveRepository(); [print(f'{d.id}: scope={bool(d.scope)}') for d in r.list_all()]"
```

**Validation checklist per directive**:
- [ ] Intent is >1 sentence
- [ ] Scope field is non-empty
- [ ] At least procedures or validation-criteria is non-empty
- [ ] Validates against updated schema
- [ ] Loads via DirectiveRepository without errors

## Risks & Mitigations

- **Content quality**: doctrine_ref content must be adapted, not copied — paraphrase and structure for YAML format
- **tactic-refs pointing to non-existent tactics**: Some enriched directives may reference tactics that don't exist yet — these will be created in WP11

## Review Guidance

- Verify each directive has substantive content (not placeholder text)
- Verify doctrine_ref source material was adapted (not verbatim copied)
- Verify all 10 directives validate against schema
- Check that `tactic-refs` reference real tactic IDs where possible

## Activity Log

- 2026-02-26T04:36:22Z – system – lane=planned – Prompt created.

---

### Implementation Command

Depends on WP01 and WP05:
```bash
spec-kitty implement WP07 --base WP05
```
- 2026-02-28T08:33:57Z – codex – shell_pid=112867 – lane=doing – Assigned agent via workflow command
- 2026-02-28T08:36:03Z – codex – shell_pid=112867 – lane=for_review – Ready for review: directives 011-019 + test-first enriched
<<<<<<< HEAD
- 2026-03-04T04:27:05Z – claude-sonnet – shell_pid=1519962 – lane=doing – Started review via workflow command
- 2026-03-04T04:29:31Z – claude-sonnet – shell_pid=1519962 – lane=planned – Moved to planned
=======
>>>>>>> 046-doctrine-artifact-domain-models-WP10
- 2026-03-04T04:45:38Z – claude-sonnet – shell_pid=1519962 – lane=done – Directives 001-010 all enriched via WP06 codex branch merged through WP10. All have scope, procedures, validation_criteria. Directive 004 has tactic_refs=[acceptance-test-first, tdd-red-green-refactor, zombies-tdd].
