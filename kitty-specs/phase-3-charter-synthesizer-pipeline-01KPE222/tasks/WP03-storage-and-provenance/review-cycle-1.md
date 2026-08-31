# WP03 Review — Cycle 1 (opus-4.6 reviewer)

## Verdict: Changes requested

WP03's owned code (staging, provenance, manifest, write_pipeline, bundle extension)
is well-designed and its 35 owned tests pass. KD-2 atomicity invariants are
exercised with real crash simulation (`patch("os.replace", ...)`) and the
manifest-last authority rule is correctly enforced.

However, two blockers prevent approval — both are explicit items in the
reviewer checklist.

---

## Blocker 1: 13 tests fail in `tests/charter/synthesizer/`

The reviewer checklist item #10 requires:
> `pytest tests/charter/synthesizer/ -q` passes (WP01+WP02+WP03 together — expected ~170+ tests).

Current result: **144 passed, 13 failed, 3 skipped**.

All 13 failures are in `tests/charter/synthesizer/test_orchestrator_synthesize.py`
(a WP01/WP02 test file). Root cause: this lane branched from the mission base
and copy-brought WP01 + WP02 source files into the single WP03 commit, but did
**not** copy the WP02 fixture YAMLs under
`tests/charter/fixtures/synthesizer/{directive,tactic,styleguide}/.../<hash>.yaml`.

The `FixtureAdapter` correctly raises `FixtureAdapterMissingError` for missing
fixtures (e.g. `tests/charter/fixtures/synthesizer/directive/mission-type-scope-directive/7eb312cccccf.directive.yaml`).
A secondary issue is that `FixtureAdapterMissingError` is a frozen dataclass,
which then triggers `FrozenInstanceError` in pytest's exception handling, but
the fix is to restore the fixtures — not to un-freeze the error class.

### Fix

Copy the missing fixture files from lane-b into this branch:

```bash
git checkout kitty/mission-phase-3-charter-synthesizer-pipeline-01KPE222-lane-b -- tests/charter/fixtures/synthesizer/
git add tests/charter/fixtures/synthesizer/
git commit -m "fix(WP03): restore missing WP02 test fixtures"
```

After this, re-run `pytest tests/charter/synthesizer/ -q` and confirm the
full suite (expected 170+) is green before re-requesting review.

---

## Blocker 2: `orchestrator.synthesize` is not wired to `write_pipeline.promote`

T018 explicitly states:

> Wire `orchestrator.synthesize` (from WP01, populated by WP02's `synthesize_pipeline`)
> to call `write_pipeline.promote` after WP02's in-memory assembly. **The lazy-import
> seam at `orchestrator.synthesize` now resolves.**

Currently `src/charter/synthesizer/orchestrator.py::synthesize()` still only
delegates to `synthesize_pipeline.run` (in-memory only) — it does not create a
`StagingDir`, does not call `promote`, and does not produce any on-disk
manifest. `write_pipeline.promote` has **no production caller** anywhere in
`src/charter/`; it is only exercised from tests.

This means WP03 ships the stage-and-promote machinery but never runs it in
the real `synthesize()` path, leaving the "lazy-import seam resolves" promise
unfulfilled. WP05 and the CLI surface that depend on `synthesize()` writing
artifacts to disk will not work until this wiring lands.

### Fix

In `src/charter/synthesizer/orchestrator.py::synthesize`, after the in-memory
`run_all(...)` assembly:

1. Create a `StagingDir` scoped to `request.run_id`.
2. Call `write_pipeline.promote(request, staging_dir, results, validation_callback)`.
3. Use a `lambda staging_dir: None` placeholder for `validation_callback` —
   WP04 will replace this with its real DRG + schema gate.
4. Wrap the staging lifecycle in the `StagingDir` context manager so that
   unhandled exceptions route to `.failed/` (the staging module already
   implements this; the wiring just needs to use `with` properly).
5. Add an integration test in `tests/charter/synthesizer/test_orchestrator_synthesize.py`
   (or a new file) that runs `synthesize(...)` end-to-end against a
   `FixtureAdapter` and asserts the manifest + artifacts land on disk.

If you interpret T018 differently (i.e. wiring is WP04's job because the
validation_callback is WP04-owned), please add a short note to the WP03 task
file explaining the hand-off so the reviewer can resolve the ambiguity — but
leaving `promote` without any production caller as-written is a dead-code
concern (checklist item #12).

---

## Non-blocking observations

- **ruff**: one `UP037` in `src/charter/synthesizer/synthesize_pipeline.py:89`
  — the `_check_source_provenance` return type uses quoted `"ProvenanceEntry"`
  instead of the unquoted self-class reference. Auto-fixable with `ruff check --fix`.
- **Scope**: the single `feat(WP03)` commit contains WP01 + WP02 + WP03 source
  files because the branch was based on the mission base rather than stacked on
  lane-b. The WP01/WP02 files are byte-identical to lane-b, so merge should
  handle this cleanly, but future WPs in this mission would benefit from
  explicit stacking on the dependency lane.
- **Good**: `PathGuard` coverage is complete on all four new modules (no raw
  `Path.write_*`, `open('w')`, or `os.replace` outside `path_guard.py` itself).
  The WP01 lint-style test in `test_path_guard.py` still passes.
- **Good**: `ProvenanceEntry` is reused from `synthesize_pipeline.py` (WP02);
  the only WP02 edit is an additive `model_validator` implementing the allOf
  constraint from `contracts/provenance.schema.yaml`, which is correct and
  in-scope for T015.
- **Good**: `canonical_yaml` is reused across `provenance.py`, `manifest.py`,
  and `write_pipeline.py` — byte-parity for `content_hash` is preserved.

---

## Summary of what to do

1. Restore WP02 test fixtures from lane-b (Blocker 1).
2. Wire `synthesize()` → `promote()` or document the deferral (Blocker 2).
3. Run `pytest tests/charter/synthesizer/ -q` — expect 170+ green.
4. Run `ruff check src/charter/synthesizer/` — fix the single `UP037`.
5. Re-request review.
