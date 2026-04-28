# Phase 0 Research — CLI Session Survival and Daemon Singleton

## 0. Method

The spec carried zero `[NEEDS CLARIFICATION]` markers. Phase 0 therefore
focuses on **design decisions** that the spec deliberately leaves to plan-
phase technical judgment: the lock primitive, the convergence rule, the
identity check, the sweep algorithm, the diagnostic shape, and the test
strategy. Each decision below records what was chosen, why, and what was
rejected.

The existing repository surfaces (`auth/token_manager.py`,
`auth/secure_storage/`, `sync/daemon.py`, `cli/commands/_auth_status.py`)
were read in full before drafting these decisions; the plan reuses
existing primitives wherever they exist.

## 1. Decisions

### D1 — Machine-wide lock primitive

- **Decision**: Use OS file-locking via `fcntl.flock(LOCK_EX | LOCK_NB)`
  on POSIX and `msvcrt.locking(LK_NBLCK)` on Windows. Lift the existing
  `_is_daemon_lock_contention` predicate from `sync/daemon.py` into a new
  `specify_cli/core/file_lock.py` module so both the daemon lock and the
  new refresh lock share one implementation.
- **Rationale**:
  - This is the exact primitive Spec Kitty already uses for the daemon-
    spawn lock. There is no behavioral or operational gap that justifies a
    second lock technology.
  - It is in the standard library on every supported platform — no new
    third-party dependency is introduced (charter dependency policy).
  - Advisory-but-respected by every well-behaved process; cooperative
    nature is acceptable because the only writers are Spec Kitty CLI
    processes by construction.
- **Alternatives rejected**:
  - **`filelock` PyPI package** — adds a third-party dependency for what
    we already do natively, and its cross-platform shim is functionally
    the same as our own.
  - **`portalocker` PyPI package** — same rejection reason.
  - **Pure PID-file with `os.O_EXCL` create** — does not handle the
    "process holding the lock died" case as cleanly as `flock`'s
    automatic release on FD close.
  - **A Redis or other out-of-process broker** — way out of scope for a
    single-user CLI tool.

### D2 — Lock file location

