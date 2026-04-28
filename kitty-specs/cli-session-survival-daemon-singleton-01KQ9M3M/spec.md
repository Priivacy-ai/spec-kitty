---
mission_id: 01KQ9M3M91HND8QRPQNJVQAFH5
mission_slug: cli-session-survival-daemon-singleton-01KQ9M3M
mission_type: software-dev
friendly_name: CLI Session Survival and Daemon Singleton
target_branch: main
---

# Mission Specification — CLI Session Survival and Daemon Singleton

> Tranche 1 of the AUTH Resilience and Security Program
> (`start-here.md` §"Tranche 1"). This spec describes only Tranche 1; the
> server-side, transport, storage, and adversarial-validation work for the rest
> of the program lives in subsequent missions.

## Purpose

**TLDR**: Stop multi-process refresh races and orphan sync daemons from
silently logging the CLI user out.

**Context**: A real incident on a developer's machine showed
`spec-kitty auth status` flipping from authenticated to *not authenticated*
even though the SaaS-side session was still active. Investigation found
multiple long-lived sync daemons spawned from temporary repository checkouts
all sharing one `~/.spec-kitty/auth/session.json`. One daemon refreshed and
rotated the token successfully; a stale daemon then tried the rotated-out
refresh token, received `invalid_grant`, and deleted the shared local session.

Spec Kitty users routinely clone the CLI into temporary directories (workspace
preparation flows, `mktemp`-rooted experiments, parallel agent runs). That is
a supported, normal workflow. The CLI must not lose authentication because of
how the user organizes those checkouts.

## Definition of "Stay Authenticated"

The user should lose CLI authentication only when one of the following is
true (per `start-here.md` §"Program Goal"):

1. They explicitly log out.
2. An admin or the server explicitly revokes the session.
3. The refresh-token family is compromised and the server revokes it.
4. The refresh token reaches its absolute server-side lifetime.
5. Local secure storage is deleted or unrecoverably corrupted.

Tranche 1 closes the leak path that does not match any of those five reasons:
**a stale local process deleting newer persisted auth material because of its
own out-of-date in-memory token state.**

## Primary Personas

- **Mission-running developer (P-DEV)**: clones Spec Kitty into one or more
  temporary directories, runs missions, leaves the CLI authenticated for days.
  Does not want to re-authenticate without cause.
- **Multi-checkout operator (P-OPS)**: keeps several long-lived clones for
  different programs; each spawns a sync daemon. Expects them to coexist.
- **Diagnoser (P-DIAG)**: when something goes wrong, wants a single command
  that reports storage state, daemon state, session id, and what to do next —
  without resorting to `lsof`, `ps`, or hand-reading `~/.spec-kitty/`.

## User Scenarios & Acceptance Tests

### Scenario 1 — Concurrent refresh under one expired session (happy path)

**Given** two CLI processes share `~/.spec-kitty/auth/session.json` and the
access token has just expired,
**When** both attempt to refresh at the same moment,
**Then** at most one network refresh request is sent, both processes end up
with the rotated, valid access and refresh tokens, and the user remains
authenticated.

**Verification**: deterministic regression test using two `TokenManager`
instances pointed at the same auth root, with the network layer arranged to
record a single `POST /token` call.

### Scenario 2 — Stale daemon meets rotated tokens (the incident)

**Given** Daemon A has just refreshed and rotated the refresh token,
**And** Daemon B is still holding the previous, now-rotated-out refresh token
in memory,
**When** Daemon B attempts a refresh and the server returns `invalid_grant`,
**Then** Daemon B reloads persisted storage, sees that current persisted
material differs from the material it just used, and **does not delete** the
local session. The user remains authenticated.

**Verification**: subprocess-based regression test that reproduces the exact
ordering observed in the incident (rotate → stale grant attempt → assert
session intact).

### Scenario 3 — Genuinely revoked session

**Given** the persisted refresh token *is* the material the server just
rejected with `invalid_grant` or `session_invalid`,
**When** the CLI receives the rejection,
**Then** the local session is cleared, and the user sees a clear, single-line
"please re-login" message with the recovery command.

### Scenario 4 — Many temp checkouts, one user

