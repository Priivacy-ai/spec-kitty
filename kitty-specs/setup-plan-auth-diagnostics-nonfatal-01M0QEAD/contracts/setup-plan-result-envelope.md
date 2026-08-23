# Contract: setup-plan local result with hosted-sync diagnostics

## Scope

This contract applies to `spec-kitty agent mission setup-plan` when hosted SaaS sync is enabled. It is additive to existing local result fields and does not change the local plan-completeness rules.

## Structured output

The command emits one JSON object. Its existing local fields remain primary. When hosted readiness is non-ready, the object includes:

```json
{
  "result": "success",
  "phase_complete": true,
  "mission_slug": "example-mission-01ABCDEF",
  "warnings": [
    {
      "code": "SAAS_SYNC_UNAUTHENTICATED",
      "message": "Hosted sync was skipped because no usable local SaaS session is available.",
      "remediation": ["Run `spec-kitty auth login` when an authorized operator chooses to restore hosted sync."]
    }
  ]
}
```

Allowed warning codes:

| Code | Condition |
|---|---|
| `SAAS_SYNC_UNAUTHENTICATED` | Local auth authority conclusively reports either logged-out state. |
| `SAAS_SYNC_AUTH_UNKNOWN` | Local auth authority cannot determine auth state. |
| `SAAS_SYNC_BOUNDARY_UNSAFE` | Structural sync preflight reports one or more unsafe conditions. `details.preflight` contains its structured projection. |

Structural example:

```json
{
  "code": "SAAS_SYNC_BOUNDARY_UNSAFE",
  "message": "Hosted sync was skipped because the local sync boundary is structurally unsafe.",
  "remediation": ["Resolve the reported sync-boundary diagnostics before retrying hosted delivery."],
  "details": {
    "preflight": {
      "ok": false,
      "mismatches": [],
      "orphan_records": [],
      "unreadable_owner_record": true,
      "project_store_diagnostic": null
    }
  }
}
```

Rules:

1. The command emits at most one JSON document.
2. `warnings` is additive; it does not replace `result`, `phase_complete`, `blocked_reason`, `error_code`, or branch fields.
3. A complete local plan exits 0 even when either warning is present.
4. An incomplete or invalid local plan retains its established nonzero/blocked behavior with warnings attached where the result envelope supports them.
5. Auth warning order precedes structural warning order.
6. A valid supported session emits neither auth warning, regardless of queue-scope availability.
7. Hosted enqueue/delivery is not attempted when any auth or structural warning makes it unsafe.

## Human-readable output

Human output prints each hosted diagnostic with `Warning:` severity and then prints the normal local setup-plan result. It must not use `Error`, `Refusing setup-plan`, or wording that implies local verification was skipped. Structural remediation may retain the preflight's specific corrective guidance.

## Local-result authority

For identical local files and branch state, changing only auth or structural hosted-sync state must not change the local result classification, `phase_complete`, local blocked/error reason, or process exit status.

## Side-effect boundary

When hosted safety is false, setup-plan must still permit repository and mission resolution, spec/plan checks, artifact writes, local lifecycle JSONL events, documentation wiring, and safe local git commit routing.

It must refuse dossier upload/enqueue, hosted queue writes attributable to setup-plan, and direct hosted delivery attributable to setup-plan.

This contract does not change `sync now` or any command whose requested operation is itself a hosted-sync side effect.
