---
work_package_id: "WP09"
subtasks:
  - "T052"
  - "T053"
  - "T054"
  - "T055"
  - "T056"
  - "T057"
  - "T058"
title: "Create New Shipped Directives"
phase: "Phase 2 - Content"
lane: "done"
assignee: ""
agent: ""
shell_pid: ""
review_status: "approved"
reviewed_by: "Stijn Dejongh"
dependencies: ["WP01", "WP05"]
history:
  - timestamp: "2026-02-26T04:36:22Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP09 – Create New Shipped Directives

## ⚠️ IMPORTANT: Review Feedback Status

- **Has review feedback?**: Check the `review_status` field above.

---

## Review Feedback

*[This section is empty initially.]*

---

## Objectives & Success Criteria

- Create 7 new shipped directives (020-026) from doctrine_ref concepts not yet represented
- Each uses the enriched format from the start (scope, procedures, integrity-rules, validation-criteria)
- IDs follow SCREAMING_SNAKE_CASE: `DIRECTIVE_020` through `DIRECTIVE_026`
- Files placed in `src/doctrine/directives/shipped/`
- `DirectiveRepository().list_all()` returns 27+ directives (19 existing + test-first + 7 new)
- All new directives validate against updated schema

## Context & Constraints

- **Depends on WP01**: Repository must exist for validation
- **Depends on WP05**: Schema must support enrichment fields
- **Parallel with WP07, WP08**: Different files
- **Research R-003**: Maps doctrine_ref concepts to new directive numbers
- **DD-007**: New directives from doctrine_ref, numbering from 020 onward

## Subtasks & Detailed Guidance

### Subtask T052 – Create 020-worklog-creation.directive.yaml

- **Purpose**: Establish the worklog creation governance rule (from doctrine_ref/014).
- **Steps**:
  1. Read `src/doctrine/doctrine_ref/directives/014-worklog-creation.md` for reference
  2. Create `src/doctrine/directives/shipped/020-worklog-creation.directive.yaml`:
     ```yaml
     schema-version: "1.0"
     id: DIRECTIVE_020
     title: Worklog Creation Standard
     intent: |
       Ensure all significant work activities are recorded in structured work logs
       to enable traceability, progress tracking, and knowledge preservation.
     enforcement: advisory
     scope: |
       Applies to all feature implementation, research tasks, and investigation work.
       Exception: trivial one-line fixes that don't alter behavior.
     procedures:
       - "Create a work log entry at the start of each work session"
       - "Record key decisions, obstacles encountered, and resolutions"
       - "Link work log entries to relevant work package IDs"
       - "Update work log at natural breakpoints and session end"
     integrity-rules:
       - "Work logs must reference the work package or task being addressed"
       - "Entries must include timestamps"
     validation-criteria:
       - "Every completed work package has associated work log entries"
       - "Work logs are parseable and follow consistent format"
     ```
  3. Adapt content from doctrine_ref — don't copy verbatim
  4. Validate against schema
- **Files**: `src/doctrine/directives/shipped/020-worklog-creation.directive.yaml` (new)

### Subtask T053 – Create 021-prompt-storage.directive.yaml

- **Purpose**: Establish prompt storage governance (from doctrine_ref/015).
- **Steps**:
  1. Read `src/doctrine/doctrine_ref/directives/015-store-prompts.md`
  2. Create directive focusing on: storing AI prompts used during development for reproducibility and audit
  3. `enforcement: advisory`
  4. Include scope, procedures for prompt storage, validation-criteria
- **Files**: `src/doctrine/directives/shipped/021-prompt-storage.directive.yaml` (new)

### Subtask T054 – Create 022-commit-protocol.directive.yaml

- **Purpose**: Establish commit protocol governance (from doctrine_ref/026).
- **Steps**:
  1. Read `src/doctrine/doctrine_ref/directives/026-commit-protocol.md`
  2. Create directive covering: conventional commits, atomic commits, meaningful messages
  3. `enforcement: required`
  4. Include procedures for commit message format, when to commit, what constitutes atomic
  5. Include integrity-rules: no WIP commits to main, no merge commits without context
