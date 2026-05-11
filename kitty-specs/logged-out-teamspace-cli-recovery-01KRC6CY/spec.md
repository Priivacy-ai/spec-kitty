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

- **FR-1:** A pure detector returns the connected teamspace handle (or `None`)
  from local repo state without making network calls. It uses, in order:
  (a) `CheckoutSyncRouting.repo_slug` / `project_slug` when sync routing is
  defined and indicates a previously-emitted repo, (b) the most recent stored
  session's private-teamspace name if a `~/.spec-kitty` credentials file ever
  existed, (c) `None`. The detector is read-only.

- **FR-2:** A pure interactivity probe returns False when (a)
  `SPEC_KITTY_NON_INTERACTIVE=1` is set, or (b) `sys.stdin.isatty()` returns
  False, or (c) `SPEC_KITTY_FORCE_INTERACTIVE=1` overrides (a)+(b) to True.

- **FR-3:** `offer_login_recovery(...)` prints a Rich panel naming the
  connected teamspace, reads one keystroke (`L`/`S`/`Q`, case-insensitive),
  and returns a result enum (`LOGGED_IN`, `SKIPPED`, `QUIT`). On `L` it
  invokes `_auth_login.login_impl(headless=False, force=False)` via
  `asyncio.run`. After successful login, returns `LOGGED_IN`. On any
  AuthenticationError during the inner login, returns `SKIPPED` and surfaces
  the underlying error to the caller's stderr.

- **FR-4:** A new shared helper `handle_unauthenticated_with_teamspace(
  *, command_name, console)` is called from each affected sync command's
  auth-missing branch. It:
  - Calls FR-1; if `None`, returns sentinel `NO_TEAMSPACE` (caller falls back
    to existing behavior).
  - If interactive (FR-2), calls FR-3.
  - If non-interactive, emits a one-line stable structured error to stderr:
    `spec-kitty: logged_out_on_connected_teamspace teamspace=<slug>
    command=<name> action=run-spec-kitty-auth-login` and returns `EXIT_4`.

- **FR-5:** New exit code constant `EXIT_LOGGED_OUT_ON_CONNECTED_TEAMSPACE = 4`
  exported from `specify_cli.auth` (or a new `specify_cli.cli.exit_codes`
  module). Tests assert exit code is exactly 4.

- **FR-6:** Backward compatibility -- when no teamspace is detected, all
  existing strings ("Run `spec-kitty auth login`", exit code 1) remain
  unchanged. No regressions to the unauthenticated-not-connected path.

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
