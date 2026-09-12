# Recorded output — FR-011 shard proof (WP13)

This is a companion evidence file to `scripts/verify_shard_3115.sh`, committed
outside the strict `owned_files` singleton (which lists only the script) but
inside the WP's declared `authoritative_surface: scripts/`, per an explicit
instruction to land the recorded output rather than hold it until the end.
It is fully reproducible by re-running the script; it is evidence, not a
substitute for re-running it.

Three real shard runs were taken in this worktree against script commit
`a0ee0f6697`/`2cf0912064` (round 1), summarised further down — they
reconcile identically on every node-id and every collected count; only the
script's own printed "count line" was blank in the first two, a bug fixed
within round 1 itself. Round 2 fixed the exit code not reflecting
ABSENT/FAILED node-ids (proven with a synthetic against real captures,
section below). Round 3 fixed two HIGHs — a vacuous checks-run guard and
four extractors whose absence-sentinels were printed but not folded into
the exit code — proven with one positive and five negative controls against
script commit `d023619789`, and the committed record now contains a real
run of the final script (a disclosed replay against real captures, not a
new shard) rather than a transcript that predates the fixes it should
demonstrate.

## A second bug, found in review: the script's own exit code did not reflect ABSENT/FAILED node-ids

Independent review found that `report_node_outcome` returned non-zero on an
absent node-id, but every one of its 7 call sites piped the result into
`while … log`, and the resulting exit status was never captured — only the
zero-collection guard fed the script-global `FAIL`, so a run in which every
one of the 13 node-ids was absent, or every one had FAILED/ERROR verdicts,
would still `exit 0`. The absences/failures would be *printed* (satisfying
T041's letter), but the exit code — what a CI wiring would actually read —
would say PASS regardless. Fixed:

- `report_node_outcome` now also inspects the matched line(s) for a
  `[gwK] [ N%] …` verdict line and returns non-zero if that verdict is
  `FAILED`/`ERROR`, not only on ABSENT — a node-id that PASSED at call time
  but ERRORed at teardown (exactly WP05's leak-guard shape) is correctly
  treated as not-a-clean-pass now, where it previously was not.
- A new `check_node` wrapper runs the same `report_node_outcome | while …`
  pipeline, captures its exit status (via `set -o pipefail`, verified
  empirically to propagate the leftmost failing stage's status through a
  trailing `while` that itself exits 0), and folds any non-zero result into
  the script-global `FAIL`. All 7 call sites now go through `check_node`.
- `FAIL=0` is initialised exactly once, before the first thing that can set
  it, and never reset afterwards. The zero-collection guard's own pass/fail
  state was split into a separate `COLLECTION_FAIL` so its own "both shards
  collected" message stays accurate to what it claims, independent of
  whether a node-id check already set the overall `FAIL`.
- `run_shard`'s return value (0, or 3 on an empty output file) is now
  checked with `if ! run_shard …` and folds into `FAIL` too — previously
  captured into `SYNC_RC`/`CLI_RC` and never read again.

**Proven bidirectionally with a cheap synthetic**, sourcing the script's own
function definitions against a real captured run file
(`out/reports/probe-run3/sync.out`) rather than re-running any shard:

```
--- test A: a real, known-PASSED node-id ---
    tests/sync/tracker/test_saas_client.py::TestRetryBehaviors::test_429_respects_retry_after
    [gw5] [ 42%] PASSED tests/sync/tracker/test_saas_client.py::TestRetryBehaviors::test_429_respects_retry_after
FAIL after test A: 0

--- test B: a deliberately bogus/absent node-id ---
    ABSENT (no line in the run's output mentions this node-id)
FAIL after test B: 1

--- test C: a real node-id that PASSED at call time but ERRORed at teardown (leak-guard shape) ---
    tests/sync/test_lifecycle_readiness.py::test_init_emits_project_init_event_offline
    [gw7] [ 93%] PASSED tests/sync/test_lifecycle_readiness.py::test_init_emits_project_init_event_offline
    [gw7] [ 93%] ERROR tests/sync/test_lifecycle_readiness.py::test_init_emits_project_init_event_offline
    [FR-007 leak guard] tests/sync/test_lifecycle_readiness.py::test_init_emits_project_init_event_offline left inventoried process-global state dirty (…)
    ERROR tests/sync/test_lifecycle_readiness.py::test_init_emits_project_init_event_offline
FAIL after test C: 1
```

Test A proves the fix does not regress the common case (a real pass leaves
`FAIL` at 0). Test B proves the exit code now reflects an absence. Test C
proves it also now reflects a node-id that looked like a pass by its call
line alone but was not — the exact case `report_node_outcome`'s old
"any hit at all" logic would have missed.

## Round 3 — two HIGHs, the same defect this mission investigates, in its own proof artefact

Independent review round 3 found that the round-2 fixes above were sound
(re-derived end-to-end, confirmed no subshell scope loss, no `set -e`
swallow, `exit "${FAIL}"` consulted) but flagged two new HIGHs: the PASS
verdict never stated how many T041 checks it ran, and every extractor's
failure sentinel was printed without being folded into the exit code. Both
are the "mechanism reporting success for having done nothing" shape this
mission exists to name, found this time in the mission's own certifying
script. Fixed in commit `d023619789`.

### HIGH-1 — the checks-run guard

Measured (by the reviewer, reproduced here): stripping all 7 `check_node`
call sites while leaving `check_node` and everything downstream intact
previously produced an identical `PASS` verdict and `exit 0` with **zero**
node-id checks run. Fixed: `check_node` increments a script-global
`CHECKS_RUN` on every invocation; `EXPECTED_CHECKS=17` (1+1+3+1+7+3+1,
matching the 17 individual `check_node` calls across the 13 T041 rows) is
declared `readonly` immediately above the node-id list; a new "checks-run
guard" section fails loudly if `CHECKS_RUN < EXPECTED_CHECKS`; the verdict
line now quotes `N/17`.

### HIGH-2 — four extractors, folded into `FAIL`

- `extract_count_line` had no sentinel and no non-zero return at all — a
  blank count line (this already happened once, see "count-line extraction
  bugfix" above) printed `NO COUNT LINE FOUND IN OUTPUT` and the script
  still exited 0.
- `extract_plugins_header` used `grep … || echo "NO … FOUND"` per line,
  which always returns the `echo`'s exit code (0), never the `grep`'s — the
  sentinel text was correct, the function's own return code was not.
- `extract_worker_header` and `extract_gw_range` already returned non-zero
  correctly; every call site discarded that status regardless (bare
  `$(…)` assignment, or an unread pipeline).

All four fixed: each returns non-zero on absence; every call site now
captures that status immediately (`$?` after a `$(…)` assignment, or the
pipefail-backed pipeline exit for the two piped into `while … log` — the
same mechanism `check_node` already proved in round 2) and folds it into
`FAIL`, printing an explicit "folded into overall exit status" line
distinguishing this from a merely-printed gap.

### Six controls — one positive, five negative, all via a stub-interpreter replay

Methodology (disclosed in full, matching what the round-2 reviewer used):
`PYTHON` is pointed at a small bash stub
(`/tmp/…/replay/stub_python.sh`, not committed — a throwaway harness, not
part of the deliverable) that intercepts only `-m pytest` invocations and
`cat`s a pre-selected file to stdout instead of running real pytest;
any other invocation (the interpreter-probe heredoc at the top of the
script) is delegated unchanged to the real `.venv/bin/python`. This lets
the **actual, unmodified, committed script** run end-to-end — every
function, every section, the real `exit` at the end — against real
captured pytest bytes, in seconds rather than the ~12 minutes a real shard
pair takes, with **no new shard executed**. The base captures are
`out/reports/probe-run3/{sync,cli}.out` from the integration-probe
measurement (SHA `eef820144f`, unchanged, not re-run).

**Positive control** — unmodified captures, script commit `d023619789`:
```
=== checks-run guard (HIGH-1: erosion hazard for the T041 list) ===
OK: 17/17 T041 node-id checks executed.
...
=== overall verdict ===
PASS: both shards ran, both collected non-zero, 17/17
  T041 node-id checks executed and every one resolved to a PASSED
  verdict line with no FAILED/ERROR/ABSENT among them, and both
  shards' plugins-header and worker-header evidence was present.
```
`EXIT: 0`. (Full transcript below, "Committed-script replay".)

**Five negative controls**, each doctoring exactly one piece of evidence out
of a copy of the real `sync.out` capture (cli.out left real/unmodified in
every case), quoted exit codes:

| doctor | what was removed | verdict line printed | exit |
|---|---|---|---|
| A | the `N workers [M items]` header line | `worker header : NO gw/workers HEADER FOUND IN OUTPUT` | **1** |
| B | the final `N passed, …` summary line | `NO COUNT LINE FOUND IN OUTPUT` | **1** |
| C | the `[gwK] ` prefix from every verdict line | `NO [gwK] TAGS FOUND IN OUTPUT` (plus 4 T041 node-id checks correctly flip to `NO VERDICT LINE`, since the same prefix backs both) | **1** |
| D | the `platform …` / `plugins: …` lines | `NO 'platform' LINE FOUND` / `NO 'plugins:' LINE FOUND` | **1** |
| E | all 7 `check_node` call sites (neutralised to `:` no-ops in a scratch copy of the script, not the committed one) | `FAIL: only 0/17 T041 node-id checks were executed.` | **1** |

Doctor C's collateral effect (breaking 4 node-id verdict matches as well as
the `gw_range` extractor) is expected, not a bug: both draw the `^\[gw[0-9]+\]`
prefix from the same lines, so corrupting it degrades both signals
together — a stronger result than an isolated failure would have been.

### MEDIUM-1 — the committed recorded output now contains a real run of the committed script

Round 3 found the prior "Run 3" transcript below was byte-identical to
`out/reports/shard-3115-run3/summary.txt`, which predates both the
plugins-header block and the `=== overall verdict ===` section — so the
committed record contained no run of the committed script, no `PASS`/`FAIL`
line, no exit code. Corrected in round 3 with a replay transcript; **round
4 found that transcript itself was hand-condensed in four places** (a
reworded LOW-4 cross-reference, an abbreviated `--ignore` list, a
compressed `cli shard — declared invocation` line, and the 17-line
reconciliation replaced by a one-line summary) — not false in any of the
four, but not the verbatim bytes a code fence labelled "full transcript"
implies either. **Corrected here: the transcript below is pasted verbatim**,
re-generated after the LOW-c fix (`-ne`, commit `fd1d540180`) rather than
re-editing the round-3 bytes, so it is simultaneously the fidelity fix and
the required re-run-after-script-change.

**Committed-script replay — full, verbatim transcript** (script commit
`fd1d540180`, captures `out/reports/probe-run3/{sync,cli}.out` — md5
`f8d9fbfcf26758e4c1eb65e9d786455b` / `c1795f6937b03ef7779aff29ffd6b85d`,
confirmed unchanged since round 2 — stub interpreter, no new shard run).
Pasted byte-for-byte from the script's own stdout, with only trailing
whitespace on a few lines stripped by this document's own markdown
rendering (invisible either way). Three lines legitimately differ from a
real (non-replay) run and are not edited out: `python:`/`command:` show the
stub interpreter's path rather than `.venv/bin/python`, and `output:`/the
`output file:` lines show this replay's scratch directory rather than
`out/reports/…` — both are direct, disclosed consequences of the replay
methodology (see above), not something a real invocation would print. Two
distinct sources of `sys.executable`/`plugins:` text appear: the top
"interpreter and import path" block is a **live** invocation of the real
`.venv/bin/python` made during this replay itself (the stub delegates any
non-`-m pytest` call unchanged); the `platform …`/`plugins: …` lines inside
each shard's own section are extracted from the **captures'** file content
(what the real `.venv/bin/python` printed when `probe-run3` was originally
produced):

```
=== FR-011 shard proof: interpreter and import path ===
sys.executable / sys.version / plugins11 registry (quoted, not inferred):
  sys.executable = /home/jeroennouws/dev/spec-kitty/.venv/bin/python
  sys.version    = 3.11.15
  pytest11 registry (9): anyio, asyncio, base_url, playwright, pytest_cov, respx, timeout, xdist, xdist.looponfail
  PYTHONPATH     = /home/jeroennouws/dev/spec-kitty/.worktrees/verification-trust-3115-01KYVYWM-lane-l/src
  SPEC_KITTY_TEST_DB_NAME = test_verification_trust_3115_01KYVYWM_replay
  repo root      = /home/jeroennouws/dev/spec-kitty/.worktrees/verification-trust-3115-01KYVYWM-lane-l

=== FR-011 shard proof — 2026-08-01T12:52:41Z ===
repo root: /home/jeroennouws/dev/spec-kitty/.worktrees/verification-trust-3115-01KYVYWM-lane-l
python:    /tmp/claude-1000/-home-jeroennouws-dev-sk-missions/8a17c880-ddcf-4679-bd75-3a525b8d5203/scratchpad/wp13/replay/stub_python.sh
output:    /tmp/claude-1000/-home-jeroennouws-dev-sk-missions/8a17c880-ddcf-4679-bd75-3a525b8d5203/scratchpad/wp13/replay/out_positive_r4

--- running shard: sync (fast-tests-sync) ---
start (UTC): 2026-08-01T12:52:41Z
command: /tmp/claude-1000/-home-jeroennouws-dev-sk-missions/8a17c880-ddcf-4679-bd75-3a525b8d5203/scratchpad/wp13/replay/stub_python.sh -u -m pytest tests/sync/ -m fast and not windows_ci -v --tb=short --ignore=tests/sync/test_orphan_sweep.py --ignore=tests/sync/test_daemon_orphan_classification.py --ignore=tests/sync/test_daemon_cleanup_boundary.py --ignore=tests/sync/test_issue_1071_singleton_reconfirmation.py -n auto --dist loadfile --durations=50 --cov=src/specify_cli/sync
end   (UTC): 2026-08-01T12:52:41Z
pytest's own exit code: 0 (informational only — the collected
  count and the count line below are the evidence, not this number)
output file: /tmp/claude-1000/-home-jeroennouws-dev-sk-missions/8a17c880-ddcf-4679-bd75-3a525b8d5203/scratchpad/wp13/replay/out_positive_r4/sync.out (4462 lines)

sync shard — pytest's own platform/plugins header (NFR-001, versioned, OBSERVED):
  platform linux -- Python 3.11.15, pytest-9.0.3, pluggy-1.6.0 -- /home/jeroennouws/dev/spec-kitty/.venv/bin/python
  plugins: anyio-4.13.0, xdist-3.8.0, timeout-2.4.0, cov-7.1.0, asyncio-1.3.0, respx-0.23.1, base-url-2.1.0, playwright-0.8.0
sync shard — distribution OBSERVED from the run's own report (NFR-001):
  worker header : 8 workers [2124 items]
  gw tags seen  :
    [gw0] [gw1] [gw2] [gw3] [gw4] [gw5] [gw6] [gw7]
      (8 distinct workers actually used)
  collected     :
    8 workers [2124 items]
  count line    :
    ====== 2112 passed, 12 skipped, 1 warning, 12 errors in 284.58s (0:04:44) ======
sync shard — declared invocation (this script's own constants, matching
  the argv logged above as "command: …"; NOT independently re-derived
  or re-measured from the run — see LOW-4 in the recorded-output note):
  --dist        : loadfile
  marker        : -m "fast and not windows_ci"
  --ignore (4)  : tests/sync/test_orphan_sweep.py,
                  tests/sync/test_daemon_orphan_classification.py,
                  tests/sync/test_daemon_cleanup_boundary.py,
                  tests/sync/test_issue_1071_singleton_reconfirmation.py
  --cov         : ON (--cov=src/specify_cli/sync)
--- running shard: cli (fast-tests-cli) ---
start (UTC): 2026-08-01T12:52:41Z
command: /tmp/claude-1000/-home-jeroennouws-dev-sk-missions/8a17c880-ddcf-4679-bd75-3a525b8d5203/scratchpad/wp13/replay/stub_python.sh -u -m pytest tests/cli/ tests/specify_cli/cli/ -m fast and not windows_ci -v --tb=short -n auto --dist loadfile --durations=50 --cov=src/specify_cli/cli
end   (UTC): 2026-08-01T12:52:41Z
pytest's own exit code: 1 (informational only — the collected
  count and the count line below are the evidence, not this number)
output file: /tmp/claude-1000/-home-jeroennouws-dev-sk-missions/8a17c880-ddcf-4679-bd75-3a525b8d5203/scratchpad/wp13/replay/out_positive_r4/cli.out (6138 lines)

cli shard — pytest's own platform/plugins header (NFR-001, versioned, OBSERVED):
  platform linux -- Python 3.11.15, pytest-9.0.3, pluggy-1.6.0 -- /home/jeroennouws/dev/spec-kitty/.venv/bin/python
  plugins: anyio-4.13.0, xdist-3.8.0, timeout-2.4.0, cov-7.1.0, asyncio-1.3.0, respx-0.23.1, base-url-2.1.0, playwright-0.8.0
cli shard — distribution OBSERVED from the run's own report (NFR-001):
  worker header : 8 workers [2917 items]
  gw tags seen  :
    [gw0] [gw1] [gw2] [gw3] [gw4] [gw5] [gw6] [gw7]
      (8 distinct workers actually used)
  collected     :
    8 workers [2917 items]
  count line    :
    =========== 1 failed, 2916 passed, 66 warnings in 453.48s (0:07:33) ============
cli shard — declared invocation (this script's own constants, matching
  the argv logged above as "command: …"; NOT independently re-derived
  or re-measured from the run — see LOW-4 in the recorded-output note):
  --dist        : loadfile
  marker        : -m "fast and not windows_ci"
  --ignore      : (none — ci-quality.yml's cli shard carries no --ignore)
  --cov         : ON (--cov=src/specify_cli/cli)

=== per-node-id reconciliation (T041/T042) ===

[1] tests/cli/commands/test_sync_status_per_project_3030.py::test_status_names_every_project_with_count_age_and_consent
    tests/cli/commands/test_sync_status_per_project_3030.py::test_status_names_every_project_with_count_age_and_consent
    [gw1] [ 94%] PASSED tests/cli/commands/test_sync_status_per_project_3030.py::test_status_names_every_project_with_count_age_and_consent

[2] tests/cli/commands/test_sync_doctor_per_project_3030.py::test_doctor_names_every_project_with_count_age_and_consent
    tests/cli/commands/test_sync_doctor_per_project_3030.py::test_doctor_names_every_project_with_count_age_and_consent
    [gw7] [ 84%] PASSED tests/cli/commands/test_sync_doctor_per_project_3030.py::test_doctor_names_every_project_with_count_age_and_consent

[3-6] tests/cli/commands/test_sync_doctor_consent_health_3030.py — issue says 4 param
      cases; the file's only parametrisation
      (test_doctor_names_the_action_for_each_project_local_fault_kind) collects 3.
      Reconciliation: reporting the 3 actual param-case outcomes, not inventing a 4th.
    case: test_doctor_names_the_action_for_each_project_local_fault_kind[unparseable-project:
      tests/cli/commands/test_sync_doctor_consent_health_3030.py::test_doctor_names_the_action_for_each_project_local_fault_kind[unparseable-project:\n  uuid: [unclosed\n-REPAIR THE FILE'S SYNTAX]
      [gw4] [ 63%] PASSED tests/cli/commands/test_sync_doctor_consent_health_3030.py::test_doctor_names_the_action_for_each_project_local_fault_kind[unparseable-project:\n  uuid: [unclosed\n-REPAIR THE FILE'S SYNTAX]
    case: test_doctor_names_the_action_for_each_project_local_fault_kind[wrong_shape-
      tests/cli/commands/test_sync_doctor_consent_health_3030.py::test_doctor_names_the_action_for_each_project_local_fault_kind[wrong_shape-- one\n- two\n-MAKE THE DOCUMENT A MAPPING]
      [gw4] [ 63%] PASSED tests/cli/commands/test_sync_doctor_consent_health_3030.py::test_doctor_names_the_action_for_each_project_local_fault_kind[wrong_shape-- one\n- two\n-MAKE THE DOCUMENT A MAPPING]
    case: test_doctor_names_the_action_for_each_project_local_fault_kind[unusable-
      tests/cli/commands/test_sync_doctor_consent_health_3030.py::test_doctor_names_the_action_for_each_project_local_fault_kind[unusable-project:\n  uuid: aaaaaaaa-0000-0000-0000-000000000001\nsync:\n  enabled: "false"\n-CORRECT THE FIELD VALUE]
      [gw4] [ 63%] PASSED tests/cli/commands/test_sync_doctor_consent_health_3030.py::test_doctor_names_the_action_for_each_project_local_fault_kind[unusable-project:\n  uuid: aaaaaaaa-0000-0000-0000-000000000001\nsync:\n  enabled: "false"\n-CORRECT THE FIELD VALUE]

[7] tests/cli/commands/test_sync_migrate_backfills_h4.py::test_the_consent_backfill_reports_records_it_could_not_resolve
    tests/cli/commands/test_sync_migrate_backfills_h4.py::test_the_consent_backfill_reports_records_it_could_not_resolve
    [gw6] [ 80%] PASSED tests/cli/commands/test_sync_migrate_backfills_h4.py::test_the_consent_backfill_reports_records_it_could_not_resolve

[8-9] tests/cli/commands/test_sync_purge_3030.py::TestPurgeAll — issue says 2; the
      class collects 7. Reconciliation: running/reporting all 7, not guessing which 2.
    case: TestPurgeAll::test_apply_all_without_the_confirmation_phrase_deletes_nothing
      tests/cli/commands/test_sync_purge_3030.py::TestPurgeAll::test_apply_all_without_the_confirmation_phrase_deletes_nothing
      [gw1] [ 40%] PASSED tests/cli/commands/test_sync_purge_3030.py::TestPurgeAll::test_apply_all_without_the_confirmation_phrase_deletes_nothing
    case: TestPurgeAll::test_apply_all_with_the_wrong_phrase_deletes_nothing
      tests/cli/commands/test_sync_purge_3030.py::TestPurgeAll::test_apply_all_with_the_wrong_phrase_deletes_nothing
      [gw1] [ 40%] PASSED tests/cli/commands/test_sync_purge_3030.py::TestPurgeAll::test_apply_all_with_the_wrong_phrase_deletes_nothing
    case: TestPurgeAll::test_confirmed_all_empties_the_machine_global_stores_and_this_checkout
      tests/cli/commands/test_sync_purge_3030.py::TestPurgeAll::test_confirmed_all_empties_the_machine_global_stores_and_this_checkout
      [gw1] [ 40%] PASSED tests/cli/commands/test_sync_purge_3030.py::TestPurgeAll::test_confirmed_all_empties_the_machine_global_stores_and_this_checkout
    case: TestPurgeAll::test_all_reaches_the_body_rows_no_targeted_selector_could
      tests/cli/commands/test_sync_purge_3030.py::TestPurgeAll::test_all_reaches_the_body_rows_no_targeted_selector_could
      [gw1] [ 41%] PASSED tests/cli/commands/test_sync_purge_3030.py::TestPurgeAll::test_all_reaches_the_body_rows_no_targeted_selector_could
    case: TestPurgeAll::test_the_all_dry_run_predicts_exactly_what_the_confirmed_run_deletes
      tests/cli/commands/test_sync_purge_3030.py::TestPurgeAll::test_the_all_dry_run_predicts_exactly_what_the_confirmed_run_deletes
      [gw1] [ 41%] PASSED tests/cli/commands/test_sync_purge_3030.py::TestPurgeAll::test_the_all_dry_run_predicts_exactly_what_the_confirmed_run_deletes
    case: TestPurgeAll::test_all_names_the_per_checkout_scope_and_claims_nothing_wider
      tests/cli/commands/test_sync_purge_3030.py::TestPurgeAll::test_all_names_the_per_checkout_scope_and_claims_nothing_wider
      [gw1] [ 42%] PASSED tests/cli/commands/test_sync_purge_3030.py::TestPurgeAll::test_all_names_the_per_checkout_scope_and_claims_nothing_wider
    case: TestPurgeAll::test_help_does_not_promise_machine_wide_erasure
      tests/cli/commands/test_sync_purge_3030.py::TestPurgeAll::test_help_does_not_promise_machine_wide_erasure
      [gw1] [ 42%] PASSED tests/cli/commands/test_sync_purge_3030.py::TestPurgeAll::test_help_does_not_promise_machine_wide_erasure

[10-12] tests/sync/test_consent_write_refusal_3030.py::test_a_refused_write_is_reported_rather_than_raised_out_of_the_cli
        — the only 3-wide parametrisation in the file (opt-in / opt-out / server).
    case: test_a_refused_write_is_reported_rather_than_raised_out_of_the_cli[opt-in]
      tests/sync/test_consent_write_refusal_3030.py::test_a_refused_write_is_reported_rather_than_raised_out_of_the_cli[opt-in]
      [gw6] [ 43%] PASSED tests/sync/test_consent_write_refusal_3030.py::test_a_refused_write_is_reported_rather_than_raised_out_of_the_cli[opt-in]
    case: test_a_refused_write_is_reported_rather_than_raised_out_of_the_cli[opt-out]
      tests/sync/test_consent_write_refusal_3030.py::test_a_refused_write_is_reported_rather_than_raised_out_of_the_cli[opt-out]
      [gw6] [ 44%] PASSED tests/sync/test_consent_write_refusal_3030.py::test_a_refused_write_is_reported_rather_than_raised_out_of_the_cli[opt-out]
    case: test_a_refused_write_is_reported_rather_than_raised_out_of_the_cli[server]
      tests/sync/test_consent_write_refusal_3030.py::test_a_refused_write_is_reported_rather_than_raised_out_of_the_cli[server]
      [gw6] [ 45%] PASSED tests/sync/test_consent_write_refusal_3030.py::test_a_refused_write_is_reported_rather_than_raised_out_of_the_cli[server]

[13] tests/sync/tracker/test_saas_client.py::TestRetryBehaviors::test_429_respects_retry_after
     (the sync half's own case; per notes/sleep-count-attribution.md this node-id has
     never itself exhibited the #3115/sleep-count failure — reported regardless.)
    tests/sync/tracker/test_saas_client.py::TestRetryBehaviors::test_429_respects_retry_after
    [gw5] [ 42%] PASSED tests/sync/tracker/test_saas_client.py::TestRetryBehaviors::test_429_respects_retry_after

=== checks-run guard (HIGH-1: erosion hazard for the T041 list) ===
OK: 17/17 T041 node-id checks executed.

=== zero-collection guard ===
OK: sync shard collected 2124 tests (non-zero).
OK: cli shard collected 2917 tests (non-zero).

=== NFR-008: input counts beside any all-checks-passed claim ===
sync shard input count: 2124
cli shard input count:  2917

Both shards collected a non-zero number of tests
(sync=2124, cli=2917). This is NOT a claim that
all tests passed — see the count lines and per-node-id reconciliation above
for the actual outcomes. A caller must read those, not this guard, to know
whether the 13 node-ids passed.

=== overall verdict ===
PASS: both shards ran, both collected non-zero, 17/17
  T041 node-id checks executed and every one resolved to a PASSED
  verdict line with no FAILED/ERROR/ABSENT among them, and both
  shards' plugins-header and worker-header evidence was present.

=== done ===
sync shard wall-clock window and cli shard wall-clock window are both printed
above (start/end, UTC) so a same-machine collision with any other test run is
reconstructable (NFR-004).
```
`EXIT: 0`.

## Interpreter and import path (identical for all three runs)
```
=== FR-011 shard proof: interpreter and import path ===
sys.executable / sys.version / plugins11 registry (quoted, not inferred):
  sys.executable = /home/jeroennouws/dev/spec-kitty/.venv/bin/python
  sys.version    = 3.11.15
  pytest11 registry (9): anyio, asyncio, base_url, playwright, pytest_cov, respx, timeout, xdist, xdist.looponfail
  PYTHONPATH     = /home/jeroennouws/dev/spec-kitty/.worktrees/verification-trust-3115-01KYVYWM-lane-l/src
  SPEC_KITTY_TEST_DB_NAME = test_verification_trust_3115_01KYVYWM_lane_l
  repo root      = /home/jeroennouws/dev/spec-kitty/.worktrees/verification-trust-3115-01KYVYWM-lane-l
```

**Correction — NFR-001's `plugins:` header, distinct from the registry above.**
The `pytest11 registry` printed above is the *installed* entry-point set
(names only, no versions) — useful, but not what NFR-001 names. NFR-001 says
explicitly the claim "quotes the run's own `plugins:` header", which is a
different line pytest prints once per run, inside `sync.out`/`cli.out`
themselves, with versions:

```
platform linux -- Python 3.11.15, pytest-9.0.3, pluggy-1.6.0 -- /home/jeroennouws/dev/spec-kitty/.venv/bin/python
plugins: anyio-4.13.0, xdist-3.8.0, timeout-2.4.0, cov-7.1.0, asyncio-1.3.0, respx-0.23.1, base-url-2.1.0, playwright-0.8.0
```

(Identical for `sync.out` and `cli.out`, all three lane-l runs and all three
probe runs.) `out/reports/*/sync.out` and `.../cli.out` are excluded by
`.gitignore:183`, so this line previously existed only in files this
repository does not track. The script now extracts and prints these two
lines itself (`extract_plugins_header`, logged right after each shard run),
so a future committed recorded-output carries the line NFR-001 names,
without needing to commit the full raw run files.

## Run 3 — STALE, historical, superseded by the committed-script replay above

**This transcript predates the round-3 fixes** (no plugins-header block, no
`=== overall verdict ===` line, no `CHECKS_RUN`) — it is round 1's actual
script output, kept for the historical record of that round's real shard
run, not as current evidence. The "Committed-script replay" transcript
above is the current record of the committed script's own output.

```
=== FR-011 shard proof — 2026-08-01T10:48:07Z ===
repo root: /home/jeroennouws/dev/spec-kitty/.worktrees/verification-trust-3115-01KYVYWM-lane-l
python:    /home/jeroennouws/dev/spec-kitty/.venv/bin/python
output:    out/reports/shard-3115-run3

--- running shard: sync (fast-tests-sync) ---
start (UTC): 2026-08-01T10:48:07Z
command: /home/jeroennouws/dev/spec-kitty/.venv/bin/python -u -m pytest tests/sync/ -m fast and not windows_ci -v --tb=short --ignore=tests/sync/test_orphan_sweep.py --ignore=tests/sync/test_daemon_orphan_classification.py --ignore=tests/sync/test_daemon_cleanup_boundary.py --ignore=tests/sync/test_issue_1071_singleton_reconfirmation.py -n auto --dist loadfile --durations=50 --cov=src/specify_cli/sync
end   (UTC): 2026-08-01T10:52:07Z
pytest's own exit code: 0 (informational only — the collected
  count and the count line below are the evidence, not this number)
output file: out/reports/shard-3115-run3/sync.out (4359 lines)

sync shard — distribution actually observed (NFR-001):
  worker header : 8 workers [2119 items]
  gw tags seen  :
    [gw0] [gw1] [gw2] [gw3] [gw4] [gw5] [gw6] [gw7] 
      (8 distinct workers actually used)
  --dist        : loadfile
  marker        : -m "fast and not windows_ci"
  --ignore (4)  : tests/sync/test_orphan_sweep.py,
                  tests/sync/test_daemon_orphan_classification.py,
                  tests/sync/test_daemon_cleanup_boundary.py,
                  tests/sync/test_issue_1071_singleton_reconfirmation.py
  --cov         : ON (--cov=src/specify_cli/sync)
  collected     :
    8 workers [2119 items]
  count line    :
    =========== 2108 passed, 11 skipped, 1 warning in 239.08s (0:03:59) ============
--- running shard: cli (fast-tests-cli) ---
start (UTC): 2026-08-01T10:52:07Z
command: /home/jeroennouws/dev/spec-kitty/.venv/bin/python -u -m pytest tests/cli/ tests/specify_cli/cli/ -m fast and not windows_ci -v --tb=short -n auto --dist loadfile --durations=50 --cov=src/specify_cli/cli
end   (UTC): 2026-08-01T10:59:53Z
pytest's own exit code: 1 (informational only — the collected
  count and the count line below are the evidence, not this number)
output file: out/reports/shard-3115-run3/cli.out (6130 lines)

cli shard — distribution actually observed (NFR-001):
  worker header : 8 workers [2913 items]
  gw tags seen  :
    [gw0] [gw1] [gw2] [gw3] [gw4] [gw5] [gw6] [gw7] 
      (8 distinct workers actually used)
  --dist        : loadfile
  marker        : -m "fast and not windows_ci"
  --ignore      : (none — ci-quality.yml's cli shard carries no --ignore)
  --cov         : ON (--cov=src/specify_cli/cli)
  collected     :
    8 workers [2913 items]
  count line    :
    =========== 1 failed, 2912 passed, 66 warnings in 465.01s (0:07:45) ============

=== per-node-id reconciliation (T041/T042) ===

[1] tests/cli/commands/test_sync_status_per_project_3030.py::test_status_names_every_project_with_count_age_and_consent
    tests/cli/commands/test_sync_status_per_project_3030.py::test_status_names_every_project_with_count_age_and_consent 
    [gw7] [ 94%] PASSED tests/cli/commands/test_sync_status_per_project_3030.py::test_status_names_every_project_with_count_age_and_consent 

[2] tests/cli/commands/test_sync_doctor_per_project_3030.py::test_doctor_names_every_project_with_count_age_and_consent
    tests/cli/commands/test_sync_doctor_per_project_3030.py::test_doctor_names_every_project_with_count_age_and_consent 
    [gw7] [ 84%] PASSED tests/cli/commands/test_sync_doctor_per_project_3030.py::test_doctor_names_every_project_with_count_age_and_consent 

[3-6] tests/cli/commands/test_sync_doctor_consent_health_3030.py — issue says 4 param
      cases; the file's only parametrisation
      (test_doctor_names_the_action_for_each_project_local_fault_kind) collects 3.
      Reconciliation: reporting the 3 actual param-case outcomes, not inventing a 4th.
    case: test_doctor_names_the_action_for_each_project_local_fault_kind[unparseable-project:
      tests/cli/commands/test_sync_doctor_consent_health_3030.py::test_doctor_names_the_action_for_each_project_local_fault_kind[unparseable-project:\n  uuid: [unclosed\n-REPAIR THE FILE'S SYNTAX] 
      [gw0] [ 63%] PASSED tests/cli/commands/test_sync_doctor_consent_health_3030.py::test_doctor_names_the_action_for_each_project_local_fault_kind[unparseable-project:\n  uuid: [unclosed\n-REPAIR THE FILE'S SYNTAX] 
    case: test_doctor_names_the_action_for_each_project_local_fault_kind[wrong_shape-
      tests/cli/commands/test_sync_doctor_consent_health_3030.py::test_doctor_names_the_action_for_each_project_local_fault_kind[wrong_shape-- one\n- two\n-MAKE THE DOCUMENT A MAPPING] 
      [gw0] [ 63%] PASSED tests/cli/commands/test_sync_doctor_consent_health_3030.py::test_doctor_names_the_action_for_each_project_local_fault_kind[wrong_shape-- one\n- two\n-MAKE THE DOCUMENT A MAPPING] 
    case: test_doctor_names_the_action_for_each_project_local_fault_kind[unusable-
      tests/cli/commands/test_sync_doctor_consent_health_3030.py::test_doctor_names_the_action_for_each_project_local_fault_kind[unusable-project:\n  uuid: aaaaaaaa-0000-0000-0000-000000000001\nsync:\n  enabled: "false"\n-CORRECT THE FIELD VALUE] 
      [gw0] [ 63%] PASSED tests/cli/commands/test_sync_doctor_consent_health_3030.py::test_doctor_names_the_action_for_each_project_local_fault_kind[unusable-project:\n  uuid: aaaaaaaa-0000-0000-0000-000000000001\nsync:\n  enabled: "false"\n-CORRECT THE FIELD VALUE] 

[7] tests/cli/commands/test_sync_migrate_backfills_h4.py::test_the_consent_backfill_reports_records_it_could_not_resolve
    tests/cli/commands/test_sync_migrate_backfills_h4.py::test_the_consent_backfill_reports_records_it_could_not_resolve 
    [gw3] [ 81%] PASSED tests/cli/commands/test_sync_migrate_backfills_h4.py::test_the_consent_backfill_reports_records_it_could_not_resolve 

[8-9] tests/cli/commands/test_sync_purge_3030.py::TestPurgeAll — issue says 2; the
      class collects 7. Reconciliation: running/reporting all 7, not guessing which 2.
    case: TestPurgeAll::test_apply_all_without_the_confirmation_phrase_deletes_nothing
      tests/cli/commands/test_sync_purge_3030.py::TestPurgeAll::test_apply_all_without_the_confirmation_phrase_deletes_nothing 
      [gw1] [ 40%] PASSED tests/cli/commands/test_sync_purge_3030.py::TestPurgeAll::test_apply_all_without_the_confirmation_phrase_deletes_nothing 
    case: TestPurgeAll::test_apply_all_with_the_wrong_phrase_deletes_nothing
      tests/cli/commands/test_sync_purge_3030.py::TestPurgeAll::test_apply_all_with_the_wrong_phrase_deletes_nothing 
      [gw1] [ 40%] PASSED tests/cli/commands/test_sync_purge_3030.py::TestPurgeAll::test_apply_all_with_the_wrong_phrase_deletes_nothing 
    case: TestPurgeAll::test_confirmed_all_empties_the_machine_global_stores_and_this_checkout
      tests/cli/commands/test_sync_purge_3030.py::TestPurgeAll::test_confirmed_all_empties_the_machine_global_stores_and_this_checkout 
      [gw1] [ 40%] PASSED tests/cli/commands/test_sync_purge_3030.py::TestPurgeAll::test_confirmed_all_empties_the_machine_global_stores_and_this_checkout 
    case: TestPurgeAll::test_all_reaches_the_body_rows_no_targeted_selector_could
      tests/cli/commands/test_sync_purge_3030.py::TestPurgeAll::test_all_reaches_the_body_rows_no_targeted_selector_could 
      [gw1] [ 40%] PASSED tests/cli/commands/test_sync_purge_3030.py::TestPurgeAll::test_all_reaches_the_body_rows_no_targeted_selector_could 
    case: TestPurgeAll::test_the_all_dry_run_predicts_exactly_what_the_confirmed_run_deletes
      tests/cli/commands/test_sync_purge_3030.py::TestPurgeAll::test_the_all_dry_run_predicts_exactly_what_the_confirmed_run_deletes 
      [gw1] [ 41%] PASSED tests/cli/commands/test_sync_purge_3030.py::TestPurgeAll::test_the_all_dry_run_predicts_exactly_what_the_confirmed_run_deletes 
    case: TestPurgeAll::test_all_names_the_per_checkout_scope_and_claims_nothing_wider
      tests/cli/commands/test_sync_purge_3030.py::TestPurgeAll::test_all_names_the_per_checkout_scope_and_claims_nothing_wider 
      [gw1] [ 41%] PASSED tests/cli/commands/test_sync_purge_3030.py::TestPurgeAll::test_all_names_the_per_checkout_scope_and_claims_nothing_wider 
    case: TestPurgeAll::test_help_does_not_promise_machine_wide_erasure
      tests/cli/commands/test_sync_purge_3030.py::TestPurgeAll::test_help_does_not_promise_machine_wide_erasure 
      [gw1] [ 42%] PASSED tests/cli/commands/test_sync_purge_3030.py::TestPurgeAll::test_help_does_not_promise_machine_wide_erasure 

[10-12] tests/sync/test_consent_write_refusal_3030.py::test_a_refused_write_is_reported_rather_than_raised_out_of_the_cli
        — the only 3-wide parametrisation in the file (opt-in / opt-out / server).
    case: test_a_refused_write_is_reported_rather_than_raised_out_of_the_cli[opt-in]
      tests/sync/test_consent_write_refusal_3030.py::test_a_refused_write_is_reported_rather_than_raised_out_of_the_cli[opt-in] 
      [gw0] [ 45%] PASSED tests/sync/test_consent_write_refusal_3030.py::test_a_refused_write_is_reported_rather_than_raised_out_of_the_cli[opt-in] 
    case: test_a_refused_write_is_reported_rather_than_raised_out_of_the_cli[opt-out]
      tests/sync/test_consent_write_refusal_3030.py::test_a_refused_write_is_reported_rather_than_raised_out_of_the_cli[opt-out] 
      [gw0] [ 47%] PASSED tests/sync/test_consent_write_refusal_3030.py::test_a_refused_write_is_reported_rather_than_raised_out_of_the_cli[opt-out] 
    case: test_a_refused_write_is_reported_rather_than_raised_out_of_the_cli[server]
      tests/sync/test_consent_write_refusal_3030.py::test_a_refused_write_is_reported_rather_than_raised_out_of_the_cli[server] 
      [gw0] [ 47%] PASSED tests/sync/test_consent_write_refusal_3030.py::test_a_refused_write_is_reported_rather_than_raised_out_of_the_cli[server] 

[13] tests/sync/tracker/test_saas_client.py::TestRetryBehaviors::test_429_respects_retry_after
     (the sync half's own case; per notes/sleep-count-attribution.md this node-id has
     never itself exhibited the #3115/sleep-count failure — reported regardless.)
    tests/sync/tracker/test_saas_client.py::TestRetryBehaviors::test_429_respects_retry_after 
    [gw5] [ 47%] PASSED tests/sync/tracker/test_saas_client.py::TestRetryBehaviors::test_429_respects_retry_after 
    0.12s call     tests/sync/tracker/test_saas_client.py::TestRetryBehaviors::test_429_respects_retry_after

=== zero-collection guard ===
OK: sync shard collected 2119 tests (non-zero).
OK: cli shard collected 2913 tests (non-zero).

=== NFR-008: input counts beside any all-checks-passed claim ===
sync shard input count: 2119
cli shard input count:  2913

Both shards collected a non-zero number of tests
(sync=2119, cli=2913). This is NOT a claim that
all tests passed — see the count lines and per-node-id reconciliation above
for the actual outcomes. A caller must read those, not this guard, to know
whether the 13 node-ids passed.

=== done ===
sync shard wall-clock window and cli shard wall-clock window are both printed
above (start/end, UTC) so a same-machine collision with any other test run is
reconstructable (NFR-004).
```

## SC-009 — run twice, each run's collected count quoted

| run | sync collected | sync count line | cli collected | cli count line |
|---|---|---|---|---|
| 1 (2026-08-01T10:21:10Z) | 2119 | 2108 passed, 11 skipped, 1 warning in 226.02s | 2913 | 1 failed, 2912 passed, 66 warnings in 463.96s |
| 2 (2026-08-01T10:34:08Z) | 2119 | 2108 passed, 11 skipped, 1 warning in 226.59s | 2913 | 1 failed, 2912 passed, 66 warnings in 479.37s |
| 3 (2026-08-01T10:48:07Z) | 2119 | 2108 passed, 11 skipped, 1 warning in 239.08s | 2913 | 1 failed, 2912 passed, 66 warnings in 465.01s |

All three runs: identical collected counts, identical pass/fail split, and all
13 T041 node-ids/groups PASSED in every run.

## The one cli-shard failure, all three runs — not one of the 13, and named

`tests/specify_cli/cli/commands/test_charter_widen_integration.py::TestGetMissionId::test_returns_none_if_json_malformed`

Traceback root: `json.decoder.JSONDecodeError` propagates out of
`_get_mission_id` (`src/specify_cli/cli/commands/charter/_widen.py:55`) via
`placement_seam(...).read_dir()` / `resolve_artifact_surface` instead of being
caught and turned into `None`. This is the same defect family as the disclosed
pre-existing failure `test_charter_io::test_get_mission_id_returns_none_when_meta_json_malformed`
(same function, same malformed-JSON contract), reached from a second test file
not literally named in the WP's pre-existing-failures list. Not one of the 13
FR-011 node-ids/groups; not attributable to WP05's leak guard (tests/sync-scoped,
this is a tests/specify_cli/cli failure); not attributable to #3115. Named here,
not chased, not fixed.

## SUPERSEDED — the "0 failures vs #3130" note above was a vacuous baseline

**Correction, same day.** The lane-l tree measured above contains none of the
mission's own fixes: `grep -c "FR-007 leak guard" tests/sync/conftest.py` was
**0** and `grep -c "_RENDER_WIDTH" tests/conftest.py` was **0** in that tree —
WP05's leak guard and WP02's render-width seam are not merge-completed onto
any lane branch; each lane only holds its own work, and "approved" does not
mean "merged". So "0 failures observed" above was not evidence the guard
produces 0 reds — it was evidence the guard was **absent**. The 13 T041
node-ids passing on that tree was correspondingly a baseline (those node-ids
fail only under `TERM=dumb FORCE_COLOR=1`, which this shard does not set),
not a fixed-tree confirmation. Superseded by the integration-probe
measurement below, which re-runs the identical shard proof on a tree that
actually contains all twelve lanes' work.

## Integration probe — a throwaway branch built from all 12 lane tips

**Probe branch**: `wp13/integration-probe`, cut from `feat/verification-trust-3115`
(base commit `771ba7fd6c`) in a dedicated worktree
(`.worktrees/wp13-integration-probe`, outside this lane), then merged with
`kitty/mission-verification-trust-3115-01KYVYWM-lane-{a..l}` in sequence.
Every merge conflict was on `kitty-specs/verification-trust-3115-01KYVYWM/status.json`
(the dossier's live status file, updated independently by each lane's
tooling) and was resolved with `git checkout --ours` (favouring `feat`'s
copy, since lanes are not authoritative over the dossier — C-010). No
non-dossier conflicts occurred across all 12 merges.

**Final probe SHA**: `eef820144f9e8e3299da51d191b925066662b65b`. **Not merged
into `feat/verification-trust-3115` or the mission branch** — the probe
branch and its worktree are throwaway, kept only for this measurement's
reproducibility.

### Integration verified before measuring anything (quoted, not assumed)

```
$ grep -c "FR-007 leak guard" tests/sync/conftest.py
8
$ grep -c "_RENDER_WIDTH" tests/conftest.py
4
$ ls scripts/mutants/
attribute_sleep_count_3115.py
disable_render_seam_3115.py
hang_a_fast_test_3115.py
neutralise_reset_token_manager_3115.py
nonterminating_dispatch_3115.py
$ ls tests/architectural/test_cli_console_render_width.py
tests/architectural/test_cli_console_render_width.py
$ ls scripts/repro_3115_render_width.sh
scripts/repro_3115_render_width.sh
```

All checks positive: WP05's leak guard, WP02's render-width seam, all four
(plus a fifth, `attribute_sleep_count_3115.py`) mutants, the render-width
architectural guard, and WP01's reproducer are all present on the probe
tree. This is a real subject for the measurement, not a second vacuous one.

### Same script, same flags, three runs on the probe tree

Interpreter identical to the lane-l runs above: `sys.executable = .venv/bin/python`
(3.11.15), `plugins11` registry (9): `anyio, asyncio, base_url, playwright,
pytest_cov, respx, timeout, xdist, xdist.looponfail`. `PYTHONPATH` pinned to
the probe worktree's own `src/` (verified `specify_cli.__file__` resolves
there, not the main checkout). `SPEC_KITTY_TEST_DB_NAME=test_verification_trust_3115_01KYVYWM_probe`.