**Given** the user spawns sync daemons from three temporary checkouts of
`spec-kitty`,
**When** the daemons start,
**Then** they converge to **one** active user-level daemon serving sync; the
extra daemons either retire themselves or are detected and reported as
orphans by `auth doctor`.

### Scenario 5 — Diagnostics

**Given** anything in the auth or daemon system has gone sideways,
**When** the user runs `spec-kitty auth doctor`,
**Then** the user sees: storage backend in use, current session id,
access-token remaining lifetime, refresh-token remaining lifetime, the
machine-wide refresh lock holder (or `unheld`), the active user-level daemon's
PID/port/version, count of orphan daemons in the reserved port range, drift
warnings (e.g., persisted session newer than in-memory), and an actionable
remediation block ("run `spec-kitty auth doctor --reset` to sweep orphans",
"run `spec-kitty auth login` to re-authenticate"). With explicit flags the
user can run targeted, opt-in repairs (`--reset` to sweep orphan daemons,
`--unstick-lock` to drop a stuck refresh lock above an age threshold). The
default invocation never mutates state.

### Scenario 6 — Single-process baseline still works

**Given** a single CLI process,
**When** it refreshes a token normally,
**Then** behavior matches the existing single-process happy path with no
extra prompts, no unnecessary network calls, and no measurable user-visible
latency increase beyond the lock acquisition cost.

## Domain Language

To keep the spec, plan, and implementation aligned, these terms are canonical
inside this mission:

| Term | Canonical meaning |
|---|---|
| **Auth store root** | The on-disk directory holding the persisted session and the machine-wide refresh lock (today: `~/.spec-kitty/auth/`). |
| **Persisted session** | The serialized session record on disk (access token, refresh token, expirations, session id, metadata). |
| **In-memory token material** | The `TokenManager` instance's currently held copy of the session, which can be older than what is on disk. |
| **Machine-wide refresh lock** | A file-system-level lock under the auth store root that serializes refresh transactions across processes on one machine. |
| **Refresh transaction** | The bounded sequence: acquire lock → reload persisted session → decide whether refresh is needed → optionally call the network → persist outcome → release lock. |
| **Stale grant rejection** | A server `invalid_grant` or `session_invalid` response received against token material that is no longer the current persisted material. |
| **User-level daemon** | The single sync daemon process per OS user that owns sync work for that user across all temp checkouts. |
| **Orphan daemon** | A sync daemon process listening on a port in the reserved daemon port range that is not the current user-level daemon. |
| **Reserved daemon port range** | The pre-existing port range Spec Kitty already uses for sync daemons. Tranche 1 inherits the existing range; it does not expand or rename it. |
| **`auth doctor`** | The new diagnostics surface. Default invocation is read-only. Repairs are opt-in via explicit flags. |

## Functional Requirements

