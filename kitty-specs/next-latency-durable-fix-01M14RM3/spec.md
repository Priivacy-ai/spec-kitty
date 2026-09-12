# Mission Specification: Next-Command Latency — Durable Fix + Perf-Gate Migration

**Mission Branch**: `perf/next-latency-durable-fix`
**Created**: 2026-08-28
**Status**: Draft (re-scoped after post-spec research squad — see `research/post-spec-squad-findings.md`)
**Input**: GitHub issue #3787 (3.2.6 milestone; parent #3595). Relates to #2723, #2722, #2853, #2749, #3783.

## Intent Summary

**Primary actors**: (1) the developer/operator running the mission loop, who invokes `spec-kitty next` many times per session; (2) the contributor opening a pull request, whose CI must not red on unrelated latency noise; (3) the maintainer, who wants a real latency regression caught without false alarms.

**Trigger & problem**: `spec-kitty next` cold-start is slow (up to ~1.8s on shared CI runners vs a 0.745s baseline) and the check guarding it — `scripts/check_nfr_003_latency.py`, run by the `clean-install-verification` job and wired into `quality-gate.needs` — is a single-shot absolute wall-clock ceiling on a shared runner, still on the **blocking PR path**. It false-reds on runner variance and has been ratcheted up four times (1.00 → 1.05 → 1.60 → 2.20s). This is the anti-pattern the statistical performance pipeline (ADR `2026-08-22-1`, `.github/workflows/performance.yml`, `@pytest.mark.performance`) was built to eliminate; the migration missed it because it is a bespoke CI **script step**, not a marked test.

**Corrected causal model** (three-lens research squad, convergent — `research/post-spec-squad-findings.md`): the step-authority **projection is NOT the cost** — `project_action_sequence` is ~0ms and already `@functools.cache`d. The brief inherited a misdiagnosis from the gate script's own docstring. The real cold-start cost splits by context:
- **CI clean-install fixture (no `charter.yaml`)** — dominated by the **~0.72s Python import floor**: 84% of cold-start is per-process module import, ~0.42s of it building 336 pydantic models pulled transitively by `next_cmd.py`'s top-level imports (`charter`, `spec_kitty_events`, `doctrine.*.models`, `status.models`). This floor governs the CI number that red-blocks PRs and worsens on a cold runner.
- **Real project with a charter** — dominated by **~0.5s charter-freshness recompute**: `_run_charter_preflight_for_next` ruamel-parses the full (1588-line) `charter.yaml` on every `next`.

**Desired outcome**: (a) **durable runtime fix, two levers** — trim the `next`-path import graph, AND content-hash-cache the charter freshness verdict — so cold-start drops materially in both contexts; (b) no wall-clock latency assertion remains on any PR-blocking path; (c) the `next`-latency signal moves onto the off-PR statistical pipeline with a committed baseline reflecting the *post-fix* latency.

**Load-bearing invariants**: the charter-freshness cache must **never serve a stale "fresh" governance verdict** (its key must fold in every input that changes the verdict — the charter bundle content hash *and* the synthesized-DRG graph file — and be content-based, never mtime); and neither lever may change `next` output for identical inputs.

