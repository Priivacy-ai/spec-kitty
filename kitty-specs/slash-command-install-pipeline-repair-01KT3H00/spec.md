# Slash Command Install Pipeline Repair

**Mission ID**: 01KT3H00ZCKSC4KS6C7W68ZQZP  
**Mission slug**: slash-command-install-pipeline-repair-01KT3H00  
**Mission type**: software-dev  
**Target branch**: main  
**GitHub issues**: #1608, #1609, #1610

---

## Purpose

Repair the broken global slash command installation pipeline so that all configured slash-command agents always have the complete canonical set of spec-kitty commands installed, detectable, and self-healing.

Three inter-dependent bugs prevent spec-kitty commands from being reliably installed and verified for Claude and other slash-command agents:

1. **#1608 — Broken template resolver**: `_get_command_templates_dir()` returns `None` after templates moved to the doctrine layer (`src/doctrine/missions/mission-steps/`), so `ensure_global_agent_commands()` silently aborts installation of 8 prompt-driven commands on every CLI startup.
2. **#1609 — Doctor blind spot**: `doctor skills --fix` only audits the Agent Skills pipeline (`.agents/skills/`, codex/vibe/pi/letta). Claude and all other slash-command agents are structurally invisible to it; it reports false-positive healthy.
3. **#1610 — Dev bootstrap gap**: The dev repo has no path to ensure a working developer environment. `spec-kitty upgrade` reports "up to date" while 8 commands are missing; there is no hook, script, or doctor check that detects or repairs this on a fresh clone or after a template change.

Fix #1608 unblocks #1609 and #1610. All three are required for a complete remedy.

---

## Actors

- **Developer/operator**: runs `spec-kitty` commands and expects slash commands to be present and complete in their AI coding agent.
- **spec-kitty CLI startup**: calls `ensure_global_agent_commands()` at every invocation; responsible for keeping global command files current.
- **`doctor skills`**: health check surface; must detect and repair gaps without operator intervention when `--fix` is passed.

---

## User Scenarios & Testing

### Primary scenario — fresh clone, `claude` configured

1. Developer clones the spec-kitty repo (or a consumer project that has `claude` in `config.yaml`).
2. Runs any `spec-kitty` command.
3. Opens Claude Code and invokes `/spec-kitty.specify`.
4. **Expected**: command is present and executes correctly.
5. **Current failure**: 8 of 15 commands are missing; `/spec-kitty.specify` is not available.

### Secondary scenario — `doctor skills --fix` repairs a degraded install

1. Developer removes `~/.claude/commands/spec-kitty.specify.md` (simulating corruption or a missed install).
2. Runs `spec-kitty doctor skills --fix`.
3. **Expected**: doctor detects the missing file and reinstalls it.
4. **Current failure**: doctor reports healthy; missing file is not detected.

### Tertiary scenario — dev repo contributor onboarding

1. New contributor clones the spec-kitty source repo and runs `uv sync`.
2. Installs the package in editable mode (`pip install -e .`).
3. Runs any `spec-kitty` command OR `make dev-setup`.
4. **Expected**: all 15 canonical commands are present in `~/.claude/commands/` (and equivalent dirs for other configured agents).
5. **Current failure**: 8 prompt-driven commands are never written; `upgrade` reports up to date.

### Edge case — agent not in `config.yaml`

- Doctor and the installer must only act on agents present in `config.yaml`'s `available` list.
- An agent directory that exists on disk but is not in `config.yaml` must not be touched.

---

## Functional Requirements

