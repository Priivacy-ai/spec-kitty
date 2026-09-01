# Research & Decisions

Evidence base: [research/post-spec-squad-findings.md](./research/post-spec-squad-findings.md) (3-lens profile-loaded squad, convergent). This file records the resulting **decisions**.

## D1 — Reject the projection cache (brief's original target)

- **Decision**: Do NOT add a step-projection cache.
- **Rationale**: `project_action_sequence` cumulative time ≈ 0ms across all three profiles; the seam is already `@functools.cache`d (`mission_step_repository.py:456`, `mission_type_repository.py:62`). A cache there moves cold-start ~0ms.
- **Alternatives considered**: persistent on-disk projection cache — rejected; reaches at most the ~70ms `_inject_projected_fields` load slice (<10%), not worth the NFR-002 staleness surface unless a cold-FS runner profile flips it (edge case, deferred).

## D2 — Durable fix Lever A: trim the `next`-path import graph

- **Decision**: Defer eager pydantic doctrine/charter/events/status model imports on the read-only `kind:"query"` path via function-level imports; anchor `next_cmd.py:21-48`; secondary lazy command registration `__init__.py:161`.
- **Rationale**: 84% of cold-start is per-process import; ~0.42s builds 336 pydantic models the query path doesn't all use. This dominates the CI-fixture number that red-blocks PRs.
- **Alternatives considered**: rewriting the model foundation (out of scope, C-004); only lazy command registration (~43ms, insufficient alone).
- **Risk**: a deferred import needed on the query path must resolve identically when first used (behavior-preserving) — guarded by NFR-004 byte-identical test.

## D3 — Durable fix Lever B: content-hash cache the charter freshness verdict

- **Decision**: Persist `CharterFreshness` to a content-keyed sidecar; on `next`, compute the cheap key and skip `compute_freshness`'s ruamel parse on a hit.
- **Key composition (C-005)**: `compute_bundle_content_hash(repo_root)` (existing, per-file mtime-agnostic BOM/CRLF-normalized sha256) **folded with the sha256 of the synthesized-DRG graph file** read by `_compute_synthesized_drg` (`computer.py:803`) — the latter is NOT in `BUNDLE_CONTENT_HASH_FILES`, so a bundle-only key would serve a stale `synthesized_drg` sub-state.
- **Rationale**: charter preflight (~0.5s ruamel of a 1588-line `charter.yaml`) dominates real-project `next` latency. Content hashing is the only safe invalidation family (mtime unreliable across git checkouts — DIR-010/011).
- **Fail-closed**: any key miss, hash error, or unreadable sidecar → recompute (never serve a possibly-stale verdict).
- **Cache location**: a repo-local cache dir (e.g. under `.kittify/`-adjacent runtime cache, gitignored) keyed by the composite hash — finalized in data-model.md; must be per-repo (freshness is `repo_root`-global, no per-mission fan-out).
- **Alternatives considered**: mtime key (rejected — DIR-010/011 footgun); doctrine-version-stamp key (rejected — misses local uncommitted edits); caching in-process only (rejected — fresh process per `next`).
- **Risk (elevated)**: serving a stale "fresh" governance verdict is worse than a stale projection → mandatory pre-merge adversarial review pass (WP-B + pre-merge squad).

## D4 — Perf benchmark shape

- **Decision**: subprocess-based `@pytest.mark.performance` benchmark — `benchmark.pedantic(lambda: subprocess.run([sys.executable,"-m","specify_cli","next",…]), rounds=N, warmup_rounds=1, iterations=1)`.
- **Rationale**: cold-start = fresh process; an in-process `benchmark.pedantic` measures a warm interpreter (structurally different, much faster). Pinned rounds avoid pytest-benchmark auto-calibration ballooning CI time on a ~1s/round subprocess. Exemplar: `tests/review/test_verdict_save_performance.py`.
- **Placement**: `tests/specify_cli/next/` → matches `performance.yml:99` next-domain leg (`paths: tests/next tests/runtime tests/specify_cli/next`), no workflow edit.
- **Baseline**: seed post-fix via `--benchmark-save` (workflow_dispatch `update_baseline`, `performance.yml:67`); `tests/performance/baselines/Linux-CPython-3.11-64bit/` has only `0001_seed.json` today.

## D5 — CI-gate retirement

- **Decision**: Remove the discrete "NFR-003 latency regression gate" step (`ci-quality.yml:4076`); KEEP the structural smoke step (`:4031`, C-001). Delete `scripts/check_nfr_003_latency.py`; drop the absolute `ci_target_median_seconds` ceiling from `nfr-003-baseline.json` (leave a historical note pointing to `performance.yml`).
- **Rationale**: the step is a single-shot wall-clock ceiling on the blocking path — the anti-pattern ADR `2026-08-22-1` eliminates; independently valuable (US2). Local `next` already at baseline (0.752s); the CI red is runner variance.
- **Alternatives considered**: keep-and-recalibrate (rejected — the ratchet this mission ends; #3783 already did the last recalibration).

## Supply-chain

No dependency add/upgrade/remove (pytest-benchmark already pinned). Section N/A; no adversarial supply-chain pass required.

## Contested findings disposition (adversarial-evidence-contract)

All three squad lenses converged; no contested finding was dropped. The one divergence (whether an on-disk step-load cache is worth it on a cold FS) is recorded as `deferred_with_rationale` (D1 alternative) — resolved by the runner profile that WP-C's benchmark produces, not blocking this plan.
