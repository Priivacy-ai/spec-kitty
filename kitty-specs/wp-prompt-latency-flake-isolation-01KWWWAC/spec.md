# Mission Specification: Isolate the WP-prompt latency NFR tests from parallel-execution flake

**Status**: Draft
**Issues**: Closes [#2032](https://github.com/Priivacy-ai/spec-kitty/issues/2032) (M4 of epic #1931)

## User Scenarios & Testing *(mandatory)*

**Primary actor**: a contributor whose otherwise-green PR is red-flagged by a latency NFR test that failed on CI-runner contention, not a regression.

**Grounding**: `tests/architectural/test_wp_prompt_build_latency.py` asserts `_build_wp_prompt(action='implement'|'review')` completes under `_LATENCY_BUDGET_SECONDS` using a **single cold `time.perf_counter()` sample**. It runs on the arch-adversarial shard (`pytest -n auto --dist loadfile`). When co-scheduled with CPU-heavy tests, contention inflates the one measured sample past the budget. #2032's evidence is decisive: a **CHANGELOG-only diff flipped PASSED→FAILED** across two commits — the diff cannot touch prompt-build latency, so the failure is pure timing variance. It red-flagged the fully-green PR #2028.

**Current state (re-checked on `main`)**: the budget was already band-aided **8.0 → 10.0s** with a comment arguing *"the correct lever for CI variance is a wider budget — not a retry plugin."* Widening lowers the flake rate but does not eliminate it (a saturated runner can still blow 10s), and an ever-widening budget erodes the NFR's meaning. The structural fix is **serial isolation** (remove the concurrent CPU load, reusing the existing C-SERIAL `-n0` pattern) — NOT on-shard statistical sampling, which multiplies the slowdown ~6× on the very runner that's already saturated, and NOT `xdist_group` (inert under `--dist loadfile`).

### User Story 1 - A loaded runner no longer reds a clean PR (Priority: P1)
As a contributor, I want the latency assertion to survive CI contention without a real regression, so my green PR is not flaky-red-flagged.

**Independent test**: run the two latency tests under simulated CPU load (`-n auto` alongside CPU-heavy tests) repeatedly; they stay green with no code regression.

### User Story 2 - The NFR still bites on a real regression (Priority: P1)
As a maintainer, I want the gate to still fail if prompt-build genuinely regresses (e.g. a new synchronous/blocking call in the build path), not to be softened into meaninglessness.

### Edge Cases
- The measurement must not become a **retry-to-green** or an ever-widening budget (both are anti-patterns; the code comment rightly rejects retry plugins — this fix rejects both).
- The min/median-of-N warm measurement must run quickly (a few extra `_build_wp_prompt` calls) so it doesn't materially slow the arch shard.
- If min/median-of-N still flakes under extreme load, fall back to serial isolation (`xdist_group` / a `-n0` pass) — must fit the sharded arch topology (`_arch_shard_map.py`), not break it.

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
| --- | --- | --- | --- | --- |
| FR-001 | Isolate via the CANONICAL `timing` marker in a NEW ALWAYS-ON serial step | As a maintainer, I want the two latency tests marked with the **existing** `@pytest.mark.timing` marker (`pytest.ini:49`), removed from the parallel `-n auto --dist loadfile` arch pole via **`and not timing`** on the arch selectors (`ci-quality.yml:1816` full branch AND `:1667` — idiom at `:2418`), and run in a **NEW dedicated ALWAYS-ON serial step** (`-n0`, `-m timing` on `tests/architectural/test_wp_prompt_build_latency.py`). **Critical: the step must be always-on** (no `if:` change-filter gate) — mirror the arch pole's `if: always()` (`:1707`), NOT the `restart-daemon-nfr-timing` job (`:2488`), which is **`cli`-change-gated** (`needs.changes.outputs.cli`); the `cli` filter (`:200-203`) covers only `src/specify_cli/cli/**`, but `_build_wp_prompt` is `src/runtime/next/**` (→ `core_misc`), so extending that cli-gated job would **silently skip the NFR on the very prompt-builder PRs it guards** (defeating SC-003). Reuse the `timing` marker + serial-step concept; do NOT register in `pyproject.toml` (forbidden), invent a marker, mirror the C-SERIAL/port pattern, or use `xdist_group` (inert under `--dist loadfile`). | High | Open |
| FR-002 | Keep wall-clock; warm-up + a bounded sample | As a maintainer, I want the oracle to stay **wall-clock** (`perf_counter`) — `_build_wp_prompt` does `subprocess.run` + `read_text`, so a CPU-time oracle would miss a new synchronous/blocking regression. Once isolated (FR-001), drop the cold-sample corruption with a **warm-up run + a single warm sample (or median-of-3)** — NOT min-of-N (which multiplies cost on the contended shard, the worst place). Budget stays a real ceiling; since it's now isolated, it can be a sane multiple of the ~1.5s warm baseline rather than an ever-growing number. | High | Open |
| FR-003 | No retry-to-green, no ever-widening budget | As a maintainer, I want the fix structural (serial isolation), NOT a retry plugin nor a further budget bump; document why isolation is the correct lever and `xdist_group` is inert. | High | Open |
| FR-004 | Shard-topology coherence | As a maintainer, I want the two tests to stay registered in `_arch_shard_map.py` (so `test_arch_shard_marker_completeness.py` stays green) while being excluded from the *parallel* run via the marker; the serial `-n0` step is the sole place they execute. No test is deselected/lost. | High | Open |
| FR-005 | Non-vacuous proof | As a maintainer, I want proof: the tests run green in the serial `-n0` step (not the parallel shard), and a **seeded artificial delay** (`time.sleep`) in the build path still reds the gate (the NFR bites — mutation-proven). | High | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
| --- | --- | --- | --- | --- | --- |
| NFR-001 | Bounded added runtime | The serial `-n0` step runs 2 tests × (1 warm-up + ≤3 samples) ≈ a few seconds in its own step; the parallel arch shard *loses* these 2 tests (net-neutral or faster). No min-of-N multiplication on a contended runner. Quantify: added wall-clock ≤ ~4× the ~1.5s warm baseline. | Performance | Medium | Open |
| NFR-002 | No concurrent-load corruption | Measured in a serial `-n0` step, the wall-clock sample sees no co-scheduled CPU load — the contention root cause is removed, not merely averaged. | Reliability | High | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
| --- | --- | --- | --- | --- | --- |
| C-001 | Fit the sharded arch topology | The tests stay registered in `_arch_shard_map.py`; any isolation must not deselect them or red `test_arch_shard_marker_completeness.py` (#2397). | Technical | High | Open |
| C-002 | No new suppressions | `ruff` + `mypy --strict` clean; no new `# noqa`/`# type: ignore`. | Technical | High | Open |

### Key Entities
- **`tests/architectural/test_wp_prompt_build_latency.py`** — the two flaky tests; `_LATENCY_BUDGET_SECONDS` (now 10.0); single cold `perf_counter` sample (→ serial-isolated + warm sample); needs a `serial`/`latency` marker.
- **`pytest.ini:49`** — the **canonical `timing` marker** (already registered). Add `@pytest.mark.timing` to the 2 tests. Do NOT register in `pyproject.toml` (`[tool.pytest.ini_options]` markers are forbidden + gate-guarded by `test_marker_registry_single_source.py`).
- **`.github/workflows/ci-quality.yml`** — the arch pole selectors (`:1667`, `:1816`) need `and not timing` (idiom at `:2418`); add a **NEW always-on serial `-m timing` step** (`if: always()` mirroring the arch pole at `:1707`, `-n0`). Do NOT reuse the `restart-daemon-nfr-timing` job (`:2488`) — it is `cli`-change-gated (`needs.changes.outputs.cli`, filter `:200-203` = `src/specify_cli/cli/**` only), so it would skip on `src/runtime/next/**` (prompt_builder) PRs.
- **`_arch_shard_map.py`** — the tests' shard registration (stays valid; completeness gate green — still registered, just excluded from the *parallel* run).

## Success Criteria *(mandatory)*

### Measurable Outcomes
- **SC-001**: The two tests execute ONLY in the serial `-n0` step (marked + excluded from the parallel arch pole selector — no double-run); a warm-up + ≤3 warm wall-clock samples, no single cold sample.
- **SC-002**: `test_arch_shard_marker_completeness.py` stays green (tests still registered in `_arch_shard_map.py`); the new **always-on** serial `-m timing` step runs + passes them **on every PR** (no `cli`/change-filter gate — mirrors the arch pole's `if: always()`, so a prompt-builder regression can't skip the NFR); `xdist_group` is not used.
- **SC-003**: A seeded artificial delay (`time.sleep`) in the build path still reds the gate (NFR bites — mutation-proven).
- **SC-004**: Budget is a meaningful multiple of the ~1.5s warm baseline (not further inflated); `ruff` + `mypy --strict` clean; no new suppressions.

## Out of Scope
- A pytest retry plugin (explicitly rejected).
- `xdist_group`-based isolation (verified inert under `--dist loadfile`).
- Broader arch-shard topology rework beyond marking + excluding these 2 tests and adding the serial `-n0` step (reusing the existing C-SERIAL pattern).

## Assumptions
- The serial `-n0` step removes the concurrent-load root cause; a warm wall-clock sample in that quiet step is stable. Wall-clock stays the oracle (the build does `subprocess.run` + `read_text`, so CPU-time would miss a blocking regression).
