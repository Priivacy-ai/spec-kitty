# Contract: charter pack consistency-check

**Command**: `spec-kitty charter pack consistency-check`

## Synopsis

Validates that the project's current charter activation state is coherent: all activated artifact IDs exist in doctrine, no unknown references, and the built-in spec-kitty doctrine pack is the default baseline. Returns structured output and a non-zero exit code if incoherence is found.

## Arguments

None (reads from `.kittify/config.yaml` and the local doctrine catalog).

## Behavior

1. Load current `PackContext` from `.kittify/config.yaml`.
2. For each kind with an explicit activation set (non-None):
   - Query doctrine catalog for that kind's available artifact IDs.
   - For each activated ID: check it exists in doctrine. Collect unknowns.
   - Check no duplicate IDs in activation set.
3. Check cross-kind references: for each activated artifact that has DRG edges to other kinds, verify those referenced artifacts are also activated (or that the referenced kind has no explicit restriction — `None` means all available).
4. Report:
   - `coherent: true/false`
   - `unknown_references`: IDs in activation set not present in doctrine
   - `missing_from_doctrine`: IDs referenced via DRG edges that are not in doctrine at all
   - `kind_violations`: IDs activated under the wrong kind
   - `suggestions`: human-readable resolution guidance per incoherence

## Output (JSON, --json flag)

```json
{
  "coherent": false,
  "unknown_references": ["directive/old-deprecated-guide"],
  "missing_from_doctrine": [],
  "kind_violations": [],
  "suggestions": [
    "directive/old-deprecated-guide: Not found in doctrine. Run 'charter deactivate directive old-deprecated-guide' to remove."
  ]
}
```

## Output (human-readable)

```
Charter Pack Consistency Check
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✗ INCOHERENT

Issues found:
  directive/old-deprecated-guide — not found in doctrine
    → Run: spec-kitty charter deactivate directive old-deprecated-guide

Run 'spec-kitty charter list --show-available' to see current activation state.
```

On success:
```
Charter Pack Consistency Check
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✓ COHERENT — All activated artifacts are present in doctrine.
```

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Coherent — all checks pass |
| 1 | Incoherent — one or more unknown references or violations found |
| 2 | config.yaml read error or doctrine unavailable |