| ID | Requirement | Status |
|---|---|---|
| FR-001 | The CLI MUST acquire a machine-wide refresh lock under the auth store root before performing any refresh transaction. | Required |
| FR-002 | The refresh transaction MUST execute as: acquire lock → reload persisted session → decide whether refresh is needed → optionally call the network → persist outcome → release lock. | Required |
| FR-003 | The CLI MUST keep its existing in-process single-flight protection for refresh, but MUST NOT rely on it for correctness across processes. | Required |
| FR-004 | While holding the refresh lock, if the reloaded persisted session contains valid, non-expired token material newer than what the caller had, the CLI MUST adopt the persisted material and skip the network refresh. | Required |
| FR-005 | On a server rejection of `invalid_grant` or `session_invalid` during refresh, the CLI MUST reload persisted storage and only clear the local session if the rejected material is still the current persisted material. | Required |
| FR-006 | On a server rejection of `invalid_grant` or `session_invalid` against material that is no longer current, the CLI MUST preserve the persisted session and exit the refresh transaction without re-attempting refresh inside the same call. | Required |
| FR-007 | When the CLI clears the local session due to a confirmed-current rejection, it MUST surface a single, user-readable message stating the cause and the recovery command (`spec-kitty auth login`). | Required |
| FR-008 | Sync daemons started from any temp checkout for the same OS user MUST converge to one active user-level daemon. Additional daemons MUST either decline to start (deferring to the active one) or self-retire on their next lifecycle tick. | Required |
| FR-009 | The CLI MUST detect daemons in the reserved daemon port range that are not the active user-level daemon and MUST be able to terminate them (sweep) on explicit user request. | Required |
| FR-010 | Orphan daemons that detect they are not the active user-level daemon MUST self-retire within their next lifecycle tick rather than continuing to operate on stale token state. | Required |
| FR-011 | The CLI MUST provide `spec-kitty auth doctor`, a default-read-only diagnostic that reports: storage backend, session id, access-token remaining lifetime, refresh-token remaining lifetime, machine-wide refresh lock holder (or `unheld`), active user-level daemon PID / port / version, orphan-daemon count, and any drift warnings. | Required |
| FR-012 | `auth doctor` MUST include an actionable remediation block whenever a problem is detected, naming the specific commands (and their flags) that resolve each problem. | Required |
| FR-013 | `auth doctor --reset` MUST sweep orphan daemons in the reserved daemon port range and MUST NOT touch the active user-level daemon. | Required |
| FR-014 | `auth doctor --unstick-lock` MUST drop a stuck machine-wide refresh lock only when its age exceeds an age threshold the implementation defines explicitly and surfaces in the doctor output. | Required |
| FR-015 | `auth doctor` without flags MUST NOT mutate any persisted state, kill any process, or touch any lock. | Required |
| FR-016 | The refresh transaction's lock-hold time MUST be bounded; if the network refresh exceeds the bounded duration the CLI MUST release the lock, treat the call as failed-without-state-loss, and report a retryable error. | Required |
| FR-017 | The CLI MUST treat a refresh-lock acquisition timeout as a benign event when persisted session material reloaded after timeout is valid (the other process succeeded), and MUST adopt that material rather than retrying or erroring. | Required |
| FR-018 | The refresh lock implementation MUST tolerate a process holding the lock being killed mid-transaction (lock file with PID; lock considered abandoned past an age threshold). | Required |
| FR-019 | The CLI MUST log refresh-transaction outcomes (no-op-adopted-newer, network-refreshed, stale-rejection-preserved, current-rejection-cleared, lock-timeout-adopted, lock-timeout-error) at a level the user can surface for diagnostics. | Required |
| FR-020 | `spec-kitty auth status` MUST continue to report authenticated/not authenticated truthfully relative to persisted state, with no behavioral regression when only one process is involved. | Required |

## Non-Functional Requirements

| ID | Requirement | Threshold | Status |
|---|---|---|---|
| NFR-001 | Refresh-transaction overhead added by the machine-wide lock in the single-process happy path. | ≤ 50 ms additional wall time at the 95th percentile on the maintainer's reference development machine. | Required |
| NFR-002 | Refresh-transaction lock-hold ceiling. | The lock MUST be released within 10 s of acquisition under all code paths, including failed network calls. | Required |
| NFR-003 | Test coverage for new and modified auth and daemon code. | ≥ 90 % line coverage for the new modules and modified branches (per project charter). | Required |
| NFR-004 | Type checking. | `mypy --strict` MUST pass with zero new errors on all changed and new code (per project charter). | Required |
| NFR-005 | Multiprocess regression test runtime. | The deterministic multiprocess regression test for the incident MUST complete in ≤ 30 s on CI to remain in the default test suite. | Required |
| NFR-006 | Diagnostic time-to-actionable. | `spec-kitty auth doctor` MUST return a result and an actionable remediation block in ≤ 3 s for a typical local state (no remote round-trips required). | Required |
| NFR-007 | Backward compatibility for existing local sessions. | Existing on-disk session files MUST continue to load without manual user action. New lock files MUST not break older CLI versions reading the same auth root (older versions ignore them). | Required |
| NFR-008 | Cross-platform support. | All new behavior MUST work on the platforms Spec Kitty currently supports (macOS and Linux at minimum); platform-specific lock primitives MUST be selected by capability detection, not by hard-coded OS check fallthrough. | Required |

## Constraints

