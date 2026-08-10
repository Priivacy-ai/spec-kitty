---
affected_files: []
cycle_number: 1
mission_slug: per-project-sync-consent-ledgers-01KZKMQZ
reproduction_command:
reviewed_at: '2026-08-10T17:03:02Z'
reviewer_agent: user
wp_id: WP06
---

# WP06 reviewer feedback — changes requested

Reviewed product commits `2f4ace541`, `15de39cc4`, and `d170c656b` against the post-WP05 base `41768e4c3`, restricted to WP06's five declared files and T026–T030. The implementation is adapter-neutral and its nine owned tests pass, but the current protocol does not yet enforce the acceptance boundary.

## 1. The transport/result lease proof is replayable after lock release (blocking)

`TransportLeaseContext.unit_of_work()` mints a `ProjectSyncContext` containing a string `transport_lease_identity`, but `mark_transport_started()`, `mark_delivery_result_unknown()`, and `record_delivery_result()` only check `context.egress_eligible`. They do not prove that the associated OS lock is still held. A caller can retain the context, exit `acquire_project_transport_lease()`, open a fresh unit of work, and start transport successfully with the stale context.

Independent reproduction on the reviewed head printed `stale_context_after_lock_release_started= in_flight`. This violates T028/FR-008/FR-025/FR-030: final check, start, and result must be gated by the *live* cross-process lease, not merely by a previously minted string.

Required remediation: make lease ownership/lifetime un-replayable at each start/result mutation (or structurally confine those mutations to a live lease-owned service), and add a negative regression that retains a context past lock release and proves start/result fail.

## 2. The final gate accepts stale authority and records the wrong generation (blocking)

`prepare_delivery_attempt()` persists `consent_generation`, `target_generation`, `admission_generation`, and `binding_audience`, but `mark_transport_started()` selects only `attempt_id` and `state`. It never compares the attempt's persisted authority tuple with the lease's current project consent epoch, exact target/account/Private-Teamspace audience, admission generation, or binding. `record_delivery_result()` then selects only the attempt epoch and writes the *current context's* target/admission generations instead of the attempt's original tuple.

Independent reproduction prepared an attempt under consent/target/admission `(3, 4, old-admission, old-binding)`, changed to a newly granted target/admission `(5, 9, new-admission, new-binding)`, and then started and marked the old attempt delivered. The stored attempt became `succeeded`, while its result was recorded as `(9, new-admission, delivered)`.

This violates T027/T028, C-010, and the truthful-original-generation rule. Required remediation: persist sufficient exact audience identity, compare every persisted authority component at the final pre-start gate, refuse stale attempts, and record genuine results under the attempt's original generations/binding.

## 3. The deny-only global kill switch is not checked (blocking)

`_lease_bound_context()` sets `kill_switch_allows` from local consent, epoch, and admission alone. It never reads the canonical `SPEC_KITTY_ENABLE_SAAS_SYNC` authority. Independent reproduction with `SPEC_KITTY_ENABLE_SAAS_SYNC=0` produced `eligible_with_kill_switch_off= True` and allowed a start.

This is a direct FR-005/C-002 final-gate regression. Required remediation: consume the existing canonical SaaS-sync enable authority during the lease-bound recheck and add both deny and admitted positive controls, including a mutant/negative test that fails if the check is removed.

## 4. Opt-out does not serialize with or wait for the live transport lease (blocking)

`settle_attempts_for_opt_out()` and `terminalize_orphaned_attempt()` accept only a raw `ProjectUnitOfWork`; they require no lease proof. The owned test calls settlement outside the transport lease. A second-process reproduction successfully terminalized one `in_flight` attempt while the first process still held the project's OS lease (`settlement_while_other_process_holds_lease= 0 1`). The implementation also terminalizes every `in_flight` row immediately and has no live-holder wait/result-settlement/deadline behavior.

This fails both T029 orderings and NFR-003: when a worker is live, opt-out must wait for its bounded genuine result; only an orphan/uncertain attempt may be irrevocably terminalized before return. Required remediation: provide one lease-serialized, bounded settlement protocol that distinguishes live completion from orphan takeover and prove both orderings across processes.

## 5. Recovery and crash-window coverage do not enforce the stated bounded protocol (blocking)

`DeliveryAttemptSpec.deadline_at` is optional and no start/recovery/settlement path consumes it. `reconciliation_policy` is persisted but ignored: every `prepared` attempt is declared retryable and every `in_flight`/`unknown` attempt is declared queryable regardless of the native protocol's actual safe capability. `record_delivery_result(TERMINAL_UNKNOWN)` also maps the attempt back to `unknown`, contradicting the terminal outcome's name.

T030 requires deterministic barriers for `before_attempt_commit`, `after_attempt_commit_before_send`, `transport_started`, `response_received_before_result`, and `result_committed`. The current tests do not force all five windows. The only process-death test exits at `test_transport_orphan_settlement.py:188`, *after* both lease and transaction context managers have already exited at line 187, so it does not prove process death while a lease is held or OS-lock release. There are no barrier handshakes, no true live-start-before-opt-out test, and no process-death proof for the other four windows.

Required remediation: make deadlines mandatory/validated and effective, derive recovery only from an explicit supported native strategy (otherwise operator review), preserve `terminal_unknown` on every surface, and add non-vacuous subprocess/barrier coverage for all five required windows plus the compound kill-during-response → immediate opt-out → late-recovery sequence.

## Review checks

- Owned tests: **PASS** — `9 passed`.
- Ruff format/check over all five owned files: **PASS**.
- Strict mypy over both touched source modules: **PASS**.
- `spec-kitty agent tasks validate-workflow WP06`: **PASS**.
- Declared-file isolation / no transport-adapter edits: **PASS** — only the five WP06-owned files changed from `41768e4c3..d170c656b`.
- Durable native identity persistence: **PARTIAL** — identity survives persistence, but strategy/deadline are not enforced and stale authority may be started.
- `terminal_unknown` late-success/resend guard: **PARTIAL** — the direct terminalization path blocks later success and plans a no-op, but the public terminal outcome mapping is non-terminal and the compound crash ordering is unproved.
- Dead code: **N/A under the explicit protocol-only staging contract** — WP07/WP08 own production adapter callers; no adapter integration is required in WP06.
- Synthetic-fixture test: **PASS for assertions present**, but required crash/barrier assertions are absent.
- Silent empty return: **PASS** for the reviewed protocol paths; idempotent terminalization's no-op is explicit.
- FR coverage: **FAIL** for FR-005/FR-008/FR-025/FR-030 and NFR-003 as detailed above.
- Frozen surface: **PASS** — no frozen or adapter file was modified by the WP commits.
- Locked decisions: **FAIL** — kill-switch, exact-authority, and opt-out serialization MUST clauses are contradicted.
- Shared-file ownership: **N/A** — all WP06 files were newly introduced and exclusively declared.
- Production fragility: **PASS** — new raises are fail-loud protocol violations/timeouts, not swallowed transient failures.

## Pre-existing mission-acceptance debt (non-WP06 blocker)

`tests/sync/test_project_store_transactions.py` remains `1 failed, 25 passed`: `test_failing_savepoint_rolls_back_inner_work_without_ending_outer_transaction` omits required `admission_operations.configuration_generation`. The same failure is established at pre-WP06 `14ac8b31` and is claimed by Priivacy-ai/spec-kitty#3309. WP06 did not modify the schema or this test and did not cause or worsen that baseline failure; retain it as mission-acceptance debt.

WP07 and WP08 depend on WP06 and must not integrate against this protocol until the corrected WP06 is approved; after remediation they should rebase onto the new approved WP06 head.
