# Quickstart: verify the planned setup-plan behavior

Run from the repository root. These commands describe the post-implementation verification sequence; the plan phase does not implement the change.

## 1. Prove the rejecting acceptance contract first

```bash
uv run pytest -q \
  tests/runtime/test_setup_plan_sync_evidence.py \
  tests/specify_cli/cli/commands/agent/test_mission_setup_plan_phases.py
```

Before production changes, the new cases must fail because current setup-plan exits 2 before local verification.

## 2. Verify tri-state local auth

```bash
uv run pytest -q tests/readiness/test_auth_probe.py tests/sync/test_credential_scope_signal.py
```

Confirm that a refresh-capable stored session is authenticated without queue scope, both conclusive logged-out states map to `SAAS_SYNC_UNAUTHENTICATED`, and token-manager/session evaluation failure maps to `SAAS_SYNC_AUTH_UNKNOWN`.

## 3. Verify setup-plan result and side-effect separation

```bash
uv run pytest -q \
  tests/runtime/test_setup_plan_sync_evidence.py \
  tests/specify_cli/cli/commands/agent/test_mission_setup_plan_phases.py \
  tests/specify_cli/cli/commands/agent/test_setup_plan_read_surface.py
```

The matrix must prove that complete local plans exit 0 under logged-out, unknown, and structurally unsafe states; incomplete local plans retain their local behavior; JSON has one result plus ordered warnings; human output uses warning severity; unsafe hosted calls are absent; and local events, artifact work, and commit routing still execute.

## 4. Verify structural guard preservation

```bash
uv run pytest -q tests/sync tests/runtime/test_setup_plan_sync_evidence.py
```

Every existing structural detector must remain green, and hosted-sync commands outside setup-plan must retain their existing fail-closed behavior.

## 5. Run focused quality checks

```bash
uv run ruff check \
  src/specify_cli/readiness/auth.py \
  src/specify_cli/sync/preflight.py \
  src/specify_cli/cli/commands/agent/mission_setup_plan.py \
  tests/readiness/test_auth_probe.py \
  tests/runtime/test_setup_plan_sync_evidence.py \
  tests/specify_cli/cli/commands/agent/test_mission_setup_plan_phases.py
```

No network login is required; all auth and boundary states use isolated local fixtures.
