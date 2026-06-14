# Data Model: ToolSurfaceContract -- Unified Tool Surface Registry

**Mission**: tool-surface-contract-01KV2K2P
**Date**: 2026-06-14

## Overview

The data model is entirely in-process (no database). All persistent state is in YAML/JSON files under `.kittify/` and the filesystem. The registry itself is a computed in-memory object built from built-in definitions and configuration.

## Enumerations

### SurfaceKind

Classifies what type of artifact a surface is.

| Value | Meaning |
|-------|---------|
| `command_skill` | Slash-command invocation skill (e.g., `.agents/skills/spec-kitty.plan/SKILL.md`) |
| `doctrine_skill` | Managed knowledge/mission-step surface |
| `session_presence` | Always-on context or orientation file (CLAUDE.md, AGENTS.md, rules files) |
| `agent_profile` | Host-native agent/subagent file projected from a Spec Kitty profile |
| `plugin_manifest` | Plugin bundle artifact for distribution/packaging |
| `native_config` | Tool-specific config glue (hooks, MCP config, vibe path config) |
| `command_file` | Slash-command file (legacy; distinct from command_skill) |

### SourceKind

Classifies where a surface originates.

| Value | Meaning |
|-------|---------|
| `checked_in` | Committed to the repository; never generated |
| `generated` | Produced from a source; gitignored; repairable on demand |
| `user_global` | Lives in the user's home/global config |
| `package` | Bundled with Spec Kitty itself |
| `plugin` | Provided by a plugin bundle |

### RequiredPolicy

| Value | Meaning |
|-------|---------|
| `required` | Must exist; absence is a hard failure |
| `repairable_required` | Must exist; absence is a finding with a repair command |
| `optional` | May exist; absence is not reported |
| `research_gap` | Known gap; absence produces a RESEARCH_GAP finding code, not a failure |

### FindingCode (stable constants)

| Code | Surface kind | Meaning |
|------|-------------|---------|
| `TOOL_SURFACE_COMMAND_SKILL_MISSING` | `command_skill` | Command skill directory or SKILL.md absent |
| `TOOL_SURFACE_COMMAND_SKILL_HASH_MISMATCH` | `command_skill` | Installed file hash differs from expected |
| `TOOL_SURFACE_DOCTRINE_SKILL_MISSING` | `doctrine_skill` | Doctrine skill absent |
| `TOOL_SURFACE_SESSION_PRESENCE_MISSING` | `session_presence` | Required orientation/context file absent |
| `TOOL_SURFACE_AGENT_PROFILE_MISSING` | `agent_profile` | Native agent profile projection absent |
| `TOOL_SURFACE_AGENT_PROFILE_RESEARCH_GAP` | `agent_profile` | Tool does not support native named agents |
| `TOOL_SURFACE_PLUGIN_BUNDLE_INCOMPLETE` | `plugin_manifest` | Bundle missing required surface projections |
| `TOOL_SURFACE_DOCS_PATH_DRIFT` | n/a | Doc file references a path not in the registry |

All codes are stable across releases. Codes are not renamed or removed without a deprecation cycle.

## Core Data Structures

### SurfaceDefinition

Abstract contract entry: what a surface is supposed to be (policy).

| Field | Type | Description |
|-------|------|-------------|
| `kind` | `SurfaceKind` | What type of artifact this is |
| `source_kind` | `SourceKind` | How the artifact is produced |
| `install_scope` | `InstallScope` | Where it lives (project, user-global, plugin-bundle) |
| `path_pattern` | `str` | Template path pattern (e.g., `.agents/skills/spec-kitty.{command}/SKILL.md`) |
| `required_policy` | `RequiredPolicy` | Whether absence is an error, a repairable gap, or optional |
| `activation_mode` | `ActivationMode` | How the tool activates this surface |
| `provider_key` | `str` | Which SurfaceProvider handles this surface kind |
| `repair_hint` | `str` | Human-readable repair description |

### SurfaceInstance

One concrete artifact on disk (installation state).

