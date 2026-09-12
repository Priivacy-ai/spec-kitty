# Contract: `spec-kitty dispatch --dry-run` Output (mission `dispatch-dry-run-route-only-01M1HKV2`)

> Companion to `kitty-specs/do-dispatch-open-op-lifecycle-01KTSJ2H/contracts/cli-do-output.md`
> (the archived, byte-frozen contract for `spec-kitty do`'s real open-Op dispatch payload — see
> `tests/architectural/test_archive_root_byte_identical.py`, NFR-002). That doc's `"status":
> "open"` JSON example predates this mission and does not yet show the `alternatives` field
> documented below; this file is intentionally self-contained so a reader does not need to
> cross-reference the archived doc to understand the `--dry-run` shape.

## `--dry-run` output

`spec-kitty dispatch "<request>" [--profile <id>] --dry-run [--json]`:

1. Routes request → profile/action exactly as real dispatch does (same `ActionRouter`, same
   explicit-`--profile` bypass, same empty-charter fallback).
2. Assembles governance context and runs the glossary chokepoint scan — both already read-only,
   unchanged from the real path.
3. Writes **nothing**: no `kitty-ops/<id>.jsonl`, no `kitty-ops/ops-index.jsonl` line, no
   `.kittify/events/glossary/*.jsonl` file, no SaaS propagator submit. No Op is opened, so there
   is no close contract to advertise.

### Success shape

Reuses the real-dispatch payload's field set (`InvocationPayload.to_dict`) minus
`invocation_id` and `close_contract`, plus a terminal `"status": "dry_run"`:

```json
{
  "status": "dry_run",
  "profile_id": "implementer-fixture",
  "profile_friendly_name": "Implementer (fixture)",
  "action": "implement",
  "governance_context_text": "...",
  "governance_context_hash": "b6b54201f23d00f5",
  "governance_context_available": true,
  "router_confidence": "canonical_verb",
  "glossary_observations": { "matched_urns": [], "high_severity": [], "all_conflicts": [], "tokens_checked": 3, "duration_ms": 0.4, "error_msg": null },
  "recommendation": null,
  "empty_charter_fallback": false,
  "alternatives": []
}
```

### `ROUTER_AMBIGUOUS` shape (FR-009)

A request that would raise `ROUTER_AMBIGUOUS` under real dispatch (exit 1) instead exits **0**
under `--dry-run`, with no winner — the deliberate UI-probing affordance the flag exists for.
This is NOT an `InvocationPayload` (no profile was resolved, so no governance context, no
recommendation, no glossary scan tied to a winner exists to report):

```json
{
  "status": "dry_run",
  "profile_id": null,
  "action": null,
  "router_confidence": "ambiguous",
  "alternatives": [
    {"profile_id": "implementer-a", "action": "implement", "confidence": "canonical_verb", "match_reason": "token 'implement' matched implementer canonical verb"},
    {"profile_id": "implementer-b", "action": "implement", "confidence": "canonical_verb", "match_reason": "token 'implement' matched implementer canonical verb"}
  ]
}
```

`ROUTER_NO_MATCH` and an unknown `--profile` (`PROFILE_NOT_FOUND`) still exit 1 with the same
structured error JSON as real dispatch — there is no partial routing signal worth reporting in
either case.

## `alternatives` on real dispatch (`spec-kitty do`, `--json`)

WP2/#3840 (FR-005) additionally threads the router's already-computed losing candidates onto the
real open-Op dispatch payload — the same list shape shown above, always present (never `null`),
even when empty. `InvocationPayload.to_dict()` (`src/specify_cli/invocation/executor.py`)
serializes `alternatives` alongside every other slot, so it now appears in the `"status": "open"`
JSON envelope too, and in `spec-kitty do`'s rich-console rendering:

```
Alternatives considered (N):
  <profile_id> / <action>  (<confidence>) — <match_reason>
```

Previously only `--dry-run`'s rich renderer printed this block; PR-BOUNDARY-002 closed that
unforced console/JSON asymmetry so the real dispatch console path renders it too. The archived
`cli-do-output.md`'s `"status": "open"` JSON example was not updated to add this field — see the
note at the top of this file — because that file is byte-frozen
(`tests/architectural/test_archive_root_byte_identical.py`, NFR-002); this paragraph is the
authoritative record of the field until a future mission is scoped to touch that archive's own
mission dossier.
