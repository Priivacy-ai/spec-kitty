# Cone attribution — per node id, `tests/sync` + `tests/architectural`

**Mission:** `chain-b-consent-bypass-3167-01KZ63HK` · **Work package:** WP03 · **Requirements:** FR-005, FR-006, NFR-003, NFR-004, C-005
**Measured:** 2026-08-04 · **Branch:** `feat/chain-b-consent-bypass-3167` · **Working path:** the repository **root checkout** `/home/jeroennouws/dev/sk-missions/3167` (`git worktree list` shows only the root checkout; no lane worktree exists, and WP01/WP02 both worked there)

This file is the `NFR-003` deliverable: **one row per node id** in the pre/post delta of the two swept
cones, each with a cause. Row count equals the delta line count and both are printed. A bulk sentence
("all differences are due to the deletion") is not an attribution and is not offered here.

## Arms, and what each one is

| Arm | Tree | Purpose |
|---|---|---|
| `base` | `f04ee0a78` = `b0482a832^` — WP02's base commit | the "pre" side of the delta |
| `mid` | `df3541c3c` — WP02 landed, WP03 not yet applied | isolates WP02's effect from WP03's |
| `post` | `mid` + WP03's T012/T014/C-006 changes | the "post" side of the delta |

`base` was materialized in the root checkout with `git checkout f04ee0a78 -- src tests`, and restored
from a `trap` (WP01 recorded losing a control to `set -e` aborting before its restore). **Two mechanical
gotchas were hit and are recorded because a re-measurer will hit them too:**

* that command does **not** delete files added *after* the base commit, so
  `tests/architectural/test_batch_drain_retired_3167.py` (added by `b0482a832`) had to be moved aside —
  the first base collection reported `arch=1591` instead of `1587` and would have hidden 4 nodes from
  the delta by counting them on both sides;
* it leaves files *deleted* by `b0482a832` staged as `A`, so the restore needs `git rm`, not only
  `git checkout HEAD --`. Restoration was verified with `git status --porcelain -- src tests` (empty)
  and `git diff HEAD --stat -- src tests` (empty) before any measurement was trusted.

## Collection-level delta (T015) — the input counts, printed

```
base  f04ee0a78   tests/sync 2395   tests/architectural 1587   total 3982
mid   df3541c3c   tests/sync 2306   tests/architectural 1589   total 3895
post  WP03        tests/sync 2308   tests/architectural 1589   total 3897
```

`base` `tests/sync` = **2395** reproduces `analysis-report.md` §4's committed input count exactly
(2376 passed + 19 skipped), which is what makes the comparison below trustworthy at all.

```
base -> post   ABSENT 91   NEW 6    (delta line count = 97)
mid  -> post   ABSENT  0   NEW 2    (WP03's own collection effect)
```

**WP03's own collection effect is `+2` and nothing else.** No node was lost, and no node id changed —
so the `batch` seam removal (T012) is collection-neutral across the ~106 files the autouse fixture
reaches, exactly as the prompt predicted. Had it not been, something other than `sync/batch.py` would
have depended on that seam and this WP would have stopped and reported.

## Outcome-level arms (T016) — the run table, N per arm

| Arm | N | Command | `passed / skipped / errors` per run | error node-id sets |
|---|---|---|---|---|
| `base` = `b0482a832^` | **5** (recorded, NOT re-measured here) | as `analysis-report.md` §4 | `2376 / 19 / {5,5,6,6,6}`, input 2395 | 5-node stable floor, plus 0–1 of the 4 nodes proven volatile at both commits |
| `post` | **5** clean (+1 contaminated, disclosed) | `.venv/bin/python -m pytest tests/sync -n0 -ra -p no:cacheprovider --timeout=300` (redirected) | see below | see below |

> **⚠️ CORRECTED at the pre-merge pass — the post-arm band as recorded below is NOT reproducible.**
> An independent lens ran the cone twice more at HEAD and got **5** errors both times, error set exactly
> the 5-node floor, with **zero** volatile nodes. So:
>
> - The post arm is **`{5, 6}`**, not `{6,6,6,6,6}` — n=7 across both measurers.
> - "Exactly one volatile node per run, never two" is **falsified downward**: zero is also observed.
>   Restate as **"zero or one volatile node above the five-node floor"**.
> - What survives, and is the load-bearing claim: **the five-node floor reproduced in every clean run at
>   both commits**, and no error in any run implicates a file this mission owns.
> - This makes the earlier disclosure ("did not return to baseline") **more pessimistic than the tree
>   actually is**, so it is not a regression — but a band that does not reproduce is still a number
>   reported without checking what it counts.
>
> Also unrecorded and worth naming: each of that lens's runs leaked a `run_sync_daemon` child that
> outlived the sweep on port 9400, and `pkill -f 'run_sync[_]daemon'` did **not** clear it — only `-9`
> did. **The recorded reap procedure needs SIGKILL.**

