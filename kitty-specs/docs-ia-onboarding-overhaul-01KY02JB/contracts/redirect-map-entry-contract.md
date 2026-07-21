# Contract: Redirect Map Entry

**Owner**: existing `scripts/docs/redirect_map.yaml` + `scripts/docs/redirect_stub_generator.py`
**Requirement**: FR-003, FR-009, NFR-006 (this mission is a consumer, not the owner — no schema
change to the existing mechanism)

## Obligation

Every path this mission moves or removes from `docs/` — chiefly during IC-01 (contributor
runbooks relocated out of `guides/`) and any consolidation under FR-009 — gets exactly one
entry added to `redirect_map.yaml` before that move is considered complete.

## Entry shape (existing schema, unchanged)

```yaml
- old_path: guides/pr-landing.html
  new_path: development/pr-landing.html
```

## Verification

`redirect_baseline_urls.json` (existing, from `common-docs-consolidation`) is the denominator
for confirming no baseline URL 404s after this mission's moves — the same NFR-006 obligation
this mission's own tasks phase will re-verify against the pre-mission URL set, extended with
this mission's own moved paths.

## What this mission does NOT change

The generator script's behavior, the stub HTML it emits (`<meta http-equiv="refresh">`), or the
map's schema — all reused as-is (C-001 spirit: don't touch working pipeline internals without
cause).
