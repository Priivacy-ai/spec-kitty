# Universal Charter Rename

## Overview

The spec-kitty codebase uses the term "constitution" as the name for its governance document, CLI command group, Python packages, persisted project paths, skill definitions, prompt templates, documentation, tests, and migrations. This term must be universally replaced with "charter" across every surface. Existing user projects that store governance state under "constitution" paths must be migrated to "charter" paths with zero data loss, including rewriting embedded references inside generated files.

## Problem Statement

"Constitution" appears in approximately 120+ files across 12+ distinct surface categories. Users interact with `spec-kitty constitution` commands, store governance artifacts under `.kittify/constitution/`, and reference the term throughout their workflow. Generated artifacts (governance.yaml, references.yaml, context-state.json) embed "constitution" in path references and command strings. Worktree setup code copies constitution state into execution workspaces. Renaming a term this deeply embedded requires coordinated changes across CLI, runtime, packaging, skills, agent artifacts, doctrine mission templates, worktree management, documentation, tests, and migrations — plus a comprehensive migration that handles every known legacy layout, rewrites generated content, and normalizes historical metadata.

## Actors

- **Spec-kitty user**: Runs CLI commands, stores governance artifacts in `.kittify/`, interacts with agent skills
- **Spec-kitty contributor**: Maintains source code, writes tests, authors migrations
- **AI agent**: Consumes slash commands, skills, and prompt templates that reference the governance concept

## User Scenarios & Testing

### Scenario 1: Existing User Upgrades (Layout A)
A user with `.kittify/constitution/constitution.md` and `.kittify/constitution/governance.yaml` runs `spec-kitty upgrade`. After upgrade: all governance artifacts exist under `.kittify/charter/` with content rewritten (embedded paths like `source_path=".kittify/constitution/..."` become `source_path=".kittify/charter/..."`). The old `.kittify/constitution/` directory no longer exists. The user's `.kittify/metadata.yaml` migration records use charter-based IDs. The user runs `spec-kitty charter context --action specify` and gets coherent governance context.

### Scenario 2: Legacy Memory Path User Upgrades (Layout B)
A user with the older `.kittify/memory/constitution.md` layout (no `.kittify/constitution/` directory) runs `spec-kitty upgrade`. The migration moves `.kittify/memory/constitution.md` to `.kittify/charter/charter.md`. Subsequent commands work without manual intervention.

### Scenario 3: Very Old User Upgrades (Layout C)
A user with `.kittify/missions/*/constitution/` directories (pre-0.10.12 layout) runs `spec-kitty upgrade`. The charter-rename migration removes mission-specific constitution directories and establishes the canonical `.kittify/charter/` layout.

### Scenario 4: Fresh Init
A new user runs `spec-kitty init`. All scaffolded paths use `.kittify/charter/`. The CLI command group is `spec-kitty charter`. No reference to "constitution" appears in any user-visible surface.

### Scenario 5: Agent Slash Command Usage
An AI agent invokes `/spec-kitty.charter` (previously `/spec-kitty.constitution`). The command template, skill definition, and governance context bootstrap all use "charter" terminology. The agent receives coherent governance context with no mention of "constitution".

### Scenario 6: Partial Migration Recovery
A user's previous upgrade was interrupted after moving `.kittify/constitution/constitution.md` to `.kittify/charter/charter.md` but before cleaning up the old directory. Running `spec-kitty upgrade` again completes the cleanup idempotently without data loss or error.

### Scenario 7: Worktree Creation After Upgrade
A user upgrades, then runs `spec-kitty implement WP01`. The new worktree's `.kittify/` symlinks point to the charter layout. No worktree contains references to constitution paths.

### Scenario 8: Contributor Development Workflow
A contributor clones the repo, runs tests, and searches for "constitution" (excluding CHANGELOG.md, kitty-specs/, and the 2 precisely bounded backward-compatibility files). Zero matches are found. All imports, module names, and test paths use "charter".

## Rename Inventory

### Surface 1: CLI Commands
| Current | Target |
|---------|--------|
| `spec-kitty constitution interview` | `spec-kitty charter interview` |
| `spec-kitty constitution generate` | `spec-kitty charter generate` |
| `spec-kitty constitution context` | `spec-kitty charter context` |
| `spec-kitty constitution sync` | `spec-kitty charter sync` |
| `spec-kitty constitution status` | `spec-kitty charter status` |
| CLI command file: `src/specify_cli/cli/commands/constitution.py` | `src/specify_cli/cli/commands/charter.py` |