The base arm is **not** re-derived. `analysis-report.md` §4 records it at n=5 and this WP's prompt
directs the implementer to use that enumeration rather than re-measure it; re-deriving it would have
cost four more full sweeps to reproduce a distribution already in the dossier. **This is a stated
dependency on someone else's measurement, not an independent confirmation of it.**

### Post-arm runs, individually

| Run | `passed / skipped / errors` | `^ERROR tests/` | `^ERROR ` (over-counting form) | usable |
|---|---|---|---|---|
| 1 | `2289 passed, 19 skipped, 1 warning, 6 errors in 199.61s (0:03:19)` | 6 | 7 | yes |
| 2 | `1 failed, 2288 passed, 19 skipped, 1 warning, 5 errors in 149.29s (0:02:29)` | 5 | 5 | no — see disclosure |
| 3 | `2289 passed, 19 skipped, 1 warning, 6 errors in 204.49s (0:03:24)` | 6 | 6 | yes |
| 4 | `2289 passed, 19 skipped, 1 warning, 6 errors in 189.49s (0:03:09)` | 6 | 6 | yes |
| 5 | `2289 passed, 19 skipped, 1 warning, 6 errors in 202.85s (0:03:22)` | 6 | 6 | yes |
| 6 | `2289 passed, 19 skipped, 1 warning, 6 errors in 185.05s (0:03:05)` | 6 | 7 | yes |

`^ERROR tests/` vs `^ERROR ` is not a stylistic preference — run 1 shows the two forms disagreeing
(6 vs 7) in a single transcript. The extra line the loose form counts is a captured-log record:

```
ERROR    specify_cli.sync.background:background.py:369 Refusing to start background sync: 5 legacy
queue event row(s) remain that no drain will deliver. ...
```

### Per-node-id set difference, post arm vs the recorded base arm

| Node id | runs observed | in base arm? |
|---|---|---|
| `tests/sync/test_background.py::TestSingletonAccessor::test_get_sync_service_returns_same_instance` | [3, 5] of 5 | VOLATILE (proven both arms) |
| `tests/sync/test_background.py::TestSingletonAccessor::test_reset_clears_singleton` | [4] of 5 | VOLATILE (proven both arms) |
| `tests/sync/test_daemon_self_retirement.py::TestRunSyncDaemonWiring::test_serve_forever_exits_cleanly_when_server_shutdown` | [1, 3, 4, 5, 6] of 5 | FLOOR (both arms) |
| `tests/sync/test_daemon_self_retirement.py::TestRunSyncDaemonWiring::test_sigterm_exits_without_deadlocking_server_shutdown` | [1, 3, 4, 5, 6] of 5 | FLOOR (both arms) |
| `tests/sync/test_dual_write_integration.py::TestDualWriteEventAndFrontmatterConsistent::test_dual_write_event_and_frontmatter_consistent` | [1, 3, 4, 5, 6] of 5 | FLOOR (both arms) |
| `tests/sync/test_dual_write_integration.py::TestDualWriteMultipleTransitions::test_dual_write_multiple_transitions` | [1, 3, 4, 5, 6] of 5 | FLOOR (both arms) |
| `tests/sync/test_legacy_queue_guard_3030.py::TestARefusedStartLeavesNoDeadSingleton::test_get_sync_service_does_not_cache_a_service_that_failed_to_start` | [1, 6] of 5 | VOLATILE (proven both arms) |
| `tests/sync/test_lifecycle_readiness.py::test_init_emits_project_init_event_offline` | [1, 3, 4, 5, 6] of 5 | FLOOR (both arms) |

**The 5-node stable floor reproduced in every clean post-arm run.** Floor nodes not observed: none. That matters for `C-004`: had a floor node stopped, the
`test_lifecycle_readiness` pin would have had to come off with an attribution. None did, so nothing
was un-pinned.

**Every non-floor error node carries exactly one dirty line, and it is the volatile shape.** Checked
per node rather than per run — a first pass that grepped a window around the node name concatenated a
neighbouring floor node's `spec-kitty-sync-runtime-start` line (a named thread with a resolvable
target) onto a volatile node and briefly looked like a second, unexplained leak shape. It was a grep
artifact. Per-node extraction:

```
run 1  test_legacy_queue_guard_3030 ...failed_to_start   - live thread name='Thread-87' target=None
run 3  test_background ...returns_same_instance           - live thread name='Thread-7'  target=None
run 4  test_background ...test_reset_clears_singleton     - live thread name='Thread-9'  target=None
run 5  test_background ...returns_same_instance           - live thread name='Thread-7'  target=None
run 6  test_legacy_queue_guard_3030 ...failed_to_start    - live thread name='Thread-87' target=None
```

