---
verdict: pass_with_notes
mode: post-merge
reviewed_at: 2026-06-29T19:34:27.825072+00:00
findings: 49
gates_recorded:
  - id: gate_1
    name: wp_lane_check
    command: spec-kitty review (internal gate 1)
    exit_code: 0
    result: pass
  - id: gate_2
    name: dead_code_scan
    command: spec-kitty review (internal gate 2)
    exit_code: 1
    result: fail
  - id: gate_3
    name: ble001_audit
    command: spec-kitty review (internal gate 3)
    exit_code: 0
    result: pass
issue_matrix_present: true
mission_exception_present: false
---

## Findings

- **dead_code** `src/specify_cli/delivery/config.py` — `UnknownModeError`: no non-test callers found
- **dead_code** `src/specify_cli/delivery/config.py` — `MissingExternalEndpointError`: no non-test callers found
- **dead_code** `src/specify_cli/delivery/config.py` — `ResolvedTarget`: no non-test callers found
- **dead_code** `src/specify_cli/delivery/config.py` — `build_teamspace`: no non-test callers found
- **dead_code** `src/specify_cli/delivery/config.py` — `build_external`: no non-test callers found
- **dead_code** `src/specify_cli/delivery/config.py` — `build_teamspace`: no non-test callers found
- **dead_code** `src/specify_cli/delivery/config.py` — `build_external`: no non-test callers found
- **dead_code** `src/specify_cli/delivery/config.py` — `ResolvedPolicy`: no non-test callers found
- **dead_code** `src/specify_cli/delivery/config.py` — `FamilyClassification`: no non-test callers found
- **dead_code** `src/specify_cli/delivery/config.py` — `DiscardDecisionKind`: no non-test callers found
- **dead_code** `src/specify_cli/delivery/config.py` — `DiscardAuditRecord`: no non-test callers found
- **dead_code** `src/specify_cli/delivery/config.py` — `DiscardDecision`: no non-test callers found
- **dead_code** `src/specify_cli/delivery/config.py` — `AuditSink`: no non-test callers found
- **dead_code** `src/specify_cli/delivery/config.py` — `JsonlAuditSink`: no non-test callers found
- **dead_code** `src/specify_cli/delivery/config.py` — `discard_decision`: no non-test callers found
- **dead_code** `src/specify_cli/delivery/dispatcher.py` — `DispatchFailure`: no non-test callers found
- **dead_code** `src/specify_cli/delivery/dispatcher.py` — `from_counts`: no non-test callers found
- **dead_code** `src/specify_cli/delivery/interfaces.py` — `gates_satisfied`: no non-test callers found
- **dead_code** `src/specify_cli/delivery/ledger.py` — `LedgerRow`: no non-test callers found
- **dead_code** `src/specify_cli/delivery/ledger.py` — `init_ledger`: no non-test callers found
- **dead_code** `src/specify_cli/delivery/ledger.py` — `record_success`: no non-test callers found
- **dead_code** `src/specify_cli/delivery/ledger.py` — `record_duplicate`: no non-test callers found
- **dead_code** `src/specify_cli/delivery/ledger.py` — `record_pending`: no non-test callers found
- **dead_code** `src/specify_cli/delivery/ledger.py` — `record_rejected`: no non-test callers found
- **dead_code** `src/specify_cli/delivery/receivers.py` — `GateKind`: no non-test callers found
- **dead_code** `src/specify_cli/delivery/receivers.py` — `ReceiverGate`: no non-test callers found
- **dead_code** `src/specify_cli/delivery/receivers.py` — `is_satisfied`: no non-test callers found
- **dead_code** `src/specify_cli/delivery/receivers.py` — `HttpResponse`: no non-test callers found
- **dead_code** `src/specify_cli/delivery/receivers.py` — `map_batch_response`: no non-test callers found
- **dead_code** `src/specify_cli/delivery/receivers.py` — `received_events`: no non-test callers found
- **dead_code** `src/specify_cli/delivery/receivers.py` — `received_event_ids`: no non-test callers found
- **dead_code** `src/specify_cli/delivery/status_report.py` — `evaluate_gc_suggestion`: no non-test callers found
- **dead_code** `src/specify_cli/event_journal/coalesce.py` — `DeliveredAnywhereQuery`: no non-test callers found
- **dead_code** `src/specify_cli/event_journal/coalesce.py` — `SupersedeMarker`: no non-test callers found
- **dead_code** `src/specify_cli/event_journal/coalesce.py` — `read_supersede_markers`: no non-test callers found
- **dead_code** `src/specify_cli/event_journal/coalesce.py` — `CoalescingStrategy`: no non-test callers found
- **dead_code** `src/specify_cli/event_journal/journal.py` — `read_blocked`: no non-test callers found
- **dead_code** `src/specify_cli/sync/migrate_journal.py` — `migration_target_token`: no non-test callers found
- **dead_code** `src/specify_cli/sync/migrate_journal.py` — `SourceDb`: no non-test callers found
- **dead_code** `src/specify_cli/sync/migrate_journal.py` — `discover_source_dbs`: no non-test callers found
- **dead_code** `src/specify_cli/sync/migrate_journal.py` — `MigrationConflict`: no non-test callers found
- **dead_code** `src/specify_cli/sync/migrate_journal.py` — `record_provenance`: no non-test callers found
- **dead_code** `src/specify_cli/sync/migrate_journal.py` — `record_conflict`: no non-test callers found
- **dead_code** `src/specify_cli/sync/migrate_journal.py` — `provenance_for`: no non-test callers found
- **dead_code** `src/specify_cli/sync/migrate_journal.py` — `SourceOutcome`: no non-test callers found
- **dead_code** `src/specify_cli/sync/migrate_journal.py` — `merge_into`: no non-test callers found
- **dead_code** `src/specify_cli/sync/queue.py` — `resolved_scope_db_path`: no non-test callers found
- **dead_code** `src/specify_cli/sync/target_authority.py` — `QueueScopeStatus`: no non-test callers found
- **dead_code** `src/specify_cli/sync/target_authority.py` — `SyncTargetSplitBrainError`: no non-test callers found
