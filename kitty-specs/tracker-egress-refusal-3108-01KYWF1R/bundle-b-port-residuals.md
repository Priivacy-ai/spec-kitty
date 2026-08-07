# Bundle-B port residuals and out-of-scope findings (#3108 / PR #3135)

Ledgered per the mission's residual convention (cf. `tracer-squad-findings.md`). Nothing here
is fixed in this PR; each entry names why it is out of scope and what would close it.

Recorded 2026-08-07, after rebasing `bundle-c-tracker-refusal-3108` onto `upstream/main`
`709a59534` (branch tip `79bd642ed`, 13 ahead / 0 behind) and porting to Bundle B's
`project_egress_refusal(project_root, identifiers)` signature.

---

## R-1. `time.sleep` is patched process-globally in two tracker retry tests (#3136)

**Not this PR.** The PR's `src/` diff contains no line matching `time.sleep` or `retry`.

`tests/sync/tracker/test_saas_client_origin.py::TestSearchIssues::test_429_retries_then_raises`
and `tests/sync/tracker/test_saas_client.py::TestRetryBehaviors::test_429_defaults_to_5s_when_missing`
both decorate with:

    @patch("specify_cli.tracker.saas_client.time.sleep")

`specify_cli.tracker.saas_client.time` **is** the stdlib `time` module object, so this rebinds
`time.sleep` for the whole interpreter, not for the module under test. The resulting `MagicMock`
is therefore a process-global recorder: every `time.sleep` any other live thread performs during
the patch window is counted, and `assert_called_once_with(...)` fails with an inflated count.

CI evidence (run 30895454874, job 91947271031) shows the recorded call list:

    Calls: [call(0.001), call(0.002), call(0.004), call(0.008), call(0.016), call(2.0)]

Only `call(2.0)` belongs to the test. The `0.001 -> 0.016` doubling is an unrelated exponential
backoff loop running concurrently. The sibling test recorded 267 calls of `call(0.05)`.

Both tests pass in a serial, single-process run of `tests/sync/tracker/` (704 passed), which is
consistent with the mechanism: the pollution needs a concurrent sleeper.

**Close by** patching the module-local reference the code actually calls, or by asserting over a
sleep recorder injected into the client, rather than rebinding a stdlib attribute. Owned by #3136.

---

## R-2. Stale nodeid in a frozen CI selection baseline

`tests/architectural/baselines/fast-tests-core-misc-nodeids.txt:8336` reads:

    tests/specify_cli/test_lane_regression_guard.py::test_runtime_no_frontmatter_lane_access[src/specify_cli/tracker/egress_consent.py]

That parametrisation id names `src/specify_cli/tracker/egress_consent.py`, which **Bundle B
deleted upstream**. The nodeid can therefore no longer be generated on `upstream/main` either.

This is a **frozen selection census**, refrozen by
`python -m tests.architectural._gate_coverage --freeze-baselines` (see
`tests/architectural/test_gate_coverage.py`). It is not an orphan created by this PR, and no
executable gate in `tests/`, `src/` or `.github/workflows/` reads this particular file — the
grep for consumers returns only docs and mission dossiers.

**Deliberately not regenerated here.** Refreezing a baseline is how a real selection regression
gets laundered into green, and this PR has no business moving a census it did not change. The
refreeze belongs to whoever lands the Bundle-B deletion follow-up on `main`.

---

## R-3. `lint` job fails on a dependency CVE, not on style

Both `lint` failures are the step **"[ENFORCED] Fail job if security checks failed"**, and the
failing sub-check is `pip-audit`, not `ruff`:

    Found 1 known vulnerability in 1 package
    cryptography 49.0.0  CVE-2026-69247  Fix Versions: 50.0.0

`ruff check src tests` and `ruff check src tests --select TID251` both print `All checks passed!`
in the same job. A dependency bump to `cryptography>=50.0.0` closes it; that is a
repository-wide dependency decision, not a tracker-egress change.

---

## R-4. 32 advisory `mypy --strict` errors on `main`, none in the egress cone

The `lint` job's mypy step is advisory (it sets an output; it does not fail the job). The 32
errors are in four files this PR never touches:

- `src/specify_cli/migration/backfill_runtime_state.py` — 28 errors, all cascading from one
  inference collapse at `:423` (`List comprehension has incompatible type List[object]`), which
  then yields `"object" has no attribute "wp_id"/"event_id"/"actor"/"to_dict"` downstream.
- `src/specify_cli/doc_analysis/doc_state.py:92` — `Redundant cast to "dict[str, Any]"`.
- `src/specify_cli/cli/commands/charter/activate.py:106,:136` — `Redundant cast to "str"`.
- `src/specify_cli/cli/commands/charter/deactivate.py:71` — `Redundant cast to "str"`.

---

## R-5. Environment trap: a user-site editable install shadows this checkout

`/usr/bin/python` resolves `specify_cli` from **another checkout** because of

    /home/jeroennouws/.local/lib/python3.14/site-packages/_editable_impl_spec_kitty_cli.pth
        -> /home/jeroennouws/dev/spec-kitty/src

So `python -c "import specify_cli"` in this worktree imports a different tree, and
`import specify_cli.tracker.egress_consent` *succeeds* there even though Bundle B deleted the
module here. Any local gate run with the bare `python`/`pytest` on `PATH` measures the wrong
source tree.

Use `/home/jeroennouws/dev/sk-missions/3108/.venv/bin/python -m pytest`, which resolves
`specify_cli` from this worktree's `src/` (and correctly raises `ModuleNotFoundError` for the
deleted module). `pytest.ini` sets `pythonpath = src`, so the venv interpreter is sufficient.

This is a workstation-configuration hazard, not a repository defect, but it silently invalidates
measurements and is worth stating where the next agent will look.
