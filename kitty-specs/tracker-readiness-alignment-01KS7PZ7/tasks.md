# Tasks — Tracker Readiness Alignment (CLI side)

Two work packages. WP02 depends on WP01 (tests target the new renderer).

## WP01 — Output-policy-aware readiness renderer

**Scope.** In `src/specify_cli/cli/commands/tracker.py`:
- Introduce `_resolve_output_policy_for_tracker() -> str`. Reads the active `OutputPolicy` from the cached coordinator result via `click.get_current_context(silent=True)` + `get_readiness`. Falls back to `_derive_output_policy()` when ctx is unreachable.
- Introduce `_render_readiness_failure(result) -> None` private helper.
- Branch the output:
  - `INTERACTIVE` → unchanged 2-line behaviour.
  - `MACHINE_OUTPUT` → single line: `result.next_action` only (when present), else `result.message`.
  - `NON_INTERACTIVE` → single line: `f"spec-kitty tracker: readiness={state} next=spec-kitty-auth-login"` for MISSING_AUTH; slugified next_token for other states.
- Update `_check_readiness` to call the new helper.

**Out of scope.** Any changes to `saas/readiness.py`, the coordinator, or other tracker subcommands.

**Acceptance.** New helper produces the expected stderr line per the test matrix; existing tests pass (after the test-side INTERACTIVE patches in WP02).

## WP02 — Contract tests

**Scope.** Extend `tests/agent/cli/commands/test_tracker.py`:

- `test_ws5_hosted_no_auth_interactive_two_line_human_format`
- `test_ws5_hosted_no_auth_machine_output_single_line_stderr`
- `test_ws5_hosted_no_auth_non_interactive_stable_machine_line`
- `test_ws5_local_tracker_skips_hosted_readiness_probe`
- `test_ws5_remediation_string_matches_saas_readiness_source`

Update `test_status_readiness_missing_auth_message` (in `test_tracker.py`) and the parametrised tests in `test_tracker_status.py` / `test_tracker_discover.py` to force `INTERACTIVE` policy so they continue to validate the human wording.

Mark each new test with `@pytest.mark.no_readiness_stub` so the autouse stub doesn't suppress them.

**Acceptance.** All six new/updated tests pass; `pytest tests/agent/cli/commands/test_tracker*.py` is green.