**Assumptions** (recorded, not asked):
- The durable fix optimizes the existing `next` read path; it does not redesign step-authority (#2723), the doctrine SSOT model, or charter-freshness *semantics* (only memoizes the verdict).
- "Materially faster" targets ≥50% cold-start reduction on the bundled fixture (import lever) and a freshness-cache-hit that skips the ~0.5s parse on a charter-bearing project; if a profiled floor makes a specific number infeasible, plan records the best-achievable with evidence.
- The clean-install job's *structural* check (that `spec-kitty next` runs at all from a clean wheel) is a legitimate blocking smoke test and is retained.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - `spec-kitty next` is fast again (Priority: P1)

A developer driving the mission loop runs `spec-kitty next` repeatedly. After the durable fix, the `next`-path import graph is trimmed (the read-only query path no longer eagerly builds the full pydantic model foundation) and the charter freshness verdict is served from a content-hash cache instead of re-parsing the whole charter every call, so cold-start drops materially in both the no-charter (CI fixture) and charter-bearing (real project) contexts.

**Why this priority**: This is the actual product defect. Migrating the CI gate without the runtime fix would just hide a slowdown that every user pays on every invocation.

**Independent Test**: `-X importtime` shows a measurably lighter `next`-path import graph; a charter-bearing project shows a `next` freshness-cache **hit** that skips the ruamel parse (profiled); subprocess cold-start median drops ≥50% on the bundled fixture; identical inputs produce byte-identical `next` JSON.

**Acceptance Scenarios**:

1. **Given** the read-only query path, **When** `spec-kitty next` runs, **Then** it does not eagerly import model/adapter modules it never uses on that path, and the import-time cost is measurably reduced.
2. **Given** a charter-bearing project whose charter is unchanged, **When** `spec-kitty next` runs twice, **Then** the second call serves the freshness verdict from the content-hash cache and skips the full charter parse.
3. **Given** identical mission inputs, **When** `next` runs with and without a warm cache / trimmed imports, **Then** the emitted JSON is byte-identical.

---

### User Story 2 - Unrelated PRs stop red-ing on latency noise (Priority: P1)

A contributor opens a PR that does not touch the `next` path. Today the blocking `clean-install-verification` latency step can red their PR purely on shared-runner variance. After this mission, no PR-blocking job asserts a wall-clock latency ceiling.

**Why this priority**: The recurring contributor-facing harm (four ratchet recalibrations; a ~92% false-red rate on the retired `timing-nfr-serial` gate per ADR `2026-08-22-1`). Latency is already at baseline on normal hardware; the block is pure runner noise.

**Independent Test**: Enumerate `quality-gate.needs` — assert no job runs a wall-clock latency ceiling; assert `clean-install-verification` still fails when `spec-kitty next` cannot run at all from a clean wheel.

**Acceptance Scenarios**:

1. **Given** the CI workflow, **When** the blocking set is enumerated, **Then** no job runs a single-shot wall-clock latency ceiling.
2. **Given** a clean-wheel install where `spec-kitty next` errors, **When** `clean-install-verification` runs, **Then** it still fails (structural smoke retained).
3. **Given** `scripts/check_nfr_003_latency.py`, **When** the mission completes, **Then** the script and the absolute `ci_target_median_seconds` ceiling no longer exist.

---

### User Story 3 - The improvement is guarded statistically, off the PR path (Priority: P2)

A `@pytest.mark.performance` benchmark for `next` cold-start runs only in `performance.yml` (off-PR, non-gating, statistical, relative-delta compare) against a committed baseline that reflects the post-fix latency.

**Why this priority**: Without a guard the durable fix could silently regress; but the guard must live on the correct (off-PR, statistical) pipeline.

**Independent Test**: A `performance`-marked, **subprocess-based** `next` benchmark exists under the next domain with a committed baseline under `tests/performance/baselines/`, is collected by `performance.yml`, and is skipped on every normal PR run (env-gated `SPEC_KITTY_RUN_PERFORMANCE=1`).

**Acceptance Scenarios**:

1. **Given** the performance pipeline, **When** it runs, **Then** it measures `next` cold-start statistically and compares against a committed baseline with a relative-delta failure threshold.
2. **Given** a normal PR run, **When** the suite executes, **Then** the `next` benchmark is not collected.
3. **Given** the committed baseline, **When** it is read, **Then** it reflects the post-fix latency.

### Edge Cases

- The synthesized-DRG graph file changes but the charter bundle does not → the freshness cache MUST still recompute (key folds in the DRG graph file); a bundle-only key would serve a stale `synthesized_drg` verdict.
- A cold CI filesystem inflates the step.yaml load slice (`_inject_projected_fields`, ~70ms local) → plan-phase profiling on the runner decides whether an on-disk step cache earns its NFR-002 surface; default is no (already `functools.cache`d in-process).
- The `next` performance leg has no committed baseline on first run → `performance.yml` treats a missing baseline as a pass (exit 4); the baseline must be seeded once post-fix via `--benchmark-save`.
- A deferred import turns out to be needed on the query path → it must still resolve identically when first used (lazy import is behavior-preserving); NFR-004 byte-identical test guards this.

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | Trim the `next`-path import graph | As a developer, I want the read-only `next` query path to defer eager imports it does not use (the pydantic doctrine/charter/events model foundation pulled by `next_cmd.py`) so per-process cold-start import cost drops. | High | Open |
| FR-002 | Cache the charter freshness verdict | As a developer, I want `spec-kitty next` to serve the charter freshness verdict from a content-hash-keyed cache and skip the full charter parse on a hit, so real-project `next` latency drops. | High | Open |
| FR-003 | `next` cold-start performance benchmark | As a maintainer, I want a subprocess-based `@pytest.mark.performance` benchmark for `next` cold-start under the next domain with a committed baseline, run only in `performance.yml`. | High | Open |
| FR-004 | Remove the blocking latency ceiling; keep the smoke check | As a contributor, I want the wall-clock latency step removed from `clean-install-verification` while the clean-wheel "does `next` run at all" check is retained. | High | Open |
| FR-005 | Retire the single-shot gate and absolute ceiling | As a maintainer, I want `scripts/check_nfr_003_latency.py` and the absolute `ci_target_median_seconds` ceiling removed so there is no ratchet left to drift. | High | Open |
| FR-006 | Baseline reflects post-fix latency | As a maintainer, I want the committed performance baseline seeded from the post-fix measurement so the pipeline guards the improvement. | Medium | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | `next` cold-start latency | On a charter-bearing project, a warm freshness cache skips the ~0.5s charter parse on `next` (profiled cache hit) — the mission's real durable latency win. The import-graph lever additionally reduces the no-op/startup import footprint (measured `-X importtime` delta). Post-tasks squad B2 established the CI-fixture real-query number is import-floor-bound in `runtime_bridge` (shared-package boundary, out of scope): NFR-001 does NOT claim a ≥50% fixture reduction; that floor is a separate architect-led follow-up. Measured over ≥5 runs. | Performance | High | Open |
| NFR-002 | No stale governance verdict | The charter freshness cache serves a recomputed verdict in 100% of cases where any keyed input changed — the charter bundle (`compute_bundle_content_hash`) OR the synthesized-DRG graph file. A dedicated correctness test proves a stale "fresh" verdict is never served; key is content-based, never mtime; misses fail closed to recompute. | Reliability | High | Open |
| NFR-003 | No latency assertion on the blocking path | Zero jobs in `quality-gate.needs` (or branch protection) assert a wall-clock latency ceiling after this mission; the `next`-latency signal runs only in the non-gating `performance.yml`. | CI Integrity | High | Open |
| NFR-004 | Output-preserving fix | Neither the import deferral nor the freshness cache changes `spec-kitty next` output: byte-identical JSON for identical inputs, warm vs cold, trimmed vs untrimmed (excluding the intrinsically per-call `timestamp` field). | Correctness | High | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | Keep the clean-wheel structural smoke test | The `clean-install-verification` check that `spec-kitty next` runs at all from a clean wheel remains a blocking gate; only the wall-clock latency assertion is removed. | Technical | High | Open |
| C-002 | Performance pipeline stays non-gating | `performance.yml` must never be a required status check, in branch protection, or in `quality-gate.needs` (ADR `2026-08-22-1` C-002). | Technical | High | Open |
| C-003 | Terminology canon | No new `feature*` aliases; the domain object is a Mission. | Technical | Medium | Open |
| C-004 | Scope boundary | The durable fix is (a) import-graph deferral on the `next` read path and (b) content-hash caching of the charter freshness verdict. It does NOT add a step-projection cache (already `functools.cache`d, ~0ms), redesign step-authority (#2723), change the doctrine SSOT model, or change charter-freshness semantics. | Technical | High | Open |
| C-005 | Fail-closed, content-keyed cache | The freshness cache key must be content-based (never mtime) and fold in every input that changes the verdict (charter bundle + synthesized-DRG graph file); any key miss or read error recomputes rather than serving a possibly-stale value. | Technical | High | Open |

### Key Entities

- **Charter freshness verdict**: the `CharterFreshness` object computed by `_run_charter_preflight_for_next` on every `next`; the ~0.5s cost on a charter-bearing project.
- **Freshness cache sidecar**: content-hash-keyed persisted verdict; key = `compute_bundle_content_hash` folded with the synthesized-DRG graph file hash.
- **`next` import graph**: the transitive top-level imports of `next_cmd.py` (the pydantic model foundation) that dominate per-process cold-start on the fixture.
- **Performance baseline**: the committed per-domain `pytest-benchmark` reference under `tests/performance/baselines/`.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: On a charter-bearing project, `spec-kitty next` serves the freshness verdict from cache and skips the ~0.5s charter parse (profiled). The import-graph lever reduces the no-op/startup import footprint by a measured `-X importtime` delta. (No ≥50% CI-fixture claim — the real-query floor is import-bound in `runtime_bridge`, deferred to a follow-up per squad B2.)
- **SC-002**: Zero PR-blocking CI jobs assert a wall-clock latency ceiling; the clean-wheel structural smoke check still gates.
- **SC-003**: A committed subprocess-based `next` cold-start performance baseline plus relative-delta comparison guards latency in the non-gating `performance.yml`, skipped on every normal PR run.
- **SC-004**: `scripts/check_nfr_003_latency.py` and the absolute `ci_target_median_seconds` ceiling no longer exist; a genuine step-change `next` latency regression is caught off-PR by the statistical pipeline; the charter freshness cache never serves a stale verdict (proven by test).
