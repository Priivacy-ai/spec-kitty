# Mission Specification: CLI Upgrade Nag and Lazy Project Migration

**Mission ID**: `01KQ6YDNMX2X2AN4WH43R5K2ZS`
**Mission slug**: `cli-upgrade-nag-lazy-project-migrations-01KQ6YDN`
**Mission type**: `software-dev`
**Target branch**: `main`
**Created**: 2026-04-27
**Source brief**: `start-here.md` · GitHub issue [Priivacy-ai/spec-kitty#812](https://github.com/Priivacy-ai/spec-kitty/issues/812)

---

## Purpose

**TL;DR.** Separate the *"your CLI is out of date"* nag from the *"this project needs migrations"* check, so users get a passive warning for one and a precise, lazy block for the other — only for the project they are currently in.

**Context.** Spec Kitty's CLI today conflates installed-runtime updates with per-project schema migrations. Users get noisy or misleading guidance and there is no reliable way to know whether a command is safe to run. This mission introduces a passive throttled CLI-update nag plus a lazy current-project compatibility check, with no global registry, no upgrade-all-projects workflow, and no silent self-update. The outcome: users always know exactly what to do next and never lose work to an unexpected upgrade.

---

## Problem Statement

Spec Kitty currently has two overlapping but distinct upgrade concerns:

1. The installed `spec-kitty` CLI/runtime can be out of date relative to the latest released version.
2. A specific project's `.kittify` metadata, schema, templates, generated agent commands, skills, or mission state can need migration to match the installed CLI.

Today these concerns are tangled. The CLI cannot tell the user *which* of the two is the issue, cannot block only when blocking is justified, and cannot offer concrete next steps. Worse, users who have many Spec Kitty projects on disk should not be forced to migrate every project whenever the CLI changes — Spec Kitty has no reliable global project registry, and correctness only depends on the project the user is currently inside.

The mission cleanly splits these two concerns and treats them with the right level of friction:

- **CLI freshness** is a *passive nag*: a single line of guidance, throttled, never blocking a compatible command.
- **Current-project compatibility** is a *lazy gate*: checked only when the user is inside a Spec Kitty project, and only blocking when the command would otherwise mutate state under an incompatible schema.

No normal command startup writes files, performs uncached network calls in CI, or self-updates.

---

## Stakeholders & Primary Actor

- **Primary actor**: a Spec Kitty CLI user (developer or AI agent driver) running `spec-kitty …` from a terminal, either inside a Spec Kitty project or anywhere on disk.
- **Secondary actors**:
  - CI / non-interactive automation invoking `spec-kitty` (must remain deterministic).
  - Maintainers writing project migrations (preserved migration history semantics).
  - Documentation readers needing a clear mental model of "upgrade CLI" vs "migrate this project".

---

## User Scenarios & Testing

### Scenario A — Compatible CLI, newer release available

1. User runs any normal `spec-kitty` command from a fresh shell (cache warm or first invocation of the day).
2. CLI starts. The compatibility planner consults a cached "latest CLI" record (or, on first interactive call of a throttle window, fetches it with a short timeout).
3. A single human-readable nag line is printed *before* the command output:

   ```
   Spec Kitty 2.0.14 is available; you have 2.0.11.
   Upgrade with: pipx upgrade spec-kitty-cli
   ```
4. The requested command proceeds normally with its full exit semantics. No file writes from the nag path.
5. Subsequent invocations within the throttle window do not re-print the nag.

**Acceptance**: AC-001.

### Scenario B — Stale, migratable project

1. User runs an unsafe command (for example `spec-kitty next --agent claude`) inside a project whose `.kittify/metadata.yaml` reports an older schema version that the installed CLI knows how to migrate.
2. The compatibility planner detects pending current-project migrations.
3. CLI **blocks** the command (non-zero exit), prints:

   ```
   This project needs Spec Kitty project migrations before this command can run.
   Run: spec-kitty upgrade
   Preview first: spec-kitty upgrade --dry-run
   ```
4. The user runs `spec-kitty upgrade --dry-run`, sees the plan, then `spec-kitty upgrade` (or `spec-kitty upgrade --yes` non-interactively) and the project is migrated. The original command then succeeds.

**Acceptance**: AC-002.

### Scenario C — Project too new for installed CLI

1. User runs an unsafe command inside a project whose schema is *newer* than the installed CLI supports.
2. The CLI **blocks** with explicit guidance:

   ```
   This project uses Spec Kitty project schema 7, but this CLI supports up to schema 6.
   Upgrade the CLI: pipx upgrade spec-kitty-cli
   ```
3. No project files are touched.

**Acceptance**: AC-003.

### Scenario D — Dry-run preview

1. User runs `spec-kitty upgrade --dry-run` (or `spec-kitty upgrade --dry-run --json`) inside a project.
2. CLI prints, in the human-readable form:

   ```
   CLI: current 2.0.11, latest 2.0.14
   Project: schema 5, target schema 7
   Migrations:
     <migration_id_1>
     <migration_id_2>
     <migration_id_3>
   ```

   and, with `--json`, returns a structured plan with the same information plus per-migration *would-modify* file lists where practical.
3. **No project files are written.**

**Acceptance**: AC-004, FR-019.

### Scenario E — Lazy, current-project apply

1. User runs `spec-kitty upgrade --project --yes` (or `--project --force` — see C-006) inside a project.
2. CLI restricts behavior to current-project compatibility and applies only that project's required migrations, idempotently and in order. Other projects on disk are untouched.
3. CLI prints a concise summary of applied migrations.

**Acceptance**: AC-005, FR-015, FR-018, FR-020, FR-021.

### Scenario F — CLI guidance outside a project

1. User runs `spec-kitty upgrade --cli` (or `spec-kitty upgrade` with no project context) from any directory.
2. CLI prints install-method-specific upgrade instructions when the install method can be detected (pipx, pip, brew, system package manager). When the install method cannot be detected, CLI prints a safe manual-upgrade fallback rather than guessing.
3. CLI does **not** fail with "not a Spec Kitty project".

**Acceptance**: AC-006, AC-007, FR-006, FR-007, FR-014, FR-016.

### Scenario G — Help / read-only commands under stale schema

1. User is in a project whose schema is incompatible (older, newer, or missing).
2. User runs `--help`, `--version`, `spec-kitty status`, `spec-kitty doctor` (diagnostic mode), or any `spec-kitty upgrade*` subcommand.
3. CLI runs the command normally without blocking, while still optionally rendering the throttled nag.

**Acceptance**: AC-008, FR-011.

### Scenario H — CI / non-interactive

1. CLI is invoked in CI (`CI=1`, no TTY, or with `--no-nag` / equivalent quiet flag).
2. The nag path performs **no** network calls, prints no nag line, prompts for nothing, and never self-updates. Compatibility checks for the current project still run when applicable.

**Acceptance**: AC-009, FR-005, NFR-002, NFR-004.

### Scenario I — Unknown install method

1. User is on a CLI build whose install method cannot be detected.
2. The nag, when shown, includes a safe manual-upgrade message (a documented fallback) instead of an incorrect guess.
3. JSON output flags `install_method = "unknown"`.

**Acceptance**: AC-009, FR-007, FR-023.

### Scenario J — Fresh nag cache

1. The throttle cache is fresh (e.g. updated less than the throttle window ago) and reports no newer CLI version.
2. Next invocation prints no nag, performs no network call, and adds less than 100 ms to startup.

**Acceptance**: AC-009, NFR-001.

### Edge cases

- Network is offline or PyPI returns an unexpected payload while the throttle window is due for refresh — fail open: no stack trace, no blocking, optionally a debug-level note.
- `.kittify/metadata.yaml` is corrupt or missing required fields — treated as "project compatibility unknown" and blocks unsafe commands with a remediation message; safe commands still run.
- User invokes `spec-kitty upgrade --dry-run` outside any project — shows CLI status only and exits cleanly.
- User passes both `--project` and `--cli` — CLI rejects the combination with a clear error.
- User passes `--yes` and `--force` together — both are honored (treated as compatible synonyms per the FR-017 alias direction; see Assumptions A-006).
- `dashboard` or `doctor` is invoked in a mode that *would* mutate state under an incompatible schema — that mode is treated as **unsafe** and is blocked with the same migration guidance as Scenario B/C.

### Always-true rules

- The nag never blocks compatible commands.
- No normal command startup writes project files.
- CI / non-interactive sessions never make uncached network calls and never self-update.
- Project migrations remain idempotent and ordered.
- The CLI never decides what to do for a project the user is not currently inside.

---

## Domain Language

| Canonical term | Definition | Avoid |
|---|---|---|
| **CLI update** | A newer released `spec-kitty` runtime/package is available than what the user has installed. Concerns the *installed binary*, not any project. | "self-update" (implies automatic), "upgrade" alone (ambiguous) |
| **Project migration** | A change applied to one project's `.kittify/` so its schema, templates, generated agent commands, skills, and metadata match the installed CLI. Always scoped to one project. | "global upgrade", "all-projects upgrade" |
| **Current project** | The Spec Kitty project (if any) that contains the working directory in which the CLI was invoked. | "the workspace", "this repo" (unqualified) |
| **Compatibility planner** | The internal component that, given the installed CLI version and the current project's metadata, returns a structured plan describing CLI freshness, project schema status, blocking decisions, and any pending migrations. | "checker", "detector" (overloaded with existing modules) |
| **Nag** | A passive, throttled, single-line user-facing notification about CLI freshness. Never blocks. | "warning" (implies actionable error), "alert" |
| **Throttle window** | The time interval during which a previously-shown nag is suppressed and no network check is repeated. | "cooldown" |
| **Safe command** | A CLI command that may run under an incompatible current-project schema without risk of corrupting or misinterpreting state. See "Safe / Unsafe command classification". | "read-only" (some safe commands print derived state) |
| **Unsafe command** | Any command that mutates `.kittify/`, mission state, worktrees, or is documented to require a current schema. | "writing command" |
| **Install method** | The detected mechanism the user used to install the CLI: pipx, pip user, pip system, brew, package manager, source/dev install, or unknown. Drives the upgrade hint. | "installer" |

---

## Safe / Unsafe Command Classification

This is the contract used by FR-008/FR-011 and AC-008. The full definitive list lives in the planning phase, but the rule is fixed here:

**Safe under incompatible current-project schema** (allowed to proceed; nag may still print):
- `--help`, `--version` on every command and subcommand.
- `spec-kitty status` (read-only mission/WP status).
- `spec-kitty dashboard` *only when invoked in a purely read-only mode*. Any dashboard mode that would initialize missing project state, write cache or config files, start sync, or repair project files is **unsafe** and is blocked under incompatible schema.
- `spec-kitty doctor` *only in its diagnostic / read-only mode*. Any `doctor` mode that fixes, repairs, or applies changes is **unsafe** and is blocked.
- All `spec-kitty upgrade …` subcommands and their flags (these are the remediation path and must always be reachable).
- All `spec-kitty agent …` subcommands that are read-only (for example `agent context resolve`, `agent tasks status`, `agent mission branch-context`).

**Unsafe under incompatible current-project schema** (blocked with explicit guidance):
- `spec-kitty next`, `spec-kitty implement`, `spec-kitty plan`, `spec-kitty tasks*`, `spec-kitty merge`, `spec-kitty accept`, `spec-kitty review`.
- Any command or mode that mutates `.kittify/`, mission state, or worktrees, including the write/init/sync/repair modes of `dashboard` and `doctor` mentioned above.
- Anything marked unsafe by the compatibility planner because the command's behavior is documented to require a matching schema.

The mode-vs-command split for `dashboard` and `doctor` is deliberate: invocation-time *mode* determines safety, not just the top-level command name.

---

## Functional Requirements

| ID | Requirement | Status |
|---|---|---|
| FR-001 | The CLI shall distinguish CLI/runtime update status from current-project migration status in every status surface (human, JSON, exit code). | Approved |
| FR-002 | On normal CLI startup, the CLI shall be able to show a throttled passive nag when a newer `spec-kitty` CLI version is available and the current command can proceed safely. | Approved |
| FR-003 | The passive CLI nag shall not block compatible commands. | Approved |
| FR-004 | The passive CLI nag shall be throttled so users are not warned on every invocation; the throttle window shall default to once per 24 hours per user, configurable via documented setting. | Approved |
| FR-005 | The passive CLI nag shall not perform network checks in CI or non-interactive automation unless explicitly requested via an opt-in flag or environment variable. | Approved |
| FR-006 | The passive CLI nag shall provide exact upgrade instructions when the install method can be detected (e.g., `pipx upgrade spec-kitty-cli`, `pip install --upgrade spec-kitty-cli`, `brew upgrade spec-kitty-cli`). | Approved |
| FR-007 | If the install method cannot be detected, the CLI shall provide a documented safe manual upgrade message instead of guessing an installer. | Approved |
| FR-008 | When run inside a Spec Kitty project, the CLI shall check the current project's schema/version compatibility against the installed CLI before any unsafe state-mutating command proceeds. | Approved |
| FR-009 | If the current project is older but can be migrated by the installed CLI, the CLI shall block the unsafe command with a non-zero exit and shall direct the user to run `spec-kitty upgrade` (and `spec-kitty upgrade --dry-run` for a preview). | Approved |
| FR-010 | If the current project requires a newer CLI than the installed CLI supports, the CLI shall block unsafe commands with a non-zero exit and shall direct the user to upgrade the CLI first. | Approved |
| FR-011 | Read-only, help, diagnostic-mode, and upgrade-related commands (per the Safe/Unsafe Command Classification section) shall remain available even if current-project compatibility is stale. | Approved |
| FR-012 | `spec-kitty upgrade --dry-run` shall show CLI freshness status, current-project status, compatibility decision, and the current-project migration plan, all without writing any project files. | Approved |
| FR-013 | `spec-kitty upgrade` run inside a project shall (a) check CLI status, (b) check current-project compatibility, and (c) plan and apply only the current project's needed migrations. | Approved |
| FR-014 | `spec-kitty upgrade` run outside a project shall not fail with "not a Spec Kitty project"; it shall fall through to CLI update guidance behavior. | Approved |
| FR-015 | `spec-kitty upgrade --project` shall restrict behavior to current-project compatibility and migrations and shall print no CLI-only output. | Approved |
| FR-016 | `spec-kitty upgrade --cli` shall restrict behavior to CLI update guidance (or supported self-upgrade behavior) and shall not attempt project migrations. | Approved |
| FR-017 | `spec-kitty upgrade --yes` shall provide non-interactive confirmation for writes; existing `--force` shall be preserved as a backward-compatible alias (see Assumptions A-006). | Approved |
| FR-018 | Project migrations shall remain idempotent and ordered, preserving the existing migration registry contract. | Approved |
| FR-019 | Project migrations shall report the files they would modify during dry-run whenever the migration can compute that list without executing side effects. | Approved |
| FR-020 | The implementation shall not introduce any "upgrade all projects" command or behavior in this first version. | Approved |
| FR-021 | The implementation shall not introduce a global project registry, recent-project cache, or cross-project state in this first version. | Approved |
| FR-022 | The CLI shall expose a structured JSON output for upgrade planning (`spec-kitty upgrade --dry-run --json` and `spec-kitty upgrade --json`) suitable for tests, automation, and scripting. The JSON shape shall be stable across patch releases. | Approved |
| FR-023 | User-facing messages shall clearly distinguish at least these cases, both in human output and JSON: *cli_update_available*, *project_migration_needed*, *project_too_new_for_cli*, *project_not_initialized*, and *install_method_unknown*. | Approved |
| FR-024 | The compatibility decision shall be exposed as a structured plan from a single internal compatibility planner; CLI command and UI rendering layers shall consume the planner's output rather than recomputing compatibility independently. | Approved |
| FR-025 | The throttle nag cache shall be invalidated when the installed CLI version changes, so a fresh install does not silently reuse the previous CLI's nag state. | Approved |

---

## Non-Functional Requirements

| ID | Requirement | Measurable threshold | Status |
|---|---|---|---|
| NFR-001 | Normal CLI startup overhead from upgrade checks shall be small when the nag cache is fresh. | < 100 ms added to startup, measured on a representative dev machine over a 50-run median. | Approved |
| NFR-002 | Network-based latest-version checks shall have a short timeout and shall fail open. | Timeout ≤ 2 s; on timeout/error, the nag is suppressed silently (no stack trace at default verbosity). | Approved |
| NFR-003 | No normal command startup path shall write project files. | Zero file writes under `.kittify/` or kitty-specs during any non-`upgrade` command's startup, verified by test. | Approved |
| NFR-004 | CI and non-interactive command behavior shall be deterministic. | No prompts, no uncached network access, no self-update; verified by CLI tests with `CI=1` and no TTY. | Approved |
| NFR-005 | Upgrade planning shall be testable without contacting PyPI, GitHub, or the network. | Latest-version source is injectable; planner unit tests reach 90%+ coverage on planner logic without network. | Approved |
| NFR-006 | The design shall preserve existing project upgrade behavior and migration history semantics. | Existing migration tests under `tests/specify_cli/upgrade/` continue to pass unchanged unless an incompatibility is documented in the plan. | Approved |
| NFR-007 | User-facing terminal output shall be concise and actionable. | Nag is one line in the default case; block messages are ≤ 4 lines and always include the exact remediation command. | Approved |
| NFR-008 | The implementation shall not introduce a SaaS, tracker, hosted auth, or sync dependency for local upgrade checks. | No new outbound calls to spec-kitty-saas, spec-kitty-tracker, or any hosted Spec Kitty service from upgrade or compatibility paths. | Approved |
| NFR-009 | The throttle window value shall be configurable by users without source edits. | A documented configuration setting (e.g., `~/.config/spec-kitty/upgrade.yaml` or environment variable) overrides the 24h default. | Approved |

---

## Constraints

| ID | Constraint | Status |
|---|---|---|
| C-001 | Work shall be confined to the `spec-kitty` repository for the first version. No changes to `spec-kitty-saas`, `spec-kitty-tracker`, or other repos. | Approved |
| C-002 | This mission shall not add a project registry or recent-project cache. | Approved |
| C-003 | This mission shall not implement an "upgrade all existing projects" command. | Approved |
| C-004 | This mission shall not implement forced CLI self-update during normal command startup. | Approved |
| C-005 | This mission shall not add tracker rollout gating to `spec-kitty-tracker`. | Approved |
| C-006 | Existing `spec-kitty upgrade` flags (`--dry-run`, `--force`, `--target`, `--json`, `--verbose`, `--no-worktrees`) shall remain working. Any deprecation must be additive (alias-style) within this mission. | Approved |
| C-007 | Implementation shall avoid hosted SaaS sync assumptions. This is local CLI/project compatibility work. | Approved |
| C-008 | The compatibility planner shall be the single authority for "is this command safe?" decisions; existing surfaces (`core.version_checker`, `migration.gate`, `upgrade.detector`) shall be unified behind, layered under, or replaced by it (final shape is a plan-phase decision). | Approved |
| C-009 | The mission shall not introduce a new mandatory runtime dependency outside the existing project tech baseline (`typer`, `rich`, `ruamel.yaml`, plus stdlib). Network access uses an existing or stdlib HTTP client. | Approved |

---

## Success Criteria

| ID | Outcome | How verified |
|---|---|---|
| SC-001 | Users with an out-of-date CLI in a compatible project see, at most once per 24 hours per user, a single-line nag and the originally-requested command still completes successfully. | CLI integration test: simulated newer release + warm cache → nag printed once → command exit code unchanged. |
| SC-002 | Users in a stale-but-migratable project who run an unsafe command get a non-zero exit and a remediation message naming the exact command to run, in under one second when the cache is warm. | CLI integration test against fixture project with older schema. |
| SC-003 | Users in a too-new project who run an unsafe command get a non-zero exit and a remediation message naming the exact CLI upgrade command for their detected install method, in under one second when the cache is warm. | CLI integration test against fixture project with newer schema. |
| SC-004 | `spec-kitty upgrade --dry-run --json` returns a stable, documented JSON plan that downstream tools can parse, in 100% of supported scenarios (compatible, stale-migratable, too-new, no-project, unknown-install). | JSON schema test + golden-file tests across all scenarios. |
| SC-005 | Running any normal Spec Kitty command in CI (`CI=1`, no TTY) produces zero outbound network calls from the upgrade nag path, in 100% of test runs. | CLI integration test with mocked network — assertion: zero requests issued from nag path. |
| SC-006 | Help / `--version` / `status` / read-only `dashboard` / diagnostic-mode `doctor` / all `upgrade` subcommands remain runnable in a project with an incompatible schema, in 100% of test scenarios. | CLI integration test matrix across the safe-command list. |
| SC-007 | Running `spec-kitty upgrade --project --yes` in a stale project applies only that project's pending migrations, leaves all other on-disk projects untouched, and reports a concise summary that names every migration applied. | Multi-project fixture test: assert only the current project changed; assert idempotent re-run is a no-op. |
| SC-008 | The documentation set (in `docs/how-to/install-and-upgrade.md`) explains the difference between "upgrade the CLI" and "migrate this project" in plain prose, with at least one worked example for each scenario in FR-023. | Documentation review during mission acceptance. |

These criteria are all user-facing or test-facing; none of them depend on internal implementation choices.

---

## Key Entities

These are the conceptual objects the spec needs to refer to. Field-level shapes belong to the plan phase.

- **Compatibility plan** — the structured output of the compatibility planner. Includes: installed CLI version, latest known CLI version (and source / staleness), current-project schema (or "no project" / "unreadable"), required-CLI schema range for the project, decision (allow / nag-only / block-migrate / block-cli-upgrade / block-corrupt-metadata), pending current-project migration list, install method, and a render-ready human message + a stable JSON form.
- **Nag cache record** — per-user persisted record of "latest known CLI version", timestamp of last fetch, and timestamp of last nag display. Invalidated on installed-CLI version change (FR-025). Stored under a per-user cache directory (Assumptions A-001).
- **Current-project metadata** — the existing `.kittify/metadata.yaml` augmented as needed to express minimum and target schema versions. Backward-compatible with current files.
- **Latest-version source** — an injectable abstraction with at least one concrete implementation (Assumptions A-002). Returns the latest published `spec-kitty` version or signals "unknown".
- **Install-method descriptor** — a small enumeration (`pipx`, `pip-user`, `pip-system`, `brew`, `system-package`, `source`, `unknown`) plus the exact upgrade-command template for each known case.
- **Upgrade message catalog** — canonical, localizable strings keyed by FR-023 case (`cli_update_available`, `project_migration_needed`, `project_too_new_for_cli`, `project_not_initialized`, `install_method_unknown`) used in both human and JSON outputs so the surfaces stay in sync.

---

## Assumptions

These are the explicit answers to the brief's "Suggested Specification Decisions" plus a few defaults the spec adopts. They are deliberately captured here (not as `[NEEDS CLARIFICATION]`) so the planning phase has a stable baseline. They may be revised during `/spec-kitty.plan` if the engineering review surfaces a better option.

| ID | Assumption | Why |
|---|---|---|
| A-001 | The nag cache lives in the user's standard cache directory (XDG `$XDG_CACHE_HOME/spec-kitty/upgrade-nag.json`, falling back to platform defaults via `platformdirs`-equivalent logic). It is per-user, not per-project. Schema is documented and forward-compatible. | Per-user, not per-project, matches "no global project registry" (C-002, FR-021) while still being throttled across all projects. |
| A-002 | The latest-version source is an **injectable provider** with PyPI metadata as the default implementation. A second implementation (no-op) is used in CI/non-interactive mode. Tests use a stub provider. | Satisfies NFR-005 (testable without network) and FR-005 (CI behavior) while keeping the default user experience honest. |
| A-003 | Internal architecture introduces a single **compatibility planner** module that subsumes (or wraps) `core.version_checker`, `migration.gate`, and `upgrade.detector`. CLI commands and UI rendering layers consume the planner's structured plan rather than recomputing decisions. | Satisfies C-008 / FR-024 and the brief's recommended direction. Final wiring (unify vs. layer vs. replace) is a plan-phase decision. |
| A-004 | The Safe/Unsafe Command Classification section above is the authoritative list. Mode-aware safety for `dashboard` and `doctor` is part of the contract: the planner consults the invoked command + mode, not just the top-level command name. | Closes the user's refinement to the safe-command cut. |
| A-005 | Throttle window default is **24 hours per user**, overridable via configuration (NFR-009). | Standard for CLI nag UX; long enough to be unobtrusive, short enough to be useful. |
| A-006 | `--yes` is introduced as a **new flag** that is treated as **functionally equivalent** to existing `--force` for confirmation purposes. Both flags continue to work; documentation recommends `--yes` going forward and notes `--force` remains supported. No deprecation warning in this mission. | Preserves C-006 backward compatibility while introducing the more conventional `--yes` spelling. |
| A-007 | The CI / non-interactive trigger is the union of `CI=1` (or any standard CI env var), `not sys.stdout.isatty()`, and an explicit `--no-nag` / `SPEC_KITTY_NO_NAG=1` opt-out. Any one of these suppresses the nag's network call and output. | Conservative; avoids surprising users in any automation context. |
| A-008 | When the install method is detected as `source` (developer install) the nag still prints, but the upgrade hint reads as a manual instruction (e.g. "rebuild from source"), not a package-manager command. | Keeps maintainers honest; avoids a wrong `pipx upgrade` hint to people running from a checkout. |
| A-009 | All user-facing messages live in a small message catalog so human and JSON renderings stay in lockstep (Key Entities → Upgrade message catalog). | Makes FR-023 directly testable. |

If any of A-001 through A-009 is rejected during planning, this spec must be revised (per DIRECTIVE_010 — Specification Fidelity) before implementation begins.

---

## Out Of Scope

- Global project registry or any cross-project recent-project cache.
- "Upgrade all projects on this machine" workflow.
- Forced CLI self-update during normal command startup.
- Full reinstall or repair of Spec Kitty itself.
- SaaS, tracker, hosted auth, sync, or rollout-gating changes.
- Changes to `spec-kitty-saas`, `spec-kitty-tracker`, or any other repository.
- New telemetry or remote logging from the upgrade path.

---

## Dependencies

- Existing modules to be touched / unified by the compatibility planner: `src/specify_cli/cli/commands/upgrade.py`, `src/specify_cli/upgrade/{detector,runner,metadata,registry}.py`, `src/specify_cli/migration/{schema_version,gate}.py`, `src/specify_cli/core/version_checker.py`, and `src/specify_cli/cli/helpers.py`.
- Existing migration registry semantics (idempotent, ordered) as the binding contract for FR-018.
- Documentation file `docs/how-to/install-and-upgrade.md` for SC-008.
- Existing test scaffolding under `tests/specify_cli/upgrade/` and `tests/cross_cutting/versioning/` continues to be authoritative for migration behavior (NFR-006).

---

## Verification Expectations

Per the brief and Spec Kitty's `software-dev` mission contract:

- **Unit tests** for the compatibility planner across all scenarios in *User Scenarios & Testing* and all FR-023 cases.
- **CLI integration tests** for user-facing command behavior, including:
  - The full safe-command matrix under incompatible schema (Scenario G / SC-006).
  - The blocked-unsafe-command matrix (Scenarios B, C, and the `dashboard`/`doctor` mode split).
  - CI / non-interactive determinism (Scenario H, SC-005).
  - Unknown install method (Scenario I).
  - Fresh nag cache no-op (Scenario J, NFR-001).
- **Multi-project fixture test** asserting current-project-only behavior (SC-007, FR-020, FR-021).
- **JSON contract tests** asserting `--json` output stability (SC-004, FR-022).
- All existing migration tests must continue to pass (NFR-006).
- Network access in tests is mocked or injected (NFR-005); no test reaches PyPI or GitHub.

---

## Change Mode

`change_mode: feature` — this mission introduces new behavior (compatibility planner, nag, lazy gate, new flags) and refactors a small set of existing modules behind the planner. It is **not** a bulk edit: there is no single identifier or string being renamed across many files. If implementation surfaces an unexpected wide-scope rename (for example renaming a public symbol used by many call sites), the bulk-edit classification skill should be re-engaged at that point.

---

## Decision Log

| Date | Decision | Reference |
|---|---|---|
| 2026-04-27 | Adopt brief verbatim as the requirements baseline; promote brief's "Suggested Specification Decisions" into Assumptions A-001…A-009. | Source brief §"Suggested Specification Decisions" |
| 2026-04-27 | `dashboard` and `doctor` safety is mode-aware, not command-aware. | User refinement during specify dialog |
| 2026-04-27 | Compatibility planner is the single authority for safe/unsafe decisions (C-008, FR-024). | Source brief recommendation; engineering preference |
| 2026-04-27 | `--yes` is added as a functional alias for `--force`, both retained. | A-006; closes brief decision §3 |

---

## Mission Readiness

Per `/spec-kitty.specify` checklist:

- [x] Functional, non-functional, and constraint requirements separated and uniquely identified.
- [x] Every requirement has a non-empty Status.
- [x] Non-functional requirements have measurable thresholds.
- [x] Success criteria are measurable and technology-agnostic.
- [x] User scenarios cover the primary flows and the principal edge cases.
- [x] Domain Language fixes terminology that would otherwise drift.
- [x] No `[NEEDS CLARIFICATION]` markers remain.
- [x] Scope explicitly bounded (Out Of Scope, C-001…C-009).
- [x] Dependencies and assumptions identified.

Ready for `/spec-kitty.checklist` (to formally generate `checklists/requirements.md`) and `/spec-kitty.plan`.
