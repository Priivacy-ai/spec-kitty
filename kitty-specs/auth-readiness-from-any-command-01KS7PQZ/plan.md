# Implementation Plan: Auth Readiness From Any Command

**Mission**: `auth-readiness-from-any-command-01KS7PQZ`
**Spec**: [spec.md](./spec.md)
**Target branch**: `main`

## Architecture

The readiness coordinator already executes on every CLI invocation through the root callback in `src/specify_cli/cli/helpers.py`. Wave 1 left a typed stub for the auth probe — `from specify_cli.cli.commands._auth_recovery import detect_logged_out_with_connected_teamspace` is imported at module scope of `src/specify_cli/readiness/coordinator.py` and explicitly marked `# WS2: auth probe wiring`. This mission turns that stub into a working probe + renderer.

```
                                                                                                                      
        root callback                                                                                                 
  (specify_cli/cli/helpers.py)                                                                                        
              │                                                                                                       
              ▼                                                                                                       
   evaluate_readiness(ctx)                                                                                            
              │                                                                                                       
              ▼                                                                                                       
   _evaluate_uncached(ctx)                                                                                            
              │                                                                                                       
        ┌─────┴───────────────┐                                                                                       
        │                     │                                                                                       
   hosted OFF             hosted ON (is_saas_sync_enabled())                                                          
        │                     │                                                                                       
        │                     ├─▶ output_policy = _derive_output_policy()                                             
        │                     │                                                                                       
        │                     ├─▶ auth_status, teamspace = probe_auth_status()    ← NEW (auth.py)                     
        │                     │                                                                                       
        │                     ├─▶ if auth_status == LOGGED_OUT_IN_TEAMSPACE:                                          
        │                     │       render_auth_guidance(...)                   ← NEW (render.py)                   
        │                     │                                                                                       
        │                     ├─▶ _invoke_nag(ctx)            (existing — order preserved)                            
        │                     │                                                                                       
        │                     └─▶ return ReadinessResult(enabled=True, ran=True, auth_status, ...)                    
        │                                                                                                             
        ├─▶ _invoke_nag(ctx)                                                                                          
        │                                                                                                             
        └─▶ return ReadinessResult(enabled=False, ran=False, auth_status=DISABLED, ...)                               
```

### Module surfaces

| File | Status | Change |
|------|--------|--------|
| `src/specify_cli/readiness/coordinator.py` | Modify | Extend `AuthStatus` enum with `AUTHENTICATED`, `LOGGED_OUT_IN_TEAMSPACE`, `NOT_IN_TEAMSPACE`, `UNKNOWN`. Modify `_evaluate_uncached` on the enabled path to call `probe_auth_status` and (conditionally) `render_auth_guidance`. |
| `src/specify_cli/readiness/auth.py` | NEW | `probe_auth_status(*, repo_root=None) -> tuple[AuthStatus, str | None]`. Uses `TokenManager.is_authenticated` and `detect_logged_out_with_connected_teamspace`. Returns the teamspace handle for the renderer. Wraps all exceptions and returns `(UNKNOWN, None)` on failure. |
| `src/specify_cli/readiness/render.py` | NEW | `render_auth_guidance(*, status, teamspace, command_name, output_policy) -> None`. Branches on `output_policy`: `INTERACTIVE` → multiline rich panel on stderr; `NON_INTERACTIVE` → reuses `_auth_recovery.emit_structured_stderr`; `MACHINE_OUTPUT` → no-op. Swallows all exceptions. |
| `src/specify_cli/readiness/__init__.py` | Modify | Re-export the new symbols only if user-visible; otherwise keep the existing 5-symbol surface stable. **Decision: keep the 5-symbol public surface; new probe/render are module-internal.** |
| `tests/readiness/test_auth_probe.py` | NEW | Probe unit tests: each of the 4 new enum values + the `UNKNOWN` exception path is reachable. |
| `tests/readiness/test_auth_renderer.py` | NEW | Renderer unit tests: each output-policy bucket × `LOGGED_OUT_IN_TEAMSPACE` + the no-op branches. |
| `tests/readiness/test_auth_coordinator_matrix.py` | NEW | 8-row integration matrix from `spec.md` Scenarios 1–8 via `evaluate_readiness(ctx)`. |
| `tests/readiness/test_coordinator_suppression_matrix.py` | Modify (minimal) | The `hosted_enabled_interactive` row's expected `auth_status` changes from `NOT_CHECKED` to "one of the authoritative values" (will be `NOT_IN_TEAMSPACE` in the test environment with no Teamspace markers). Change one assertion; no row count change. |

### Dependencies

- **No new pip deps.** All imports are stdlib or already in the codebase:
  - `_auth_recovery.detect_logged_out_with_connected_teamspace` — existing.
  - `_auth_recovery.emit_structured_stderr` — existing.
  - `specify_cli.auth.get_token_manager` — existing.
  - `rich.panel.Panel`, `rich.console.Console` — already a dependency.

### Test strategy

1. **Probe tests** (`test_auth_probe.py`):
   - `AUTHENTICATED`: mock `TokenManager.is_authenticated = True` → `(AUTHENTICATED, None)`.
   - `LOGGED_OUT_IN_TEAMSPACE`: mock `TokenManager.is_authenticated = False`, mock `detect_logged_out_with_connected_teamspace -> "my-team"` → `(LOGGED_OUT_IN_TEAMSPACE, "my-team")`.
   - `NOT_IN_TEAMSPACE`: mock `TokenManager.is_authenticated = False`, mock `detect_logged_out_with_connected_teamspace -> None` → `(NOT_IN_TEAMSPACE, None)`.
   - `UNKNOWN`: mock `get_token_manager` to raise → `(UNKNOWN, None)`. Also `UNKNOWN` if the helper raises.

