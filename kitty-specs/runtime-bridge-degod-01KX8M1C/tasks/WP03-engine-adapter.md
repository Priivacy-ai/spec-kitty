---
work_package_id: WP03
title: Engine-adapter (FR-013)
dependencies: [WP01, WP02]
requirement_refs:
- FR-013
- FR-007
- FR-001
- FR-006
tracker_refs:
- '2531'
planning_base_branch: design/runtime-bridge-degod
merge_target_branch: design/runtime-bridge-degod
branch_strategy: Planning artifacts for this mission were generated on design/runtime-bridge-degod. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into design/runtime-bridge-degod unless the human explicitly redirects the landing branch.
subtasks:
- T011
- T012
- T013
- T014
phase: Extraction spine
shell_pid: '1742369'
history:
- at: '2026-07-11T00:00:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/runtime/next/
create_intent:
- src/runtime/next/runtime_bridge_engine.py
- tests/runtime/test_bridge_engine.py
execution_mode: code_change
owned_files:
- src/runtime/next/runtime_bridge_engine.py
- src/runtime/next/runtime_bridge.py
- tests/runtime/test_bridge_engine.py
role: implementer
tags: []
task_type: implement
---

# WP03 — Engine-adapter (FR-013)

## Context

First extraction WP. It concentrates **all** `_internal_runtime` private access
into a single `runtime_bridge_engine.py` adapter seam (FR-013), so that the
engine boundary is owned in exactly one place and no "core" reaches engine
internals. It also relocates the CC23 `_advance_run_state_after_composition`
body into the adapter (reduced ≤15, FR-004) while keeping a **thin residual
compat delegate** in `runtime_bridge.py` for its heavy monkeypatch surface.

**Depends on WP01 (parity oracle) + WP02 (compat guard)** — both are already
green on unmodified source. This WP's acceptance gate is: **the oracle stays
green and the compat guard stays green** after the move. That is the definition
of behavior-preserving here (C-001) — do not weaken either.

Read `data-model.md §Engine-adapter surface` and `research.md §Seams`/`§Compat`.
The engine adapter wraps `_read_snapshot`, `_load_frozen_template`,
`_append_event`, `_write_snapshot` (from `_internal_runtime.engine`) and
`plan_next` (from `_internal_runtime.planner`).

**The site list is grep-complete, not a sample.** Before moving anything, run the
grep in T011 and reconcile every hit — FR-013 fails if any engine-private access
survives outside the adapter. The most commonly missed hits are the two
`_load_frozen_template` accesses at `:1322` (`_resolve_step_binding`) and `:1375`
(`_resolve_step_agent_profile`), which are **not** among the decide_next sites.

## Ordered steps

### T011 — Create `runtime_bridge_engine.py`; move grep-complete engine privates
Grep the module for **every** `_internal_runtime` private access — do not rely on
a remembered list:
```
grep -nE "_read_snapshot|_load_frozen_template|_append_event|_write_snapshot|plan_next|_internal_runtime\.(engine|planner)" src/runtime/next/runtime_bridge.py
```
Reconcile every hit. The known site list (must all be present): `_read_snapshot`,
`_load_frozen_template` at **`:1322`** and **`:1375`**, plus the decide_next/answer
sites `:1800` / `:1840` / `:2606` / `:3261` / `:3416`; `_append_event`,
`_write_snapshot`, `plan_next`. Move these privates into
`runtime_bridge_engine.py` as the sole home of engine-internal access. Preserve
the capture points the WP01 oracle asserts (`_append_event` / `_write_snapshot` /
`_read_snapshot` snapshot seed `:3418`) — same call semantics, new home.

### T012 — `_advance_run_state_after_composition` body → adapter (≤15) + thin residual delegate
Move the CC23 body of `_advance_run_state_after_composition` (`:1800`) into the
engine adapter and reduce it to **≤15** (extract small helpers / flatten
branches — do not re-add `# noqa: C901`). It duplicates the engine's own
`next_step` success branch, so it is adapter-owned logic, **not** a core. Keep a
**thin residual delegate** at `runtime_bridge._advance_run_state_after_composition`
that forwards to the adapter — this preserves its heavy compat surface (**8×
patch + 9× attr**) so `monkeypatch.setattr(runtime_bridge,
"_advance_run_state_after_composition", …)` still intercepts. Logic in the
adapter, compat shim in the residual.

