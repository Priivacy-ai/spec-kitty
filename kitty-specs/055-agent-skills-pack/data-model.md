# Data Model: Agent Skills Pack

**Feature**: 055-agent-skills-pack
**Date**: 2026-03-21

## Entities

### CanonicalSkill

Represents a skill authored in the doctrine layer.

| Field | Type | Description |
|-------|------|-------------|
| name | str | Skill identifier (e.g., `spec-kitty-setup-doctor`) |
| skill_dir | Path | Directory containing SKILL.md and siblings |
| skill_md | Path | Path to SKILL.md |
| references | list[Path] | Paths to files in references/ subdirectory |
| scripts | list[Path] | Paths to files in scripts/ subdirectory |
| assets | list[Path] | Paths to files in assets/ subdirectory |
| all_files | list[Path] | All installable files (SKILL.md + references + scripts + assets) |

**Source location**: `src/doctrine/skills/<name>/`

**Discovery**: Registry scans `src/doctrine/skills/` (local dev) or package `doctrine/skills/` (installed) for directories containing `SKILL.md`.

### ManagedFileEntry

One entry per installed file in the manifest.

| Field | Type | Description |
|-------|------|-------------|
| skill_name | str | Originating skill name |
| source_file | str | Relative path within skill directory (e.g., `SKILL.md`, `references/matrix.md`) |
| installed_path | str | Relative path from project root where file was installed |
| installation_class | str | One of: `shared-root-capable`, `native-root-required`, `wrapper-only` |
| agent_key | str | Agent identifier (e.g., `claude`, `codex`) |
| content_hash | str | `sha256:<hex>` hash of installed content |
| installed_at | str | ISO 8601 timestamp |

### ManagedSkillManifest

Top-level manifest persisted as `.kittify/skills-manifest.json`.

| Field | Type | Description |
|-------|------|-------------|
| version | int | Schema version (starts at 1) |
| created_at | str | ISO 8601 timestamp of first creation |
| updated_at | str | ISO 8601 timestamp of last modification |
| spec_kitty_version | str | Version of spec-kitty that wrote the manifest |
| entries | list[ManagedFileEntry] | All tracked installed files |

### InstallationClass (enum)

| Value | Behavior |
|-------|----------|
| `shared-root-capable` | Install to `.agents/skills/` (shared root) |
| `native-root-required` | Install to vendor-specific skill root (e.g., `.claude/skills/`) |
| `wrapper-only` | No skill installation; wrappers only |

### VerifyResult

Result of checking installed skills against the manifest.

| Field | Type | Description |
|-------|------|-------------|
| ok | bool | True if all checks pass |
| missing | list[ManagedFileEntry] | Files in manifest but not on disk |
| drifted | list[tuple[ManagedFileEntry, str]] | Files with changed hash (entry, actual_hash) |
| unmanaged | list[str] | Files in skill roots not tracked by manifest |
| errors | list[str] | Error messages |

## Relationships

```
CanonicalSkill (1) ──installs──> (N) ManagedFileEntry
ManagedSkillManifest (1) ──contains──> (N) ManagedFileEntry
Agent (1) ──has──> (1) InstallationClass
Agent (1) ──receives──> (N) ManagedFileEntry
```

## State Transitions

### Manifest Lifecycle

```
[no manifest] ──init──> [populated manifest]
[populated manifest] ──verify──> [ok | drift detected]
[drift detected] ──sync/repair──> [populated manifest] (restored)
[populated manifest] ──upgrade──> [updated manifest] (new skills/versions)
```