**Sync shard** — identical invocation to the lane-l runs (`tests/sync/ -m
"fast and not windows_ci" -v --tb=short --ignore=…×4 -n auto --dist loadfile
--durations=50 --cov=src/specify_cli/sync`). Worker header (all 3 runs):
**`8 workers [2124 items]`**, gw0..gw7 (8 distinct).

| run | sync count line |
|---|---|
| 1 | `2112 passed, 12 skipped, 1 warning, 12 errors in 300.44s` |
| 2 | `2112 passed, 12 skipped, 1 warning, 12 errors in 295.88s` |
| 3 | `2112 passed, 12 skipped, 1 warning, 12 errors in 284.58s` |

**CLI shard** — identical invocation (`tests/cli/ tests/specify_cli/cli/ -m
"fast and not windows_ci" -v --tb=short -n auto --dist loadfile
--durations=50 --cov=src/specify_cli/cli`). Worker header (all 3 runs):
**`8 workers [2917 items]`**, gw0..gw7.

| run | cli count line |
|---|---|
| 1 | `1 failed, 2916 passed, 66 warnings in 456.71s` |
| 2 | `1 failed, 2916 passed, 66 warnings in 437.16s` |
| 3 | `1 failed, 2916 passed, 66 warnings in 453.48s` |

Collected counts on the probe tree are slightly higher than on lane-l alone
(2124 vs 2119 sync; 2917 vs 2913 cli) — the merged-in lanes each add a small
number of new tests (e.g. WP01's reproducer, WP02's seam tests, WP03's
mutants). **All 13 T041 node-ids/groups PASSED in every one of the 3 runs**
— identical outcome to the lane-l-only measurement, now on a tree that
actually contains the fixes.

