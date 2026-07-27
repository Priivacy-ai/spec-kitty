---
work_package_id: WP04
title: Extract Software-Dev Action Doctrine Assets
lane: "done"
dependencies: []
base_branch: feature/agent-profile-implementation
base_commit: 6574829a137207f0939d7cf3ca500471284509c1
created_at: '2026-03-09T16:28:15.045649+00:00'
subtasks:
- T018
- T019
- T020
- T021
- T022
- T023
phase: Phase 2 - Source Doctrine Assets
assignee: claude
agent: claude
shell_pid: '405823'
review_status: "approved"
reviewed_by: "Stijn Dejongh"
history:
- timestamp: '2026-03-09T14:23:30Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
requirement_refs:
- FR-012
- FR-015
---

# Work Package Prompt: WP04 - Extract Software-Dev Action Doctrine Assets

## ⚠️ IMPORTANT: Review Feedback Status

- Check `review_status` first if this WP has already been reviewed once.

---

## Review Feedback

*[Empty initially.]*  

---

## Markdown Formatting

Use fenced code blocks when showing YAML or markdown snippets. Keep path references in backticks.

## Objectives & Success Criteria

- `src/doctrine/missions/software-dev/command-templates/specify.md`, `plan.md`, `implement.md`, and `review.md` keep only workflow/bootstrap content.
- Extracted governance prose is stored in `src/doctrine/missions/software-dev/actions/<action>/guidelines.md`.
- Each action receives a valid `index.yaml` that declares its doctrine scope.
- Source-template structure remains intact so downstream template generation still works.

## Context & Constraints

- Primary source templates:
  - `src/doctrine/missions/software-dev/command-templates/specify.md`
  - `src/doctrine/missions/software-dev/command-templates/plan.md`
  - `src/doctrine/missions/software-dev/command-templates/implement.md`
  - `src/doctrine/missions/software-dev/command-templates/review.md`
- New runtime assets:
  - `src/doctrine/missions/software-dev/actions/specify/`
  - `src/doctrine/missions/software-dev/actions/plan/`
  - `src/doctrine/missions/software-dev/actions/implement/`
  - `src/doctrine/missions/software-dev/actions/review/`
- Supporting references:
  - `kitty-specs/054-constitution-interview-compiler-and-bootstrap/spec.md`
  - `kitty-specs/054-constitution-interview-compiler-and-bootstrap/data-model.md`
  - `kitty-specs/054-constitution-interview-compiler-and-bootstrap/research.md`
- Implementation command: `spec-kitty implement WP04`

## Subtasks & Detailed Guidance

### Subtask T018 - Audit extractable governance prose in the four source templates

- **Purpose**: Separate runtime doctrine content from workflow instructions before editing any template.
- **Steps**:
  1. Read all four software-dev source templates in full.
  2. Mark each section as either:
     - workflow/bootstrap content to preserve
     - governance prose to extract into runtime doctrine assets
  3. Record the heading strings and approximate ranges for removed prose so reviewers can validate the extraction.
  4. Pay special attention to `specify.md` and `plan.md`, which currently contain the densest inline guidance.
- **Files**:
  - the four command templates above
- **Parallel?**: No
- **Notes**: Do not rely only on heading names; check whether a section contains workflow instructions or doctrine prose.

### Subtask T019 - Create `specify` and `plan` action assets

- **Purpose**: Move planning/specification governance prose into retrievable runtime assets.
- **Steps**:
  1. Create `guidelines.md` for `specify` and `plan` with the extracted prose, preserving heading order and wording where that wording matters.
  2. Create matching `index.yaml` files declaring action-scoped directives, tactics, paradigms, styleguides, and toolguides.
  3. Keep the schema aligned with `data-model.md`; avoid inventing a parallel structure.
  4. Use shipped doctrine IDs only in the action indexes.
- **Files**:
  - `src/doctrine/missions/software-dev/actions/specify/guidelines.md`
  - `src/doctrine/missions/software-dev/actions/specify/index.yaml`
  - `src/doctrine/missions/software-dev/actions/plan/guidelines.md`
  - `src/doctrine/missions/software-dev/actions/plan/index.yaml`
