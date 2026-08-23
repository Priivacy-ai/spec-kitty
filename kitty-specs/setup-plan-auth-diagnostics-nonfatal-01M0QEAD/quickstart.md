# Quickstart: verify issue #3621 remediation

Run from the WP execution workspace allocated by Spec Kitty. Keep SaaS disabled for
planning/finalization commands; tests explicitly control the enable flag per case.

## Red-first evidence

Each WP must commit its failing test before production code. Capture the failure against
`planning_base_branch=fix/setup-plan-auth-diagnostics-nonfatal` and the passing result on
the WP head.

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

Cross representative rows with usable session, logged out, auth-assessment failure,
boundary unsafe, and boundary exception. Only `warnings` may differ.

## Quality gates

```bash
uv run ruff check \
  src/specify_cli/auth/token_manager.py \
  src/specify_cli/readiness/auth.py \
  src/specify_cli/status/lifecycle_events.py \
  src/specify_cli/cli/commands/agent/setup_plan_hosted.py \
  src/specify_cli/cli/commands/agent/mission_setup_plan.py

uv run mypy --strict \
  src/specify_cli/auth/token_manager.py \
  src/specify_cli/readiness/auth.py \
  src/specify_cli/status/lifecycle_events.py \
  src/specify_cli/cli/commands/agent/setup_plan_hosted.py \
  src/specify_cli/cli/commands/agent/mission_setup_plan.py

uv run pytest -q tests/architectural/test_no_legacy_terminology.py
```

## Release closeout

Issue #3127 is not a WP dependency. Before Mission acceptance or release readiness,
verify it is resolved and the authoritative mainline CI gate permits release. Do not
reinterpret its known red as an acceptable baseline.