One volatile node per run, never two, and the node moves while the count does not — which is exactly
`Priivacy-ai/spec-kitty#3193`'s "the observer moves; the leak does not". The fourth node on the
already-proven-volatile list
(`test_daemon_self_retirement.py::TestStartSelfCheckTick::test_returned_timer_thread_is_daemon`) was
**not** observed in any of these 5 runs. That is the same phenomenon, not evidence it was fixed.

### Pin ledger, post arm

`10 ACCEPTED (#3130) + 1 UNOBSERVABLE this run + 1 partial-match error = 12` in every clean run —
identical to the ledger `analysis-report.md` §4 records at base. The three entries in this mission's
cone:

| `_PinnedLeak` entry | Base arm | Post arm | Action |
|---|---|---|---|
| `test_lifecycle_readiness.py::test_init_emits_project_init_event_offline` | partial-match ERROR in the full serial sweep, passes in isolation | same, 5/5 runs | **none** — pre-existing; its `[E26]` observability comes from an unpinned leak in `tests/sync/test_dual_write_integration.py`, a file this mission does not own |
| `test_runtime.py::TestSyncRuntime::test_starts_background_service` | `ACCEPTED` | `ACCEPTED`, 5/5 runs | **none** |
| `test_runtime.py::TestUnauthenticatedBehavior::test_no_websocket_when_unauthenticated` | `ACCEPTED` | `ACCEPTED`, 5/5 runs | **none** |

**No pin was added, widened, removed or re-pinned.** The registry is semantically identical to
`b0482a832` — verified by an AST probe comparing `(node_id, markers, issue, kwargs)` for all 12 entries
on both sides. The probe's input count is printed (12 vs 12) because its first version matched only
`ast.Assign` and missed the annotated `_PINNED_LEAKS: tuple[...] = (...)`, returning `0 == 0` — a
vacuous "identical" that would have proved nothing.

The three entries moved line numbers, because C-006's residual note is inserted above each:
`:371 -> :420`, `:389 -> :442`, `:395 -> :452`. Any further edit to `_leak_guard.py` moves them again;
cite them by node id where possible.

## Disclosures — what is NOT established here

1. **The base arm was not re-measured.** It is taken from `analysis-report.md` §4 at n=5
   (`{5,5,6,6,6}`), per this WP's explicit instruction to use that enumeration rather than re-derive
   it. Every base-arm figure in this file is therefore a dependency on another measurer's work, not an
   independent confirmation. If that enumeration is wrong, so is this comparison.
2. **Post-arm run 2 is contaminated and excluded.** It reported `1 failed` —
   `test_leak_guard_probe_3115.py::test_leak_guard_bites_a_synthetic_leak_via_subprocess`, asserting
   `'FR-007 leak guard' in ''`. The nested subprocess produced **empty output**, the signature of a
   killed process; the sweep wrapper died at the same moment without writing its own log lines, so
   something external reaped `pytest`-matching command lines mid-run. A killed run is neither a pass
   nor a fail: the file was re-run narrowed (`2 passed, 1 skipped`, EXIT=0), and run 2 is reported but
   not counted. Its error set was the 5-node floor and nothing else.
3. **Two rows deviate from the requested shape, and are not forced to fit.** The prompt's row status
   vocabulary is `ABSENT|FLIPPED` and its cause set has no member for *added* nodes. Six nodes are
   NEW (collected in `post`, absent in `base`): 4 are WP02/T005's permanence guard and 2 are WP03/T014's
   controls. They are recorded with status `NEW`, and the 4 guard nodes are attributed to
   `RETIRED-BY-T007` with the subtask column naming `WP02/T005`, because inventing an
   `ADDED-BY-T005` cause would be widening a closed set on my own authority. Flagged rather than hidden.
4. **Out-of-tree importers of `specify_cli.sync.batch` remain unexcluded**, as WP01's manifest §5
   already disclosed. Nothing in this WP narrows that gap.

## The delta, one row per node id

**Delta line count: 91 ABSENT + 6 NEW + 3 FLIPPED = 100.**
**Row count below: 100.** Both printed, so the equality is checkable rather than asserted.

Causes are drawn from the closed set `{RETIRED-BY-T007, FIXTURE-UNBLIND-T012, GUARD-STRENGTHEN-T014,
LEAK-PIN-T016, NOT-CAUSED-BY-THIS-MISSION}`. Two honest deviations from the requested shape are
flagged rather than papered over, and both are described in the disclosure section at the end.

### FLIPPED — present in both arms, outcome differs

