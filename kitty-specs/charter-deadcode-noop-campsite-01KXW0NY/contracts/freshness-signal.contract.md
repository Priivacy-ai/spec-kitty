# Contract — `synthesized_drg` freshness signal is no-op-correct

**Requirements:** FR-006; NFR-001, NFR-003. **Invariants:** INV-2, INV-6.
**Surface:** `src/specify_cli/charter_runtime/freshness/computer.py` (+ the preflight consumer
`charter_runtime/preflight/runner.py:_attempt_auto_refresh`).

## Statement

The `synthesized_drg` freshness signal drives whether the preflight auto-refresh shells out to
`charter synthesize`. It MUST report **fresh** when the on-disk doctrine artifacts already reflect
the current authoritative inputs (a genuine no-op), and **stale** only when a re-synthesize would
produce a materially different tracked artifact.

## Guarantees

| # | Given | Then `synthesized_drg` is |
|---|-------|---------------------------|
| F1 | doctrine artifacts already match current `charter.yaml` + pack inputs | **fresh** (no synthesize) |
| F2 | only volatile/non-substantive fields differ (timestamps, provenance — cf. `_VOLATILE_GRAPH_FIELDS`, #1912) | **fresh** (no synthesize / no churn) |
| F3 | `charter.yaml`, activation, or a pack input changed substantively | **stale** (synthesize runs) |
| F4 | doctrine artifact missing | **stale** (synthesize runs) |

## Rationale / failure modes to avoid

- **Under-fresh (the bug):** signal reports stale on F1/F2 → needless synthesize → tracked-doctrine
  churn → dirty tree (violates INV-1). This is what #2373's residual instance is.
- **Over-fresh (the anti-fix):** signal reports fresh on F3 → real change never regenerates → silent
  staleness (violates INV-2). The fix MUST NOT trade the churn for silent staleness.

## Test obligations (red-first, doctrine-tracked)

- F1/F2: after a clean synthesize, recompute freshness → fresh; run preflight twice → tree clean.
  This assertion is RED before the fix (reproduce per LM-1 in a doctrine-tracked checkout).
- F3: mutate `charter.yaml` → freshness stale → synthesize regenerates.
- Keep regeneration materialized on disk (INV-6) — do not convert readers to on-demand.
