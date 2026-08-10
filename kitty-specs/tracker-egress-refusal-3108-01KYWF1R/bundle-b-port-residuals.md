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

---

## R-6. `tracker bind` cannot be driven end-to-end on the LOCAL path (#3172's class)

Found 2026-08-07 while folding #3174 (the "no over-gating" coverage gap). #3174 asks for the
ungated commands — `status`, `bind`, `unbind`, `map add`, `map list` — to be executed against a
`tracker.egress: refused` fixture. Four of the five are covered by
`TestUS7NoOverGatingUngatedCommandsSurviveRefusal`. **`bind` is not, and cannot be** without
faking a signal unrelated to this mission.

Measured under the acceptance harness's isolated `HOME`:

    tracker bind --provider beads --workspace acme-ws --credential command=... \
        --doctrine-mode spec_kitty_authoritative
    -> exit 1
    spec-kitty tracker: readiness=missing_auth next=spec-kitty-auth-login

Structural cause: `bind_command` calls `_check_readiness(require_mission_binding=False,
probe_reachability=False)` **directly** (`cli/commands/tracker.py:585`). Its siblings
`status` / `map add` / `map list` / `unbind` go through `_check_binding_readiness`, which
short-circuits on `_is_local_binding()` and therefore never reaches the hosted auth probe.
`bind` has no such short-circuit — reasonably, since it is the command that *creates* the
binding `_is_local_binding()` would read, so there is nothing to short-circuit on yet.

The consequence is the same shape #3172 records for the hosted path: a hosted pre-flight
(`saas.readiness._probe_auth` -> `get_token_manager().is_authenticated`) aborts a **local**
`beads` invocation before mission code is reached. A CLI-literal acceptance cell for `bind`
would therefore be satisfied by an `exit 1` that has nothing to do with the egress gate — the
exact false-green class #3172 is filed about.

**Not fixed here.** #3172 is a separate mission and was explicitly out of scope for this fold.
Closing it would mean either giving `bind` a provider-aware short-circuit (it can read
`--provider` before deciding, which `_is_local_binding()` cannot) or making the acceptance
harness fake `get_token_manager` — the latter is a bigger and less honest patch than the
coverage it buys.

The gate is genuinely absent from `bind` regardless: `LocalTrackerService.bind` carries no
`tracker_egress_verdict` call in the re-derived census, and
`test_ungated_commands_consult_no_verdict_binding_while_sync_pull_consults_one` proves zero
verdict calls across the four drivable ungated commands. What is missing is only the *executed*
CLI-literal proof for `bind` specifically.

---

## R-7. `integration-tests-sync` is red on the merge-base, not on this PR

Classified 2026-08-07 while folding #3174/#3110. The job reports **4 errors, 0 failures**, all
FR-007 leak-guard *teardown* errors:

    tests/sync/test_dual_write_integration.py::TestDualWriteEventAndFrontmatterConsistent::test_dual_write_event_and_frontmatter_consistent
    tests/sync/test_dual_write_integration.py::TestDualWriteMultipleTransitions::test_dual_write_multiple_transitions
    tests/sync/test_daemon_self_retirement.py::TestRunSyncDaemonWiring::test_serve_forever_exits_cleanly_when_server_shutdown
    tests/sync/test_daemon_self_retirement.py::TestRunSyncDaemonWiring::test_sigterm_exits_without_deadlocking_server_shutdown

Leaked symbols are `[E26] specify_cli.sync.runtime._runtime` and
`[E27] specify_cli.sync.background._service` (plus two live threads), i.e. the sync runtime and
background-service singletons — nothing in the tracker-egress cone.

**Reproduced byte-identically on pristine main.** The merge-base `709a59534` CI run
(`31128128294`, job `92707752017`) fails `integration-tests-sync` with the *same four node-ids*
and the same leak-guard message: `209 passed, 4 errors`. On this PR: `366 passed, 4 errors` —
the higher pass count is this mission's four new `tests/sync/tracker/` files being selected, not
new failures.

This PR touches **zero** files under `src/specify_cli/sync/` and no `tests/sync/` file other
than the four tracker test files. Separate root cause from the #3110 SC-004 crossing folded in
the same pass; not a PR defect and not this mission's to fix.
