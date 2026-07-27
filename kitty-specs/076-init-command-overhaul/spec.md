# Spec: Init Command Overhaul

**Feature:** 076-init-command-overhaul
**Mission type:** software-dev
**Status:** Specified
**Target branch:** main

---

## Problem Statement

`spec-kitty init` has accumulated significant technical debt. It was originally designed as a per-project installer but has never been coherently redesigned as the global machine-level bootstrapper it needs to be. The result is a command with:

- Architecturally wrong behavior that is still active: charter/doctrine interview running before the user has a project; per-project `.kittify/scripts/` copying that serves no purpose; REPO_MAP/SURFACES template generation; dashboard startup; git commit of generated files
- Flags with no valid end-user use case: `--template-root`, `--debug`, `--skip-tls`, `--github-token`, `--preferred-implementer`, `--preferred-reviewer`, `--script`, `--force`
- A completely unused preference system: `preferred_implementer` and `preferred_reviewer` are stored in `config.yaml` and loaded at startup, but the methods that would act on them (`select_implementer`, `select_reviewer`) are never called anywhere in the codebase — the data is collected and silently ignored
- A double-prompt problem: when commands are installed both globally (`~/.kittify/`) and locally (`.claude/commands/`, `.codex/prompts/`, etc.), users see duplicate slash commands in their AI tools
- No documented architecture for the global `~/.kittify/` runtime vs per-project `.kittify/`

This feature removes all architecturally wrong code, simplifies the CLI surface, redesigns init as a global runtime bootstrapper, removes the unused preference system from the entire codebase, adds a safe migration to eliminate local command duplicates, and captures all resulting architectural decisions as ADRs.

---

## Goals

- `spec-kitty init` becomes a clean, fast, machine-level setup command that bootstraps `~/.kittify/`
- The CLI surface is reduced to only flags that do real work
- `preferred_implementer` and `preferred_reviewer` are removed from the entire codebase (CLI flags, data model, config serialization, docs, tests) with a cleanup migration for existing `config.yaml` files
- A safe migration removes per-project agent command directories when and only when the global equivalents are confirmed present, eliminating double prompts
- All architectural decisions are documented as ADRs in `architecture/adrs/`
- Existing projects continue to work without modification

## Non-Goals

- Per-project setup (`.kittify/`, `.gitignore`, `.claudeignore`) — belongs in a future `spec-kitty setup` or implicit first-run
- Charter/doctrine authoring — belongs in `/spec-kitty.charter`
- Mission selection — belongs in `/spec-kitty.specify`
- No new user-facing features beyond the cleanup

---

## Actors

- **Developer (new install):** Running `spec-kitty init` for the first time on a machine. Needs the global runtime created and agents configured.
- **Developer (existing install):** Running `spec-kitty init` again to add/remove agents or upgrade the global runtime. Must not lose existing agent configuration or local-only command customizations.

---

## User Scenarios & Testing

### Scenario A — First-time machine setup
A developer installs spec-kitty-cli via pipx and runs `spec-kitty init`. The command detects no global runtime exists, creates `~/.kittify/` with missions and skills, prompts for which AI agents to enable (with a clear warning that this is a machine-wide setting), and exits. No project directory is created or modified.

### Scenario B — Add an agent to an existing install
A developer already has spec-kitty configured with Claude only. They run `spec-kitty init` again, see Claude is installed, and select Codex to add. The command installs Codex globally. Other projects on the machine are not affected — they continue to use only the agents they reference.

### Scenario C — Init in a new project directory
A developer runs `spec-kitty init my-new-project`. The command creates the `my-new-project/` directory, bootstraps/verifies the global runtime, and writes minimal project scaffolding (`.gitignore`, agent config reference). The developer then runs `/spec-kitty.specify` inside the project.

### Scenario D — Non-interactive CI/machine provisioning
A developer runs `spec-kitty init --ai claude,codex --non-interactive`. The command runs silently, creates the global runtime for the specified agents, and exits with code 0. No prompts are shown.

### Scenario E — Re-running init on an already-initialized machine
A developer runs `spec-kitty init` on a machine where `~/.kittify/` already exists and is current. The command detects this, shows which agents are configured, optionally offers to add/remove, and exits cleanly without overwriting anything.

### Scenario F — Upgrade removes local command duplicates safely
A developer runs `spec-kitty upgrade` on an existing project that has local `.claude/commands/` and `.codex/prompts/` directories. The upgrade migration checks that global command files exist for each agent. Where they do, the local files are removed. Where global files are absent, the local files are left untouched. The developer no longer sees duplicate slash commands in Claude Code.

