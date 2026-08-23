---
work_package_id: WP01
title: Canonical local auth classification
dependencies: []
requirement_refs:
- FR-002
- FR-003
planning_base_branch: fix/setup-plan-auth-diagnostics-nonfatal
merge_target_branch: fix/setup-plan-auth-diagnostics-nonfatal
branch_strategy: Planning artifacts for this mission were generated on fix/setup-plan-auth-diagnostics-nonfatal. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/setup-plan-auth-diagnostics-nonfatal unless the human explicitly redirects the landing branch.
created_at: '2026-08-23T16:23:38Z'
subtasks:
- T001
- T002
- T003
- T004
phase: Phase 1 - Auth authority
history:
- at: '2026-08-23T16:23:38Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
authoritative_surface: src/specify_cli/readiness/
create_intent: []
execution_mode: code_change
owned_files:
- src/specify_cli/readiness/auth.py
- tests/readiness/test_auth_probe.py
- tests/sync/test_credential_scope_signal.py
tags: []
task_type: implement
tracker_refs:
- https://github.com/Priivacy-ai/spec-kitty/issues/3621
---

# Work Package Prompt: WP01 — Canonical local auth classification

## Objective

Make the existing readiness auth probe the single local authentication authority used by the later setup-plan orchestration. It must distinguish authenticated, conclusively logged out, and unknown without consulting queue scope or the network.

This package also removes obsolete tests that describe `read_queue_scope_from_credentials()` as a setup-plan authentication gate. The queue parser and physical-store invariance tests remain because queue scope is still valid routing metadata.

## Success Criteria

- `probe_auth_status()` returns `AUTHENTICATED` when `TokenManager.is_authenticated` is true.
- A refresh-capable session remains authenticated even if its short-lived access token is expired; do not add access-token-expiry logic here.
- A false auth result plus a connected Teamspace returns `LOGGED_OUT_IN_TEAMSPACE` and the normalized handle.
- A false auth result without a connected Teamspace returns `NOT_IN_TEAMSPACE`.
- Failure to import/acquire/evaluate the token manager returns `UNKNOWN`, never either logged-out state.
- Detector failure returns `UNKNOWN` as it does today.
- No auth probe reads queue scope or performs network I/O.
- Credential-scope tests continue to prove parsing and physical-store invariance without claiming that a scope means authenticated.

## Context

Read these mission artifacts before editing:

- `kitty-specs/setup-plan-auth-diagnostics-nonfatal-01M0QEAD/spec.md` — FR-002, FR-003, C-004, C-005.
- `kitty-specs/setup-plan-auth-diagnostics-nonfatal-01M0QEAD/research.md` — Decision 1.
- `kitty-specs/setup-plan-auth-diagnostics-nonfatal-01M0QEAD/data-model.md` — Authentication Classification.
- `kitty-specs/setup-plan-auth-diagnostics-nonfatal-01M0QEAD/contracts/setup-plan-result-envelope.md` — warning-code mapping consumed by WP02.

Current code facts:

- `src/specify_cli/readiness/auth.py` already returns `AuthStatus` and is documented as local-only/no-raise.
- Its nested `is_authenticated` exception handler currently assigns `False`, then consults the Teamspace detector. That can misclassify an indeterminate session-store failure as logged out.
- `TokenManager.is_authenticated` is the supported usable-session authority and already treats refresh-capable sessions correctly.
- `tests/sync/test_credential_scope_signal.py` was created for an older fatal setup-plan gate. Its parsing and store-invariance coverage remains useful; its gate expectations are superseded.

## Branch Strategy

- Planning base: `fix/setup-plan-auth-diagnostics-nonfatal`.
- Final merge target: `fix/setup-plan-auth-diagnostics-nonfatal`.
- Run implementation through `spec-kitty agent action implement WP01 --agent <name>`.
- Spec Kitty allocates the execution worktree from the lane recorded in `lanes.json`; do not create or select a worktree manually.
- Commit only files listed in `owned_files`.

## Explicit Non-Goals

- Do not change authentication storage formats or browser-mediated OAuth.
- Do not add access-token expiry warnings or forced refresh behavior.
- Do not change `AuthStatus` vocabulary or readiness rendering policy.
- Do not change queue-scope parsing semantics, queue database selection, or migrations.
- Do not add a hosted request to confirm local authentication state.
- Do not edit setup-plan production behavior; WP02 owns that adapter.
- Do not “fix” unrelated readiness or sync failures outside the three owned files.

## Subtasks and Detailed Guidance

### T001 — Write rejecting auth-probe contract cases

Modify `tests/readiness/test_auth_probe.py` before changing production behavior.

Required cases:

1. Change `test_probe_unknown_on_token_manager_is_authenticated_failure` to expect `AuthStatus.UNKNOWN` and no handle. Make the detector fail loudly if consulted, proving evaluation failure short-circuits as unknown.
2. Preserve explicit cases for `LOGGED_OUT_IN_TEAMSPACE` and `NOT_IN_TEAMSPACE`; unknown must not replace conclusive false results.
3. Add or tighten an authenticated case that represents a refresh-capable stored session through `is_authenticated=True`. The setup-plan mission does not need to inspect access-token expiry separately.
4. Add a queue-independence guard. Patch queue-scope readers to raise if called, then prove `probe_auth_status()` still returns the token-manager-derived verdict.
5. Preserve import/acquisition and detector-failure unknown cases.

Rejecting-first evidence:

- Run the updated `is_authenticated` exception case before editing `auth.py`.
- Record that it fails because current code returns `NOT_IN_TEAMSPACE` or consults the detector.
- Do not weaken the assertion or hide it behind a permissive fallback.

