# WP09 Review Cycle 2 — Independent Review

- **Reviewer:** reviewer-renata (independent; did not implement)
- **Date:** 2026-08-13
- **Op:** profile invocation `01KZX120HEVXFKPKQTFF1J3YCK` (governance context hash `7164268119947b1e`)
- **Commit under review:** `7ddfd660c` — "test(WP09): prove transport revocation and recovery matrix"
- **Branch:** `pr/per-project-sync-consent-progress`

## Scope reviewed

- `tests/support/sync_transport_barriers.py` (new, 2392 lines) — barrier protocol, production adapter contracts, independent evidence oracle
- `tests/sync/test_transport_revocation_matrix.py` (new, 1161 lines) — T041 + T040 mutants
- `tests/sync/test_transport_crash_matrix.py` (new, 606 lines) — T042 + T043
- `tests/architectural/test_egress_consent_boundary.py` (updated) — per-symbol sink classification, final owner labels
- `tests/architectural/test_sync_writer_census.py` (updated) — exact grant census after adapter convergence
- `tests/sync/test_daemon_publish_consent_3030.py` (updated) — regression migrated to canonical admitted-project protocol
- Task spec: `kitty-specs/per-project-sync-consent-ledgers-01KZKMQZ/tasks/WP09-aggregate-revocation-crash-matrix.md` (T040–T043)

## Gate commands and results

| Command | Result |
|---|---|
| `uv run python -m pytest tests/sync/test_transport_revocation_matrix.py tests/sync/test_transport_crash_matrix.py -q --tb=short --timeout=300 -n auto --dist loadfile` | **191 passed** in 112.36s |
| `uv run python -m pytest tests/architectural/test_egress_consent_boundary.py tests/architectural/test_sync_writer_census.py tests/sync/test_daemon_publish_consent_3030.py -q -n auto --dist loadfile` | **67 passed, 2 xfailed** (both xfails pre-existing before 7ddfd660c; xfail count in the file unchanged) |
| `uv run ruff check` (all six owned files) | All checks passed |
| `uv run mypy` (barriers + both matrices) | Success: no issues found |

## Findings

### T040 — barriers and censuses: PASS
- All five required phases exist as `BarrierPhase` (`before_attempt_commit`, `after_attempt_commit_before_send`, `transport_started`, `response_received_before_result`, `result_committed`).
- Barriers are **real** file-based rendezvous (controller-owned release files, worker-owned arrival files) — not sleeps. The only `time.sleep` calls are 5 ms bounded polling on marker files with deadlines; every marker is validated against the full identity payload and a cross-identity marker raises `AssertionError`.
- Identity binding covers project, attempt, native correlation, and family; the seed identity is never accepted as transport correlation — the production hook must supply the durable attempt/native tuple (`bind_production_identity`, `controller_wait_for_binding`), and rebinding to a different attempt is rejected. `test_barrier_release_is_bound_to_every_transport_identity_field` proves one mixed run cannot release another run's window on any of the four fields.
- Phase hooks patch the real WP06 durable-transition functions (`prepare_delivery_attempt`, `mark_transport_started`, `record_delivery_result` and their live per-module aliases), not test doubles of the protocol.
- Census: `_WP09_SINK_CLASSIFICATIONS` classifies **every** source-discovered sink symbol into one of the ten matrix families (empty family sets are explicit loopback/control rows with rationale); `test_wp09_sender_census_is_exact_per_symbol_not_per_file` and `test_wp09_every_discovered_sink_symbol_is_classified_into_the_matrix` enforce per-symbol inspection. Final owner labels corrected to WP07/WP08 and asserted (`{row.final_owner} == {"WP07","WP08"}`). 21 producer/discovery/control integration rows verified to delegate by symbol, with local-only rows proven to make no live calls. The daemon-publish 3030 regression now runs under the canonical admitted-project protocol.