### Surface 2: Python Packages & Modules
| Current Path | Target Path |
|-------------|------------|
| `src/constitution/` (14 modules) | `src/charter/` |
| `src/specify_cli/constitution/` (11 modules) | `src/specify_cli/charter/` |
| `src/specify_cli/dashboard/constitution_path.py` | `src/specify_cli/dashboard/charter_path.py` |
| `src/specify_cli/state_contract.py` (references `.kittify/constitution/context-state.json`) | Updated to charter paths |
| `src/specify_cli/cli/commands/init.py` (constitution setup during init) | Updated to charter |
| `src/doctrine/constitution/defaults.yaml` | `src/doctrine/charter/defaults.yaml` |

All import statements across the codebase referencing `constitution.*` must change to `charter.*`.

### Surface 3: Persisted User Project Paths
| Current Layout | Target Layout |
|---------------|--------------|
| `.kittify/constitution/constitution.md` | `.kittify/charter/charter.md` |
| `.kittify/constitution/interview/answers.yaml` | `.kittify/charter/interview/answers.yaml` |
| `.kittify/constitution/references.yaml` | `.kittify/charter/references.yaml` |
| `.kittify/constitution/library/*.md` | `.kittify/charter/library/*.md` |
| `.kittify/constitution/governance.yaml` | `.kittify/charter/governance.yaml` |
| `.kittify/constitution/directives.yaml` | `.kittify/charter/directives.yaml` |
| `.kittify/constitution/metadata.yaml` | `.kittify/charter/metadata.yaml` |
| `.kittify/constitution/context-state.json` | `.kittify/charter/context-state.json` |
| `.kittify/memory/constitution.md` (legacy Layout B) | `.kittify/charter/charter.md` |
| `.kittify/missions/*/constitution/` (legacy Layout C) | Removed (consolidated into charter layout) |

### Surface 3a: Generated Content Inside Persisted Files
The migration must also rewrite embedded "constitution" references within generated files, not just move them:
| File | Embedded References |
|------|-------------------|
| `charter.md` (was `constitution.md`) | Header `# Project Constitution`, generator comment `spec-kitty constitution generate` |
| `references.yaml` | `source_path: ".kittify/constitution/..."` entries |
| `context-state.json` | Any path references |
| Agent prompt files | `spec-kitty constitution context --action {action} --json` bootstrap commands |

### Surface 4: Skills
| Current | Target |
|---------|--------|
| Skill name: `spec-kitty-constitution-doctrine` | `spec-kitty-charter-doctrine` |
| Source: `src/doctrine/skills/spec-kitty-constitution-doctrine/` | `src/doctrine/skills/spec-kitty-charter-doctrine/` |
| Reference: `references/constitution-command-map.md` | `references/charter-command-map.md` |
| Installed: `.claude/skills/spec-kitty-constitution-doctrine/` | `.claude/skills/spec-kitty-charter-doctrine/` |
| Installed: `.agents/skills/spec-kitty-constitution-doctrine/` | `.agents/skills/spec-kitty-charter-doctrine/` |
| Manifest entries in `.kittify/skills-manifest.json` | Updated to charter name |

### Surface 5: Command Templates & Agent Artifacts
| Current | Target |
|---------|--------|
| `src/specify_cli/missions/software-dev/command-templates/constitution.md` | `...command-templates/charter.md` |
| `.claude/commands/spec-kitty.constitution.md` | `.claude/commands/spec-kitty.charter.md` |
| `.codex/prompts/spec-kitty.constitution.md` | `.codex/prompts/spec-kitty.charter.md` |
| `.opencode/command/spec-kitty.constitution.md` | `.opencode/command/spec-kitty.charter.md` |
| All other agent directories with constitution command files | Renamed to charter |

### Surface 6: Migrations
| Current | Action |
|---------|--------|
| `m_0_10_12_constitution_cleanup.py` | Convert to no-op stub, rename file |
| `m_0_13_0_update_constitution_templates.py` | Convert to no-op stub (already disabled), rename file |
| `m_2_0_0_constitution_directory.py` | Convert to no-op stub, rename file |
| `m_2_0_2_constitution_context_bootstrap.py` | Convert to no-op stub, rename file |
| `m_2_1_2_fix_constitution_doctrine_skill.py` | Convert to no-op stub, rename file |
| `src/specify_cli/upgrade/metadata.py` | Add legacy migration ID normalization map |
| New: `m_3_1_1_charter_rename.py` | Comprehensive migration handling ALL legacy layouts, content rewriting, prompt updates, metadata ID normalization |
| `src/doctrine/procedures/shipped/migrate-project-guidance-to-spec-kitty-constitution.procedure.yaml` | Rename to charter equivalent |