### Scenario G — Upgrade on a project with no global runtime
A developer runs `spec-kitty upgrade` on a machine where `~/.kittify/` does not exist (e.g. a CI environment). The migration detects the missing global runtime, skips all local command removal, and emits a warning that the user should run `spec-kitty init` first.

---

## Functional Requirements

| ID | Requirement | Status |
|----|-------------|--------|
| FR-001 | `spec-kitty init` defaults to operating in the current directory when no `project_name` argument is given; there is no `--here` flag | Proposed |
| FR-002 | When `project_name` is given, the command creates a new subdirectory and initializes within it | Proposed |
| FR-003 | The command bootstraps `~/.kittify/` as the global runtime if it does not exist or is outdated; failure to bootstrap must surface as an explicit error, not be silently swallowed | Proposed |
| FR-004 | The command detects which AI agents are already installed globally and presents them to the user | Proposed |
| FR-005 | The user can add or remove agents during init; the UI clearly states that changes are machine-wide and affect all projects | Proposed |
| FR-006 | Agent selection is persisted to global agent config | Proposed |
| FR-007 | Skills are installed to `~/.kittify/` canonical locations; per-project directories reference the global install | Proposed |
| FR-008 | The `--ai` flag accepts a comma-separated list of agent keys for non-interactive agent selection | Proposed |
| FR-009 | The `--non-interactive` flag suppresses all prompts; combined with `--ai`, the command runs fully headless | Proposed |
| FR-010 | The command initializes a git repository in the project directory if one does not exist, unless `--no-git` is given | Proposed |
| FR-011 | The command writes `.gitignore` protection for all possible agent directories in the project | Proposed |
| FR-012 | The command writes a `.claudeignore` file in the project directory | Proposed |
| FR-013 | The command writes project metadata to `.kittify/metadata.yaml` | Proposed |
| FR-014 | The command writes VCS config to `.kittify/config.yaml` without a `selection` block | Proposed |
| FR-015 | The command completes without creating or prompting about charter, doctrine, missions, REPO_MAP/SURFACES templates, or dashboard | Proposed |
| FR-016 | Re-running init on an already-configured machine is idempotent — no data is lost or overwritten without explicit user action | Proposed |
| FR-017 | `preferred_implementer` and `preferred_reviewer` are removed from the `AgentSelectionConfig` dataclass, `save_agent_config`, `load_agent_config`, and all serialization/deserialization paths | Proposed |
| FR-018 | `select_implementer()` and `select_reviewer()` methods are removed from `AgentConfig` | Proposed |
| FR-019 | `AgentSelectionConfig` is removed entirely; the `selection` section is no longer written to or read from `config.yaml` | Proposed |
| FR-020 | A `spec-kitty upgrade` migration strips `agents.selection.preferred_implementer` and `agents.selection.preferred_reviewer` from existing `.kittify/config.yaml` files | Proposed |
| FR-021 | A `spec-kitty upgrade` migration removes per-project agent command files (e.g. `.claude/commands/spec-kitty.*.md`) for each agent where the corresponding global command directory (`~/.kittify/`) is confirmed to contain those files | Proposed |
| FR-022 | The local-command-removal migration (FR-021) must never delete a project-local command file if the global equivalent is absent; it must skip the entire agent if global commands are missing | Proposed |
| FR-023 | The local-command-removal migration (FR-021) must not touch command files that were not generated by spec-kitty (identified by absence of a spec-kitty-command-version header or equivalent marker) | Proposed |
| FR-024 | The deprecated `--mission` flag is removed entirely from `spec-kitty init` | Proposed |
| FR-025 | The `--ignore-agent-tools` flag is removed from `spec-kitty init` (tool availability checks are not performed during global init) | Proposed |
| FR-026 | All 7 architectural decisions made during this overhaul are documented as ADRs in `architecture/adrs/` per DIRECTIVE_003 | Proposed |
| FR-027 | All user-facing documentation is updated to remove references to deleted flags and the removed preference system | Proposed |

---

## Flags to Remove

All of these flags currently exist in `init.py` and are active in the control flow. They are architecturally wrong, not merely dead, and must be removed along with the code they enable.