### The `#3130` question, answered with a real figure

**12 errors, by node-id, identical across all 3 runs**, every one tagged
`[FR-007 leak guard]` in its own teardown-error text (quoted, not inferred):

1. `test_issue_598_hang_fixes.py::TestBackgroundStopBounded::test_stop_does_not_hang_when_sync_is_slow`
2. `test_issue_598_hang_fixes.py::TestBackgroundStopBounded::test_stop_emits_structured_warning_when_sync_times_out`
3. `test_runtime.py::TestSyncRuntime::test_starts_background_service`
4. `test_runtime.py::TestUnauthenticatedBehavior::test_no_websocket_when_unauthenticated`
5. `test_target_authority.py::test_all_fields_populated_under_env_equals_config`
6. `test_background_body.py::TestTimerBodyQueue::test_timer_triggers_when_only_body_queue_has_tasks`
7. `test_background_body.py::TestTimerBodyQueue::test_timer_skips_when_both_queues_empty`
8. `test_background_body.py::TestRuntimeLifecycle::test_start_creates_body_queue`
9. `test_background_body.py::TestRuntimeLifecycle::test_shared_db_path`
10. `test_target_authority_wiring.py::test_readiness_host_config_keys_off_resolved_target`
11. `test_lifecycle_readiness.py::test_init_emits_project_init_event_offline`
12. `tracker/test_saas_client_consent_gate_3030.py::test_mission_creation_bind_transmits_for_a_consenting_project`

