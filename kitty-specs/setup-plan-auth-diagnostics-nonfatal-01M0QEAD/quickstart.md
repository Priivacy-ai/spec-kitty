# Quickstart: verify issue #3621 remediation

Run from the WP execution workspace allocated by Spec Kitty. Keep SaaS disabled for
planning/finalization commands; tests explicitly control the enable flag per case.

## Red-first evidence

Each WP must commit its failing test before production code. Capture the failure against
the WP's dependency-resolved lane base immediately before production changes, and the
passing result on the WP head. For independent WP01 and WP03 that base is
`planning_base_branch=fix/setup-plan-auth-diagnostics-nonfatal`; the original end-to-end
issue may also be demonstrated there.

## Targeted verification

```bash
uv run pytest -q \
  tests/auth/test_token_manager.py \
  tests/readiness/test_auth_probe.py

uv run pytest -q \
  tests/status/test_lifecycle_events.py \
  tests/specify_cli/cli/commands/agent/test_setup_plan_hosted.py

uv run pytest -q \
  tests/runtime/test_setup_plan_sync_evidence.py \
  tests/specify_cli/cli/commands/agent/test_mission_setup_plan_phases.py \
  tests/specify_cli/cli/commands/agent/test_setup_plan_read_surface.py \
  tests/specify_cli/cli/commands/agent/test_issue_3425_setup_plan_legacy_layout_silent_capture.py

uv run pytest -q \
  tests/architectural/test_setup_plan_hosted_effect_gate.py \
  tests/architectural/test_status_sync_boundary.py \
  tests/architectural/test_dossier_sync_boundary.py

uv run pytest -q tests/sync/test_sync_boundary_preflight.py
```

## Required production-chain cases

1. Real isolated encrypted session storage with expired access token, usable refresh
   token, and no queue scope: real setup-plan emits no auth warning.
2. Real isolated unreadable/corrupted session storage: real setup-plan emits exactly
   `SAAS_SYNC_AUTH_UNKNOWN` and still returns the local outcome.
3. Boundary preflight raises: real setup-plan returns the local outcome,
   `SAAS_SYNC_BOUNDARY_UNSAFE`, and zero hosted sink calls.
4. Hosted decision refused: local lifecycle JSONL exists while lifecycle fan-out,
   dossier, offline queue, body-upload, daemon, and dashboard spies remain zero.
5. Canonical auth assessment acquisition/evaluation raises: real setup-plan emits exactly
   `SAAS_SYNC_AUTH_UNKNOWN`, no unauthenticated warning, the complete baseline local
   payload/exit, and zero hosted effects.
6. SaaS disabled: the real command completes with fatal auth, boundary, and route spies
   untouched, no warnings, no hosted effects, and a baseline-identical local result.
7. Canonical read-only routing returns null, denied/missing identity, or raises: real
   setup-plan emits exactly `SAAS_SYNC_ROUTE_UNAVAILABLE` and refuses hosted effects.

## Compatibility matrix

Capture baseline and compare primary fields plus exit for:

- complete substantive plan;
- new pristine scaffold;
- populated insufficient plan;
- committed pristine/insufficient plan;
- non-substantive/uncommitted spec;
- missing spec;
- template configuration error;
- missing template/generic local exception;
- project/context/git resolution failure.

Run the full parameterized cross-product of every local row with usable session, logged
out, auth-assessment failure, boundary unsafe, boundary exception, and route unavailable
where repository context exists. Compare the complete baseline payload after removing
only `warnings`, plus exact exit equality. For pre-root rows, assert boundary and route
probes are not called and no structural/routing warning is fabricated.

## Quality gates

```bash
uv run ruff check \
  src/specify_cli/auth/token_manager.py \
  src/specify_cli/readiness/auth.py \
  src/specify_cli/status/lifecycle_events.py \
  src/specify_cli/cli/commands/agent/setup_plan_hosted.py \
  src/specify_cli/cli/commands/agent/setup_plan_hosted_effects.py \
  src/specify_cli/cli/commands/agent/mission_setup_plan.py

uv run mypy --strict \
  src/specify_cli/auth/token_manager.py \
  src/specify_cli/readiness/auth.py \
  src/specify_cli/status/lifecycle_events.py \
  src/specify_cli/cli/commands/agent/setup_plan_hosted.py \
  src/specify_cli/cli/commands/agent/setup_plan_hosted_effects.py \
  src/specify_cli/cli/commands/agent/mission_setup_plan.py

uv run pytest -q tests/architectural/test_no_legacy_terminology.py
```

## Release closeout

Issue #3127 is not a WP or Mission-completion dependency. At Mission acceptance, record a
terminal fixed or deferred-with-followup verdict with evidence. If it remains unresolved,
do not declare release readiness until it and the authoritative mainline CI gate permit
release; do not reinterpret its known red as an acceptable baseline.
