# Implementation Plan: ToolSurfaceContract -- Unified Tool Surface Registry

**Branch**: `feat/tool-surface-contract` | **Date**: 2026-06-14 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `kitty-specs/tool-surface-contract-01KV2K2P/spec.md`
**Parent epic**: #1945 | **Glossary PR**: #1935 (prerequisite)

## Summary

Introduce a new `tool_surface` bounded context in `src/specify_cli/tool_surface/` that acts as the single authoritative registry for what surfaces (command skills, doctrine skills, session presence, native agent profiles, plugin bundle artifacts) should exist for each configured tool. Existing installers are wrapped as providers -- their core logic is preserved. The registry powers a new `spec-kitty doctor tool-surfaces --json` command with stable finding codes and repair commands, while keeping `doctor skills --json` and `spec-kitty agent config` fully backward-compatible. Nine sequenced work packages correspond to the nine child issues (#1936, #1944, #1937-#1943).

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: typer (CLI), rich (console output), ruamel.yaml (YAML/frontmatter), mypy (type checking, strict mode), pytest (testing)
**Storage**: File-based -- `.kittify/config.yaml` (configured tools), `.kittify/command-skills-manifest.json` (command-skill install state), `.kittify/skills-manifest.json` (doctrine-skill install state); no relational database
**Testing**: pytest with >= 90% line coverage for new code; mypy --strict with zero warnings; integration tests for all CLI commands added or modified; focused unit tests per provider; regression tests for `doctor skills --json` schema
**Target Platform**: Linux, macOS, Windows 10+ (cross-platform CLI tool)
**Project Type**: Single Python package (`src/specify_cli/`)
**Performance Goals**: `doctor tool-surfaces --json` completes in <= 5 seconds for a project with up to 19 configured tools on a standard developer workstation
**Constraints**: Zero breaking changes to `doctor skills --json` output schema; `spec-kitty agent config list/status/sync` external interface unchanged; existing `.kittify/config.yaml` `agents.available` entries require no manual migration; naming convention `ToolSurfaceContract` (not `AgentSurfaceContract`) non-negotiable; gitignore policy for generated files unchanged
**Scale/Scope**: 19 supported tool harnesses, 9 work packages, 5 surface kinds (command skills, doctrine skills, session presence, native agent profiles, plugin bundle artifacts)

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Cross-platform (DIR-001)**: All file path operations must use `pathlib.Path`; no hardcoded separators. Provider wrappers must inherit this from existing installers. ✓ Required.
- **Python 3.11+ (DIR-002)**: New bounded context must use 3.11+ features (StrEnum, dataclasses, match/case where appropriate). ✓ Required.
- **Git required (DIR-003)**: No new git dependencies introduced -- this bounded context operates on the filesystem and config files only. ✓ N/A.
- **Tests (DIR-005)**: Every new module in `tool_surface/` needs focused unit tests. Every new CLI command needs integration tests. Migration compat fixtures (IC-02/WP02) must be in place before any user-visible provider work merges. ✓ Required.
- **Type annotations (DIR-006)**: mypy --strict must pass with zero warnings across all new code. ✓ Required.
- **Breaking changes (DIR-009)**: `doctor skills --json` and `agent config` interfaces are existing public CLI surfaces -- any change requires CHANGELOG entry and backward-compatibility guarantee. ✓ Required.
- **Terminology (C-003, C-005)**: `ToolSurfaceContract`, not `AgentSurfaceContract`; Tool vs. Agent distinction maintained throughout. ✓ Non-negotiable gate.
- **Sonar complexity ceiling**: All new functions must remain at cyclomatic complexity <= 15. Registry expansion, plan building, and provider dispatch are at risk -- extract helpers if needed. ✓ Watch.
- **God-module constraint (C-001)**: No new logic in `core.config`, `agent.config`, or `doctor.py`. New bounded context only. ✓ Hard constraint.

*Post-Phase 1 re-check*: SurfacePlan builder and PluginBundle provider are the highest-risk complexity points. If either exceeds complexity 15 during design, extract subcomponents before WP.

## Project Structure

### Documentation (this mission)

```
kitty-specs/tool-surface-contract-01KV2K2P/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── contracts/
│   └── doctor-tool-surfaces-output.schema.json   # Phase 1 output
├── quickstart.md        # Phase 1 output
└── tasks.md             # Phase 2 output (/spec-kitty.tasks)
```

### Source Code (repository root)

```
src/specify_cli/tool_surface/           # NEW bounded context
    __init__.py
    enums.py                            # SurfaceKind, SourceKind, InstallScope, ActivationMode,
                                        # CommandSurfaceCapability, MutabilityPolicy, RequiredPolicy
    model.py                            # SurfaceDefinition, SurfaceInstance, SurfacePlan,
                                        # SurfaceStatus, SurfaceFinding dataclasses
    registry.py                         # ToolSurfaceRegistry -- loads builtins + provider registrations
    builtins.py                         # Built-in surface definitions for all 19 harnesses
    plan.py                             # SurfacePlanBuilder -- computes plan from config + registry
    status.py                           # SurfaceStatusService -- probes current state vs plan
    findings.py                         # FindingCode constants + finding factory
    repair.py                           # SurfaceRepairService -- repairs provider-owned SurfaceStatus objects
    docs.py                             # DocsLinter -- validates doc paths against registry

    providers/
        __init__.py
        base.py                         # AbstractSurfaceProvider protocol
        command_skills.py               # Wraps specify_cli.skills.command_installer
        managed_skills.py               # Wraps specify_cli.skills.installer, verifier, registry
        agent_profiles.py               # Wraps doctrine.agent_profiles + profile projection
        slash_commands.py               # Wraps AGENT_COMMAND_CONFIG, runtime.agent_commands, _load_slash_command_state()
        session_presence.py             # Wraps specify_cli.session_presence.writers.registry
        native_config.py                # Wraps tool-specific config helpers (vibe_config, etc.)
        plugin_bundle.py                # New: projects surfaces into plugin package layouts

    profiles/
        __init__.py
        projection.py                   # Projects Spec Kitty agent profiles -> host-native formats
        renderers.py                    # Per-harness render functions (Claude Code, Codex, etc.)
        manifest.py                     # Tracks projected profile files (hash, owner, repair)

    bundles/
        __init__.py
        model.py                        # PluginBundle dataclass + validation result
        claude.py                       # Claude Code plugin bundle projection
        copilot.py                      # GitHub Copilot plugin bundle projection
        vscode.py                       # VS Code extension bundle projection

    data/
        tool-surface-contract.schema.json   # JSON Schema for registry entries (owned by WP01/IC-01)
        surface-status.schema.json          # JSON Schema for doctor output (owned by WP01/IC-01)

src/specify_cli/cli/commands/doctor.py  # MODIFIED: add `tool-surfaces` subcommand
src/specify_cli/cli/commands/agent/
    config.py                           # MODIFIED (WP07/IC-07): route through SurfacePlan

tests/specify_cli/tool_surface/
    __init__.py
    test_enums.py
    test_model.py
    test_registry.py
    test_plan.py
    test_status.py
    test_findings.py
    test_repair.py
    test_docs.py
    providers/
        test_command_skills.py
        test_managed_skills.py
        test_agent_profiles.py
        test_session_presence.py
        test_plugin_bundle.py
    profiles/
        test_projection.py
        test_renderers.py
        test_manifest.py
    integration/
        test_doctor_tool_surfaces_cli.py    # CLI integration: --json output, --kind filtering, --fix
        test_migration_compat.py            # Regression: doctor skills --json unchanged
        test_agent_config_compat.py         # Regression: agent config unchanged
```

**Structure Decision**: Single project layout under `src/specify_cli/`. The new `tool_surface/` package is a self-contained bounded context. It imports from `specify_cli.skills`, `specify_cli.session_presence`, `specify_cli.runtime`, and `src/doctrine/agent_profiles` but does not move or modify those modules.

## Complexity Tracking

No charter gate violations.

## Implementation Concern Map

The nine implementation concerns correspond exactly to the nine child issues, in the mandatory sequence from C-008.

### IC-01 -- Registry Skeleton and Glossary-Compliant Naming (#1936)

- **Purpose**: Introduce `src/specify_cli/tool_surface/` with enums, dataclasses, and a registry stub that defines the vocabulary and type boundaries without changing any runtime behavior.
- **Relevant requirements**: FR-001, FR-018, C-001, C-003, C-005
- **Affected surfaces**: `src/specify_cli/tool_surface/__init__.py`, `enums.py`, `model.py`, `registry.py`, `builtins.py` (stubs), `providers/base.py`; `tests/specify_cli/tool_surface/test_enums.py`, `test_model.py`, `test_registry.py`
- **Sequencing/depends-on**: none (first work package)
- **Risks**: Glossary PR #1935 must be merged or its terminology respected before naming is finalized. Any name introduced here propagates through all subsequent ICs.

### IC-02 -- Migration and Compatibility Gate (#1944)

- **Purpose**: Define and implement the user-facing migration path as a compatibility rollout; establish test fixtures that all subsequent provider ICs must pass before merging.
- **Relevant requirements**: FR-007, FR-008, FR-009, FR-011, NFR-004
- **Affected surfaces**: `tests/specify_cli/tool_surface/integration/test_migration_compat.py`, `test_agent_config_compat.py`; migration fixtures asserting `doctor skills --json` schema and `agent config` interface are unchanged
- **Sequencing/depends-on**: IC-01 (needs registry stubs to exist)
- **Risks**: This IC functions as a gate: no subsequent IC may merge if its migration fixtures fail. Must be completed before any user-visible provider work (IC-03 onward).

### IC-03 -- Command-Skill Provider and `doctor tool-surfaces` (#1937)

- **Purpose**: Route command-skill status through the provider model and add the first umbrella doctor command (`doctor tool-surfaces --kind command-skill --json` and `--fix`).
- **Relevant requirements**: FR-001, FR-002, FR-003, FR-004, FR-005, FR-006, FR-010
- **Affected surfaces**: `providers/command_skills.py`, `providers/slash_commands.py`; `plan.py` (first real surface plan); `status.py`, `findings.py`, `repair.py`; `src/specify_cli/cli/commands/doctor.py`; integration tests
- **Backward compatibility note**: `doctor skills` must continue to work. Its behavior maps to `doctor tool-surfaces --kind command-skill --kind command-file`. The doctor.py wiring for `doctor skills` must delegate to the new `doctor tool-surfaces` implementation filtered by those two kinds.
- **Sequencing/depends-on**: IC-01, IC-02
- **Risks**: Finding codes established here become the public API -- they must follow the stable-code contract from day one. `doctor tool-surfaces` with no `--kind` flag must not break if later kinds are not yet implemented.

### IC-04 -- Session-Presence Provider (#1938)

- **Purpose**: Add a provider for session presence and context/hook surfaces, making the distinction between session presence and command-skill install state explicit in doctor output.
- **Relevant requirements**: FR-003, FR-006, FR-010, FR-018, NFR-001
- **Affected surfaces**: `providers/session_presence.py`; `providers/native_config.py` (partial -- hooks and tool-specific glue); `status.py` (extend for `context_file`, `hook`, and `rule` kinds emitted by the session-presence provider); finding codes for session-presence gaps
- **Sequencing/depends-on**: IC-01, IC-02, IC-03
- **Risks**: Session presence paths differ per harness (CLAUDE.md vs. AGENTS.md vs. rules files). Provider must not assume a fixed path.

### IC-05 -- Managed Doctrine Skill Provider (#1939)

- **Purpose**: Add a provider for managed doctrine skills, clearly separating them from command skills in doctor output and status.
- **Relevant requirements**: FR-003, FR-006, FR-010, FR-018
- **Affected surfaces**: `providers/managed_skills.py`; wraps `specify_cli.skills.registry`, `specify_cli.skills.installer`, `specify_cli.skills.verifier`; new finding codes for doctrine-skill gaps; integration tests
- **Sequencing/depends-on**: IC-01, IC-02, IC-03
- **Risks**: The managed doctrine skill verifier already has its own reporting; the provider wrapper must not duplicate that logic or change its behavior.

### IC-06 -- Native Agent Profile Projection (#1940)

- **Purpose**: Project built-in Spec Kitty profiles and org/project overlay profiles into host-native agent/subagent formats, tracked in a manifest and covered by `doctor tool-surfaces`.
- **Relevant requirements**: FR-012, FR-013, FR-014
- **Affected surfaces**: `providers/agent_profiles.py`; `profiles/projection.py`, `profiles/renderers.py`, `profiles/manifest.py`; finding codes for projection gaps; tools that do not support named agents get `RESEARCH_GAP` code
- **Sequencing/depends-on**: IC-01, IC-02, IC-03
- **Risks**: Host-native formats differ significantly per harness (Claude Code `.claude/agents/`, Codex `AGENTS.md` hints, etc.). Renderers must be isolated per harness and guarded by feature-detection logic.
- **Native projection targets for IC-06** (confirmed from architecture research):

  | Target | Path | Format | Scope |
  |--------|------|--------|-------|
  | Claude Code project/user | `.claude/agents/<profile-id>.md` | `claude-agent` (Markdown frontmatter + body) | `PROJECT` or `USER_GLOBAL` |
  | Claude plugin bundle | `agents/<profile-id>.md` | `claude-plugin-agent` | `PLUGIN_BUNDLE` |
  | Copilot CLI | `.github/agents/<profile-id>.agent.md` or `~/.copilot/agents/<profile-id>.agent.md` | `copilot-agent` (`.agent.md` frontmatter + instructions) | `PROJECT` or `USER_GLOBAL` |
  | VS Code | `.github/agents/<profile-id>.agent.md` | `vscode-agent` | `PROJECT` |
  | Codex | No verified native profile primitive | → `research-gap-surface` finding; keep `ad-hoc-profile-load` fallback | N/A |

  Do NOT model Codex AGENTS.md hints as native profiles — AGENTS.md is a `context_file` surface (session presence), not an agent profile projection.

  Renderers for Claude, Copilot, and VS Code must be implemented in `profiles/renderers.py` by IC-06. Each renderer is an isolated function with stable inputs/outputs. Profile manifest: `.kittify/agent-profiles-manifest.json`.

### IC-07 -- Legacy Agent Config Refactor (#1941)

- **Purpose**: Refactor `spec-kitty agent config list/status/sync` to consume `SurfacePlan` internally, removing the duplicated recomputation logic while preserving the external interface unchanged.
- **Relevant requirements**: FR-008, NFR-004
- **Affected surfaces**: `src/specify_cli/cli/commands/agent/config.py`; `tests/specify_cli/cli/commands/test_agent_config.py`; IC-02 migration fixtures must still pass
- **Sequencing/depends-on**: IC-01, IC-02, IC-03 (needs a working SurfacePlan to route through)
- **Risks**: `agent config` has subtly different status semantics from `doctor tool-surfaces`; the refactor must preserve those semantics exactly. Any divergence is a regression.

### IC-08 -- Docs Contract Lint (#1942)

- **Purpose**: Add validation so docs that reference generated/native tool surface paths cannot drift from the ToolSurfaceContract registry; a lint step fails on any mismatch.
- **Relevant requirements**: FR-016, FR-017
- **Affected surfaces**: `docs.py` (DocsLinter); relevant doc files (`docs/host-surface-parity.md`, etc.); CI lint integration; tests
- **Sequencing/depends-on**: IC-01 through IC-06 (all surface kinds must be registered before doc coverage can be validated)
- **Risks**: Docs may reference paths not yet defined in later ICs; the linter must be configurable to exclude known `RESEARCH_GAP` surfaces from hard failures.

### IC-09 -- Plugin Bundle Projection and Validation (#1943)

- **Purpose**: Add plugin bundle projection and pre-publish validation as a release/staging capability, grouping canonical surfaces into a plugin package layout for distribution.
- **Relevant requirements**: FR-015, FR-016
- **Affected surfaces**: `providers/plugin_bundle.py`; `bundles/model.py`, `bundles/claude.py`, `bundles/copilot.py`, `bundles/vscode.py`; validation report schema; tests
- **Sequencing/depends-on**: IC-01 through IC-06 (all surface kinds must be registered so the bundle can include them)
- **Risks**: Plugin bundle format differs per distribution target (Claude Code plugin manifest, VS Code extension manifest, etc.). Projection must be format-aware. No auto-install logic may be introduced.