| Flag | Lines (approx) | Reason |
|------|---------------|--------|
| `--here` | 740 | Redundant — current directory is the default when no `project_name` is given |
| `--script` / `--script-type` | 734, 982–992 | The script type drives copying of `.kittify/scripts/bash/` or `powershell/`; those directories are never invoked at runtime (shim generation replaced them) |
| `--preferred-implementer` | 735, 911–937 | The preference is stored but `select_implementer()` is never called anywhere; the entire preference system is being removed |
| `--preferred-reviewer` | 736, 949–967 | Same as above |
| `--force` | 741, 790 | Only used to suppress confirmation for `--here` in a non-empty dir; removed with `--here` |
| `--template-root` | 750, 1007 | No end-user use case; `SPEC_KITTY_TEMPLATE_ROOT` env var remains available for maintainers |
| `--debug` | 744, 1010–1024 | Exclusively wired to the remote GitHub download path being removed |
| `--skip-tls` | 743, 1077 | Exclusively wired to the remote GitHub download path being removed |
| `--github-token` | 745–748, 1160 | Exclusively wired to the remote GitHub download path being removed |
| `--mission` | 737, 995–1000 | Already hidden/deprecated; remove entirely |
| `--ignore-agent-tools` | 738, 884–908 | Tool availability checks are not appropriate during global machine init |

---

## Code Paths to Remove

All of these code paths are active today. Each must be removed along with its tests.

| Code Path | Location | Reason |
|-----------|----------|--------|
| Remote GitHub tarball download | `template/github_client.py`, init.py:1149–1163 | spec-kitty is distributed via pipx; package templates are always available |
| Local-repo template override | `template/manager.py:get_local_repo_root`, init.py:1007 | Developer-only; no CLI flag needed; env var remains |
| `.kittify/scripts/bash/` and `powershell/` copying | `template/manager.py:copy_specify_base_from_local` lines 131–150 | Nothing invokes these scripts; shim generation is the dispatch model |
| Script type selection | init.py:982–992 | Driven entirely by `--script` flag being removed |
| Mission selection + `_activate_mission()` | init.py:994–1005, 1199–1211 | Missions are per-feature; no mission decisions at init time |
| Preferred agent selection (Stage 3) | init.py:911–970 | Entire preference system being removed |
| `_run_doctrine_stack_init` | init.py:1261 (call), init.py:520–572 (definition) | Charter belongs in `/spec-kitty.charter` |
| `_run_inline_interview` | init.py:433–516 | Part of charter interview; removed with doctrine stage |
| `_apply_doctrine_defaults` | init.py:392–429 | Part of charter interview; removed with doctrine stage |
| `_maybe_generate_structure_templates` | init.py:1260 (call), init.py:576–623 (definition) | Not appropriate during machine-level init |
| `ensure_dashboard_running` | init.py:1347 | Not appropriate during machine-level init |
| Initial git commit of generated files | init.py:1469–1490 | init bootstraps a global runtime, not a git project |
| `AgentSelectionConfig` dataclass | `core/agent_config.py:28–37` | Entire class removed (FR-019) |
| `select_implementer()` method | `core/agent_config.py:57–72` | Never called anywhere in the codebase |
| `select_reviewer()` method | `core/agent_config.py:75–99` | Never called anywhere in the codebase |
| `selection` block in `save_agent_config` | `core/agent_config.py:195–196` | No longer written |
| `selection` block in `load_agent_config` | `core/agent_config.py:158–162` | No longer read |

---

## New Deliverables: Upgrade Migrations

### Migration A — Strip `selection` block from `config.yaml`

Strips `agents.selection.preferred_implementer` and `agents.selection.preferred_reviewer` from any existing `.kittify/config.yaml`. Safe to run on all projects: if the keys are absent, the migration is a no-op.

### Migration B — Remove local per-project agent command duplicates

Removes spec-kitty-generated command files from per-project agent directories (`.claude/commands/spec-kitty.*.md`, `.codex/prompts/spec-kitty.*.md`, etc.) for any agent where the equivalent files are confirmed present in the global runtime.

**Safety invariants (must all hold before any deletion):**

1. `~/.kittify/` exists and contains at least one missions subdirectory (global runtime is present)
2. For the specific agent being cleaned, the global command directory exists and contains files matching the spec-kitty command naming pattern
3. The local file being deleted contains a `spec-kitty-command-version` header (confirming it is a generated file, not a user-authored one)
4. If any invariant fails for an agent, that agent's local files are left completely untouched

The migration must emit a clear per-agent summary of what was removed and what was skipped, and why.

---

## Non-Functional Requirements

