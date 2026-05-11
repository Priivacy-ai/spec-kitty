---
work_package_id: WP01
title: Recovery helper module and unit tests
dependencies: []
requirement_refs:
- FR-001
- FR-002
- FR-003
- FR-004
- FR-005
- FR-006
planning_base_branch: kitty/mission-logged-out-teamspace-cli-recovery-01KRC6CY-lane-a
merge_target_branch: kitty/mission-logged-out-teamspace-cli-recovery-01KRC6CY-lane-a
branch_strategy: Planning artifacts for this mission were generated on kitty/mission-logged-out-teamspace-cli-recovery-01KRC6CY-lane-a. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into kitty/mission-logged-out-teamspace-cli-recovery-01KRC6CY-lane-a unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-logged-out-teamspace-cli-recovery-01KRC6CY-lane-a
base_commit: 1bcab2618d377cbeed66f19be907c57009cdc28b
created_at: '2026-05-11T19:01:00.000000+00:00'
subtasks:
- T001
- T002
- T003
phase: Phase 1 - Implementation
assignee: ''
agent: ''
shell_pid: '68506'
history:
- timestamp: '2026-05-11T19:01:00Z'
  agent: claude
  action: Prompt generated for Mission 7
authoritative_surface: src/specify_cli/cli/commands/
execution_mode: code_change
owned_files:
- src/specify_cli/cli/commands/_auth_recovery.py
- tests/cli/commands/test_auth_recovery.py
tags: []
---

# Work Package WP01 -- Recovery helper module

## Goal

Add a single new module `src/specify_cli/cli/commands/_auth_recovery.py`
exporting the detector, interactivity probe, interactive prompt, and shared
facade that downstream `sync` commands will call when authentication is
missing and a teamspace was previously connected. Cover the module end-to-end
with unit tests in `tests/cli/commands/test_auth_recovery.py`.

This WP is intentionally atomic: shipping the module and tests together makes
the surface independently reviewable without requiring any caller to import
the new helper yet (WP02 wires it in).

## Subtasks

- **T001** -- Add `src/specify_cli/cli/commands/_auth_recovery.py` containing:
  - Module constant `EXIT_LOGGED_OUT_ON_CONNECTED_TEAMSPACE: int = 4`.
  - `class RecoveryOutcome(StrEnum)` with members `LOGGED_IN`, `SKIPPED`,
    `QUIT`, `NO_TEAMSPACE`, `EXIT_4`.
  - `def detect_logged_out_with_connected_teamspace(repo_root: Path | None =
    None) -> str | None`. Resolution order:
    1. If a valid current session exists (TokenManager reports an unexpired
       access token OR a usable refresh token), return None.
    2. Try `specify_cli.sync.routing.resolve_checkout_sync_routing()`; if it
       returns a routing with a non-empty `repo_slug`, return that.
    3. Else if it has a non-empty `project_slug`, return that.
    4. Else inspect the most recently stored session via
       `TokenManager.get_current_session()`; if it has any team where
       `team.is_private_teamspace` is True and `team.name` is non-empty,
       return that team name.
    5. Else return None.
    All imports of `TokenManager` / sync routing must be inside the function
    (lazy) to keep import cost low. Function must not perform network I/O.
  - `def is_interactive() -> bool`. Returns True iff:
    - `os.environ.get("SPEC_KITTY_FORCE_INTERACTIVE") == "1"` (highest
      priority), OR
    - `sys.stdin.isatty()` is True AND
      `os.environ.get("SPEC_KITTY_NON_INTERACTIVE") != "1"`.
  - `def _read_one_keystroke() -> str`. Tries `readchar.readkey()`; on any
    ImportError or OSError falls back to
    `(sys.stdin.readline() or "").strip().lower()[:1] or ""`. Returns the
    keystroke lowercased and truncated to one char.
  - `def offer_login_recovery(*, teamspace: str, command_name: str,
    console: Console) -> RecoveryOutcome`. Prints a Rich panel naming the
    teamspace and command, then prompts `[L]ogin / [S]kip / [Q]uit`. On `l`,
    invokes
    `asyncio.run(specify_cli.cli.commands._auth_login.login_impl(headless=
    False, force=False))` and returns `LOGGED_IN`. If `login_impl` raises any
    subclass of `specify_cli.auth.errors.AuthenticationError`, the error is
    printed and `SKIPPED` is returned. On `s` returns `SKIPPED`. On `q`
    returns `QUIT`. Any other input is treated as `SKIPPED`.
  - `def emit_structured_stderr(*, teamspace: str, command_name: str) -> None`
    -- writes the canonical line to `sys.stderr`:
    `spec-kitty: logged_out_on_connected_teamspace teamspace=<slug>
    command=<name> action=run-spec-kitty-auth-login\n`. ASCII only,
    no Rich markup.
  - `def handle_unauthenticated_with_teamspace(*, command_name: str,
    console: Console) -> RecoveryOutcome` -- facade:
    1. `teamspace = detect_logged_out_with_connected_teamspace()`.
    2. If `teamspace is None` -> `return RecoveryOutcome.NO_TEAMSPACE`.
    3. If `is_interactive()` -> call `offer_login_recovery(...)` and return
       its outcome.
    4. Else -> `emit_structured_stderr(...)` and `return
       RecoveryOutcome.EXIT_4`.

