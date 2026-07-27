# Phase 1 Data Model — CI Test-Topology Performance

The "entities" of this mission are committed **data files** (the source of truth the guards and CI legs read), not runtime models.

## E1 — Shard registry (generalizes `tests/_arch_shard_map.py`)
One table keyed by shard *group*; `arch` and `next` are rows.

| Field | Type | Meaning |
|-------|------|---------|
| `group` | str | e.g. `"arch"`, `"next"` — the marker prefix stem |
| `roots` | tuple[str, …] | dir/file roots the group covers (whole-file for `*.py`, whole-dir for pole roots) |
| `shard_count` | int | number of legs (`arch`=3, `next`=3 initially) |
| `marker_prefix` | str | e.g. `"arch_shard"`, `"next_shard"` → markers `<prefix>_1..N` |
| `assignment` | dict[relpath → shard_idx] | committed, balanced (from measured durations) |

**Invariants**: every eligible relpath appears in exactly one `assignment`; `shard_idx ∈ 1..shard_count`; `shard_for(relpath)` returns `None` outside the group's roots (keeps the conftest hook scoped). Arch's existing assignment is preserved byte-for-byte.

## E2 — Real-port suite registry (`tests/_real_port_suites.py`)
| Field | Type | Meaning |
|-------|------|---------|
| `FIXED_RANGE_SUITES` | tuple[str, …] | test-file relpaths that bind `find_free_port_in_range` (must run `-n0`) |

Seed: `test_orphan_sweep.py`, `test_daemon_orphan_classification.py`, `test_daemon_cleanup_boundary.py`, `test_issue_1071_singleton_reconfirmation.py`. **Invariant**: none of these may be collected under an `-n auto` job (asserted by the generalized `test_serial_port_preservation.py`). Ephemeral port-0 binders are deliberately *absent*.

## E3 — Baseline node-id manifest (`tests/architectural/baselines/<job>-nodeids.txt`)
| Field | Type | Meaning |
|-------|------|---------|
| lines | sorted node-id strings | the pre-change `pytest --collect-only` set for a re-scoped/sharded job |

**Invariant**: post-change executed union == baseline set (symmetric-difference == ∅). Regenerated deliberately (with provenance) only when the intended selection legitimately changes; never silently.

## E4 — Timings artifact (mirrors `_gate_coverage._TIMINGS_BASELINE`)
| Field | Type | Meaning |
|-------|------|---------|
| `job/leg` | str | job or matrix-leg name |
| `minutes` | float | measured wall-clock |
| `run_id` | str | GitHub Actions run id (provenance) |

**Invariant**: budgets (NFR-001..008) are checked against recorded values, not asserted live; skew (NFR-006) computed from the per-leg rows.

## E5 — Sonar coverage-exclusion set (`sonar-project.properties`)
`sonar.coverage.exclusions = src/specify_cli/migration/**, **/static/**, **/__main__.py, src/specify_cli/next/**`
**Invariant**: coverage-only (files stay in issue analysis); the set contains only confirmed duct-tape/glue/non-Python assets — never core Python.

## Relationships
- E1 feeds the `conftest.py` collection hook (stamps `<prefix>_<n>` markers) **and** `_gate_coverage.same_tier_shard_counts` (E3's guarantee).
- E2 feeds `test_serial_port_preservation.py`.
- E4 is produced by IC-07 from the real post-change run; E3 gates every selection-changing WP.
