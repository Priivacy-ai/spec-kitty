# Quickstart: deterministic matrix & tracer writes

How an agent uses the mission's new surfaces. All commands are idempotent, emit `--json`, and route to the correct partition automatically — no source-reading, no hand-editing.

## Record an acceptance-matrix verdict
```bash
spec-kitty agent acceptance-verdict --mission <handle> \
  --criterion FR-001 --result pass --verification-method "unit+integration" --actor claude --json
```
Canonical acceptance now persists the recomputed `overall_verdict` even with no negative invariants (no more stale `pending`).

## Set an issue-matrix per-item verdict
```bash
spec-kitty agent issue-verdict --mission <handle> \
  --issue "#1726" --verdict verified-already-fixed --wp WP01 --actor claude --json
```
Writes `issue-matrix.json` (single canonical artifact; the dashboard renders from JSON). A legacy `issue-matrix.md` mission is migrated on this first write.

## Capture a finding from a lane (no lane block)
```bash
spec-kitty agent tracer-append --mission <handle> \
  --category tooling-friction --entry "move-task hung on sync fan-out" --actor claude --json
```
Routes to the coordination surface; leaves zero `kitty-specs/` commits on the lane branch; `move-task` is not blocked afterward.

## Bulk-migrate legacy issue matrices
```bash
spec-kitty issue-matrix migrate --json          # all missions
spec-kitty issue-matrix migrate --mission <handle> --json
```

## What changed structurally (for reviewers)
- `issue-matrix.md` → `issue-matrix.json` (no markdown render); all consumers read JSON.
- Row-aware merge driver: two lanes editing disjoint rows now union without clobber.
- Execution lanes branch from the recorded planning-artifact commit → lane writes survive consolidation.
- Issue-reference discovery scans all mission artifacts; zero-reference missions record Gate 4 `not_applicable`.
- Unroutable writes (deleted `target_branch`) return a structured **zero-write refusal** disclosing #3033 — never a fallback write.
