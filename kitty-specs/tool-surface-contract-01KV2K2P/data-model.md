# Data Model: ToolSurfaceContract -- Unified Tool Surface Registry

**Mission**: tool-surface-contract-01KV2K2P
**Date**: 2026-06-14

## Overview

The data model is entirely in-process (no database). All persistent state is in YAML/JSON files under `.kittify/` and the filesystem. The registry itself is a computed in-memory object built from built-in definitions and configuration.

## Enumerations

### SurfaceKind

Classifies what type of artifact a surface is. Use the full enum; do not collapse distinct kinds.

| Value | Meaning |
|-------|---------|
| `context_file` | Always-on orientation or context file (CLAUDE.md, AGENTS.md) |
| `rule` | Rules/steering file loaded by the tool (e.g., `.cursor/rules/*.mdc`) |
| `command_file` | Slash-command file written to a global command directory |
| `command_skill` | Slash-command invocation skill (`.agents/skills/spec-kitty.{cmd}/SKILL.md`) |
| `doctrine_skill` | Managed knowledge/mission-step skill surface |
| `workflow` | Workflow definition file (e.g., Windsurf/Kilocode `.workflows/`) |
| `agent_profile` | Host-native agent/subagent file projected from a Spec Kitty profile |
| `plugin_manifest` | Plugin bundle manifest for distribution/packaging |
| `mcp_server` | MCP server config entry (`.mcp.json` or equivalent) |
| `hook` | Tool hook entry (e.g., `.claude/settings.json` hook section) |
| `native_config` | Tool-specific config glue (vibe `skill_paths`, MCP config, etc.) |
| `memory` | Persistent memory file (tool-native memory store) |
| `setting` | Tool settings entry (e.g., VS Code `.vscode/settings.json` entry) |

> **Important**: `session_presence` is NOT a SurfaceKind. Session presence is a provider that expands into `context_file`, `hook`, and `rule` instances. This distinction matters for `--kind` filtering, docs validation, and plugin mapping.

### SourceKind

| Value | Meaning |
|-------|---------|
| `checked_in` | Committed to the repository; never generated |
| `generated` | Produced from a source; gitignored; repairable on demand |
| `user_global` | Lives in the user's home/global config |
| `team_global` | Team/org-managed global config |
| `package` | Bundled with Spec Kitty itself |
| `plugin` | Provided by a plugin bundle |
| `external_registry` | From an external plugin or package registry |

### InstallScope

| Value | Meaning |
|-------|---------|
| `project` | Installed into the current repository |
| `user_global` | Installed into the user's home/global config |
| `team` | Team/org-managed install |
| `plugin_bundle` | Staged into a plugin package root (not a project install) |

### ActivationMode

| Value | Meaning |
|-------|---------|
| `always` | Loaded unconditionally at session start |
| `glob` | Activated by file path matching |
| `model_decision` | Activated by the model's autonomous decision |
| `manual` | Requires explicit user invocation |
| `user_invoked` | User types the slash command |
| `skills_invocable` | Invocable via the skills protocol |
| `event` | Triggered by a tool lifecycle event |
| `disabled` | Known but explicitly inactive |

### MutabilityPolicy

| Value | Meaning |
|-------|---------|
| `generated_overwrite_if_hash_matches` | Safe to overwrite if on-disk hash matches manifest hash |
| `preserve_user_edits` | Do not overwrite; user edits are canonical |
| `user_editable` | User may edit; repair regenerates from source |
| `read_only_package` | Owned by a package; never mutate directly |

### RequiredPolicy

| Value | Meaning |
|-------|---------|
| `required` | Must exist; absence is a hard failure |
| `repairable_required` | Must exist; absence is a finding with a repair command |
| `optional` | May exist; absence is not reported |
| `research_gap` | Known gap; absence produces a `research-gap-surface` finding, not a failure |

## Stable Finding Codes

Finding codes are kebab-case strings. They are stable across releases: a code that has appeared in any released version of `doctor tool-surfaces --json` cannot be renamed or removed without a deprecation cycle.