- **Decision**: `~/.spec-kitty/auth/refresh.lock`. Sibling to
  `~/.spec-kitty/auth/session.json`. On Windows the `RuntimeRoot` helper
  resolves an equivalent location under `%LOCALAPPDATA%\spec-kitty\auth\`.
- **Rationale**:
  - Co-locating the lock with the artifact it protects is conventional
    and makes `auth doctor` introspection trivial.
  - Per-user by virtue of the home-directory base — no configuration
    needed.
  - Does not collide with the existing daemon lock at
    `~/.spec-kitty/sync-daemon.lock`.
- **Alternatives rejected**:
  - System-wide `/var/lock/spec-kitty/...` — needs privileges, and the
    "user" granularity in `spec.md` is OS-user, not machine.
  - `~/.spec-kitty/refresh.lock` (one level up) — works, but groups auth
    artifacts less cleanly.

### D3 — Lock file content schema

- **Decision**: JSON: `{"pid": int, "started_at": "<iso8601 utc>",
  "host": "<gethostname>", "version": "<package version>"}`. Written
  atomically via the existing `specify_cli.core.atomic.atomic_write`
  helper.
- **Rationale**:
  - `auth doctor` needs holder PID and acquisition timestamp to
    distinguish a healthy hold from a stuck one (FR-011, FR-014).
  - `host` future-proofs against shared filesystems (NFS, SMB) where
    different machines might map the same auth root, and lets
    `auth doctor` flag those.
  - `version` lets future tranches detect cross-version coordination
    issues without extra plumbing.
- **Alternatives rejected**:
  - PID alone — insufficient for stuck-lock detection.
  - Binary protocol — gratuitous; humans read this file in incident
    triage.

### D4 — Reload-before-refresh identity comparison

- **Decision**: Two sessions are "the same material" iff their
  `(session_id, refresh_token)` tuple is byte-equal.
- **Rationale**:
  - The refresh token is the credential the server is rejecting, so
    using it directly (plus session id as a sanity belt) is the most
    direct identity check.
  - No hashing is needed for this purpose; the comparison runs only in
    the same process that already holds the plaintext.
  - Cheap, deterministic, no clock dependency.
- **Alternatives rejected**:
  - Comparing `last_used_at` — drifts under clock skew.
  - Comparing `issued_at` — equal across rotations since the SaaS
    sometimes carries it forward; not a reliable identity.
  - Hashing the tuple — solves no problem; introduces a new failure
    mode (hash collisions are negligible but the comparison is no
    longer trivial to reason about).

### D5 — Refresh transaction outcomes (state machine)

- **Decision**: One typed enum, one outcome per terminal state of the
  transaction:
  - `AdoptedNewer` — persisted material was newer-valid, no network
    refresh.
  - `Refreshed` — network refresh succeeded; persisted material rotated.
  - `StaleRejectionPreserved` — server rejected with `invalid_grant` or
    `session_invalid`, but the rejected material was already not the
    current persisted material; local session preserved.
  - `CurrentRejectionCleared` — server rejected current persisted
    material; local session cleared, `RefreshTokenExpiredError` /
    `SessionInvalidError` propagated.
  - `LockTimeoutAdopted` — could not acquire lock within the bounded
    time, but the now-persisted material is valid; adopt and proceed.
  - `LockTimeoutError` — could not acquire lock and the persisted
    material is still expired; raise a retryable error.
- **Rationale**: Six terminal states is small enough to enumerate in
  tests and large enough to cover every observed branch in spec.md
  scenarios 1–3 plus FR-016/FR-017 cases. Each outcome has a unique
  observable side-effect for testing (storage write, exception type,
  log line), which keeps the unit-test surface clean.
- **Alternatives rejected**:
  - Boolean `True/False` "did refresh fire" — loses the FR-006 (stale
    preserved) vs FR-005 (current cleared) distinction.
  - Full RefreshState machine with intermediate states — over-modelled
    for a one-shot bounded transaction.

### D6 — Daemon convergence + self-retirement

- **Decision**: Each daemon, every `DAEMON_TICK_SECONDS=30`, reads
  `DAEMON_STATE_FILE`. If the recorded `port` ≠ `self.port`, the daemon
  initiates `server.shutdown()` and exits cleanly. State-file ownership
  flows: only `_ensure_sync_daemon_running_locked` writes the state
  file, and it is gated by the existing `DAEMON_LOCK_FILE`. Whichever
  daemon last successfully wrote the state file is the singleton.
- **Rationale**:
  - The existing daemon-spawn lock already prevents the typical "two
    daemons start simultaneously" race. The remaining failure was
    "daemon A wrote the state file in 2025, daemon B started today and
    wrote the state file, but daemon A is still running" — which the
    self-retirement tick fixes.
  - A 30 s tick keeps the convergence latency low (within FR-008's
    "next lifecycle tick") without hammering the disk.
- **Alternatives rejected**:
  - SIGTERM signaling between daemons — no PID-discovery primitive,
    and signals are platform-divergent.
  - Heartbeat record per daemon — more state to maintain; strict
    state-file ownership is simpler.

### D7 — Orphan identification rule

- **Decision**: A listening port in `[9400, 9450)` is a "Spec Kitty
  daemon" if `GET /api/health` returns 200 with both `protocol_version`
  and `package_version` JSON keys. Of those, the "current" daemon is
  the one whose port equals `DAEMON_STATE_FILE`'s recorded port.
  Everything else with that signature is an orphan.
- **Rationale**:
  - The signature is unique to the Spec Kitty daemon; other applications
    on the same port range will not coincidentally produce both keys.
  - We do not require the auth token to identify orphans (we don't have
    it for them by construction); we only require the protocol+package
    pair.
  - The probe is read-only and side-effect-free.
- **Alternatives rejected**:
  - PID-based identification — does not generalize across users; not
    every daemon process has a PID we can read without privileges.
  - Process-name pattern matching (`psutil.cmdline()`) — works, but
    couples to subprocess-launch shape that future packaging changes
    might break.

### D8 — Orphan termination strategy

- **Decision**: Best-effort graceful shutdown first, escalate on
  failure:
  1. `_stop_daemon_by_http(orphan.url, token=None)` (HTTP shutdown
     endpoint; will return 403 because we don't have the orphan's
     token, but the daemon also has a separate clean-shutdown path —
     ★ see footnote)
  2. If port still listening after 1 s: `psutil.Process(orphan.pid).terminate()`.
  3. If port still listening after 2 s: `psutil.Process(orphan.pid).kill()`.
  4. Whether or not termination succeeded, attempt to remove the
     orphan's state file (if discoverable).
- **Rationale**: The graceful path keeps log integrity; the escalation
  path guarantees forward progress so `auth doctor --reset` always
  converges in bounded time.
- **★ Footnote**: WP05 will add a token-less `/api/shutdown-self` path
  guarded by the rule "only honor when the request comes from
  127.0.0.1 AND the requester's daemon record proves it is the
  current state-file daemon". Implementation detail; falls inside
  WP05.
- **Alternatives rejected**:
  - SIGTERM-only — race-prone; some daemons may catch and ignore.
  - Force-kill always — loses on-shutdown log flush; surprises users.

### D9 — `auth doctor` shape (active-repair mode)

- **Decision**: Default invocation is read-only (FR-015). Two opt-in
  flags: `--reset` (sweeps orphans, FR-013) and `--unstick-lock`
  (force-releases the refresh lock when older than
  `STALE_LOCK_THRESHOLD_S=60`, FR-014). No combined `--auto-fix` flag
  (C-008). A `--json` flag emits the same data as machine-readable JSON
  for ops scripts.
- **Rationale**: Resolves decision moment
  `DM-01KQ9M41VJENF0T6H83VRK5DYQ`. The opt-in shape matches the user's
  stated preference (B): repairs are useful but must not happen by
  surprise.
- **Alternatives rejected**: pure read-only (rejected: leaves the user
  in lsof-land for orphans), or default-includes-repair (rejected:
  surprises the user, violates C-008).

### D10 — Multiprocess regression test design

- **Decision**: `tests/auth/concurrency/test_incident_regression.py`
  spawns two CLI worker processes via `subprocess.Popen` with `python
  -c`. Each worker imports `TokenManager`, points at a `tmp_path`-
  rooted auth store via `MONKEYPATCH`-equivalent env vars, and drives
  the rotate-then-stale-grant ordering. The fake refresh server is a
  short-lived `http.server.HTTPServer` thread inside the test process
  that returns either a rotated session or `{"error":"invalid_grant"}`
  based on a request-counter file. File barriers (`tmp_path /
  "rotated.flag"`) sequence the two workers deterministically — no
  `time.sleep`-based ordering.
- **Rationale**:
  - Real subprocesses are necessary because the bug is cross-process
    by definition; pytest-only fixtures cannot reproduce it.
  - File barriers eliminate the typical multiprocess-test flake source.
  - 30 s NFR ceiling fits comfortably under in-process CI.
- **Alternatives rejected**:
  - `multiprocessing.Process` spawn — shares the parent's file
    descriptors and `httpx` connection pools; not a faithful repro of
    "two CLIs from two temp checkouts".
  - Docker-compose simulation — heavyweight; CI cost would jump.

### D11 — `mypy --strict` posture for new modules

- **Decision**: All new modules ship with explicit `from __future__
  import annotations`, fully-typed public surfaces, and no
  `# type: ignore` comments. Internal dataclasses are `frozen=True`
  where possible to enable `Hashable`-based equality checks in tests.
