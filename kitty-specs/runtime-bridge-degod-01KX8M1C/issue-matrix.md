# Issue matrix — runtime-bridge-degod-01KX8M1C

Per FR-037 of the spec-kitty-mission-review skill Gate-4. One row per issue referenced in spec.md.

| Issue | Title | Verdict | Evidence ref |
|-------|-------|---------|--------------|
| #2531 | Decompose `runtime_bridge.py` god-module into ports+cores (behavior-preserving) | fixed | design/runtime-bridge-degod — ALL 10 WPs approved. runtime_bridge.py 3813→2674 LOC decomposed into ports+cores (engine/io/cores/composition/retrospective/identity seams); zero # noqa: C901 across the family (NFR-002); WP01 parity oracle + WP02 compat guard green on the aggregate. NFR-005 residual (70.1%) short of the ~35-40% guidance — flagged for retro (orchestration core extraction is a follow-up). |
| #1619 | Epic: runtime/state overhaul | deferred-with-followup | Follow-up: #1619 (parent epic remains open). This mission is a scoped slice (`runtime_bridge.py` only); the broader overhaul is explicitly out of scope (spec Non-Goals). |
| #2173 | Epic: infra-logic separation (inject infra as ports, keep core pure) | deferred-with-followup | Follow-up: #2173 (parent epic remains open). This mission applies the ports+cores treatment (C-002) to one module; the epic tracks the other god-modules. |
| #2056 | Sibling god-module: `agent/mission.py` | deferred-with-followup | Follow-up: #2056 (own mission). Sibling (different file, same shape); not a deliverable here, referenced only as a convention template (C-003). |
| #2057 | Sibling god-module: `merge.py` | deferred-with-followup | Follow-up: #2057 (already landed under its own mission). Reused here as the flat-module + `__all__` convention template (C-003). |
| #2059 | Sibling god-module: `doctor.py` | deferred-with-followup | Follow-up: #2059 (own mission). Sibling (different file); not a deliverable here. |
| #2464 | Sibling god-module: `agent/workflow.py` | deferred-with-followup | Follow-up: #2464 (already landed). Reused here as the layout + `DecideNextContext` + lazy-accessor template (spec Assumptions). |
| #2535 | Doctrine-controlled gates mission (WP14 inverts the composition-dispatch selection) | deferred-with-followup | Follow-up: #2535 (gates WP14, after this mission). Downstream consumer this mission ENABLES via FR-008 (clean selection seam) WITHOUT coupling to its unlanded `resolve_gates` (C-005). |
| #2545 | Sibling: coord-authority trio degod | deferred-with-followup | Follow-up: #2545 (separate branch). Does not touch `runtime_bridge.py` (rewrites `cli/commands/agent/workflow.py`, lists #2531 out of scope); light rebase only, coordinate not block (C-006). |

Valid `Verdict` values: `fixed`, `verified-already-fixed`, `deferred-with-followup`, `in-mission` (being fixed by a later WP in this mission; must reach a terminal verdict before mission `done`).
