# Contract — `doctor doctrine` health reporting (FR-001, FR-002)

Behavioral contract for the I-1 fix. The proving test (`tests/specify_cli/test_doctor_doctrine.py`, new case) drives the real CLI / `_collect_profile_health` seam — not a hand-built `PackHealth`.

## C1 — Inline-ref-invalid profile ⇒ unhealthy + surfaced
- **Given** a project whose org doctrine pack contains a profile with a forbidden inline-reference field (e.g. `tactic_refs`)
- **When** `spec-kitty doctor doctrine --json` runs
- **Then** the JSON reports `healthy: false` for that pack
- **And** the invalid profile is surfaced with `{path, id, error_summary}`
- **And** the other (valid) profiles remain visible (the invalid one does not blank out the surface)
- **And** the process exit code is non-zero (consistent with the existing unhealthy path)

## C2 — No fail-to-green
- The report MUST NEVER be `healthy: true` as a side effect of a profile load raising. An empty collected set (because loading raised) is `healthy: false`, not vacuously true.

## C3 — Schema-invalid parity (regression guard)
- The existing schema-invalid-profile behavior (already `healthy: false` + surfaced) MUST remain unchanged; the inline-ref case behaves identically.

## C4 — General load contract unchanged (R1)
- `resolve_profile`/`get_ancestors` and other general callers retain their existing inline-ref behavior; only the doctor health consumer changes. (No assertion in this contract — covered by NFR-001 regression.)
