# SPEC_KITTY_HOME State Isolation

**Mission slug**: `spec-kitty-home-isolation-01KW1JXX`
**Mission type**: software-dev (bug fix)
**Source**: [GitHub issue #2171](https://github.com/Priivacy-ai/spec-kitty/issues/2171) — *Bug: SPEC_KITTY_HOME does not isolate POSIX sync/auth/tracker/daemon state*
**Status**: Draft (awaiting `/spec-kitty.plan`)

---

## Overview

`SPEC_KITTY_HOME` is documented and runbooked as the isolation boundary that lets an
operator point a local Spec Kitty CLI at a separate hosted-sync environment (e.g. an
Upsun-hosted private Teamspace) without colliding with their everyday development
session. Today that contract is only half true: the environment variable governs
**runtime / Mission assets**, but the **global sync state** — sync config, hosted-auth
sessions and refresh lock, event queues and active queue scope, the Lamport clock, the
sync daemon, and tracker credentials/cache — still resolves to the shared default home
(`~/.spec-kitty` on POSIX).

The consequence is a silent, dangerous false sense of isolation. An operator can export
`SPEC_KITTY_HOME="$HOME/.spec-kitty-upsun"`, run the documented isolation runbook, and
still read and write the same dev credentials, server URL, queue databases, and daemon
state as their normal session. They believe they are targeting a production/private
environment while the CLI is quietly using the old dev session.

This mission makes `SPEC_KITTY_HOME` the **single authoritative root** for all global
sync/auth/tracker/daemon state so the documented isolation contract actually holds —
while preserving today's behavior exactly when the variable is unset.

---

## User Scenarios & Testing

### Primary scenario (happy path)

1. An operator wants to run their local CLI against a separate hosted-sync environment.
2. They export `SPEC_KITTY_HOME` to a dedicated, isolated directory.
3. They run the isolation workflow — set the sync server URL, log in, check status,
   drain the queue.
4. **Every** piece of global state produced (sync config, auth session + refresh lock,
   queue DBs + active queue scope, Lamport clock, daemon state/log/lock, tracker
   credentials/cache) is written under the directory named by `SPEC_KITTY_HOME`.
5. Their default home (`~/.spec-kitty`) is untouched and contributes nothing to the
   isolated session.

### Exception / fallback scenario

- The operator does **not** set `SPEC_KITTY_HOME`. All state resolves to today's
  locations (`~/.spec-kitty` on POSIX; the platform-appropriate directory on Windows)
  with behavior byte-identical to the current release — no surprises, no migration.

### Edge cases

- `SPEC_KITTY_HOME` is set to an **empty string** → treated as unset; resolution falls
  through to the platform defaults.
- The operator runs `spec-kitty state doctor` under each configuration → the reported
  global-sync root always matches the root the CLI actually reads and writes.
- A directory named by `SPEC_KITTY_HOME` does not yet exist → path *resolution* must not
  fail or pre-create directories; directories are created lazily by the writing
  operation exactly as they are for the default home today.

### How this is verified

- A CLI-level integration test sets distinct `HOME` and `SPEC_KITTY_HOME`, runs the sync
  server command through the real entrypoint, and asserts the config lands under
  `SPEC_KITTY_HOME` and that `$HOME/.spec-kitty/config.toml` is absent.
- Focused unit tests assert the default path for each state surface (sync config, queue
  DBs authenticated + unauthenticated, auth store, refresh lock, Lamport clock, daemon
  state/log/lock, tracker credentials/store, state-doctor root) under both the env-set
  and env-unset conditions.
- Platform tests confirm `SPEC_KITTY_HOME` precedence over the Windows default and the
  unset fall-through on linux/darwin/win32.

---

## Requirements

### Functional Requirements

| ID | Requirement | Status |
|----|-------------|--------|
| FR-001 | When `SPEC_KITTY_HOME` is set, setting the sync server URL writes the sync configuration **only** under the selected root; no config file is created under the default home. | Proposed |
| FR-002 | When `SPEC_KITTY_HOME` is set, hosted-auth session storage defaults under the selected root. | Proposed |
| FR-003 | When `SPEC_KITTY_HOME` is set, the auth token refresh lock defaults under the selected root. | Proposed |
| FR-004 | When `SPEC_KITTY_HOME` is set, the unauthenticated event-queue database defaults under the selected root. | Proposed |
| FR-005 | When `SPEC_KITTY_HOME` is set, the authenticated (scoped) event-queue database **and** the active queue scope record default under the selected root. | Proposed |
| FR-006 | When `SPEC_KITTY_HOME` is set, sync-daemon state, log, and lock files default under the selected root. | Proposed |
| FR-007 | When `SPEC_KITTY_HOME` is set, the Lamport clock file defaults under the selected root. | Proposed |
| FR-008 | When `SPEC_KITTY_HOME` is set, tracker credentials and tracker cache/store default under the selected root (single-root decision — see C-003). | Proposed |
| FR-009 | `spec-kitty state doctor` reports a global-sync root identical to the root the runtime code actually reads and writes, under every supported env configuration. | Proposed |
| FR-010 | Every global sync/auth/tracker/daemon location is derived from one authoritative state root; no code path independently recomputes the default home for global sync state. | Proposed |
| FR-011 | Authoritative state-root resolution honors `SPEC_KITTY_HOME` on Linux, macOS, and Windows; when the variable is unset, each platform's current default is preserved (POSIX `~/.spec-kitty`; Windows platform-appropriate directory). | Proposed |
| FR-012 | An empty `SPEC_KITTY_HOME` value is treated as unset and falls through to the platform default. | Proposed |
| FR-013 | The in-repo skill document `spk-team-upsun-cli-sync/SKILL.md` is updated to describe the true isolation behavior and includes a verification command operators can run to confirm where state landed. | Proposed |

### Non-Functional Requirements

| ID | Requirement | Threshold / Measure | Status |
|----|-------------|---------------------|--------|
| NFR-001 | Backward compatibility when `SPEC_KITTY_HOME` is unset. | POSIX state paths are byte-identical to the current `~/.spec-kitty` layout; 0 regressions in the existing suite plus dedicated no-env assertions. | Proposed |
| NFR-002 | Path resolution remains a pure operation. | Resolving any state path creates 0 directories as a side effect. | Proposed |
| NFR-003 | Windows behavior is consistent and overridable. | With the variable unset, Windows resolves to the platformdirs app-data base; surfaces that previously leaked to `~/.spec-kitty` are intentionally normalized onto that base (decision `DM-01KW1KDHVGWZ0QERDMV1CRJ15S`; no auto-migration of existing data); with the variable set, it takes precedence — all proven by win32-path tests. | Proposed |
| NFR-004 | Code quality bar. | New/changed code passes `ruff` and `mypy --strict` with 0 issues and 0 warnings; new code carries ≥90% test coverage. | Proposed |
| NFR-005 | Credential safety. | 0 credentials or secrets are written or logged outside the resolved root. | Proposed |

### Constraints

| ID | Constraint | Status |
|----|------------|--------|
| C-001 | Do **not** auto-migrate existing real `~/.spec-kitty` data as part of this fix. Setting the variable selects a (possibly fresh) separate root; existing default-home data is left in place. | Proposed |
| C-002 | Scope is the spec-kitty CLI repository only — code, tests, and the in-repo skill document. Sibling `spec-kitty-saas` runbooks/test plans are explicitly a separate follow-up tracked in that repository. | Proposed |
| C-003 | `SPEC_KITTY_HOME` is the single state-root selector for global sync state. No new separate state-root environment variable is introduced. | Proposed |

---

## Key Entities

- **Runtime state root** — the single authoritative base directory for global
  sync/auth/tracker/daemon state. All child locations (sync config, auth store, refresh
  lock, queues, active queue scope, Lamport clock, daemon state/log/lock, tracker
  credentials/store) are derived from it.
- **`SPEC_KITTY_HOME`** — the environment variable that selects the runtime state root.
  When set (and non-empty), it wins on all platforms. When unset/empty, the platform
  default applies.
- **Default home** — the platform default location used when the variable is unset
  (`~/.spec-kitty` on POSIX; the platform-appropriate directory on Windows).

---

## Success Criteria

- **SC-001**: With distinct `HOME` and `SPEC_KITTY_HOME`, 100% of global state files
  (sync config, auth session + refresh lock, queue DBs + active queue scope, Lamport
  clock, daemon state/log/lock, tracker credentials/cache) land under `SPEC_KITTY_HOME`;
  the default home contains 0 of them.
- **SC-002**: An operator following the isolation runbook with only `SPEC_KITTY_HOME` set
  has 0 cross-contamination from default-home credentials, server URL, queue, or daemon
  state.
- **SC-003**: With `SPEC_KITTY_HOME` unset, existing behavior is unchanged — the full
  test suite plus dedicated no-env assertions pass with 0 regressions.
- **SC-004**: `spec-kitty state doctor`'s reported global-sync root matches the
  runtime-resolved root in 100% of tested env configurations.

---

## Assumptions

- The recommended direction from the issue (a single authoritative runtime state root
  governed by `SPEC_KITTY_HOME`, rather than introducing a new dedicated state-root
  variable) is the intended design. *(Confirmed with the operator.)*
- Tracker credentials/cache route under the same authoritative root as the rest of global
  state, not a separate tracker root. *(Confirmed — see C-003 / FR-008.)*
- Scope is limited to the spec-kitty CLI repository; sibling `spec-kitty-saas` doc/runbook
  updates are a separate follow-up. *(Confirmed — see C-002.)*
- No automatic data migration is performed; operators who want their existing data under
  the isolated root will move it themselves. *(Confirmed — see C-001.)*
- "Global sync state" here means the cross-mission state under the runtime state root; it
  does **not** change per-repository or per-mission artifact locations.
- On Windows, several surfaces currently leak to `~/.spec-kitty` while others use the
  platformdirs app-data base. The fix normalizes all surfaces onto the single platformdirs
  base (decision `DM-01KW1KDHVGWZ0QERDMV1CRJ15S`); a few unset-Windows paths therefore move
  onto that base. This is intended (see NFR-003) and carries no automatic data migration
  (C-001).

---

## Domain Language

To avoid the conceptual drift that caused this bug, the spec distinguishes two homes that
had collapsed into one operator-facing contract:

- **Runtime / Mission asset home** — already honors `SPEC_KITTY_HOME` today.
- **Runtime state root (global sync state home)** — the subject of this mission; must
  also honor `SPEC_KITTY_HOME`.

Canonical operator-facing statement after this fix: *"`SPEC_KITTY_HOME` selects the root
for all local Spec Kitty state."* Avoid implying isolation in docs unless tests prove it.

---

## Affected Surfaces (reference from issue evidence — not requirements)

These call sites are enumerated in the issue's evidence section and serve as the starting
inventory for `/spec-kitty.plan`. They are recorded here for traceability
(DIRECTIVE_003); the plan phase owns confirming the exhaustive, current list and the
resolution mechanism.

- `src/specify_cli/runtime/home.py` / `src/kernel/paths.py` — already honor the variable
  (the asset home; reference behavior to match).
- `src/specify_cli/sync/config.py` — `SyncConfig.config_dir`.
- `src/specify_cli/sync/queue.py` — `_spec_kitty_dir()` feeding credentials, auth session
  dir, legacy + scoped queue dirs, active queue scope.
- `src/specify_cli/sync/daemon.py` — POSIX `_sync_root()`, `_daemon_root()`, module
  constant `SPEC_KITTY_DIR`.
- `src/specify_cli/sync/clock.py` — default Lamport clock path.
- `src/specify_cli/auth/secure_storage/file_fallback.py` — default auth store dir.
- `src/specify_cli/auth/token_manager.py` — POSIX refresh lock.
- `src/specify_cli/tracker/credentials.py` and `src/specify_cli/tracker/store.py` —
  tracker roots.
- `src/specify_cli/state/doctor.py` — `global_sync` root.
- `src/specify_cli/state/contract.py` — `StateRoot.GLOBAL_SYNC` model and its reported
  files.

---

## Out of Scope

- Updating sibling `spec-kitty-saas` runbooks, scripts, and test plans (separate
  follow-up in that repo — C-002).
- Automatic migration of existing `~/.spec-kitty` data (C-001).
- Introducing any new state-root environment variable (C-003).
- Changing per-repository or per-mission artifact locations.

---

## Dependencies

- Git and a POSIX or Windows environment (existing platform support matrix).
- No new third-party dependencies anticipated.
