# Implementation Plan: Next-Command Latency — Durable Fix + Perf-Gate Migration

**Branch**: `perf/next-latency-durable-fix` | **Date**: 2026-08-28 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `kitty-specs/next-latency-durable-fix-01M14RM3/spec.md` (re-scoped after post-spec research squad; map in [research/post-spec-squad-findings.md](./research/post-spec-squad-findings.md))

## Summary

Make `spec-kitty next` fast again and move its latency guard off the blocking PR path onto the statistical performance pipeline. The research squad proved the brief's original target (a step-projection cache) is a dead end — the projection is ~0ms and already `@functools.cache`d. The durable fix is **two independent levers**: (A) trim the `next`-path import graph so per-process cold-start stops eagerly building the pydantic model foundation the read-only query path never uses (dominates the CI-fixture number); and (B) content-hash-cache the charter freshness verdict so `next` stops re-parsing a 1588-line `charter.yaml` on every call (dominates real-project latency). Alongside, migrate the latency signal from a blocking single-shot ceiling (`scripts/check_nfr_003_latency.py` in `clean-install-verification`) to a subprocess-based `@pytest.mark.performance` benchmark in the non-gating `performance.yml`, retaining only the structural clean-wheel smoke check.

## Technical Context

**Language/Version**: Python 3.11+ (repo baseline; CI perf runner pins CPython 3.11)
**Primary Dependencies**: typer/click (CLI), pydantic (models — the cold-start cost), ruamel.yaml (charter parse — the cost), pytest + pytest-benchmark 5.2.3 (statistical perf), existing `@functools.cache` seams
**Storage**: filesystem sidecar for the charter-freshness cache (location TBD in Phase 1 — a repo-local cache dir, content-keyed); no DB
**Testing**: pytest (`PYTHONPATH=src` forced — global `spec-kitty` resolves the sibling fork); `@pytest.mark.performance` subprocess benchmarks via pytest-benchmark; black-box byte-identical subprocess diff for NFR-004
**Target Platform**: Linux/macOS dev + GitHub-hosted Ubuntu CI (Blacksmith runners)
**Project Type**: single (CLI tool; this repo dogfoods spec-kitty)
**Performance Goals**: `next` cold-start median ≥50% below pre-fix on the bundled clean-install fixture (import lever); charter-bearing project serves freshness from cache, skipping the ~0.5s ruamel parse on a hit (charter lever)
**Constraints**: NFR-002 no stale "fresh" governance verdict (content-keyed, fail-closed, folds in the synthesized-DRG graph file); NFR-004 byte-identical `next` output except the intrinsic per-call `timestamp`; C-002 `performance.yml` stays non-gating; C-001 keep the clean-wheel structural smoke gate
**Scale/Scope**: 4 work packages; ~185-line script deletion + one CI-step deletion + two runtime optimizations + one benchmark; touches `src/specify_cli/cli/commands/next_cmd.py`, `src/specify_cli/__init__.py`, `src/specify_cli/charter_runtime/freshness/`, `src/charter/bundle.py`, `.github/workflows/{ci-quality,performance}.yml`, `tests/`

## Constitution Check (Charter — compact context loaded)

*GATE: Must pass before Phase 0. Re-check after Phase 1.*

- **DIR-040 recurring-bug structural intervention / DIR-043 close-defect-class-by-construction**: the durable fix must target the *measured* cost centers, not the hypothesized one — satisfied (squad re-scope). The freshness cache closes the "re-parse every call" class by construction; the import trim closes the "eager-build unused models" class.
- **DIR-036 black-box integration testing**: NFR-004 byte-identical proof is a real subprocess diff, not an implementation-coupled assertion.
- **DIR-044 canonical sources**: the benchmark reuses the ADR `2026-08-22-1` `pytest-benchmark`/`performance.yml` pipeline and the `tests/review/test_verdict_save_performance.py` exemplar — no hand-rolled harness. The freshness cache key reuses the existing `compute_bundle_content_hash`.
- **Terminology Canon (C-003)**: no new `feature*` aliases.
- **ATDD-first**: every WP's DoD observable in its own diff (in-diff black-box test), per the #3590 lesson carried from the prior mission.
- **No dependency changes** → supply-chain section N/A (pytest-benchmark already present).