- **Parallel?**: Yes
- **Notes**: Use a **hybrid extraction approach**: write a script (or inline migration step in T021) that detects identified prose sections and auto-generates `guidelines.md` stubs, then manually review and refine the stubbed content. Do not hand-author `guidelines.md` from scratch — the stub ensures the heading structure is traceable to its source.

### Subtask T020 - Create `implement` and `review` action assets

- **Purpose**: Complete the action asset set so every bootstrap action has runtime doctrine content.
- **Steps**:
  1. Create `guidelines.md` and `index.yaml` for `implement`.
  2. Create `guidelines.md` and `index.yaml` for `review`.
  3. If one of these templates has little or no prose to extract, create a minimal but valid guideline file rather than faking content.
  4. Keep action indexes intentionally scoped rather than copying every selected artifact into every action.
- **Files**:
  - `src/doctrine/missions/software-dev/actions/implement/*`
  - `src/doctrine/missions/software-dev/actions/review/*`
- **Parallel?**: Yes
- **Notes**: Review is especially sensitive to scope creep; avoid stuffing implementation-only doctrine into the review action index.

### Subtask T021 - Strip inline prose from the source templates

- **Purpose**: Make runtime doctrine retrieval authoritative instead of embedded template text.
- **Steps**:
  1. Remove only the sections identified as extractable governance prose.
  2. Preserve:
     - frontmatter
     - `## Constitution Context Bootstrap (required)` sections
     - `$ARGUMENTS` blocks
     - all workflow and stop-point instructions
  3. Re-read each edited template after the change to confirm the command still makes sense standalone.
- **Files**:
  - the four software-dev source templates
- **Parallel?**: No
- **Notes**: The output should look intentionally slimmed, not accidentally truncated.

### Subtask T022 - Validate doctrine IDs in action indexes

- **Purpose**: Prevent the new action scope declarations from referencing nonexistent shipped artifacts.
- **Steps**:
  1. Cross-check each `index.yaml` entry against shipped doctrine assets.
  2. Prefer a small, defensible action scope over exhaustive indexing.
  3. Keep the four action indexes internally consistent so context retrieval semantics stay predictable.
  4. If a template’s extracted prose implies a doctrine concept that does not have a shipped ID yet, capture that through `guidelines.md`, not by inventing a fake index ID.
- **Files**:
  - the four `index.yaml` files
  - `src/doctrine/directives/shipped/`
  - other shipped doctrine roots as needed
- **Parallel?**: No
- **Notes**: Invalid IDs here will surface later as runtime failures; catch them at authoring time.

### Subtask T023 - Add source-template and action-asset tests

- **Purpose**: Lock the source-asset contract before migration and runtime retrieval depend on it.
- **Steps**:
  1. Add tests or golden assertions verifying:
     - action asset files exist
     - source templates still include bootstrap blocks
     - targeted inline governance headings are absent from source templates
  2. Keep the assertions specific to software-dev templates only.
  3. Avoid brittle snapshot tests that would make minor wording updates expensive unless the repo already uses that pattern here.
- **Files**:
  - tests in the doctrine/specify_cli asset suites
- **Parallel?**: No
- **Notes**: These tests should fail clearly when someone reintroduces inline prose into source templates later.

## Test Strategy

- Run the new or updated template/asset-focused tests.
- If no dedicated asset suite exists yet, add one under `tests/specify_cli/` or the closest doctrine-facing test module and run it directly.

## Risks & Mitigations

- It is easy to remove too much from `plan.md` or `implement.md`. Reviewers should compare structure, not just pass/fail grep checks.
- Action indexes can become arbitrary if they are not tied back to the extracted guidance. Keep the scope intentionally justified.

## Review Guidance

- Diff the before/after template structure to confirm the workflows still read coherently.
- Confirm each action asset directory contains both `guidelines.md` and `index.yaml`.
- Confirm all action-index IDs resolve to real shipped doctrine artifacts.

## Activity Log

- 2026-03-09T14:23:30Z - system - lane=planned - Prompt created.
- 2026-03-09T16:38:37Z – claude – shell_pid=405823 – lane=for_review – Governance prose extracted to actions/, 8 index.yaml files, 2 templates slimmed, 53 new tests
- 2026-03-09T16:51:47Z – claude – shell_pid=405823 – lane=done – Reviewed and approved. .merged-software-dev/ cleaned. Merged into feature branch.