**Cross-check against `#3130`'s own list (fetched via `gh issue view 3130`)**:
`#3130` names 11 base node-ids plus states "two more … appear only under
`--dist loadfile`" (`test_target_authority_wiring.py::test_readiness_host_config_keys_off_resolved_target`
and `test_background.py::TestSingletonAccessor::test_get_sync_service_returns_same_instance`).
All 11 base node-ids matched exactly (1:1, same node-ids, same order of
discovery). Of the two `--dist loadfile`-only extras, **only one** appeared
in any of my 3 runs (`test_target_authority_wiring.py`) — `11 + 1 = 12`,
matching the measured count. `test_background.py::TestSingletonAccessor::test_get_sync_service_returns_same_instance`
**passed in all 3 runs**, quoted:

```
tests/sync/test_background.py::TestSingletonAccessor::test_get_sync_service_returns_same_instance
[gw5] [ 68%] PASSED tests/sync/test_background.py::TestSingletonAccessor::test_get_sync_service_returns_same_instance   (run 1: gw5; run 2: gw6; run 3: gw5)
```

**Correction — this is not a discrepancy from `#3130`'s summary sentence,
and it is precise about which of `#3130`'s two statements it is consistent
with.** `#3130` makes two statements about this pair, of different
strength. Its **summary** says "1–2 more that appear only under `--dist
loadfile`" — a hedged range; observing exactly one of the two is *inside*
that range. Its **body** is stronger and more specific: *"Two more … Under
`loadfile` they land in separate workers, each with a clean baseline, **so
both are flagged** — and both are correct."* That is a definite claim of
two, not a range. **This measurement (one of two, three runs out of three)
is consistent with the summary's hedged range and is not consistent with
the body's specific "both are flagged" claim.** The first version of this
note cited only the summary and read the outcome as within-range without
naming that the body says something stronger and different; corrected here.

**What was checked, and what remains genuinely open.** `#3130`'s body
attributes this pair's exposure to `--dist loadfile` landing the polluter
and victim in *separate* workers with clean baselines. Checked directly,
per run, by worker:

| run | worker | immediate predecessor file on that worker |
|---|---|---|
| 1 | `gw5` | `tests/sync/test_body_integration.py` |
| 2 | `gw6` | `tests/sync/test_body_integration.py` |
| 3 | `gw5` | `tests/sync/test_emitter_mission_id.py` |

(An earlier version of this table conflated the three runs into one
sentence naming both files for all three; corrected — run 3's predecessor
is `test_emitter_mission_id.py`, not `test_body_integration.py`, though the
conclusion below is unaffected.) `test_background.py` did **not** land with
a clean baseline in any of the 3 runs; a different, unflagged file ran on
the same worker immediately before it every time. That is a plausible,
specific reason the already-dirty-before-snapshot suppression `#3130`'s
body describes could stay live via an unnamed predecessor, consistent with
(not contradicting) `#3130`'s own mechanism. Also unnamed until now:
`-n auto` resolved to **8** workers in this sandbox, against CI's 4-vCPU
runner — a different worker count changes loadfile's file-to-worker
assignment directly, so this environment's assignment is not expected to
match CI's. Not established: whether either factor is *the* reason, or
whether CI's own 4-worker assignment would expose the second
extra. Both are named, neither is resolved.

### Three-way attribution (the point of this round)

- **WP05 leak guard (expected, `#3130`)**: 12 sync-shard errors, all
  `[FR-007 leak guard]`-tagged, matching all 11 of `#3130`'s base node-ids
  plus 1 of its 2 `--dist loadfile`-only extras — consistent with `#3130`'s
  **summary** sentence's hedged "1–2" range, and **not** consistent with
  its **body**'s more specific "both are flagged" claim (see the full
  correction above). Not chased to green.