| Field | Type | Description |
|-------|------|-------------|
| `definition` | `SurfaceDefinition` | The contract entry this instance satisfies |
| `path` | `Path` | Absolute path to the artifact |
| `exists` | `bool` | Whether the file/directory is present |
| `hash` | `str \| None` | SHA-256 of the file content (if present and hashable) |
| `owner` | `str` | Which installer/provider wrote this file |

### SurfacePlan

The computed set of surface instances that should exist for the currently configured tools.

| Field | Type | Description |
|-------|------|-------------|
| `tool_key` | `str` | Configured tool identifier (e.g., `codex`, `claude`) |
| `instances` | `list[SurfaceInstance]` | All surfaces that should exist for this tool |
| `computed_at` | `str` | ISO timestamp |

### SurfaceFinding

A single finding from probing actual state vs. planned state.

| Field | Type | Description |
|-------|------|-------------|
| `code` | `str` | Stable finding code (see FindingCode constants) |
| `tool_key` | `str` | The configured tool this finding relates to |
| `surface_kind` | `SurfaceKind` | The surface kind affected |
| `path` | `Path \| None` | The affected file or directory path |
| `repair_command` | `str \| None` | The CLI command that resolves this finding |
| `detail` | `str` | Human-readable explanation |

### NativeAgentProfile

A host-native agent/subagent file projected from a Spec Kitty profile.

| Field | Type | Description |
|-------|------|-------------|
| `profile_urn` | `str` | Canonical URN of the source profile (e.g., `urn:profile:architect-alphonso`) |
| `source_layer` | `str` | `builtin`, `org`, or `project` |
| `tool_key` | `str` | Target tool harness |
| `output_path` | `Path` | Where the native file is written |
| `format` | `str` | Native format key (e.g., `claude_code_agent_md`, `codex_agents_md_hint`) |
| `hash` | `str \| None` | Hash of the projected file (for manifest tracking) |

### PluginBundle

A release/staging artifact grouping projected surfaces.

| Field | Type | Description |
|-------|------|-------------|
| `distribution_target` | `str` | Bundle format (e.g., `claude_code_plugin`, `vscode_extension`) |
| `surfaces` | `list[SurfaceInstance]` | The surfaces included in this bundle |
| `validation_result` | `BundleValidationResult` | Whether all required surfaces are present |

### BundleValidationResult

| Field | Type | Description |
|-------|------|-------------|
| `passed` | `bool` | Whether the bundle is complete and valid |
| `missing_surfaces` | `list[SurfaceFinding]` | Any gaps in the bundle |
| `warnings` | `list[str]` | Non-blocking issues |

## Manifest Files (Installation State)

These files are not policy; they are snapshots of installation state. The registry is policy.

| File | Owner | Contents |
|------|-------|---------|
| `.kittify/command-skills-manifest.json` | `command_installer` (existing) | Installed command skill files, hashes, owners |
| `.kittify/skills-manifest.json` | `skills/installer` (existing) | Installed doctrine skill files, hashes, owners |
| `.kittify/tool-surface-profile-manifest.json` | NEW: `profiles/manifest.py` | Projected native agent profile files, hashes, owners |

## State Transitions

The ToolSurfaceContract bounded context is stateless at the registry level. State transitions apply only to manifests:

```
[absent] --repair--> [installed] --hash-check--> [hash-matches | hash-mismatch]
                                                          |
                                               [hash-mismatch] --repair--> [installed]
```

There are no approval workflows or multi-step state machines in this bounded context.

## Invariants

1. **Registry is policy; manifests are state.** A surface that is in the manifest but absent from the registry is orphaned (not an error, but not managed). A surface in the registry but absent from the manifest is a repairable gap.
2. **Finding codes are immutable once published.** A code that has appeared in any released version of `doctor tool-surfaces --json` cannot be renamed or removed without a deprecation cycle.
3. **Provider wrapping preserves installer invariants.** No provider may bypass the ref-count, hash-check, or shared-root safety logic of the underlying installer.
4. **Existing manifests remain valid after the registry is introduced.** No migration step rewrites or invalidates existing `.kittify/command-skills-manifest.json` or `.kittify/skills-manifest.json` content.
5. **`doctor skills --json` output is frozen.** The `SurfaceStatusService` for command skills must produce identical output to the pre-registry `doctor skills` command for all currently documented finding codes.
