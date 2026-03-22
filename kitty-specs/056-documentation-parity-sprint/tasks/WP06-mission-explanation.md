---
work_package_id: WP06
title: Mission System Explanation Update
lane: "doing"
dependencies: [WP01]
requirement_refs: [FR-008]
planning_base_branch: fix/skill-audit-and-expansion
merge_target_branch: fix/skill-audit-and-expansion
branch_strategy: Planning artifacts for this feature were generated on fix/skill-audit-and-expansion. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/skill-audit-and-expansion unless the human explicitly redirects the landing branch.
base_branch: 056-documentation-parity-sprint-WP01
base_commit: a3c2fae9fa7c40e05f6ae6b06619574b80195a42
created_at: '2026-03-22T14:58:53.695123+00:00'
subtasks: [T027, T028, T029, T030, T031]
shell_pid: "21973"
agent: "coordinator"
history:
- date: '2026-03-22'
  action: created
  agent: claude
  note: Generated from plan.md Phase 3
---

# WP06: Mission System Explanation Update

## Objective

Expand existing `docs/explanation/mission-system.md` (currently 251 lines) with
content from the `spec-kitty-mission-system` skill. Add the 4 built-in missions
with their step sequences, the hierarchy model, template resolution, and
mission selection guidance.

## Source Material

Read `src/doctrine/skills/spec-kitty-mission-system/SKILL.md` and
`references/mission-comparison-matrix.md`. Read the existing doc at
`docs/explanation/mission-system.md`.

## Implementation

### T027: Expand 4 built-in missions

Add a section covering each mission with its step sequence, required artifacts,
and key guards:

- **software-dev**: discovery → specify → plan → tasks → implement → review → accept
- **research**: scoping → methodology → gathering ⇄ synthesis → output → done
- **plan**: specify → research → plan → review
- **documentation**: discover → audit → design → generate → validate → publish

Include a comparison table similar to the skill's reference matrix.

### T028: Add hierarchy explanation

Explain the mission → feature → WP → workspace hierarchy:
- Mission = reusable workflow blueprint
- Feature = concrete thing being built (kitty-specs/###-feature/)
- Work Package = parallelizable slice (tasks/WP##.md)
- Workspace = isolated git worktree per WP

Include meta.json as the link between feature and mission.

### T029: Add mission selection guide

Add a practical "which mission should I use?" section:

| If you're... | Use |
|---|---|
| Building features, fixing bugs | software-dev |
| Investigating, evaluating options | research |
| Planning architecture, roadmaps | plan |
| Writing docs, filling gaps | documentation |

### T030: Add template resolution

Explain the 5-tier chain at user level:
1. Project override (.kittify/overrides/)
2. Global mission (~/.kittify/missions/)
3. Package default (built-in)

Users only need to know: drop a file in `.kittify/overrides/command-templates/`
to customize a prompt. Skip the legacy and global tiers in user docs.

### T031: Add guard overview

Briefly explain that guards block step transitions (e.g., can't plan without
spec.md). List the most common guards users encounter without the full
primitive syntax.

## Definition of Done

- [ ] Existing doc expanded (not rewritten from scratch)
- [ ] All 4 missions documented with step sequences
- [ ] Hierarchy diagram included
- [ ] Selection guide included
- [ ] Template override instructions included
- [ ] No internal implementation details

## Implementation Command

```bash
spec-kitty implement WP06 --base WP01
```

## Activity Log

- 2026-03-22T14:58:53Z – coordinator – shell_pid=21973 – lane=doing – Assigned agent via workflow command
