# Spec: Init Command Overhaul

**Feature:** 076-init-command-overhaul
**Mission type:** software-dev
**Status:** Specified
**Target branch:** main

---

## Problem Statement

`spec-kitty init` has accumulated significant technical debt. It was originally designed as a per-project installer but has never been coherently redesigned as the global machine-level bootstrapper it needs to be. The result is a command with:

- Dead code paths (.sh/.ps1 script dispatch, remote GitHub tarball download, mission selection, script type selection, doctrine/charter interview)
- Flags that do nothing useful for end users (`--template-root`, `--debug`, `--skip-tls`, `--github-token`, `--preferred-implementer`, `--preferred-reviewer`, `--script`, `--force`)
- Architecturally wrong behavior (installing per-project agent directories at init time; running charter interview before the user has a project)
- No documented architecture for the global `~/.kittify/` runtime vs per-project `.kittify/`

This feature removes all dead code, simplifies the CLI surface to what is actually needed, redesigns init as a global runtime bootstrapper, and captures all resulting architectural decisions as ADRs.

---

## Goals

- `spec-kitty init` becomes a clean, fast, machine-level setup command that bootstraps `~/.kittify/`
- The CLI surface is reduced to only flags that do real work
- All architectural decisions made during this overhaul are documented as ADRs in `architecture/adrs/`
- Existing projects continue to work without modification

## Non-Goals

- Per-project setup (`.kittify/`, `.gitignore`, `.claudeignore`) is out of scope — that belongs in a future `spec-kitty setup` or happens implicitly on first `/spec-kitty.specify`
- Charter/doctrine authoring is out of scope — that belongs in `/spec-kitty.charter`
- Mission selection is out of scope — that belongs in `/spec-kitty.specify`
- No new user-facing features beyond the cleanup

---

## Actors

- **Developer (new install):** Running `spec-kitty init` for the first time on a machine. Needs the global runtime created and agents configured.
- **Developer (existing install):** Running `spec-kitty init` again to add/remove agents or upgrade the global runtime. Must not lose existing agent configuration.

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

---

## Functional Requirements

| ID | Requirement | Status |
|----|-------------|--------|
| FR-001 | `spec-kitty init` defaults to operating in the current directory when no `project_name` argument is given; there is no `--here` flag | Proposed |
| FR-002 | When `project_name` is given, the command creates a new subdirectory and initializes within it | Proposed |
| FR-003 | The command bootstraps `~/.kittify/` as the global runtime if it does not exist or is outdated | Proposed |
| FR-004 | The command detects which AI agents are already installed globally and presents them to the user | Proposed |
| FR-005 | The user can add or remove agents during init; the UI clearly states that changes are machine-wide and affect all projects | Proposed |
| FR-006 | Agent selection is persisted to global agent config (not per-project config) | Proposed |
| FR-007 | Skills are installed to `~/.kittify/` canonical locations; per-project directories reference the global install | Proposed |
| FR-008 | The `--ai` flag accepts a comma-separated list of agent keys for non-interactive agent selection | Proposed |
| FR-009 | The `--non-interactive` flag suppresses all prompts; combined with `--ai`, the command runs fully headless | Proposed |
| FR-010 | The command initializes a git repository in the project directory if one does not exist, unless `--no-git` is given | Proposed |
| FR-011 | The command writes `.gitignore` protection for all possible agent directories in the project | Proposed |
| FR-012 | The command writes a `.claudeignore` file in the project directory | Proposed |
| FR-013 | The command writes project metadata to `.kittify/metadata.yaml` | Proposed |
| FR-014 | The command writes VCS config to `.kittify/config.yaml` | Proposed |
| FR-015 | The command completes without creating or prompting about charter, doctrine, missions, or dashboard | Proposed |
| FR-016 | Re-running init on an already-configured machine is idempotent — no data is lost or overwritten without explicit user action | Proposed |

---

## Flags to Remove

