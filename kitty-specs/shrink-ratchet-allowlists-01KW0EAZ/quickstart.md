# Quickstart / Verification: Shrink Architectural Ratchet Allowlists

> **⚠️ Refresh reconciliation (2026-06-29):** PR #2159 was refreshed onto current `origin/main`, where
> `harden-dead-symbol-gate` had landed and OVERTOOK FR-001 (`category_a`), FR-002 (`category_b`
> `charter_*_app`), and FR-006 (the `_extract_all_literal` parser fix). **Delivered scope is now
> FR-003 + FR-004 + an accuracy sync (FR-005).** The adapter deletion orphaned
> `core.version_checker::MismatchType`, which was **DEMOTED out of `version_checker.__all__` — NOT
> grandfathered**. Steps below describe only the delivered work; there is no parser fix or
> `write_pipeline.__all__` trim in this PR.

No API contracts (no `contracts/` dir) — internal architectural-debt burn-down. Run everything via
`uv run` (the installed `spec-kitty`/tooling may lag local `main`).

## Preconditions
- On the refreshed PR branch for #2159 (recreated on current `origin/main`).
- Per DIR-003, best-effort assign issue #2049 to the HiC before implementing.
- Confirm the live values on the refreshed tree: `legacy_contract_allowlist` 152, `pure_shim_files` 3,
  `category_5_wp_in_flight_adapters` 3, `category_a_slice_f_deferred` live 10 (recorded stale 12),
  `category_b_grandfathered_legacy` live 273 (recorded stale 286), `category_4_backcompat_shims` 8 (do
  NOT touch category_4).

## The change (per FR)
1. **FR-003** — remove the dangling `kitty-specs/033-…/contracts/event-envelope.md` from
   `_LEGACY_CONTRACT_ALLOWLIST` (`tests/contract/test_example_round_trip.py`); set `_baselines.yaml`
   `legacy_contract_allowlist: 152 → 151`.
2. **FR-004** — delete the whole `src/specify_cli/compat/_adapters/` package (`detector.py`, `gate.py`,
   `version_checker.py`, and the now-empty `__init__.py`); empty `_CATEGORY_5_WP_IN_FLIGHT_ADAPTERS`
   (`test_no_dead_modules.py`); `_ADAPTER_FILES` (`test_compat_shims.py`) self-empties via glob; remove
   the 9 `specify_cli.compat._adapters.*::*` symbols from `_CATEGORY_B_GRANDFATHERED_LEGACY`
   (`test_no_dead_symbols.py`); set `pure_shim_files: 0` and `category_5_wp_in_flight_adapters: 0`.
3. **FR-004 (orphan)** — demote `MismatchType` out of `src/specify_cli/core/version_checker.py`'s
   `__all__` (the deleted adapter was its only cross-file importer); do NOT grandfather it into any
   allowlist. The `Literal` alias stays defined as an internal annotation.
4. **FR-005 accuracy sync** — record the true live sizes of the two UNENFORCED informational baselines:
   `category_a_slice_f_deferred: 12 → 10` and `category_b_grandfathered_legacy: 286 → 264`
   (273 live on main − 9 dead adapter symbols). No `+1` (MismatchType demoted, not added).
5. **FR-005 corrections** — note that `legacy_contract_allowlist` lives in `tests/contract/` and that the
   parser fix (FR-006) landed on main via `harden-dead-symbol-gate`.
6. Every `_baselines.yaml` edit gets a `# justification:` comment naming #2049 (C-002).

## Verification commands
```bash
# 1. Adapter package gone; no functional importers:
test ! -d src/specify_cli/compat/_adapters && echo "adapters package deleted OK"
grep -rn "compat._adapters" src/ tests/ | grep -i import   # expect: empty

# 2. MismatchType demoted (not exported, not grandfathered):
grep -n "MismatchType" src/specify_cli/core/version_checker.py   # defined, but absent from __all__
grep -rn "MismatchType" tests/architectural/test_no_dead_symbols.py   # expect: no allowlist entry

# 3. The gates (the C-001 / NFR-004 proof):
PWHEADLESS=1 uv run pytest tests/architectural/test_ratchet_baselines.py \
                    tests/architectural/test_no_dead_modules.py \
                    tests/architectural/test_no_dead_symbols.py \
                    tests/architectural/test_compat_shims.py -q

# 4. Contract round-trip (legacy_contract):
PWHEADLESS=1 uv run pytest tests/contract/test_example_round_trip.py -q

# 5. Full suites + lint/type:
PWHEADLESS=1 uv run pytest tests/architectural/ tests/contract/ -q
uv run ruff check .
uv run mypy src/specify_cli/core/version_checker.py
```

## Pass criteria (→ Success Criteria)
- `_baselines.yaml`: enforced — `legacy_contract_allowlist: 151`, `pure_shim_files: 0`,
  `category_5_wp_in_flight_adapters: 0`; informational — `category_a_slice_f_deferred: 10`,
  `category_b_grandfathered_legacy: 264`; `category_4_backcompat_shims: 8` untouched. (SC-1, C-001)
- `compat/_adapters/` package deleted; no functional importers; `MismatchType` demoted out of `__all__`. (SC-2, NFR-002)
- `pytest tests/architectural/ tests/contract/` green at the reduced baselines. (SC-3, NFR-001)
- `ruff` + `mypy` clean. (SC-4, NFR-003)
- PR #2159 advances #2049 with FR-003 + FR-004 + accuracy sync; FR-001/FR-002/FR-006 noted as overtaken by main. (SC-5)

## Note on CI vs local
The local `python -m ruff` tid251 failures and the order-dependent `test_pytest_marker_convention` flake
are environment artifacts, not repo failures (confirmed in the prior mission) — verify on CI, don't chase locally.
