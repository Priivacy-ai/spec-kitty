# Contract: `spec-kitty upgrade` post-state coherence

**Traces to**: FR-002 (#705), NFR-006

## Stimulus

A user (or CI job) runs `spec-kitty upgrade --yes` in any
spec-kitty-initialized project where the CLI binary version matches the
target schema bound (currently `MIN_SUPPORTED_SCHEMA == MAX_SUPPORTED_SCHEMA == 3`).

## Required behavior

After the command exits with status `0`:

1. **`.kittify/metadata.yaml` MUST contain**:
   - `spec_kitty.version` equal to the CLI binary's version.
   - `spec_kitty.schema_version` equal to `REQUIRED_SCHEMA_VERSION` (an integer,
     currently `3`).
   - `spec_kitty.last_upgraded_at` updated to within the last 5 seconds.
   - `spec_kitty.initialized_at` UNCHANGED.
2. **`.kittify/metadata.yaml` MUST NOT contain**:
   - A `null` or empty value for `spec_kitty.schema_version`.
   - Any duplicate top-level keys.
3. **An immediately-following `spec-kitty agent mission branch-context --json`
   MUST**:
   - Exit with status `0`.
   - Print a JSON payload with `"result": "success"`.
   - **NOT** trigger the `PROJECT_MIGRATION_NEEDED` gate.

## Forbidden behavior

- The command MUST NOT print `Upgrade complete!` while leaving the project
  in a state where the next `agent` command is gated by
  `PROJECT_MIGRATION_NEEDED`.
- The command MUST NOT silently overwrite `spec_kitty.schema_version`
  during its post-migration metadata save.

## Implementation hint (informative, not normative)

Confirmed root cause: `_stamp_schema_version` (raw YAML round-trip)
followed by `metadata.save()` (dataclass-only serialization that drops
unknown keys) at `src/specify_cli/upgrade/runner.py:163–164`. Smallest-
blast-radius fix is to swap the call order so `_stamp_schema_version` runs
*after* `metadata.save()`. See [research.md R2](../research.md#r2--schema-version-clobber-root-cause-fr-002--705).

## Verifying tests

- Unit: extend
  `tests/cross_cutting/versioning/test_upgrade_version_update.py` with a
  case that runs `UpgradeRunner.upgrade()` against a fixture project and
  asserts `yaml.safe_load(metadata.yaml)['spec_kitty']['schema_version'] == 3`.
- E2E: new test
  `tests/e2e/test_upgrade_post_state.py` that drives the full CLI in a tmp
  dir: `spec-kitty init <tmp>` → `spec-kitty upgrade --yes` →
  `spec-kitty agent mission branch-context --json`. Asserts second command
  exits 0 and JSON `result == "success"`.