Old migrations are converted to stubs (`detect()` returns `False`) because the new charter-rename migration subsumes all their functionality. The metadata normalization map rewrites old migration IDs in `.kittify/metadata.yaml` on load, so users who already ran the old migrations have their records updated to charter-based IDs.

### Surface 7: Tests
| Current | Target |
|---------|--------|
| `tests/constitution/` (16 test files) | `tests/charter/` |
| `tests/init/test_constitution_runtime_integration.py` | `tests/init/test_charter_runtime_integration.py` |
| `tests/test_dashboard/test_api_constitution.py` | `tests/test_dashboard/test_api_charter.py` |
| `tests/upgrade/migrations/test_constitution_migration.py` | `tests/upgrade/migrations/test_charter_migration.py` |
| `tests/upgrade/test_constitution_template_migration.py` | `tests/upgrade/test_charter_template_migration.py` |
| `tests/upgrade/test_migration_constitution_cleanup_unit.py` | `tests/upgrade/test_migration_charter_cleanup_unit.py` |
| `tests/merge/test_profile_constitution_e2e.py` | `tests/merge/test_profile_charter_e2e.py` |
| `tests/agent/cli/commands/test_constitution_cli.py` | `tests/agent/cli/commands/test_charter_cli.py` |
| `tests/agent/test_workflow_constitution_context.py` | `tests/agent/test_workflow_charter_context.py` |
| `tests/git_ops/test_worktree.py` | Update constitution.md references to charter.md |

All test content referencing "constitution" in strings, paths, assertions, and fixtures must also be updated.

### Surface 8: Documentation (comprehensive)
| Current | Target |
|---------|--------|
| `docs/2x/doctrine-and-constitution.md` | `docs/2x/doctrine-and-charter.md` |
| `docs/development/constitution-path-resolution-gaps.md` | `docs/development/charter-path-resolution-gaps.md` |
| `examples/constitution-driven-quality.md` | `examples/charter-driven-quality.md` |
| `architecture/2.x/user_journey/005-governance-mission-constitution-operations.md` | `...005-governance-mission-charter-operations.md` |
| `README.md` (9 matches) | Updated to charter |
| `docs/reference/cli-commands.md` (27 matches) | Updated to charter |
| `docs/reference/slash-commands.md` (18 matches) | Updated to charter |
| `docs/reference/file-structure.md` (3 matches) | Updated to charter |
| `docs/reference/supported-agents.md` (1 match) | Updated to charter |
| `docs/reference/configuration.md` (8 matches) | Updated to charter |
| `glossary/README.md` (1 match) | Updated to charter |
| `glossary/contexts/governance.md` (16 matches) | Updated to charter |
| `glossary/contexts/configuration-project-structure.md` (6 matches) | Updated to charter |
| `glossary/contexts/doctrine.md` (13 matches) | Updated to charter |
| `src/kernel/README.md` (5 matches) | Updated to charter |
| `src/kernel/paths.py` (1 match) | Updated to charter |
| `.kittify/AGENTS.md` (3 matches) | Updated to charter |
| `.kittify/overrides/AGENTS.md` (3 matches) | Updated to charter |
| `.kittify/memory/058-architectural-review.md` (7 matches) | Updated to charter |
| `docs/development/test-execution-report-pr305.md` | Updated to charter |
| `docs/development/doctrine-inclusion-assessment.md` | Updated to charter |
| `docs/development/pr305-review-resolution-plan.md` | Updated to charter |
| `docs/development/code-review-2026-03-25.md` | Updated to charter |
| `docs/development/test-plan-pr305.md` | Updated to charter |
| `docs/how-to/non-interactive-init.md` | Updated to charter |
| `docs/how-to/setup-governance.md` | Updated to charter |
| `examples/claude-cursor-collaboration.md` | Updated to charter |
| `examples/solo-developer-workflow.md` | Updated to charter |
| `examples/worktree-parallel-features.md` | Updated to charter |
| `architecture/2.x/04_implementation_mapping/README.md` | Updated to charter |
| `architecture/audience/internal/maintainer.md` | Updated to charter |
| `architecture/audience/internal/spec-kitty-cli-runtime.md` | Updated to charter |
| `architecture/audience/internal/lead-developer.md` | Updated to charter |

