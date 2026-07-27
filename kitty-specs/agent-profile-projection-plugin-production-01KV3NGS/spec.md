# Spec: Agent Profile Projection and Plugin Production Pipeline

**Mission:** agent-profile-projection-plugin-production-01KV3NGS
**Mission ID:** 01KV3NGSDCJ272573TF6T6NWDW
**Type:** software-dev
**Status:** Draft

## Overview

rc44 established the ToolSurfaceContract registry and added staging plugin bundles, but did not wire the repair service into `init`/`upgrade`, did not ship production plugin artifacts, and left Codex native profile projection unimplemented. This mission closes all three gaps.

**The product rule this mission enforces:** Every configured harness either shows Spec Kitty agent profiles in its native UI, or shows an explicit `not_applicable` finding in `doctor tool-surfaces`. No silent gaps. No "doctor can see the problem but init/upgrade doesn't fix it."

## User Scenarios & Testing

### Scenario 1: Fresh init (Claude + Codex configured)

1. Developer runs `spec-kitty init --ai claude codex`
2. `.claude/agents/<profile>.md` and `.codex/agents/<profile>.toml` files are created
3. `doctor tool-surfaces --json` reports `present` for all configured surfaces
4. Running `spec-kitty init` again produces identical results with zero changes reported

### Scenario 2: Upgrading from rc44

1. rc44 project has 11-entry command-skill manifest, missing native profile directories, no unsafe symlinks cleaned
2. Developer runs `spec-kitty upgrade`
3. CLI auto-creates missing safe surfaces, auto-repairs stale manifest, summarizes what changed
4. `doctor tool-surfaces --json` reports zero errors except documented `not_applicable` entries

### Scenario 3: Drift protection — interactive mode

1. Developer edits `.claude/agents/analyst.md` to customize the analyst profile
2. Developer runs `spec-kitty upgrade` in interactive mode
3. CLI detects drift on `analyst.md` and prompts per-file before any overwrite
4. Developer declines — file is preserved; upgrade proceeds for all other surfaces

### Scenario 4: Drift protection — non-interactive mode (CI)

1. Same drift as Scenario 3
2. Developer runs `spec-kitty upgrade --yes`
3. CLI reports drift with full path but does NOT overwrite; exits non-zero
4. Developer runs `spec-kitty upgrade --repair-drift=overwrite` to force replacement

### Scenario 5: Installing the Claude Code plugin

1. Developer runs `spec-kitty plugin build --target claude-code`
2. Bundle is generated; `claude plugin validate --strict` passes with zero warnings
3. Developer installs locally via `claude --plugin-dir dist/spec-kitty-plugins/claude-code/`
4. End users install via `claude plugin marketplace add <url>` then `claude plugin install spec-kitty@spec-kitty-plugins`

### Scenario 6: Plugin runtime bootstrap

1. End user has `spec-kitty` CLI installed — plugin delegates to it directly
2. End user without `spec-kitty` — plugin falls back to `uvx spec-kitty-cli==<pinned-version>`
3. Both paths produce identical plugin behaviour

## Functional Requirements

### A. Init/Upgrade Surface Repair Wiring

| ID | Requirement | Status |
|---|---|---|
| FR-001 | `spec-kitty init` calls the ToolSurfaceContract repair service after writing agent configuration, before returning to the user | Proposed |
| FR-002 | `spec-kitty upgrade` calls the ToolSurfaceContract repair service after all migrations complete, before returning to the user | Proposed |
| FR-003 | Missing generated surfaces (absent from disk, present in canonical manifest) are auto-created during `init` and `upgrade` without user prompting | Proposed |
| FR-004 | Stale generated surfaces (manifest-owned, bytes outdated but not user-modified) are auto-repaired during `init` and `upgrade` without user prompting | Proposed |
| FR-005 | Drifted generated surfaces (manifest-owned, bytes changed outside of spec-kitty since last repair) trigger a per-file interactive prompt in interactive mode before any overwrite; the prompt names the file path | Proposed |
| FR-006 | In non-interactive mode, drifted surfaces are reported with file paths and are not overwritten; overwrite requires the explicit flag `--repair-drift=overwrite`; `--yes` alone must not trigger overwrite of drifted files; the command exits non-zero when drift is detected and `--repair-drift=overwrite` was not passed | Proposed |
| FR-007 | `init` and `upgrade` emit a summary listing: surfaces created, surfaces repaired, drift found (with paths), and surfaces skipped as `not_applicable` | Proposed |
| FR-008 | `init` and `upgrade` are idempotent: running either command twice on a project with no manual edits produces identical output and no reported drift on the second run | Proposed |

### B. Native Agent Profile Renderers

