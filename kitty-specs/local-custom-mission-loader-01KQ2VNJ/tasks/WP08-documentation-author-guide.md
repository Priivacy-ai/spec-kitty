---
work_package_id: WP08
title: 'Documentation: Custom Mission Author Guide + Error Code Table'
dependencies:
- WP05
requirement_refs:
- C-005
- NFR-002
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T039
- T040
- T041
phase: Phase 5 - Polish
assignee: ''
agent: "claude:sonnet:curator-carla:implementer"
shell_pid: "55890"
history:
- at: '2026-04-25T17:54:43Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: curator-carla
authoritative_surface: docs/reference/missions.md
execution_mode: code_change
owned_files:
- docs/reference/missions.md
role: implementer
tags: []
---

# Work Package Prompt: WP08 – Documentation: Custom Mission Author Guide + Error Code Table

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load curator-carla
```

## Branch Strategy

- **Planning/base branch at prompt creation**: `main`
- **Final merge target for completed work**: `main`
- **Actual execution workspace is resolved later** by `/spec-kitty.implement`. Trust the printed lane workspace.

## Objectives & Success Criteria

Update `docs/reference/missions.md` with reference material for custom mission authors: YAML shape, retrospective marker rule, profile / contract binding rules, and the closed enumeration of validation error / warning codes.

Success criteria:
1. Reader can author a valid custom mission YAML using only `docs/reference/missions.md` as a source.
2. Error code table mirrors `kitty-specs/<mission>/contracts/validation-errors.md` byte-for-byte (mission-review verifies parity).
3. ERP example walkthrough cross-links `kitty-specs/<mission>/quickstart.md` and the example fixture.
4. Markdown linter passes; existing references in the file remain intact.

## Context & Constraints

- WP08 is editorial. No code change.
- `docs/reference/` is reference material; it may overlap with `quickstart.md` but is the canonical source for the closed enums.
- See [research.md](../research.md) §R-008 for envelope shape (reference; not modified here).
- Charter directive DIRECTIVE_010 (Specification Fidelity) requires the docs to match the implemented behavior.

## Subtasks & Detailed Guidance

### Subtask T039 — Author the custom-mission author guide

- **Purpose**: A reader who has never used Spec Kitty before can author a `mission.yaml` from this guide alone.
- **Steps**:
  1. Read existing `docs/reference/missions.md`. Note the section structure and tone.
  2. Add a top-level section `## Authoring Custom Missions` (placement: after the built-in mission reference; before any appendix). Subsections:
     - `### YAML shape` — list the top-level keys (`mission`, `steps`, optional `audit_steps`) and a minimal valid example.
     - `### Step fields` — table covering `id`, `title`, `description`, `agent_profile` (alias `agent-profile`), `contract_ref`, `requires_inputs`, `depends_on`, `raci`, `raci_override_reason`. Mark which are required for which step kind.
     - `### The retrospective marker` — explain `id == "retrospective"` is mandatory on the last step; explain that execution is deferred to a future tranche.
     - `### Profile binding` — explain the `agent_profile` vs `contract_ref` choice; cite [research.md](../research.md) §R-003 for the rationale.
     - `### Reserved keys` — list the four built-in keys; explain they cannot be shadowed; cite §R-002.
     - `### Discovery precedence` — re-state the seven tiers (explicit / env / project_override / project_legacy / user_global / project_config / builtin).
- **Files**: `docs/reference/missions.md`.

### Subtask T040 — Author the closed error code table

- **Purpose**: NFR-002 — operators and tooling rely on a stable, documented enumeration.
- **Steps**:
  1. Add a section `### Validation error codes` immediately after the author-guide subsections.
  2. Mirror the table structure from [contracts/validation-errors.md](../contracts/validation-errors.md): one row per error code, columns "Code | When | Required `details` keys".
  3. Repeat the warning table (`MISSION_KEY_SHADOWED`, `MISSION_PACK_LOAD_FAILED`).
  4. Add a marker comment that links back to the contracts file:
     ```markdown
     <!-- This table mirrors contracts/validation-errors.md in the
     local-custom-mission-loader-01KQ2VNJ mission. Mission-review
     verifies parity. -->
     ```
- **Files**: `docs/reference/missions.md`.
- **Parallel?**: [P].

### Subtask T041 — Add the ERP example walkthrough

- **Purpose**: A short, copy-paste-ready example that exercises every covered branch.
- **Steps**:
  1. Add a section `### Example: ERP integration mission` after the error-code table.
  2. Inline the ERP fixture YAML (or link to `tests/fixtures/missions/erp-integration/mission.yaml` as the canonical copy — single source of truth).
  3. Show the three CLI invocations side by side:
     - `spec-kitty mission run erp-integration --mission erp-q3-rollout` (success, default panel output).
     - `spec-kitty mission run erp-integration --mission erp-q3-rollout --json` (success, JSON envelope).
     - `spec-kitty mission run no-such-key --mission x --json` (error, JSON envelope).
  4. Cross-link `kitty-specs/local-custom-mission-loader-01KQ2VNJ/quickstart.md` for the operator-narrative version.
- **Files**: `docs/reference/missions.md`.
- **Parallel?**: [P].

## Test Strategy (no code tests; documentation review only)

- Run a markdown linter if the project has one (e.g., `markdownlint docs/reference/missions.md`).
- Manually read the updated file end-to-end for tone consistency with surrounding sections.
- Verify all internal links resolve (use `markdown-link-check` or similar if present).

## Risks & Mitigations

- **Risk**: Documentation drifts when error codes evolve in future tranches.
  - **Mitigation**: The marker comment in T040 makes the link explicit; mission-review's documentation-fidelity check catches drift.
- **Risk**: Inlining the ERP YAML duplicates the fixture and creates a copy to maintain.
  - **Mitigation**: Prefer linking to the fixture file; only inline a 5-line minimal example if linking is awkward in the doc system.

## Review Guidance

- Reviewer reads the updated section end-to-end and confirms a non-Spec-Kitty author can produce a working `mission.yaml` from this material alone.
- Reviewer compares the error code table against `contracts/validation-errors.md` line-by-line.
- Reviewer confirms no out-of-scope sections were modified (e.g., the built-in mission reference unchanged).

## Activity Log

- 2026-04-25T17:54:43Z -- system -- Prompt created.
- 2026-04-25T19:26:36Z – claude:sonnet:curator-carla:implementer – shell_pid=55890 – Started implementation via action command
- 2026-04-25T19:29:55Z – claude:sonnet:curator-carla:implementer – shell_pid=55890 – Custom mission author guide + closed error code table + ERP example walkthrough
