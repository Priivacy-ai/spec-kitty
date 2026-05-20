# Research: Phase 4 Auth Identity-Boundary Canary Gate

**Mission**: phase4-canary-gate-01KS1W46
**Date**: 2026-05-20

---

## Decision 1: Fix-Substance Criteria for #1141

**Decision**: A fix is substantive iff the merge commit modifies `OfflineQueue.queue_event` or its callers in the `fire_saas_fanout → emit_wp_status_changed` chain in a way that changes the queuing logic (not just log output), AND at least one test is added or modified that fails on the pre-fix code and passes on the post-fix code.

**Rationale**: `rc15` landed a diagnostic breadcrumb in the fanout path that confirmed the correct transition was visible at fanout invocation time. The evidence at `rc15-attempt1/run-1.json` scenario 4 shows the canary peek helper still gets `from='for_review' to='in_review'` instead of `from='in_review' to='planned'`. This means the rollback event is either not reaching `queue_event`, or it is being coalesced/overwritten by a prior event.

**Key code path**: `src/specify_cli/sync/queue.py` — `OfflineQueue.queue_event` implements coalesce-by-key logic for `MissionDossierArtifactIndexed` and `MissionDossierSnapshotComputed` via an INSERT+UPDATE split pattern. `WPStatusChanged` events must NOT be coalesced — each transition is a discrete, ordered, uniquely-keyed event. If `WPStatusChanged` was accidentally being coalesced or if the row-eviction logic was silently replacing it, that would produce exactly the scenario 4 failure.

**Verification checklist for WP01**:
1. `git show <merge-commit> -- src/specify_cli/sync/queue.py src/specify_cli/status/adapters.py` — confirm non-logging changes.
2. `git show <merge-commit> -- tests/sync/` — confirm a test with `in_review → planned` assertion was added.
3. If only `logger.*` lines changed: reject fix as diagnostic-only.

**Alternatives considered**: Trusting the issue's CLOSED state alone — rejected because rc14's fix was also merged but only shipped diagnostic plumbing, requiring re-open.

---

## Decision 2: Fix-Substance Criteria for #1182

**Decision**: A fix is substantive iff `sync now`'s top-level Synced/Duplicates/Errors counter no longer counts durably-queued events (those that were queued but whose final-sync window expired) as `unknown` errors.

**Rationale**: `rc15-attempt1/run-1.json` scenarios 1 and 2 show `sync.event_loop_unavailable severity=warning` and `Errors: 24 (unknown: 24)` / `Errors: 27 (unknown: 3)`. The events ARE durably queued (this was confirmed by the rc15 fixes to the FORBIDDEN_KEY gate). The problem is the top-level reporter — it sees a non-zero exit from the in-process 5s final-sync flush and classifies all unflushed-but-queued events as errors rather than as `queued_for_next_sync` or similar.

**Three candidate fixes** (from #1182 issue description):
- Option A: Catch the `EventLoopUnavailable` condition and report affected events as `queued_pending` rather than `unknown_error`.
- Option B: Extend the final-sync flush timeout past 5s (rejected: changes behavior across all CLI contexts).
- Option C: Remove `sync now` from the scenarios' success criteria and rely solely on queue-peek state (rejected: weakens the contract).

Option A is the expected fix. WP01 verifies the diff implements Option A or an equivalent change to the error-classification branch.

---

## Decision 3: RC-Cut Authority

**Decision**: This gate does NOT cut an RC autonomously. If the latest published prerelease is still v3.2.0rc15 after both blockers are confirmed CLOSED, WP02 stops and reports. Cutting rc16 requires explicit operator instruction.

**Rationale**: CLAUDE.md: "NEVER create releases without explicit user instruction!" RC version bumps must follow the CLAUDE.md release workflow (`pyproject.toml` → `CHANGELOG.md` → tag → push → monitor `release.yml`). Files to update when instructed: `pyproject.toml` (`version = "3.2.0rc16"`), `CHANGELOG.md` (new entry), `.kittify/metadata.yaml` (if version key present).

**Minimum post-install verification**:
```bash
/Users/robert/.local/bin/spec-kitty --version                   # confirms installed version
/Users/robert/.local/pipx/venvs/spec-kitty-cli/bin/python \
  -c "import specify_cli.sync.owner, specify_cli.sync.preflight; print('ok')"
SPEC_KITTY_ENABLE_SAAS_SYNC=1 /Users/robert/.local/bin/spec-kitty sync status --check --json
```

---

## Decision 4: Evidence File Schema (from rc15-attempt1)

**Decision**: Canary run result JSON has the following top-level keys (confirmed from `rc15-attempt1/run-1.json`):

```json
{
  "outcome": "fail",           // "pass" | "fail" — this is the gate field
  "run_id": "<ULID>",
  "run_number": 1,
  "cli_version": "3.2.0rc15",
  "events_package_version": "5.1.0",
  "timestamp": "<ISO8601>",
  "scenarios": [
    {
      "id": 1,
      "name": "Fresh Authenticated Mission",
      "status": "fail",
      "failure_mode": "sync.event_loop_unavailable",
      "details": "..."
    }
  ]
}
```

The gate passes iff `"outcome": "pass"` at top level. The harness sets this only when all four scenario statuses are `"pass"`.

**Evidence preservation rule**: Each attempt produces a subdirectory at `artifacts/sync_identity_boundary/<rc-tag>-attempt<N>/` containing `latest.json` and `run-1.json` (for single-run) or `runs/run-{1..4}.json` (for four-run). Prior attempt dirs (e.g., `rc15-attempt1/`) are read-only — do not overwrite.

---

## Decision 5: Teamspace MVP Canary Failure Triage

**Decision**: Each failure mode has a specific diagnosis path; none permit SaaS mutation as a fix.

| Failure Pattern | Diagnosis | Permitted Action |
|-----------------|-----------|-----------------|
| `mission did not materialize within 60s` | Polling helper not connected or SaaS drain stalled | Verify drain queue; check e2e#40 polling helper is in use |
| HTTP 413 on sync | CLI payload too large | Investigate CLI payload size; do NOT raise ingress cap |
| `/health/ready/` 503 | Readiness contamination or infra terminal_failed nonzero | Investigate infra failures; do NOT fix by deleting rows |
| `terminal_failed` or `DrainMaterializationRejected` | Either planning#16 regression or business_rule row (acceptable) | Verify `last_failure_class`; if `business_rule` and readiness ignores it, acceptable |

**Alternatives considered**: Raising ingress cap to suppress 413 — explicitly excluded by start-here.md stop conditions.

---

## Open Questions

None. All decisions resolved. Gate is ready for WP generation.
