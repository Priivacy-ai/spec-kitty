# Tasks: Logged-Out Teamspace CLI Recovery

**Mission:** `logged-out-teamspace-cli-recovery-01KRC6CY`
**Issue:** [Priivacy-ai/spec-kitty#829](https://github.com/Priivacy-ai/specify/issues/829)

## Work Packages

| WP | Title | Depends on | Lane |
|----|-------|-----------|------|
| WP01 | Recovery helper module: detector, interactivity probe, prompt, facade, exit code, and tests | (none) | lane-a |
| WP02 | Wire recovery helper into sync commands (now/status/doctor/routes/share), integration tests, operator doc | WP01 | lane-a |

## Tasks

### WP01 -- Recovery helper module

- T001 [WP01] Add `src/specify_cli/cli/commands/_auth_recovery.py` with:
  - `EXIT_LOGGED_OUT_ON_CONNECTED_TEAMSPACE = 4`
  - `class RecoveryOutcome(StrEnum)` (LOGGED_IN, SKIPPED, QUIT, NO_TEAMSPACE, EXIT_4)
  - `detect_logged_out_with_connected_teamspace(repo_root: Path | None = None) -> str | None`
  - `is_interactive() -> bool`
  - `_read_one_keystroke() -> str` (readchar with input() fallback)
  - `offer_login_recovery(*, teamspace, command_name, console) -> RecoveryOutcome`
  - `handle_unauthenticated_with_teamspace(*, command_name, console) -> RecoveryOutcome`
  - `emit_structured_stderr(*, teamspace, command_name)` helper
- T002 [WP01] Add `tests/cli/commands/test_auth_recovery.py` covering:
  - `detect_*`: valid session returns None; missing session + routing slug returns slug; routing returns None + stored session has private-team returns team name; nothing returns None
  - `is_interactive`: TTY+no env -> True; TTY+NON_INTERACTIVE=1 -> False; no-TTY -> False; no-TTY+FORCE_INTERACTIVE=1 -> True
  - `offer_login_recovery`: L -> LOGGED_IN (login_impl called); S -> SKIPPED; Q -> QUIT; login raises AuthenticationError -> SKIPPED
  - `handle_unauthenticated_with_teamspace`: no teamspace -> NO_TEAMSPACE (no output); non-interactive + teamspace -> EXIT_4 + stderr line; interactive + teamspace -> calls prompt
- T003 [WP01] Mark WP01 done.

### WP02 -- Wire into sync commands

- T010 [WP02] Update `src/specify_cli/cli/commands/sync.py` so each of these branches calls `handle_unauthenticated_with_teamspace` before falling back to the legacy message:
  - `now()` -- unauthenticated-result branch
  - `status()` -- when `--check` is set and session missing/expired (via the `_check_server_connection` caller)
  - `doctor()` -- "No credentials" / both-tokens-expired branch
  - `routes()` -- when `_require_authenticated_session` raises
  - `share()` -- when `_require_authenticated_session` raises
  - Preserve legacy strings + exit code 1 when helper returns NO_TEAMSPACE
- T011 [WP02] Add `tests/sync/test_sync_logged_out_recovery.py` covering, for `sync now` and `sync doctor`:
  - non-interactive + connected teamspace -> exit code 4 + stderr structured line + no rich panel
  - non-interactive + no teamspace -> exit 1, legacy "Run `spec-kitty auth login`" string unchanged
  - interactive + teamspace + user picks `S` -> exit code 4
  - interactive + teamspace + user picks `L` (mocked login_impl) -> login invoked, exit 0
- T012 [WP02] Confirm existing `tests/sync/test_sync_doctor.py` and `tests/sync/test_sync_status_command.py` still pass unchanged.
- T013 [WP02] Add `docs/recovery/logged-out-teamspace.md` operator note with the structured stderr line, exit code semantics, and how to disable the interactive prompt (`SPEC_KITTY_NON_INTERACTIVE=1`).
- T014 [WP02] Mark WP02 done.

## Acceptance

All FR-001 through FR-007 are covered by T001-T014. Mission is complete when both WPs are in `approved` lane and `tests/cli/commands/test_auth_recovery.py` + `tests/sync/test_sync_logged_out_recovery.py` pass.