| ID | Requirement | Status |
|---|---|---|
| FR-009 | `ClaudeCodeProfileRenderer` projects built-in and overlay Spec Kitty profiles to `.claude/agents/<profile_id>.md` with YAML frontmatter (`name`, `description`) and a structured Markdown body including a provenance footer; this renderer already exists and must be verified to run on `upgrade` | Existing / verify wiring |
| FR-010 | `CopilotProfileRenderer` projects profiles to `.github/agents/<profile_id>.agent.md`; the file extension must be `.agent.md`, not the deprecated `.chatmode.md`; existing renderer must be validated against current VS Code custom-agent docs | Existing / verify extension |
| FR-011 | A new `CodexProfileRenderer` projects profiles to `.codex/agents/<profile_id>.toml`; the TOML includes the three required fields `name`, `description`, and `developer_instructions`; when a profile provides values for optional Codex config keys (`model`, `model_reasoning_effort`, `sandbox_mode`), those are included | Proposed |
| FR-012 | When Amazon Q Developer CLI agent format is confirmed stable during this mission, an `AmazonQProfileRenderer` projects profiles to `~/.aws/amazonq/cli-agents/<profile_id>.json`; if format or stability cannot be confirmed, the harness is marked `not_applicable` and a follow-up tracking issue is filed | Proposed |
| FR-013 | When Augment Code subagent format is confirmed stable during this mission, an `AugmentProfileRenderer` projects profiles to `.augment/agents/<profile_id>.md` with YAML frontmatter and Markdown body; if not confirmed, the harness is marked `not_applicable` and a follow-up issue is filed | Proposed |
| FR-014 | All harnesses without a verified stable native agent-profile primitive (Windsurf, Cursor, Kiro, and any others) are explicitly marked `not_applicable` for the `agent_profile` surface kind; this appears in `doctor tool-surfaces --json` output with a human-readable reason | Proposed |
| FR-015 | `doctor tool-surfaces --kind agent-profile --json` reports per-harness status as exactly one of: `present`, `missing`, `stale`, `drifted`, `not_applicable`, or `research_gap`; `research_gap` is only valid for harnesses not yet assessed | Proposed |
| FR-016 | After `CodexProfileRenderer` lands, `doctor tool-surfaces --kind agent-profile` must no longer report `research_gap` for Codex; it reports `present`, `missing`, `stale`, or `drifted` based on disk state | Proposed |

### C. Claude Code Plugin Production

| ID | Requirement | Status |
|---|---|---|
| FR-017 | `spec-kitty plugin build --target claude-code` generates a complete plugin bundle at `dist/spec-kitty-plugins/claude-code/` | Proposed |
| FR-018 | The bundle includes `.claude-plugin/plugin.json` with: `name`, `displayName`, `version` (matching the current spec-kitty-cli release version, not `0.0.0`), `description`, `author`, and component pointers for `skills`, `agents`, and `hooks` | Proposed |
| FR-019 | The bundle includes skill files reflecting the full current canonical command-skill set | Proposed |
| FR-020 | The bundle includes agent profile Markdown files in `agents/` for all built-in Spec Kitty profiles | Proposed |
| FR-021 | The bundle includes a `bin/` wrapper script that checks for an installed `spec-kitty` CLI on `PATH`; if found, it delegates to the installed CLI; if not found, it falls back to `uvx spec-kitty-cli==<version>` pinned to the current release | Proposed |
| FR-022 | `claude plugin validate --strict` passes with zero errors and zero strict warnings on the generated bundle; this validation runs in CI as part of the release pipeline | Proposed |
| FR-023 | A `marketplace.json` is maintained in the repository (or a dedicated plugins sub-directory) enabling installation via `claude plugin marketplace add <url>` + `claude plugin install spec-kitty@spec-kitty-plugins` | Proposed |
| FR-024 | The project README (or a dedicated plugin install guide) documents both the marketplace install path and the `--plugin-dir` local development install path | Proposed |

### D. Codex Plugin Projector

| ID | Requirement | Status |
|---|---|---|
| FR-025 | A `CodexBundleProjector` generates a Codex plugin bundle at `dist/spec-kitty-plugins/codex/` with `.codex-plugin/plugin.json` conforming to the Codex plugin JSON schema | Proposed |
| FR-026 | The Codex plugin manifest includes all required fields: `name`, `version`, `description`, `author.name`, `interface.displayName`, `interface.shortDescription` | Proposed |
| FR-027 | The Codex bundle includes `skills/` (current canonical command-skill set), `.mcp.json` when applicable, and hooks discoverable by presence | Proposed |
| FR-028 | The Codex bundle does NOT include agent profile packaging at the plugin level; the `plugin.json` does not reference an `agents/` component unless official Codex documentation explicitly confirms plugin-level agent packaging | Proposed |
| FR-029 | A `marketplace.json` is generated alongside the bundle enabling repo-local install via `codex plugin marketplace add <path>` + `codex plugin add spec-kitty@spec-kitty-plugins` | Proposed |