2. **Renderer tests** (`test_auth_renderer.py`):
   - `INTERACTIVE` + `LOGGED_OUT_IN_TEAMSPACE` → stderr contains "spec-kitty auth login" and the teamspace handle; stdout empty.
   - `NON_INTERACTIVE` + `LOGGED_OUT_IN_TEAMSPACE` → stderr contains exactly the canonical single-line `spec-kitty: logged_out_on_connected_teamspace …`; stdout empty.
   - `MACHINE_OUTPUT` + `LOGGED_OUT_IN_TEAMSPACE` → no output.
   - Any policy + non-`LOGGED_OUT_IN_TEAMSPACE` status → no output.
   - Renderer crashes are swallowed (no exception escapes).

3. **Coordinator matrix** (`test_auth_coordinator_matrix.py`):
   - Eight parametrized rows from Scenarios 1–8 exercising the full integration:
     - Hosted-off: `disabled` no leakage.
     - Hosted-on + authenticated + TTY: `AUTHENTICATED`, silent.
     - Hosted-on + logged_out_in_teamspace + TTY: `LOGGED_OUT_IN_TEAMSPACE`, multiline stderr panel.
     - Hosted-on + logged_out_in_teamspace + non-TTY: `LOGGED_OUT_IN_TEAMSPACE`, single-line stderr.
     - Hosted-on + not_in_teamspace + TTY: `NOT_IN_TEAMSPACE`, silent.
     - Hosted-on + logged_out_in_teamspace + `--json`: `LOGGED_OUT_IN_TEAMSPACE`, no stderr text.
     - Hosted-on + logged_out_in_teamspace + `--quiet`: silent.
     - Authenticated + `--help`: silent.

4. **Regression**: existing Wave 1 tests (`test_coordinator_suppression_matrix.py`, `test_coordinator_nag_passthrough.py`, `test_coordinator_caching.py`) all stay green. Only one assertion in the suppression matrix is relaxed (see "Module surfaces" above), and the relaxation does not weaken the no-leakage guarantee — the assertion still checks "no `teamspace` substring in stdout/stderr".

### Risks and mitigations

| Risk | Mitigation |
|------|-----------|
| Probe blocks startup with slow I/O. | Helper already uses local signals only + lazy imports. No network I/O. NFR-001: <5ms median budget. |
| Renderer crashes inside the coordinator → CLI broken. | Wrap the renderer call in a `try/except` inside `_evaluate_uncached`, swallow exceptions to preserve Wave 1's "never raise" invariant. |
| Existing sync commands' guidance flow regresses. | Sync commands keep calling `handle_unauthenticated_with_teamspace` independently; the new coordinator probe is additive. Existing sync tests in `tests/sync/` MUST remain green. |
| Token-manager import-time side effects. | All imports inside the probe are lazy (`PLC0415`-style) following Wave 1's pattern. |
| Concurrent worktree contention overwrites changes during this mission. | This mission runs entirely in `.worktrees/auth-readiness-from-any-command-01KS7PQZ`, which is git-isolated. |

### File-level acceptance check

After implementation, the diff against `main` MUST contain exactly:

- `src/specify_cli/readiness/coordinator.py` (modified — enum extension + 5–15 lines in `_evaluate_uncached`).
- `src/specify_cli/readiness/auth.py` (new — ~60–80 lines).
- `src/specify_cli/readiness/render.py` (new — ~60–80 lines).
- `tests/readiness/test_auth_probe.py` (new).
- `tests/readiness/test_auth_renderer.py` (new).
- `tests/readiness/test_auth_coordinator_matrix.py` (new).
- `tests/readiness/test_coordinator_suppression_matrix.py` (minimal — 1 assertion relaxed).
- `kitty-specs/auth-readiness-from-any-command-01KS7PQZ/` (mission artifacts).

No other files touched.

## Decision log

- **D1**: Renderer reuses `_auth_recovery.emit_structured_stderr` for the non-interactive path rather than reimplementing. Rationale: single source of truth for the stable CI line; the format is part of the existing public-facing contract.
- **D2**: Probe returns `tuple[AuthStatus, str | None]` rather than a dataclass. Rationale: simpler API, only one downstream consumer (the renderer needs the handle), no premature abstraction.
- **D3**: `AuthStatus.NOT_CHECKED` is preserved as a non-canonical value for backward compatibility but is never *produced* by the new probe — the coordinator now sets one of the 5 authoritative values (`DISABLED`, `AUTHENTICATED`, `LOGGED_OUT_IN_TEAMSPACE`, `NOT_IN_TEAMSPACE`, `UNKNOWN`). Wave 1's contract document permits enum extension; this honors it.
- **D4**: The Wave 1 `hosted_enabled_interactive` suppression-matrix row needs ONE assertion relaxed (from `NOT_CHECKED` to `NOT_IN_TEAMSPACE`). This is explicitly permitted by the Wave 1 contract: "WS2 MAY add `AuthStatus` values without breaking this contract". The "no Teamspace leakage" assertion in that test row is unchanged and continues to pass.
- **D5**: Renderer order: nag fires first (Wave 1 invariant), auth guidance fires second. Stderr order matters for log scrapers but both are best-effort — we preserve Wave 1's existing call order.

## Out-of-scope confirmation

- Upgrade UX, tracker alignment, docs missions are excluded — verified by file-level acceptance check above.
- No `pyproject.toml` change. No `.kittify/config.yaml` change. No SaaS-side change. No ingress change.
