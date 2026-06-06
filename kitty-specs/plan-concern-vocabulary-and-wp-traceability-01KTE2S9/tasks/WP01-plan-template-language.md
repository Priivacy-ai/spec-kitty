---
work_package_id: WP01
title: Plan Template Language
dependencies: []
requirement_refs:
- FR-001
- FR-002
- FR-003
- FR-004
- FR-005
tracker_refs: []
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-plan-concern-vocabulary-and-wp-traceability-01KTE2S9
base_commit: 36504454c9a0fb0686346265cf8dfa1d764ea53a
created_at: '2026-06-06T11:17:11.983763+00:00'
subtasks:
- T001
- T002
- T003
- T004
agent: "claude:sonnet-4-6:implementer:implementer"
shell_pid: "78252"
history:
- date: '2026-06-06'
  event: created
agent_profile: implementer-ivan
authoritative_surface: src/doctrine/missions/
execution_mode: code_change
owned_files:
- src/doctrine/missions/software-dev/templates/plan-template.md
- src/doctrine/missions/mission-steps/software-dev/plan/prompt.md
- src/doctrine/missions/mission-steps/software-dev/tasks/prompt.md
- src/doctrine/missions/built_in_step_contracts/tasks.step-contract.yaml
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your agent profile:

```
/ad-hoc-profile-load implementer-ivan
```

This configures your working style, doctrine references, and capability constraints for this work package.

---

## Objective

Replace the pseudo-WP vocabulary in spec-kitty's plan-phase templates and prompts. Remove "Parallel Work Analysis", "Work Distribution", and "Agent Assignments" sections from `plan-template.md`. Introduce an "Implementation Concern Map" section with IC-## placeholder stubs. Update three prompt files to use the new concern vocabulary consistently.

**This WP is text-only — no Python changes.**

---

## Context

The plan template currently has a `## Parallel Work Analysis` section (line ~111 in `src/doctrine/missions/software-dev/templates/plan-template.md`) with subsections `### Dependency Graph`, `### Work Distribution`, and `- **Agent assignments**`. This language reads like WP-level decomposition and causes agents and reviewers to treat plan slices as pseudo-WPs.

The fix introduces "implementation concern" as the plan-phase vocabulary, with IC-## identifiers (IC-01, IC-02…). An implementation concern captures architectural intent (purpose, affected surfaces, sequencing, risks) but is explicitly NOT an executable unit.

