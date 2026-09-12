# The CI baseline, by node-id

The per-node-id table behind [`ci-baseline-at-landing.md`](ci-baseline-at-landing.md). That file
sets the un-draft standard — *no new red is attributable to this PR; every red matches this baseline
by node-id* — and its first draft pointed at a table that existed only in the session that produced
it. **A standard whose comparison basis cannot be re-derived is not a standard**, which is this
mission's own subject, so the table is committed here.

Built from two `CI Quality` runs on `bb2020fea924d6e5b157974f27a7cab1a77ad259`, the SHA this mission
branched from:

| Run | Trigger | When |
|---|---|---|
| [`30681941495`](https://github.com/Priivacy-ai/spec-kitty/actions/runs/30681941495) | schedule | 2026-08-01T03:24:54Z |
| [`30621215287`](https://github.com/Priivacy-ai/spec-kitty/actions/runs/30621215287) | push | 2026-07-31T09:47:27Z |

**41 distinct failing node-ids in the union. 39 stable** — identical in both runs, same job(s).

### Conceded: this baseline is anchored 6 commits behind the PR's true base

The table is measured at `bb2020fea`, the SHA the mission branched from. The PR's actual
merge-base is `f9fde44bb` — `bb2020fea..f9fde44bb` is **6 substantive commits touching ~81
`src/` and ~116 `tests/` files** (including a doctrine-consolidation feature), not a docs-only
gap. The failing-node-id set *could* legitimately differ between the two SHAs, and no `CI Quality`
run exists at `f9fde44bb` (it is a landing-fold SHA that never triggered the schedule/push
workflow). The direction of the drift is **conservative for attribution**: a red introduced by
those 6 main commits but absent from this `bb2020fea` list would be *over*-attributed to the PR
(flagged for a human to dismiss), never silently slipped past. It is stated here rather than
implied, because "a standard whose comparison basis cannot be re-derived is not a standard" is
this mission's own subject — and re-derivability includes naming the base you could not measure.

## Tracked by an open issue — expected, not a problem

| # | Node-id | Job(s) | Issue |
|---|---|---|---|
| 1 | `tests/integration/test_review_cycle_rejection_only.py::test_approving_a_rejected_wp_writes_no_verdict_artifact` | regression (blocking), integration-core-misc | `#2996` |
| 2 | `tests/review/test_cycle.py::test_self_referential_feedback_source_is_rejected` | regression (blocking), integration-review | `#2996` |
| 3 | `tests/review/test_cycle.py::test_new_cycle_body_never_duplicates_a_prior_cycle_file` | regression (blocking), integration-review | `#2996` |
| 4 | `tests/agent/cli/commands/test_charter_cli.py::test_sync_command_human_and_json_surfaces_do_not_contradict_3045` | regression (blocking), integration-agent | `#3045` |
| 5 | `tests/regression/test_issue_3086_merge_delete_branch_flattens_coordination_metadata.py::test_issue_3086_merge_delete_branch_flattens_coordination_metadata` | regression (blocking), integration-core-misc | `#3086` |
| 6 | `tests/sync/test_strict_json_stdout.py::test_mission_create_json_strict_when_sync_skips_ingress` | regression (blocking) | `#2782` |
| 7 | `tests/specify_cli/invocation/test_registry_builtin_activation_parity.py::test_excluded_builtin_absent_from_routing_and_context` | integration-core-misc (specify-cli-heavy) | `#3092` |

## Shard-isolation victims — tracked by open `#3115`, which this mission does NOT close

`#3115` names all six of these files. **This PR does not green them** — they show a complete,
well-formed panel reporting an empty queue, which is shard pollution, not the render-width fold this
mission fixed. The `...` in their assertion dumps is pytest's own repr elision, not CLI truncation.

| # | Node-id | Job |
|---|---|---|
| 8–10 | `tests/sync/test_consent_write_refusal_3030.py::test_a_refused_write_is_reported_rather_than_raised_out_of_the_cli` `[opt-in]` `[opt-out]` `[server]` | fast-tests-sync |
| 11 | `tests/cli/commands/test_sync_doctor_consent_health_3030.py::test_doctor_says_the_consent_index_is_unreadable_and_names_the_action` | fast-tests-cli |
| 12–14 | `…test_sync_doctor_consent_health_3030.py::test_doctor_names_the_action_for_each_project_local_fault_kind` `[unparseable]` `[wrong_shape]` `[unusable]` | fast-tests-cli |
| 15 | `tests/cli/commands/test_sync_doctor_per_project_3030.py::test_doctor_names_every_project_with_count_age_and_consent` | fast-tests-cli |
| 16 | `tests/cli/commands/test_sync_status_per_project_3030.py::test_status_names_every_project_with_count_age_and_consent` | fast-tests-cli |
| 17 | `tests/cli/commands/test_sync_purge_3030.py::TestPurgeAll::test_all_names_the_per_checkout_scope_and_claims_nothing_wider` | fast-tests-cli |
| 18 | `tests/cli/commands/test_sync_purge_3030.py::TestPurgeAll::test_help_does_not_promise_machine_wide_erasure` | fast-tests-cli |
| 19 | `tests/cli/commands/test_sync_migrate_backfills_h4.py::test_the_consent_backfill_reports_records_it_could_not_resolve` | fast-tests-cli |

## The mission's own expected reds — `#3136`

**The victim is a class, not an enumeration.** Any `time.sleep` call-count assertion reachable in
`tests/sync/tracker/` can be the victim; whichever one is open when the intruder sleeps takes the
hit. `#3136`'s body names two node-ids and instructs successors to key on them — that instruction is
already stale, and keying on it will miss reds.

| # | Node-id | Stability |
|---|---|---|
| 20 | `tests/sync/tracker/test_saas_client.py::TestPolling::test_exponential_backoff_intervals` (`assert 115 == 3`) | both runs |
| 21 | `tests/sync/tracker/test_saas_client.py::TestRetryBehaviors::test_429_defaults_to_5s_when_missing` (`Called 80 times`) | **run 1 only** |
| 22 | `tests/sync/tracker/test_saas_client_origin.py::TestSearchIssues::test_429_retries_then_raises` (`Called 556 times`) | **run 2 only** |

Rows 21 and 22 alternating between runs is the mechanism confirming itself.

## Filed by this mission — had no owner before

| # | Node-id(s) | Issue |
|---|---|---|
| 23 | `tests/regression/test_issue_2804_merge_resets_gate_artifacts.py::test_merge_resets_filled_gate_artifacts_to_placeholder` — `#2804` is **closed** | **`#3138`** |
| 24–37 | `tests/specify_cli/regression/test_twelve_agent_parity.py::test_command_output_unchanged[accept-*]` (12 params: claude, gemini, copilot, cursor, qwen, opencode, windsurf, kilocode, auggie, q, kiro, antigravity) | **`#3139`** |
| 38–39 | `tests/specify_cli/skills/test_command_renderer.py::test_snapshot[codex-accept]`, `[vibe-accept]` | **`#3139`** |
| 40 | `tests/lanes/test_worktree_allocator.py::TestDefensiveHelpers::test_read_coordination_branch_none_on_malformed_json` | **`#3140`** |
| 41 | `tests/unit/status/test_mission_status_aggregate.py::TestLoadCoordUnavailableFailsClosed::test_corrupt_meta_fails_closed_instead_of_legacy_fallback` | **`#3140`** |
| 42 | `…::test_non_dict_meta_fails_closed_instead_of_legacy_fallback` | **`#3140`** |
| 43 | `tests/specify_cli/cli/commands/test_charter_widen_integration.py::TestGetMissionId::test_returns_none_if_json_malformed` | **`#3140`** |

Rows 24–39 all name the **`accept`** surface and no other command — one drift observed fourteen
times, not fourteen defects. Stated as an observed pattern; the diff was not traced.

## How to use this table

**`tests/architectural/` is clean on this baseline** — no failures under that path in either run, all
three `arch-adversarial` shards green. This mission adds tests there, so **any red under
`tests/architectural/` on the PR is the PR's**.

**`tests/sync/` is not clean, but its reds are attributable.** The **primary** rule is strict
node-id membership: a `tests/sync/` red whose node-id is in the tables above is baseline; one whose
node-id is *not* is the PR's, full stop. The leak-guard `[FR-007 leak guard]` tag is a **secondary
convenience**, not the standard — it only distinguishes leak-guard-*emitted* reds, and a `[FR-007
leak guard]`-tagged red is unambiguously the PR's. But the inverse ("untagged ⇒ baseline") does
**not** hold: this PR rewrites `tests/sync/conftest.py` (+1157) and adds sync test files
(`test_saas_client.py`, `test_sync_consent_default_deny.py`), so an *untagged* new red is entirely
possible and must be judged by node-id membership, not by the absence of the tag. Where the two
rules disagree, node-id membership wins.

## The gap this table cannot close

Four jobs — `fast-tests-status`, `integration-tests-sync`, `integration-tests-sync-real-port`,
`integration-tests-status` — have been `skipped` for 13 consecutive push/schedule runs behind a
failing `fast-tests-sync` (`#3127`). **They contribute no baseline rows.** If this PR turns one of
them green→red, the comparison that would reveal it does not exist. That is a known, unclosable hole
in the un-draft evidence, not something to be talked around.
