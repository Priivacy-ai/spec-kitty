# Implementation Plan: Logged-Out Teamspace CLI Recovery

**Mission:** `logged-out-teamspace-cli-recovery-01KRC6CY`
**Spec:** [spec.md](./spec.md)
**Issue:** [Priivacy-ai/spec-kitty#829](https://github.com/Priivacy-ai/spec-kitty/issues/829)

## Summary

Ship a small, well-factored recovery module under
`src/specify_cli/cli/commands/_auth_recovery.py` (or
`specify_cli/auth/recovery.py`, see Decision D1) that:

- Detects a previously-connected teamspace from `sync.routing` and the auth
  storage layer.
- Decides interactivity from stdin TTY + `SPEC_KITTY_NON_INTERACTIVE` /
  `SPEC_KITTY_FORCE_INTERACTIVE`.
- Offers an interactive `[L]/[S]/[Q]` Rich panel that drives
  `_auth_login.login_impl` when chosen.
- Emits a deterministic structured stderr line and exits 4 for non-interactive
  callers.

Wire that module into the auth-missing branches of `sync now`,
`sync status --check`, `sync doctor`, `sync routes`, and `sync share`. Behavior
for the unauthenticated-not-connected path remains byte-identical.

## Technical Context

**Language/Version**: Python 3.11+ (existing spec-kitty codebase)
**Primary Dependencies**: typer, rich, existing `specify_cli.auth.*` and `specify_cli.sync.routing` -- no new third-party deps
**Storage**: None. Detection is read-only over existing files.
**Testing**: pytest, typer.testing.CliRunner, unittest.mock; ~90% coverage on new module
**Target Platform**: Cross-platform CLI (Linux, macOS, Windows 10+)
**Project Type**: Single project (Spec Kitty CLI)
**Performance Goals**: detector returns in <50ms with no network I/O
**Constraints**: No new third-party deps. No changes to OAuth flow internals. No persisted state file.
**Scale/Scope**: ~250 LOC new code, ~400 LOC new tests, 1 operator doc page.

## Decisions

- **D1.** Place new module at
  `src/specify_cli/cli/commands/_auth_recovery.py` next to existing
  `_auth_login.py`, `_auth_status.py`, `_teamspace_mission_state_gate.py`.
  Rationale: keeps CLI-only concerns (Rich panels, exit codes, stdin)
  out of the lower-level `auth/` package. The `auth/` package remains
  free of `rich`-level UX.

- **D2.** New module exports:
  - `EXIT_LOGGED_OUT_ON_CONNECTED_TEAMSPACE: int = 4`
  - `class RecoveryOutcome(StrEnum)`: `LOGGED_IN`, `SKIPPED`, `QUIT`,
    `NO_TEAMSPACE`, `EXIT_4`.
  - `detect_logged_out_with_connected_teamspace(repo_root: Path | None = None)
    -> str | None` -- returns the teamspace handle to display.
  - `is_interactive() -> bool` (reads env + `sys.stdin.isatty`).
  - `offer_login_recovery(*, teamspace: str, command_name: str,
    console: Console) -> RecoveryOutcome`.
  - `handle_unauthenticated_with_teamspace(*, command_name: str,
    console: Console) -> RecoveryOutcome` -- the convenience facade.

- **D3.** Teamspace handle resolution order in
  `detect_logged_out_with_connected_teamspace`:
  1. `resolve_checkout_sync_routing()` -> `repo_slug` (best human handle).
  2. Falls back to `project_slug`.
  3. Falls back to the most recently stored `StoredSession.teams` private
     team name in the auth secure-storage, if present and non-empty.
  4. Returns `None` if none of the above yield a string.
  The detector returns `None` when there *is* a valid current session
  (caller has no recovery work to do).

- **D4.** Structured non-interactive stderr line, single line, ASCII only,
  stable for scripts:
  ```
  spec-kitty: logged_out_on_connected_teamspace teamspace=<slug> command=<name> action=run-spec-kitty-auth-login
  ```
  Exit code is `4` everywhere.

- **D5.** Interactive prompt uses `readchar.readkey()` *when* available
  (the project already vendors it for other interactive flows). Fallback to
  `input().strip().lower()[:1]` if `readchar` import fails. Unrecognised input
  is treated as `S` (skip), never blocks the CLI.

- **D6.** When the user picks `L`, we call
  `asyncio.run(login_impl(headless=False, force=False))`. After successful
  login, we return `LOGGED_IN` and let the caller decide whether to retry the
  original command or print a message asking the user to re-run it. Per
  scope-control, we **do not** auto-retry the command in this mission --
  retrying introduces partial-success edge cases that deserve their own spec.
  We print "Logged in. Re-run `spec-kitty <command>` to continue." and exit 0.

- **D7.** All affected `sync.py` branches that currently print the bare
  `Run spec-kitty auth login` message and exit 1 are updated. If the helper
  returns `NO_TEAMSPACE`, we keep the legacy message + exit 1 verbatim, so
  the negative path is byte-identical.

## Architectural Map

| Concern | Source location | Change |
|---|---|---|
| Detection | `src/specify_cli/sync/routing.py:resolve_checkout_sync_routing` | Reused read-only |
| Session read | `src/specify_cli/auth/manager.py` / `token_manager.py` | Reused read-only |
| Interactive prompt | new `_auth_recovery.py` | Added |
| `sync now` auth path | `cli/commands/sync.py:1004-1073` (`now()`) | Calls helper |
| `sync status --check` auth path | `cli/commands/sync.py:833-950` (`_check_server_connection`) | Caller updated |
| `sync doctor` auth path | `cli/commands/sync.py:1284-1492` | Calls helper for "No credentials" branch |
| `sync routes` / `sync share` auth path | `cli/commands/sync.py:218-389` | Calls helper via `_require_authenticated_session` adapter |
| Exit codes | new `cli/exit_codes.py` (or constant in `_auth_recovery.py`) | New constant `EXIT_LOGGED_OUT_ON_CONNECTED_TEAMSPACE = 4` |
| Tests | `tests/cli/commands/test_auth_recovery.py` (new); `tests/sync/test_sync_logged_out_recovery.py` (new) | New |
| Docs | `docs/recovery/logged-out-teamspace.md` (new) | New |

## Work Package Plan

WP01 -- Recovery module + unit tests (independent, atomic).
WP02 -- Wire into `sync now`, `sync status --check`, `sync doctor`,
        `sync routes`, `sync share` + integration tests + operator doc.

Lane: single lane (`lane-a`) since WP02 depends on WP01 surfaces.

## Risks & Mitigations

- **Risk:** Detector reads auth secure storage on import.
  **Mitigation:** Lazy imports inside the function; never at module top level.
- **Risk:** `readchar` not available on some Windows shells.
  **Mitigation:** D5 fallback to `input()`.
- **Risk:** Test flakes from real stdin detection.
  **Mitigation:** All tests monkeypatch `sys.stdin.isatty` and the env var.

## Acceptance Gate

- All new unit tests pass.
- All updated sync command integration tests pass.
- Existing `tests/sync/test_sync_doctor.py`, `test_sync_status_command.py`,
  `test_sync_status_check.py` still pass without modification (negative path
  byte-identical).
- `ruff check src/specify_cli/cli/commands/_auth_recovery.py` clean.
- Manual run of `spec-kitty sync now` on this repo with
  `SPEC_KITTY_NON_INTERACTIVE=1` and no credentials prints the structured line
  and exits 4.

## Out of Scope

- Persisting `last_known_teamspace` to disk.
- Auto-retrying the failed command after login.
- Adding the helper to non-sync commands (auth doctor has its own surface).
- Changing OAuth flow internals.
