---
work_package_id: WP08
title: Create New Shipped Directives
lane: "done"
dependencies: [WP01]
base_branch: feature/agent-profile-implementation
base_commit: f6306beadf9e7f0d90c8a37954abf1f3555a4350
created_at: '2026-02-28T08:36:11.456737+00:00'
subtasks:
- T059
- T060
- T061
- T062
- T063
- T064
- T065
phase: Phase 2 - Content
assignee: ''
agent: claude-sonnet
shell_pid: '1520139'
review_status: "approved"
reviewed_by: "Stijn Dejongh"
review_feedback: "feedback://046-doctrine-artifact-domain-models/WP08/20260304T042931Z-6ee02237.md"
history:
- timestamp: '2026-02-26T04:36:22Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP08 – Create New Shipped Directives

## ⚠️ IMPORTANT: Review Feedback Status

- **Has review feedback?**: Check the `review_status` field above.

---

## Review Feedback

*[This section is empty initially.]*

---

## Objectives & Success Criteria

- Enrich all 9 shipped directives (011-019) plus `test-first` with substantive content
- Same enrichment standards as WP07: expanded intent, scope, procedures/validation-criteria
- All enriched directives validate against updated schema
- `test-first.directive.yaml` already has `tactic-refs` — only add `scope` and `procedures`

## Context & Constraints

- **Depends on WP01**: YAML files must be in `shipped/`
- **Depends on WP05**: Schema must support enrichment fields
- **Parallel with WP07**: Different directive files, no overlap
- **Note**: `test-first.directive.yaml` is a special case — it already has populated `tactic-refs`, so only `scope` and `procedures` need to be added

## Subtasks & Detailed Guidance

### Subtask T042 – Enrich 011-feedback-clarity-standard

- **Purpose**: Add scope and procedures for feedback quality.
- **Steps**: Read current file, expand intent, add scope (all review comments, PR feedback, issue responses), add procedures (specific, actionable language; reference code lines; suggest alternatives), add validation-criteria.
- **Files**: `src/doctrine/directives/shipped/011-feedback-clarity-standard.directive.yaml`

### Subtask T043 – Enrich 012-work-package-granularity-standard

- **Purpose**: Add scope and procedures for work package sizing.
- **Steps**: Enrich with scope (all work package creation, task decomposition), procedures (3-7 subtasks target, 200-500 line prompts, split if >10 subtasks), integrity-rules (no WP >10 subtasks).
- **Files**: `src/doctrine/directives/shipped/012-work-package-granularity-standard.directive.yaml`

### Subtask T044 – Enrich 013-dependency-validation-requirement

- **Purpose**: Add scope and procedures for dependency management.
- **Steps**: Enrich with scope (all WP dependencies, cross-feature references), procedures (declare deps in frontmatter, validate DAG, no circular deps), validation-criteria (cycle detection passes, all refs valid).
- **Files**: `src/doctrine/directives/shipped/013-dependency-validation-requirement.directive.yaml`

### Subtask T045 – Enrich 014-acceptance-criteria-completeness

- **Purpose**: Add scope and procedures for acceptance criteria.
- **Steps**: Enrich with scope (all user stories, feature specs), procedures (testable criteria, measurable outcomes, no vague adjectives), integrity-rules (every requirement must have acceptance criteria).
- **Files**: `src/doctrine/directives/shipped/014-acceptance-criteria-completeness.directive.yaml`

### Subtask T046 – Enrich 015-research-time-boxing-requirement

- **Purpose**: Add scope and procedures for research time-boxing.
- **Steps**: Enrich with scope (all research tasks, Phase 0 activities), procedures (set time limit before starting, document findings regardless of outcome, escalate if blocked), validation-criteria (research completes within timebox, findings documented).
- **Files**: `src/doctrine/directives/shipped/015-research-time-boxing-requirement.directive.yaml`

### Subtask T047 – Enrich 016-finding-documentation-standard