| ID | Description | Status |
|----|-------------|--------|
| FR-001 | `_get_command_templates_dir()` must resolve the correct template directory from the doctrine layer (`src/doctrine/missions/mission-steps/software-dev/*/prompt.md`) in both editable and wheel installs. | Required |
| FR-002 | `_sync_agent_commands()` must enumerate templates from the per-step subdirectory layout (`{step}/prompt.md`) rather than a flat `*.md` glob. | Required |
| FR-003 | After the resolver fix, `ensure_global_agent_commands()` must install all commands in `PROMPT_DRIVEN_COMMANDS` (currently: `specify`, `plan`, `tasks`, `tasks-outline`, `tasks-packages`, `analyze`, `charter`, `research`) to the global command directory for each configured slash-command agent. The count is derived from the runtime set, not hardcoded here. | Required |
| FR-004 | `ensure_global_agent_commands()` must write the version lock only after all command files are successfully written, so a partial install does not mark the run as complete. If sync fails for any configured agent, the lock must not be updated for any agent — the try/except wraps the full agent-iteration loop, not individual agents. | Required |
| FR-005 | `doctor skills` must check, for each agent in `config.yaml`'s `available` list that uses the slash-command pipeline, whether all canonical commands are present and match the current source. | Required |
| FR-006 | `doctor skills --fix` must invoke `ensure_global_agent_commands()` (or equivalent) to reinstall missing or stale slash-command files for configured agents, scoped to only those in `config.yaml`. | Required |
| FR-007 | `doctor skills` must report missing slash-command files explicitly by name; it must not report healthy when files are absent. | Required |
| FR-008 | A `make dev-setup` target (or equivalent contributor script) must exist and must invoke the global command installer, so contributors can bootstrap a working dev environment with a single command. | Required |
| FR-009 | After installing the package (editable or wheel), the first invocation of any `spec-kitty` CLI command must ensure all canonical global commands are installed for configured agents. The approved implementation mechanism is Layer C (CLI startup auto-repair via `ensure_global_agent_commands()`, which already runs on every invocation). No separate post-install hook is used; this avoids fragile hook mechanisms and satisfies C-003. **Limitation**: a developer who installs in editable mode and opens Claude Code without running any `spec-kitty` command directly will not yet have commands installed until their first CLI invocation (e.g., via `make dev-setup`). | Required |
| FR-010 | The bootstrap path (`make dev-setup`, CLI startup auto-repair, and `doctor skills --fix`) must be idempotent: repeated execution must not duplicate files or produce errors. | Required |
| FR-011 | The fix must not touch agent directories for agents not present in `config.yaml`'s `available` list, even if those directories exist on disk. | Required |
| FR-012 | The agent-commands version lock must be updated to the current CLI version after a successful full install, so subsequent CLI startups skip the slow path. | Required |

---

## Non-Functional Requirements

| ID | Description | Threshold | Status |
|----|-------------|-----------|--------|
| NFR-001 | The slow-path install (when lock version mismatches) must complete within 5 seconds on a warm filesystem for a project with ≤4 configured agents. The fast path (lock current) must complete within the charter's standard < 2-second CLI operation budget. Note: the 5-second threshold applies only to the cold/upgrade scenario, not to normal CLI invocations. | ≤ 5 seconds (slow path); < 2 seconds (fast path) | Required |
| NFR-002 | `doctor skills` (read-only health check, no `--fix`) must complete within 3 seconds on a first run. Subsequent runs with a warm filesystem are expected to be < 2 seconds per the charter's CLI operation budget. | ≤ 3 seconds | Required |
| NFR-003 | The fix must not introduce regressions in the existing Agent Skills pipeline (codex/vibe/pi/letta); existing `doctor skills` behaviour for those agents must be unchanged. | Zero regressions on Agent Skills pipeline | Required |
| NFR-004 | All new code paths must be covered by tests (unit or integration); no new branch may be left uncovered. | 100% branch coverage on new code | Required |
| NFR-005 | All new code must pass `mypy --strict` and `ruff check`. | Zero mypy errors, zero ruff violations | Required |

---

## Constraints