### Surface 9: Configuration & Build
| File | Changes |
|------|---------|
| `pyproject.toml` | Package list, data includes — all "constitution" references become "charter" |
| `.gitignore` | `.kittify/constitution/` entries become `.kittify/charter/` |
| `.kittify/skills-manifest.json` | Skill name entries updated |
| `CLAUDE.md` | References to `spec-kitty constitution` commands and `Constitution Check` sections updated |

### Surface 10: Doctrine Mission Artifacts
| File | Changes |
|------|---------|
| `src/doctrine/missions/software-dev/mission.yaml` | "constitution" → "charter" (1 match) |
| `src/doctrine/missions/software-dev/templates/plan-template.md` | "Constitution Check" → "Charter Check" (2 matches) |
| `src/doctrine/missions/software-dev/templates/task-prompt-template.md` | `.kittify/constitution/constitution.md` path reference (1 match) |
| `src/doctrine/missions/software-dev/actions/specify/guidelines.md` | "constitution context bootstrap" → "charter context bootstrap" (1 match) |
| `src/doctrine/missions/software-dev/actions/plan/guidelines.md` | "Constitution Compliance" section + "constitution" references (5 matches) |
| `src/doctrine/missions/software-dev/actions/implement/guidelines.md` | "constitution context bootstrap" (1 match) |
| `src/doctrine/missions/software-dev/actions/review/guidelines.md` | "constitution context bootstrap" (1 match) |
| `src/doctrine/missions/documentation/templates/plan-template.md` | "Constitution Check" (1 match) |
| `src/doctrine/missions/research/templates/task-prompt-template.md` | `.kittify/constitution/constitution.md` path reference (1 match) |

### Surface 11: Worktree & Runtime Code
| File | Changes |
|------|---------|
| `src/specify_cli/core/worktree.py` | `setup_feature_directory()` comment and symlink logic referencing constitution (1+ matches) |
| `src/specify_cli/template/manager.py` | `copy_constitution_templates()` → `copy_charter_templates()`, all internal references |
| `src/specify_cli/cli/commands/init.py` | Constitution setup references during project initialization |

### Surface 12: Doctrine Procedures
| Current | Target |
|---------|--------|
| `src/doctrine/procedures/shipped/migrate-project-guidance-to-spec-kitty-constitution.procedure.yaml` | `...migrate-project-guidance-to-spec-kitty-charter.procedure.yaml` |

## Canonical Charter Path Layout

After this rename, the canonical governance directory layout for user projects is:

```
.kittify/
  charter/
    charter.md              # Main governance document (was constitution.md)
    interview/
      answers.yaml          # Interview responses
    references.yaml         # Reference manifest
    library/
      *.md                  # Support documentation
    governance.yaml         # Generated governance config
    directives.yaml         # Generated directives
    metadata.yaml           # Generated metadata
    context-state.json      # Context state tracking
```

## Migration Strategy

### Comprehensive Charter-Rename Migration

A single new migration (`m_3_1_1_charter_rename.py`) handles ALL known legacy layouts. The 5 existing constitution-related migrations are converted to no-op stubs because the charter-rename migration subsumes their functionality.

### Supported Layouts

**Layout A (modern, post-2.0)**: `.kittify/constitution/` full directory tree
**Action**: Rename directory to `.kittify/charter/`. Rename `constitution.md` → `charter.md`. Rewrite embedded "constitution" references in generated files. Update agent prompt bootstrap commands.

**Layout B (legacy, pre-2.0)**: `.kittify/memory/constitution.md` single file
**Action**: Create `.kittify/charter/`. Move file to `.kittify/charter/charter.md`. Leave `.kittify/memory/` otherwise untouched.

**Layout C (very old, pre-0.10.12)**: `.kittify/missions/*/constitution/` directories
**Action**: Remove mission-specific constitution directories. Establish canonical `.kittify/charter/` layout from `.kittify/memory/constitution.md` if present.

### Content Rewriting

After path moves, the migration rewrites embedded "constitution" references in all files under `.kittify/charter/`:
- `charter.md`: header, generator comment
- `references.yaml`: `source_path` entries
- `context-state.json`: any path references
- `governance.yaml`, `directives.yaml`, `metadata.yaml`: any embedded references
- Deployed agent prompt files: `spec-kitty constitution context` → `spec-kitty charter context`

### Metadata ID Normalization

On metadata load, a normalization map rewrites historical migration IDs from constitution-era names to charter-era names. This runs at load time (before the migration loop), ensuring the runner correctly recognizes previously-applied migrations under their new IDs.

