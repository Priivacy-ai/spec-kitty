# Feature Specification: Agent Skills Support for Codex and Vibe

**Feature Branch**: `083-agent-skills-codex-vibe`
**Mission Type**: `software-dev`
**Created**: 2026-04-14
**Source**: GitHub issue [#624](https://github.com/Priivacy-ai/spec-kitty/issues/624)
**Status**: Draft

## Overview

Spec Kitty will announce Mistral Vibe as a fully supported coding agent in its next release. During discovery we validated that Vibe is not a drop-in clone of the existing prompt-file integration model; it is a skills-first agent that discovers Agent Skills from `.agents/skills/`, `.vibe/skills/`, and `~/.vibe/skills/`.

P0 research into OpenAI's public Codex documentation (April 2026) confirmed that **Codex has also moved to the Agent Skills model**, that its `/skills` surface reads from the same `.agents/skills/` discovery tree, and that **custom prompts — the current Spec Kitty integration point for Codex — are deprecated**. Spec Kitty's `codex` wiring today generates flat prompt files into `.codex/prompts/` while also shipping skills to `.agents/skills/`; the prompt-file side is obsolete.

This mission therefore does two things at once:

1. Introduce a generic mechanism for delivering Spec Kitty's `/spec-kitty.*` command surface as Agent Skills packages (`SKILL.md` + body) into `.agents/skills/`.
2. Onboard **Vibe** as the first native consumer of that mechanism and **modernize Codex** onto it, retiring the deprecated `.codex/prompts/` rendering path.

The two agents share one integration shape, so doing both together is strictly simpler than doing them sequentially, and it lets the next release announce Mistral support without shipping a second legacy integration next to the one we already need to remove.

## User Scenarios & Testing *(mandatory)*

### Primary User Stories

- **US-1 — New Vibe user onboards.** A developer with Mistral Vibe installed runs `spec-kitty init --ai vibe` in an empty project. Init succeeds non-interactively, writes the agent into `.kittify/config.yaml`, renders `/spec-kitty.*` as Agent Skills under `.agents/skills/`, protects Vibe runtime state in `.gitignore`, and finishes with instructions for launching the workflow inside Vibe.
- **US-2 — Vibe user invokes Spec Kitty slash commands.** Inside a running Vibe session in a Spec-Kitty-initialized project, typing `/` shows `spec-kitty.specify`, `spec-kitty.plan`, `spec-kitty.tasks`, `spec-kitty.implement`, `spec-kitty.review`, `spec-kitty.merge`, and the other canonical commands. Invoking one runs the same workflow body a Claude/Codex user would see.
- **US-3 — Existing Codex user upgrades.** A developer on an older Spec Kitty release runs `spec-kitty upgrade` in a project that currently has `.codex/prompts/spec-kitty.*.md`. After upgrade, their Codex slash commands are served from `.agents/skills/spec-kitty.*` instead; the old `.codex/prompts/` entries Spec Kitty owns are removed; any non-Spec-Kitty files under `.codex/prompts/` are left untouched; their Codex workflow continues to work inside Codex without user intervention.
- **US-4 — Shared `.agents/skills/` coexistence.** A project with both `vibe` and `codex` (and optionally other shared-root agents) configured runs `spec-kitty init` or upgrade. Skills and command packages contributed by Spec Kitty for one agent do not remove or overwrite files owned by another installed tool; removing one agent (via `spec-kitty agent config remove`) removes only the Spec-Kitty-owned entries for that agent and leaves shared entries in place as long as another consumer still needs them.
- **US-5 — Verify-setup detects Vibe.** A developer runs `spec-kitty verify-setup --check-tools` on a machine with `vibe` on `PATH`; the command lists Vibe with a green status and the discovered executable path. On a machine without Vibe, it lists Vibe as missing with a link to the install instructions.
- **US-6 — README and docs match reality.** A developer reading the repository README sees Vibe in the supported-tools table and finds a documented description of how the Codex and Vibe integrations work (Agent-Skills-based, shared `.agents/skills/` root, additive installation).

### Acceptance Scenarios

1. **Given** a clean project with Vibe installed, **When** the user runs `spec-kitty init --ai vibe --non-interactive`, **Then** the command exits 0, `.kittify/config.yaml` contains `vibe` in `agents.available`, `.agents/skills/` contains Agent Skills packages for every canonical `/spec-kitty.*` command, `.gitignore` protects the Vibe runtime directory, and the printed next-steps reference launching the workflow from inside Vibe.
2. **Given** a Vibe session started in a Spec-Kitty-initialized project, **When** the user types `/spec-kitty.specify`, **Then** Vibe executes the same specification-creation workflow a Claude Code user would see, reading from the skill package in `.agents/skills/`.
3. **Given** a project upgraded from an earlier release with `.codex/prompts/spec-kitty.*.md` files, **When** the user runs `spec-kitty upgrade`, **Then** the Spec-Kitty-owned files under `.codex/prompts/` are removed, equivalent Agent Skills packages are installed under `.agents/skills/`, any non-Spec-Kitty files in `.codex/prompts/` are preserved, and `spec-kitty verify-setup` reports a healthy Codex integration.
4. **Given** a project with both `vibe` and `codex` in `agents.available`, **When** the user runs `spec-kitty agent config remove codex`, **Then** the Codex-owned agent directory state is cleaned up while the Agent Skills packages in `.agents/skills/` that Vibe still needs remain in place, and no third-party files in `.agents/skills/` written by other tools are deleted.
5. **Given** a workstation without Vibe installed, **When** the user runs `spec-kitty verify-setup --check-tools`, **Then** the command reports Vibe as not installed and prints the install command (`curl -LsSf https://mistral.ai/vibe/install.sh | bash` or `uv tool install mistral-vibe`).
6. **Given** the repository's README, **When** a reader scans the supported-tools table, **Then** Mistral Vibe appears with its agent key `vibe`, its primary directory `.agents/skills/`, and a link to the documentation describing the skills-based integration shape shared with Codex.

### Edge Cases

- A project has `.agents/skills/` populated by another tool (for example, hand-written skills or skills installed by a non-Spec-Kitty system). Spec Kitty must never clobber those entries during install, upgrade, or remove.
- A project already has a file at `.agents/skills/spec-kitty.specify/SKILL.md` from a previous Spec Kitty version but with different content. Upgrade should overwrite Spec-Kitty-owned entries and carry forward the current content without prompting.
- Vibe is not installed but the user runs `spec-kitty init --ai vibe`. Init must still succeed (the workflow does not require Vibe at install time), but `verify-setup` and the printed next-steps should clearly flag the missing binary and its install command.
- A user manually deletes `.agents/skills/` from their project. A subsequent `spec-kitty next --agent vibe` must either regenerate the packages or fail with a specific, actionable doctor message that points the user at the repair path.
- A project previously used Codex via `.codex/prompts/` and ran into content drift (a user edited one of the prompt files by hand). Upgrade must not silently discard those edits without either migrating them into the new skill or surfacing them to the user; at minimum the old files must be preserved in git history so a user who edited them can recover.
- A project using agents whose skills discovery goes through `.agents/skills/` (Codex, Vibe, Copilot, Cursor, opencode, Windsurf, Auggie, Roo, Antigravity) has three or more such agents installed simultaneously. Removing any one of them must not delete Spec Kitty skill packages still needed by the others.
- A project on Windows where Vibe's binary resolution or shebangs may differ. Verify-setup and install instructions must work correctly or be clearly marked as unsupported for this release.
- A project whose target branch is not `main`. All generated notices, documentation, and commit messages must avoid hardcoded `main` and defer to the real target branch.

## Requirements *(mandatory)*

### Functional Requirements

| ID | Requirement | Status |
|----|-------------|--------|
| FR-001 | The CLI MUST accept `vibe` as a valid value for `--ai` in `spec-kitty init` and for `spec-kitty agent config add/remove/list/status/sync`. | Proposed |
| FR-002 | `.kittify/config.yaml` MUST accept `vibe` in `agents.available` and round-trip it through load/save without data loss. | Proposed |
| FR-003 | `spec-kitty init --ai vibe --non-interactive` MUST exit 0 on a clean project and leave the project in a state that `spec-kitty next --agent vibe` can drive. | Proposed |
| FR-004 | The runtime MUST render every canonical `/spec-kitty.*` command **template file present in `src/specify_cli/missions/software-dev/command-templates/`** as an Agent Skills package (`<skill-root>/spec-kitty.<command>/SKILL.md` plus any required body files) into the configured skill root for each supported agent. Current canonical set (11 templates): `analyze`, `charter`, `checklist`, `implement`, `plan`, `research`, `review`, `specify`, `tasks`, `tasks-outline`, `tasks-packages`. CLI-only commands without template files (`tasks-finalize`, `accept`, `merge`, `status`, `dashboard`) are out of scope and tracked as follow-up work. | Accepted |
| FR-005 | The Agent Skills renderer MUST emit `SKILL.md` frontmatter that satisfies the documented requirements of both Vibe (`name`, `description`, optional `allowed-tools`, `user-invocable`) and Codex (`name`, `description`), without requiring a separate render pass per agent. | Proposed |
| FR-006 | The installer MUST write Spec-Kitty-owned skill packages into `.agents/skills/` additively: it MUST NOT delete or overwrite files it does not own, and it MUST tolerate the presence of third-party subdirectories in the same root. | Proposed |
| FR-007 | The installer MUST track ownership of each skill package it writes (for example via a manifest file or a deterministic naming prefix) so that uninstall and upgrade operations can identify Spec-Kitty-owned entries without false positives. | Proposed |
| FR-008 | `spec-kitty agent config remove <agent>` MUST remove only Spec-Kitty-owned entries that are no longer required by any remaining configured agent; shared-root entries still needed by another configured agent MUST remain in place. | Proposed |
| FR-009 | `spec-kitty verify-setup --check-tools` MUST detect the `vibe` executable on `PATH` and report its presence, absence, and resolved path, using the same output shape as existing agent detections. | Proposed |
| FR-010 | The gitignore manager MUST protect project-local Vibe runtime and state directories (for example `.vibe/`) from accidental commit, without blocking project-local Vibe configuration intentionally checked in by the user. | Proposed |
| FR-011 | The Codex integration MUST be modernized so that `/spec-kitty.*` slash commands are served to Codex from `.agents/skills/`, and the legacy `.codex/prompts/` output path MUST be removed from the rendering pipeline. | Proposed |
| FR-012 | An upgrade migration MUST detect Spec-Kitty-owned files under `.codex/prompts/` in previously initialized projects and remove them after the equivalent Agent Skills packages have been installed in `.agents/skills/`; non-Spec-Kitty files under `.codex/prompts/` MUST be preserved untouched. | Proposed |
| FR-013 | The AI choices list (`AI_CHOICES`), agent skill registry (`AGENT_SKILL_CONFIG`), and tool-detection registry (`AGENT_TOOL_REQUIREMENTS`) MUST be updated to include `vibe` as a shared-root agent whose primary skill root is `.agents/skills/`. `AGENT_DIRS` and `AGENT_DIR_TO_KEY` are command-layer registries (mapping agents to their dedicated prompt-file directories) and deliberately do NOT include `codex` or `vibe`, since those agents use the skills layer exclusively. | Accepted |
| FR-014 | The README supported-tools table and user documentation MUST list Mistral Vibe with its agent key (`vibe`), its integration shape (Agent Skills via `.agents/skills/`), and its install instructions, and MUST describe the Codex integration as Agent-Skills-based rather than prompt-file-based. | Proposed |
| FR-015 | The mission MUST deliver an architecture decision record describing the Agent Skills renderer contract, the shared-root coexistence policy, and the Codex migration path. | Proposed |
| FR-016 | Automated tests MUST cover: `init --ai vibe --non-interactive` success, config round-trip of `vibe`, verify-setup detection, gitignore protection, additive install into a pre-populated `.agents/skills/`, `agent config remove` correctness in shared-root conditions, Codex legacy-path migration, and skill-package rendering for every canonical command. | Proposed |

### Non-Functional Requirements

| ID | Requirement | Status |
|----|-------------|--------|
| NFR-001 | Installing, upgrading, or removing Vibe or Codex MUST complete in under 3 seconds on a clean project on a developer-class machine (measured on the existing CI baseline), excluding network operations. | Proposed |
| NFR-002 | Shared-root coexistence MUST hold across at least three simultaneously configured shared-root agents: adding or removing any one of them MUST leave every third-party file in `.agents/skills/` byte-identical, verified by a test that diffs the directory before and after. | Proposed |
| NFR-003 | The Codex modernization MUST be zero-touch for existing users: running `spec-kitty upgrade` on a project previously initialized with `--ai codex` MUST produce a working Codex slash-command surface with no manual steps, verified by integration tests that start from fixtures of pre-modernization projects. | Proposed |
| NFR-004 | The skill-package renderer MUST be pure and deterministic: given the same input templates, it MUST produce byte-identical output on repeated runs and across supported operating systems, verified by a snapshot test. | Proposed |
| NFR-005 | The Agent Skills renderer and installer MUST keep the existing command-file path working unchanged for all agents not being migrated in this mission (claude, gemini, copilot, cursor, qwen, opencode, windsurf, kilocode, auggie, roo, q, antigravity). Regression tests MUST assert parity with pre-mission output for those agents. | Proposed |

### Constraints

| ID | Constraint | Status |
|----|-------------|--------|
| C-001 | The canonical agent key for Mistral Vibe is `vibe`, chosen to follow the existing product-name convention (`claude`, `codex`, `gemini`) rather than the vendor name. | Accepted |
| C-002 | The primary skill discovery root for both Vibe and Codex in this mission is `.agents/skills/`. Vendor-specific roots (`.vibe/skills/`, `~/.vibe/skills/`, `~/.codex/skills/`) are out of scope for this release. | Accepted |
| C-003 | The mission MUST land spike decisions and the implementation together in a single release so that Mistral support can be announced without a follow-up migration. | Accepted |
| C-004 | No supported agent key, directory, or integration class currently in production (as of `main` at mission start) may be removed or renamed by this mission. Codex's integration class may change from command-dir to skill-package, but the `codex` key itself is preserved. | Accepted |
| C-005 | The mission must not introduce a Mistral-only code path. Any new rendering or installation logic must be a generic abstraction that Codex consumes in the same release; Vibe is the first native consumer of that abstraction, not a one-off integration. | Accepted |

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001** The next Spec Kitty release includes Mistral Vibe in its announcement, and a developer following only the public README can go from a clean project to a working `/spec-kitty.specify` invocation inside Vibe in fewer than 10 minutes.
- **SC-002** In integration tests, 100% of canonical `/spec-kitty.*` commands render as Agent Skills packages discoverable by both Vibe's and Codex's skills-discovery rules; 0% of them still ship to `.codex/prompts/` after upgrade.
- **SC-003** In a project where three shared-root agents are installed and then one is removed, 100% of third-party files in `.agents/skills/` remain byte-identical before and after the remove operation, verified by automated diff.
- **SC-004** For existing Codex users, zero manual migration steps are required between the pre- and post-mission release; `spec-kitty upgrade` alone produces a working Codex slash-command surface in automated upgrade tests.
- **SC-005** `spec-kitty verify-setup --check-tools` on a machine with Vibe installed reports Vibe as present in at least 99% of successful runs against a matrix of supported operating systems, matching the detection reliability of existing tooling entries (claude, codex, gemini).
- **SC-006** No regression is introduced for the twelve non-migrated agents: pre- and post-mission snapshot tests of their command-file output produce zero diffs.

## Key Entities *(include if feature involves data)*

- **Agent Skills Package.** A self-contained directory discovered by Vibe and Codex, containing at minimum a `SKILL.md` file with YAML frontmatter (`name`, `description`, optional `allowed-tools`, optional `user-invocable`) and a Markdown body. Spec Kitty owns a set of such packages named `spec-kitty.<command>` and installs them into the configured shared skill root.
- **Shared Skill Root.** The on-disk location `.agents/skills/` (project-local) and optionally `~/.agents/skills/` (global) that multiple agents read from. Spec Kitty must treat this root as shared state: additive on write, selective on delete, non-authoritative for content it does not own.
- **Command Template.** An existing `src/specify_cli/missions/*/command-templates/<command>.md` file that today is rendered into agent-specific command directories. After this mission, these same templates are additionally rendered into Agent Skills packages by a new renderer, with per-agent frontmatter adjustments applied deterministically.
- **Skill Ownership Manifest.** A mechanism (location and format to be decided during planning; a JSON manifest under `.kittify/` is the current leading option) that records which Agent Skills packages in `.agents/skills/` were written by Spec Kitty. Used by `agent config remove` and `upgrade` to identify owned entries without guessing.
- **Legacy Codex Prompts Directory.** `.codex/prompts/` in previously initialized projects. Post-mission, Spec Kitty does not write to this directory; an upgrade migration removes only the files it previously owned there.

## Assumptions

- Vibe's documented discovery of `.agents/skills/` works identically to Codex's implementation; integration tests should confirm this on fixtures that mirror both agents' discovery logic.
- A skill-package layout acceptable to both Codex (per OpenAI's Agent Skills docs) and Vibe (per Mistral's Agents & Skills docs) exists and does not require agent-specific branching inside individual skill files. If planning phase proves this false for a specific command, per-agent overlays are an acceptable fallback but must remain declarative.
- Users on the next release will run `spec-kitty upgrade` before expecting Codex to work in its new form. An out-of-band compatibility shim that keeps the deprecated `.codex/prompts/` path working is not required.
- The `vibe` executable name is stable and matches what Mistral publishes at the time of release. If it changes, tool detection becomes a configuration change, not a redesign.
- Windows support for Vibe matches what Mistral currently ships. Any platform-specific gaps are out of scope for this mission but should be flagged during implementation if encountered.

## Dependencies

- P0 research findings on Vibe's and Codex's skills model (summary captured above; full research artifacts to be written during the plan phase).
- The existing `AGENT_SKILL_CONFIG` infrastructure in `src/specify_cli/core/config.py` already models shared-root vs native-root vs wrapper-only agents; this mission extends rather than replaces that taxonomy.
- The existing migration framework (`src/specify_cli/upgrade/migrations/`) and its `get_agent_dirs_for_project()` helper, which this mission will extend with skill-root-aware variants.
- Documentation sources (cited during discovery): Mistral Vibe Agents & Skills docs, OpenAI Codex Agent Skills and Slash-Commands docs. Both must be re-checked during planning to guard against version drift.

## Open Questions

None require blocking clarification at the specification level. The remaining design choices — exact Skill Ownership Manifest format, per-agent frontmatter overlay strategy, and the precise upgrade migration sequence for `.codex/prompts/` — are implementation decisions for the plan phase.

## Out of Scope

- Global (`~/`) skill installation for Vibe or Codex. This release targets project-local `.agents/skills/` only.
- Vendor-specific discovery roots (`.vibe/skills/`, `~/.vibe/skills/`, `~/.codex/skills/`). Users who want those can still use Spec Kitty via the shared root; native per-vendor roots are a follow-up.
- Modernizing any agent other than Codex onto the skill-package renderer in this mission. The renderer is designed to be extensible; switching additional agents over is explicitly deferred.
- Changes to the mission state machine, lane computation, or merge workflow. This mission only affects how command templates are rendered and delivered to agents.
- A general-purpose "skills marketplace" or discovery CLI surface. This mission installs exactly the canonical Spec Kitty command set as skills; it does not add user-authored skill discovery.
