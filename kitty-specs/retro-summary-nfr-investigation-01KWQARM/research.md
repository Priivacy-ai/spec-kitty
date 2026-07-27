# Research: Retro-summary NFR investigation — evidence base + methodology (#2342)

Prior evidence assembled from the issue and the post-spec adversarial squad's *measured* leads. These are leads to **verify**, not conclusions.

## Background (from #2342)
- `test_200_missions_under_5s` (NFR-003: `build_summary` over a 200-mission corpus < 5s) breached twice on CI: **5.11s** (PR #2336 run 1) and **5.10s** (run 2, unrelated diff). Two consecutive near-identical readings are suspicious both ways: too consistent for pure runner noise, too close to the line for an obvious algorithmic blow-up.
- Budget dance: 5.0s baseline → briefly re-tuned to 6.5s (commit **`95504c0d4`**) → **reverted to 5.0s + test quarantined** (`@pytest.mark.quarantine`) in commit **`f844a057f`** (verified via `git log -S "@pytest.mark.quarantine" -- tests/retrospective/test_summary_tolerance.py`; the earlier-cited `f52764466` is an unrelated SSOT/seam-consolidation commit). Variance collection via the non-blocking `quarantine-visibility` job started at that merge. These are the honest budget-dance endpoints the flippable-oracle bisection should anchor on.

## Measured leads (post-spec squad, verify against live corpus)
- **`YAML()` object construction is NOT the hotspot.** Measured with the repo's ruamel: `YAML(typ="safe")` construction ≈ 38µs → ×200 ≈ 7.7ms ≈ **0.15% of the 5000ms budget**; hoisting a single reused instance saves ~9.4ms ≈ 0.19%. The breach was ~100–110ms over budget — an order of magnitude larger. So a YAML()-hoist "fix" would be a red herring.
- **Dominant per-mission cost is in `reader.py` + `schema.py`, not `summary.py`.** `summary.py:421` is only the call site `record = read_record(retro_path)`. The parse/validate cost is `read_record` (`reader.py:333`) → `_load_yaml_mapping` YAML safe-load (`reader.py:117`) → `_coerce_legacy_schema_versions` (`reader.py:355`) → `RetrospectiveRecord.model_validate(...)` **called at `reader.py:355`** (model defined at `schema.py:380`), run ×200 — the "YAML load paths" candidate. Profile must confirm.
- **The bisection window must span `reader.py schema.py summary.py`, not summary.py alone.** #1888/#2119 don't touch `summary.py` (terminus-classification → **#821** `9733727df`; `_resolve_summary_record_path` → **#1850** `8544012fa`; #2119 only did a no-op literal→constant swap `ecf45f52c`). **Prime suspect: commit `0818c7590` (#1778)** rewrote `_load_yaml_mapping`, inserted a per-record `_coerce_legacy_schema_versions` pass on the hot path, and edited `test_summary_tolerance.py` — all without touching `summary.py`, so a `summary.py`-only bisect steps right over it. Confirm the corpus exercises a suspected branch before trusting a flat delta (the retrospective-only corpus writes `retrospective.yaml` with no `meta.json`, so some read-path branches are dead in this workload).

## Methodology (binding)
1. **Profiling (IC-01):** build the test's 200-mission corpus; `cProfile` `build_summary` ≥5 runs; report **median + min–max spread** and a per-phase breakdown (fs scan / YAML parse / reduce). Function-level cProfile naturally separates `YAML.__init__` from `YAML.load`.
2. **Bisection (IC-02):** the oracle **must be proven flippable** before trusting a "no regression" result — establish a known-bad endpoint that reads red on this hardware, or use a relative per-phase-delta threshold. Fast local hardware makes the raw `assert elapsed < 5.0` oracle prone to marking every commit GOOD (false negative). If the oracle can't flip → verdict = **inconclusive**, not "no regression."
3. **Disposition (IC-03):** exactly one of — real regression → root fix + restore 5.0s + lift quarantine; CI-flake → dedicated non-blocking perf slice **or** `local_only`. Never a budget bump. Week-long CI-variance collection = maintainer follow-up.

## Deliverable
`docs/plans/engineering-notes/2342-retro-summary-nfr/report.md` — verdict + evidence (profiling table, bisection outcome) + one recommended disposition with enactment + quarantine-lift steps. Conditional minimal `summary.py` fix only if clean and low-risk.

## Key files
- `src/specify_cli/retrospective/summary.py` (`build_summary`; the `read_record` **call site** at ~:421)
- `src/specify_cli/retrospective/reader.py` (`read_record` :333, `_load_yaml_mapping` :117, `_coerce_legacy_schema_versions` :355 — the real hot path)
- `src/specify_cli/retrospective/schema.py` (`RetrospectiveRecord` model def :380; validated via `.model_validate(...)` at `reader.py:355`)
- `tests/retrospective/test_summary_tolerance.py::test_200_missions_under_5s` (quarantined; corpus fixture)
- `tests/_support/quarantine.py`; `docs/guides/testing-flakiness.md`
