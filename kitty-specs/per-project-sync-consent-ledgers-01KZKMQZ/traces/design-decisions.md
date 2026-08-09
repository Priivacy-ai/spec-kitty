# Design Decisions Trace

## D-001 — UUID-owned ProjectSyncStore

**Decision**: One canonical UUID owns one `sync.db`; a ProjectSyncStore unit of work owns every live connection and outer transaction.  
**Reason**: A common filename is not atomic if components independently connect/commit; the unit binds control, epochs, journal, attempts, and results.  
**Status**: accepted.

## D-010 — Durable uncertainty and explicit history capability

**Decision**: Admission operations and transport attempts persist before I/O with native idempotency/audience identity; sealed history can move only through a confirmed immutable preview cohort.  
**Reason**: Process death must not invent success or silently resend, and later opt-in must not become retroactive disclosure consent.  
**Status**: accepted.

## D-011 — Current writers participate in cutover

**Decision**: Daemons and foreground writers in the current version share the layout-generation barrier; sources are read-only logical SQLite snapshots with WAL semantics. Only unrecognized old binaries can create non-deliverable late residue.  
**Reason**: Quiescing only the daemon leaves a capture-loss window, while opening sources through normal constructors mutates evidence.  
**Status**: accepted.

## D-002 — One project consent authority

**Decision**: A versioned project-control row is the only grant; every legacy/path/repo/index/config source is non-granting migration input.  
**Reason**: Multiple granting sources permit stale inheritance and disagreement.  
**Status**: accepted.

## D-003 — Capture local, gate egress conjunctively

**Decision**: Project-isolated local capture is allowed without hosted consent; epochs seal pre-consent and revoked-period rows, and every send requires kill switch, current eligible epoch, local grant, exact-target admission, and per-write proof.  
**Reason**: Local durability is not disclosure and must work offline; later opt-in is not retroactive consent for accumulated history.  
**Status**: accepted; supersedes only #3030 shared-store/capture coupling.

## D-004 — Exclusive verified cutover

**Decision**: Quiesce recognized daemons, copy without source mutation, verify exact IDs/status/attempts/targets/timestamps/hashes, atomically cut over, and make legacy stores/late writes diagnostic-only. Unknown identity quarantines and old grants require re-consent.  
**Reason**: Old writers and live dual-read can duplicate or leak; inferred identity can misassign data.  
**Status**: accepted.

## D-005 — Opt-out cross-process barrier

**Decision**: Final transport and genuine result recording hold a bounded project lease; opt-out cancels pre-start work and waits for already-started settlement before it seals/returns. Remote revoke status is separate.  
**Reason**: An unlocked final check cannot close the check/use race, and discarding a real result would falsify disclosure evidence.  
**Status**: accepted.

## D-006 — SaaS contract upstream

**Decision**: Core consumes the SaaS mission's canonical admission/refusal contract and never invents a parallel protocol.  
**Reason**: Server-side enforcement owns hosted admission semantics.  
**Status**: accepted.

## D-007 — Historical cohort excluded

**Decision**: This mission never inspects, mutates, or declares disposition of the 1,322 events.  
**Reason**: That operation requires a separate Human-in-Charge decision and audit.  
**Status**: accepted; #585 remains open.

## D-008 — Daemon hints only narrow

**Decision**: A fresh deny/revoke hint may suppress a store open; missing, stale, unknown, pending, or possible grant requires an authoritative read. No hint can express grant.  
**Reason**: Discovery performance must not create another consent authority.  
**Status**: accepted.

## D-009 — Split cross-repository proof

**Decision**: The conforming CLI proves B–F absent from request bytes, bypass clients prove server refusal, and a real stale-generation race proves terminal client parking.  
**Reason**: A correct client cannot simultaneously omit and send the same unadmitted payloads.  
**Status**: accepted.