- **Files**: `src/doctrine/directives/shipped/022-commit-protocol.directive.yaml` (new)

### Subtask T055 – Create 023-clarification-before-execution.directive.yaml

- **Purpose**: Establish clarification-before-execution governance (from doctrine_ref/023).
- **Steps**:
  1. Read `src/doctrine/doctrine_ref/directives/023-clarification-before-execution.md`
  2. Create directive covering: when to ask for clarification vs proceeding, how to formulate questions
  3. `enforcement: required`
  4. Include procedures for identifying ambiguity, escalation path, documentation of assumptions
  5. Include integrity-rules: never proceed with significant ambiguity in scope or requirements
- **Files**: `src/doctrine/directives/shipped/023-clarification-before-execution.directive.yaml` (new)

### Subtask T056 – Create 024-locality-of-change.directive.yaml

- **Purpose**: Establish locality of change governance (from doctrine_ref/021).
- **Steps**:
  1. Read `src/doctrine/doctrine_ref/directives/021-locality-of-change.md`
  2. Create directive covering: minimize blast radius, keep changes close to the problem, avoid unrelated modifications
  3. `enforcement: required`
  4. Include procedures for scoping changes, reviewing diff for scope creep
  5. Include integrity-rules: no unrelated changes in the same commit/PR
- **Files**: `src/doctrine/directives/shipped/024-locality-of-change.directive.yaml` (new)

### Subtask T057 – Create 025-boy-scout-rule.directive.yaml

- **Purpose**: Establish boy scout rule governance (from doctrine_ref/036).
- **Steps**:
  1. Read `src/doctrine/doctrine_ref/directives/036-boy-scout-rule.md`
  2. Create directive covering: leave code better than you found it, but within locality constraints
  3. `enforcement: advisory`
  4. Include procedures for identifying small improvements, balancing with locality of change
  5. Include scope: only improvements within the area of active work, not sweeping refactors
- **Files**: `src/doctrine/directives/shipped/025-boy-scout-rule.directive.yaml` (new)
- **Notes**: This directive has natural tension with directive 024 (locality of change) — address this in the scope section

### Subtask T058 – Create 026-hic-escalation-protocol.directive.yaml

- **Purpose**: Establish human-in-command escalation protocol (from doctrine_ref/040).
- **Steps**:
  1. Read `src/doctrine/doctrine_ref/directives/040-hic-escalation-protocol.md`
  2. Create directive covering: when agents must escalate to human, what constitutes a blocker, how to format escalation requests
  3. `enforcement: required`
  4. Include procedures for escalation triggers, escalation format, waiting behavior
  5. Include integrity-rules: agents must never proceed past an escalation trigger without human approval
- **Files**: `src/doctrine/directives/shipped/026-hic-escalation-protocol.directive.yaml` (new)

## Test Strategy

```bash
# Validate all new directives
pytest tests/doctrine/directives/ -v -k "schema"

# Quick validation via repository
python -c "
from doctrine.directives import DirectiveRepository
r = DirectiveRepository()
for d in r.list_all():
    if int(d.id.split('_')[1]) >= 20:
        print(f'{d.id}: {d.title} (scope={bool(d.scope)}, procs={len(d.procedures)})')
"
```

## Risks & Mitigations

- **doctrine_ref files may not exist**: If specific doctrine_ref files are missing, create directives based on the concept name and general best practices
- **tactic-refs to non-existent tactics**: Wire tactic-refs conservatively — only reference existing tactics. New tactics for these directives will be created in WP11

## Review Guidance

- Verify each directive has substantive, non-placeholder content
- Verify `enforcement` level is appropriate (required vs advisory)
- Verify content adapted from doctrine_ref (not verbatim)
- Verify directive numbering is sequential (020-026)
- Verify all 7 files validate against schema

## Activity Log

- 2026-02-26T04:36:22Z – system – lane=planned – Prompt created.

---

### Implementation Command

Depends on WP01 and WP05 (parallel with WP07, WP08):
```bash
spec-kitty implement WP09 --base WP05
```
- 2026-03-04T04:46:54Z – unknown – lane=done – Reviewed and approved: tactic-ref and enrichment consistency tests passing. 469 tests total.