| Flag | Reason |
|------|--------|
| `--here` | Redundant — current directory is the default when no `project_name` is given |
| `--script` / `--script-type` | Dead code — no `.sh`/`.ps1` scripts exist or are invoked; dispatch replaced by shim generation |
| `--preferred-implementer` | Removed — per-agent role assignment is not an init-time concern |
| `--preferred-reviewer` | Removed — per-agent role assignment is not an init-time concern |
| `--force` | Removed with `--here`; no remaining use case |
| `--template-root` | End-user dead path — package-bundled templates are the sole source |
| `--debug` | Was specific to remote template download; removed with that code path |
| `--skip-tls` | Was specific to remote template download; removed with that code path |
| `--github-token` | Was specific to remote template download; removed with that code path |

---

## Code Paths to Remove

| Code Path | Reason |
|-----------|--------|
| Remote GitHub tarball download (`download_and_extract_template`, `github_client.py`) | spec-kitty is distributed via pipx; package templates are always available; remote download is never needed by end users |
| Local-repo template override (`get_local_repo_root`, `SPEC_KITTY_TEMPLATE_ROOT` env var) | Developer-only path with no end-user use case; maintainers can use env var directly if needed without a CLI flag |
| `.kittify/scripts/bash/` and `.kittify/scripts/powershell/` copying and cleanup | Dead code — no scripts are ever invoked; shim generation replaced this model |
| Script type selection (Stage 4) | Entirely driven by the dead `--script` flag |
| Mission selection and activation (Stages 5 and 9) | Missions are per-feature, selected during `/spec-kitty.specify` |
| Preferred implementer/reviewer selection (Stage 3) | Removed concept |
| Doctrine/charter interview (`_run_doctrine_stack_init`, `_run_inline_interview`, `_apply_doctrine_defaults`) | Charter belongs in `/spec-kitty.charter`; running it during machine setup is architecturally wrong |
| REPO_MAP.md / SURFACES.md structure template generation | Not appropriate during machine-level init |
| Dashboard startup (`ensure_dashboard_running`) | Not appropriate during machine-level init |
| Initial git commit of all generated files | init bootstraps a global runtime, not a git project |

---

## Non-Functional Requirements

| ID | Requirement | Status |
|----|-------------|--------|
| NFR-001 | `spec-kitty init` completes in under 10 seconds on a machine with an existing global runtime (no network required) | Proposed |
| NFR-002 | `spec-kitty init --non-interactive --ai claude` exits with code 0 and produces no interactive prompts | Proposed |
| NFR-003 | Re-running init on an already-configured machine produces no changes to existing files unless the runtime is outdated | Proposed |
| NFR-004 | All removed code paths have corresponding test deletions or test updates so the test suite passes cleanly | Proposed |
| NFR-005 | New and modified code paths have 90%+ test coverage consistent with project standards | Proposed |

---

## Constraints

| ID | Constraint | Status |
|----|------------|--------|
| C-001 | The CLI framework is typer; no new framework dependencies are introduced | Proposed |
| C-002 | mypy --strict must pass across all modified files | Proposed |
| C-003 | Existing projects (those with a `.kittify/` already present) must continue to work without any migration step | Proposed |
| C-004 | The `--ai` flag and agent key vocabulary must remain backward-compatible with any documented usage | Proposed |
| C-005 | No per-project agent directories (`.claude/`, `.codex/`, etc.) are created by `spec-kitty init`; those are the responsibility of per-project setup flows | Proposed |

---

## Architecture Decision Records (Deliverables)

A core deliverable of this feature is authoring the following ADRs in `architecture/adrs/`. Each captures a decision made or confirmed during this overhaul that has no existing ADR.

### ADR-A: Global `~/.kittify/` as Machine-Level Runtime

**Decision:** `spec-kitty init` bootstraps a single global runtime at `~/.kittify/`. This is the canonical location for missions, globally-installed skills, and agent configuration. Per-project `.kittify/` directories are thin overlays that reference the global runtime.

