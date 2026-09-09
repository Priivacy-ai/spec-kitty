# Data Model — CI Pipeline Reinstatement (Phase 1)

The "entities" of a CI mission are its config contracts, not runtime records. Each below has a schema,
invariants, and (where relevant) a lifecycle.

## E1 — Workflow disposition (governance verdict map)
`docs/convergence/interim-ci-producer.md` row + `test_release_ci_ownership.py` set.
- **Fields:** `path` (workflow file), `disposition` ∈ {`restore`, `defer`, `never-restore`, **`introduced`**}, `rationale`.
- **Invariant:** the enforcer asserts an *exact set* per disposition; every `.github/workflows/*` file maps to exactly one; net-new files use `introduced`; retired files stay `never-restore`/absent.
- **Lifecycle:** `defer → restore` (de-defer) or `∅ → introduced` (net-new), always in the same change as the workflow edit (C-001 lockstep).

## E2 — Coverage/xunit artefact (naming contract)
- **Fields:** coverage file `coverage-<tier>-<module>.xml` (dotted `--cov=<module>`, `relative_files=true`); artifact `name: <job>-reports`, `path: out/reports/`; xunit `xunit-result-<shard>-<run_id>.xml`.
- **Invariant:** basename unique per shard (dedup is by basename); artifact name ends `-reports` (glob `*-reports`). Producer→consumer: shards → `diff-cover` (PR gate) + `sonar.yml` (nightly).

## E3 — Dead-code census (P1 machine oracle)
- **Fields:** `surface` (path/symbol), `status` ∈ {`dead`, `live`}, `evidence` (importer count / ADR / retirement gate ref), `authorizes` (drop | denominator-exclude).
- **Invariants:** (a) a base-red may be dropped ONLY if the census marks its subject `dead`; (b) a census-`dead` surface is excluded from the coverage denominator; (c) the census itself is non-vacuous — a planted dead-code-shard / retired-import is flagged, proven by a self-mutation negative test; (d) census-`dead` ≠ enforcement-allowlist target (those stay always-on).

## E4 — Allowlist-vs-shape-guard membership (P2)
- **Fields:** `test_id`, `class` ∈ {`enforcement-allowlist`, `shape-guard`, `behavioral`}.
- **Invariant:** committed, machine-checkable; a test's class cannot be silently relabeled to move it on/off the blocking gate. `enforcement-allowlist` → always-on blocking; `shape-guard` → off the blocking gate (advisory/derived-from-source).

## E5 — Filter-group → job routing model (two-authority)
- **Fields:** `group` (name), `globs[]`, `jobs[]` gated by `needs.changes.outputs.<group>`.
- **Invariants:** two hand-authorities only (dorny block, job `if:`); every derived surface asserted against them; `src/**` unmatched → `run-all`; `docs`/`corpus` are non-src (excluded from unmatched loop); a collection-completeness oracle (non-vacuous, reads real YAML) fails if any test is zero-gated.

## E6 — Run mode
- **Values:** `pr` (fail-fast, short-circuit, no perf/e2e) | `full` (nightly + manual "run full": run-all, `if: always()`, incl. perf/e2e/interpreter).
- **Invariant:** in `pr`, a successor skipped by short-circuit is NOT merge-eligible-green; in `full`, job count is 100% regardless of failures.

## E7 — Shard boundary registry
- **Fields:** `group → {roots, shard_count, marker_prefix, units}`; boundaries derived from a recorded `--durations` run (run-id captured) **on the post-scrub live basis**.
- **Invariant:** skew ≤20%; balanced on measured duration, not file count; re-derived against live `src/**` after the retirement scrub (never before).

## E8 — Warmup env artefact
- **Fields:** cache key = hash(`uv.lock` + resolved `spec_kitty_events` rev); PR→pinned rev, nightly→latest mainline.
- **Invariant:** deterministic per (lockfile, rev); one build reused by all downstream shards.