### T041 — both revoke orderings × outcomes: PASS
- Ordering one (pause before transport, then opt-out): all ten families, real subprocess paused at `after_attempt_commit_before_send`, opt-out cancels the durable attempt (`CANCELED`, no result), zero captured transport bytes (relay's local delegation POST correctly distinguished from hosted egress), project B progresses with physical isolation proof (every `ProjectSyncStore` open recorded and asserted to be PROJECT_B only).
- Ordering two (transport started, then opt-out): all ten families × {delivered, duplicate, refused, timeout}. Opt-out is proven to block while the result lease is live and return only after settlement; exact request bytes asserted through the closed wire-envelope oracle; attempt/result generations asserted against an independently-read authority; timeout terminalizes to `terminal_unknown`.
- Post-return fencing: `test_public_opt_out_bounds_a_hung_live_holder_and_fences_late_success` proves bounded lease wait (<8 s), `terminal_unknown` recorded while the holder still lives, and a late `record_delivery_result(DELIVERED)` raises `ProjectStoreError` without state change.
- Hosted duplicate is a **real** classifier path pinned to the paired SaaS `c3f39217` revision (blob-level SHAs asserted immutable), with mutants proving the replay header and exact native correlation are load-bearing.

### T042 — hard-kill recovery matrix: PASS
- Real `subprocess.Popen` workers killed with `process.kill()`; negative returncode asserted (a graceful exit fails the test). All five windows × ten families (50 cases), including the three task-named windows.
- Truthful outcomes per window: before attempt commit → no durable row and no bytes; before send → `PREPARED`, `RETRY_NATIVE_IDENTITY`, may_resend true; during response uncertainty → `IN_FLIGHT`/`UNKNOWN`, `QUERY_NATIVE_IDENTITY` or `OPERATOR_REVIEW` by reconciliation policy, may_resend false; after result commit → `SUCCEEDED`/`DELIVERED`, may_resend false. Recovery plans preserve the original native identity, cross-checked against the persisted payload reference.
- Fail-closed generation change while queued: `test_queued_attempt_rejects_changed_target_authority` — target configuration_generation and admission_generation change makes `mark_transport_started` raise `ProjectStoreError`; the attempt stays `PREPARED` pinned to old-generation authority.

### T043 — compound opt-out/late-recovery: PASS
- Single test per family (all ten) runs the mandated ordering as one sequence: pause at `response_received_before_result` → SIGKILL → immediate `disable_checkout_sync` → bounded lease records `terminal_unknown` and returns → production recovery re-entered with a **poisoned** physical sink under temporarily restored authority. Asserts zero recovery bytes, unchanged attempt-id set, unchanged captured bytes, `TERMINAL_UNKNOWN`/`terminal_unknown` preserved, result authority equals attempt authority (no old-generation rewrite), late `record_delivery_result(DELIVERED)` raises, and project B progressed. Event relay recovery additionally proves no fresh Event is minted.

### Anti-fake evidence
13 forgery oracle mutants (`_ORACLE_MUTANTS`) prove the independent expectation cannot be satisfied by consistent forged bytes + forged durable metadata; poisoned-sink tests prove each family reaches its real physical sink; partial-byte and local-only-relay witnesses are rejected.

## Concerns noted, not blocking

1. **Account/team change representation (T042).** The queued fail-closed test mutates target `configuration_generation` and `admission_generation` on the admission row (where account/teamspace identity lives) for one family only, explicitly labeled a delegated WP06 ledger control. Account-identity/teamspace-identity swaps as such are not separately mutated; the ledger's canonical representation of any such change is a generation bump, so coverage is adequate but indirect.
2. **Ordering-one × outcomes.** Pause-before-start is not crossed with the four outcomes; this is structurally correct (no transport occurs before cancel), and all four outcomes are exercised in the started ordering.
3. **Loopback fakes at the sink.** Physical sinks are observed loopback/fake transports with exact byte capture — exactly what the task's Test strategy prescribes; the paired SaaS c3 pin plus WP11's deployment witness cover the live-endpoint gap.
4. **Census duplicate row.** `record_project_opt_out` now appears twice in the grant census (Counter count 2), reflecting a real second grant site after WP07/WP08; the exact-count test locks it.

## Verdict

**APPROVED.** Every census family appears in the matrix; both revoke orderings and every kill window pass for every applicable family; the compound kill/opt-out/late-recovery test preserves terminal uncertainty as a single mandated sequence; a second project remains live and physically isolated throughout. No weakened assertions, no representative-family sampling, no sleep-based races, no exception-only simulations found.