| Node id | Status | Cause | Subtask |
|---|---|---|---|
| `tests/sync/test_background.py::TestSingletonAccessor::test_get_sync_service_returns_same_instance` | FLIPPED | NOT-CAUSED-BY-THIS-MISSION — volatile band, already proven to fire at BOTH `b0482a832^` and `b0482a832` (analysis-report.md §4). Observed in run(s) [3, 5] of 5; absent in the rest. Single shape `live thread name='Thread-N' target=None`; producers `sync/daemon.py:687,:715,:745` (`_ChainedTimer`) and `sync/background.py:528` (`threading.Timer`) — no file this mission owns. `Priivacy-ai/spec-kitty#3193`. | T016 |
| `tests/sync/test_background.py::TestSingletonAccessor::test_reset_clears_singleton` | FLIPPED | NOT-CAUSED-BY-THIS-MISSION — volatile band, already proven to fire at BOTH `b0482a832^` and `b0482a832` (analysis-report.md §4). Observed in run(s) [4] of 5; absent in the rest. Single shape `live thread name='Thread-N' target=None`; producers `sync/daemon.py:687,:715,:745` (`_ChainedTimer`) and `sync/background.py:528` (`threading.Timer`) — no file this mission owns. `Priivacy-ai/spec-kitty#3193`. | T016 |
| `tests/sync/test_legacy_queue_guard_3030.py::TestARefusedStartLeavesNoDeadSingleton::test_get_sync_service_does_not_cache_a_service_that_failed_to_start` | FLIPPED | NOT-CAUSED-BY-THIS-MISSION — volatile band, already proven to fire at BOTH `b0482a832^` and `b0482a832` (analysis-report.md §4). Observed in run(s) [1, 6] of 5; absent in the rest. Single shape `live thread name='Thread-N' target=None`; producers `sync/daemon.py:687,:715,:745` (`_ChainedTimer`) and `sync/background.py:528` (`threading.Timer`) — no file this mission owns. `Priivacy-ai/spec-kitty#3193`. | T016 |

### NEW — collected in `post`, not collected in `base`

| Node id | Status | Cause | Subtask |
|---|---|---|---|
| `tests/architectural/test_batch_drain_retired_3167.py::test_live_batch_symbols_are_still_visible` | NEW | RETIRED-BY-T007 (permanence guard landed with the retirement) | WP02/T005 |
| `tests/architectural/test_batch_drain_retired_3167.py::test_no_transmit_primitive_remains_in_batch` | NEW | RETIRED-BY-T007 (permanence guard landed with the retirement) | WP02/T005 |
| `tests/architectural/test_batch_drain_retired_3167.py::test_retired_drain_symbols_are_absent` | NEW | RETIRED-BY-T007 (permanence guard landed with the retirement) | WP02/T005 |
| `tests/architectural/test_batch_drain_retired_3167.py::test_watch_list_still_matches_the_frozen_manifest` | NEW | RETIRED-BY-T007 (permanence guard landed with the retirement) | WP02/T005 |
| `tests/sync/test_no_queue_drain_constructed_3030.py::test_scanner_flags_a_synthetic_reintroduction` | NEW | GUARD-STRENGTHEN-T014 | WP03/T014 |
| `tests/sync/test_no_queue_drain_constructed_3030.py::test_the_scan_is_non_vacuous` | NEW | GUARD-STRENGTHEN-T014 | WP03/T014 |

### ABSENT — collected in `base`, not collected in `post`

All 91 are the test nodes WP02/T007 retired alongside the queue-backed senders they
covered. The cause is enumerated per node id rather than stated as a set, because a cause covering a
set that does not name its members is not an attribution. Per-file counts, which must sum to
91:

| File | ABSENT nodes |
|---|---|
| `tests/sync/test_batch_sync.py` | 37 |
| `tests/sync/test_batch_error_surfacing.py` | 26 |
| `tests/sync/test_offline_replay.py` | 11 |
| `tests/sync/test_integration.py` | 7 |
| `tests/sync/test_batch_retry_hygiene.py` | 6 |
| `tests/architectural/test_batch_split_single_authority.py` | 2 |
| `tests/sync/test_batch_400_no_details_poison_2736.py` | 2 |
| **total** | **91** |

