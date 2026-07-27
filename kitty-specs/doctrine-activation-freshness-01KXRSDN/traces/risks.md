# Risk Register — Doctrine-activation freshness integrity

Tracer (seeded at planning; watch during implement; assess at close).

| ID | Risk | Likelihood | Impact | Mitigation | Status |
|----|------|-----------|--------|------------|--------|
| R-01 | Wiring parity into the read-path forces a never-synthesized (fresh-seed) project spuriously stale | Med | High | Preserve `computer.py:367-408` fresh-seed early-exit; red-first test that a fresh project stays fresh | OPEN |
| R-02 | The parity read regresses #2732 content-identity (changes the hash of an unchanged bundle) | Low | High | NFR-002 preserve-regression test; parity is a SEPARATE signal composed with the hash, not a hash input | OPEN |
| R-03 | #2770 baseline re-freeze guesses N instead of computing it → zero-delta test flaps | Med | Med | Compute the regen delta from a fresh `generate_graph`, then re-freeze `test_extractor_projection.py:52-54` to match; never hand-pick | OPEN |
| R-04 | `--resynthesize` / seam accidentally makes the DEFAULT activate path eager (spawns synthesis) | Med | High | NFR-001 subprocess/call-count spy on default `charter activate`; the eager path is flag-gated only | OPEN |
| R-05 | #2773 lands mid-mission and deprecates references.yaml, colliding with the fail-closed preflight (DD-03) | Low | Med | Fail-closed leaves #2773 clean by design; if #2773 lands, the preflight becomes a no-op — coordinate, don't stopgap | OPEN |
| R-06 | Editing `consistency_check.py` (charter) from the IC-03 (specify_cli) concern crosses ownership | Low | Med | The pre-extract is a charter-local refactor; keep it in the same WP that consumes it, record the cross-layer edit rationale | OPEN |
| R-07 | #2157a aggregation changes a per-prerequisite verdict (behavior drift) | Low | Med | Aggregation is additive (report all vs raise-first); pin per-verdict values unchanged | OPEN |
| R-08 | merge_defaults/init path (ADR 2026-07-15-1 S1) ships and re-opens the hole if the reconciler weren't writer-agnostic | Low | High | DD-01 read-path parity is writer-agnostic by construction; add a merge_defaults-seeded visibility test | OPEN |
