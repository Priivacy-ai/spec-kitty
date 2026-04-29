---
work_package_id: WP01
title: Add Shipped Doctrine Artifacts (SPDD/REASONS)
dependencies: []
requirement_refs:
- FR-001
- FR-002
- FR-003
- FR-004
- FR-005
- FR-006
- NFR-003
- NFR-004
- C-003
- C-007
planning_base_branch: doctrine/spdd-reasons-pack
merge_target_branch: doctrine/spdd-reasons-pack
branch_strategy: Planning artifacts for this feature were generated on doctrine/spdd-reasons-pack. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into doctrine/spdd-reasons-pack unless the human explicitly redirects the landing branch.
created_at: '2026-04-29T08:15:46Z'
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
- T007
agent: claude
history:
- date: '2026-04-29'
  author: spec-kitty.tasks
  note: Initial WP generated
agent_profile: curator-carla
authoritative_surface: src/doctrine/
execution_mode: code_change
model: claude-opus-4-7
owned_files:
- src/doctrine/paradigms/shipped/structured-prompt-driven-development.paradigm.yaml
- src/doctrine/tactics/shipped/reasons-canvas-fill.tactic.yaml
- src/doctrine/tactics/shipped/reasons-canvas-review.tactic.yaml
- src/doctrine/styleguides/shipped/reasons-canvas-writing.styleguide.yaml
- src/doctrine/directives/shipped/038-structured-prompt-boundary.directive.yaml
- src/doctrine/templates/fragments/reasons-canvas-template.md
- tests/doctrine/test_spdd_reasons_artifacts.py
role: implementer
tags:
- doctrine
- shipped-artifacts
---

## ⚡ Do This First: Load Agent Profile

Before reading the rest of this WP, load the curator profile so you adopt the right identity and boundaries:

- Run the `/ad-hoc-profile-load` skill with profile `curator-carla` and role `implementer`.
- Profile file: `src/doctrine/agent_profiles/shipped/curator-carla.agent.yaml`.
- After load, restate your identity, governance scope, and boundaries in one short paragraph before continuing.

# WP01 — Add Shipped Doctrine Artifacts (SPDD/REASONS)

## Branch Strategy

- **Planning base branch**: `doctrine/spdd-reasons-pack`
- **Merge target**: `doctrine/spdd-reasons-pack`
- **Execution workspace**: allocated by `lanes.json` at `spec-kitty agent action implement WP01 --agent claude --mission spdd-reasons-doctrine-pack-01KQC4AX`. Do not guess the worktree path.

## Objective

Ship six new doctrine library files so that any project may opt in to SPDD and the REASONS Canvas through charter selection. The artifacts must validate against existing schemas without schema modification, and must be discoverable through `DoctrineService` repositories without service-level changes.

This WP is foundational — WP02, WP03, WP04, WP05, and WP06 depend on it.

## Context

### Spec references
- FR-001..FR-006, NFR-003, NFR-004, C-003, C-007 — see [spec.md](../spec.md).
- Artifact YAML shapes — see [data-model.md](../data-model.md).

### Schema requirements (verified)
| Kind | Path | Required fields |
|---|---|---|
| paradigm | `src/doctrine/schemas/paradigm.schema.yaml` | `schema_version` ("1.0"), `id` (kebab-case), `name`, `summary` |
| tactic | `src/doctrine/schemas/tactic.schema.yaml` | `id` (kebab-case), `schema_version` ("1.0"), `name`, `steps[]` (each requires `title`) |
| styleguide | `src/doctrine/schemas/styleguide.schema.yaml` | `id` (kebab-case), `schema_version` ("1.0"), `title`, `scope` (enum), `principles[]` |
| directive | `src/doctrine/schemas/directive.schema.yaml` | `id` (UPPERCASE: `^[A-Z][A-Z0-9_-]*$`), `schema_version` ("1.0"), `title`, `intent`, `enforcement` (enum). If `lenient-adherence`, `explicit_allowances` array required. |

### Reference example artifacts
Read at least one of each kind before writing yours, to mirror voice and structure:
- `src/doctrine/paradigms/shipped/atomic-design.paradigm.yaml`
- `src/doctrine/tactics/shipped/autonomous-operation-protocol.tactic.yaml`
- `src/doctrine/styleguides/shipped/aggregate-design-rules.styleguide.yaml`
- `src/doctrine/directives/shipped/001-architectural-integrity-standard.directive.yaml`

### Existing test surface (do not modify)
- `tests/doctrine/test_artifact_compliance.py`
- `tests/doctrine/test_directive_consistency.py`
- `tests/doctrine/test_tactic_compliance.py`
- `tests/doctrine/test_artifact_kinds.py`
- `tests/doctrine/test_service.py`
- `tests/doctrine/test_nested_artifact_discovery.py`

These automatically pick up new shipped artifacts from the `shipped/` subdirectories. They MUST pass without modification.

## Subtasks