| ID | Description | Status |
|----|-------------|--------|
| C-001 | The fix for `_get_command_templates_dir()` must work in both editable dev installs and wheel installs without conditional logic that hardcodes the dev repo layout. | Required |
| C-002 | `doctor skills --fix` must only act on agents in `config.yaml`'s `available` list; it must never create directories or install files for unconfigured agents. | Required |
| C-003 | The editable-install hook must not depend on `make` being available; it must use a mechanism that works in all supported environments (Linux, macOS, Windows 10+). | Required |
| C-004 | No changes to the Agent Skills manifest format or the `.agents/skills/` pipeline are required by this mission. | Constraint (scope boundary) |
| C-005 | The version lock file path and format must remain backward-compatible; no migration is needed for existing installs. | Required |

---

## Assumptions

- The doctrine package (`src/doctrine/`) ships as part of the spec-kitty distribution and is always present alongside the CLI.
- The 8 prompt-driven commands (`specify`, `plan`, `tasks`, `tasks-outline`, `tasks-packages`, `analyze`, `charter`, `research`) are stable and no renaming is needed as part of this mission. The 7 CLI-driven shim commands are (`implement`, `review`, `accept`, `merge`, `status`, `next`, `advise`). Together they constitute the 15 canonical commands referenced in success criteria.
- `config.yaml` is always present in `.kittify/` for any project that has run `spec-kitty init`; projects without `config.yaml` fall back to the existing legacy behaviour (all agents).
- The `make` toolchain is available in the dev environment but cannot be assumed for end-user installations (hence C-003).

---

## Success Criteria

1. After running any `spec-kitty` command in a project with `claude` configured, all 15 canonical commands are present in `~/.claude/commands/` (8 prompt-driven + 7 CLI-driven shims).
2. `spec-kitty doctor skills` reports the correct health state (missing files are reported as gaps, not suppressed).
3. `spec-kitty doctor skills --fix` repairs a degraded install without operator intervention, for each agent in `config.yaml`.
4. A contributor who clones the dev repo and runs `make dev-setup` (or installs in editable mode) has all commands present within one step.
5. `spec-kitty upgrade --dry-run` and `spec-kitty doctor skills` agree on health state; no more false-positive "up to date" while commands are missing.
6. The Agent Skills pipeline (codex/vibe/pi/letta) is unaffected: existing tests pass without modification.

---

## Key Entities

| Entity | Description |
|--------|-------------|
| `_get_command_templates_dir()` | Resolver in `src/specify_cli/runtime/agent_commands.py`; returns the directory containing prompt-driven command templates. Must be updated to use the doctrine layer path. |
| `_sync_agent_commands()` | Installer loop in the same module; iterates templates and writes output files. Glob pattern must change from flat `*.md` to per-step `{step}/prompt.md`. |
| `ensure_global_agent_commands()` | Orchestrator called at CLI startup; version-locked with `agent-commands.lock`. Calls resolver then sync. |
| `doctor skills` subcommand | Health check in `src/specify_cli/cli/commands/doctor.py`; must gain a slash-command audit path alongside the existing Agent Skills audit. |
| `AGENT_COMMAND_CONFIG` | Dict in `src/specify_cli/core/config.py` mapping agent keys to their global command directory, extension, and arg format. Source of truth for slash-command agents. |
| `config.yaml` available list | `.kittify/config.yaml`; determines which agents are active. Doctor and installer must respect this list (FR-011, C-002). |
| `agent-commands.lock` | Version lock file in `~/.kittify/cache/`; gates the slow-path install on every CLI startup. Must be updated after a successful complete install (FR-012). |
| Stale command file | A command file is *stale* when its version marker (first `_VERSION_MARKER_HEAD_LINES` lines) does not contain the string `"{_VERSION_MARKER_PREFIX} {current_version}"`. A file is *missing* when it does not exist on disk. Both states count as gaps for `doctor skills` and `--fix`. |
| Doctrine layer templates | `src/doctrine/missions/mission-steps/software-dev/{step}/prompt.md`; canonical source for prompt-driven commands. |

---

## Dependencies

- GitHub #1608: resolver + renderer fix (prerequisite for #1609 and #1610 functional fixes)
- GitHub #1609: doctor slash-command audit (depends on #1608 for `--fix` to work)
- GitHub #1610: dev bootstrap (depends on #1608; layered with #1609)