- **`#3115` itself**: **0** observed reds, on either shard, in any of the 3
  probe runs. This bullet previously rested on node-id 13
  (`test_saas_client.py::TestRetryBehaviors::test_429_respects_retry_after`),
  which the same evidence file concedes has never itself exhibited the
  failure — a non-discriminating case. The nodes that *do* exhibit `#3115`'s
  sleep-count failure are `#3136`'s, and both passed, quoted directly from
  the run files:
  ```
  [gw5] [ 35%] PASSED tests/sync/tracker/test_saas_client.py::TestPolling::test_exponential_backoff_intervals
  [gw1] [ 71%] PASSED tests/sync/tracker/test_saas_client_origin.py::TestSearchIssues::test_429_retries_then_raises
  ```
  (run 1 line numbers/workers shown; both passed identically in runs 2 and 3
  — `gw4`/`gw5` and `gw5`/`gw1` respectively.) This is consistent with the
  mission's own established finding (`#3136`, deferred): the sync-side
  sleep-count failure is CI-load/thread-contention-dependent
  (`subprocess.Popen._wait` busy-wait racing under real concurrency) and
  WP06's own floor could not reproduce it locally either (9 of 10 local
  selections passed). A local probe passing on the real discriminating nodes
  is **favourable but still not proof `#3115` is fixed** — it is consistent
  with the deferred, load-dependent state already on record, not a
  substitute for a CI-load reproduction. **Separately, on the CLI half**:
  the CLI-side node-ids (rows 1–9 above) are known to fail only under
  `TERM=dumb FORCE_COLOR=1` (FR-001), which this shard does not set — WP02's
  render-width seam being present on the probe tree makes the *tree* a real
  subject, but does not make *this shard invocation* a discriminating
  instrument for the CLI half specifically. Their PASSED verdicts here are
  baseline behaviour, not a fixed-tree confirmation, for that reason alone
  (independent of the tree/lane-l distinction above).
