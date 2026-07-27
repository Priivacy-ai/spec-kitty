# Issue matrix — event-sync-retention-delivery-01KVYWRG

Per FR-037 of the spec-kitty-mission-review skill Gate-4. One row per issue referenced in spec.md.

| Issue | Title | Verdict | Evidence ref |
|-------|-------|---------|--------------|
| #2130 | Event sync retention/delivery design synthesis (PR) — folded into spec | fixed | Design folded into spec.md L6 and implemented across all 12 WPs (journal/ledger/dispatcher/receivers/migration/CLI), merged on `mission/event-sync-retention-delivery`. |
| #2146 | Target authority prerequisite — single resolved sync target | deferred-with-followup | Resolver + status/scope leg delivered by WP01 (`sync/target_authority.py`) + WP02 (config/runtime/auth/readiness/preflight/owner wired); FR-016 status/scope adequate. Follow-up: bind `sync/client.py` (WebSocket) + `tracker/saas_client.py` (tracker) to `ResolvedSyncTarget.resolved_server_url` — those sites are outside this mission's owned_files (DRIFT-2 in mission-review-report.md). |
| #2144 | Capture-before-drain invariant — no event loss on drain | fixed | WP03 capture-first: Teamspace-bound facts written to `event_journal` before SaaS/auth/team/network gates (`sync/emitter.py::_emit` before delivery gates); `test_capture_first.py::test_emit_writes_journal_before_delivery_gates_when_disabled`. |
| #2165 | Docs reorganization context — acknowledged, out of mission scope | deferred-with-followup | spec.md L8 (acknowledged docs-reorg context, does not move this mission's artifacts). Follow-up: #2165 stays open for a separate docs-reorg effort |
| #2131 | Multi-target fan-out — declined for MVP (single active target) | deferred-with-followup | spec.md L128 C-003 (fan-out declined; ledger schema kept extensible). Follow-up: #2131 deferred post-MVP — re-open for many-targets ledger extension |

Valid `Verdict` values: `fixed`, `verified-already-fixed`, `deferred-with-followup`, `in-mission` (being fixed by a later WP in this mission; must reach a terminal verdict before mission `done`).

## Deferred follow-ups (post-merge mission review, 2026-06-29)

- **C-008 / DRIFT-1 — OPT_OUT discard-safety runtime enforcement.**
  Status: deferred-with-followup.
  Follow-up handle: wire `discard_decision` into the capture path (refuse/audit a Teamspace-bound or fail-closed UNKNOWN family) as part of retiring the legacy destructive `queue.py` drain (RISK-1 dual-drain). Live wiring requires (a) a production family→`FamilyClassification` source and (b) a single live capture-time discard site, neither of which exists in the transitional dual-drain state. The public surface is held in the `_CATEGORY_C_EVENT_SYNC_RETENTION_DELIVERY` allowlist of `tests/architectural/test_no_dead_symbols.py` until then.
  Rationale: the discard machinery (`delivery/config.py`: `FamilyClassification`, `DiscardDecision`/`DiscardDecisionKind`, `DiscardAuditRecord`, `AuditSink`, `JsonlAuditSink`, `discard_decision`) is implemented and unit-tested but is not yet wired into a live capture-time path; a Teamspace-bound family is not silently dropped today because the emitter's capture-first write is unconditional and OPT_OUT (retention OFF) is not yet enforced at capture.