| ID | Requirement | Status |
|----|-------------|--------|
| NFR-001 | `spec-kitty init` completes in under 10 seconds on a machine with an existing global runtime (no network required) | Proposed |
| NFR-002 | `spec-kitty init --non-interactive --ai claude` exits with code 0 and produces no interactive prompts | Proposed |
| NFR-003 | Re-running init on an already-configured machine produces no changes to existing files when the installed version matches | Proposed |
| NFR-004 | All removed code paths have corresponding test deletions or updates; `tests/specify_cli/cli/commands/test_init_doctrine.py` is deleted | Proposed |
| NFR-005 | New and modified code paths have 90%+ test coverage consistent with project standards | Proposed |
| NFR-006 | The local-command-removal migration (Migration B) has integration tests covering: global present → files removed; global absent → files untouched; non-generated local file → untouched; mixed agents → per-agent correct behavior | Proposed |

---

## Constraints

| ID | Constraint | Status |
|----|------------|--------|
| C-001 | The CLI framework is typer; no new framework dependencies are introduced | Proposed |
| C-002 | `mypy --strict` must pass across all modified files | Proposed |
| C-003 | Existing projects with a `.kittify/` already present must continue to work without any manual migration step | Proposed |
| C-004 | The `--ai` flag and agent key vocabulary must remain backward-compatible with any documented usage | Proposed |
| C-005 | No per-project agent directories (`.claude/`, `.codex/`, etc.) are created by `spec-kitty init`; those are managed by per-project setup flows and Migration B | Proposed |
| C-006 | Migration B must never cause data loss: if any safety invariant is not met, the migration skips that agent entirely and logs a warning | Proposed |

---

## Architecture Decision Records (Deliverables)

A core deliverable of this feature is authoring the following ADRs in `architecture/adrs/`. Each captures a decision made or confirmed during this overhaul that has no existing ADR.

### ADR-A: Global `~/.kittify/` as Machine-Level Runtime

**Decision:** `spec-kitty init` bootstraps a single global runtime at `~/.kittify/`. This is the canonical location for missions, globally-installed skills, and agent configuration. Per-project `.kittify/` directories are thin overlays.

**Covers:**
- Why init targets `~/.kittify/` not the project directory
- The distinction between global runtime state and per-project state: missions → global; charter → per-project; agent config → global; feature specs → per-project
- Upgrade behavior: re-running init updates the global runtime without touching projects
- `ensure_runtime()` failure must be surfaced, not silently swallowed

**Supersedes:** The implicit assumption in pre-076 code that init writes per-project templates.

---

### ADR-B: Package-Bundled Templates as Sole Template Source

**Decision:** Template assets are always sourced from the installed spec-kitty-cli package. Remote GitHub tarball download and the `--template-root` CLI flag are removed. The `SPEC_KITTY_TEMPLATE_ROOT` environment variable remains available for maintainers testing template changes locally.

**Covers:**
- Why remote download is unnecessary (pipx distribution guarantees package availability)
- Why `--template-root` CLI flag is removed (no end-user use case; env var is sufficient for maintainers)
- Consequence: `--debug`, `--skip-tls`, `--github-token` are also removed as they were exclusively used by the remote download path
- No network access is required during init

---

### ADR-C: Global Skill Installation; Per-Project Symlinks at Setup Time

**Decision:** Skills are installed canonically to `~/.kittify/agent-skills/{agent}/` by `spec-kitty init`. Per-project agent directories reference skills via symlinks (copy fallback). Per-project wiring is triggered at project setup time, not at machine init time.

**Covers:**
- Why skills are global (single upgrade point; no per-project duplication)
- Symlink-first with copy fallback
- Current implementation installs per-project wiring during init (a known gap to be closed in a follow-on feature)

---

### ADR-D: Charter and Doctrine Are Not Init-Time Concerns

**Decision:** All doctrine/charter interview code (`_run_doctrine_stack_init`, `_run_inline_interview`, `_apply_doctrine_defaults`) is removed from `spec-kitty init`. Charter is a per-project governance artifact authored via `/spec-kitty.charter` after a project exists.

**Covers:**
- Why init previously included charter (historical accident)
- Correct workflow position: `/spec-kitty.charter` runs after `/spec-kitty.specify`
- Impact: init is now stateless with respect to any individual project

---

### ADR-E: Shim Generation Supersedes Script-Type Dispatch

**Decision:** The `.kittify/scripts/bash/` and `.kittify/scripts/powershell/` directories, `--script` flag, and all script-type selection logic are removed. Agent command dispatch was fully replaced by shim generation (`shims/generator.py`), which writes thin markdown files directly into agent command directories. No shell or PowerShell scripts are invoked at runtime.

