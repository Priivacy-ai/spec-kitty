---
work_package_id: WP04
title: Retrospective seam
dependencies: [WP03]
requirement_refs:
- FR-001
- FR-006
tracker_refs:
- '2531'
planning_base_branch: design/runtime-bridge-degod
merge_target_branch: design/runtime-bridge-degod
branch_strategy: Planning artifacts for this mission were generated on design/runtime-bridge-degod. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into design/runtime-bridge-degod unless the human explicitly redirects the landing branch.
subtasks:
- T015
- T016
phase: Extraction spine
shell_pid: '1985551'
history:
- at: '2026-07-11T00:00:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/runtime/next/
create_intent:
- src/runtime/next/runtime_bridge_retrospective.py
- tests/runtime/test_bridge_retrospective.py
execution_mode: code_change
owned_files:
- src/runtime/next/runtime_bridge_retrospective.py
- src/runtime/next/runtime_bridge.py
- tests/runtime/test_bridge_retrospective.py
role: implementer
tags: []
task_type: implement
---

# WP04 — Retrospective seam

## Context

A **low-coupling, confidence-front-loading** extraction (IC-03). It lifts the
self-contained learning-capture cluster out of `runtime_bridge.py` into a new
`runtime_bridge_retrospective.py` seam. Chosen early precisely because it is
self-contained — it exercises the extraction machinery (move → re-export →
oracle+compat green) on a low-risk cluster before the harder seams (cores,
decision-builder, decide_next phase-split, identity).

**Depends on WP01 + WP02** (both green on unmodified source). The acceptance gate
is unchanged: **oracle stays green, compat guard stays green** after the move.
The WP01 oracle **captures and asserts the retrospective `Confirm.ask` gate**
(`contracts/parity-oracle.md §Side-effect isolation`) — so a change to *whether*
or *what* the retrospective emits is a parity break. Preserve the exact
retrospective side-effect semantics.

Read `plan.md` IC-03 and `research.md §Seams` (retrospective row). Do not invent
new behavior — this is a behavior-preserving relocation (C-001).

## Ordered steps

### T015 — Create `runtime_bridge_retrospective.py`; move the learning-capture cluster
Identify the self-contained retrospective/learning-capture cluster in
`runtime_bridge.py` (the `Confirm.ask`-gated retrospective flow and its helpers).
Grep for the cluster's symbols and their call sites to confirm the boundary is
clean (no bidirectional coupling back into the orchestrator that would create an
import cycle — C-007). Move the cluster into `runtime_bridge_retrospective.py`
with identical call semantics. Preserve the `Confirm.ask` gate exactly — the WP01
oracle captures and asserts it.

### T016 — Seam unit tests; re-export patched symbols; oracle + compat green
Add focused unit tests for the retrospective seam (FR-006 — the cluster tested in
isolation against stubs where it touches I/O). Re-import every moved patched
symbol into `runtime_bridge`'s guarded compat re-export block (with a
`_wf`-style LAZY-ACCESSOR for any name a sibling module calls, per WP02's
inventory — the retrospective-pair risk is noted in `research.md §Compat`). Then
run **both safety nets**: the WP01 parity oracle (all 3 entries, full floor,
incl. the **captured retrospective side-effect**) and the WP02 compat guard
(per-entry sentinels + AST identity). Both MUST be green.

## Acceptance
- Retrospective learning-capture cluster extracted into
  `runtime_bridge_retrospective.py`; boundary clean (no new import cycle — C-007).
- Moved patched symbols re-exported (+ lazy-accessor where sibling-called);
  identity re-export holds (`rb.x is retrospective.x`).
- **WP01 oracle green** — including the **captured retrospective `Confirm.ask`
  side-effect** asserting binding equality before/after.
- **WP02 compat guard green** — all relevant sentinels fire through their reaching
  entry.
- Retrospective seam has focused unit tests (FR-006).
- `ruff --select C901` zero new offenders; `mypy` clean; no suppressions.

## Safeguards
- The oracle **captures** the retrospective side-effect — a change to what the
  retrospective emits/commits returns an identical `Decision` but is still a
  parity break. Do not alter the `Confirm.ask` gate semantics.
- Watch the retrospective-pair compat risk (`research.md §Compat`) — names a
  sibling module calls need re-export **and** the lazy accessor, or the compat
  guard goes false-green.
- Behavior-preserving only (C-001): relocate, never re-decide.

## References
- `plan.md:105-107` IC-03 (retrospective seam purpose)
- `research.md:18` §Seams (retrospective row); `research.md:71` §Compat (retrospective-pair risk)
- `contracts/parity-oracle.md:28-33` §Side-effect isolation (retrospective `Confirm.ask` captured)
- `contracts/compat-surface.md` (re-export + lazy-accessor discipline)
- `src/runtime/next/runtime_bridge.py` (retrospective cluster — grep to bound)
- `contracts/parity-oracle.md`, `tests/runtime/test_bridge_compat_surface.py` (re-run as acceptance gate)

## Activity Log

- 2026-07-11T19:21:50Z – user – shell_pid=1985551 – Moved to for_review
- 2026-07-11T19:26:36Z – user – shell_pid=1985551 – Moved to approved
