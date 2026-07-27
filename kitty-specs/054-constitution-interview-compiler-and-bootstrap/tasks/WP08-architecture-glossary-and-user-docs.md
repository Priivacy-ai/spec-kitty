---
work_package_id: WP08
title: Architectural Review, Glossary, and User Docs
lane: "done"
dependencies:
- WP05
- WP06
- WP07
base_branch: feature/agent-profile-implementation
base_commit: 71ca89bda487a8c3e4dd3e5374698f5bda9c47a8
created_at: '2026-03-10T07:28:46.345632+00:00'
subtasks:
- T039
- T040
- T041
- T042
phase: Phase 4 - Review and Documentation Closeout
assignee: ''
agent: ''
shell_pid: '616235'
review_status: "approved"
reviewed_by: "Stijn Dejongh"
history:
- timestamp: '2026-03-09T14:23:30Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
requirement_refs:
- FR-013
- FR-016
- FR-017
- FR-018
- NFR-001
---

# Work Package Prompt: WP08 - Architectural Review, Glossary, and User Docs

## ⚠️ IMPORTANT: Review Feedback Status

- This package is reviewer-oriented. If it returns from review, treat the feedback as the worklist to close before approval.

---

## Review Feedback

*[Empty initially.]*  

---

## Markdown Formatting

Keep terminology, commands, and file paths in backticks. Use fenced code blocks for CLI or YAML examples.

## Objectives & Success Criteria

- The implemented feature is checked against the architecture and planning contract from a reviewer-role perspective.
- Canonical terminology is consistent across the feature spec, plan, tasks, runtime docs, and user-facing examples.
- User documentation explains the strict `interview -> generate -> context` flow, explicit local support file declarations, additive overlap warnings, shipped-only validation, and the absence of generated `library/`.
- Documentation and examples stop referring to removed or legacy surfaces such as `agents.yaml`, generated library docs, or old JSON payload shapes.

## Context & Constraints

- Preferred implementer profile: a reviewer-oriented agent or contributor. Treat this as an architectural review and documentation package, not feature expansion.
- Primary references:
  - `kitty-specs/054-constitution-interview-compiler-and-bootstrap/spec.md`
  - `kitty-specs/054-constitution-interview-compiler-and-bootstrap/plan.md`
  - `kitty-specs/054-constitution-interview-compiler-and-bootstrap/research.md`
  - `kitty-specs/054-constitution-interview-compiler-and-bootstrap/data-model.md`
  - `kitty-specs/054-constitution-interview-compiler-and-bootstrap/quickstart.md`
  - `kitty-specs/054-constitution-interview-compiler-and-bootstrap/tasks.md`
- Likely user-facing docs to inspect:
  - `README.md`
  - doctrine/constitution command template docs
  - any CLI docs or examples touched by feature 054 implementation
- Implementation command: `spec-kitty implement WP08 --base WP07`

## Subtasks & Detailed Guidance

### Subtask T039 - Perform an architectural review against the feature contract

- **Purpose**: Confirm the implemented system matches the intended boundaries before the documentation is updated to describe it.
- **Steps**:
  1. Compare the implementation against `spec.md`, `plan.md`, `research.md`, and `data-model.md`.
  2. Review the core runtime surfaces:
     - `src/specify_cli/cli/commands/constitution.py`
     - `src/specify_cli/constitution/compiler.py`
     - `src/specify_cli/constitution/context.py`
     - `src/specify_cli/constitution/catalog.py`
     - `src/specify_cli/constitution/resolver.py`
     - migration files relevant to generated prompts
  3. Capture any mismatches or notable tradeoffs directly in the WP activity log or review notes, then resolve them or document them clearly before closing the package.
  4. Keep the review grounded in architecture and UX contracts, not coding style preferences.
- **Files**:
  - planning artifacts
  - implemented runtime files for feature 054
- **Parallel?**: No
- **Notes**: This is the package’s gating step. Do not update docs first and discover design mismatches later.

### Subtask T040 - Normalize glossary and canonical terminology

- **Purpose**: Make the feature teachable and reviewable by using one vocabulary consistently.
- **Steps**:
  1. Audit the feature artifacts and touched docs for mixed terms such as:
     - override vs support file
     - bootstrap/full/compact context
     - doctrine catalog vs shipped doctrine
     - generated files vs `library_files`
  2. Choose and apply the canonical wording already implied by the spec and data model.
  3. Update glossary sections or introduce a compact glossary note where the repo already documents constitution terminology.
  4. Avoid rewriting unrelated documentation; keep the edit set focused on terms this feature changes materially.
- **Files**:
  - `kitty-specs/054-constitution-interview-compiler-and-bootstrap/*.md`
  - user-facing docs touched by feature 054
- **Parallel?**: Yes
- **Notes**: `local support file` should remain the preferred term unless a narrower concept is truly intended.

### Subtask T041 - Update user-facing documentation for the constitution workflow

- **Purpose**: Make the new runtime behavior discoverable to maintainers and operators without requiring spec spelunking.
- **Steps**:
  1. Update the relevant user docs to describe:
     - the strict interview prerequisite
     - explicit local support declarations in `answers.yaml` / `references.yaml`
     - additive conflict warnings when local files overlap shipped doctrine
     - shipped-only validation by default
     - first-load bootstrap vs later compact context behavior
  2. Include at least one concise example command flow and one local support declaration example if the docs currently lack them.
  3. Make sure the docs do not imply that local files override shipped doctrine.
- **Files**:
  - `README.md`
  - any constitution workflow docs touched by feature 054
- **Parallel?**: Yes
- **Notes**: Write for users of the CLI, not for implementers reading the plan.

### Subtask T042 - Refresh documentation and regression checks for stale examples

- **Purpose**: Prevent the docs from silently drifting back to removed surfaces.
- **Steps**:
  1. Search for stale references to:
     - generated `.kittify/constitution/library/`
     - `agents.yaml` as constitution output
     - legacy JSON payload keys
  2. Update or remove those examples where they overlap this feature’s scope.
  3. Add a lightweight regression check or focused test if the repo already validates user documentation/examples mechanically.
  4. If no automated doc check exists, make the changed examples precise enough for manual reviewer verification.
- **Files**:
  - docs and tests touched by the updated examples
- **Parallel?**: No
- **Notes**: This is the final coherence sweep; do not leave the repo teaching the old behavior.

## Test Strategy

- Re-run the focused tests most likely to fail when documentation examples or terminology drift:
  - constitution CLI tests
  - context tests
  - any documentation/example validation checks that already exist in the repo
- Manually verify at least one documented command sequence against the implemented CLI behavior.

## Risks & Mitigations

- Documentation packages often become vague. Keep every updated example aligned to real file names, real commands, and the final JSON contract.
- Architectural review can balloon into redesign. Limit this package to review findings, terminology alignment, and user-documentation accuracy.

## Review Guidance

- Confirm the package was handled from a reviewer-role mindset rather than as speculative redesign.
- Confirm glossary changes reduce ambiguity instead of introducing new synonyms.
- Confirm user docs explain additive local support behavior and shipped-only validation accurately.

## Activity Log

- 2026-03-09T14:23:30Z - system - lane=planned - Prompt created.
- 2026-03-10T07:35:57Z – unknown – shell_pid=616235 – lane=for_review – Moved to for_review
- 2026-03-10T07:38:45Z – unknown – shell_pid=616235 – lane=done – Moved to done
