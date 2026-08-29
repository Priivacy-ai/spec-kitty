---
work_package_id: WP07
title: TIER-1 override template refresh
dependencies: []
requirement_refs:
- FR-007
planning_base_branch: research/doctrine-wheel-mission-types-public-api
merge_target_branch: research/doctrine-wheel-mission-types-public-api
branch_strategy: Planning artifacts for this mission were generated on research/doctrine-wheel-mission-types-public-api. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into research/doctrine-wheel-mission-types-public-api unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-doctrine-consumer-surface-missions-extraction-01KZ6G6H
base_commit: 11f36ea6b8c8e890ccdb0cf94ee2fa6821d01671
created_at: '2026-08-04T16:59:13.388969+00:00'
subtasks:
- T029
- T030
- T031
phase: Phase 3 - Bundled fixes
history:
- at: '2026-08-04T15:30:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: .kittify/overrides/missions/software-dev/command-templates/
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- .kittify/overrides/missions/software-dev/command-templates/implement.md
- .kittify/overrides/missions/software-dev/command-templates/review.md
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP07 – TIER-1 override template refresh

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

---

## Objectives & Success Criteria

`.kittify/overrides/missions/software-dev/command-templates/implement.md` and `review.md` are tracked TIER-1 template-resolver overrides that still teach the raw `AgentProfileRepository(...)`/`DoctrineService(...)` construction pattern the sole-door mission (PR #3175) just banned, and reference the retired `spec-kitty constitution context` command.

This WP is done when:
- Neither file references raw `AgentProfileRepository`/`DoctrineService` construction.
- Neither file references `constitution context`.
- Each file either matches the current canonical template it overrides, or is deleted if it no longer diverges usefully.

## Context & Constraints

Read `spec.md` (FR-007, SC-004, User Story 4) before starting.

**Verified staleness** (re-confirm against your checkout): `implement.md` (lines 10, 27, 29, 39, 41) and `review.md` (lines 10, 26, 28, 38, 40) both reference `spec-kitty constitution context --action .../--json` and raw construction. Both files were last touched well before the PR #3175 sole-door landing — that landing changed production `src/` construction sites, not these dogfood overrides.

**The canonical pattern to model**: `charter.activation.doctrine_service_builder.build_activation_aware_doctrine_service(repo_root)` — find the current canonical templates these files override and compare.

## Branch Strategy

- **Strategy**: {{branch_strategy}}
- **Planning base branch**: {{planning_base_branch}}
- **Merge target branch**: {{merge_target_branch}}

## Subtasks & Detailed Guidance

### T029 – Refresh `implement.md`

- **Purpose**: Stop teaching the banned pattern.
- **Steps**: Compare against the current canonical `implement.md` template it overrides. Rebase this override onto the canonical construction pattern and command references, or delete it if it no longer diverges usefully from the canonical template.
- **Files**: `.kittify/overrides/missions/software-dev/command-templates/implement.md`.
- **Parallel?**: [P] — independent of T030.

### T030 – Refresh `review.md`

- **Purpose**: Same as T029, for the sibling file.
- **Steps**: Same approach as T029.
- **Files**: `.kittify/overrides/missions/software-dev/command-templates/review.md`.
- **Parallel?**: [P] — independent of T029.

### T031 – Verify

- **Purpose**: Confirm SC-004.
- **Steps**: `grep -n "constitution context\|AgentProfileRepository(\|DoctrineService(" .kittify/overrides/missions/software-dev/command-templates/implement.md .kittify/overrides/missions/software-dev/command-templates/review.md` — expect no match (or the files no longer exist, if deleted).
- **Files**: n/a (verification).
- **Parallel?**: No — final gate.

## Risks & Mitigations

- **Risk**: Patching only the two construction lines without noticing the file is otherwise stale (per the original issue #3182's own framing, this was deliberately not folded into the sole-door landing for exactly this reason). **Mitigation**: do a wholesale comparison against the current canonical template, not a targeted find-and-replace.

## Review Guidance

- Confirm the refreshed files (or their deletion) are consistent with the current canonical templates, not just patched in isolation.

## Activity Log

> **CRITICAL**: Activity log entries MUST be in chronological order (oldest first, newest last). Append new entries at the end.

- 2026-08-04T15:30:00Z – system – Prompt created.