### E. Command-Skill Manifest Repair

| ID | Requirement | Status |
|---|---|---|
| FR-030 | Stale command-skill manifests (e.g., 11-entry rc44-era manifests where the canonical set has grown) self-heal during `spec-kitty upgrade` following the "safe stale" auto-repair policy; no user prompt required | Proposed |
| FR-031 | Drifted generated command skill files (user-modified SKILL.md files) follow the same drift policy as agent profiles: prompt in interactive mode, report-only in non-interactive | Proposed |
| FR-032 | Old unsafe symlink artifacts (e.g., `.agents/skills/spec-kitty.advise`) are detected during `upgrade` and removed; the removal is included in the upgrade summary | Proposed |

### F. Roo Code Deprecation

| ID | Requirement | Status |
|---|---|---|
| FR-033 | Roo Code is removed from `AI_CHOICES` in `src/specify_cli/core/config.py` and from `AGENT_DIRS` in the migration module; `spec-kitty init` can no longer target Roo Code | Proposed |
| FR-034 | `spec-kitty upgrade` detects existing `.roo/` directories and emits a deprecation notice: Roo Code shut down 2026-05-15; the directory is preserved but is no longer managed by spec-kitty | Proposed |
| FR-035 | The upgrade migration removes Roo Code from `.kittify/config.yaml` when present and reports the removal in the upgrade summary | Proposed |
| FR-036 | User-facing documentation is updated to remove Roo Code from the Supported AI Agents list and note its shutdown date | Proposed |

### G. Certification Tests and Migration Fixture

| ID | Requirement | Status |
|---|---|---|
| FR-037 | Automated tests for `ClaudeCodeProfileRenderer`: output path, required frontmatter fields, provenance footer presence, idempotent re-render | Proposed |
| FR-038 | Automated tests for `CodexProfileRenderer`: TOML format validity, all three required fields present, output path under `.codex/agents/`, optional-field passthrough | Proposed |
| FR-039 | Automated tests for `CopilotProfileRenderer`: file extension is `.agent.md` (not `.chatmode.md`), output path under `.github/agents/` | Proposed |
| FR-040 | Integration tests for `init`/`upgrade` ToolSurfaceContract wiring: missing surfaces created, stale surfaces repaired, drifted surfaces reported-only in `--yes` non-interactive mode | Proposed |
| FR-041 | Migration acceptance fixture test: given a project fixture with configured `claude` and `codex`, 11-entry command-skill manifest, and no native profile directories — `spec-kitty upgrade --yes` creates all missing safe surfaces, repairs the stale manifest, leaves `doctor tool-surfaces --json` with zero findings except `not_applicable` entries, and exits 0 | Proposed |
| FR-042 | The doctor JSON stability contract (`test_migration_compat.py`) is updated to include `agent_profile` surface kinds in the frozen baseline after renderers land | Proposed |

## Non-Functional Requirements

| ID | Requirement | Threshold | Status |
|---|---|---|---|
| NFR-001 | All new and changed Python modules pass `mypy --strict` with zero type errors | 0 mypy errors on changed modules | Proposed |
| NFR-002 | All new code paths have automated test coverage | ≥90% branch coverage on new code | Proposed |
| NFR-003 | New and changed functions stay within the project complexity ceiling | McCabe complexity ≤15 per function | Proposed |
| NFR-004 | Claude Code plugin bundle passes strict validation | `claude plugin validate --strict` exits 0 with zero errors and zero warnings | Proposed |
| NFR-005 | Doctor JSON schema stability | `doctor tool-surfaces --json` schema matches frozen baseline in `test_migration_compat.py`; new fields additive only | Proposed |
| NFR-006 | Init/upgrade idempotency | Second consecutive run on an unedited project reports zero surfaces created and zero drift | Proposed |
| NFR-007 | Non-interactive drift safety | `--yes` alone must not overwrite drifted files under any code path | Proposed |
| NFR-008 | Terminology guard | `tests/architectural/test_no_legacy_terminology.py` passes after any prose or doctrine changes | Proposed |

## Constraints