- **Pre-existing, neither guard nor `#3115`**: **1** — the cli shard's
  `test_charter_widen_integration.py::TestGetMissionId::test_returns_none_if_json_malformed`,
  identical across all 3 probe runs and identical to the 3 lane-l-only runs.
  Same defect family as the disclosed `test_charter_io::…malformed`
  pre-existing failure, from a second file. Named, not chased.

No contamination observed between the three categories: the 12 leak-guard
errors are all teardown-phase `ERROR`s carrying the guard's own tag; the
1 pre-existing failure is a collection-phase `FAILED` in a disjoint shard
(cli, not sync) with an unrelated traceback (`JSONDecodeError`, not a
process-global-state assertion); and the 13 target node-ids are clean of
both.

**No CI job claim is made anywhere in this file.** The shard *labels*
(`fast-tests-sync`, `fast-tests-cli`) name the CI jobs whose configuration
this script copies — they are not claims that those jobs ran, and no CI
workflow run exists for probe SHA `eef820144f` (it was never pushed; the
probe branch/worktree are local and throwaway). Every count and outcome
above is from a local run of this script, not from GitHub Actions.

### Three CI deviations, not one — listed together for honesty

Only the `-v`-for-`-q` swap was disclosed in the script's own comments
before this round. Two more exist and were not previously listed together:

1. **`-v` instead of `-q`** (disclosed in the script, `verify_shard_3115.sh`
   lines 349-367 as of commit `d023619789` — corrected from an earlier,
   already-stale "~245-263" citation; the line numbers moved when the
   HIGH-1/HIGH-2 fixes were added above this block) — required to get the
   worker-count header and per-node-id verdict lines at all;
   selection/dist/marker/`--cov` unchanged.
2. **Interpreter and install method.** CI pins `python-version: '3.12'` and
   runs via `uv sync --frozen --all-extras` then `uv run python -m pytest
   …`. This script ran **Python 3.11.15** from the repo's `.venv` via
   `PYTHONPATH`, per this mission's own binding instruction (standing-rules.md's
   interpreter clause: `.venv/bin/python`, not a bare interpreter, because
   `pytest-timeout`/`xdist` are only registered there). Not a discretionary
   choice made by this script — but still a real difference from CI's
   3.12/`uv`-managed environment, stated plainly.
3. **`--cov-report=xml:…` dropped.** Both CI shard commands carry
   `--cov-report=xml:out/reports/coverage/coverage-fast-{sync,cli}.xml`;
   this script runs `--cov=…` (so `--cov`'s scheduling-affecting behaviour,
   per NFR-001, is reproduced) but does not write the XML report, since
   nothing in this WP consumes it. Test selection, distribution and pass/fail
   outcomes are unaffected by the report *format*; only the coverage-tracing
   presence (`--cov` on/off) matters for NFR-001, and that is unchanged.