## Project Structure

### Documentation (this mission)

```
kitty-specs/next-latency-durable-fix-01M14RM3/
├── plan.md              # This file
├── spec.md              # Re-scoped spec
├── research/
│   └── post-spec-squad-findings.md   # 3-lens convergent evidence (the map)
├── research.md          # Phase 0 decisions (this command)
├── data-model.md        # Phase 1: cache key + verdict entities
├── quickstart.md        # Phase 1: how to measure/verify
├── contracts/           # Phase 1: cache-key + output-preservation contracts
└── tasks.md             # Phase 2 (/spec-kitty.tasks — NOT this command)
```

### Source Code (repository root)

```
src/specify_cli/
├── __init__.py                       # _build_app (:161) — lazy command registration (WP-A secondary)
├── cli/commands/next_cmd.py          # top-level imports (:21-48, WP-A); _run_charter_preflight_for_next (:523, WP-B); _run_query_mode (:791)
└── charter_runtime/freshness/
    └── computer.py                   # compute_freshness (:794), _compute_synthesized_drg (:803), _safe_load_yaml (:352) — WP-B cache seam
src/charter/
└── bundle.py                         # compute_bundle_content_hash — WP-B key base

tests/
├── specify_cli/next/  or  tests/runtime/   # WP-C: @pytest.mark.performance next cold-start benchmark
├── charter_runtime/ (or nearest)           # WP-B: no-stale-verdict correctness test
└── specify_cli/next/                        # WP-A/B: byte-identical (NFR-004) subprocess test

.github/workflows/
├── ci-quality.yml       # remove latency step (:4076); KEEP smoke (:4031) — WP-D
└── performance.yml      # next domain leg already present (:99) — WP-C (no workflow edit)

scripts/check_nfr_003_latency.py        # DELETE — WP-D
kitty-specs/shared-package-boundary-cutover-01KQ22DS/nfr-003-baseline.json  # drop absolute ceiling — WP-D
tests/performance/baselines/Linux-CPython-3.11-64bit/  # WP-C: seed next baseline post-fix
```

**Structure Decision**: Single-project CLI. Two runtime levers live in their own subsystems (`cli/commands/next_cmd.py` import surface + `charter_runtime/freshness/`), independent of each other; the CI/perf changes live in `.github/workflows/` + `tests/performance/` + `scripts/`.

## Complexity Tracking

No Charter violations requiring justification. The one elevated-risk item (caching a governance verdict, WP-B) is handled by design (content-keyed, fail-closed, folds in the DRG graph file) and a mandatory pre-merge adversarial review pass — not a complexity waiver.

## Parallel Work Analysis

### Dependency Graph

```
WP-A (import-graph trim)  ─┐
                           ├─→ WP-C (benchmark + seed POST-fix baseline) ─→ WP-D (remove blocking gate + delete script/ceiling)
WP-B (charter-freshness cache) ─┘
```

- **WP-A** and **WP-B** are independent subsystems → parallel (Wave 1).
- **WP-C** depends on A **and** B: the committed performance baseline must reflect the *post-fix* latency (FR-006), so the benchmark is seeded only after both levers land.
- **WP-D** depends on **WP-C**: never remove the blocking guard before its off-PR replacement exists (no guard gap). WP-D also carries FR-004/FR-005/NFR-003/C-001.

### Work Distribution