- **Purpose**: Add scope and procedures for finding documentation.
- **Steps**: Enrich with scope (all research findings, technical investigations), procedures (structured finding format, link to evidence, categorize by impact), validation-criteria (all findings have rationale and source).
- **Files**: `src/doctrine/directives/shipped/016-finding-documentation-standard.directive.yaml`

### Subtask T048 – Enrich 017-glossary-integrity-standard

- **Purpose**: Add scope and procedures for glossary integrity.
- **Steps**: Enrich with scope (all user-facing text, documentation, code comments), procedures (use canonical terms, check glossary before introducing new terms, update glossary when adding terms), integrity-rules (no synonyms for canonical terms). Wire tactic-refs to glossary-related tactics/styleguides if applicable.
- **Files**: `src/doctrine/directives/shipped/017-glossary-integrity-standard.directive.yaml`

### Subtask T049 – Enrich 018-doctrine-versioning-requirement

- **Purpose**: Add scope and procedures for doctrine versioning.
- **Steps**: Enrich with scope (all doctrine artifact changes, schema updates), procedures (bump schema_version on breaking changes, maintain backward compatibility, document version history), integrity-rules (no breaking changes without version bump).
- **Files**: `src/doctrine/directives/shipped/018-doctrine-versioning-requirement.directive.yaml`

### Subtask T050 – Enrich 019-documentation-gap-prioritization

- **Purpose**: Add scope and procedures for documentation gap analysis.
- **Steps**: Enrich with scope (all documentation gaps identified by Divio audit), procedures (prioritize by user impact, HIGH for missing tutorials/core reference, MEDIUM for how-tos, LOW for explanations), validation-criteria (gap analysis documented, HIGH priority gaps addressed first).
- **Files**: `src/doctrine/directives/shipped/019-documentation-gap-prioritization.directive.yaml`

### Subtask T051 – Verify test-first.directive.yaml enrichment

- **Purpose**: Add scope and procedures to test-first without changing existing tactic-refs.
- **Steps**:
  1. Read current `test-first.directive.yaml` — it already has `tactic-refs`
  2. Add `scope`: "Applies to all code changes that add or modify behavior. Covers feature work, bug fixes, and refactoring with behavioral changes."
  3. Add `procedures`: ordered steps for test-first workflow
  4. Do NOT modify existing `tactic-refs` or `enforcement`
  5. Validate against schema
- **Files**: `src/doctrine/directives/shipped/test-first.directive.yaml`
- **Notes**: This is a special case — preserve existing content, only add enrichment fields

## Test Strategy

```bash
pytest tests/doctrine/directives/ -v -k "schema"
```

Same validation checklist as WP07 — each directive must have expanded intent, scope, and at least procedures or validation-criteria.

## Risks & Mitigations

- **test-first special handling**: Must preserve existing tactic-refs — read file carefully before modifying
- **Directive numbering 011-019**: These are spec-kitty process directives (not software engineering ones) — enrichment content should reflect process/workflow concerns

## Review Guidance

- Verify test-first.directive.yaml preserves existing tactic-refs
- Verify all 10 directives validate against schema
- Verify enrichment content matches each directive's domain (process vs engineering)

## Activity Log

- 2026-02-26T04:36:22Z – system – lane=planned – Prompt created.

---

### Implementation Command

Depends on WP01 and WP05 (parallel with WP07):
```bash
spec-kitty implement WP08 --base WP05
```
- 2026-02-28T08:36:11Z – codex – shell_pid=112867 – lane=doing – Assigned agent via workflow command
- 2026-02-28T08:46:06Z – codex – shell_pid=194283 – lane=for_review – Moved to for_review
- 2026-03-04T04:27:10Z – claude-sonnet – shell_pid=1520139 – lane=doing – Started review via workflow command
- 2026-03-04T04:29:31Z – claude-sonnet – shell_pid=1520139 – lane=planned – Moved to planned
- 2026-03-04T04:45:39Z – claude-sonnet – shell_pid=1520139 – lane=done – Directives 011-019 + test-first all enriched via WP07 codex branch merged through WP10. All have scope, procedures. test-first has tactic_refs preserved.
