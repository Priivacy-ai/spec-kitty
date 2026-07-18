# WP07 review-cycle-1 — migration correctness + remaining fallout

The migration body, state/gitignore, versioning repoint, and the ~48-test reconciliation are largely sound and green (migration+state 81, reconciliation 157, dead-code gates green). But the whole-suite pass surfaced **3 real defects** that block aggregate-green (NFR-005). Fix these; do NOT delete-to-green.

## 1. CRITICAL — the migration would NEVER RUN (`target_version` > package version)
`m_consolidate_charter_bundle.py` sets `target_version` **greater than** `"3.2.6"` (deliberately, per its docstring, to order after the seed migrations). But `spec-kitty upgrade` **skips** any migration whose `target_version` exceeds the installed package version (`pyproject.toml` = `3.2.6`) — so the finalizer migration never executes for users, leaving them permanently on the un-migrated (four-file / config-activation) world. Proven by `tests/upgrade/test_auto_discovery.py::test_discovered_migration_targets_do_not_exceed_package_version`.
**Fix — make it runnable AND correctly ordered:**
- The migration MUST have `target_version <= package version`. Determine the correct ordering mechanism against the runner: if same-`target_version` migrations order deterministically (by migration_id / registration) such that `consolidate` runs AFTER `m_unify_charter_activation` + the rc35 seed pair, set `target_version = "3.2.6"` and pick a migration_id that sorts last. **If same-version ordering can't guarantee "after the seeds"**, then this schema-change ships with a version bump: bump `pyproject.toml` `3.2.6 → 3.2.7` + a `CHANGELOG.md` entry + `uv.lock` (release-bump completeness), and set `target_version = "3.2.7"` (runs after all 3.2.6 migrations, and now ≤ package). Verify `spec-kitty upgrade` actually applies the migration on a legacy fixture.

## 2. Migration `description` too long (275 chars > limit)
`test_auto_discovery.py::test_discovered_migrations_have_required_attributes` caps the migration `description` length. Shorten `m_consolidate_charter_bundle.description` to ≤ the enforced cap (check the test for the exact number).

## 3. 9 `tests/charter/test_bundle_validate_cli.py` failures (unowned orphan — ADD to owned_files + fix)
The `charter bundle validate` CLI + its tests still expect the pre-v2 bundle shape. Update them to manifest v2: `tracked_files = [charter.md, charter.yaml]`, `derived_files = []`, `content_hash_files = [charter.yaml]`, `schema_version 2.0.0`. Add `tests/charter/test_bundle_validate_cli.py` to your `owned_files`. (Also add `tests/architectural/test_no_dead_modules.py` + `tests/architectural/_baselines.yaml` to owned_files — the orchestrator added the `charter.extractor`/`m_consolidate_charter_bundle` allowlist entries + ratchet bumps there; own them for the record.)

## Proof required
`spec-kitty upgrade` applies the migration on a legacy fixture (not skipped); `PWHEADLESS=1 uv run pytest tests/charter tests/upgrade tests/architectural -q` green (or residual reds proven pre-existing at `main`). Run gates FOREGROUND.