### T013 — Arch guard (no core reaches engine internals) + FR-007 #2531 pointer
Add an **architecture guard test** (in `test_bridge_engine.py`) asserting no
module other than `runtime_bridge_engine.py` imports/accesses
`_internal_runtime.engine` / `.planner` privates — FR-013 requires ALL
engine-private access concentrated in the adapter. Add the **FR-007 top-of-file
decomposition pointer** referencing **#2531** to `runtime_bridge.py`, matching the
sibling convention (#2056/#2057/#2059/#2464). Also introduce **`__all__` for the 8
public names** on `runtime_bridge.py` (sibling `merge.py` parity, research.md
§Engine-adapter). Nuance to preserve: `__all__` governs **only** `import *` — it does
**NOT** preserve the ~50 private symbols, which remain owned by the explicit guarded
compat re-export block (do not conflate the two — see `contracts/compat-surface.md`
§`__all__`).

### T014 — Guarded re-export; oracle + compat guard stay green
Re-import every moved patched symbol back into `runtime_bridge` in the **guarded
compat re-export block**, with a `_wf`-style LAZY-ACCESSOR for any name a sibling
module calls through the shim (per WP02's inventory). Then run **both safety
nets**: the WP01 parity oracle (all 3 entries, full floor) and the WP02 compat
guard (per-entry sentinels + AST identity). Both MUST be green. Add the seam's own
focused unit tests for the adapter (contract-tested against engine stubs, FR-006).

## Acceptance
- All `_internal_runtime` engine-privates concentrated in
  `runtime_bridge_engine.py` — **grep-complete** (incl. `:1322` / `:1375`); arch
  guard test proves no other module reaches engine internals.
- `_advance_run_state_after_composition` logic in the adapter at **CC ≤15**; thin
  residual delegate preserves the 8-patch/9-attr compat surface.
- FR-007 #2531 decomposition pointer present at top of `runtime_bridge.py`.
- `__all__` introduced for the 8 public names on `runtime_bridge.py` (governs `import *`
  only — the ~50 private symbols remain in the guarded compat re-export block).
- **WP01 oracle green** (all 3 entries, full floor) and **WP02 compat guard green**
  (all sentinels fire) — the acceptance gate.
- Adapter seam has focused unit tests against engine stubs (FR-006).
- `ruff --select C901` reports zero new offenders; `mypy` clean; no suppressions.

## Safeguards
- **Grep-complete site list** — an engine-private access left behind outside the
  adapter fails FR-013. `:1322` / `:1375` are the classic misses.
- The residual keeps **only** the compat delegate; logic is adapter-owned. Do not
  leave decision logic in `runtime_bridge.py` for this symbol.
- Do not let the intra-seam moves create a false-green: the compat guard (WP02
  guard A) must still fire each moved symbol's sentinel through its reaching
  entry, and guard B must confirm `rb.x is engine.x` (no function-scope
  re-import).
- A parity break (Decision inequality OR a captured side-effect delta on
  `_append_event`/`_write_snapshot`) = the extraction changed behavior = reject.

## References
- `data-model.md:24-25` §Engine-adapter surface (grep-complete site list authority)
- `research.md:14` §Seams (engine module + `_advance_run_state_after_composition` reconciliation)
- `contracts/compat-surface.md:8-12` (KEEP-IN-PLACE / thin-residual-delegate for `_advance_run_state_after_composition`)
- `plan.md:100-103` IC-02 (engine-adapter purpose + arch-guard)
- `src/runtime/next/runtime_bridge.py:1800` `_advance_run_state_after_composition` (CC23)
- `src/runtime/next/runtime_bridge.py:1322`, `:1375` `_load_frozen_template` (the classic missed engine sites)
- `contracts/parity-oracle.md` (re-run as acceptance gate)
- `tests/runtime/test_bridge_compat_surface.py` (re-run as acceptance gate)

## Activity Log

- 2026-07-11T18:21:03Z – user – shell_pid=1742369 – Moved to for_review
- 2026-07-11T18:30:07Z – user – shell_pid=1742369 – Moved to approved
