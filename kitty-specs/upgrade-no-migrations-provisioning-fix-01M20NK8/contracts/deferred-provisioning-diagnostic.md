# Contract — `deferred_provisioning` diagnostic (absent-authority skip)

When `spec-kitty upgrade` runs against a project with no config authority, provisioning is **deferred (not completed)** and MUST be observable via this contract.

## JSON mode
- The upgrade JSON payload carries a non-error field: `deferred_provisioning: true` (with an optional `reason: "no_config_authority"`).
- The deferral MUST NOT appear in `errors`.
- The deferral MUST NOT appear in `warnings` (the oracle asserts `warnings == []`).
- `status` is `up_to_date` (or `success` with auto-commit when other repairs apply); never `failed` solely due to the absent authority.

## Human mode
- A `Note:` line states provisioning was deferred because no config authority exists, and points at `spec-kitty init` / #4047 for full provisioning.

## Test obligations
- SC-004: a test asserts `deferred_provisioning` is emitted (JSON) and the `Note:` line is printed (human) on the config-absent path.
- FR-009: the redesigned monkeypatch test asserts the forced activation error in `errors` AND the deferral in `deferred_provisioning`, separately.
- INV-1: a test asserts the authority file is NOT created after the deferred run.
