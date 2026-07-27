---
work_package_id: WP05
title: Implement Action-Scoped Iterative Context Retrieval
lane: "done"
dependencies:
- WP02
- WP04
base_branch: feature/agent-profile-implementation
base_commit: f0f7049609b6883422af2e6910d5a56524797ac2
created_at: '2026-03-09T16:54:06.119544+00:00'
subtasks:
- T024
- T025
- T026
- T027
- T028
- T029
phase: Phase 2 - Runtime Context
assignee: ''
agent: claude
shell_pid: '527528'
review_status: "approved"
reviewed_by: "Stijn Dejongh"
history:
- timestamp: '2026-03-09T14:23:30Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
requirement_refs:
- FR-006
- FR-007
- FR-013
- FR-014
- FR-015
- FR-016
- NFR-002
---

# Work Package Prompt: WP05 - Implement Action-Scoped Iterative Context Retrieval

## ⚠️ IMPORTANT: Review Feedback Status

- If review feedback exists, address it before treating this WP as complete.

---

## Review Feedback

*[Empty initially.]*  

---

## Markdown Formatting

Use fenced code blocks when documenting YAML, JSON, or CLI examples.

## Objectives & Success Criteria

- `constitution context` uses action indexes and selected references to scope what it returns.
- First bootstrap call for an action defaults to depth 2; later calls default to compact depth 1; explicit `--depth` wins.
- `context --json` returns both `context` and `text`, plus `mode` and `depth`.
- Local support files participate only when their action scope matches the requested action or they are global.
- Missing or corrupted constitution artifacts degrade gracefully instead of crashing the command or downstream workflow consumers.

## Context & Constraints

- Primary runtime files:
  - `src/specify_cli/constitution/context.py`
  - `src/specify_cli/cli/commands/constitution.py`
  - `src/specify_cli/cli/commands/agent/workflow.py`
  - `src/specify_cli/next/prompt_builder.py`
- Supporting runtime/data files:
  - `src/doctrine/missions/__init__.py`
  - new `src/doctrine/missions/action_index.py`
  - `src/doctrine/service.py`
  - `.kittify/constitution/context-state.json`
- Planning references:
  - `kitty-specs/054-constitution-interview-compiler-and-bootstrap/data-model.md`
  - `kitty-specs/054-constitution-interview-compiler-and-bootstrap/quickstart.md`
  - `kitty-specs/054-constitution-interview-compiler-and-bootstrap/contracts/constitution-cli-contract.md`
- Implementation command: `spec-kitty implement WP05 --base WP04`

## Subtasks & Detailed Guidance

### Subtask T024 - Add `ActionIndex` loading and exports under `src/doctrine/missions/`

- **Purpose**: Give runtime code a typed way to read `actions/<action>/index.yaml`.
- **Steps**:
  1. Create a small module for `ActionIndex` and a loader that reads `src/doctrine/missions/<mission>/actions/<action>/index.yaml`.
  2. Define an empty, valid fallback shape when an action index is missing so runtime degradation stays graceful.
  3. Export the new types/helpers from `src/doctrine/missions/__init__.py` for clean downstream imports.
- **Files**:
  - `src/doctrine/missions/action_index.py`
  - `src/doctrine/missions/__init__.py`
- **Parallel?**: Yes
- **Notes**: Keep this module narrow; it is a loader/shape definition, not a second doctrine service.

### Subtask T025 - Rework bootstrap-state and depth handling in `build_constitution_context()`

- **Purpose**: Replace the current summary-only bootstrap logic with explicit depth-aware behavior.
- **Steps**:
  1. Read the current `build_constitution_context()` implementation and its helper functions.
  2. Add `depth` handling so:
     - omitted depth + first load -> depth 2 / bootstrap
     - omitted depth + later load -> depth 1 / compact
     - explicit depth -> exact requested depth
  3. Preserve `mark_loaded` semantics and keep state persisted in `.kittify/constitution/context-state.json`.
  4. Treat missing or malformed constitution artifacts as graceful-degradation cases, not hard crashes.
- **Files**:
  - `src/specify_cli/constitution/context.py`
- **Parallel?**: No
- **Notes**: This task owns mode selection logic. Downstream callers should not guess the default depth themselves.

### Subtask T026 - Fetch action-scoped doctrine through the correct repositories

- **Purpose**: Ensure each depth level is built from the right doctrine source and the right action scope.
- **Steps**:
  1. Intersect the action index with selected project references for each artifact type.
  2. Fetch directives, tactics, styleguides, toolguides, and any other supported artifact families through the corresponding `DoctrineService` repository.
  3. Return only title/ID summaries at depth 1, full directive/tactic/action-guideline content at depth 2, and add styleguide/toolguide detail at depth 3.
  4. Keep `implement`-only doctrine out of `specify` or `plan` contexts and vice versa.
