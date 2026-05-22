# Tasks: Auth Readiness From Any Command

**Mission**: `auth-readiness-from-any-command-01KS7PQZ`
**Spec**: [spec.md](./spec.md) · **Plan**: [plan.md](./plan.md)

This mission has a small, tightly-coupled diff (~3 production modules + 3 test files). It is split into 3 sequential work packages so the implement-review loop has clear hand-offs but each WP stays reviewable in one pass.

## Dependency graph

```
WP01 (probe + enum extension)
   │
   ▼
WP02 (renderer)
   │
   ▼
WP03 (coordinator wiring + integration matrix tests)
```

All three WPs target the same lane (lane-a). Each WP commits the source change and its own unit tests. WP03 also touches the one assertion in the pre-existing Wave 1 suppression-matrix test (per `plan.md` "Module surfaces").

## Work Packages

### WP01 — Auth probe and `AuthStatus` extension

**Goal**: Extend `AuthStatus` and add the probe module so subsequent WPs have something to call.

**Files**:
- `src/specify_cli/readiness/coordinator.py` (extend `AuthStatus` enum only — do NOT touch `_evaluate_uncached` in this WP).
- `src/specify_cli/readiness/auth.py` (new).
- `tests/readiness/test_auth_probe.py` (new).

**Acceptance**:
- `AuthStatus` exports `AUTHENTICATED`, `LOGGED_OUT_IN_TEAMSPACE`, `NOT_IN_TEAMSPACE`, `UNKNOWN` in addition to `NOT_CHECKED`, `DISABLED`.
- `probe_auth_status(*, repo_root: Path | None = None) -> tuple[AuthStatus, str | None]` exists in `specify_cli.readiness.auth`.
- The probe uses no network I/O. All heavy imports are lazy.
- `test_auth_probe.py` exercises each of the 5 producible enum values (DISABLED is NOT producible by the probe — the coordinator sets it on the hosted-off path; the probe only runs when hosted mode is on, so it produces one of `AUTHENTICATED`/`LOGGED_OUT_IN_TEAMSPACE`/`NOT_IN_TEAMSPACE`/`UNKNOWN`).
- Test suite stays green (`pytest tests/readiness/`).

**Dependencies**: none.

### WP02 — Guidance renderer

**Goal**: Render auth guidance per `OutputPolicy`. Reuse `_auth_recovery.emit_structured_stderr` for the non-interactive path.

**Files**:
- `src/specify_cli/readiness/render.py` (new).
- `tests/readiness/test_auth_renderer.py` (new).

**Acceptance**:
- `render_auth_guidance(*, status: AuthStatus, teamspace: str | None, command_name: str, output_policy: OutputPolicy) -> None` exists.
- `OutputPolicy.INTERACTIVE` + `LOGGED_OUT_IN_TEAMSPACE`: multiline rich panel on stderr, contains the teamspace handle and the literal remediation `spec-kitty auth login`. Stdout untouched.
- `OutputPolicy.NON_INTERACTIVE` + `LOGGED_OUT_IN_TEAMSPACE`: exactly the canonical single line on stderr from `_auth_recovery.emit_structured_stderr`. Stdout untouched.
- `OutputPolicy.MACHINE_OUTPUT`: no-op. Stdout and stderr both untouched.
- Any non-`LOGGED_OUT_IN_TEAMSPACE` status: no-op.
- Renderer never raises (all exceptions swallowed).
- Test suite stays green.

**Dependencies**: WP01 (uses the extended `AuthStatus` enum).

### WP03 — Coordinator wiring + 8-row matrix

**Goal**: Wire the probe and renderer into `_evaluate_uncached`. Add the integration matrix test. Relax the one Wave 1 assertion permitted by the Wave 1 contract.

**Files**:
- `src/specify_cli/readiness/coordinator.py` (modify `_evaluate_uncached` on the hosted-enabled path: call probe → write `auth_status` → call renderer when `LOGGED_OUT_IN_TEAMSPACE`).
- `tests/readiness/test_auth_coordinator_matrix.py` (new — 8 rows).
- `tests/readiness/test_coordinator_suppression_matrix.py` (modify ONE assertion in the `hosted_enabled_interactive` row: from `AuthStatus.NOT_CHECKED` to "one of `{AUTHENTICATED, LOGGED_OUT_IN_TEAMSPACE, NOT_IN_TEAMSPACE, UNKNOWN}`"; the no-leakage assertion is unchanged).

**Acceptance**:
- All 8 matrix rows pass per `spec.md` Scenarios 1–8.
- Hosted-off rows in the legacy suppression matrix still pass byte-identical.
- `evaluate_readiness` still never raises (wrap probe + renderer in a try/except inside the coordinator).
- Renderer call is gated by `auth_status == LOGGED_OUT_IN_TEAMSPACE` AND `output_policy in {INTERACTIVE, NON_INTERACTIVE}` — `MACHINE_OUTPUT` is silent.
- Nag invocation order is preserved (nag fires first, auth guidance second).
- Full `pytest tests/readiness/` green.

**Dependencies**: WP01 + WP02.

## Out-of-scope items (mirroring spec.md)

- Upgrade UX, tracker alignment, docs (Missions D/E/F).
- Refactoring `_auth_recovery.detect_logged_out_with_connected_teamspace`.
- SaaS-side changes.
- Flipping launch defaults.