### Idempotency Rules
1. If `.kittify/charter/charter.md` already exists and no constitution paths exist, migration is a no-op.
2. If both `.kittify/charter/` and `.kittify/constitution/` exist (partial migration), merge files from `constitution/` that don't already exist in `charter/`, then remove `constitution/`.
3. If `.kittify/memory/constitution.md` exists but `.kittify/charter/charter.md` already exists, the memory file is a stale leftover — remove it.
4. Migration must never overwrite user data that already exists at the target path.

### Old Migration Stub Conversion

The 5 existing constitution-related migrations are converted to stubs:
- File renamed (e.g., `m_0_10_12_charter_cleanup.py`)
- `migration_id` changed to charter-based name (e.g., `"0.10.12_charter_cleanup"`)
- `detect()` returns `False` (superseded by charter-rename)
- `can_apply()` returns `False, "Superseded by charter-rename migration"`
- `apply()` returns success no-op

The metadata normalization map bridges old IDs → new IDs so the runner recognizes previously-applied records.

## Functional Requirements

| ID | Requirement | Status |
|----|-------------|--------|
| FR-001 | All CLI commands previously under `spec-kitty constitution` are available under `spec-kitty charter` with identical behavior | Proposed |
| FR-002 | All governance artifacts are stored under `.kittify/charter/` in user projects | Proposed |
| FR-003 | The main governance document is named `charter.md` (not `constitution.md`) | Proposed |
| FR-004 | The skill `spec-kitty-charter-doctrine` replaces `spec-kitty-constitution-doctrine` in all agent directories | Proposed |
| FR-005 | All agent slash commands use `/spec-kitty.charter` (not `/spec-kitty.constitution`) | Proposed |
| FR-006 | An upgrade migration moves `.kittify/constitution/` contents to `.kittify/charter/` preserving all user data | Proposed |
| FR-007 | An upgrade migration moves `.kittify/memory/constitution.md` to `.kittify/charter/charter.md` | Proposed |
| FR-008 | Migration is idempotent: running it multiple times produces the same result without data loss | Proposed |
| FR-009 | Migration handles partial/interrupted states safely (both source and target exist) | Proposed |
| FR-010 | All Python imports reference `charter` modules, not `constitution` modules | Proposed |
| FR-011 | The `pyproject.toml` package configuration references `charter` packages, not `constitution` | Proposed |
| FR-012 | All prompt templates, command templates, and doctrine mission artifacts use "charter" terminology | Proposed |
| FR-013 | Fresh `spec-kitty init` scaffolds `.kittify/charter/` with no "constitution" references | Proposed |
| FR-014 | The `.gitignore` ignores `.kittify/charter/` generated files (not `.kittify/constitution/`) | Proposed |
| FR-015 | Migration rewrites embedded "constitution" references inside generated `.kittify/` files (governance.yaml, references.yaml, context-state.json, charter.md header/comments) | Proposed |
| FR-016 | Worktree setup code (`setup_feature_directory()`, `copy_charter_templates()`) uses charter paths for new worktrees | Proposed |
| FR-017 | The 5 existing constitution-related migrations are converted to no-op stubs with charter-based migration IDs | Proposed |
| FR-018 | Metadata normalization rewrites old constitution-era migration IDs to charter-era IDs in `.kittify/metadata.yaml` on load | Proposed |
| FR-019 | Migration handles Layout C (pre-0.10.12 mission-specific constitution directories) | Proposed |
| FR-020 | Migration updates bootstrap command strings in deployed agent prompts from `spec-kitty constitution context` to `spec-kitty charter context` | Proposed |

## Non-Functional Requirements

| ID | Requirement | Status |
|----|-------------|--------|
| NFR-001 | Zero occurrences of "constitution" (case-insensitive) in shipped source when searching with `rg`, excluding: CHANGELOG.md, kitty-specs/, and the 2 precisely bounded backward-compatibility files (the charter-rename migration that must detect old paths, and the metadata normalization map that must map old IDs) | Proposed |
| NFR-002 | No file or directory name in the repository contains "constitution", excluding CHANGELOG.md and kitty-specs/ | Proposed |
| NFR-003 | Migration completes in under 5 seconds for a typical project with fewer than 50 governance files | Proposed |
| NFR-004 | All existing tests pass after the rename (adjusted for new names), with 90%+ coverage on new migration code | Proposed |
| NFR-005 | `mypy --strict` passes on all renamed modules | Proposed |

## Constraints

