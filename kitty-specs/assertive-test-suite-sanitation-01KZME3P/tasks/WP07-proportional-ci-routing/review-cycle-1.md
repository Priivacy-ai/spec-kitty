# WP07 review cycle 1 — changes requested

Reviewer: `reviewer-renata` (`wp07-review1`)

Commit reviewed: `b700f116c66ff9e5d1ccd045d505f425c79152b6`

## Verdict

REJECT. Selector ownership and shard-map reconciliation are correct, but the frozen-DAG timing claim, baseline/sidecar reconciliation, and #3284 replacement evidence are not yet reviewable as complete.

## Blocking findings

### 1. The reported DAG critical path omits a required route

`wp07-route-manifest.yaml` records `full-parallel` as required and places both `regression` and `full-parallel` on paths to `quality-gate`. `wp07-results.json` nevertheless computes the reported 31.7371% critical-path improvement only as `62.23 -> 42.48`, excluding the measured required whole-tree/full-parallel leg (`61.43 -> 61.37`), as well as undeclared/timeless `install` and `quality-gate` nodes.

Under the manifest's own parallel topology, the measured critical path is at least:

```
max(62.23, 61.43) -> max(42.48, 61.37)
62.23 -> 61.37 = 1.38% (MISS)
```

Under `base-workloads.yaml`'s frozen `full-collection -> {regression, quarantine, ...}` topology, the measured subset is `123.66 -> 103.85 = 16.02%` before adding install/gate overhead. These are materially different results. The current 31.7371% value is valid only for the regression/quarantine subgraph and cannot be labeled the frozen-DAG critical path.

Required correction:

- choose and document one authoritative frozen DAG;
- retain every frozen route or explicitly map it, rather than replacing the denominator with four hand-selected nodes;
- record all DAG nodes needed to compute summed compute and critical path, including the declared install/gate nodes;
- report the narrow-subgraph metric separately if useful;
- preserve the honest 0.0977% whole-tree MISS.

The four full-stage medians/maxima and SHA256 values are internally valid: all four hashes reconstruct exactly from the recorded `/usr/bin/time -p` triplets. The four narrow-route hashes do not resolve to any retained raw artifact or reproducible serialization. Retain the raw narrow command outputs (or define a canonical serialization that reproduces each hash) so review can verify them independently.

### 2. Baseline/sidecar reconciliation is incomplete and currently corrupts YAML ownership

`tests/architectural/_baselines.yaml` still carries sections for two deleted gates:

- `test_all_declarations_required`
- `test_verdict_seam_census`, including a live comment/reference to deleted `census/verdict_seam_IC01.yaml`

`tests/architectural/test_ratchet_baselines.py` still requires, grandfathers, and reads those deleted-gate sections. In addition, deleting the `test_shared_module_object_patches:` key left its 11 indented `rows:` attached to `test_verdict_seam_census`; YAML now parses that stale section as `writer_count/resolver_count/reader_count/rows`, silently joining unrelated baselines.

The two files described as "live baselines" are also unread at HEAD:

- `tests/architectural/baselines/fast-tests-core-misc-nodeids.txt`
- `tests/architectural/baselines/integration-tests-next-nodeids.txt`

Repository-wide call-site search finds `load_baseline_nodeids()` and `baseline_diff()` only at their definitions in `_gate_coverage.py`; their former live consumer was deleted. `--freeze-baselines` remains a writer, not a reader. Do not retain/regenerate dead sidecars as proof of coverage. Either restore a live, non-vacuous comparison that reads them, or remove the dead sidecars and stale helper surface after proving an equivalent route oracle survives. Remove the stale deleted-gate sections/references and repair the misplaced rows in either case.

### 3. The #3284 disposition does not preserve or retire the deleted test's actual oracle

The deleted node `test_core_misc_shards_plus_e2e_owner_cover_legacy_selection` compared the real legacy core-misc node universe with the real union of the replacement shard selections. Its replacement tests validate only the regression/quarantine literal manifests and bounded #2782 collection. Those are useful, but they are not the deleted node's core-misc coverage oracle.

The retained `test_ci_collection_completeness.py` is the documented sole route oracle and may be an acceptable survivor, but the WP07 disposition does not name it, compare its modeled boundary with the deleted real-collection boundary, or provide a fault showing it catches the same shard-drop defect. Correct the disposition/evidence and either:

- prove the retained oracle plus a bounded fidelity anchor dominates the deleted test's unique boundary; or
- add an efficient static/bounded equivalent in an already-owned test file.

Do not claim that the regression/quarantine checks replace the core-misc union check.

## Independently verified passing evidence

- Exact workflow roles: #2782 is the sole `regression` marker owner and remains in blocking `quality-gate`; quarantine has an explicit empty Tier-3 manifest and is not blocking.
- Map reconciliation: exactly 58 `_arch_shard_map.py` entries and 3 `_next_shard_map.py` entries removed; all 61 removed paths are absent; remaining assignments have zero missing paths and zero duplicates; `test_gate_read_literal_ban.py` remains assigned.
- Focused route/policy gates: `42 passed in 27.68s`.
- Full architecture gate: `748 passed, 2 xfailed in 530.30s`.
- WP07 disposition auditor: pass.
- Ruff on changed Python paths: pass.
- `git diff --check`: pass.
- `actionlint`: 65 diagnostics on both implementation parent and HEAD; no new diagnostic count.
- Whole-stage timing arithmetic: medians, maxima, 17.3263% scanner, 2.6157% deletion, 19.4889% combined, and 0.0977% routing MISS recompute exactly.
- Narrow-subgraph arithmetic: 65.8109% summed compute and 31.7371% regression/quarantine-only path recompute exactly, but are not the full frozen-DAG metrics.

## Anti-pattern checklist

1. Dead code: **FAIL** — retained baseline reader helpers/sidecars have no live consumer.
2. Synthetic-fixture test: **FAIL** — the asserted #3284 replacement exercises a different route oracle from the deleted test; causal equivalence is not established.
3. Silent empty return: **N/A** — no new production error path.

## Cycle-2 acceptance target

Keep the correct selector/map/workflow work unchanged. Repair the evidence and stale-reader surfaces above, recompute the authoritative DAG metrics without denominator loss, run the focused route gates and full architecture gate, then resubmit. This is cycle 1 of the user-mandated maximum 3 review cycles.
