# Implementation Plan: Isolate the WP-prompt latency NFR tests from parallel-execution flake

**Branch**: `fix/latency-nfr-isolation` | **Issue**: Closes #2032 (M4 of #1931) | **Spec**: [spec.md](./spec.md)

## Summary

The two `test_wp_prompt_build_latency.py` tests flake because a single cold wall-clock sample is corrupted by co-scheduled CPU load on the `-n auto --dist loadfile` arch pole (a CHANGELOG-only diff flipped pass→fail). The structural fix reuses the **canonical `timing` marker** (`pytest.ini:49`) but runs it in a **NEW always-on serial step**: add `@pytest.mark.timing` to the two tests, add `and not timing` to the arch pole selectors (`:1667`, `:1816`) so they leave the parallel shard, and add a new `-n0` `-m timing` step gated `if: always()` (mirroring the arch pole `:1707`). **Do NOT reuse the `restart-daemon-nfr-timing` job (`:2488`)** — it is `cli`-change-gated (`needs.changes.outputs.cli`, filter `:200-203` = `src/specify_cli/cli/**`), but `_build_wp_prompt` is `src/runtime/next/**` (→ `core_misc`), so that job would silently skip the NFR on the very prompt-builder PRs it guards (violating SC-003). Keep the **wall-clock** oracle (the build does `subprocess.run` + `read_text`, so CPU-time would miss a blocking regression); once isolated, a warm-up + single warm sample is stable. **No new marker, no `pyproject.toml` registration (gate-forbidden), no C-SERIAL/port mirror, no `xdist_group` (inert under `--dist loadfile`).**

## Technical Context

**Language/Version**: Python 3.11; `pytest` + `pytest-xdist` (loadfile scheduling); GitHub Actions (`ci-quality.yml`).
**Project Type**: single project — test-marker + CI-workflow + measurement change (tightly coupled).
**Constraints**: no retry plugin; no ever-widening budget; `_arch_shard_map.py` completeness gate stays green (tests remain registered); no new suppressions; `ruff` + `mypy --strict` clean.
**Scale/Scope**: `test_wp_prompt_build_latency.py` (marker + warm sample), `.github/workflows/ci-quality.yml` (arch-selector `and not timing` + a new always-on serial `-n0 -m timing` step). Small, cohesive. The `timing` marker already lives in `pytest.ini` — **no `pyproject.toml` change**.

## Charter Check
- **No retry-to-green / no masking** — structural isolation, not a retry plugin or budget bump. ✅
- **Non-vacuous / red-first** — a seeded `time.sleep` in the build path still reds the gate (proven). ✅
- **Canonical sources** — reuse the **existing** `timing` marker (`pytest.ini:49`) + its dedicated `-m timing` job; register nothing in `pyproject.toml`; invent no new marker or mechanism. ✅
- **No new suppressions**; `ruff` + `mypy --strict` clean. ✅

## Implementation Concern Map → Work Package

Single cohesive WP (the marker, the selector exclusion, and the serial step **must land together** — a marker without the serial step would silently drop the tests; a serial step without the exclusion would double-run them).

### WP01 — Serial-isolate the latency tests + robust warm measurement
- **Relevant requirements**: FR-001..005; NFR-001/002; SC-001..004.
- **Affected surfaces**:
  - `tests/architectural/test_wp_prompt_build_latency.py`: add **`@pytest.mark.timing`** (canonical) to both tests; replace the single cold `perf_counter` sample with a **warm-up call + one warm sample (or median-of-3)**; keep the wall-clock assertion; set the budget to a sane multiple of the ~1.5s warm baseline (can tighten from 10.0 now it's isolated — keep margin). Add/keep the mutation-provable NFR (a seeded `time.sleep` reds it).
  - `.github/workflows/ci-quality.yml`: add **`and not timing`** to the arch pole selectors (`:1667` AND `:1816` — idiom at `:2418`); add a **NEW always-on serial step** (`if: always()` mirroring the arch pole `:1707`, `-n0`, `-m timing` on `tests/architectural/test_wp_prompt_build_latency.py`). **Do NOT reuse `restart-daemon-nfr-timing` (`:2488`)** — it is `cli`-change-gated (skips on `src/runtime/next/**` prompt-builder PRs → silent NFR loss). **No `pyproject.toml` change** (marker already in `pytest.ini`).
  - `_arch_shard_map.py`: unchanged — tests stay registered (completeness gate green); excluded from the *parallel* run only.
- **Sequencing**: none (single WP). **Risks**: double-run (mitigate: selector exclusion `and not timing` + the `-m timing` job land together); tests silently dropped (mitigate: confirm the `-m timing` job actually collects the file); `pyproject.toml` marker temptation (forbidden — use `pytest.ini`'s existing `timing`).

## Project Structure
```
kitty-specs/wp-prompt-latency-flake-isolation-01KWWWAC/  spec · plan · tasks
tests/architectural/test_wp_prompt_build_latency.py       # @pytest.mark.timing + warm measurement
.github/workflows/ci-quality.yml                          # arch-selector exclude + NEW always-on serial -m timing job
```
**Structure Decision**: single project, one tightly-coupled WP (test + config + CI must land atomically).