- **WP-A — Import-graph trim** (FR-001, NFR-001 import lever, NFR-004): defer eager pydantic doctrine/charter/events/status model imports on the read-only `kind:"query"` path; anchor `next_cmd.py:21-48`, secondary lazy command registration in `__init__.py:161`. DoD: `-X importtime` shows a measurably lighter graph (module count / self-import time down by a stated threshold) AND a byte-identical `next` JSON subprocess test. Profile: `python -X importtime -m specify_cli next …` before/after.
  - Owned: `src/specify_cli/cli/commands/next_cmd.py`, `src/specify_cli/__init__.py`, `tests/specify_cli/next/test_next_import_footprint.py` (new).
- **WP-B — Charter-freshness content-hash cache** (FR-002, NFR-002, NFR-004, C-005): persist `CharterFreshness` to a content-keyed sidecar; key = `compute_bundle_content_hash` folded with the synthesized-DRG graph file hash; skip the ruamel parse on a hit; fail-closed on miss/read-error. DoD: in-diff no-stale test (mutate bundle → recompute; mutate DRG graph file → recompute) AND a profiled cache-hit that skips `_safe_load_yaml` AND byte-identical output. **Elevated risk — governance verdict; pre-merge adversarial review pass required.**
  - Owned: `src/specify_cli/charter_runtime/freshness/` (new cache module + wiring at `computer.py`/`next_cmd.py:523`), `tests/charter_runtime/test_freshness_cache.py` (new). Reads `src/charter/bundle.py` (no edit expected; a small key-surface addition if the DRG-graph hash isn't exposed).
- **WP-C — Perf benchmark + baseline** (FR-003, FR-006, NFR-001 guard): subprocess-based `@pytest.mark.performance` `next` cold-start benchmark (`benchmark.pedantic(subprocess.run([...]), rounds=…, warmup_rounds=1, iterations=1)`; exemplar `tests/review/test_verdict_save_performance.py`) under `tests/specify_cli/next/`; seed the `next` baseline under `tests/performance/baselines/Linux-CPython-3.11-64bit/` from the post-fix measurement. DoD: the benchmark is collected by `performance.yml`'s next leg, skipped on normal PR runs (env-gated), and a committed baseline exists reflecting post-fix latency.
  - Owned: `tests/specify_cli/next/test_next_cold_start_performance.py` (new), `tests/performance/baselines/Linux-CPython-3.11-64bit/<next>.json` (new).
- **WP-D — Retire the blocking gate** (FR-004, FR-005, NFR-003, C-001): remove the discrete "NFR-003 latency regression gate" step at `.github/workflows/ci-quality.yml:4076`; KEEP the structural smoke step at `:4031`. Delete `scripts/check_nfr_003_latency.py`; drop the absolute `ci_target_median_seconds` ceiling from `kitty-specs/shared-package-boundary-cutover-01KQ22DS/nfr-003-baseline.json` (leave the file's historical record or repoint it as a note). DoD: `quality-gate.needs` enumeration shows no wall-clock latency ceiling; the clean-wheel smoke still fails when `next` cannot run; the script no longer exists.
  - Owned: `.github/workflows/ci-quality.yml`, `scripts/check_nfr_003_latency.py` (delete), `kitty-specs/shared-package-boundary-cutover-01KQ22DS/nfr-003-baseline.json`, `tests/ci/` guard if one asserts the blocking set.

### Coordination Points

- **Sync**: A+B land (Wave 1) → measure post-fix → C seeds baseline → D removes the old gate.
- **Integration tests**: NFR-004 byte-identical subprocess diff spans A and B (a shared black-box oracle, NOT the masked `canonical()` from `tests/runtime/test_bridge_parity.py`). The pre-merge review squad re-verifies NFR-002 (no stale governance verdict) and the cross-WP CI graph (no blocking latency ceiling remains, smoke retained).
- **Runner attribution**: local measurements are warm-FS; the authoritative cold-wheel attribution comes from `performance.yml` on the actual runner once the benchmark lands — noted as a WP-C follow-through, not a blocker.
