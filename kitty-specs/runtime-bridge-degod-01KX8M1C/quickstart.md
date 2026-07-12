# Quickstart: working with the decomposed runtime bridge

After this mission, `src/runtime/next/runtime_bridge.py` is a thin orchestration
surface; the logic lives in focused seam modules. Where to look:

| I want to change… | Go to |
|-------------------|-------|
| how a composed action dispatches / the FR-008 selection | `runtime_bridge_composition.py` |
| the CLI/composition guard rules | `runtime_bridge_cores.py` → `evaluate_guards(snapshot)` (pure; facts from `runtime_bridge_io.gather_artifact_presence`) |
| how a `Decision` is built (step vs blocked) | `runtime_bridge_cores.py` → `step_or_blocked` (the one Decision-builder) |
| tasks.md parsing | `runtime_bridge_cores.py` (pure, zero-dep leaf) |
| engine reads/writes (`_internal_runtime`) | `runtime_bridge_engine.py` (the only place; do NOT reach engine privates elsewhere) |
| meta.json / coord-branch / mission-ULID resolution | `runtime_bridge_identity.py` |
| feature-runs.json / template discovery / run lifecycle | `runtime_bridge_io.py` |
| the top-level decide_next flow | `runtime_bridge.py` — the 4-phase chain (`bootstrap → dependency-gate → composition-dispatch → decision-materialize`) over `DecideNextContext` |

## The two rules every change obeys
1. **Parity oracle stays green.** `pytest tests/runtime/test_bridge_parity.py` — a break means you changed `decide_next()` behavior. This is a behavior-preserving codebase surface.
2. **Compat surface stays green.** `pytest tests/runtime/test_bridge_compat_surface.py` — if you move a private symbol that tests patch via `runtime_bridge.<name>`, keep it reachable (guarded re-export / lazy-accessor) or the guard fails (and catches the silent false-green).

## Writing a new pure core
Take plain data in, return plain data out, import only stdlib / `Lane` / decision types — no filesystem, no `meta.json`, no git. Add a direct unit test that runs it with in-memory inputs (no I/O). That's what keeps `runtime_bridge.py` thin and every function ≤ 15.
