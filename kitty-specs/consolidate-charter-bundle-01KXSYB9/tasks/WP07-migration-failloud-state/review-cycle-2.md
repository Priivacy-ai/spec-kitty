---
affected_files: []
cycle_number: 2
mission_slug: consolidate-charter-bundle-01KXSYB9
reproduction_command:
reviewed_at: '2026-07-18T19:05:00Z'
reviewer_agent: claude:opus:reviewer-renata:reviewer
verdict: approved
wp_id: WP07
---

# WP07 review-cycle-2 — APPROVED

Cycle-2 remediation of the migration + fail-loud + git-class finalizer. All three
cycle-1 blockers correctly resolved and the load-bearing ordering mechanism is
sound and proven.

## Verified
1. **Version revert** — `pyproject.toml` = 3.2.6; `CHANGELOG.md` carries a #2773
   entry under the open 3.2.6 cycle. The only surviving `3.2.7` string is an
   explanatory docstring comment documenting why it isn't targeted — no stray bump.
2. **Migration target + ordering** — `TARGET_VERSION = "3.2.6"` (tied with
   `m_unify_charter_activation`); module renamed to
   `m_unify_charter_activation_finalize.py` (migration_id unchanged:
   `consolidate_charter_bundle_fold`). Empirically confirmed `pkgutil.iter_modules`
   yields sorted order and the finalize module sorts immediately after
   `m_unify_charter_activation` with nothing between. `registry.get_all()` uses a
   stable `sorted()` on Version, so the tied-3.2.6 order preserves discovery order.
   Reproduced through the real production path (`auto_discover_migrations()` →
   `get_all()`): `unify` then `fold`. `test_registry_orders_fold_after_seed_migrations`
   rebuilds from `auto_discover_migrations()`; `test_fold_relocates_seed_migration_output`
   proves the end-to-end seed→fold relocation + idempotent re-fire. Version-cap test
   passes (3.2.6 ≤ 3.2.6).
3. **Description** — 208 chars (≤ 256 cap).
4. **compat-guard fix** — `validate()` now gates on `charter.yaml` (not the retired
   `metadata.yaml`); `test_validate_json_is_strict_on_incompatible_bundle` proves the
   previously-silent v2 skip is closed.
5. **bundle-validate v2 reconciliation** — legitimate reframe of the retired
   gitignore invariant to `test_validate_v2_requires_no_gitignore_entries`; not a
   delete-to-green.
6. **Regression untag** — `test_generate_force_preserves_curated_charter_prose_2772`
   has no active `@pytest.mark.regression`; docstring records the WP03 fix. No other
   mission regression tags remain.

## Proof (foreground, lane worktree)
- `PWHEADLESS=1 uv run pytest tests/upgrade tests/charter/test_bundle_validate_cli.py
  tests/architectural/test_no_dead_modules.py tests/architectural/test_no_dead_symbols.py`
  → 630 passed.
- `ruff check` on the changed source → clean.

Known-benign (not rejected on): mypy `BaseMigration` subclass-Any + `charter_bundle.py:263`
Returning-Any (documented `follow_imports=skip` C-002 boundary artifacts); pre-review
gate `no_coverage` (lane-venv bare-`python3` quirk).

Verdict: **approved**.