| Code | Meaning |
|------|---------|
| `configured-tool-unknown` | Config references unsupported harness key |
| `surface-provider-missing` | Registry entry has no provider |
| `generated-surface-missing` | Generated file expected by contract is absent |
| `managed-file-drift` | Manifest hash differs from on-disk bytes |
| `managed-file-modified` | Provider refuses mutation due to user edits |
| `unsafe-managed-path` | Path escapes root or uses unsafe symlink |
| `unmanaged-spec-kitty-surface` | Spec-kitty-looking file not owned by manifest |
| `stale-generated-surface` | Old canonical command/skill still manifest-owned |
| `configured-tool-surface-uninstalled` | Tool configured but install manifest has no entries for its required surface |
| `native-config-missing` | Required glue config entry is absent |
| `native-config-drift` | Glue config entry differs from expected value |
| `native-agent-profile-missing` | Generated native agent profile file is absent |
| `native-agent-profile-drift` | Generated native agent profile differs from manifest hash/source projection |
| `profile-source-invalid` | Canonical profile YAML fails schema or repository validation |
| `profile-projection-unsupported` | Configured tool has no verified native profile target |
| `profile-name-invalid` | Profile ID/name is invalid for target native format |
| `profile-overlay-conflict` | Overlay profile resolution is ambiguous or unsafe |
| `profile-sentinel-skipped` | Sentinel/internal profile intentionally not projected |
| `context-file-missing` | Required always-on context surface absent |
| `session-presence-incomplete` | Context file or hook entry missing for session presence |
| `research-gap-surface` | Harness has no known implementation for this surface kind |
| `docs-ref-stale` | Docs reference a path not in the contract |
| `plugin-manifest-stale-path` | Plugin manifest lists a component path that is absent |
| `plugin-skill-name-invalid` | Plugin skill name violates host naming requirements |
| `bundle-component-missing` | Bundle should include a component but projection omitted it |
| `tool-api-assumption-mismatch` | Skill references an unavailable host tool capability |
| `trust-unverified` | External package lacks trust metadata |

## Core Data Structures

### ManifestRef

Reference from a SurfaceDefinition to the manifest that tracks its installation state.

| Field | Type | Description |
|-------|------|-------------|
| `id` | `str` | Stable manifest identifier |
| `path` | `str` | Path relative to project root |
| `owner` | `str` | Python module that owns this manifest |
| `schema_version` | `int` | Manifest schema version |
| `manifest_kind` | `str` | Type of manifest (e.g., `hash_refcount`) |

### InvocationSpec

How the tool invokes this surface.

| Field | Type | Description |
|-------|------|-------------|
| `pattern` | `str \| None` | Invocation pattern (e.g., `$spec-kitty.{command}`, `/spec-kitty.plan`) |
| `examples` | `tuple[str, ...]` | Example invocations |
| `command_surface` | `CommandSurfaceCapability` | Whether this is an adapter, skills-invocable, or none |
| `argument_delivery` | `str \| None` | How arguments are passed to the surface |

### ProfileProjectionSpec

How a surface produces native agent profile files.

| Field | Type | Description |
|-------|------|-------------|
| `source_layers` | `tuple[str, ...]` | Which profile layers to project: `builtin`, `org`, `project` |
| `native_format` | `str` | Target format: `claude-agent`, `claude-plugin-agent`, `copilot-agent`, `vscode-agent`, `generic-markdown` |
| `path_template` | `str` | Path template for output files (e.g., `.claude/agents/{profile_id}.md`) |
| `include_sentinel_profiles` | `bool` | Whether to project internal/sentinel profiles |
| `name_template` | `str` | Template for the native agent name (default: `{profile_id}`) |

### SurfaceDefinition

Abstract contract entry: the policy for what a surface should be.

