---
work_package_id: WP02
title: Wire recovery helper into sync commands and add operator doc
dependencies:
- WP01
requirement_refs:
- FR-006
- FR-007
planning_base_branch: kitty/mission-logged-out-teamspace-cli-recovery-01KRC6CY-lane-a
merge_target_branch: kitty/mission-logged-out-teamspace-cli-recovery-01KRC6CY-lane-a
branch_strategy: Planning artifacts for this mission were generated on kitty/mission-logged-out-teamspace-cli-recovery-01KRC6CY-lane-a. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into kitty/mission-logged-out-teamspace-cli-recovery-01KRC6CY-lane-a unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-logged-out-teamspace-cli-recovery-01KRC6CY-lane-a
base_commit: 1bcab2618d377cbeed66f19be907c57009cdc28b
created_at: '2026-05-11T19:01:00.000000+00:00'
subtasks:
- T010
- T011
- T012
- T013
- T014
phase: Phase 1 - Implementation
assignee: ''
agent: ''
history:
- timestamp: '2026-05-11T19:01:00Z'
  agent: claude
  action: Prompt generated for Mission 7
authoritative_surface: src/specify_cli/cli/commands/sync.py
execution_mode: code_change
owned_files:
- src/specify_cli/cli/commands/sync.py
- tests/sync/test_sync_logged_out_recovery.py
- docs/recovery/logged-out-teamspace.md
tags: []
---

# Work Package WP02 -- Wire recovery into sync commands

## Goal

Use the `_auth_recovery` helpers from WP01 in every auth-missing branch of
the `spec-kitty sync` command surface. Add integration tests that prove the
interactive and non-interactive paths behave per the spec. Ship a one-page
operator note that documents the structured stderr line and exit code 4.

## Subtasks

- **T010** -- Update `src/specify_cli/cli/commands/sync.py`:
  - In `now()`, when `_sync_result_looks_unauthenticated(...)` is True or the
    "Sync made no progress" final block fires (strict mode), call
    `handle_unauthenticated_with_teamspace(command_name="sync now",
    console=console)`. On `EXIT_4`, raise `typer.Exit(code=4)`. On
    `LOGGED_IN`, print "Logged in. Re-run `spec-kitty sync now` to continue."
    and return (exit 0). On `QUIT` or `SKIPPED`, fall through to the existing
    `[yellow]` message and exit 1 path. On `NO_TEAMSPACE`, behavior is
    byte-identical to today.
  - In `_check_server_connection`, when the function would return
    `"[yellow]Not authenticated[/yellow]"` or `"[yellow]Session expired
    [/yellow]"`, also surface a recovery hint by exposing a new helper
    `_maybe_handle_auth_missing(command_name)` on the calling side (`status`
    with `--check=True`) that invokes the facade after the table prints.
    Easier path: extract the auth-missing decision into the `status()`
    command's `--check` branch so the recovery helper runs there after the
    table renders.
  - In `doctor()`, when the "Both access and refresh tokens are expired" or
    "Not authenticated. Run `spec-kitty auth login`." issue is emitted,
    append a call to `handle_unauthenticated_with_teamspace(command_name=
    "sync doctor", console=console)` and exit 4 if it returns `EXIT_4`.
    Other outcomes do not change the rest of the doctor output.
  - In `routes()` and `share()`, the `_require_authenticated_session()`
    helper currently exits 1 with the legacy string. Replace the current body
    of `_require_authenticated_session()` with: if a session exists, return
    it; otherwise call `handle_unauthenticated_with_teamspace(command_name=
    "sync routes"|"sync share")` and react: `EXIT_4` -> `typer.Exit(4)`;
    `LOGGED_IN` -> re-resolve session and continue; `SKIPPED`/`QUIT`/
    `NO_TEAMSPACE` -> existing `typer.Exit(1)` path. Because the helper
    accepts a `command_name`, expose it via a new private wrapper
    `_require_authenticated_session(command_name: str)` and update the two
    call sites.

- **T011** -- Add `tests/sync/test_sync_logged_out_recovery.py` using
  `typer.testing.CliRunner` and the `sync` Typer app. Mock
  `handle_unauthenticated_with_teamspace` and the underlying token manager.
  Cover, for `sync now` and `sync doctor`:
  - non-interactive + connected teamspace -> exit code 4, stderr contains
    `logged_out_on_connected_teamspace teamspace=acme-eng command=sync now
    action=run-spec-kitty-auth-login`.
  - non-interactive + no teamspace -> exit code 1, stderr does NOT contain
    `logged_out_on_connected_teamspace`, stdout contains the legacy "Run
    `spec-kitty auth login`" message.
  - interactive + teamspace + user picks `S` -> exit code 1 (we fall through
    to the existing legacy exit path on SKIPPED).
  - interactive + teamspace + user picks `L` (mocked) -> `login_impl`
    invoked exactly once; exit 0; stdout contains the "Re-run" message.
  - The doctor case skips the "Re-run" expectation since doctor's recovery
    is informational only.

- **T012** -- Verify existing suites still pass without modification:
  `pytest tests/sync/test_sync_doctor.py tests/sync/test_sync_status_command.py
  tests/sync/test_sync_status_check.py -q`.

- **T013** -- Add `docs/recovery/logged-out-teamspace.md`:
  - Operator overview of the recovery prompt.
  - Exact text of the structured stderr line and a sample CI snippet
    detecting exit code 4.
  - How to suppress the interactive prompt
    (`SPEC_KITTY_NON_INTERACTIVE=1`) and how to force it
    (`SPEC_KITTY_FORCE_INTERACTIVE=1`).
  - Cross-link to `spec-kitty auth login` and `spec-kitty sync doctor`.

- **T014** -- Mark WP02 done.

## Acceptance

- FR-006 holds: no-teamspace path is byte-identical to pre-change.
- FR-007 holds: all five sync subcommands route through the facade.
- New tests in `tests/sync/test_sync_logged_out_recovery.py` pass; existing
  sync tests pass unchanged.
- `ruff check src/specify_cli/cli/commands/sync.py
  tests/sync/test_sync_logged_out_recovery.py
  docs/recovery/logged-out-teamspace.md` is clean.

## Activity Log

- 2026-05-11T19:07:14Z – unknown – claiming for implementation
- 2026-05-11T19:07:16Z – unknown – starting work
- 2026-05-11T19:15:46Z – unknown – WP02 done: 6/6 new integration tests pass, full sync test suite 1509/1509 (excl. pre-existing daemon/orphan failures), ruff clean, docs added
- 2026-05-11T19:15:52Z – unknown – Approved: WP02 surface integrates the recovery helper into 5 sync command paths; 6/6 integration tests + 19/19 unit tests pass; ruff clean; legacy NO_TEAMSPACE path byte-identical; operator doc added