| Node id | Status | Cause | Subtask |
|---|---|---|---|
| `tests/architectural/test_batch_split_single_authority.py::test_shrink_delegates_to_shared_split_authority` | ABSENT | RETIRED-BY-T007 | WP02/T007 |
| `tests/architectural/test_batch_split_single_authority.py::test_shrink_uses_plain_split_not_create_aware` | ABSENT | RETIRED-BY-T007 | WP02/T007 |
| `tests/sync/test_batch_400_no_details_poison_2736.py::TestWholeBatch400NoDetailsIsTransient::test_no_details_400_does_not_reject_or_bump_innocents` | ABSENT | RETIRED-BY-T007 | WP02/T007 |
| `tests/sync/test_batch_400_no_details_poison_2736.py::TestWholeBatch400WithDetailsStillRejects::test_details_400_rejects_named_events_and_bumps_retry` | ABSENT | RETIRED-BY-T007 | WP02/T007 |
| `tests/sync/test_batch_error_surfacing.py::TestBatchSyncEventResults::test_category_counts_property` | ABSENT | RETIRED-BY-T007 | WP02/T007 |
| `tests/sync/test_batch_error_surfacing.py::TestBatchSyncEventResults::test_connection_error_populates_event_results` | ABSENT | RETIRED-BY-T007 | WP02/T007 |
| `tests/sync/test_batch_error_surfacing.py::TestBatchSyncEventResults::test_http_200_mixed_populates_event_results` | ABSENT | RETIRED-BY-T007 | WP02/T007 |
| `tests/sync/test_batch_error_surfacing.py::TestBatchSyncEventResults::test_http_400_with_details` | ABSENT | RETIRED-BY-T007 | WP02/T007 |
| `tests/sync/test_batch_error_surfacing.py::TestBatchSyncEventResults::test_http_400_with_structured_details` | ABSENT | RETIRED-BY-T007 | WP02/T007 |
| `tests/sync/test_batch_error_surfacing.py::TestBatchSyncEventResults::test_http_401_populates_auth_expired_category` | ABSENT | RETIRED-BY-T007 | WP02/T007 |
| `tests/sync/test_batch_error_surfacing.py::TestBatchSyncEventResults::test_http_403_missing_private_team_preserves_direct_ingress_category` | ABSENT | RETIRED-BY-T007 | WP02/T007 |
| `tests/sync/test_batch_error_surfacing.py::TestBatchSyncEventResults::test_http_500_populates_server_error_category` | ABSENT | RETIRED-BY-T007 | WP02/T007 |
| `tests/sync/test_batch_error_surfacing.py::TestBatchSyncEventResults::test_missing_private_team_skip_has_machine_facing_category` | ABSENT | RETIRED-BY-T007 | WP02/T007 |
| `tests/sync/test_batch_error_surfacing.py::TestBatchSyncEventResults::test_timeout_populates_retryable_transport_category` | ABSENT | RETIRED-BY-T007 | WP02/T007 |
| `tests/sync/test_batch_error_surfacing.py::TestParseErrorResponse::test_details_invalid_json_treated_as_text` | ABSENT | RETIRED-BY-T007 | WP02/T007 |
| `tests/sync/test_batch_error_surfacing.py::TestParseErrorResponse::test_error_only_no_details` | ABSENT | RETIRED-BY-T007 | WP02/T007 |
| `tests/sync/test_batch_error_surfacing.py::TestParseErrorResponse::test_error_with_details_as_list` | ABSENT | RETIRED-BY-T007 | WP02/T007 |
| `tests/sync/test_batch_error_surfacing.py::TestParseErrorResponse::test_error_with_plain_text_details` | ABSENT | RETIRED-BY-T007 | WP02/T007 |
| `tests/sync/test_batch_error_surfacing.py::TestParseErrorResponse::test_error_with_structured_json_details_string` | ABSENT | RETIRED-BY-T007 | WP02/T007 |
| `tests/sync/test_batch_error_surfacing.py::TestParseErrorResponse::test_per_event_detail_key_surfaces_distinct_violations` | ABSENT | RETIRED-BY-T007 | WP02/T007 |
| `tests/sync/test_batch_error_surfacing.py::TestParseEventResults::test_accepted_and_warning_are_successful` | ABSENT | RETIRED-BY-T007 | WP02/T007 |
| `tests/sync/test_batch_error_surfacing.py::TestParseEventResults::test_all_success` | ABSENT | RETIRED-BY-T007 | WP02/T007 |
| `tests/sync/test_batch_error_surfacing.py::TestParseEventResults::test_empty_results_array` | ABSENT | RETIRED-BY-T007 | WP02/T007 |
| `tests/sync/test_batch_error_surfacing.py::TestParseEventResults::test_error_field_fallback` | ABSENT | RETIRED-BY-T007 | WP02/T007 |
| `tests/sync/test_batch_error_surfacing.py::TestParseEventResults::test_mixed_results` | ABSENT | RETIRED-BY-T007 | WP02/T007 |
| `tests/sync/test_batch_error_surfacing.py::TestParseEventResults::test_mixed_with_pending_does_not_inflate_errors` | ABSENT | RETIRED-BY-T007 | WP02/T007 |
| `tests/sync/test_batch_error_surfacing.py::TestParseEventResults::test_pending_does_not_count_toward_success_count` | ABSENT | RETIRED-BY-T007 | WP02/T007 |
| `tests/sync/test_batch_error_surfacing.py::TestParseEventResults::test_pending_status_is_pending_not_error` | ABSENT | RETIRED-BY-T007 | WP02/T007 |
| `tests/sync/test_batch_error_surfacing.py::TestParseEventResults::test_queued_status_is_pending_not_error` | ABSENT | RETIRED-BY-T007 | WP02/T007 |
| `tests/sync/test_batch_error_surfacing.py::TestParseEventResults::test_rejected_with_no_error_message` | ABSENT | RETIRED-BY-T007 | WP02/T007 |
| `tests/sync/test_batch_retry_hygiene.py::TestRetryCountStableOnBatchLevelFailures::test_http_401_does_not_bump_retry_count` | ABSENT | RETIRED-BY-T007 | WP02/T007 |
| `tests/sync/test_batch_retry_hygiene.py::TestRetryCountStableOnBatchLevelFailures::test_http_403_generic_unauthorized_does_not_bump_retry_count` | ABSENT | RETIRED-BY-T007 | WP02/T007 |
| `tests/sync/test_batch_retry_hygiene.py::TestRetryCountStableOnBatchLevelFailures::test_http_403_private_team_does_not_bump_retry_count` | ABSENT | RETIRED-BY-T007 | WP02/T007 |
| `tests/sync/test_batch_retry_hygiene.py::TestRetryCountStableOnBatchLevelFailures::test_http_500_does_not_bump_retry_count` | ABSENT | RETIRED-BY-T007 | WP02/T007 |
| `tests/sync/test_batch_retry_hygiene.py::TestRetryCountStableOnBatchLevelFailures::test_preflight_no_private_team_does_not_bump_retry_count` | ABSENT | RETIRED-BY-T007 | WP02/T007 |
| `tests/sync/test_batch_retry_hygiene.py::TestRetryCountStillBumpsOnPerEventRejection::test_per_event_rejection_still_bumps_retry_count` | ABSENT | RETIRED-BY-T007 | WP02/T007 |
| `tests/sync/test_batch_sync.py::test_batch_healthy_session_no_rehydrate` | ABSENT | RETIRED-BY-T007 | WP02/T007 |
| `tests/sync/test_batch_sync.py::test_batch_negative_cache_honored_across_calls` | ABSENT | RETIRED-BY-T007 | WP02/T007 |
| `tests/sync/test_batch_sync.py::test_batch_shared_only_session_triggers_one_me_rehydrate` | ABSENT | RETIRED-BY-T007 | WP02/T007 |
| `tests/sync/test_batch_sync.py::test_batch_skips_ingress_when_rehydrate_yields_no_private` | ABSENT | RETIRED-BY-T007 | WP02/T007 |
| `tests/sync/test_batch_sync.py::TestBatchSync1000Events::test_batch_sync_1000_events` | ABSENT | RETIRED-BY-T007 | WP02/T007 |
| `tests/sync/test_batch_sync.py::TestBatchSyncEmptyQueue::test_batch_sync_empty_queue` | ABSENT | RETIRED-BY-T007 | WP02/T007 |
| `tests/sync/test_batch_sync.py::TestBatchSyncErrors::test_batch_sync_auth_failure` | ABSENT | RETIRED-BY-T007 | WP02/T007 |
| `tests/sync/test_batch_sync.py::TestBatchSyncErrors::test_batch_sync_bad_request` | ABSENT | RETIRED-BY-T007 | WP02/T007 |
| `tests/sync/test_batch_sync.py::TestBatchSyncErrors::test_batch_sync_connection_error` | ABSENT | RETIRED-BY-T007 | WP02/T007 |
| `tests/sync/test_batch_sync.py::TestBatchSyncErrors::test_batch_sync_partial_failure` | ABSENT | RETIRED-BY-T007 | WP02/T007 |
| `tests/sync/test_batch_sync.py::TestBatchSyncErrors::test_batch_sync_server_error` | ABSENT | RETIRED-BY-T007 | WP02/T007 |
| `tests/sync/test_batch_sync.py::TestBatchSyncErrors::test_batch_sync_timeout` | ABSENT | RETIRED-BY-T007 | WP02/T007 |
| `tests/sync/test_batch_sync.py::TestBatchSyncLimit::test_batch_sync_respects_limit` | ABSENT | RETIRED-BY-T007 | WP02/T007 |
| `tests/sync/test_batch_sync.py::TestBatchSyncSuccess::test_batch_sync_auth_header` | ABSENT | RETIRED-BY-T007 | WP02/T007 |
| `tests/sync/test_batch_sync.py::TestBatchSyncSuccess::test_batch_sync_caps_advertised_limit_to_cli_ceiling` | ABSENT | RETIRED-BY-T007 | WP02/T007 |
| `tests/sync/test_batch_sync.py::TestBatchSyncSuccess::test_batch_sync_consumes_advertised_max_events_per_batch` | ABSENT | RETIRED-BY-T007 | WP02/T007 |
| `tests/sync/test_batch_sync.py::TestBatchSyncSuccess::test_batch_sync_gzip_compression` | ABSENT | RETIRED-BY-T007 | WP02/T007 |
| `tests/sync/test_batch_sync.py::TestBatchSyncSuccess::test_batch_sync_leaves_rows_untouched_when_checkout_still_disabled` | ABSENT | RETIRED-BY-T007 | WP02/T007 |
| `tests/sync/test_batch_sync.py::TestBatchSyncSuccess::test_batch_sync_prefers_private_team_over_shared_default` | ABSENT | RETIRED-BY-T007 | WP02/T007 |
| `tests/sync/test_batch_sync.py::TestBatchSyncSuccess::test_batch_sync_rehydrates_stale_drain_blockers_before_post` | ABSENT | RETIRED-BY-T007 | WP02/T007 |
| `tests/sync/test_batch_sync.py::TestBatchSyncSuccess::test_batch_sync_reports_single_oversized_event_without_posting` | ABSENT | RETIRED-BY-T007 | WP02/T007 |
| `tests/sync/test_batch_sync.py::TestBatchSyncSuccess::test_batch_sync_retries_smaller_batch_after_server_size_rejection` | ABSENT | RETIRED-BY-T007 | WP02/T007 |
| `tests/sync/test_batch_sync.py::TestBatchSyncSuccess::test_batch_sync_sends_private_team_slug_header` | ABSENT | RETIRED-BY-T007 | WP02/T007 |
| `tests/sync/test_batch_sync.py::TestBatchSyncSuccess::test_batch_sync_server_413_on_single_event_classifies_as_oversized_event` | ABSENT | RETIRED-BY-T007 | WP02/T007 |
| `tests/sync/test_batch_sync.py::TestBatchSyncSuccess::test_batch_sync_shrinks_batch_to_advertised_decompressed_bytes` | ABSENT | RETIRED-BY-T007 | WP02/T007 |
| `tests/sync/test_batch_sync.py::TestBatchSyncSuccess::test_batch_sync_success` | ABSENT | RETIRED-BY-T007 | WP02/T007 |
| `tests/sync/test_batch_sync.py::TestBatchSyncSuccess::test_batch_sync_throttled_category_on_429` | ABSENT | RETIRED-BY-T007 | WP02/T007 |
| `tests/sync/test_batch_sync.py::TestBatchSyncSuccess::test_batch_sync_url_construction` | ABSENT | RETIRED-BY-T007 | WP02/T007 |
| `tests/sync/test_batch_sync.py::TestBatchSyncSuccess::test_batch_sync_uses_fallback_decompressed_byte_limit` | ABSENT | RETIRED-BY-T007 | WP02/T007 |
| `tests/sync/test_batch_sync.py::TestBatchSyncSuccess::test_batch_sync_with_duplicates` | ABSENT | RETIRED-BY-T007 | WP02/T007 |
| `tests/sync/test_batch_sync.py::TestHistoricalMissionStateGuard::test_batch_sync_rejects_legacy_status_row_before_network` | ABSENT | RETIRED-BY-T007 | WP02/T007 |
| `tests/sync/test_batch_sync.py::TestSaasFeatureFlag::test_batch_sync_skips_network_when_disabled` | ABSENT | RETIRED-BY-T007 | WP02/T007 |
| `tests/sync/test_batch_sync.py::test_sync_all_queued_events_terminates_on_no_private_team` | ABSENT | RETIRED-BY-T007 | WP02/T007 |
| `tests/sync/test_batch_sync.py::TestSyncAllQueuedEvents::test_sync_all_continues_past_oversized_event` | ABSENT | RETIRED-BY-T007 | WP02/T007 |
| `tests/sync/test_batch_sync.py::TestSyncAllQueuedEvents::test_sync_all_in_batches` | ABSENT | RETIRED-BY-T007 | WP02/T007 |
| `tests/sync/test_batch_sync.py::TestSyncAllQueuedEvents::test_sync_all_progress_output_is_log_readable` | ABSENT | RETIRED-BY-T007 | WP02/T007 |
| `tests/sync/test_batch_sync.py::TestSyncAllQueuedEvents::test_sync_all_stops_on_all_errors` | ABSENT | RETIRED-BY-T007 | WP02/T007 |
| `tests/sync/test_integration.py::TestBatchSyncAuthHandling::test_401_marks_events_for_retry` | ABSENT | RETIRED-BY-T007 | WP02/T007 |
| `tests/sync/test_integration.py::TestBatchSyncAuthHandling::test_server_error_keeps_events_queued` | ABSENT | RETIRED-BY-T007 | WP02/T007 |
| `tests/sync/test_integration.py::TestFullFlow::test_batch_payload_contains_correct_events` | ABSENT | RETIRED-BY-T007 | WP02/T007 |
| `tests/sync/test_integration.py::TestFullFlow::test_event_emission_to_queue_to_sync` | ABSENT | RETIRED-BY-T007 | WP02/T007 |
| `tests/sync/test_integration.py::TestFullFlow::test_lamport_clock_ordering_preserved` | ABSENT | RETIRED-BY-T007 | WP02/T007 |
| `tests/sync/test_integration.py::TestMultiEventBatch::test_feature_created_plus_wp_batch` | ABSENT | RETIRED-BY-T007 | WP02/T007 |
| `tests/sync/test_integration.py::TestMultiEventBatch::test_mixed_event_types_in_batch` | ABSENT | RETIRED-BY-T007 | WP02/T007 |
| `tests/sync/test_offline_replay.py::TestBatchSyncThroughput::test_batch_sync_throughput_1000_events` | ABSENT | RETIRED-BY-T007 | WP02/T007 |
| `tests/sync/test_offline_replay.py::TestBatchSyncThroughput::test_batch_sync_throughput_multiple_batches` | ABSENT | RETIRED-BY-T007 | WP02/T007 |
| `tests/sync/test_offline_replay.py::TestEventRecovery::test_100_percent_event_recovery` | ABSENT | RETIRED-BY-T007 | WP02/T007 |
| `tests/sync/test_offline_replay.py::TestEventRecovery::test_event_order_preserved` | ABSENT | RETIRED-BY-T007 | WP02/T007 |
| `tests/sync/test_offline_replay.py::TestEventRecovery::test_partial_failure_recovery` | ABSENT | RETIRED-BY-T007 | WP02/T007 |
| `tests/sync/test_offline_replay.py::TestIdempotency::test_idempotency_duplicate_events` | ABSENT | RETIRED-BY-T007 | WP02/T007 |
| `tests/sync/test_offline_replay.py::TestIdempotency::test_idempotency_mixed_results` | ABSENT | RETIRED-BY-T007 | WP02/T007 |
| `tests/sync/test_offline_replay.py::TestOfflineWorkflowEndToEnd::test_complete_offline_workflow` | ABSENT | RETIRED-BY-T007 | WP02/T007 |
| `tests/sync/test_offline_replay.py::TestOfflineWorkflowEndToEnd::test_intermittent_connectivity` | ABSENT | RETIRED-BY-T007 | WP02/T007 |
| `tests/sync/test_offline_replay.py::TestReconnectionTriggersBatchSync::test_multiple_reconnection_cycles` | ABSENT | RETIRED-BY-T007 | WP02/T007 |
| `tests/sync/test_offline_replay.py::TestReconnectionTriggersBatchSync::test_reconnection_triggers_batch_sync` | ABSENT | RETIRED-BY-T007 | WP02/T007 |

