# Tasks: Next-Command Latency — Durable Fix + Perf-Gate Migration

**Mission**: next-latency-durable-fix-01M14RM3 | **Branch**: `perf/next-latency-durable-fix`
**Plan**: [plan.md](./plan.md) | **Spec**: [spec.md](./spec.md) | **Squad map**: [research/post-spec-squad-findings.md](./research/post-spec-squad-findings.md)

4 work packages. Durable fix = two independent runtime levers (WP01 imports, WP02 charter-freshness cache), then the off-PR statistical guard (WP03) and the blocking-gate retirement (WP04).

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|----|----------|
| T001 | Profile baseline `next` import graph; find query-path-unreachable imports | WP01 | |
| T002 | Defer eager model imports in `next_cmd.py` to function scope | WP01 | |
| T003 | Lazy command registration in `_build_app` (secondary) | WP01 | |
| T004 | `test_next_import_footprint.py` — assert trimmed footprint | WP01 | |
| T005 | `test_next_output_preservation.py` — byte-identical (no-charter) | WP01 | |
| T006 | `freshness/cache.py` — composite content key + entry + fail-closed IO | WP02 | [P] |
| T007 | Wire cache into `compute_freshness` (skip parse on hit) | WP02 | |
| T008 | Verdict serialize round-trips exactly; gitignore cache dir | WP02 | |
| T009 | `test_freshness_cache.py` — 6 contract guarantees incl. DRG-graph invalidation | WP02 | |
| T010 | Charter-path byte-identical assertion (NFR-004) | WP02 | |
| T011 | `test_next_cold_start_performance.py` — subprocess `benchmark.pedantic` | WP03 | |
| T012 | Verify env-gated collection semantics (perf leg) | WP03 | |
| T013 | Seed post-fix `next` baseline JSON | WP03 | |
| T014 | Document missing-baseline pass + update_baseline path | WP03 | |
| T015 | Remove the latency step from `ci-quality.yml`; keep smoke | WP04 | |
| T016 | Delete `check_nfr_003_latency.py`; clear dangling refs | WP04 | |
| T017 | Drop absolute ceiling from `nfr-003-baseline.json`; add note | WP04 | |
| T018 | Guard test: no wall-clock ceiling on blocking path; smoke retained | WP04 | |

*The `[P]` marker indicates parallelism, not status. Completion is event-sourced via `spec-kitty agent tasks mark-status`.*

## Dependency Graph

```
WP01 (import trim) ─┐
                    ├─→ WP03 (benchmark + POST-fix baseline) ─→ WP04 (retire blocking gate)
WP02 (charter cache) ┘
```

- **WP01** and **WP02** are independent subsystems (`next_cmd.py`/`__init__.py` vs `charter_runtime/freshness/`) → **parallel** (Wave 1).
- **WP03** depends on **WP01 + WP02** (baseline must reflect post-fix latency).
- **WP04** depends on **WP03** (no guard gap: replacement exists before the blocking gate is removed).

## Work Packages

### WP01 — Import-graph trim on the next read path (Priority: P1)

- **Goal**: Defer eager pydantic model imports on the read-only `next` query path (FR-001, NFR-001, NFR-004).
- **Independent test**: `-X importtime` shows a lighter graph; `test_next_import_footprint.py` + `test_next_output_preservation.py` pass.
- **Subtasks**: T001, T002, T003, T004, T005 · **Deps**: none · **Prompt**: [tasks/WP01-import-graph-trim.md](./tasks/WP01-import-graph-trim.md)
- **Risk**: deferred import still needed on the path just moves cost; circular imports.

### WP02 — Charter-freshness content-hash cache (Priority: P1)

- **Goal**: Cache the charter freshness verdict; skip the 1588-line ruamel parse on a hit (FR-002, NFR-002, NFR-004, C-005).
- **Independent test**: profiled cache hit skips the parse; `test_freshness_cache.py` proves all 6 contract guarantees incl. DRG-graph invalidation + fail-closed.
- **Subtasks**: T006, T007, T008, T009, T010 · **Deps**: none · **Prompt**: [tasks/WP02-charter-freshness-cache.md](./tasks/WP02-charter-freshness-cache.md)
- **Risk**: ELEVATED — caches a governance verdict; stale "fresh" is a correctness regression. Pre-merge adversarial review pass required.

### WP03 — next cold-start performance benchmark + seeded baseline (Priority: P2)

- **Goal**: Subprocess-based `@pytest.mark.performance` `next` benchmark on `performance.yml`; seed post-fix baseline (FR-003, FR-006).
- **Independent test**: env-gated collection; passes under `SPEC_KITTY_RUN_PERFORMANCE=1`; committed baseline exists.
- **Subtasks**: T011, T012, T013, T014 · **Deps**: WP01, WP02 · **Prompt**: [tasks/WP03-perf-benchmark-baseline.md](./tasks/WP03-perf-benchmark-baseline.md)
- **Risk**: in-process vs subprocess confusion; auto-calibration CI-time balloon.

### WP04 — Retire the blocking NFR-003 latency gate (Priority: P2)

- **Goal**: Remove the blocking latency step; keep the structural smoke; delete the script + absolute ceiling (FR-004, FR-005, NFR-003, C-001).
- **Independent test**: `quality-gate.needs` has no wall-clock ceiling; smoke retained; script gone.
- **Subtasks**: T015, T016, T017, T018 · **Deps**: WP03 · **Prompt**: [tasks/WP04-retire-blocking-gate.md](./tasks/WP04-retire-blocking-gate.md)
- **Risk**: accidentally removing the structural smoke (C-001); dangling script references.

## MVP

WP01 + WP02 (the durable fix) is the value core; WP03 guards it; WP04 delivers the contributor-facing unblock (US2).
