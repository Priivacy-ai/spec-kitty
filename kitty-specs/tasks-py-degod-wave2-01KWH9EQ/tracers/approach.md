# Tracer: Approach

**Mission**: tasks-py-degod-wave2-01KWH9EQ
**Created**: 2026-07-02 (seeded at planning per `mission-tracer-files` procedure)
**Lifecycle**: seed at planning → append during implement → assess at close

## Planned approach (seed)

- **Low-risk-per-move discipline**: pure cut-paste relocations, golden byte-identical at
  every step; any golden delta = revert the move, never fix forward.
- **One command family per WP** (mission.py degod template): relocate move_task family,
  then mapping+status families, then coreless commands, then render seam, then
  shim-finalize + LOC gate.
- **@patch seams decided per WP**: keep module-level re-exports by default; re-point
  patches only deliberately, with the full targeted suite as the guard.
- **Gates last but proven**: LOC gate and AST json.dumps gate land with non-vacuity
  self-tests (synthetic violation red) per DIRECTIVE_043.
- **Boyscout lane**: marker census + gate-visibility fixes for the tasks domain; #2034
  upstream refresh with the 2026-07-02 re-census.

## Deviations / discoveries (append during implement)

- **WP09 (2026-07-02)**: the "empty allowlist at ship time" prediction in
  gate-contracts.md Gate 1 did not survive contact with the whole-directory
  glob — 9 pre-existing non-tasks siblings carry inline dumps (out-of-scope,
  #2289–#2293 surface). Shipped the gate with the contract's shrink-only
  exception mechanism instead of narrowing the glob or rewriting out-of-scope
  files; `tasks*.py` at 0 sites is asserted directly (SC-002 for the mission's
  remit). Relocation cost of the final sweep: ~300 body lines moved, +~45
  re-export/rationale lines; 4 seam-census move-sets re-pinned; 3 relocated
  bodies needed strict-typing tightening (their old homes were on the mypy
  transitional quarantine list — the family modules are not).
- **WP09**: per-WP targeted suites let 4 mission-introduced arch-gate REDs
  accumulate silently (dead-symbol burn-down obligations + coord-authority
  write-census drift from WP04's render-seam change). The closure WP's full
  `tests/architectural/` sweep caught them; adjudicated at root (drain/re-pin,
  shrink-only) with cross-base green proof on degod-follow-ups.
