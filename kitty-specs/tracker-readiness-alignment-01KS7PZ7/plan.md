# Plan — Tracker Readiness Alignment (CLI side)

## Architecture

The CLI already has two readiness surfaces:

1. **Central coordinator** (`specify_cli.readiness.coordinator`) — owns `OutputPolicy` (`INTERACTIVE` / `NON_INTERACTIVE` / `MACHINE_OUTPUT`) and is invoked once per CLI startup from the root callback. Result is cached on `ctx.obj`.
2. **Hosted SaaS readiness** (`specify_cli.saas.readiness`) — owns the `ReadinessState` chain (`ROLLOUT_DISABLED` → `MISSING_AUTH` → `MISSING_HOST_CONFIG` → ...) used by tracker subcommands via `_check_readiness`.

The tracker readiness gate currently lives in `cli/commands/tracker.py::_check_readiness`. It writes a 2-line `secho(message) + echo(next_action)` to stderr on any non-ready state. This mission re-shapes that renderer to consult the coordinator's `OutputPolicy` and choose:

- **INTERACTIVE** → existing 2-line human format (unchanged).
- **MACHINE_OUTPUT** (`--json` / `--quiet`) → single-line stderr ending with the remediation string only; stdout untouched.
- **NON_INTERACTIVE** (help / version / CI / non-TTY) → stable machine-readable line `spec-kitty tracker: readiness=<state> next=spec-kitty-auth-login`.

`get_readiness(ctx)` from the coordinator returns `_NOOP_DISABLED` when no ctx is available, so the renderer needs a defensive fallback when called outside a Typer `ctx` (e.g., direct test invocation). In that case it falls back to deriving the policy directly from argv via the coordinator's `_derive_output_policy()` helper.

## File-level changes

| File | Change |
|---|---|
| `src/specify_cli/cli/commands/tracker.py` | Replace the `if not result.is_ready:` block in `_check_readiness` with a renderer that selects format based on coordinator-derived `OutputPolicy`. Add small private helpers `_resolve_output_policy_for_tracker()` and `_render_readiness_failure(result)`. Lazy-import the coordinator inside the helper. |
| `tests/agent/cli/commands/test_tracker.py` | Add five new WS5 tests (each marked `@pytest.mark.no_readiness_stub`): one per AC matrix row. |
| `tests/agent/cli/commands/test_tracker_status.py` | Update two existing parametrised tests + the `test_status_host_unreachable_message` test to force `INTERACTIVE` policy so they continue to validate the canonical 2-line wording. |
| `tests/agent/cli/commands/test_tracker_discover.py` | Same `INTERACTIVE` patch for the readiness-failure parametrised test. |

## Dependencies

- No new third-party deps.
- New internal imports: `specify_cli.readiness.coordinator.get_readiness`, `specify_cli.readiness.coordinator.OutputPolicy`, `specify_cli.readiness.coordinator._derive_output_policy`, and `click`. Lazy-imported inside `_resolve_output_policy_for_tracker` to avoid an import cycle with `saas/readiness.py`.

## Test strategy

All new tests live in `tests/agent/cli/commands/test_tracker.py` under the dedicated `# WS5 (...)` section at the end of the file. Each test:

1. Sets `SPEC_KITTY_ENABLE_SAAS_SYNC=1` via monkeypatch.
2. Stubs `evaluate_readiness` to return a synthetic `MISSING_AUTH` `ReadinessResult` constructed from the canonical `_WORDING` dict (so a future change to the canonical message bubbles through every test).
3. Patches `specify_cli.cli.commands.tracker._resolve_output_policy_for_tracker` to drive the desired bucket. (Direct policy patching is simpler and avoids depending on environment-detection internals.)
4. Asserts stdout/stderr byte content against the matrix in `spec.md`.

Backward compatibility: the existing autouse `_stub_check_readiness` fixture continues to apply to legacy tests not marked `no_readiness_stub`. The patch surface — `specify_cli.cli.commands.tracker._check_readiness` — is preserved.

## Operating-rule compliance

- No SaaS DB / queue / readiness counter mutation: this mission only changes how stderr is rendered; no state is written.
- No new pip deps.
- No event producers introduced; nothing to lint.
- Edits are confined to `cli/commands/tracker.py` + four test files. No coordinator internals are modified; we only consume the public `get_readiness` / `OutputPolicy` surfaces (plus `_derive_output_policy` for the no-ctx fallback, which is module-private to the coordinator but unchanged for many releases).
- The mission ran from an isolated worktree to coexist with sister missions C/D/F on the same repo without corrupting their working trees. See the "subagent execution notes" in `spec.md`.
