# Implementation Plan: Retrospective Summary NFR Investigation

**Branch**: `fix/retro-summary-nfr-investigation` | **Date**: 2026-07-04 | **Spec**: [spec.md](./spec.md)
**Input**: Mission specification from `kitty-specs/retro-summary-nfr-investigation-01KWQARM/spec.md`

## Summary

Deliver an evidence-backed **verdict** (real regression | CI variance | inconclusive) on `test_200_missions_under_5s` (NFR-003) plus **one recommended disposition**, via (1) repeated-run `cProfile` of `build_summary` over the 200-mission corpus with a per-phase breakdown, and (2) a **flippable-oracle** `git bisect`. Ship code only if a clean, low-risk root-cause regression falls out (then restore the 5.0s budget + remove the quarantine marker). The week-long CI-variance collection is a maintainer follow-up (out of session scope). Prior evidence + methodology in [research.md](./research.md).

### Methodology decisions (from the post-spec squad's measured leads)

- **Focus the profile on the real hot path — which is NOT `summary.py`.** `summary.py:421` is only the *call site* `record = read_record(retro_path)`. The measured cost lives in **`reader.py`** — `read_record` (`reader.py:333`), `_load_yaml_mapping` / YAML safe-load (`reader.py:117`), `_coerce_legacy_schema_versions` (`reader.py:355`) — and the Pydantic validation `RetrospectiveRecord.model_validate(...)` **called at `reader.py:355`** (the `RetrospectiveRecord` model is defined at `schema.py:380`), run ×200. Per-mission `YAML()` object construction is ~0.2% of budget (a non-hotspot). The profile must confirm the parse/validate path against the live corpus.
- **Bisection oracle must be proven flippable (C-005-style rigor).** Local hardware is faster than CI, so the raw `assert elapsed < 5.0` oracle may never flip → `git bisect run` would falsely mark every commit GOOD. The oracle must either use the 5.0s test *only after* demonstrating a known-bad endpoint reads red on this hardware, or use a **relative per-phase timing delta** with an explicit bad/good threshold. A "no discrete regression" ruling is valid only with a demonstrated-flippable oracle; otherwise the verdict is **inconclusive**.
- **Candidate window = `git log -- reader.py schema.py summary.py`, NOT summary.py alone.** A `summary.py`-only window structurally cannot locate a regression in the parse/validate code. The squad found #1888/#2119 don't touch `summary.py` (terminus/record-path branches trace to #821/#1850 and aren't exercised by the retrospective-only corpus), and — critically — **commit `0818c7590` (#1778)** rewrote `_load_yaml_mapping`, inserted a per-record `_coerce_legacy_schema_versions` pass on the hot path, AND edited the quarantined `test_summary_tolerance.py`, all **without touching `summary.py`** — a prime suspect a summary.py-only bisect would step right over. Confirm the corpus exercises a suspected branch before trusting a flat delta.

## Technical Context

**Language/Version**: Python 3.11 (repo pinned `3.11.15`)
**Primary Dependencies**: `cProfile` / `pstats` (stdlib), `git bisect`, `pytest`; target under study `specify_cli.retrospective.summary.build_summary`
**Storage**: the 200-mission corpus fixture the test builds (reused as the profiling workload — not re-invented)
**Testing**: `tests/retrospective/test_summary_tolerance.py::test_200_missions_under_5s` (currently `@pytest.mark.quarantine`); `tests/_support/quarantine.py`
**Target Platform**: local dev machine for profiling/bisect (GitHub-runner-class + week-long variance = maintainer follow-up)
**Project Type**: single project (investigation → report; conditional code fix)
**Performance Goals**: `build_summary` over 200 missions < 5.0s (NFR-003)
**Constraints**: flippable oracle (C-005); no budget-bump-to-green (charter flakiness policy); reuse the corpus fixture (canonical source); report at a canonical `docs/plans/engineering-notes/…` path; any code passes `mypy --strict` + `ruff`
**Scale/Scope**: 200-mission corpus; deliverable is a committed report (+ conditional small `summary.py` fix)

## Charter Check

*GATE: must pass before task decomposition.*

