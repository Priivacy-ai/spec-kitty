# Data Model: Agent Skills Installer Infrastructure

**Feature**: 042-agent-skills-installer-infrastructure
**Date**: 2026-03-20

## Entities

### DistributionClass (Enum)

Classifies how an agent receives Spec Kitty skill content.

| Value | Meaning |
|-------|---------|
| `shared-root-capable` | Agent officially scans `.agents/skills/` in project scope |
| `native-root-required` | Agent requires a vendor-specific project root for native skills |
| `wrapper-only` | Agent has no first-class `SKILL.md` surface; uses prompt/command wrappers only |

### WrapperConfig (Value Object)

Preserves the exact semantics of the current `AGENT_COMMAND_CONFIG` per-agent dict.

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `dir` | `str` | Wrapper output directory relative to project root | `".claude/commands"` |
| `ext` | `str` | File extension for generated wrappers | `"md"`, `"toml"`, `"prompt.md"` |
| `arg_format` | `str` | Variable syntax for arguments in rendered templates | `"$ARGUMENTS"`, `"{{args}}"` |

### AgentSurface (Entity — Canonical)

Full capability profile for one supported agent. This is the canonical source of truth. All other agent metadata is derived from it.

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `key` | `str` | Canonical agent key (matches `AI_CHOICES` keys) | `"claude"`, `"q"` |
| `display_name` | `str` | Human-readable agent name | `"Claude Code"` |
| `distribution_class` | `DistributionClass` | How this agent receives skill content | `NATIVE_ROOT_REQUIRED` |
| `agent_root` | `str` | Filesystem root directory for this agent | `".claude"` |
| `wrapper` | `WrapperConfig` | Wrapper generation configuration | See WrapperConfig |
| `wrapper_subdir` | `str` | Subdirectory within agent_root for wrappers | `"commands"`, `"prompts"` |
| `skill_roots` | `tuple[str, ...]` | Project skill roots in precedence order | `(".claude/skills/",)` |
| `compat_notes` | `str` | Optional compatibility notes | `"also scans .claude/skills/"` |

**Relationships**: One AgentSurface per supported agent. Stored in `AGENT_SURFACE_CONFIG` dict keyed by `key`.

### ManagedFile (Value Object)

One entry in the skills manifest tracking a Spec-Kitty-managed file.

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `path` | `str` | File path relative to project root | `".claude/commands/spec-kitty.specify.md"` |
| `sha256` | `str` | Content hash for drift detection | `"a1b2c3..."` |
| `file_type` | `str` | Category of managed file | `"wrapper"`, `"skill_root_marker"` |

### SkillsManifest (Entity — Persistent)

Record of what Spec Kitty installed in a project. Serialized to `.kittify/agent-surfaces/skills-manifest.yaml`.

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `spec_kitty_version` | `str` | CLI version that wrote this manifest | `"2.1.0"` |
| `created_at` | `str` | ISO timestamp of first creation | `"2026-03-20T16:00:00Z"` |
| `updated_at` | `str` | ISO timestamp of last update | `"2026-03-20T16:30:00Z"` |
| `skills_mode` | `str` | Distribution mode used during install | `"auto"` |
| `selected_agents` | `list[str]` | Agent keys selected during init | `["claude", "codex"]` |
| `installed_skill_roots` | `list[str]` | Skill root directories created | `[".agents/skills/", ".claude/skills/"]` |
| `managed_files` | `list[ManagedFile]` | All managed file entries | See ManagedFile |

**Lifecycle**: Created during `spec-kitty init`. Updated during `spec-kitty upgrade` and `spec-kitty agent config sync`. Read during verification and drift detection.

### VerificationResult (Value Object)

Result of post-installation verification checks.

| Field | Type | Description |
|-------|------|-------------|
| `passed` | `bool` | True if all checks passed |
| `errors` | `list[str]` | Actionable error messages |
| `warnings` | `list[str]` | Non-blocking warnings |

## State Transitions

### SkillsManifest Lifecycle

```
[Not Exists] → spec-kitty init → [Created]
[Created] → spec-kitty init --force → [Recreated]
[Created] → spec-kitty upgrade → [Updated] (migration adds manifest to pre-Phase-0 projects)
[Created] → spec-kitty agent config sync → [Updated] (repair/cleanup)
[Created] → spec-kitty agent config remove <agent> → [Updated] (orphan cleanup)
```

### Skill Root Directory Lifecycle

```
[Not Exists] → init resolves root needed → [Created with .gitkeep]
[Exists] → agent removed, no other agent needs root → [Removed by sync]
[Exists] → agent removed, other agents still need root → [Preserved by sync]
[Missing] → sync detects missing → [Recreated]
```

## Validation Rules

1. `AgentSurface.key` must be present in `AI_CHOICES` — enforced by a startup assertion.
2. `AgentSurface.wrapper.dir` must equal `f"{agent_root}/{wrapper_subdir}"` — structural consistency.
3. `SkillsManifest.selected_agents` must be a subset of `AGENT_SURFACE_CONFIG.keys()`.
4. `SkillsManifest.installed_skill_roots` must be consistent with the selected agents' distribution classes and the `skills_mode`.
5. `ManagedFile.sha256` must match the current file content for verification to pass.
6. `wrapper-only` agents must have empty `skill_roots` tuples.
7. `native-root-required` agents must not list `.agents/skills/` in their `skill_roots`.

## Manifest YAML Schema

```yaml
# .kittify/agent-surfaces/skills-manifest.yaml
spec_kitty_version: "2.1.0"
created_at: "2026-03-20T16:00:00Z"
updated_at: "2026-03-20T16:30:00Z"
skills_mode: "auto"
selected_agents:
  - claude
  - codex
  - opencode
installed_skill_roots:
  - ".agents/skills/"
  - ".claude/skills/"
managed_files:
  - path: ".agents/skills/.gitkeep"
    sha256: "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    file_type: "skill_root_marker"
  - path: ".claude/skills/.gitkeep"
    sha256: "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    file_type: "skill_root_marker"
  - path: ".claude/commands/spec-kitty.specify.md"
    sha256: "abc123..."
    file_type: "wrapper"
  - path: ".codex/prompts/spec-kitty.specify.prompt.md"
    sha256: "def456..."
    file_type: "wrapper"
```