- **Rationale**: Charter NFR. Also, a new lock primitive and a new
  command surface are exactly the surfaces that benefit most from the
  strictness floor.

## 2. Open questions

None. The spec has zero `[NEEDS CLARIFICATION]` markers and the
decision moment from `/spec-kitty.specify`
(`DM-01KQ9M41VJENF0T6H83VRK5DYQ`) is resolved.

## 3. Best-practice references applied

- **OAuth 2.0 Security BCP (RFC 9700)** — refresh tokens MUST rotate;
  refresh-token reuse-detection lives at the server (Tranche 2). On the
  client, our job is to not delete a session due to legitimate races.
- **OAuth 2.0 for Native Apps (RFC 8252)** — token storage stays on
  disk under user control; transport is HTTPS via existing flows;
  loopback callback is unchanged.
- **Auth0 Refresh Token Rotation** — the rotation pattern in `auth/
  flows/refresh.py` already follows the standard; the new transaction
  layer is additive.
- **OWASP Session Management Cheat Sheet** — sessions cleared at the
  client must reflect actual revocation; we add reload-before-clear so
  client-side clears match the server's last word, not a stale process's
  last word.

## 4. Tactic application notes

- **`adr-drafting-workflow`**: this section is the ADR for D1…D11.
  Each carries decision, rationale, and rejected alternatives.
