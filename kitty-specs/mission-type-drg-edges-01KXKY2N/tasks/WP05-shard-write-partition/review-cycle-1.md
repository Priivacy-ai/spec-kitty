# WP05 Review — Cycle 1 — CHANGES REQUESTED

**Reviewer:** reviewer-renata (claude:opus)
**Verdict:** REQUEST CHANGES — 2 blocking findings.

The **core WP05 implementation is excellent and behaviour-preserving** (verified live:
280 nodes / 757 edges / 10 orphans, `assert_valid` clean, DD-8 totality proven, atomic
delete correct, sibling edits intent-preserving). Both blockers below are narrow and
cheap to fix; neither requires reworking the partition/flip design. See "Verified good"
at the end so the re-implement does not churn the parts that already pass.

---

## BLOCKER 1 — The `charter.drg` dead-symbol mission-fix (commit `80e5974cb`) is INCORRECT: it broke the facade-contract gate

The orchestrator mission-fix removed `load_graph` from `charter.drg.__all__` + its import
to satisfy `test_no_dead_symbols`. But `load_graph` is a **contract-required facade
re-export**, so removing it introduced **2 new architectural-gate failures** that were
green on the mission base and at the implementer's Ready point:

```
FAILED tests/architectural/test_charter_facades_reexport_doctrine.py::test_facade_reexports_doctrine_symbol_by_identity[charter.drg.load_graph]
    AttributeError: module 'charter.drg' has no attribute 'load_graph'
FAILED tests/architectural/test_charter_facades_reexport_doctrine.py::test_facade_all_lists_every_reexport[charter.drg]
    AssertionError: charter.drg.__all__ is missing contract symbols: ['load_graph'].
                    Add them to __all__ or update the contract table.
```