**Covers:**
- What the old script dispatch model did
- Why shim generation replaced it (simpler, agent-native, no platform detection)
- Why `--script` flag and `.sh`/`.ps1` files are safe to delete

---

### ADR-F: Global Agent Commands Supersede Per-Project Copies; Safe Local Removal Migration

**Decision:** When spec-kitty commands are installed both globally (`~/.kittify/`) and per-project (`.claude/commands/`, etc.), users see duplicate slash commands in their AI tools. The canonical location is global. A migration removes generated per-project command files once global equivalents are confirmed present.

**Covers:**
- Why per-project command files were created historically (pre-global-runtime model)
- Why global is now canonical
- The four safety invariants that must hold before any deletion (global runtime present; global agent commands present; local file has spec-kitty-generated header; invariant failure skips agent entirely)
- The migration must be safe to run on CI machines and developer machines alike

---

### ADR-G: Preferred Agent Roles Removed as Unused Concept

**Decision:** `preferred_implementer` and `preferred_reviewer` are removed from the entire codebase. The fields were stored in `AgentSelectionConfig`, serialized to `config.yaml`, and loaded at startup — but the methods that would act on them (`select_implementer`, `select_reviewer`) were never called anywhere. The entire preference layer was collecting data that no runtime code ever consumed.

**Covers:**
- What the fields were intended for (routing implementation vs review to different agents)
- Why they were never activated (the feature was never fully built)
- A cleanup migration strips these keys from existing `config.yaml` files on upgrade
- `AgentSelectionConfig` is removed entirely; `AgentConfig.selection` field is removed

---

## Assumptions

1. The `spec-kitty agent config` CLI subcommands (add/remove/list/status/sync) remain the mechanism for modifying agent selection after init. Init uses the same underlying config but presents a simplified selection UI for first-time setup.
2. FR-011 through FR-014 (minimal per-project writes) represent the current minimum viable project scaffolding. A future feature may move these to a dedicated `spec-kitty setup` command.
3. `~/.kittify/` is the conventional global home on macOS and Linux (including WSL). Windows native paths are not in scope.
4. The `spec-kitty-command-version` frontmatter header is a reliable marker for spec-kitty-generated command files. Files without this header are treated as user-authored and never touched by Migration B.

---

## Files Requiring Changes

| File | Change |
|------|--------|
| `src/specify_cli/cli/commands/init.py` | Remove 11 flags and all associated processing stages (see tables above) |
| `src/specify_cli/core/agent_config.py` | Remove `AgentSelectionConfig`, `select_implementer`, `select_reviewer`, `selection` serialization |
| `src/specify_cli/template/github_client.py` | Delete file |
| `src/specify_cli/template/manager.py` | Remove `get_local_repo_root`, script-copying logic |
| `src/specify_cli/upgrade/migrations/` | Add Migration A (strip selection keys) and Migration B (remove local command duplicates) |
| `docs/how-to/non-interactive-init.md` | Remove all references to `--preferred-implementer`, `--preferred-reviewer`, `--script` |
| `docs/reference/cli-commands.md` | Remove removed flags from init command reference |
| `docs/reference/configuration.md` | Remove `selection.preferred_implementer`, `selection.preferred_reviewer` entries |
| `docs/how-to/manage-agents.md` | Remove preference references |
| `tests/agent/test_init_command.py` | Remove tests for removed flags |
| `tests/agent/test_agent_config_unit.py` | Remove `preferred_implementer`/`preferred_reviewer` assertions |
| `tests/specify_cli/cli/commands/test_init_doctrine.py` | Delete file |
| `tests/upgrade/migrations/test_m_2_0_1_tool_config_key_rename.py` | Update for preference key removal |

---

## Success Criteria

1. `spec-kitty init` with no arguments completes in under 10 seconds on a machine with an existing global runtime, with no network calls required.
2. The `--help` output for `spec-kitty init` lists no more than 4 flags (`--ai`, `--non-interactive`, `--no-git`, and `--version`).
3. Running `spec-kitty init` on a machine where `~/.kittify/` already exists and is current produces zero file changes.
4. All 7 ADRs described above are authored and committed to `architecture/adrs/`.
5. The test suite passes with no regressions; `test_init_doctrine.py` is deleted; `github_client.py` is deleted.
6. `mypy --strict` passes across all modified files.
7. After `spec-kitty upgrade` on a project with global runtime installed, no duplicate spec-kitty slash commands appear in Claude Code or any other configured agent tool.
8. `preferred_implementer` and `preferred_reviewer` do not appear in any `.kittify/config.yaml` written by the new code.
