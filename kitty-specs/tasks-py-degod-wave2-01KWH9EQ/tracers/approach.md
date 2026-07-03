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

_(none yet)_
