# ToolSurfaceContract -- Unified Tool Surface Registry

**Parent epic:** #1945
**Glossary context:** PR #1935 (prerequisite)
**Mission ID:** 01KV2K2P989VGC1TZF43ATGCPC

## Overview

Spec Kitty supports 19 execution tools (Claude Code, Codex, Copilot, Cursor, Windsurf, and others), each requiring native artifacts: command skills, doctrine skills, session-presence files, native agent profile projections, and plugin bundle manifests. These surface kinds are currently verified by separate subsystems with no shared contract, causing impossible states after a fresh clone and no single place to answer "what should exist for this configured tool?"

This mission establishes a single authoritative registry -- the ToolSurfaceContract -- that owns that answer and powers unified install, verify, repair, and docs validation across all surface kinds.

## Problem Statement

When a contributor clones Spec Kitty with Codex configured:

- `.agents/skills/` is absent (gitignored generated directory)
- `doctor skills --json` reports 11 missing command skills
- Managed doctrine skill verification reports 75 missing doctrine skills
- Session presence, docs, and plugin bundle surfaces are each checked separately by different subsystems
- No single command shows the complete health of a configured tool's surfaces
- No stable finding codes exist that CI can gate on

The structural root cause: tool-surface policy is recomputed by multiple subsystems instead of owned by one contract.

## User Scenarios & Testing

### Scenario 1: Fresh-clone repair (primary scenario)

A new contributor clones the repo with Codex listed in `.kittify/config.yaml`. They run `spec-kitty doctor tool-surfaces --json` and receive a complete report: which surface kinds are missing, the stable finding code for each gap, and the exact repair command to run. After running repair, all surfaces are present and a second `doctor tool-surfaces` run reports `ok: true`.

**Edge case:** The repo has multiple tools configured. The report covers all configured tools and all surface kinds in one pass.

**Rule that must hold:** Repair commands must be runnable without any manual file editing.

### Scenario 2: CI pipeline gating

A CI pipeline runs `spec-kitty doctor tool-surfaces --json`. The output contains stable machine-readable finding codes, affected file paths, and suggested repair commands. The pipeline can fail on specific codes and suppress others by policy without parsing human-readable text.

### Scenario 3: Existing user -- no manual migration required

An existing user upgrades Spec Kitty. Their `.kittify/config.yaml` is unchanged. All `spec-kitty agent config list/status/sync` commands continue to work identically. `doctor skills --json` output is unchanged. No manual file edits are required.