The canonical template is `src/doctrine/missions/software-dev/templates/plan-template.md`. **Do not edit** `src/specify_cli/missions/software-dev/templates/plan-template.md` — that copy is stranded with no live runtime consumer (issue #1731).

---

## Subtask T001 — Replace Parallel Work Analysis in plan-template.md

**File**: `src/doctrine/missions/software-dev/templates/plan-template.md`

**Purpose**: Replace the pseudo-WP section with an Implementation Concern Map that uses IC-## stub entries.

**What to find**: The existing section starting with `## Parallel Work Analysis` and its subsections (`### Dependency Graph`, `### Work Distribution`, agent assignments bullet). Read the file first to find exact line numbers and surrounding context.

**Replace with**:

```markdown
## Implementation Concern Map

*Include this section when the mission has multiple distinct architectural areas that inform how tasks are decomposed.*

> **Note**: Implementation concerns are NOT work packages and are NOT executable units.
> `/spec-kitty.tasks` translates these into executable WPs — one concern may become
> multiple WPs; multiple small concerns may merge into one WP. Do not label concerns
> with WP-style IDs or sequencing language.

### IC-01 — [Name]

- **Purpose**: [One sentence: what this concern addresses and why it matters]
- **Relevant requirements**: [FR-### refs from spec.md]
- **Affected surfaces**: [File paths or module names this concern touches]
- **Sequencing/depends-on**: [IC-## IDs this concern must follow, or "none"]
- **Risks**: [Key coordination notes or implementation risks]

### IC-02 — [Name]

- **Purpose**: [One sentence]
- **Relevant requirements**: [FR-### refs]
- **Affected surfaces**: [Paths/modules]
- **Sequencing/depends-on**: [IC-## or "none"]
- **Risks**: [Notes]
```

**Also update** the inline comment in the Technical Context section that says "If multiple developers/agents will work on this mission, add a 'Parallel Work Organization' section below showing the dependency graph and agent assignments." Change it to:

```
If multiple developers/agents will work on this mission, add an "Implementation
Concern Map" section below to decompose architectural intent into IC-## concerns
before generating tasks.
```

**Validation**:
- [ ] `rg "Parallel Work Analysis" src/doctrine/missions/software-dev/templates/` returns no hits
- [ ] `rg "Work Distribution" src/doctrine/missions/software-dev/templates/` returns no hits
- [ ] `rg "Agent assignments" src/doctrine/missions/software-dev/templates/` returns no hits
- [ ] `## Implementation Concern Map` is present with IC-01, IC-02 stubs
- [ ] The "Note" block explicitly states concerns are not WPs

---

## Subtask T002 — Update plan/prompt.md stop-point language

**File**: `src/doctrine/missions/mission-steps/software-dev/plan/prompt.md`

**Purpose**: Update the plan prompt so its stop-point and report language refers to implementation concerns rather than implying WPs are directly produced by the plan phase.

**Read the file first** to find the exact lines before editing.

**Find and update** (search for these phrases):

1. Any text that says "/spec-kitty.tasks will 'generate work packages'" — change to:
   > "`/spec-kitty.tasks` translates implementation concerns from `plan.md` into executable work packages."

2. The MANDATORY STOP POINT section — verify it does not use WP-like language for what the plan produces. The stop point should describe what the plan produced (concerns map, architecture, research) not a WP breakdown.

3. In the final report guidance — if it lists "work package slices" or similar, change to "implementation concerns (IC-## entries)".

**What NOT to change**: The stop-point itself (the plan must still stop before task generation) — only the vocabulary describing what `/spec-kitty.tasks` does next.

**Validation**:
- [ ] The stop-point and report language does not say the plan phase produces work packages
- [ ] The language explicitly says tasks translates concerns into WPs

---

## Subtask T003 — Update tasks/prompt.md description header

**File**: `src/doctrine/missions/mission-steps/software-dev/tasks/prompt.md`

**Purpose**: The frontmatter description says "Break a plan into work packages". Update it to use concern vocabulary.

**Find**:
```yaml
description: Break a plan into work packages
```

**Replace with**:
```yaml
description: Translate implementation concerns into work packages
```

**Also scan** the first paragraph of the prompt body for any "break the plan into WPs" phrasing and update similarly to "translate implementation concerns from plan.md into executable work packages".

**Validation**:
- [ ] `rg "Break a plan into work packages" src/doctrine/missions/mission-steps/software-dev/tasks/` returns no hits

---

## Subtask T004 — Update tasks.step-contract.yaml outline step description

**File**: `src/doctrine/missions/built_in_step_contracts/tasks.step-contract.yaml`

**Purpose**: The `outline` step currently says: `description: Produce tasks.md — the work-package outline derived from the plan`. This implies WPs are directly derived from plan slices.

**Find**:
```yaml
  - id: outline
    description: Produce tasks.md — the work-package outline derived from the plan
```

**Replace with**:
```yaml
  - id: outline
    description: Produce tasks.md — work packages translated from implementation concerns in the plan
```

**Validation**:
- [ ] `rg "work-package outline derived from the plan" src/doctrine/` returns no hits

---

## Branch Strategy

Planning branch: `main`
Merge target: `main`
Execution worktree: allocated by `lanes.json` after `finalize-tasks`

Implement using: `spec-kitty agent action implement WP01 --agent claude`

---

## Definition of Done

- [ ] All four files edited
- [ ] Stale-phrase check passes: `rg "Parallel Work Analysis|Work Distribution|work-package outline derived from the plan|Break a plan into work packages" src/doctrine/missions/` returns 0 hits
- [ ] No Python files modified
- [ ] `git diff --stat` shows only the four expected doctrine files changed

---

## Reviewer Guidance

This WP is text-only. Review for:
1. The IC-## stub structure in plan-template.md matches the fields specified in the data-model (concern-id, name, purpose, relevant-requirements, affected-surfaces, sequencing/depends-on, risks)
2. The "Note" block clearly states concerns are not WPs and not executable
3. No residual "Parallel Work Analysis" or "Work Distribution" language remains
4. The stop-point language in plan/prompt.md is updated but the stop-point itself is preserved

## Activity Log

- 2026-06-06T11:17:13Z – claude:sonnet-4-6:implementer:implementer – shell_pid=78252 – Assigned agent via action command