Keep fixtures local and deterministic. Do not write real credentials, call OAuth, or reach a SaaS host.

### T002 — Correct indeterminate token-manager classification

Modify only `src/specify_cli/readiness/auth.py`.

Implementation requirements:

1. Preserve the lazy import and no-raise outer boundary.
2. If importing `get_token_manager`, acquiring the manager, or evaluating `tm.is_authenticated` raises, immediately return `(AuthStatus.UNKNOWN, None)`.
3. Only consult `detect_logged_out_with_connected_teamspace()` after `is_authenticated` was evaluated successfully and returned false.
4. Preserve handle trimming and the distinction between `LOGGED_OUT_IN_TEAMSPACE` and `NOT_IN_TEAMSPACE`.
5. Update the module docstring/resolution order if needed so it explicitly states that auth-authority evaluation failure is unknown.
6. Do not import `specify_cli.sync.queue`, read credentials/scope files directly, inspect access-token expiry, or perform network I/O.
7. Do not change `AuthStatus` members in `coordinator.py`; the existing enum is sufficient and that file is outside this WP's ownership.

The intended control flow is:

```text
token manager unavailable/evaluation error -> UNKNOWN
is_authenticated true                     -> AUTHENTICATED
is_authenticated false + team handle       -> LOGGED_OUT_IN_TEAMSPACE
is_authenticated false + no handle         -> NOT_IN_TEAMSPACE
detector error                              -> UNKNOWN
```

### T003 — Reframe credential-scope regressions as routing-only

Modify `tests/sync/test_credential_scope_signal.py` without changing queue production code.

Required changes:

1. Rewrite the module documentation so queue scope is described exclusively as routing/store-selection metadata.
2. Remove or replace tests that call `_enforce_saas_sync_auth_refusal` and expect scope-present pass, no-scope exit 2, or gate-specific behavior.
3. Preserve the supported TOML and explicit-JSON parser cases, absent/garbage defensive behavior, physical-store invariance, and read-only preflight store-selection checks.
4. Keep the environment/home isolation fixture; it protects the operator's real Spec Kitty runtime data.
5. Ensure no retained assertion says credentials or scope prove a supported usable session.
6. Do not change parser behavior or physical queue paths. C-004 expressly excludes queue/store migration or routing changes.

If a queue-scope test is valuable but its name says “auth signal,” rename it to the routing concept it actually proves. Avoid broad mechanical renames outside this owned file.

### T004 — Run focused auth and routing gates

Run from the WP execution workspace:

```bash
uv run pytest -q tests/readiness/test_auth_probe.py tests/sync/test_credential_scope_signal.py
uv run pytest -q tests/readiness tests/saas/test_readiness_unit.py tests/saas/test_readiness_integration.py
uv run ruff check \
  src/specify_cli/readiness/auth.py \
  tests/readiness/test_auth_probe.py \
  tests/sync/test_credential_scope_signal.py
```

Also run the repository's applicable typing check for `src/specify_cli/readiness/auth.py` if the project command exposes one. Do not expand the WP to fix unrelated baseline failures; report them with exact command/output and prove they pre-existed when possible.

## Test Strategy

Testing is mandatory because the specification and charter require ATDD-first behavior.

- Unit boundary: `tests/readiness/test_auth_probe.py` pins classification and no-raise behavior.
- Routing boundary: `tests/sync/test_credential_scope_signal.py` ensures this mission does not damage scope parsing or physical-store selection.
- Compatibility boundary: readiness coordinator and SaaS readiness suites must remain green because they consume the same probe/enum.
- No test may depend on ambient login state, a real home directory, a network request, or a running daemon.

## Definition of Done

- [ ] T001's changed unknown case was observed failing before production modification.
- [ ] All auth classifications match the data model.
- [ ] Token-manager evaluation failure cannot fall through to logged-out detection.
- [ ] Queue readers are not part of auth classification.
- [ ] Refresh-capable authenticated behavior is preserved.
- [ ] Obsolete fatal setup-plan gate tests are removed from the credential routing suite.
- [ ] Parser and physical-store invariance tests remain green.
- [ ] Focused pytest and Ruff gates pass.
- [ ] Only `owned_files` were modified.

## Risks and Mitigations

- **Risk: unknown becomes a catch-all for a genuine false result.** Mitigation: preserve separate false-result tests with and without a Teamspace handle.
- **Risk: tests merely mock the desired enum.** Mitigation: exercise the real `probe_auth_status()` control flow and fail if the wrong downstream detector is consulted.
- **Risk: removing old gate tests deletes queue safety coverage.** Mitigation: retain parsing, inert-store, and read-only preflight cases explicitly.
- **Risk: token-expiry scope creep.** Mitigation: rely on `TokenManager.is_authenticated`; do not add new expiry messages or state.
- **Risk: ambient operator credentials leak into tests.** Mitigation: keep complete environment/path isolation and no-network behavior.

## Reviewer Guidance

Review this WP independently as the canonical authority seam:

1. Inspect the diff for any queue import or network call in `readiness/auth.py`; either is blocking.
2. Confirm every exception around token-manager acquisition/evaluation becomes `UNKNOWN`.
3. Confirm a successfully evaluated false still reaches the existing Teamspace detector.
4. Confirm `tests/sync/test_credential_scope_signal.py` still protects routing and store invariance rather than being gutted.
5. Verify no production queue/auth storage format changed.
6. Run the focused commands from T004.

## Activity Log

- 2026-08-23T16:23:38Z — system — Prompt created via `/spec-kitty.tasks`.
