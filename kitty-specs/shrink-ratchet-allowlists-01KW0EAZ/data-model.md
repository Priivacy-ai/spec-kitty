# Data Model: Shrink Architectural Ratchet Allowlists

> **⚠️ Refresh reconciliation (2026-06-29):** PR #2159 was refreshed onto current `origin/main`, where
> `harden-dead-symbol-gate` had landed and OVERTOOK FR-001 (`category_a` entries), FR-002 (`category_b`
> `charter_*_app` entries), and FR-006 (the `_extract_all_literal` parser fix). **Delivered scope is now
> FR-003 + FR-004 + an accuracy sync (FR-005).** The adapter deletion orphaned
> `core.version_checker::MismatchType`, which was **DEMOTED out of `version_checker.__all__` — NOT
> grandfathered** (the gate scans only `__all__` names, so demotion closes the orphan with zero new
> allowlist debt). Earlier drafts that described a `write_pipeline.__all__` trim or `category_b` targets
> of 276/284/286 are superseded by this note.

**No domain data entities.** This is an architectural-debt burn-down mission. The only structured state
touched is the ratchet ledger, the gate allowlists, and one demoted `__all__` member, recorded here for
precision.

## Ledger deltas (`tests/architectural/_baselines.yaml`)

| Key | Before | After | Enforced? | Driver |
|-----|--------|-------|-----------|--------|
| `legacy_contract_allowlist` | 152 | **151** | yes (`test_ratchet_baselines.py`) | FR-003 (−1 dangling contract) |
| `pure_shim_files` | 3 | **0** | yes | FR-004 (`_ADAPTER_FILES` glob self-empties on package deletion) |
| `category_5_wp_in_flight_adapters` | 3 | **0** | yes | FR-004 (same adapters, hardcoded list emptied) |
| `category_a_slice_f_deferred` | 12 | **10** | **no — informational** | FR-005 accuracy sync (main rescued `promote` + one more; PR removes no `category_a` entry) |
| `category_b_grandfathered_legacy` | 286 | **264** | **no — informational** | FR-005 accuracy sync (live 273 on main − 9 dead adapter symbols = 264) |
| `category_4_backcompat_shims` | 8 | 8 (UNCHANGED) | n/a | OUT OF SCOPE — #2048 / PR #2152 (C-005) |

**Enforced invariant (C-001 / NFR-004):** for the three enforced keys, each `After` value MUST equal the
live frozenset/file-list size after the corresponding entries are removed; `test_ratchet_baselines.py`
enforces equality and forbids growth. The `test_no_dead_symbols:` section (`category_a_*`, `category_b_*`)
is **not** cross-checked by the ratchet test, so its values are synced to the true live size purely for
accuracy — they drifted because `harden-dead-symbol-gate` landed without re-recording them.

### `category_b` arithmetic (FR-005)

```
286   recorded (stale) before harden-dead-symbol-gate landed
273   live on main  (harden-gate rescued ~13 ::app / emit_* / is_legacy_format /
                     SparseCheckoutRemediationResult entries)
−9    this PR removes the dead specify_cli.compat._adapters.*::* symbol entries
= 264 recorded                (NO +1 — MismatchType was demoted, not added)
```

## Allowlist entry removals (delivered)

| Allowlist (file) | Entry removed | FR |
|------------------|---------------|----|
| `_LEGACY_CONTRACT_ALLOWLIST` (`tests/contract/test_example_round_trip.py`) | `kitty-specs/033-github-observability-event-metadata/contracts/event-envelope.md` | FR-003 |
| `_ADAPTER_FILES` (`test_compat_shims.py`, glob-discovered) + `_CATEGORY_5_WP_IN_FLIGHT_ADAPTERS` (`test_no_dead_modules.py`) + the 9 `specify_cli.compat._adapters.*::*` symbols in `_CATEGORY_B_GRANDFATHERED_LEGACY` (`test_no_dead_symbols.py`) | the `compat/_adapters/` package (3 shims + empty `__init__.py`) and its symbols | FR-004 |

**OVERTAKEN (not part of this PR):** the `category_a` `StagedArtifact`/`promote` removals (FR-001) and
the `category_b` `charter_activate_app`/`charter_deactivate_app` removals (FR-002) — main's
`harden-dead-symbol-gate` already cleared or rescued these. This PR does not edit those entries.

## Symbol-contract change (the only `src/` edit besides the package deletion)

`src/specify_cli/core/version_checker.py` `__all__`:

| Symbol | cross-file importer? | Action |
|--------|----------------------|--------|
| `compare_versions`, `format_version_error`, `should_check_version`, `maybe_emit_no_upgrade_notice` | yes | **keep** in `__all__` |
| `MismatchType` (`Literal` type alias) | no — sole former importer was the deleted `compat/_adapters/version_checker.py` shim | **demote** (remove from `__all__`; alias stays defined as an internal annotation) |

Demoting `MismatchType` rather than grandfathering it closes the orphan at the root: the dead-symbol gate
scans only `__all__` names, so a non-exported alias is invisible to it — zero new allowlist debt, zero
functional change, and no follow-up ticket owed.