| ID | Constraint | Status |
|---|---|---|
| C-001 | Migrations use `get_agent_dirs_for_project()` — never hardcode `AGENT_DIRS`; never create directories for agents not in `config.yaml` | Active |
| C-002 | The drift policy (prompt / report-only / auto-repair) applies uniformly to agent profiles, command skills, and plugin manifests; no surface kind receives silent-overwrite treatment | Active |
| C-003 | Codex plugin bundle must not include agent profile packaging unless `developers.openai.com/codex/plugins/build` explicitly documents plugin-level agent packaging | Active |
| C-004 | The CLI hint mechanism (`<claude-code-hint>` on stderr) is not in scope for this mission; it requires Anthropic marketplace listing | Active |
| C-005 | Amazon Q CLI agent projection targets the user-global path `~/.aws/amazonq/cli-agents/` only; no project-level agent config path has been confirmed in official AWS documentation | Active |
| C-006 | Plugin build output writes only within `dist/spec-kitty-plugins/`; no out-of-tree writes during `plugin build` | Active |
| C-007 | Roo Code removal must not fail on projects that have no `.roo/` directory or no Roo Code entry in `config.yaml`; all detection code must guard for absence | Active |
| C-008 | All changes to `origin/main` go through pull requests; `spec-kitty upgrade` and `plugin build` must not push to remote branches | Active |

## Success Criteria

1. Running `spec-kitty upgrade` on an rc44 project configured for `claude` and `codex` leaves `doctor tool-surfaces --json` with zero errors; `.claude/agents/` and `.codex/agents/` contain projected profiles; the command-skill manifest reflects the full current canonical set
2. `spec-kitty plugin build --target claude-code` completes without error and `claude plugin validate --strict` exits 0 on the output
3. A developer following the README can install the Spec Kitty Claude Code plugin from the git-based marketplace in under 3 minutes
4. Running `spec-kitty upgrade` twice consecutively on an unedited project produces identical output — zero new surfaces, zero drift detected on the second run
5. Editing a generated profile file then running `spec-kitty upgrade` in interactive mode produces a per-file prompt; running with `--yes` reports drift and exits non-zero without modifying the file
6. All new and changed code passes `mypy --strict` (on changed modules), `ruff check`, and the full pytest suite with ≥90% coverage on new paths

## Key Entities

| Entity | Description |
|---|---|
| `ToolSurfaceContract` | Policy registry tracking what surfaces each configured harness should have; owns repair and doctor logic |
| `AgentProfilesProvider` | Surface provider that drives native agent profile projection across all harnesses |
| `ProfileRenderer` | Protocol implemented by each harness-specific renderer (Claude Code, Codex, Copilot, etc.) |
| `SurfaceRepairService` | Applies drift/stale/missing policy to surfaces reported by providers |
| `BundleProjector` | Protocol implemented by each harness-specific plugin bundle generator |
| Native agent profile | A harness-recognized file that causes the tool to expose a named, selectable AI persona in its UI |
| Drift | A manifest-owned generated file whose bytes have been changed outside of spec-kitty since last repair |
| Stale | A manifest-owned generated file that is outdated but has not been user-modified |
| `not_applicable` | Explicit finding: harness has been assessed and confirmed to lack a native agent-profile primitive |
| `research_gap` | Finding: harness has not yet been assessed for native agent-profile support |

## Assumptions

1. Codex custom-agent TOML format (`.codex/agents/<id>.toml`, required fields `name`/`description`/`developer_instructions`) is stable per `developers.openai.com/codex/subagents`; no YAML renderer is needed
2. Amazon Q CLI agent format (`~/.aws/amazonq/cli-agents/<id>.json`) is confirmed from the AWS What's New announcement (July 2025); GA status assumed; renderer targets user-global path only
3. Augment Code subagent format (`.augment/agents/<id>.md`, YAML frontmatter with `name`/`description`/`model`/`tools`) is CLI-GA per official docs; explicit ruling (renderer or `not_applicable`) is made during implementation
4. Claude Code plugin system is GA (v2.0.12+, confirmed); git-based marketplace distribution is supported; no Anthropic signing required
5. Codex plugin schema is stable per `developers.openai.com/codex/plugins/build`; hooks are discovered by presence, not manifest pointer
6. VS Code custom agents use `.agent.md` extension; the rename from `.chatmode.md` is stable as of 2025
7. Roo Code shut down 2026-05-15; community forks (Cline, ZooCode) are out of scope unless explicitly added as separate harnesses in a future mission

## Domain Language

| Term | Definition | Avoid |
|---|---|---|
| Drift | A manifest-owned generated file whose bytes were changed outside of spec-kitty | "modified", "dirty" |
| Stale | A manifest-owned generated file that is outdated but unmodified by the user | "old", "outdated" |
| Not applicable | A harness assessed and confirmed to lack a native agent-profile primitive | leaving the field blank |
| Research gap | A harness not yet assessed for native agent-profile support | "unsupported" |
| Native agent profile | A file format that causes a harness to expose a named, selectable AI persona in its UI | "custom agent" (ambiguous across tools) |
| Surface | A specific generated artifact tracked by the ToolSurfaceContract registry | "file" |
| Mission | A unit of spec-driven work in Spec Kitty | "feature" |