### T001 — Author paradigm `structured-prompt-driven-development.paradigm.yaml`

**Path**: `src/doctrine/paradigms/shipped/structured-prompt-driven-development.paradigm.yaml`

Required fields: `schema_version: "1.0"`, `id: structured-prompt-driven-development`, `name`, `summary`.

Use the YAML body from [data-model.md §Paradigm](../data-model.md). Include `applicability`, `when_not_to_use`, and `related` sections for richness; only the four required fields are schema-mandatory.

**Validation**:
- `uv run pytest tests/doctrine/test_artifact_compliance.py -q`
- `uv run pytest tests/doctrine/test_artifact_kinds.py -q`

### T002 — Author tactic `reasons-canvas-fill.tactic.yaml`

**Path**: `src/doctrine/tactics/shipped/reasons-canvas-fill.tactic.yaml`

Use the body from [data-model.md §Tactic: reasons-canvas-fill](../data-model.md). Five `steps`, each with `title` and `description`.

**Validation**:
- `uv run pytest tests/doctrine/test_tactic_compliance.py -q`

### T003 — Author tactic `reasons-canvas-review.tactic.yaml`

**Path**: `src/doctrine/tactics/shipped/reasons-canvas-review.tactic.yaml`

Use the body from [data-model.md §Tactic: reasons-canvas-review](../data-model.md). Five steps.

### T004 — Author styleguide `reasons-canvas-writing.styleguide.yaml`

**Path**: `src/doctrine/styleguides/shipped/reasons-canvas-writing.styleguide.yaml`

Use the body from [data-model.md §Styleguide](../data-model.md). `scope: docs`. Six principles.

### T005 — Author directive `038-structured-prompt-boundary.directive.yaml`

**Path**: `src/doctrine/directives/shipped/038-structured-prompt-boundary.directive.yaml`

`id: DIRECTIVE_038` (UPPERCASE). `enforcement: lenient-adherence`. `explicit_allowances` is REQUIRED with this enforcement value — populate the four allowed deviation outcomes from [data-model.md §Directive](../data-model.md):
1. Documented approved deviation captured in `kitty-specs/<mission>/reasons-canvas.md` "Deviations".
2. Glossary update follow-up.
3. Charter follow-up.
4. Follow-up mission.

**Validation**:
- `uv run pytest tests/doctrine/test_directive_consistency.py -q`
- The id `DIRECTIVE_038` must not collide with any existing directive id.

### T006 — Author template fragment `reasons-canvas-template.md`

**Path**: `src/doctrine/templates/fragments/reasons-canvas-template.md` (create the `fragments/` subdirectory if it does not exist).

Use the body from [data-model.md §Template fragment](../data-model.md). Seven sections: Requirements, Entities, Approach, Structure, Operations, Norms, Safeguards. Plus an append-only Deviations section.

### T007 — Add `tests/doctrine/test_spdd_reasons_artifacts.py`

**Path**: `tests/doctrine/test_spdd_reasons_artifacts.py`

Add a small test (≤120 lines) that:
1. Loads each new artifact via the existing `DoctrineService` repository APIs (`paradigms`, `tactics`, `styleguides`, `directives`).
2. Asserts `id`, `schema_version`, and key required fields are present and well-formed.
3. Asserts the artifacts are present in `shipped/` (not project-side).
4. Asserts `DIRECTIVE_038.enforcement == "lenient-adherence"` and `len(explicit_allowances) == 4`.
5. Asserts the template fragment file exists and contains all seven canvas section headers.

Do NOT add CLI/integration tests in this WP — those belong to WP02.

## Definition of Done

- All seven files written.
- `uv run pytest tests/doctrine -q` passes.
- `uv run mypy --strict src/doctrine` clean (if tests touch typed modules).
- No modification to `src/doctrine/schemas/*.schema.yaml`.
- No modification to existing shipped artifacts.

## Reviewer guidance

- Verify schema validation: each artifact must pass without changes to schemas.
- Verify `DIRECTIVE_038.enforcement` is `lenient-adherence` with 4 explicit allowances.
- Verify the canvas template has all 7 sections with the canonical names (Requirements, Entities, Approach, Structure, Operations, Norms, Safeguards).
- Verify no schema or service file was touched.

## Risks

- **Schema field drift**: `data-model.md` examples may include slightly more fields than the schema requires; if any extra field collides with schema validation, drop it and capture the divergence in the WP completion notes.
- **Filename vs id mismatch**: For directive id `DIRECTIVE_038`, the file is named `038-structured-prompt-boundary.directive.yaml`. Both must agree on the `038` and `structured-prompt-boundary` parts.
- **Template fragment placement**: If `src/doctrine/templates/fragments/` does not exist, create it; existing tests do not assert directory layout, but the new file path must match the FR-005 spec exactly.

## Out of scope (for this WP)

- Charter wiring (WP02).
- Skill (WP03).
- Prompt fragment rendering (WP04).
- Review gate (WP05).
- User-facing docs (WP06).