- **T002** -- Add `tests/cli/commands/test_auth_recovery.py` covering:
  - `detect_logged_out_with_connected_teamspace`:
    * with a valid `TokenManager` session -> returns None.
    * with no session + routing returning `repo_slug="acme-eng"` -> returns
      `"acme-eng"`.
    * with no session + routing returning slug=None but `project_slug="acme"`
      -> returns `"acme"`.
    * with no session + routing returning None + stored session has a private
      team named `"Engineering"` -> returns `"Engineering"`.
    * with no session + no routing + no stored session -> returns None.
  - `is_interactive`:
    * TTY + no env -> True.
    * TTY + `SPEC_KITTY_NON_INTERACTIVE=1` -> False.
    * no TTY + no env -> False.
    * no TTY + `SPEC_KITTY_FORCE_INTERACTIVE=1` -> True.
  - `offer_login_recovery` (with `_read_one_keystroke` monkeypatched and
    `_auth_login.login_impl` patched as `AsyncMock`):
    * input `"l"` -> `LOGGED_IN`, `login_impl` awaited once.
    * input `"s"` -> `SKIPPED`, `login_impl` not called.
    * input `"q"` -> `QUIT`.
    * `login_impl` raises `AuthenticationError("nope")` -> `SKIPPED`, error
      message rendered to console.
  - `handle_unauthenticated_with_teamspace`:
    * detector returns None -> `NO_TEAMSPACE`, no stderr output, no prompt
      called.
    * detector returns `"acme-eng"` + non-interactive -> `EXIT_4`, captured
      stderr contains the canonical line with `teamspace=acme-eng
      command=test action=run-spec-kitty-auth-login`.
    * detector returns `"acme-eng"` + interactive -> `offer_login_recovery`
      called with the slug; return value propagated.

- **T003** -- Run `pytest tests/cli/commands/test_auth_recovery.py -q` and
  confirm all tests pass; mark WP01 done.

## Acceptance

- All five FRs referenced above are exercised by `test_auth_recovery.py`.
- `ruff check src/specify_cli/cli/commands/_auth_recovery.py
  tests/cli/commands/test_auth_recovery.py` is clean.
- Module has no top-level imports of `readchar`, `TokenManager`, or
  `_auth_login` (all lazy) so importing it does not trigger network /
  filesystem side-effects in unrelated tests.

## Activity Log

- 2026-05-11T19:07:08Z – unknown – shell_pid=68506 – Approved: 19/19 unit tests pass, ruff clean, FRs 001-006 covered