---

## C-005 handoff — the conftest change, described here rather than only in the code

The pre-merge completeness lens blocked on this: this artifact carried the per-node-id pin delta but the
word "conftest" appeared in it **zero** times, so C-005's second limb was met only in the code. Stated here
so the artifact is self-contained.

**What changed in `tests/sync/conftest.py`, and why the sync-cone mission must know.** Its autouse fixture
made three patches. The `specify_cli.sync.batch.is_sync_enabled_for_checkout` patch is **removed** — the
name no longer exists — and `raising=False` went with it. The `specify_cli.sync.runtime.…` patch **stays**,
now at `raising=True`, because that name is bound at import in `sync/runtime.py` and read inside
`_auto_start_enabled`, so a rename or typo fails loudly instead of silently creating an attribute.
`EventEmitter._project_consents_to_capture` is **untouched** — zero `+`/`-` diff lines touch it.

**Why it matters to that mission specifically:** for every `tests/sync` file whose name lacked `"consent"`
or `"capture_gate"`, that fixture used to grant the batch gate `True`. Any historical measurement of this
cone was taken with that grant in place. **A pre-existing leak observation is not comparable across this
change** if the observation depended on the fixture's grant. The pins were unaffected — verified, 12
entries semantically identical, ledger reproducing at both commits — but the reasoning must be re-checked
rather than assumed for anything else.