**Covers:**
- Why init targets `~/.kittify/` not the project directory
- The distinction between global runtime state and per-project state
- What belongs at each level (missions → global; charter → per-project; agent config → global; feature specs → per-project)
- Upgrade behavior: re-running init updates the global runtime without touching projects

**Supersedes:** The implicit assumption in pre-076 code that init writes per-project templates.

---

### ADR-B: Package-Bundled Templates as Sole Template Source

**Decision:** Template assets are always sourced from the installed spec-kitty-cli package. Remote GitHub tarball download and local-repo override paths are removed from the end-user CLI. Developer testing of template changes uses the `SPEC_KITTY_TEMPLATE_ROOT` environment variable directly, not a CLI flag.

**Covers:**
- Why remote download is unnecessary (pipx distribution guarantees package availability)
- Why `--template-root` CLI flag is removed (no end-user use case)
- How maintainers test template changes locally (env var, no flag needed)
- Consequence: no network access required during init

---

### ADR-C: Global Skill Installation with Per-Project Symlinks

**Decision:** Skills are installed canonically to `~/.kittify/agent-skills/{agent}/`. Per-project agent directories reference skills via symlinks where the filesystem supports it, falling back to copies. `spec-kitty init` installs skills globally; per-project wiring happens at project setup time, not at machine init time.

**Covers:**
- Why skills are global (avoid per-project duplication; single upgrade point)
- Symlink-first strategy with copy fallback
- What `spec-kitty init` writes vs what per-project setup writes

---

### ADR-D: Charter and Doctrine Are Not Init-Time Concerns

**Decision:** The doctrine/charter interview, `_run_doctrine_stack_init`, and all related prompts are removed from `spec-kitty init`. Charter is a per-project governance artifact authored via `/spec-kitty.charter` after a project exists. Machine setup (init) has no knowledge of project governance.

**Covers:**
- Why init previously included charter (historical accident, not intentional design)
- The correct point in the workflow to introduce charter (`/spec-kitty.charter`, after `/spec-kitty.specify`)
- Impact: init is now stateless with respect to any individual project

---

### ADR-E: Shim Generation Supersedes Script-Type Dispatch

**Decision:** The `.kittify/scripts/bash/` and `.kittify/scripts/powershell/` directories, `--script` flag, and all script-type selection logic are removed. Agent command dispatch was fully replaced by shim generation (`shims/generator.py`), which writes thin markdown files directly into agent command directories. No shell or PowerShell scripts are invoked at runtime.

**Covers:**
- What the old script dispatch model did
- Why shim generation replaced it (simpler, agent-native, no platform detection needed)
- Why the `--script` flag and `.sh`/`.ps1` files are safe to delete (nothing invokes them)
- Reference to the shim generator as the canonical dispatch mechanism

---

## Assumptions

1. The `spec-kitty agent config` CLI subcommands (add/remove/list/status/sync) introduced in ADR-6 remain the mechanism for modifying agent selection after init. Init uses the same underlying config but presents a simplified selection UI for first-time setup.
2. "Per-project setup" (creating `.kittify/` in a project, writing `.claudeignore`, etc.) is out of scope for this feature. FR-011 through FR-014 represent the minimal project-level writes that init currently does and that are not obviously wrong; a future feature may move these to a dedicated `spec-kitty setup` command.
3. `~/.kittify/` is the conventional global home on all platforms (macOS, Linux, Windows via WSL). Windows native path behavior is not in scope for this overhaul.

---

## Success Criteria

1. `spec-kitty init` with no arguments completes in under 10 seconds on a machine with an existing global runtime, with no network calls required.
2. The `--help` output for `spec-kitty init` lists no more than 4 flags (`--ai`, `--non-interactive`, `--no-git`, and optionally a version/debug flag).
3. Running `spec-kitty init` on a machine where `~/.kittify/` already exists produces zero file changes to the global runtime when the installed version matches.
4. All 5 ADRs described above are authored and committed to `architecture/adrs/`.
5. The test suite passes with no regressions; tests for removed code paths are deleted.
6. `mypy --strict` passes across all modified files.
