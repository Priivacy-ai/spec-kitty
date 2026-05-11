# Spec: Logged-Out Teamspace CLI Recovery

**Mission:** logged-out-teamspace-cli-recovery-01KRC6CY
**Issue:** [Priivacy-ai/spec-kitty#829](https://github.com/Priivacy-ai/spec-kitty/issues/829)
**Priority:** P1

## Problem

When a repo is connected to a Teamspace but the local CLI session is logged out
(no credentials, or refresh token expired), `spec-kitty sync ...` and related
commands print bare guidance such as `Run spec-kitty auth login`. There is:

1. No detection that the repo was previously connected to a Teamspace, so the
   user doesn't know *which* identity to log into.
2. No interactive recovery path -- the user has to read the message, copy the
   command, and try again.
3. No machine-readable, deterministic non-interactive output, so CI scripts
   cannot reliably detect the "logged-out-on-connected-teamspace" case versus
   a generic auth error.

## Goal

Improve CLI recovery when a repo is connected to a Teamspace but the local
session is logged out, by:

- Detecting prior Teamspace connection from local repo identity / sync routing.
- Offering interactive `[L]ogin / [S]kip / [Q]uit` when the call site is a TTY
  and `SPEC_KITTY_NON_INTERACTIVE` is not set.
- Emitting a stable structured error (exit code 4) with the connected
  teamspace slug, so non-interactive callers (CI) can detect the case.
- Keeping all existing flows for unauthenticated-but-not-connected and for
  authenticated users unchanged.

## Scope

In scope:

- New helper `detect_logged_out_with_connected_teamspace(repo_root)`.
- New helper `is_interactive()` (TTY + `SPEC_KITTY_NON_INTERACTIVE`).
- New `offer_login_recovery(...)` interactive prompt.
- Wire those helpers into the auth-missing paths of:
  - `spec-kitty sync now`
  - `spec-kitty sync status --check`
  - `spec-kitty sync doctor`
  - `spec-kitty sync routes`
  - `spec-kitty sync share`
- A new stable exit code (`4`) for "logged out on connected teamspace".

Out of scope:

- Adding the recovery prompt to non-sync commands (auth doctor already has its
  own path; runtime / status / charter do not surface this error today).
- Changing the underlying browser/device OAuth flow.
- Persisting the teamspace identity in a new file -- we infer from existing
  routing / repo identity state.

## User Stories

1. **Interactive operator.** Robert runs `spec-kitty sync now` on a repo that
   was last connected to teamspace `acme-eng`. His local session has expired.
   The CLI prints a panel naming `acme-eng` and offers `[L]ogin / [S]kip /
   [Q]uit`. He hits `L`, the browser flow opens, he authenticates, and the
   command resumes (or exits cleanly with guidance to re-run).

2. **CI script.** GitHub Actions runs `spec-kitty sync now` on a fork's CI
   where credentials never existed. `SPEC_KITTY_NON_INTERACTIVE=1` is set.
   The CLI prints a JSON-tagged line "logged_out_on_connected_teamspace
   teamspace=acme-eng action=run-spec-kitty-auth-login" and exits with code 4.
   The script checks for exit 4 specifically and skips or surfaces the case.

3. **Logged-out, not-connected user.** A first-time user runs
   `spec-kitty sync now` in a repo that has never been connected to a
   teamspace. The CLI prints the existing "Run spec-kitty auth login" message
   and exits non-zero, unchanged.

## Functional Requirements

| ID | Description | Priority | Status |
|----|-------------|----------|--------|
| FR-001 | A pure detector `detect_logged_out_with_connected_teamspace(repo_root)` returns the connected teamspace handle (or None) from local repo state without making network calls. Resolution order: `CheckoutSyncRouting.repo_slug`, then `project_slug`, then the most recent stored session's private-teamspace name. Returns None when a valid current session exists or no teamspace identity can be resolved. | High | Open |
| FR-002 | A pure interactivity probe `is_interactive()` returns False when `SPEC_KITTY_NON_INTERACTIVE=1` is set, or `sys.stdin.isatty()` returns False. `SPEC_KITTY_FORCE_INTERACTIVE=1` overrides both to True. | High | Open |
| FR-003 | `offer_login_recovery(*, teamspace, command_name, console)` prints a Rich panel naming the connected teamspace, reads one keystroke (L/S/Q, case-insensitive), and returns RecoveryOutcome.LOGGED_IN / SKIPPED / QUIT. On L it invokes `_auth_login.login_impl(headless=False, force=False)` via `asyncio.run`. On AuthenticationError, returns SKIPPED with the error surfaced to stderr. | High | Open |
| FR-004 | `handle_unauthenticated_with_teamspace(*, command_name, console)` is the shared facade. It calls FR-001; if None it returns NO_TEAMSPACE so callers fall back to legacy behavior. If interactive (FR-002), it calls FR-003. Otherwise it writes the structured stderr line and returns EXIT_4. | High | Open |
| FR-005 | The non-interactive structured stderr line is a single ASCII line, stable for scripts: `spec-kitty: logged_out_on_connected_teamspace teamspace=<slug> command=<name> action=run-spec-kitty-auth-login`. Exit code is `EXIT_LOGGED_OUT_ON_CONNECTED_TEAMSPACE = 4`, exported as a module constant. | High | Open |
| FR-006 | Backward compatibility: when no teamspace is detected (NO_TEAMSPACE), the existing legacy message "Run `spec-kitty auth login`" and exit code 1 are preserved verbatim. The unauthenticated-not-connected path emits no new strings and no new exit codes. | High | Open |
| FR-007 | The auth-missing branches of `spec-kitty sync now`, `spec-kitty sync status --check`, `spec-kitty sync doctor`, `spec-kitty sync routes`, and `spec-kitty sync share` invoke `handle_unauthenticated_with_teamspace` before falling back to the legacy message. Each path is covered by an integration test in both interactive and non-interactive modes. | High | Open |

## Acceptance Criteria

1. Unit tests for `detect_logged_out_with_connected_teamspace` covering:
   missing routing, routing with no project slug, routing with a slug, valid
   session (returns None), expired session, missing credentials file.

2. Unit tests for `is_interactive()` covering TTY+no env, TTY+
   `SPEC_KITTY_NON_INTERACTIVE=1`, no TTY, no TTY +
   `SPEC_KITTY_FORCE_INTERACTIVE=1`.

3. Unit tests for `offer_login_recovery` mocking `login_impl` and stdin:
   `L` -> `LOGGED_IN`, `S` -> `SKIPPED`, `Q` -> `QUIT`, login raises ->
   `SKIPPED`.

4. CLI integration tests using `CliRunner` for `spec-kitty sync now`:
   non-interactive + connected teamspace exits 4 with the structured line;
   non-interactive + no teamspace exits with the legacy message and exit 1;
   interactive + connected teamspace + user picks `S` exits 4 cleanly; user
   picks `L` triggers `login_impl` (mocked).

5. The same integration coverage applies to `spec-kitty sync status --check`
   and `spec-kitty sync doctor` auth-missing branches.

6. Docs: a one-page operator note in `docs/recovery/logged-out-teamspace.md`
   showing the interactive panel screenshot text, the structured stderr line,
   and exit code semantics.

## Non-Goals

- Persisting a new "last-known teamspace" field. Reuse what exists.
- Changing the OAuth flow.
- Changing existing behavior of the unauthenticated-not-connected path.

## Open Questions

None at spec time. All resolved in plan.md decisions.
