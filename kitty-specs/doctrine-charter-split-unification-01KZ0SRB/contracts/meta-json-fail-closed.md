# Contract: meta.json Fail-Closed Authority

**Owning FR:** FR-007
**Landed by:** WP07, WP08, WP09
**Tracker:** #3140

## The contract

A corrupt or non-dict `meta.json` **always fails closed** — a typed
`MissionMetaReadError` (a `RuntimeError` subclass) or `None`, **never** a raw
`ValueError` — through exactly **one** public reader:
`specify_cli.core.paths.load_meta_fail_closed`.

- The reader promotes the pre-existing `_load_meta_fail_closed` in-place — one
  home, no competing second authority. Its `load_meta` import stays
  function-local to avoid re-forming the `core.paths ↔ mission_metadata`
  import cycle.
- Two distinct `load_meta` signatures exist in the tree
  (`mission_metadata.py:275` feature_dir vs `task_utils/support.py:599`
  meta_path) — every routed call site is disambiguated against the correct one.
- Deliberately-silent callers (`load_meta_or_empty`, `on_malformed="none"`)
  are preserved untouched; only raise-default/unwrapped and divergent-wrapper
  callers route through the authority.

## Non-vacuous durability guard

`tests/specify_cli/test_meta_fail_closed_full_census_contract.py` (WP09)
independently AST-discovers every `load_meta(`-shaped call site in the tree
(resolving import aliases, not a text grep) and cross-references it against a
frozen, reasoned ledger of accounted-for sites. It fails if a new,
unaccounted site appears, or if any accounted site regresses to a raw
`ValueError`. This closed a real gap the original WP07 grep-count census
missed (an aliased `load_meta as _x` import invisible to text grep).

## Evidence

- `notes/meta-load-census.md` — the classified, grep-count-reconciled caller
  census (WP07)
- `tests/specify_cli/core/test_load_meta_fail_closed_authority.py` (WP07)
- `tests/specify_cli/test_meta_fail_closed_batch_a.py` (WP08)
- `tests/specify_cli/test_meta_fail_closed_full_census_contract.py` (WP09)
- `tests/unit/status/test_mission_status_aggregate.py::TestLoadCoordUnavailableFailsClosed`
  (the two pre-existing reds this contract turns green)