**Pin renumbering, because every citation elsewhere used the old numbers:**

| Node id | Was | Now |
|---|---|---|
| `test_lifecycle_readiness.py::test_init_emits_project_init_event_offline` | `:371` | **`:420`** |
| `test_runtime.py::TestSyncRuntime::test_starts_background_service` | `:389` | **`:442`** |
| `test_runtime.py::TestUnauthenticatedBehavior::test_no_websocket_when_unauthenticated` | `:395` | **`:452`** |

**And the registry itself moved**: it is `tests/sync/_leak_guard.py:376-479`, not the `:333-423` the
programme plan records. Re-derive rather than citing either.

---

## SC-003 evidence — recorded here because the pre-merge pass found it absent

`SC-003` required the drain guard's pass to be quoted from a redirected run with its node count. It was
never recorded; the completeness lens blocked on it, correctly — **its only support was a claim.**

```
$ .venv/bin/python -m pytest tests/sync/test_no_queue_drain_constructed_3030.py -ra -p no:cacheprovider -q
5 passed in 63.73s (0:01:03)
EXIT=0
```

5 nodes: the 3 original scan tests plus the 2 added by this mission (the synthetic-reintroduction positive
control and the non-vacuity assertion that `sync/batch.py` is in the scanned set).

**The guard was strengthened, not weakened.** An independent lens verified it discriminates in both
directions: a silenced matcher fails, an over-firing matcher fails, and re-adding the
`_DEFINING_MODULE` self-exclusion fails the non-vacuity test. That matters because with the sender names
gone the original scan would otherwise pass for a reason that no longer discriminates.
