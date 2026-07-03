# Tracer: Design Decisions

**Mission**: tasks-py-degod-wave2-01KWH9EQ
**Created**: 2026-07-02 (seeded at planning per `mission-tracer-files` procedure)
**Lifecycle**: seed at planning → append during implement → assess at close

## Seed decisions (from spec)

1. **Dedicated `tasks_command_adapters.py`** for the port-seam adapter classes rather than
   folding into `agent_tasks_ports.py` — breaks the ports ↔ command-modules import-cycle
   risk (debrief risk note). Deviation requires a recorded no-cycle argument.
2. **Honest LOC ceiling over target-hitting**: ≤1400 is a Wave 1 planning estimate; the
   gate records the real achievable number with rationale if higher (spec FR-004/NFR-004).
3. **Render seam indent parameterization** (or an indented-envelope capability) collapses
   `_StatusRender` instead of keeping a subclass override — one production adapter per
   port (#2173 / C-004).
4. **#2300 divergence frozen**: skip-vs-refuse behavior preserved verbatim (C-001);
   characterized by the golden harness, reconciled only in #2300's own mission.
5. **Boyscout bounded to the tasks domain** (charter standing order 2: domain-matched
   folds only); repo-wide #2034 fix stays upstream.

## Post-spec squad decisions (2026-07-02)

6. **Seam bridge = lazy parent-module attribute routing** (`_tasks.<attr>`), the proven
   `mission.py` template mechanism — NOT bare module-level re-exports, which do not
   preserve patch interception (squad CRITICAL, alphonso+renata convergent).
7. **Byte-freeze suite before routing**: the shape-checked harness JSON legs cannot carry
   the byte-identity claim; 13 byte-exact characterization cases are committed BEFORE the
   render-seam change (squad CRITICAL, renata).
8. **LOC ceiling = min(achieved, 1400)**, >1400 escalates to the operator — closes the
   self-certification hole (renata).
9. **Ratchet re-point ≠ fixture adjustment**: the coord-harness branch-coverage ratchet is
   re-pointed per relocation WP; deletion/floor-lowering forbidden (FR-012).
10. **Shared-helpers module added** (FR-003) — the ~30 cross-family helpers were the
    decomposition blind spot (priti).

## New decisions (append during implement)

_(none yet)_