- **Files**:
  - `src/specify_cli/constitution/context.py`
  - `src/doctrine/service.py` only if additional typed access helpers are genuinely required
- **Parallel?**: No
- **Notes**: Avoid generic file-walking shortcuts; the feature explicitly wants per-type repository ownership.

### Subtask T027 - Include action-scoped local support references safely

- **Purpose**: Make local support declarations usable at runtime without undermining shipped doctrine authority.
- **Steps**:
  1. Read local support references from `references.yaml`.
  2. Include a local support file only when its `action` matches the requested action or it is global.
  3. Surface local support content additively alongside shipped doctrine, preserving any warning metadata.
  4. Do not let local support content replace or suppress shipped doctrine content when both target the same concept.
- **Files**:
  - `src/specify_cli/constitution/context.py`
- **Parallel?**: No
- **Notes**: Keep the runtime behavior aligned with the additive conflict semantics introduced in WP02.

### Subtask T028 - Update the context CLI and downstream consumers

- **Purpose**: Expose the new runtime contract cleanly and keep prompt-building consumers compatible.
- **Steps**:
  1. Add `--depth` to the `constitution context` command.
  2. Update JSON output to include `context`, `text`, `mode`, and `depth`.
  3. Review `src/specify_cli/cli/commands/agent/workflow.py` and `src/specify_cli/next/prompt_builder.py` so they still consume the result correctly.
  4. Keep the text payload stable enough that existing callers can use `text` without learning a new rendering surface.
- **Files**:
  - `src/specify_cli/cli/commands/constitution.py`
  - `src/specify_cli/cli/commands/agent/workflow.py`
  - `src/specify_cli/next/prompt_builder.py`
- **Parallel?**: No
- **Notes**: This WP owns the context JSON compatibility contract. Avoid fragmenting it across later cleanups.

### Subtask T029 - Add context and consumer regression tests

- **Purpose**: Lock in the runtime behavior across CLI and consumer entry points.
- **Steps**:
  1. Expand `tests/specify_cli/constitution/test_context.py` to cover:
     - first vs later load
     - explicit `--depth`
     - action isolation
     - missing/corrupt files
     - scoped local support files
  2. Add CLI-level tests for the new JSON shape.
  3. Add regression coverage for workflow/prompt-builder call sites if the existing suites do not already cover the contract.
- **Files**:
  - `tests/specify_cli/constitution/test_context.py`
  - `tests/specify_cli/cli/commands/test_constitution_cli.py`
  - other consumer tests as needed
- **Parallel?**: No
- **Notes**: Make the tests specific about `context == text` and the returned `depth` value.

## Test Strategy

- Run:
  - `pytest -q tests/specify_cli/constitution/test_context.py`
  - `pytest -q tests/specify_cli/cli/commands/test_constitution_cli.py`
  - any targeted workflow/prompt-builder tests touched by the implementation

## Risks & Mitigations

- This WP touches a shared runtime surface used by both humans and agent automation. Keep the rendering stable and test the consumer entry points, not just the helper function.
- State handling can drift if explicit depth requests mutate first-load state incorrectly. Keep “state decides default only” as an explicit invariant.

## Review Guidance

- Confirm `context --json` now includes `context`, `text`, `mode`, and `depth`.
- Confirm first-load depth behavior changes only when `--depth` is omitted.
- Confirm action-scoped local support files do not bleed into unrelated actions.

## Activity Log

- 2026-03-09T14:23:30Z - system - lane=planned - Prompt created.
- 2026-03-10T04:01:59Z – claude – shell_pid=518388 – lane=doing – Assigned agent via workflow command
- 2026-03-10T04:13:59Z – claude – shell_pid=518388 – lane=for_review – Ready for review: action-scoped context retrieval with depth parameter, ActionIndex module, local support filtering, --depth CLI option, and JSON context/text/depth fields. All 38 tests pass, ruff clean, mypy clean.
- 2026-03-10T04:33:41Z – claude – shell_pid=527528 – lane=doing – Started review via workflow command
- 2026-03-10T04:35:05Z – claude – shell_pid=527528 – lane=done – Review passed: all success criteria met — depth parameter, action-scoped doctrine via repositories, local support action filtering, context/text/depth JSON fields, graceful degradation, 38 tests all green. | Done override: WP05 branch reviewed and approved; merge to feature/agent-profile-implementation pending merge workflow
