# Contract: `tension_unreconciled` finding

Emitted by two surfaces that must render this finding identically (SC-001): the
`spec-kitty charter pack consistency-check` command (existing `--json` flag pattern,
`src/specify_cli/cli/commands/charter/pack.py`) and the `charter activate` warning
path. Both consume the same `TensionFinding` value (data-model.md) — this contract is
the shape both surfaces must agree on, not two independent formats.

## JSON shape (consistency-check `--json` output)

Added to the existing `ConsistencyReport` JSON payload as a new top-level key,
alongside `coherent`, `unknown_references`, etc.:

```json
{
  "coherent": true,
  "unreconciled_tensions": [
    {
      "type": "tension_unreconciled",
      "pair": ["directive:024-locality-of-change", "directive:025-boy-scout-rule"],
      "resolution_paths": ["deactivate one side", "activate a reconciler"]
    }
  ]
}
```

**Invariants**:

- `coherent` MUST NOT be `false` solely because `unreconciled_tensions` is non-empty
  (NFR-001) — this key is additive/advisory.
- `pair` is always the sorted URN pair (lexicographically smaller first) — the same
  pair authored in either direction, or found from either endpoint, produces exactly
  one entry (INV-001, Edge Case: symmetric authoring drift).
- `resolution_paths` always has exactly 2 entries, both present verbatim as shown — a
  finding with only one path fails SC-001.
- Absence of a pair from this list, when both sides are active, is a defect for
  NFR-001 (a no-op checker returning `[]` fails the requirement) — the acceptance test
  for this contract MUST assert on a positive finding, not merely absence-of-error.

## `charter activate` warning text

Surfaced alongside existing activation warnings (FR-010) using the same `pair` +
`resolution_paths` data — human-readable, not JSON, but naming both artefacts and both
resolution paths verbatim (SC-001 applies to both surfaces identically).

Example:

```
Warning: directive:024-locality-of-change is in tension with
directive:025-boy-scout-rule. Resolve by: (1) deactivating one side, or
(2) activating a reconciler that bridges both (a single reconciler bridging
both sides, or two distinct active reconcilers each bridging one side).
```

## Non-finding case (edge case coverage)

Given an `in_tension_with` pair where only one side is in the active set: **no**
`tension_unreconciled` entry is emitted for that pair (spec.md US1, Acceptance
Scenario 3) — the check only fires on co-activated pairs.

## Error case (fail-closed)

If the DRG load required to compute this finding throws (malformed graph, missing
node, etc.), the error MUST surface in `ConsistencyReport.verification_errors` (an
existing field) — never silently reduce to an empty `unreconciled_tensions` list
(FR-009: "the DRG load fails closed"). A swallowed exception masquerading as "no
tensions found" is indistinguishable from the correct empty case and is exactly the
defect FR-009 exists to prevent.
