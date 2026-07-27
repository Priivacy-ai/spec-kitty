# Data Model: Universal Charter Rename

**Feature**: 063-universal-charter-rename
**Date**: 2026-04-04 (revised)

## Entities

### Charter (was: Constitution)

The governance document and its associated configuration for a spec-kitty project.

**Canonical path**: `.kittify/charter/`

| File | Purpose | Format | Embedded "constitution" to rewrite |
|------|---------|--------|------------------------------------|
| `charter.md` | Main governance document | Markdown | Header, generator comment |
| `interview/answers.yaml` | Interview responses | YAML | None expected |
| `references.yaml` | Reference manifest | YAML | `source_path` entries |
| `library/*.md` | Support documentation | Markdown | None expected |
| `governance.yaml` | Generated governance config | YAML | Possible embedded references |
| `directives.yaml` | Generated directives | YAML | Possible embedded references |
| `metadata.yaml` | Generated metadata | YAML | Possible embedded references |
| `context-state.json` | Context state tracking | JSON | Possible path references |

**Legacy paths** (migration sources):

| Layout | Path | Source Version |
|--------|------|----------------|
| A (modern) | `.kittify/constitution/constitution.md` + subdirs | 2.0.0+ |
| B (legacy) | `.kittify/memory/constitution.md` (single file) | Pre-2.0 |
| C (very old) | `.kittify/missions/*/constitution/` (per-mission dirs) | Pre-0.10.12 |

### Migration State

Applied migrations tracked in `.kittify/metadata.yaml`.

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Migration identifier — normalized to charter-era names at load time |
| `applied_at` | datetime | When the migration was applied |
| `result` | string | `"success"`, `"skipped"`, or `"failed"` |
| `notes` | string | Optional notes |

### Metadata ID Normalization

On `ProjectMetadata.load()`, old migration IDs are rewritten to charter-era names before the runner checks them.

| Old ID (in user metadata) | New ID (after normalization) |
|--------------------------|------------------------------|
| `0.10.12_constitution_cleanup` | `0.10.12_charter_cleanup` |
| `0.13.0_update_constitution_templates` | `0.13.0_update_charter_templates` |
| `2.0.0_constitution_directory` | `2.0.0_charter_directory` |
| `2.0.2_constitution_context_bootstrap` | `2.0.2_charter_context_bootstrap` |
| `2.1.2_fix_constitution_doctrine_skill` | `2.1.2_fix_charter_doctrine_skill` |

After normalization, the updated metadata is persisted so the map is only needed once per user.

### Old Migration Stubs

The 5 existing constitution-related migrations become no-op stubs:

| File (renamed) | New migration_id | Behavior |
|----------------|------------------|----------|
| `m_0_10_12_charter_cleanup.py` | `0.10.12_charter_cleanup` | `detect()` → False |
| `m_0_13_0_update_charter_templates.py` | `0.13.0_update_charter_templates` | `detect()` → False (was already disabled) |
| `m_2_0_0_charter_directory.py` | `2.0.0_charter_directory` | `detect()` → False |
| `m_2_0_2_charter_context_bootstrap.py` | `2.0.2_charter_context_bootstrap` | `detect()` → False |
| `m_2_1_2_fix_charter_doctrine_skill.py` | `2.1.2_fix_charter_doctrine_skill` | `detect()` → False |

### New Migration: Charter Rename

| Attribute | Value |
|-----------|-------|
| `migration_id` | `"3.1.1_charter_rename"` |
| `target_version` | `"3.1.1"` |
| `description` | `"Comprehensive charter rename: migrate all constitution-era state"` |

**State transitions**:

```
detect():
  .kittify/constitution/ exists           → True (Layout A)
  .kittify/memory/constitution.md exists  → True (Layout B)
  .kittify/missions/*/constitution/ exist → True (Layout C)
  none of the above                       → False (already migrated or fresh)

apply():
  Phase 1: Layout normalization
    Layout C: remove .kittify/missions/*/constitution/ dirs
    Layout B: mkdir .kittify/charter/, move memory/constitution.md → charter/charter.md
    Layout A: mv .kittify/constitution/ → .kittify/charter/
              mv .kittify/charter/constitution.md → .kittify/charter/charter.md
    Partial:  merge constitution/ into charter/ (no overwrite), remove constitution/

  Phase 2: Content rewriting
    For each text file in .kittify/charter/:
      case-insensitive replace "constitution" → "charter"
    For each deployed agent prompt file:
      replace "spec-kitty constitution context" → "spec-kitty charter context"

  Phase 3: Agent artifact rename
    Rename spec-kitty.constitution.md → spec-kitty.charter.md in all agent dirs
    Rename spec-kitty-constitution-doctrine/ → spec-kitty-charter-doctrine/ in all agent skill dirs

  Phase 4: Metadata normalization
    Rewrite old migration IDs in .kittify/metadata.yaml (same map as load-time normalizer)

  Already done:
    .kittify/charter/charter.md exists, no constitution paths → no-op
```