| Field | Type | Description |
|-------|------|-------------|
| `id` | `str` | Stable unique identifier (e.g., `codex.command_skills`) |
| `tool_key` | `str` | Which tool harness this definition belongs to |
| `variant` | `str` | Harness variant (e.g., `default`, `plugin`, `user-global`) |
| `kind` | `SurfaceKind` | What type of artifact this is |
| `provider` | `str` | Which SurfaceProvider handles this surface kind |
| `source_kind` | `SourceKind` | How the artifact is produced |
| `install_scope` | `InstallScope` | Where it lives |
| `activation` | `ActivationMode` | How the tool activates this surface |
| `required` | `RequiredPolicy` | Whether absence is an error, repairable gap, or optional |
| `path_template` | `str \| None` | Template path pattern (e.g., `.agents/skills/spec-kitty.{command}/SKILL.md`) |
| `expected_set` | `str \| None` | Named set of expected instances (e.g., `canonical_commands`) |
| `manifest` | `ManifestRef \| None` | Reference to the manifest tracking installation state |
| `invocation` | `InvocationSpec \| None` | How the tool invokes this surface |
| `profile_projection` | `ProfileProjectionSpec \| None` | Profile projection spec (agent_profile kinds only) |
| `mutability` | `MutabilityPolicy` | Whether the file may be overwritten on repair |
| `package_id` | `str` | Package that owns this surface definition (e.g., `spec-kitty-core`) |
| `projection_id` | `str` | Stable projection group identifier |
| `docs_refs` | `tuple[str, ...]` | Doc files that may reference this surface path |
| `test_refs` | `tuple[str, ...]` | Test files that verify this surface |
| `depends_on` | `tuple[str, ...]` | Surface IDs that must exist before this one |
| `plugin_components` | `tuple[str, ...]` | Plugin component types this surface contributes (e.g., `skill`, `agent`, `hook`) |

### SurfaceInstance

One concrete artifact on disk.

| Field | Type | Description |
|-------|------|-------------|
| `definition_id` | `str` | ID of the SurfaceDefinition this instance satisfies |
| `tool_key` | `str` | Tool harness this instance belongs to |
| `variant` | `str` | Harness variant |
| `kind` | `SurfaceKind` | Surface kind of this instance |
| `path` | `str \| None` | Path relative to project root (or absolute for user-global) |
| `manifest_path` | `str \| None` | Path of the manifest that tracks this instance |
| `owner_key` | `str` | Provider key that owns this instance |
| `source_kind` | `SourceKind` | How this instance is produced |
| `install_scope` | `InstallScope` | Scope of this installation |
| `required` | `RequiredPolicy` | Required policy from the definition |
| `expected_hash` | `str \| None` | SHA-256 expected by manifest (None if not tracked) |
| `metadata` | `Mapping[str, object]` | Provider-specific metadata |

### SurfaceStatus

Result of probing one SurfaceInstance against actual on-disk state.

| Field | Type | Description |
|-------|------|-------------|
| `instance` | `SurfaceInstance` | The instance that was probed |
| `state` | `str` | One of: `present`, `missing`, `drifted`, `stale`, `orphaned`, `unsafe`, `unsupported`, `not_applicable` |
| `findings` | `tuple[SurfaceFinding, ...]` | Zero or more findings for this instance |

### SurfaceFinding

A single finding from probing actual state vs. planned state.

| Field | Type | Description |
|-------|------|-------------|
| `code` | `str` | Stable finding code (see Finding Codes table above) |
| `severity` | `str` | `error`, `warning`, or `info` |
| `message` | `str` | Human-readable explanation |
| `tool_key` | `str \| None` | The configured tool this finding relates to |
| `surface_id` | `str \| None` | The SurfaceDefinition ID this finding relates to |
| `path` | `str \| None` | The affected file or directory path |
| `repair_command` | `str \| None` | The CLI command that resolves this finding |
| `docs_ref` | `str \| None` | Relevant documentation URL or path |
| `details` | `Mapping[str, object]` | Provider-specific structured detail |

### SurfacePlan

The computed set of surface instances that should exist for configured tools.

| Field | Type | Description |
|-------|------|-------------|
| `config` | `AgentConfig` | The resolved agent configuration |
| `definitions` | `tuple[SurfaceDefinition, ...]` | All definitions applicable to this config |
| `instances` | `tuple[SurfaceInstance, ...]` | All expanded instances |

### SurfaceReport

The output of `SurfaceStatusService.collect()`.

