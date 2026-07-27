---
work_package_id: WP07
title: Close the Integration and Compatibility Gaps
lane: "done"
dependencies:
- WP01
- WP02
- WP03
- WP05
- WP06
base_branch: feature/agent-profile-implementation
base_commit: 45ae7f1915fe5de494c8625d061afd11c0c07dfe
created_at: '2026-03-10T07:02:14.347681+00:00'
subtasks:
- T036
- T037
- T038
phase: Phase 4 - Integration Hardening
assignee: ''
agent: ''
shell_pid: '597638'
review_status: "approved"
reviewed_by: "Stijn Dejongh"
history:
- timestamp: '2026-03-09T14:23:30Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
requirement_refs:
- FR-010
- FR-017
- FR-018
- NFR-001
- NFR-002
---

# Work Package Prompt: WP07 - Close the Integration and Compatibility Gaps

## ⚠️ IMPORTANT: Review Feedback Status

- Review feedback, if present, is blocking.

---

## Review Feedback

*[Empty initially.]*  

---

## Markdown Formatting

Use fenced code blocks when needed. Keep file and command references in backticks.

## Objectives & Success Criteria

- Existing integration and e2e tests align with the new CLI, compiler, and context contracts.
- An end-to-end scenario proves explicit local support declarations, additive conflict warnings, and first-vs-subsequent context behavior.
- Downstream consumers that request constitution context continue to function with the updated JSON/text contract.

## Context & Constraints

- Primary files:
  - `tests/integration/test_profile_constitution_e2e.py`
  - `tests/e2e/test_doctrine_reconstruction.py`
  - `src/specify_cli/next/prompt_builder.py`
  - `src/specify_cli/cli/commands/agent/workflow.py`
  - any additional targeted test modules that consume constitution context
- Reference scenario: `kitty-specs/054-constitution-interview-compiler-and-bootstrap/quickstart.md`
- Implementation command: `spec-kitty implement WP07 --base WP06`

## Subtasks & Detailed Guidance

### Subtask T036 - Refresh legacy integration and e2e tests

- **Purpose**: Remove stale expectations that will otherwise obscure real regressions.
- **Steps**:
  1. Audit tests that still expect:
     - generated `.kittify/constitution/library/`
     - legacy JSON keys such as `success`, `constitution_path`, or `files_written` as the only output contract
     - old compact/bootstrap payload assumptions
  2. Update only the assertions that changed because of this feature.
  3. Keep broad behavioral coverage intact rather than deleting failing assertions wholesale.
- **Files**:
  - integration/e2e tests touched by the constitution pipeline
- **Parallel?**: Yes
- **Notes**: This is cleanup with intent, not a blanket snapshot refresh.

### Subtask T037 - Add an end-to-end scenario for declared local support files

- **Purpose**: Prove the full feature story works outside isolated unit tests.
- **Steps**:
  1. Create or extend one integration/e2e scenario that:
     - writes interview answers with at least one explicit local support declaration
     - runs generation
     - verifies `library_files`
     - verifies no generated `library/` or `agents.yaml`
     - exercises first and second `context` calls for an action
  2. Assert additive warning behavior when the local file targets the same concept as a shipped artifact.
  3. Keep the fixture compact and tied to the quickstart narrative.
- **Files**:
  - one focused integration/e2e test module
- **Parallel?**: No
- **Notes**: Prefer one strong scenario over multiple weak, overlapping ones.

### Subtask T038 - Verify workflow and prompt-builder compatibility

- **Purpose**: Ensure downstream consumers still use constitution context correctly after the JSON/rendering changes.
- **Steps**:
  1. Inspect `src/specify_cli/cli/commands/agent/workflow.py` and `src/specify_cli/next/prompt_builder.py` call sites.
  2. Add targeted regression tests if the current suites do not already cover:
     - `text` availability
     - bootstrap/compact mode handling
     - absence of crashes when constitution artifacts are missing or partial
  3. Confirm these consumers do not depend on removed library materialization.
- **Files**:
  - `src/specify_cli/cli/commands/agent/workflow.py`
  - `src/specify_cli/next/prompt_builder.py`
  - related tests
- **Parallel?**: Yes
- **Notes**: This WP is the final compatibility sweep; do not let subtle downstream breakages survive because the core CLI tests were green.

## Test Strategy

- Run the targeted integration/e2e suites you update.
- Re-run any workflow or prompt-builder regression tests touched by this WP.

## Risks & Mitigations

- Integration cleanup can be noisy. Keep changes tightly tied to the new contract so reviewers can distinguish intended evolution from accidental behavior drift.
- Downstream consumers often rely on text shape implicitly. Preserve the core rendering structure while standardizing the JSON envelope.

## Review Guidance

- Confirm at least one test now covers the full declared-local-support flow.
- Confirm no stale library-materialization assumptions remain.
- Confirm workflow/prompt-builder consumers are explicitly exercised after the context changes.

## Activity Log

- 2026-03-09T14:23:30Z - system - lane=planned - Prompt created.
- 2026-03-10T07:23:07Z – unknown – shell_pid=597638 – lane=for_review – Integration gaps closed: stale tests updated, e2e local-support scenario added, workflow/prompt-builder regression coverage added
- 2026-03-10T07:28:38Z – unknown – shell_pid=597638 – lane=done – Moved to done
