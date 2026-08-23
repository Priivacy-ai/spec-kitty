# Contract: setup-plan result envelope and hosted-effect boundary

## Authority

The local verification outcome is the primary command result. Hosted-delivery
diagnostics are additive warnings and never determine the process exit.

## Structured result

`--json` emits exactly one JSON object. Existing primary fields remain unchanged. When
present, warnings use:

```json
{
  "result": "success",
  "phase_complete": true,
  "warnings": [
    {
      "code": "SAAS_SYNC_AUTH_UNKNOWN",
      "severity": "warning",
      "hosted_disposition": "refused",
      "message": "Hosted sync was skipped because local authentication could not be evaluated.",
      "remediation": ["Inspect local authentication storage before retrying hosted sync."]
    }
  ]
}
```

Allowed warning codes for this Mission:

- `SAAS_SYNC_UNAUTHENTICATED`
- `SAAS_SYNC_AUTH_UNKNOWN`
- `SAAS_SYNC_BOUNDARY_UNSAFE`
- an existing or explicitly introduced routing-specific code for authenticated/no-route
  cases; it must never be an authentication code.

Warnings are deduplicated and ordered authentication, structural boundary, delivery
route. `details` may include sanitized preflight evidence but never credentials or raw
exception dumps.

## Human result

Human mode renders hosted diagnostics as warnings and then renders the normal local
result. It must not describe local setup-plan as refused, failed, or unauthenticated
when only hosted delivery was refused.

## Binding local outcome matrix

| Local condition | Primary payload contract | Exit |
|---|---|---:|
| Substantive complete plan | `result=success`, `phase_complete=true` | 0 |
| Newly created pristine scaffold | `result=success`, `phase_complete=false`, `scaffold_only=true` | 0 |
| Populated but insufficient plan | `result=blocked`, `phase_complete=false`, current `blocked_reason` | 0 |
| Committed pristine/insufficient plan | `result=blocked`, `phase_complete=false`, current `blocked_reason` | 0 |
| Non-substantive or uncommitted spec | `result=blocked`, `phase_complete=false`, `error_code=SPEC_NOT_SUBSTANTIVE_OR_UNCOMMITTED` | 0 |
| Missing spec | current `SPEC_FILE_MISSING` payload | 1 |
| Template configuration error | `result=error`, `phase_complete=false`, `error_code=TEMPLATE_CONFIGURATION_ERROR` | 1 |
| Missing template or generic local exception | current error payload | 1 |
| Project/context/git resolution failure | current payload | current exit |

Before refactoring, tests capture all existing primary fields for each row. For every
hosted-readiness variant, those fields and the exit remain identical. Only `warnings`
may be added. Structural warnings are available only after repository-root resolution.

## Authentication mapping

| Evaluation | Diagnostic | Hosted effects |
|---|---|---|
| authenticated | none | depends on boundary and route |
| logged out | `SAAS_SYNC_UNAUTHENTICATED` | refused |
| unknown | `SAAS_SYNC_AUTH_UNKNOWN` | refused |

An expired access token with a usable refresh token is authenticated. Queue-scope
availability does not participate.

## Structural mapping

- Safe preflight: no structural warning.
- Returned unsafe preflight: `SAAS_SYNC_BOUNDARY_UNSAFE` with sanitized `to_dict()`
  evidence.
- Preflight evaluation exception: `SAAS_SYNC_BOUNDARY_UNSAFE` with a stable
  `boundary_evaluation_failed` reason and no raw exception text.

The latter two refuse hosted effects and do not change local status or exit.

## Hosted-effect boundary

When `allow_effects=false`, all of these have zero calls:

- lifecycle SaaS fan-out and offline event queue;
- dossier enqueue, capture-for-hosted-publication, or upload;
- body-upload queue;
- daemon or dashboard publication;
- direct hosted transport discovered in the setup-plan call graph.

Local lifecycle JSONL, plan/spec file operations, documentation wiring, safe commits,
and local result emission continue whenever their local workflow stage is eligible.

## Compatibility and exclusions

- SaaS-disabled invocations do not run hosted-readiness probes and add no warnings.
- `sync now` and other hosted-only commands keep their current refusal semantics.
- No network auth probe, token refresh, strict-sync flag, queue migration, or general
  token-expiry UX is introduced.