| ID | Constraint | Rationale | Status |
|---|---|---|---|
| C-001 | Refresh tokens MUST NOT be made non-expiring. Renewability is achieved through robust rotation, not by removing the absolute lifetime. | OAuth 2.0 Security BCP (RFC 9700) and Auth0 refresh-token-rotation guidance. Non-expiring refresh tokens defeat compromise-detection. | Required |
| C-002 | The CLI MUST NOT hide or smooth over real server-side revocation or compromise. A confirmed-current `invalid_grant` or `session_invalid` MUST clear local state and prompt re-login. | OWASP Session Management Cheat Sheet; user must be told the truth about session state. | Required |
| C-003 | No hosted SaaS, sync, tracker, or WebSocket call may be made on this development machine without `SPEC_KITTY_ENABLE_SAAS_SYNC=1`. | Local rule from `start-here.md` §"Local Rules". | Required |
| C-004 | Tranche 1 MUST land independently of server-side changes. Tranche 2 work (server token-family semantics, RFC 7009-style revocation, session-status endpoint) is a separate mission and is not a prerequisite. | Program tranching strategy in `start-here.md` §"How Many Tranches"; the incident fix must ship without waiting for SaaS work. | Required |
| C-005 | The auth store root layout MUST remain backward-readable. New artifacts (lock files, daemon-singleton metadata) MUST NOT relocate or rename existing session files. | NFR-007 corollary; users on intermediate CLI versions must keep working. | Required |
| C-006 | Native-app OAuth posture must remain consistent with RFC 8252. Tokens are persisted on disk under user control with the existing storage backend; transport is unchanged in this tranche. | RFC 8252 ("OAuth 2.0 for Native Apps"). Deeper storage hardening is Tranche 4, not Tranche 1. | Required |
| C-007 | `auth doctor` default invocation MUST be safe to run anywhere, anytime — including from a temp checkout without an active mission — and MUST NOT require network access to produce a useful local report. | Diagnostics are most needed when something is already broken; `auth doctor` cannot itself depend on the broken path. | Required |
| C-008 | Active-repair flags (`--reset`, `--unstick-lock`) MUST require explicit opt-in. There MUST be no `--auto-fix` or equivalent that combines them with `auth doctor` defaults. | Decision moment DM-01KQ9M41VJENF0T6H83VRK5DYQ resolved as `report-plus-active-repair`: the user wants opt-in repairs, not surprising mutations. | Required |

## Success Criteria

These outcomes are how we judge the mission complete from the user's
perspective. Each is measurable and technology-agnostic.

- **SC-001**: A user running missions across three or more temporary
  checkouts of `spec-kitty` for 24 hours without explicit logout, server
  revocation, lifetime expiry, or local-storage loss observes zero
  unsolicited "not authenticated" states.
- **SC-002**: When the incident pattern is reproduced (rotate-then-stale-
  grant) the local session survives. Verified by the deterministic
  regression test in the default test suite.
- **SC-003**: When the user does need to re-authenticate (legitimate cause),
  the CLI tells them exactly which legitimate cause it was and what to do.
- **SC-004**: A user with a misbehaving auth state can run a single command
  (`spec-kitty auth doctor`) and receive within seconds a complete picture
  of local auth state plus the exact next command to run.
- **SC-005**: A user with orphan daemons can clear them with one explicit
  command (`spec-kitty auth doctor --reset`) without learning `lsof`, `ps`,
  or port numbers.
- **SC-006**: Running multiple CLI processes that need refresh at the same
  moment results in one network refresh request, not N.

## Key Entities

- **AuthSession**: persisted session record. Identity is `session_id`. Owns
  access token, refresh token, expirations, storage-backend tag, and the
  metadata needed to detect drift between in-memory and persisted copies.
- **MachineRefreshLock**: a process-coordination artifact under the auth
  store root. Identity is the lock-file path. Carries holder PID, holder
  start-time, and acquisition timestamp so `auth doctor` and the
  `--unstick-lock` flow can reason about it.
- **UserDaemon**: the one sync daemon process per OS user. Identity is the
  user-level daemon-registration record (PID, port, version, started_at).
  Other daemons compare themselves against this record to decide whether to
  retire.