- **`requirements-validation-workflow`**: each FR/NFR/C maps in
  `plan.md` §"Requirement-to-WP map" to a verifying test or a
  preserved-by-omission marker. None are aspirational.
- **`premortem-risk-identification`**: see `plan.md` §"Risks" — 7
  failure modes and countermeasures.

## 5. Phase 0 exit checklist

- [x] Every spec `[NEEDS CLARIFICATION]` marker resolved (zero present).
- [x] Each technology choice has rationale and rejected alternatives
      recorded.
- [x] No new third-party dependencies introduced.
- [x] Cross-platform considerations (POSIX vs Windows) addressed for
      every new primitive.
- [x] Test strategy named for each FR group (unit, multiprocess
      regression, daemon lifecycle, doctor offline guarantees).

Phase 0 complete. Phase 1 artifacts (`data-model.md`, `contracts/`,
`quickstart.md`) follow.

## 6. FR → testable predicate map

| FR | Predicate the test asserts |
|---|---|
| FR-001 | `MachineFileLock` acquires before `refresh_flow.refresh` is called. |
| FR-002 | `RefreshOutcome` recorded for every transaction; sequence of side-effects matches the contract. |
| FR-003 | Two same-process callers issuing `refresh_if_needed` concurrently produce one network call (existing `asyncio.Lock` behavior preserved). |
| FR-004 | Persisted-newer-and-valid case skips network call entirely. |
| FR-005 | Rejection of current material ⇒ `clear_session()` fires. |
| FR-006 | Rejection of stale material ⇒ `clear_session()` does NOT fire. |
| FR-007 | On clear, single user-readable Rich line printed with recovery command. |
| FR-008 | Two daemons, only one running after second's first tick. |
| FR-009 | `enumerate_orphans()` finds orphan; `sweep_orphans()` terminates only orphans. |
| FR-010 | Daemon whose port disagrees with state file shuts down within 2 ticks. |
| FR-011 | `auth doctor` default invocation prints all named sections. |
| FR-012 | Whenever `findings` is non-empty, `remediation` block names commands+flags. |
| FR-013 | `auth doctor --reset` invokes `sweep_orphans()` and not `force_release()`. |
| FR-014 | `auth doctor --unstick-lock` invokes `force_release()` only when lock age > threshold. |
| FR-015 | `auth doctor` (no flags) makes zero `Path.unlink`, `psutil.Process.terminate`, or HTTP `POST /api/shutdown` calls. |
| FR-016 | Network refresh exceeding `max_hold_s` returns `LockTimeoutError`; lock released. |
| FR-017 | Lock-acquisition timeout where persisted is valid ⇒ `LockTimeoutAdopted`. |
| FR-018 | Lock file owner killed ⇒ another process can adopt after `stale_after_s`. |
| FR-019 | Each terminal `RefreshOutcome` produces one log line at INFO. |
| FR-020 | Existing single-process `auth status` output unchanged byte-for-byte (golden test). |

## 7. Failure-mode catalog (premortem)

See `plan.md` §"Risks" — R1…R7. Each risk has a named counter-design
and at least one test gating regression.
