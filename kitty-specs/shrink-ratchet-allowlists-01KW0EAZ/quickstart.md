# Quickstart / Verification: Shrink Architectural Ratchet Allowlists

> **⚠️ RE-SCOPE (post-implementation):** FR-006 (the `_extract_all_literal` parser fix) and the
> `write_pipeline.__all__` trim were **deferred to #2158** — un-blinding the parser surfaced ~117
> dead symbols (a ratchet *growth*). The delivered mission does NOT touch the parser or
> `write_pipeline.py`. Actual `category_b_grandfathered_legacy` = **276** (the 9 adapter dead-symbol
> entries also lived in category_b, and the adapter deletion orphaned `MismatchType`, +1). Sections
> below that describe the parser fix / `__all__` trim / a 284 target are superseded by this note.


No API contracts (no `contracts/` dir) — internal architectural-debt burn-down. Run everything via
`uv run` (the installed `spec-kitty`/tooling may lag local `main`).

## Preconditions
- On `feat/shrink-ratchet-allowlists` (or its lane worktree).
- Per DIR-003, best-effort assign issue #2049 to the HiC before implementing.
- Re-confirm live counts (they drift): `category_a` declared 12 / live 11, `category_b` 286, `legacy_contract` 152, `pure_shim_files` 3, `category_5` 3, `category_4` 9 (do NOT touch category_4).

## The change (per FR)
1. **FR-006 first** — fix `_extract_all_literal` (`test_no_dead_symbols.py` ~L938): `continue` for non-`__all__` AnnAssign; add a focused unit test.
2. **FR-006 cascade** — in `src/charter/synthesizer/write_pipeline.py`, after verifying no star-import and re-grepping callers, trim `__all__` to `["stage_and_validate"]` (demote `promote`, `compute_written_artifacts`, `StagedArtifact`).
3. **FR-001** — remove `write_pipeline::StagedArtifact` and `::promote` from `category_a_slice_f_deferred`; set `_baselines.yaml` `category_a_slice_f_deferred: 9`.
4. **FR-002** — remove `charter.activate::charter_activate_app` and `charter.deactivate::charter_deactivate_app` from `category_b_grandfathered_legacy`; set `286 → 284`.
5. **FR-004** — delete the 3 `compat/_adapters/*` files; remove their entries from `_ADAPTER_FILES` / `category_5` / dead-symbol allowlist; set `pure_shim_files: 0` and `category_5_wp_in_flight_adapters: 0`.
6. **FR-003** — remove the dangling `033-…/event-envelope.md` from `legacy_contract_allowlist` (`tests/contract/test_example_round_trip.py`); set `152 → 151`.
7. **FR-005** — post the path/count corrections as a comment on #2049.
8. Every `_baselines.yaml` edit gets a `# justification:` comment naming #2049 (C-002).

## Verification commands
```bash
# 1. Adapter shims gone; no functional importers:
test ! -f src/specify_cli/compat/_adapters/version_checker.py && echo "adapters deleted OK"
grep -rn "compat._adapters" src/ tests/ | grep -i import   # expect: empty (only allowlist refs removed)

# 2. The gates (the C-001 / NFR-004 proof):
PWHEADLESS=1 uv run pytest tests/architectural/test_ratchet_baselines.py \
                    tests/architectural/test_no_dead_modules.py \
                    tests/architectural/test_no_dead_symbols.py \
                    tests/architectural/test_compat_shims.py -q

# 3. Contract round-trip (legacy_contract):
PWHEADLESS=1 uv run pytest tests/contract/test_example_round_trip.py -q

# 4. Full suites + lint/type:
PWHEADLESS=1 uv run pytest tests/architectural/ tests/contract/ -q
uv run ruff check .
uv run mypy src/charter/synthesizer/write_pipeline.py

# 5. The un-blinded gate now inspects write_pipeline (FR-006 proof):
#    after the fix, test_no_dead_symbols sees write_pipeline.__all__ = ["stage_and_validate"] (all live).
```

## Pass criteria (→ Success Criteria)
- `_baselines.yaml`: `category_a_slice_f_deferred: 9`, `category_b_grandfathered_legacy: 284`, `legacy_contract_allowlist: 151`, `pure_shim_files: 0`, `category_5_wp_in_flight_adapters: 0`; `category_4_backcompat_shims` untouched. (SC-1, C-001)
- 3 adapter files deleted; no functional importers. (SC-2, NFR-002)
- `pytest tests/architectural/ tests/contract/` green; the dead-symbol gate inspects `write_pipeline` public symbols. (SC-3, NFR-001)
- `ruff` + `mypy` clean. (SC-4, NFR-003)
- #2049 closed + FR-005 corrections posted. (SC-5)

## Note on CI vs local
The local `python -m ruff` tid251 failures and the order-dependent `test_pytest_marker_convention` flake
are environment artifacts, not repo failures (confirmed in the prior mission) — verify on CI, don't chase locally.
