# Mission Specification: Auth Readiness From Any Command

**Mission ID**: `01KS7PQZT1WW259DACAPH09XC8`
**Mission slug**: `auth-readiness-from-any-command-01KS7PQZ`
**Mission type**: `software-dev`
**Target branch**: `main`
**Tracking issue**: [Priivacy-ai/spec-kitty#1094](https://github.com/Priivacy-ai/spec-kitty/issues/1094)
**Predecessor**: [#1093 — central CLI startup readiness coordinator](https://github.com/Priivacy-ai/spec-kitty/issues/1093) (commit `77c1647e7`)

## Purpose

**TLDR**: Wire the readiness coordinator's auth probe so any spec-kitty command surfaces logged-out-in-teamspace guidance through one seam.

**Context**: Wave 1 (issue #1093) landed the central CLI startup readiness coordinator with a stub `AuthStatus`. This mission exercises the existing `detect_logged_out_with_connected_teamspace()` helper inside the coordinator on the hosted-enabled path, widens `AuthStatus` to authoritative values, and renders guidance for both TTY and non-TTY contexts while honoring the Wave 1 suppression contract byte-for-byte.

## Problem Statement

Currently `_auth_recovery.detect_logged_out_with_connected_teamspace()` is only consulted by a subset of commands (the `spec-kitty sync ...` family). With the Wave 1 readiness coordinator now in place, every CLI invocation has a single readiness pass — but `AuthStatus` is always `NOT_CHECKED` on the enabled path because the probe is a stub seam. We need to actually exercise the detection helper from the coordinator, produce an authoritative `AuthStatus` value, and render guidance for both interactive and non-interactive contexts without violating the suppression contract that the Wave 1 mission established.

## Intent Summary

- **Primary actor**: any operator running any `spec-kitty` subcommand with hosted mode enabled.
- **Trigger**: every CLI invocation passes through the root callback, which already calls `evaluate_readiness(ctx)`.
- **Happy-path outcome**: when the operator is authenticated, the readiness coordinator silently sets `AuthStatus.AUTHENTICATED`; no UI noise is added beyond what existed before Wave 1.
- **Exception path** (the value-add of this mission): when the operator is logged out *and* the local repo state shows a connected Teamspace, the coordinator surfaces actionable guidance once per invocation — multiline rich panel on stderr in TTY mode, single-line stable stderr message in CI/non-TTY mode, nothing at all for `--json`/`--quiet`/`--help`/`--version`.
- **Invariant always true**: if `is_saas_sync_enabled()` returns false, no Teamspace-labeled text appears anywhere in the CLI output — Wave 1's "no leakage" guarantee is preserved.
- **Canonical term**: "Teamspace" (one word, capitalized) is the user-facing term; "teamspace" (lowercase) is reserved for code identifiers. The structured stderr line uses `teamspace=<slug>` as defined by `_auth_recovery.emit_structured_stderr`.

## User Scenarios & Testing

### Scenario 1 — Hosted mode disabled (default today, the launch invariant)
- Given: `SPEC_KITTY_ENABLE_SAAS_SYNC` is not set.
- When: an operator runs `spec-kitty status` (or any other command).
- Then: no Teamspace-labeled output anywhere; `ReadinessResult.auth_status == AuthStatus.DISABLED`; existing Wave 1 suppression-matrix tests still pass byte-identical.

### Scenario 2 — Hosted mode enabled, authenticated
- Given: `SPEC_KITTY_ENABLE_SAAS_SYNC=1`, valid session in keyring.
- When: any command runs.
- Then: probe sets `AuthStatus.AUTHENTICATED`; no guidance rendered; no prompt.

### Scenario 3 — Hosted mode enabled, logged out, no Teamspace markers in repo
- Given: `SPEC_KITTY_ENABLE_SAAS_SYNC=1`, no session, no routing/team metadata.
- When: any command runs.
- Then: probe sets `AuthStatus.NOT_IN_TEAMSPACE`; no guidance rendered; no prompt.

### Scenario 4 — Hosted mode enabled, logged out, connected Teamspace, TTY
- Given: `SPEC_KITTY_ENABLE_SAAS_SYNC=1`, no session, `detect_logged_out_with_connected_teamspace()` returns a non-None handle, `stdout.isatty() == True`, `OutputPolicy.INTERACTIVE`.
- When: any normal command runs.
- Then: probe sets `AuthStatus.LOGGED_OUT_IN_TEAMSPACE`; coordinator emits a multiline rich panel on **stderr** including the remediation string `spec-kitty auth login`. Stdout untouched.

### Scenario 5 — Hosted mode enabled, logged out, connected Teamspace, non-TTY
- Given: same as Scenario 4 but `OutputPolicy.NON_INTERACTIVE` (CI env or non-TTY stdout).
- When: any normal command runs.
- Then: probe sets `AuthStatus.LOGGED_OUT_IN_TEAMSPACE`; coordinator writes a single stable ASCII line to stderr: `spec-kitty: logged_out_on_connected_teamspace teamspace=<slug> command=<name> action=run-spec-kitty-auth-login`. No prompt, no blocking.

### Scenario 6 — Hosted mode enabled, logged-out-in-teamspace, `--json`
- Given: same as Scenario 4 but argv contains `--json` (`OutputPolicy.MACHINE_OUTPUT`).
- When: any command runs.
- Then: probe sets `AuthStatus.LOGGED_OUT_IN_TEAMSPACE` (the field reflects the truth) but **no stderr text is emitted**. Stdout JSON is byte-intact.

### Scenario 7 — Hosted mode enabled, `--quiet`
- Then: same as Scenario 6 — silent.

### Scenario 8 — Authenticated + `--help` / `--version`
- Then: silent. Probe may still set `AuthStatus.AUTHENTICATED`; nothing is rendered.

## Domain Language

- **Hosted mode**: enabled via the `SPEC_KITTY_ENABLE_SAAS_SYNC` env var; checked by `is_saas_sync_enabled()`.
- **Connected Teamspace**: local repo has sync-routing metadata, stored session/team metadata, or repo/project markers pointing at a Teamspace.
- **`AuthStatus`**: the coordinator's enum recording the verdict of the readiness probe. Pre-mission values: `NOT_CHECKED`, `DISABLED`. Post-mission values: `NOT_CHECKED` (preserved alias for backward compatibility), `DISABLED`, `AUTHENTICATED`, `LOGGED_OUT_IN_TEAMSPACE`, `NOT_IN_TEAMSPACE`, `UNKNOWN`.
- **OutputPolicy**: existing three-bucket suppression classification (`INTERACTIVE`, `NON_INTERACTIVE`, `MACHINE_OUTPUT`) computed by `_derive_output_policy`. The renderer consults this bucket to decide what (if anything) to emit.

## Functional Requirements

| ID | Status | Requirement |
|----|--------|-------------|
| FR-001 | Required | Add an auth readiness probe at `src/specify_cli/readiness/auth.py` that wraps `_auth_recovery.detect_logged_out_with_connected_teamspace()` and maps the result plus session state into an `AuthStatus` value. |
| FR-002 | Required | Extend `AuthStatus` in `src/specify_cli/readiness/coordinator.py` with `AUTHENTICATED`, `LOGGED_OUT_IN_TEAMSPACE`, `NOT_IN_TEAMSPACE`, `UNKNOWN`. Preserve `NOT_CHECKED` and `DISABLED` for backward compatibility. |
| FR-003 | Required | Probe MUST use local signals only — no network I/O during startup. |
| FR-004 | Required | Probe runs only when `is_saas_sync_enabled()` returns true. On the disabled path, `ReadinessResult.auth_status == AuthStatus.DISABLED` is preserved byte-identical to Wave 1. |
| FR-005 | Required | Add a guidance renderer at `src/specify_cli/readiness/render.py` with two surface functions: one for `OutputPolicy.INTERACTIVE`, one for `OutputPolicy.NON_INTERACTIVE`. Both write to stderr only. |
| FR-006 | Required | Interactive renderer emits a multiline rich panel that includes the remediation command `spec-kitty auth login` and the resolved teamspace handle. |
| FR-007 | Required | Non-interactive renderer emits a single stable ASCII line on stderr: `spec-kitty: logged_out_on_connected_teamspace teamspace=<slug> command=<name> action=run-spec-kitty-auth-login`. Reuse `_auth_recovery.emit_structured_stderr` to avoid duplication. |
| FR-008 | Required | Renderer is invoked from `_evaluate_uncached` only when `auth_status == LOGGED_OUT_IN_TEAMSPACE` AND `output_policy in {INTERACTIVE, NON_INTERACTIVE}`. For `MACHINE_OUTPUT`, the probe still records the status but no stderr text is emitted. |
| FR-009 | Required | Coordinator must never raise out of the readiness path. Any probe/renderer exception is swallowed and `ReadinessResult.auth_status` falls back to `UNKNOWN`. |
| FR-010 | Required | The new code MUST NOT mutate the SaaS DB, queue, or readiness counters. |
| FR-011 | Required | Existing sync-command auth gating (in `src/specify_cli/cli/commands/sync.py` and friends) MUST remain unchanged. The new probe is additive only. |
| FR-012 | Required | Tests cover the 8-row auth matrix from Scenarios 1–8 above. |
| FR-013 | Required | Existing Wave 1 suppression-matrix tests (`tests/readiness/test_coordinator_suppression_matrix.py`) pass without modification on the hosted-off rows. The single hosted-on row in that file is allowed to be relaxed from `NOT_CHECKED` to "one of the authoritative values" — see plan for the exact change. |

## Non-Functional Requirements

| ID | Status | Requirement | Threshold |
|----|--------|-------------|-----------|
| NFR-001 | Required | Startup overhead added by the auth probe. | < 5 ms median on a clean repo with no Teamspace markers (local signals only; bounded by one dict-style lookup of routing metadata and one keyring read by the existing `TokenManager`). |
| NFR-002 | Required | No new pip dependency. | Net new entries in `pyproject.toml` `[project] dependencies` MUST be zero. |
| NFR-003 | Required | Pre-existing Wave 1 tests stay green. | `pytest tests/readiness/test_coordinator_suppression_matrix.py tests/readiness/test_coordinator_nag_passthrough.py tests/readiness/test_coordinator_caching.py` exits 0. |

## Constraints

| ID | Status | Constraint |
|----|--------|-----------|
| C-001 | Required | Probe gated behind `is_saas_sync_enabled()` — no Teamspace-labeled output anywhere when hosted mode is off. |
| C-002 | Required | No refactoring of `_auth_recovery.detect_logged_out_with_connected_teamspace`. Reuse only. |
| C-003 | Required | Coordinator must never raise from the readiness path — Wave 1 invariant (FR-010 of #1093). |
| C-004 | Required | Public default CLI output stays Teamspace-free in hosted-off mode. |
| C-005 | Required | `spec-kitty next` is the only entry point for advancing WP state. `status.events.jsonl` is sole authority. |
| C-006 | Required | No new pip deps. No SaaS DB/queue/readiness mutation. No ingress changes. |
| C-007 | Required | `unset GITHUB_TOKEN` before any `gh` write. No direct `main` push — PR only. |

## Success Criteria

1. Every CLI invocation in hosted-on mode has a deterministic `AuthStatus` value (one of `AUTHENTICATED`, `LOGGED_OUT_IN_TEAMSPACE`, `NOT_IN_TEAMSPACE`, `UNKNOWN`) — measured by the new probe-coverage test asserting each enum member is reachable.
2. Logged-out-in-Teamspace operators see remediation guidance from any normal command (not just `spec-kitty sync ...`) — measured by the renderer matrix test.
3. The "no Teamspace leakage in hosted-off mode" guarantee is preserved — measured by the unmodified Wave 1 suppression-matrix test passing.
4. The Wave 1 `--json` byte-identity guarantee is preserved — measured by the hosted-on + `--json` row of the new auth matrix asserting stdout JSON is untouched and stderr is empty.

## Key Entities

- **`AuthStatus`** (StrEnum, extended): records the verdict.
- **Auth probe** (`specify_cli.readiness.auth.probe_auth_status`): pure-function mapping `(repo_root, current_session) -> AuthStatus`.
- **Renderer** (`specify_cli.readiness.render.render_auth_guidance`): pure side-effecting function `(status, teamspace, command_name, output_policy) -> None`.
- **Coordinator** (existing `_evaluate_uncached`): orchestration — calls probe, calls renderer when appropriate, stores result.

## Assumptions

1. The existing `_auth_recovery.detect_logged_out_with_connected_teamspace()` is correct and stable. We reuse it verbatim.
2. The existing `_auth_recovery.emit_structured_stderr()` is the canonical single-line renderer for the CI case; we reuse it.
3. The Wave 1 coordinator's `_invoke_nag` ordering remains: nag fires unconditionally on both paths; this mission does not reorder. The renderer is invoked **after** the nag so any nag text reaches stderr before any auth guidance.
4. `TokenManager.is_authenticated` is the source of truth for "authenticated"; consistent with `_auth_recovery.detect_logged_out_with_connected_teamspace`'s first resolution step.

## Out of Scope

- Upgrade UX (Mission D handles snooze/opt-out/auto-upgrade).
- Tracker alignment (Mission E).
- Docs (Mission F).
- Flipping launch defaults (`SPEC_KITTY_ENABLE_SAAS_SYNC` stays opt-in).
- SaaS-side changes.
- Any refactor of `_auth_recovery.detect_logged_out_with_connected_teamspace`.
- Frontend code — none expected; if any sneaks in, the `frontend-freddy` review applies.

## References

- Wave 1 spec: `kitty-specs/cli-startup-readiness-coordinator-skeleton-01KS7JRV/spec.md`
- Wave 1 contract: `kitty-specs/cli-startup-readiness-coordinator-skeleton-01KS7JRV/contracts/readiness-api.md`
- Detection helper: `src/specify_cli/cli/commands/_auth_recovery.py`
- Coordinator: `src/specify_cli/readiness/coordinator.py`