## Path Mappings

### Source Code Paths

| Old Path | New Path |
|----------|----------|
| `src/constitution/` | `src/charter/` |
| `src/specify_cli/constitution/` | `src/specify_cli/charter/` |
| `src/specify_cli/cli/commands/constitution.py` | `src/specify_cli/cli/commands/charter.py` |
| `src/specify_cli/dashboard/constitution_path.py` | `src/specify_cli/dashboard/charter_path.py` |
| `src/doctrine/constitution/` | `src/doctrine/charter/` |

### Skill Paths

| Old Path | New Path |
|----------|----------|
| `src/doctrine/skills/spec-kitty-constitution-doctrine/` | `src/doctrine/skills/spec-kitty-charter-doctrine/` |
| `references/constitution-command-map.md` | `references/charter-command-map.md` |

### Agent Artifact Paths (per agent directory)

| Old Path | New Path |
|----------|----------|
| `<agent>/commands/spec-kitty.constitution.md` | `<agent>/commands/spec-kitty.charter.md` |
| `<agent>/skills/spec-kitty-constitution-doctrine/` | `<agent>/skills/spec-kitty-charter-doctrine/` |

### User Project Paths

| Old Path | New Path |
|----------|----------|
| `.kittify/constitution/` | `.kittify/charter/` |
| `.kittify/constitution/constitution.md` | `.kittify/charter/charter.md` |
| `.kittify/memory/constitution.md` | `.kittify/charter/charter.md` |
| `.kittify/missions/*/constitution/` | Removed |

## Symbol Renames (Key Classes & Functions)

| Old Symbol | New Symbol | Module |
|-----------|-----------|--------|
| `CompiledConstitution` | `CompiledCharter` | `charter.compiler` |
| `ConstitutionParser` | `CharterParser` | `charter.parser` |
| `ConstitutionSection` | `CharterSection` | `charter.parser` |
| `ConstitutionInterview` | `CharterInterview` | `charter.interview` |
| `ConstitutionTemplateResolver` | `CharterTemplateResolver` | `charter.template_resolver` |
| `compile_constitution()` | `compile_charter()` | `charter.compiler` |
| `write_compiled_constitution()` | `write_compiled_charter()` | `charter.compiler` |
| `build_constitution_context()` | `build_charter_context()` | `charter.context` |
| `build_constitution_draft()` | `build_charter_draft()` | `charter.generator` |
| `sync_constitution()` | `sync_charter()` | `charter.sync` |
| `resolve_project_constitution_path()` | `resolve_project_charter_path()` | `specify_cli.dashboard.charter_path` |
| `copy_constitution_templates()` | `copy_charter_templates()` | `specify_cli.template.manager` |
| `ConstitutionCleanupMigration` | `CharterCleanupMigration` | (stub) |
| `ConstitutionDirectoryMigration` | `CharterDirectoryMigration` | (stub) |
| `ConstitutionContextBootstrapMigration` | `CharterContextBootstrapMigration` | (stub) |
| `UpdateConstitutionTemplatesMigration` | `UpdateCharterTemplatesMigration` | (stub) |
| `FixConstitutionDoctrineSkillMigration` | `FixCharterDoctrineSkillMigration` | (stub) |

## Backward-Compatibility Exception Files

Exactly 2 files in shipped source will contain "constitution" strings after the rename:

| File | Reason | Content |
|------|--------|---------|
| `src/specify_cli/upgrade/migrations/m_3_1_1_charter_rename.py` | Must detect old filesystem paths containing "constitution" | Path literals in `detect()` and `apply()` |
| `src/specify_cli/upgrade/metadata.py` | Must map old migration IDs to new ones | 5 dictionary keys in `_LEGACY_MIGRATION_ID_MAP` |

These are precisely bounded, justified by backward-compatibility requirements, and defined as the ONLY permitted exceptions in NFR-001.