- **OrphanDaemon**: any process listening on the reserved daemon port range
  that is not the current `UserDaemon`. Identity is `(pid, port)`.
- **DoctorReport**: the structured output of `auth doctor`. Identity is the
  invocation timestamp + auth-store-root path. Carries findings,
  remediation suggestions, and the boolean "any problems detected".

## Edge Cases

The following edge cases MUST have explicit, named behavior:

- **Lock file on a network filesystem**: behavior is documented; if
  filesystem-level locking semantics are unsafe, the CLI MUST fall back to
  a portable advisory mechanism rather than silently violate mutual
  exclusion.
- **Stale lock from a killed process**: handled by the lock-age threshold
  (FR-018) and `--unstick-lock` (FR-014).
- **Persisted session corrupted on disk**: treat as "no session"; do not
  crash; `auth status` returns not-authenticated; `auth doctor` reports
  "storage corrupted, run `spec-kitty auth login`".
- **Clock skew between processes**: any age/expiration math MUST be
  monotonic-clock-based or tolerant of small (< 60 s) skew so two processes
  do not flip-flop on "is the access token expired".
- **Race where two processes both think they are the user-level daemon**:
  one MUST yield within its next lifecycle tick; the registration record is
  the tiebreaker.
- **OS-user transition mid-session** (e.g., `sudo` shell): out of scope —
  the mission is "per OS user" and treats UID changes as separate users.

## Assumptions

These are the defaults we adopt unless explicitly contradicted. They are
recorded so reviewers can challenge them rather than discover them in code.

- The reserved daemon port range is the existing range used by
  `spec-kitty sync daemon` today. Tranche 1 inherits it as-is.
- The auth store root is `~/.spec-kitty/auth/` on macOS and Linux. Tranche
  4 may move it to OS keychains; Tranche 1 leaves the location alone.
- "User" means OS user. Tranche 1 does not address machines with multiple
  Spec Kitty SaaS accounts under one OS user.
- Server-side `invalid_grant` and `session_invalid` semantics are as the
  current SaaS deployment returns them. Tranche 2 will tighten the
  family-level semantics on the server; Tranche 1 only changes how the
  client interprets them.
- The user is allowed to have non-Spec-Kitty processes listening on
  arbitrary ports. The reserved daemon port range is narrow enough that
  matching by port + Spec-Kitty-process signature is safe.

## Dependencies and References

- **Authoritative program brief**: `start-here.md` §"Tranche 1 - CLI
  Session Survival and Daemon Singleton".
- **OAuth 2.0 Security BCP**: RFC 9700 (refresh-token rotation,
  compromise-detection guidance).
- **OAuth 2.0 for Native Apps**: RFC 8252 (token storage and transport
  posture for the CLI).
- **Refresh-token rotation guidance**: Auth0 "Refresh Token Rotation".
- **Session lifecycle posture**: OWASP Session Management Cheat Sheet.
- **Charter / project doctrine**: DIRECTIVE_003 (decision documentation) and
  DIRECTIVE_010 (specification fidelity) apply to this mission.

## Out of Scope (explicit)

The following items are *not* part of Tranche 1. They are listed so the
plan and tasks stay scoped:

- Server-side refresh-token family / generation tracking. (Tranche 2.)
- RFC 7009-style revocation endpoint. (Tranche 2.)
- WebSocket auth contract changes and bearer-token-in-URL removal.
  (Tranche 3.)
- OS-keychain backed local storage and Django-`SECRET_KEY` separation.
  (Tranche 4.)
- Privileged action gating, API-key scopes, connector OAuth, rate-limit
  hardening. (Tranche 5.)
- Cross-repo adversarial validation suite, soak runbook, release gate.
  (Tranche 6.)

## Decisions Recorded

- **DM-01KQ9M41VJENF0T6H83VRK5DYQ** — `auth doctor` shape: chosen
  `report-plus-active-repair`. Default is read-only; opt-in flags
  `--reset` and `--unstick-lock` perform explicit, narrow repairs. See
  `decisions/DM-01KQ9M41VJENF0T6H83VRK5DYQ.md`.
