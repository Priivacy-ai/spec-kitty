# Data Model: Shrink Architectural Ratchet Allowlists

**No domain data entities.** This is an architectural-debt burn-down mission. The only structured state
touched is the ratchet ledger and the gate allowlists, recorded here for precision.

## Ledger deltas (`tests/architectural/_baselines.yaml`)

| Key | Before | After | Driver |
|-----|--------|-------|--------|
| `category_a_slice_f_deferred` | 12 (declared; live 11) | **9** | FR-001 (−2 entries + drift fix) |
| `category_b_grandfathered_legacy` | 286 | **284** | FR-002 (−2 entries) |
| `legacy_contract_allowlist` | 152 | **151** | FR-003 (−1 dangling) |
| `pure_shim_files` | 3 | **0** | FR-004 (−3 files) |
| `category_5_wp_in_flight_adapters` | 3 | **0** | FR-004 (same 3 files, paired) |
| `category_4_backcompat_shims` | 9 | 9 (UNCHANGED) | OUT OF SCOPE — #2048/PR #2152 (C-005) |

**Invariant (C-001 / NFR-004):** each `After` value MUST equal the live frozenset/file-list size after
the corresponding entries are removed. `test_ratchet_baselines.py` enforces equality and forbids growth.

## Allowlist entry removals

| Allowlist (file) | Entry removed | FR |
|------------------|---------------|----|
| `category_a_slice_f_deferred` (`test_no_dead_symbols.py`) | `charter.synthesizer.write_pipeline::StagedArtifact`, `::promote` | FR-001 |
| `category_b_grandfathered_legacy` (`test_no_dead_symbols.py`) | `…charter.activate::charter_activate_app`, `…charter.deactivate::charter_deactivate_app` | FR-002 |
| `legacy_contract_allowlist` (`tests/contract/test_example_round_trip.py`) | `kitty-specs/033-github-observability-event-metadata/contracts/event-envelope.md` | FR-003 |
| `_ADAPTER_FILES` (`test_compat_shims.py`) + `category_5` (`test_no_dead_modules.py`) + adapter symbols (`test_no_dead_symbols.py`) | the 3 `compat/_adapters/*` files/symbols | FR-004 |

## Symbol-contract change (FR-006, the only `src/` edit besides deletions)

`src/charter/synthesizer/write_pipeline.py` `__all__`:

| Symbol | `from`-import caller in `src/`? | Action |
|--------|--------------------------------|--------|
| `stage_and_validate` | yes (`_synthesis.py:272`) | **keep** in `__all__` |
| `promote` | no (module-style only) | **demote** (remove from `__all__`) |
| `compute_written_artifacts` | no | **demote** |
| `StagedArtifact` | no | **demote** |

Result: `__all__ = ["stage_and_validate"]` (verify no star-import + re-grep each demoted symbol first, D-02).
This satisfies the un-blinded dead-symbol gate without re-adding allowlist entries.

## Parser fix (FR-006)

`_extract_all_literal` (`test_no_dead_symbols.py`, ~line 910): in the `ast.AnnAssign` branch, `continue`
when the target is not `__all__` instead of falling through to the `value is None → return frozenset()`
early-return at ~line 938. Pure logic fix; add a focused unit test exercising a module whose first
top-level node is a non-`__all__` `AnnAssign` followed by a real `__all__`.
