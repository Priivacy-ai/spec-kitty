# Contracts — ci-health-charter-path-and-arch-shard-01KWRTB2

Declared **N/A by design** in [plan.md](../plan.md): this mission has no data
entities or API surfaces — it is a docs fix plus a CI-topology change. The
executable contracts ARE the mission's deliverables — the invariant tests
themselves:

| Contract | Executable surface |
|---|---|
| No stale charter path in guarded docs (FR-001/FR-002) | `tests/docs/test_current_charter_paths.py` |
| Arch-shard marker partition (total, no gaps/dupes) (FR-004/FR-005) | `tests/architectural/test_arch_shard_marker_completeness.py` |
| Arch-pole shard-union bounded (no single shard = full universe) (FR-005) | `tests/architectural/test_shard_universe_bounded.py` |
| Shard-name assertions re-pinned (FR-003) | `tests/architectural/test_ci_quality_path_filters.py` |
| Coverage-topology ownership across shards (FR-006) | `tests/release/test_coverage_topology_ownership.py` |
| CI-topology timings fixture reflects sharded shape (FR-007) | `tests/release/ci_topology_timings_postshrink.json` (narrative, not test-asserted) |
| Issue #2397 acceptance re-verification (FR-008) | `acceptance-record.md` |
| Docs-only trim still holds per shard | `tests/architectural/test_docs_scoped_arch_coverage.py` |
| De-serialized, group-less pole preserved | `tests/architectural/test_arch_pole_deserialized.py` |

See `data-model.md` for the shard-assignment table shape and `quickstart.md`
for the local reproduction commands.
