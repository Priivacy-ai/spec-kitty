# Contract — Coverage/xunit artefact naming (E2)

Load-bearing so glob aggregators + Sonar resolve every shard's output. Preserve verbatim (C-005).

## Producer (each test shard)
- Coverage: `out/reports/coverage/coverage-<tier>-<module>.xml` via `pytest --cov=<module> --cov-report=xml:...`
  — **dotted** `--cov=<module>` form (never path form); `[tool.coverage.run] relative_files = true`.
- xunit: `out/reports/xunit-reports/xunit-result-<shard>-<run_id>.xml`.
- Upload: `actions/upload-artifact` `name: <job>-reports`, `path: out/reports/`, `if: always()`.

## Invariants
1. Coverage basename `coverage-*.xml` **unique per shard** (dedup is by basename — a collision silently drops a shard's data).
2. Artifact name ends `-reports` (consumers glob `pattern: '*-reports'`).
3. Cobertura XML with ≤1 `<source>` (dotted `--cov` guarantees this; guarded by the coverage-root-collision test).

## Consumers
- `diff-cover` (PR gate): download `*-reports`, glob `coverage-*.xml`, `--fail-under=90` on changed critical-path lines.
- `sonar.yml` (nightly): download `*-reports` (+ previous-run fallback + cross-workflow by head-SHA), dedup by basename, comma-join to `sonar.python.coverage.reportPaths`. **No single merged `coverage.xml`** — Sonar merges server-side.

## Stale-artefact fallback (spec edge case)
- A partial re-trigger leaving stale coverage → the aggregator/Sonar falls back to the most-recent successful run's `*-reports` for shards that did not re-run. (Needs a WP home — flagged for tasks.)