**These are NOT pre-existing base-red and NOT a flake** (the WP Ready-log claim of "2
pre-existing base-red" is inaccurate for these two):
- `git show kitty/mission-mission-type-drg-edges-01KXKY2N:src/charter/drg.py` shows the
  base **imports and `__all__`-exports `load_graph`** (line 55 + line 93) → both facade
  tests were green on base.
- The implementer marked Ready at 11:16Z on commit `d5bbc1d1a` (before the mission-fix);
  the mission-fix `80e5974cb` landed ~11:27Z. The facade reds appear **only after** the
  mission-fix. The "2 residual reds" the implementer actually saw were
  `test_no_dead_symbols` + `test_golden_count_ban` — the very gates the mission-fix then
  addressed.

**Root cause — a genuine two-gate tension the fix resolved the wrong way:**
- `test_no_dead_symbols` flags any `__all__` name with no `src/` importer. WP03 rerouted
  src consumers `load_graph` → `load_built_in_graph`, orphaning `load_graph`'s internal use.
- `test_charter_facades_reexport_doctrine` (mission `charter-mediated-doctrine-selection-01KRTZCA`,
  contract `kitty-specs/charter-mediated-doctrine-selection-01KRTZCA/contracts/charter-facade-modules.md`
  Symbol tables) **requires** `charter/drg.py` to re-export `load_graph` by identity for
  external/direct importers — exactly like the documented `MissionStep` precedent in the
  same facade table ("the symbol remains an explicit PEP 484 re-export for direct
  importers" even with no src consumer).

`test_no_dead_symbols` documents three resolutions (its own header, ~lines 96–102): remove
from `__all__`, delete the symbol, **or add it to the re-export-shim exemption / hand
allowlist** (`_is_reexport_shim_symbol`). The mission-fix chose "remove from `__all__`",
which violates the facade contract. The correct resolution is the **allowlist** branch.

**Required fix (satisfies BOTH gates):**
1. Restore `load_graph` to `charter/drg.py` imports and `__all__` (it is contract-required).
2. Add `load_graph` to the `test_no_dead_symbols` re-export-shim exemption / hand-allowlist,
   with a one-line rationale citing `charter-facade-modules.md` (contract-required facade
   re-export with no internal caller — same status as `MissionStep`).
3. Re-run both `test_charter_facades_reexport_doctrine.py` and
   `test_no_dead_symbols.py` and confirm green together.

**Note:** removing `built_in_graph_source` from `charter.drg.__all__` is **fine** — it is a
new WP03 symbol and is NOT in the facade contract table. Only the `load_graph` removal is
the violation. (The `test_golden_count_ban` half of the mission-fix is correct and green —
leave it.)

---

## BLOCKER 2 — `_partition_by_kind` has no focused test; FR-007's edge-by-source-kind clause and DD-11 ordering are untested

The WP DoD/complexity watch-item explicitly required extracting the partition step as a
pure helper **"with its own focused test, rather than inlining."** The helper was extracted
(good — complexity is well-managed), but **no test references `_partition_by_kind`**
(`grep -rn _partition_by_kind tests/` → none), and WP05 added **no new test functions** to
`test_extractor.py` (only repointed 3 existing ones to fragment form).

This leaves two FR-007 clauses invisible to the current suite:
- **"edges whose source node is that kind"** — because the loader merges every fragment's
  edges into one set on reload, a regression that routes edges to the *wrong* kind fragment
  (e.g. by target-kind) would still reconstitute the identical 757-edge graph and **pass
  every current WP05 test** (`test_sharded_layout`, `test_idempotent`, freshness twins,
  `assert_valid`). I verified source-kind routing is correct *manually*, but it is not
  pinned by any test.
- **DD-11 canonical intra-fragment ordering** (nodes by URN; edges by
  `(source, target, relation)`) — `test_idempotent`/freshness only prove *determinism*
  (byte-identity across runs), not that the order matches the DD-11 spec. A deterministic-
  but-wrong reorder passes today.

Per the charter Quality standing order ("every new branch/helper needs tests in the same
PR; extracting helpers without adding focused tests simply moves the failure").

**Required fix:** add a focused unit test for `_partition_by_kind(graph)` asserting, on a
small hand-built `DRGGraph` (include a target-only kind and multi-kind edges):
1. one fragment per populated kind (totality), including the target-only kind (empty edges);
2. each fragment's nodes are all of that fragment's kind (homogeneity);
3. each edge is placed in its **source** node's kind fragment (the currently-invisible clause);
4. DD-11 order: fragment nodes sorted by URN, edges sorted by `(source, target, relation)`;
5. (optional) disjoint union of fragments reconstructs the input node/edge sets exactly.

---

## Anti-pattern checklist

1. Dead code — **PASS** (all new helpers `_partition_by_kind`/`_write_graph_yaml`/
   `_dump_graph_document`/`_read_graph_source` have live callers).
2. Synthetic-fixture test — **PASS** (`test_context.py` mock repoints to the real
   `load_validated_graph` seam that `context.py:922` calls — load-bearing, not synthetic).
3. Silent empty return — **PASS** (no new silent empty/None returns).
4. FR coverage — **PARTIAL / see Blocker 2** (FR-007's edge-by-source-kind + DD-11 ordering
   clauses unasserted; FR-012 monolith-absent + FR-015 no-import are covered).
5. Frozen surface — **PASS**.
6. Locked decision — **PASS** (FR-015 no in-YAML import: `grep -E '^\s*import:|!include'
   src/doctrine/*.graph.yaml` → none).
7. Shared-file ownership — **PASS** (extractor.py write-step leeway is prompt-sanctioned and
   documented; the WP01 edge pass is untouched — see below).
8. Production fragility — **PASS** (no new fragile raises; write order is crash-safe:
   fragments written → stale fragments pruned → monolith unlinked last).

---

## Verified good (do NOT rework — these all pass)

- **Behaviour-preserving flip:** post-regenerate, `src/doctrine/graph.yaml` DELETED; 10
  `*.graph.yaml` fragments present; seam load → 280 nodes / 757 edges / 10 orphans (== pre-flip);
  `assert_valid` clean; `regenerate-graph --check` fresh; re-regenerate byte-identical.
- **DD-8 totality:** 10 populated node-kinds == 10 fragments (1:1); sum of fragment nodes = 280,
  edges = 757 (nothing lost/duplicated); every fragment homogeneous; every edge assigned by
  source-kind; `template.graph.yaml` = 16 nodes / 0 edges (target-only proof). Other target-only
  kinds (asset/glossary/glossary_scope/mission_step_contract) are correctly unpopulated (0 nodes),
  so correctly get no fragment.
- **DD-7 atomic delete:** `test_sharded_layout.py` asserts fragments present ∧ monolith absent;
  write path unlinks the monolith last (crash-safe ordering); green.
- **Transparent WP04-gate flip:** WP05 did NOT edit `test_doctrine_regenerate_graph.py`; it and
  `test_sharded_layout.py` pass reading fragments (10 passed).
- **Sibling edits intent-preserving:** `test_extractor.py` (3 monolith→fragment asserts,
  strengthened), `test_context.py` (mock repointed to the correct `load_validated_graph` seam),
  `test_builtin_graph_seam.py` (post-flip asserts + the transitional `seam==monolith` parity
  scaffold dropped — legitimately superseded, since post-delete `load_graph(root/graph.yaml)` is
  unrepeatable; coverage now via `test_sharded_layout` + freshness twins + WP06's equality proof).
  80 passed across the 3 files.
- **Edge pass NOT disturbed** (criterion 7): WP05's `extractor.py` hunks are confined to the
  module docstring + `generate_graph` Step 9 + the new write helpers; no `extract_*_edges` /
  mission_type edge logic touched.
- **Golden-count mission-fix** (the second half of `80e5974cb`) is correct: the two `==` edge
  counts each have a set-equality assertion above them; `test_golden_count_ban` green (10 passed).
- **Lint/gates:** ruff + mypy --strict clean on `doctrine.py` + `extractor.py`; complexity ≤ 15
  (C901 clean); zero new suppressions.
- **Flaky standalone:** `test_surface_resolution_audit` + `test_untrusted_path_containment`
  pass standalone (28 passed) — pre-existing parallel-isolation flakiness, not a regression.
- **Broad suite:** `tests/doctrine tests/doctrine/drg tests/architectural` = 2 failed / 3583
  passed. The **only** 2 fails are the facade-contract reds from Blocker 1.

Fix Blocker 1 (restore `load_graph` + allowlist it) and Blocker 2 (focused `_partition_by_kind`
test), re-run the two facade tests + `test_no_dead_symbols` + the new focused test, and this WP
is ready to approve.