**Rule that must hold:** The migration/compatibility layer (#1944) is an early implementation gate -- any provider work that could affect existing users must be gated on passing migration fixtures before that work merges.

### Scenario 4: Native agent profile selection

A user who has configured Claude Code, Copilot CLI, or VS Code opens the tool's native agent/subagent selector and finds "Architect Alphonso" and "Researcher Robbie" listed, along with any org or project overlay profiles. These were projected from Spec Kitty's canonical profile sources into host-native formats by the tool surface contract machinery. Projection targets and path formats:

- **Claude Code project/user**: `.claude/agents/<profile-id>.md` (Claude agent frontmatter + body)
- **Claude plugin**: `agents/<profile-id>.md` (Claude plugin agent format)
- **Copilot CLI**: `.github/agents/<profile-id>.agent.md` or `~/.copilot/agents/<profile-id>.agent.md`
- **VS Code**: `.github/agents/<profile-id>.agent.md` (auto-discovered by VS Code)
- **Codex**: no verified native profile primitive → `research-gap-surface` finding; keep `ad-hoc-profile-load` as fallback

`doctor tool-surfaces` verifies that projection files exist and are up to date.

### Scenario 5: Plugin bundle validation (staging/release only)

A release pipeline validates that the Spec Kitty plugin bundle contains correct projections of all canonical surfaces -- command skills, doctrine skills, session presence, native profiles -- before the bundle is published. The validation produces a machine-readable report. No auto-install, no marketplace push, and no replacement of project-local installation occurs.

### Scenario 6: Docs cannot silently drift from contract

A doc file references a generated skill path. A lint step validates that every documented generated/native path exists in the ToolSurfaceContract registry. If a path is renamed in the contract, the lint step fails, preventing stale documentation from shipping.

## Functional Requirements

| ID | Requirement | Status |
|----|-------------|--------|
| FR-001 | The system shall provide a single registry that, given a configured tool, returns the complete set of surfaces (command skills, doctrine skills, session presence, native agent profiles, plugin bundle artifacts) that should exist for that tool. | Proposed |
| FR-002 | The registry shall expose a machine-readable status command (`doctor tool-surfaces --json`) reporting all surface kinds with stable finding codes, affected paths, and repair commands. | Proposed |
| FR-003 | `doctor tool-surfaces --json` shall cover at minimum: command skills, slash-command file surfaces (`command_file`), doctrine skills, session presence (context files, hooks, rules), native agent profile projections, and plugin bundle surfaces. | Proposed |
| FR-004 | `doctor tool-surfaces --json` shall support filtering by surface kind (e.g., `--kind command-skill`). | Proposed |
| FR-005 | Finding codes in `doctor tool-surfaces --json` shall be stable across releases: the same code shall mean the same condition and shall not be renamed or removed without a documented deprecation cycle. | Proposed |
| FR-006 | Repair commands surfaced by `doctor tool-surfaces` shall be runnable without any manual file editing by the user. | Proposed |
| FR-007 | The existing `doctor skills --json` command shall remain backward-compatible: its finding codes, output schema, and behavior shall not change. | Proposed |
| FR-008 | The existing `spec-kitty agent config list/status/sync` commands shall continue to work with no change to their external interface. | Proposed |
| FR-009 | Existing `.kittify/config.yaml` `agents.available` entries shall require no manual migration on upgrade. | Proposed |
| FR-010 | The registry shall wrap existing command-skill, doctrine-skill, session-presence, and native-glue installers as providers without replacing their core logic (ref-counts, hash checks, shared-root safety). | Proposed |
| FR-011 | The migration/compatibility rollout (#1944) shall function as an early gate: any provider implementation that could affect existing users shall be blocked on passing migration/compatibility test fixtures before that work merges. | Proposed |
| FR-012 | The system shall project built-in Spec Kitty agent profiles and org/project overlay profiles into host-native agent/subagent formats for each configured tool that supports named agents. | Proposed |
| FR-013 | Native agent profile projections shall receive the same source/generated/manifest/doctor treatment as command skills: tracked in a manifest, repairable by a repair command, checked by `doctor tool-surfaces`. | Proposed |
| FR-014 | Tools that do not support named agents natively shall receive a stable `RESEARCH_GAP` finding code for native agent profile projection rather than a hard failure. | Proposed |
| FR-015 | The plugin bundle surface kind shall support projection and pre-publish validation of all canonical surfaces into a plugin package layout. | Proposed |
| FR-016 | Plugin bundle projection and validation shall operate as a release/staging capability only: no auto-install, no marketplace publish, and no replacement of project-local installation. | Proposed |
| FR-017 | Docs that reference generated or native tool surface paths shall be validated against the registry; validation shall fail if a documented path is absent from the contract. | Proposed |
| FR-018 | The system shall clearly distinguish command skills, doctrine skills, session presence, native agent profiles, and plugin bundle surfaces as separate surface kinds in all status output and repair commands. | Proposed |

## Non-Functional Requirements

| ID | Requirement | Threshold | Status |
|----|-------------|-----------|--------|
| NFR-001 | `doctor tool-surfaces --json` shall complete for a project with up to 19 configured tools on a 4-core 3.0 GHz CPU, 16 GB RAM, SSD workstation (representative of a CI runner). | <= 5 seconds | Proposed |
| NFR-002 | All new public interfaces in the ToolSurfaceContract bounded context shall pass mypy --strict with zero warnings. | 0 mypy warnings | Proposed |
| NFR-003 | Test coverage for new code in the ToolSurfaceContract bounded context shall meet the project minimum. | >= 90% line coverage | Proposed |
| NFR-004 | The `doctor skills --json` output structure shall not regress for any finding code that existing consumers depend on. | 0 breaking schema changes | Proposed |
| NFR-005 | Each work package in the implementation sequence (#1936, #1944, #1937-#1943) shall be independently mergeable without breaking existing functionality. | 0 regressions per work package merge | Proposed |

## Constraints

| ID | Constraint | Status |
|----|------------|--------|
| C-001 | The ToolSurfaceContract registry shall be introduced as a new bounded context; no new logic shall be added to existing `core.config`, `agent.config`, or `doctor.py` modules to avoid further god-module growth. | Accepted |
| C-002 | Existing command-skill manifests and doctrine-skill manifests shall remain installation-state snapshots; the registry is policy, manifests are state. | Accepted |
| C-003 | The naming convention `ToolSurfaceContract` (not `AgentSurfaceContract`) is non-negotiable and must be used in all new identifiers, CLI output, and documentation. | Accepted |
| C-004 | Existing installers shall be wrapped as providers, not rewritten; core installer logic must be preserved intact. | Accepted |
| C-005 | The glossary-compliant term distinction must be maintained: Tool = concrete execution runtime; Agent = logical collaborator identity/role; Tool Surface = installable/verifiable artifact exposed to a Tool. | Accepted |
| C-006 | Plugin bundle scope is validation and projection for release/staging only; no marketplace publish or auto-install logic shall be introduced. (See FR-016 for the testable requirement form.) | Accepted |
| C-007 | Generated tool surface files that are currently gitignored must remain gitignored; no change to the git tracking policy for generated files is in scope. | Accepted |
| C-008 | The implementation sequence must follow the prescribed order: #1936 (registry skeleton) -> #1944 (migration/compatibility gate) -> #1937 (command-skill provider) -> #1938 (session-presence provider) -> #1939 (doctrine-skill provider) -> #1940 (native profile projection) -> #1941 (legacy agent config refactor) -> #1942 (docs lint) -> #1943 (plugin bundle validation). | Accepted |
| C-009 | PR #1935 (glossary pre-formalization) is a prerequisite; all new naming must respect the terminology established there. | Accepted |
| C-010 | Cross-platform compatibility (Linux, macOS, Windows 10+) must be maintained; no platform-specific path assumptions may be introduced. | Accepted |

## Success Criteria

1. A contributor who clones the repo with any configured tool can run `spec-kitty doctor tool-surfaces --json` and receive a complete, actionable report of missing surfaces with repair commands -- no manual investigation required.
2. Running the repair commands resolves all reported findings for a fresh clone with no manual file edits by the user.
3. `doctor skills --json` output is unchanged for all currently documented finding codes.
4. `spec-kitty agent config list/status/sync` behaves identically from the user's perspective before and after the migration.
5. Built-in and org/project overlay agent profiles are selectable as named agents in host-native tool UIs for all configured tools that support named agents.
6. Docs paths for generated tool surfaces cannot silently drift from the contract -- any mismatch causes a lint failure.
7. Plugin bundle validation correctly reports whether all canonical surfaces are represented in the package layout before publication.
8. All 9 work packages (#1936, #1944, #1937-#1943) are implemented in order and each is independently mergeable without regressions.

## Key Entities

| Entity | Description |
|--------|-------------|
| ToolSurfaceContract | The authoritative registry entry for a configured tool -- defines what surface kinds should exist, their source classification, install scope, and repair policy. |
| SurfaceKind | Classification of a surface: `context_file`, `rule`, `command_file`, `command_skill`, `doctrine_skill`, `workflow`, `agent_profile`, `plugin_manifest`, `mcp_server`, `hook`, `native_config`, `memory`, `setting`. Note: `session_presence` is a provider name, not a SurfaceKind value. |
| SurfaceProvider | An adapter that wraps an existing installer to expand, probe, repair, and remove one surface kind for a given tool. |
| SurfaceInstance | One concrete artifact on disk (e.g., `.agents/skills/spec-kitty.plan/SKILL.md`), tracked in a manifest with hash and owner. |
| SurfacePlan | The computed set of surface instances that should exist for the currently configured tools, derived from the registry. |
| FindingCode | A stable, machine-readable identifier for a specific doctor finding. JSON wire format is kebab-case (e.g., `"generated-surface-missing"`). Python constants may use SCREAMING_SNAKE names but must map to the kebab-case string values. |
| NativeAgentProfile | A host-selectable named agent/subagent generated from a Spec Kitty profile (built-in, org overlay, or project overlay) and projected into a tool's native format. |
| PluginBundle | A release/staging artifact that groups projected surfaces for distribution as a plugin package; not used for project-local installation. |
| Manifest | An installation-state snapshot recording which surface instances are installed, their hashes, and their owners. The manifest is not policy. |

## Domain Language

| Canonical term | Definition | Do not confuse with |
|----------------|------------|---------------------|
| Tool | A concrete execution product/runtime (Claude Code, Codex, Copilot, ...) | Agent (logical identity/role) |
| Agent | A logical collaborator identity or role (Architect Alphonso, Researcher Robbie, ...) | Tool (execution runtime) |
| Tool Surface | An installable, verifiable, packageable artifact or config entry exposed to a concrete Tool | Agent profile source (the canonical source, not the generated projection) |
| ToolSurfaceContract | The authoritative registry (policy source) for what should exist for a configured tool | Manifest (installation-state snapshot, not policy) |
| SurfaceProvider | Code adapter wrapping an existing installer | Installer (the wrapped underlying logic) |
| Command skill | A surface providing slash-command invocation for a Tool | Doctrine skill (managed knowledge surface) |
| Doctrine skill | A managed knowledge/mission-step surface for a Tool | Command skill (command invocation surface) |
| Session presence | Always-on context or orientation files loaded at tool session start | Command skills or doctrine skills |
| Native agent profile | A host-native agent/subagent file projected from a Spec Kitty profile | Profile source YAML (the canonical source, not the generated file) |
| Plugin bundle | A distribution package grouping surfaces for release/staging publication | Project-local installation |

## Assumptions

1. PR #1935 (glossary pre-formalization) merges before or concurrently with #1936; if it has not merged when #1936 begins, #1936 must not introduce naming that conflicts with its in-flight definitions.
2. Tools that do not support named agents/subagents natively receive a `RESEARCH_GAP` finding code for native agent profile projection rather than a hard failure; this is not a blocker for the surface contract.
3. The `.kittify/config.yaml` `agents.available` field accurately reflects which tools are configured; the registry will not attempt to discover unconfigured tools from the filesystem.
4. Generated tool surface files (skills, profiles, hooks, config glue) remain gitignored throughout this mission; repair commands assume generated dirs are absent on fresh clone.
5. Review protocol: Codex reviews each work package PR for glossary compliance, source/generated/manifest ownership correctness, backward compatibility, stable finding codes, repair safety, and focused tests. Claude implements; Codex reviews. No work package merges without Codex sign-off.
