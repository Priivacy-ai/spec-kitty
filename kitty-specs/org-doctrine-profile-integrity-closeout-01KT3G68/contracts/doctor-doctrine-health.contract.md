# Contract — `doctor doctrine` health reporting (FR-001, FR-002)

Behavioral contract for the I-1 fix. The proving test (`tests/specify_cli/test_doctor_doctrine.py`, new case) drives the real CLI / `_collect_profile_health` seam — not a hand-built `PackHealth`.

**Design note (R1, revised):** the fix is in `repository._load_layer` (catch `InlineReferenceRejectedError` → `_record_skip`), NOT a consumer-only catch — that is the only design under which "valid profiles remain visible" (C1) is achievable, because profile loading is eager/all-or-nothing (alphonso A1, debbie DD-1).

## C1 — Inline-ref-invalid profile ⇒ unhealthy + surfaced
- **Given** a project whose org doctrine pack contains a profile with a forbidden inline-reference field (e.g. `tactic_refs`)
- **When** `spec-kitty doctor doctrine --json` runs
- **Then** the JSON reports `healthy: false` for that pack
- **And** the invalid profile is surfaced with `{path, id, error_summary}` (the load-layer skip has the YAML, so `id` is populated — DD-2)
- **And** the other (valid) profiles — in the same pack, other packs, and the built-in layer — **remain visible** (the invalid one does not blank out the surface)

## C2 — No fail-to-green (proven by the same RED test as C1)
- The report MUST NEVER be `healthy: true` as a side effect of a profile load raising. An empty collected set (because loading raised) is `healthy: false`, not vacuously true (the `all([]) == True` mechanism at `_doctrine_health.py:112`).
- **Proving test:** the C1 `tactic_refs` scenario IS the C2 proof — assert the inline-ref scenario yields `healthy: false` with the surface non-empty (DD-5).

## C3 — Schema-invalid parity (regression guard)
- The existing schema-invalid-profile behavior (already `healthy: false` + surfaced as a skip) MUST remain unchanged; the inline-ref case now behaves identically (both are skips).

## C4 — General load contract (R1, revised)
- Under the load-layer skip, general callers (`resolve_profile`/`get_ancestors`) treat an inline-ref-invalid profile as **unavailable/skipped** (no longer raising). NFR-001 regression (incl. `tests/doctrine/test_inline_ref_rejection.py`, `tests/doctrine/agent_profiles/`) MUST confirm no caller regresses.

## C5 — Non-zero exit on unhealthy (operator preference: loud over hidden)
- `doctor doctrine` currently always `raise typer.Exit(0)` (alphonso A3). Per the operator's explicit preference — **a clear RC=1 with a surfaced error is preferred over RC=0 hiding a defect** — this contract REQUIRES the command to exit **1 when the report is unhealthy** and 0 only when healthy (`raise typer.Exit(0 if report.healthy else 1)`).
- The surfaced invalid profile MUST carry a clear, readable `error_summary` (forbidden field + migration hint), not a vague "skipped."
- The integration test (FR-002) asserts `exit_code == 1` for the inline-ref scenario.
