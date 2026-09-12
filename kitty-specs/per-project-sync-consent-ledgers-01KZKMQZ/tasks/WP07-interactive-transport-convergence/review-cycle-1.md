---
affected_files: []
cycle_number: 1
mission_slug: per-project-sync-consent-ledgers-01KZKMQZ
reproduction_command:
reviewed_at: '2026-08-11T14:23:50Z'
reviewer_agent: codex
wp_id: WP07
---

# WP07 whole-work-package review — changes requested

Reviewed candidate: `e0cebb9ac1257c61ca28c92ce58dfbce7ca4dd43` (product aggregate parent `d908f4ec356f5386be3c76e862a7f22ee2217b97`; WP07 product checkpoint `e46fecebd1be5f990070e735d2c8b8075630bb42`).

Reviewer: Reviewer Renata / codex, independent whole-WP review.

## Verdict

Changes requested. T031–T035 cannot remain recorded complete while explicitly WP07-owned regression suites fail on the canonical `for_review` aggregate.

## Blocking findings

### 1. Required sequential consent-fixture migrations were never performed

`tests/delivery/test_cross_project_refusal_state_3030.py:52-55` and `tests/delivery/test_liveness_predicate_before_limit_3030.py:72-75` still call the retired grant seam `set_project_consent(..., True)`. All six nodes fail during setup with `LegacyConsentMigrationRequiredError` before exercising the sender behavior.

This is WP07-owned work, not an external baseline: both files are listed in WP07 `owned_files` and lane-e `write_scope`, and WP07's Test Strategy explicitly requires their sequential migration. The WP07 implementation range `e510ec74b..e46fecebd` contains no change to either file.

Remediation: migrate the fixtures through the real project-owned explicit opt-in, layout, target/admission authority used by the dispatcher while preserving every existing refusal, liveness, FIFO and non-deletion assertion. Run both complete modules.

### 2. The canonical ledger projection does not preserve terminal parking

`tests/delivery/test_project_store_ledger.py::test_terminal_refusal_is_parked_and_selection_keeps_fifo_order` fails at line 102: after `event-1` is terminally parked for target 1, `SqliteDeliveryLedger.select_undelivered(target_id="target-2", ...)` returns `event-1` again. Expected selection is `event-2`, `event-3`.

This violates T032's explicit requirement that the delivery ledger be a truthful read/status projection over canonical attempts while retaining legacy caller compatibility, and T035's no-resend/terminal-parking requirement.

Remediation: make the canonical/compatibility projection retain the existing global terminal-parking invariant without writing a duplicate legacy attempt or weakening per-target delivered/duplicate behavior. Run the complete project-store ledger and dispatcher suites, including terminal refusal/recovery mutants.

### 3. The current WP08-preserving aggregate breaks the #3108 hosted-drain positive

`tests/sync/tracker/test_tracker_egress_refusal_3108.py::test_us1_sc4_hosted_drain_unaffected_by_tracker_key` fails at line 1758 in isolation. Both body rows remain pending because the public drain logs `project sync store is locked`; the test's non-vacuous positive requires the queue to drain to zero independently of the tracker narrowing key.

The node was changed and lane-owned by WP07 T034, while the reviewed head deliberately includes the current WP08 aggregate. Approval therefore requires the T034 narrowing proof to survive WP08's project-store/background convergence.

Remediation: reconcile the test/public body-drain setup with the current project-store UoW/lease boundary so no store lock is held across the transport and both with-key/no-key arms make real positive progress. Do not bypass the WP06 final gate or weaken the zero-row assertion. Run the exact node plus WP08 background authority/isolation tests.

## Verification evidence

Relevant whole-WP gate:

```text
2 failed, 1530 passed, 1 skipped, 2 xfailed, 6 errors in 124.32s
```

Exact isolated rerun:

```text
2 failed, 6 errors in 44.73s
```

Static gates are green and should remain so:

- Ruff check: all changed Python files passed.
- Ruff format: 64 changed Python files already formatted.
- strict mypy: 22 changed source modules passed.
- `git diff --check`: passed.

Contract/security inspection found no separate blocker in the reviewed T032/T033/T034 sender implementation: SaaS `e8bc840f`/`9f973d21` Event, body and LocalCommit shapes match the proof-bearing wire vocabulary; Authorization remains header-only; typed refusal and UNKNOWN recovery tests otherwise pass. Changed-path ownership is complete across the union of WP07 `owned_files` and lane-e `write_scope`; the split metadata should not be used to classify the three reds above as external.

The prior submission `--force` rationale is accepted as limited to the unrelated untracked WP08 baseline artifact. It does not waive these product/test review gates.
