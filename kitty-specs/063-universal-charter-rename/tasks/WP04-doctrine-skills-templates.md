---
work_package_id: WP04
title: Doctrine, Skills, Templates & Mission Artifacts
dependencies: []
requirement_refs:
- FR-004
- FR-005
- FR-012
planning_base_branch: main
merge_target_branch: main
branch_strategy: 'Planning branch: main. Merge target: main. No dependencies — can start immediately.'
subtasks: [T018, T019, T020, T021, T022, T023, T024]
history:
- date: '2026-04-04'
  action: created
  by: spec-kitty.tasks
authoritative_surface: src/doctrine/
execution_mode: code_change
owned_files: [src/doctrine/**, src/specify_cli/missions/**]
---

# WP04: Doctrine, Skills, Templates & Mission Artifacts

## Objective

Rename the doctrine defaults directory, skill package, command template, and procedure file. Update all 9 doctrine mission artifact files that embed "constitution" references.

## Context

Doctrine is the governance framework layer. It ships skills (agent capabilities), mission templates (prompt blueprints), action guidelines (per-action rules), and procedures (migration guides). All reference "constitution" which must become "charter".

## Implementation Command

```bash
spec-kitty implement WP04
```

## Subtask T018: Rename src/doctrine/constitution/ → src/doctrine/charter/

**Purpose**: Rename the doctrine defaults directory.

**Steps**:
1. `git mv src/doctrine/constitution/ src/doctrine/charter/`
2. In `src/doctrine/charter/defaults.yaml`:
   - Replace all "constitution" references (e.g., `constitution.interview.apply_answer_overrides` → `charter.interview.apply_answer_overrides`)

**Validation**: `rg -i constitution src/doctrine/charter/` returns zero matches.

## Subtask T019: Rename skill directory + update content

**Purpose**: Rename the governance skill from constitution-doctrine to charter-doctrine.

**Steps**:
1. `git mv src/doctrine/skills/spec-kitty-constitution-doctrine/ src/doctrine/skills/spec-kitty-charter-doctrine/`
2. Rename reference file: `git mv src/doctrine/skills/spec-kitty-charter-doctrine/references/constitution-command-map.md src/doctrine/skills/spec-kitty-charter-doctrine/references/charter-command-map.md`
3. In `SKILL.md`:
   - Update `name: spec-kitty-constitution-doctrine` → `name: spec-kitty-charter-doctrine`
   - Update description: all "constitution" → "charter"
   - Update triggers: "interview for constitution" → "interview for charter", "generate constitution" → "generate charter", "sync constitution" → "sync charter", "constitution status" → "charter status"
   - Update heading: `# spec-kitty-constitution-doctrine` → `# spec-kitty-charter-doctrine`
   - Update all body text
4. In `references/charter-command-map.md`:
   - Replace all "constitution" references in command names, descriptions, examples
5. In `references/doctrine-artifact-structure.md`:
   - Replace all "constitution" references

**Validation**: `rg -i constitution src/doctrine/skills/spec-kitty-charter-doctrine/` returns zero matches.

## Subtask T020: Rename command template file + update content

**Purpose**: Rename the slash command template.

**Steps**:
1. `git mv src/specify_cli/missions/software-dev/command-templates/constitution.md src/specify_cli/missions/software-dev/command-templates/charter.md`
2. In `charter.md`:
   - Replace all "constitution" references: command names, paths, descriptions
   - Update `spec-kitty constitution context` → `spec-kitty charter context`
   - Update `Constitution Context Bootstrap` → `Charter Context Bootstrap`
   - Update `.kittify/constitution/constitution.md` → `.kittify/charter/charter.md`
   - Update all governance-related terminology

**Validation**: `rg -i constitution src/specify_cli/missions/software-dev/command-templates/charter.md` returns zero matches.

## Subtask T021: Rename doctrine procedure file

**Purpose**: Rename the migration procedure document.

**Steps**:
1. `git mv src/doctrine/procedures/shipped/migrate-project-guidance-to-spec-kitty-constitution.procedure.yaml src/doctrine/procedures/shipped/migrate-project-guidance-to-spec-kitty-charter.procedure.yaml`
2. In the renamed file: replace all "constitution" references in the procedure content.

**Validation**: `rg -i constitution` on the renamed file returns zero matches.

## Subtask T022: Update software-dev mission templates

**Purpose**: Update plan and task templates that reference constitution.

**Steps**:
1. In `src/doctrine/missions/software-dev/templates/plan-template.md`:
   - `## Constitution Check` → `## Charter Check`
   - `[Gates determined based on constitution file]` → `[Gates determined based on charter file]`
2. In `src/doctrine/missions/software-dev/templates/task-prompt-template.md`:
   - `.kittify/constitution/constitution.md` → `.kittify/charter/charter.md`

**Validation**: `rg -i constitution` on both files returns zero matches.

## Subtask T023: Update software-dev action guidelines (4 files)

**Purpose**: Update the per-action governance guidelines.

**Steps**:
1. In `src/doctrine/missions/software-dev/actions/specify/guidelines.md`:
   - "constitution context bootstrap" → "charter context bootstrap"
2. In `src/doctrine/missions/software-dev/actions/plan/guidelines.md`:
   - "Constitution Compliance" → "Charter Compliance"
   - "If a constitution exists" → "If a charter exists"
   - "If no constitution exists" → "If no charter exists"
   - "Constitution Check" → "Charter Check"
   - "constitution context bootstrap" → "charter context bootstrap"
3. In `src/doctrine/missions/software-dev/actions/implement/guidelines.md`:
   - "constitution context bootstrap" → "charter context bootstrap"
4. In `src/doctrine/missions/software-dev/actions/review/guidelines.md`:
   - "constitution context bootstrap" → "charter context bootstrap"

**Validation**: `rg -i constitution src/doctrine/missions/software-dev/actions/` returns zero matches.

## Subtask T024: Update documentation + research mission templates

**Purpose**: Update non-software-dev mission templates.

**Steps**:
1. In `src/doctrine/missions/documentation/templates/plan-template.md`:
   - `## Constitution Check` → `## Charter Check`
2. In `src/doctrine/missions/research/templates/task-prompt-template.md`:
   - `.kittify/constitution/constitution.md` → `.kittify/charter/charter.md`
3. In `src/doctrine/missions/software-dev/mission.yaml`:
   - "constitution" → "charter" in the description text

**Validation**: `rg -i constitution src/doctrine/missions/` returns zero matches.

## Definition of Done

- [ ] `src/doctrine/charter/` exists (old constitution/ removed)
- [ ] `src/doctrine/skills/spec-kitty-charter-doctrine/` exists (old constitution-doctrine/ removed)
- [ ] Command template at `charter.md` (old constitution.md removed)
- [ ] Procedure file renamed
- [ ] All 9 doctrine mission artifacts updated
- [ ] `rg -i constitution src/doctrine/ src/specify_cli/missions/` returns zero matches

## Risks

- **Skill deployment**: After renaming, the global skill sync (`ensure_global_agent_skills()`) will auto-deploy the new skill and remove the old one. No manual intervention needed.
- **Template loading**: Verify the mission config loader finds `charter.md` by name.

## Reviewer Guidance

- Check SKILL.md triggers carefully — agents match on these strings
- Verify all mission templates (software-dev, documentation, research) are covered
- Check the plan-template.md "Charter Check" section — this drives the planning workflow