| ID | Constraint | Status |
|----|-----------|--------|
| C-001 | Historical CHANGELOG.md entries mentioning "constitution" are out of scope and left unchanged | Confirmed |
| C-002 | Historical kitty-specs/ feature artifacts mentioning "constitution" are out of scope and left unchanged | Confirmed |
| C-003 | Old migrations must not break upgrades — they are converted to no-op stubs, and the charter-rename migration subsumes their functionality | Confirmed |
| C-004 | The metadata normalization map in metadata.py must bridge old migration IDs to new IDs so previously-applied records are recognized | Confirmed |
| C-005 | No backward-compatibility alias from `spec-kitty constitution` to `spec-kitty charter` — clean break | Confirmed |
| C-006 | The charter-rename migration must contain "constitution" path literals (to detect old state) — this is the only permitted exception in new code | Confirmed |
| C-007 | The metadata normalization map must contain old "constitution" migration ID strings as lookup keys — this is the only other permitted exception | Confirmed |

## Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Missed occurrence of "constitution" in an obscure file | Medium | High — violates acceptance criteria | Automated grep-based acceptance test as final gate, with precisely bounded exclusions |
| Migration overwrites user-modified charter files | Low | High — data loss | Never overwrite existing target files; merge from source only if target absent |
| Metadata normalization misses edge cases | Low | Medium — old migrations re-run | Test normalization against all 5 known old IDs plus corrupt/partial metadata |
| Old migration stubs cause issues for step-by-step upgraders | Low | Medium — missed intermediate transforms | Charter-rename migration handles ALL known layouts, not just post-2.0 state |
| Agent directories not all updated | Medium | Medium — some agents see stale commands | Use `get_agent_dirs_for_project()` helper to ensure all configured agents are processed |
| Import breakage from missed module rename | Medium | High — runtime crash | Run full test suite + mypy as validation gate |
| Generated content rewriting misses embedded references | Medium | Medium — stale strings in user files | Content rewriting uses case-insensitive replacement on all files under `.kittify/charter/` |
| Worktree symlinks break after main repo rename | Low | Medium — stale symlinks | Worktree code uses charter paths; existing worktrees are ephemeral |

## Assumptions

1. The three known legacy layouts (`.kittify/constitution/`, `.kittify/memory/constitution.md`, and `.kittify/missions/*/constitution/`) are the only layouts that need migration support.
2. The skill rename from `spec-kitty-constitution-doctrine` to `spec-kitty-charter-doctrine` does not require preserving the old skill name as an alias.
3. The `.kittify/.migration-backup/` directory may contain old constitution references in backup snapshots; these backups are not modified by this rename.
4. All 12 supported agent directories follow the same pattern for command/prompt file naming and will be updated uniformly.
5. Existing worktrees are ephemeral and will be recreated; the migration does not need to update symlinks in existing worktrees.

## Success Criteria

1. A case-insensitive search for "constitution" across the shipped repository (excluding CHANGELOG.md, kitty-specs/, and the 2 bounded backward-compatibility files) returns zero matches.
2. No file or directory name in the repository contains "constitution" (excluding CHANGELOG.md and kitty-specs/).
3. Users with Layout A (`.kittify/constitution/`) can upgrade and immediately use `spec-kitty charter` commands with preserved and content-rewritten governance data.
4. Users with Layout B (`.kittify/memory/constitution.md`) can upgrade and find their governance document at `.kittify/charter/charter.md`.
5. Users with Layout C (`.kittify/missions/*/constitution/`) can upgrade and have mission-specific constitutions cleaned up.
6. Fresh project initialization produces only "charter" paths and terminology.
7. The full test suite passes with all test files renamed and test content updated.
8. `mypy --strict` passes on all charter modules.
9. After migration, `.kittify/metadata.yaml` contains only charter-era migration IDs (no constitution-era IDs remain).
10. After migration, no generated file under `.kittify/charter/` contains embedded "constitution" references.

## Dependencies

- Existing migration infrastructure in `src/specify_cli/upgrade/migrations/`
- Metadata load/save in `src/specify_cli/upgrade/metadata.py`
- Agent directory management via `get_agent_dirs_for_project()`
- Skill deployment pipeline that copies from `src/doctrine/skills/` to agent directories
- Worktree setup in `src/specify_cli/core/worktree.py`

## Out of Scope

- Historical CHANGELOG.md entries
- Historical kitty-specs/ feature spec artifacts
- Backup snapshots under `.kittify/.migration-backup/`
- Any external documentation or websites referencing "constitution"
- Existing worktree symlinks (ephemeral, will be recreated)