| Field | Type | Description |
|-------|------|-------------|
| `ok` | `bool` | True when no error-severity findings |
| `schema_version` | `int` | Schema version of this report (currently `1`) |
| `project_root` | `str` | Absolute path to the project root |
| `configured_tools` | `list[str]` | Tool keys from config |
| `summary` | `SurfaceSummary` | Aggregate counts |
| `surfaces` | `list[SurfaceStatus]` | Per-instance probe results |
| `findings` | `list[SurfaceFinding]` | All findings across all surfaces |

### SurfaceSummary

| Field | Type | Description |
|-------|------|-------------|
| `surfaces` | `int` | Total number of surface instances checked |
| `present` | `int` | Instances with state `present` |
| `missing` | `int` | Instances with state `missing` |
| `drifted` | `int` | Instances with state `drifted` |
| `warnings` | `int` | Finding count at `warning` severity |
| `errors` | `int` | Finding count at `error` severity |

### RepairResult

Returned by `SurfaceRepairService.repair()`.

| Field | Type | Description |
|-------|------|-------------|
| `repaired` | `list[str]` | Surface IDs successfully repaired |
| `skipped` | `list[str]` | Surface IDs skipped (e.g., user edits preserved) |
| `failed` | `list[str]` | Surface IDs where repair failed |
| `dry_run` | `bool` | Whether this was a dry-run (no mutations made) |
| `findings_after` | `list[SurfaceFinding]` | Remaining findings after repair (empty on full success) |

## ToolHarness

| Field | Type | Description |
|-------|------|-------------|
| `key` | `str` | Stable machine identifier (e.g., `codex`, `claude`) |
| `display_name` | `str` | Human-readable name |
| `variants` | `tuple[str, ...]` | Supported variants (default: `("default",)`) |
| `supported` | `bool` | Whether this harness is fully supported |
| `docs_url` | `str \| None` | Documentation URL |
| `requires_cli` | `bool` | Whether a CLI tool must be installed |
| `product_family` | `str \| None` | Optional product family grouping |

## Manifest Files (Installation State)

These files are not policy; they are snapshots of installation state. The registry is policy.

| File | Owner | Contents |
|------|-------|---------|
| `.kittify/command-skills-manifest.json` | `command_installer` (existing) | Installed command skill files, hashes, owners |
| `.kittify/skills-manifest.json` | `skills/installer` (existing) | Installed doctrine skill files, hashes, owners |
| `.kittify/agent-profiles-manifest.json` | NEW: `profiles/manifest.py` | Projected native agent profile files, hashes, owners |

## State Transitions

The ToolSurfaceContract bounded context is stateless at the registry level. State transitions apply only to manifests:

```
[absent] --repair--> [installed] --hash-check--> [hash-matches | hash-mismatch]
                                                          |
                                               [hash-mismatch] --repair--> [installed]
```

`SurfaceRepairService.repair()` MUST operate on provider-owned `SurfaceStatus` objects, not reconstruct `SurfaceInstance` from `SurfaceFinding`. This preserves manifest/source/hash/refcount context.

## Invariants

1. **Registry is policy; manifests are state.** A surface in the manifest but absent from the registry is orphaned (not an error, but not managed). A surface in the registry but absent from the manifest is a repairable gap.
2. **Finding codes are immutable once published.** Codes that have appeared in any released version of `doctor tool-surfaces --json` cannot be renamed or removed without a deprecation cycle. Codes are kebab-case, not SCREAMING_SNAKE.
3. **Provider wrapping preserves installer invariants.** No provider may bypass the ref-count, hash-check, or shared-root safety logic of the underlying installer.
4. **Existing manifests remain valid after the registry is introduced.** No migration step rewrites or invalidates existing `.kittify/command-skills-manifest.json` or `.kittify/skills-manifest.json` content.
5. **`doctor skills --json` output is frozen.** `doctor skills` delegates to `doctor tool-surfaces --kind command-skill --kind command-file` internally; its JSON output structure must not change.
6. **`session_presence` is a provider, not a SurfaceKind.** It expands into `context_file`, `hook`, and `rule` SurfaceKind instances depending on the harness.
7. **Repair operates on SurfaceStatus objects.** Never reconstruct SurfaceInstance from SurfaceFinding for repair; doing so loses manifest/source/hash/refcount context.
