---
work_package_id: WP05
title: Agent Artifacts & Configuration
dependencies: []
requirement_refs:
- FR-005
- FR-014
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks: [T025, T026, T027, T028, T029, T030, T031]
history:
- date: '2026-04-04'
  action: created
  by: spec-kitty.tasks
authoritative_surface: .claude/
execution_mode: code_change
owned_files: [.claude/**, .codex/**, .opencode/**, .agents/**, .github/prompts/**, .gemini/**, .cursor/**, .qwen/**, .windsurf/**, .kilocode/**, .augment/**, .roo/**, .amazonq/**, .kittify/skills-manifest.json, .kittify/AGENTS.md, .kittify/overrides/**, .kittify/charter/**, .kittify/memory/**, .gitignore, CLAUDE.md]
---

# WP05: Agent Artifacts & Configuration

## Objective

Rename agent command files and skill directories across all 12 agent directories. Update configuration files (.kittify/skills-manifest.json, AGENTS.md, .gitignore, CLAUDE.md). Rename the dev repo's own `.kittify/constitution/` directory.

## Context

Agent artifacts are generated copies of source templates (from WP04). This WP renames the DEPLOYED copies in the spec-kitty development repo itself. The 12 supported agents each have command files and some have skill directories.

Agent directories: `.claude/`, `.codex/`, `.opencode/`, `.github/`, `.gemini/`, `.cursor/`, `.qwen/`, `.windsurf/`, `.kilocode/`, `.augment/`, `.roo/`, `.amazonq/`

## Implementation Command

```bash
spec-kitty implement WP05 --base WP04
```

## Subtask T025: Rename command files in all agent directories

**Purpose**: Each agent has a `spec-kitty.constitution.md` command file that must become `spec-kitty.charter.md`.

**Steps**:
For each agent directory that exists and contains a constitution command file:
1. Find the file: `find . -name 'spec-kitty.constitution.md' -not -path './.git/*' -not -path './kitty-specs/*'`
2. For each found file: `git mv <path>/spec-kitty.constitution.md <path>/spec-kitty.charter.md`
3. Update content in each renamed file: replace all "constitution" → "charter"

Known locations (verify each exists before renaming):
- `.claude/commands/spec-kitty.constitution.md`
- `.codex/prompts/spec-kitty.constitution.md`
- `.opencode/command/spec-kitty.constitution.md`
- And up to 9 more agent directories

**Validation**: `find . -name '*constitution*' -path './*/' -not -path './.git/*' -not -path './kitty-specs/*' -not -path './.kittify/.migration-backup/*'` returns zero results for command files.

## Subtask T026: Rename skill directories in all agent directories

**Purpose**: Skill directories contain `spec-kitty-constitution-doctrine/` which must become `spec-kitty-charter-doctrine/`.

**Steps**:
1. Find all: `find . -type d -name 'spec-kitty-constitution-doctrine' -not -path './.git/*' -not -path './kitty-specs/*' -not -path './src/*' -not -path './.kittify/.migration-backup/*'`
2. For each found directory: `git mv <path>/spec-kitty-constitution-doctrine/ <path>/spec-kitty-charter-doctrine/`
3. Within each renamed directory: rename reference files if they contain "constitution" in their names
4. Update content of all files within (SKILL.md, references/*.md)

Known locations:
- `.claude/skills/spec-kitty-constitution-doctrine/`
- `.agents/skills/spec-kitty-constitution-doctrine/`

**Validation**: No directories named `spec-kitty-constitution-doctrine` remain outside `.git/`, `kitty-specs/`, `src/`, and `.kittify/.migration-backup/`.

## Subtask T027: Update .kittify/skills-manifest.json

**Purpose**: The skills manifest tracks installed skills by name.

**Steps**:
1. In `.kittify/skills-manifest.json`:
   - Replace all `"spec-kitty-constitution-doctrine"` → `"spec-kitty-charter-doctrine"`
   - Replace any path references containing "constitution"

**Validation**: `rg -i constitution .kittify/skills-manifest.json` returns zero matches.

## Subtask T028: Update .kittify/AGENTS.md + overrides

**Purpose**: Agent guidance documents reference constitution paths and concepts.

**Steps**:
1. In `.kittify/AGENTS.md` (3 matches):
   - "Follow the plan and constitution requirements" → "Follow the plan and charter requirements"
   - "`.kittify/constitution/constitution.md` - Project constitution" → "`.kittify/charter/charter.md` - Project charter"
   - "### Worktree Constitution Sharing" → "### Worktree Charter Sharing"
2. In `.kittify/overrides/AGENTS.md` (3 matches): same changes

**Validation**: `rg -i constitution .kittify/AGENTS.md .kittify/overrides/AGENTS.md` returns zero matches.

## Subtask T029: Update .gitignore entries

**Purpose**: Update gitignore patterns for the new charter directory.

**Steps**:
1. In `.gitignore`, replace:
   - `.kittify/constitution/context-state.json` → `.kittify/charter/context-state.json`
   - `.kittify/constitution/directives.yaml` → `.kittify/charter/directives.yaml`
   - `.kittify/constitution/governance.yaml` → `.kittify/charter/governance.yaml`
   - `.kittify/constitution/metadata.yaml` → `.kittify/charter/metadata.yaml`
   - `.kittify/constitution/references.yaml` → `.kittify/charter/references.yaml`

**Validation**: `rg -i constitution .gitignore` returns zero matches.

## Subtask T030: Rename .kittify/constitution/ → .kittify/charter/ (dev repo)

**Purpose**: The spec-kitty development repo itself has a `.kittify/constitution/` directory.

**Steps**:
1. `git mv .kittify/constitution/ .kittify/charter/` (if tracked by git)
   - If not tracked: `mv .kittify/constitution/ .kittify/charter/`
2. Rename the main document: `git mv .kittify/charter/constitution.md .kittify/charter/charter.md` (if exists)
3. Update content within `.kittify/charter/charter.md`: replace "constitution" → "charter" in headers and generator comments

**Validation**: `.kittify/constitution/` does not exist. `.kittify/charter/charter.md` exists.

## Subtask T031: Update CLAUDE.md

**Purpose**: The project instructions file references constitution commands and paths.

**Steps**:
1. In `CLAUDE.md`:
   - Replace `spec-kitty constitution` → `spec-kitty charter` in all command examples
   - Replace `Constitution Check` → `Charter Check` in template descriptions
   - Replace `.kittify/constitution/` → `.kittify/charter/` in path references
   - Replace any other "constitution" references
2. In `.kittify/memory/058-architectural-review.md` (7 matches):
   - Replace all "constitution" references

**Validation**: `rg -i constitution CLAUDE.md .kittify/memory/058-architectural-review.md` returns zero matches.

## Definition of Done

- [ ] No agent directory contains `spec-kitty.constitution.md` files
- [ ] No agent directory contains `spec-kitty-constitution-doctrine/` directories
- [ ] `.kittify/charter/charter.md` exists (old constitution/ removed)
- [ ] .gitignore uses charter paths
- [ ] CLAUDE.md uses charter terminology
- [ ] `rg -i constitution` across all owned files returns zero matches

## Risks

- **Missing agent directories**: Some of the 12 directories may not exist in the dev repo. Use existence checks before `git mv`.
- **Untracked files**: `.kittify/constitution/` may contain untracked generated files. Use `mv` for those, `git mv` for tracked ones.

## Reviewer Guidance

- Verify the full list of 12 agent directories is checked
- Confirm .gitignore patterns match the actual charter directory structure
- Check CLAUDE.md thoroughly — it's the primary project context for agents