- **Evidence-first / non-vacuous (standing order)** — the verdict is gated on measured profiling + a *proven-flippable* bisection oracle; a bare "looks fine" conclusion is inadmissible. ✅
- **No budget-bump-to-green** — disposition may not be "raise the budget"; real regression → root fix, variance → relocate off blocking CI. ✅
- **Canonical sources** — reuse the test's corpus fixture and the quarantine mechanism; do not re-invent the workload. ✅
- **Draft-PR-first / operator decides** — the disposition is a recommendation; the operator makes the final call. ✅
- **Quality gates** — any shipped code passes `mypy --strict` + `ruff`, no new suppressions. ✅

No violations → Complexity Tracking not required.

## Project Structure

### Documentation (this mission)
```
kitty-specs/retro-summary-nfr-investigation-01KWQARM/
├── spec.md · plan.md · research.md · tasks.md
```

### Source / deliverables (repository root)
```
docs/plans/engineering-notes/2342-retro-summary-nfr/report.md   # the committed investigation deliverable (verdict + evidence + disposition)
src/specify_cli/retrospective/reader.py|schema.py|summary.py     # a fix, if a clean one falls out, most likely lands in reader.py/schema.py (the parse/validate hot path), not summary.py
tests/retrospective/test_summary_tolerance.py                    # touched ONLY to restore 5.0s + remove quarantine if fixed
```

**Structure Decision**: single project. Primary deliverable is a Markdown report under `docs/plans/engineering-notes/`; code/test changes are conditional on finding a clean, low-risk regression.

## Implementation Concern Map

### IC-01 — Per-phase profiling of build_summary
- **Purpose**: quantify where `build_summary`'s time goes over the 200-mission corpus, with statistical honesty.
- **Relevant requirements**: FR-001; NFR-001; SC-001.
- **Affected surfaces**: a throwaway profiling harness that builds the test's 200-mission corpus and runs `cProfile` over `build_summary` ≥5 times; report median + min–max spread and a per-phase breakdown (fs scan / YAML parse / reduce). Confirm or refute the `read_record` YAML-parse-×200 lead.
- **Sequencing/depends-on**: none.
- **Risks**: local absolute time ≠ CI; lean on the *relative* per-phase breakdown, not raw seconds.

### IC-02 — Flippable-oracle bisection
- **Purpose**: locate a real regressing commit or credibly rule one out across the real `summary.py`/YAML-load candidate window.
- **Relevant requirements**: FR-002; SC-002.
- **Affected surfaces**: derive the candidate commit window from `git log -- src/specify_cli/retrospective/reader.py src/specify_cli/retrospective/schema.py src/specify_cli/retrospective/summary.py` (the full parse+coerce+validate path, not just the call site) — include `0818c7590` (#1778) explicitly; **first establish a flippable oracle** (prove a known-bad endpoint reads red, or define a relative per-phase-delta threshold); then `git bisect run` with that oracle. Record a regressing SHA or a substantiated "no discrete regression"; if the oracle can't be made to flip → **inconclusive**.
- **Sequencing/depends-on**: IC-01 (the per-phase metric informs the relative oracle threshold).
- **Risks**: **the false-GOOD trap** (fast local hardware) — mitigated by the mandatory flippable-oracle proof; corpus may not exercise a suspected branch → confirm before trusting a flat delta.

### IC-03 — Verdict, disposition, and committed report (+ conditional fix)
- **Purpose**: synthesize IC-01/IC-02 into one verdict + one recommended disposition, captured durably.
- **Relevant requirements**: FR-003, FR-004, FR-005, FR-006; SC-003, SC-004.
- **Affected surfaces**: write `docs/plans/engineering-notes/2342-retro-summary-nfr/report.md` — profiling numbers, bisection outcome, the single verdict, one recommended disposition (fix+restore 5.0s / dedicated non-blocking perf slice / `local_only`) with rationale + enactment steps (incl. the maintainer's week-long variance collection) and the quarantine-lift step. **If** a clean, low-risk root-cause regression is found: apply the minimal `summary.py` fix, restore the test to 5.0s, remove the `quarantine` marker, and prove it green; **else** no code ships and the report states why the quarantine remains.
- **Sequencing/depends-on**: IC-01, IC-02.
- **Risks**: over-reaching into a large/speculative fix — out of scope; recommend it instead. Disposition must never be a budget bump.
