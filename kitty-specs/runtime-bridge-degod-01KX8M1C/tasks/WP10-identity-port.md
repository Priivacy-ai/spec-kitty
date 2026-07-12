---
work_package_id: WP10
title: Identity/coord port (LAST)
dependencies: [WP09]
requirement_refs:
- FR-001
- FR-003
- FR-004
- FR-005
- NFR-005
- NFR-006
tracker_refs:
- '2531'
planning_base_branch: design/runtime-bridge-degod
merge_target_branch: design/runtime-bridge-degod
branch_strategy: Planning artifacts for this mission were generated on design/runtime-bridge-degod. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into design/runtime-bridge-degod unless the human explicitly redirects the landing branch.
subtasks:
- T034
- T035
- T036
phase: Extraction spine
history:
- at: '2026-07-11T00:00:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/runtime/next/
create_intent:
- src/runtime/next/runtime_bridge_identity.py
- tests/runtime/test_bridge_identity.py
execution_mode: code_change
owned_files:
- src/runtime/next/runtime_bridge_identity.py
- src/runtime/next/runtime_bridge.py
- tests/runtime/test_bridge_identity.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP10 – Identity/coord port (LAST)

## Context

This is the **final** extraction and the **hottest fracture line** in the module — coord-branch
naming, mission-ULID resolution, and primary-feature-dir resolution. It carries the mission's
fattest scar debt (#2091 / #1978 / #1918 / #1814 / #2069) and is correctness-critical: a
malformed coord branch → `git worktree` exits 128. It is cut LAST, behind the fattest golden
coverage, precisely because a silent drift here is the most dangerous (plan.md IC-09).
Behavior-preserving (C-001).

It depends on **all seven prior extraction WPs** (WP03–WP09) — it lands on top of the fully
decomposed module so its relocation is the last edit to `runtime_bridge.py`. As the last WP it
also owns the two **whole-mission closure assertions**: zero `# noqa: C901` remain repo-wide in
the module family (NFR-002/SC-002) and NFR-005 residual-LOC + NFR-006 timing parity.

### What moves — and what stays (research.md §Compat is load-bearing here)

**MOVE** to `runtime_bridge_identity.py`: coord-branch naming, mission-ULID resolution
(`_resolve_mission_ulid:134`), primary-feature-dir resolution (`_primary_runtime_feature_dir:78`).

**KEEP-IN-PLACE** in the residual (mandatory — do not move):
- **`_wrap_with_decision_git_log:187`** — KEEP-IN-PLACE (research.md §Compat). It also
  neutralizes the identity-trio + retrospective-pair false-green risks. (WP05 already lifted its
  *pure* `resolve_commit_target` selection out of `:226–261`; the wrapper shell stays.)

**LAZY-ACCESSOR** (`_wf`-style, per #2464/merge.py) for names a **sibling module calls**
through the shim — re-export alone is false-green for these:
- 🔴 **`_primary_runtime_feature_dir`** — patched 6× (`test_runtime_bridge_identity.py:71–222`)
  while an **unpatched `_resolve_mission_ulid` calls it internally**. A plain re-export makes
  the 6 patches no-ops (intra-seam call resolves via the seam's own global). It needs
  re-export **AND** the lazy accessor so the sibling call routes through the shim.
- Apply the same lazy-accessor treatment to any other identity symbol a sibling seam calls.

## Ordered Steps

### T034 — Create `runtime_bridge_identity.py`; move the identity/coord cluster

1. Create `src/runtime/next/runtime_bridge_identity.py` with a responsibility docstring +
   `#2531` decomposition pointer (FR-007).
2. Move coord-branch naming, `_resolve_mission_ulid:134`, and `_primary_runtime_feature_dir:78`
   and their private helpers. Preserve the malformed-coord correctness path exactly (a bad coord
   branch must still surface, not silently swallow — `git worktree` exit-128 scar).
3. Import DAG (research.md §Import DAG): `identity` may import `io`; it must NOT be imported by
   `cores`. No `decision → runtime_bridge_*` top-level edge (C-007).
4. Reduce any touched function >15 to ≤15 (FR-004); do not relocate a `# noqa`.

### T035 — KEEP-IN-PLACE `_wrap_with_decision_git_log`; lazy-accessor for sibling-called symbols

1. Leave `_wrap_with_decision_git_log:187` in the residual (KEEP-IN-PLACE — compat mandate).
2. For every relocated identity symbol a sibling module calls, add BOTH the guarded re-export
   AND the `_wf`-style lazy accessor so `runtime_bridge.<name>` remains the patch target and the
   sibling call routes through the shim (FR-012). **`_primary_runtime_feature_dir` is the named
   high-risk case** — verify the 6× patches in `test_runtime_bridge_identity.py:71–222` still
   take effect (the sentinel must fire).
3. Confirm re-export identity (`runtime_bridge.x is runtime_bridge_identity.x`) for every
   relocated symbol.

### T036 — Whole-mission closure assertions; final oracle + compat green

1. Create `tests/runtime/test_bridge_identity.py`:
   - Unit-test coord-branch naming / mission-ULID / primary-feature-dir against stubs (FR-006),
     including the malformed-coord path.
   - **Zero `# noqa: C901` repo-wide in the module family** — the authoritative check is a
     **`ruff --select C901` offender-count == 0** over `runtime_bridge.py` and every
     `runtime_bridge_*.py` sibling (NFR-002/SC-002). Do **NOT** use a raw text grep for the
     literal `# noqa: C901`: `runtime_bridge.py:2465` contains a docstring that *mentions* the
     marker as prose (```# noqa: C901```), which a grep false-positives on. Assert the ruff
     offender count is zero (no function is over the complexity ceiling and therefore no
     suppression is needed) — this is the mission-closing complexity assertion.
   - **C-007 no-new-import-cycle** (whole-family closure) — add a concrete regression assertion
     that the decomposed `runtime_bridge*` family introduced **no new top-level import cycle**.
     Specifically: assert the `decision.py:428` → orchestrator edge stays **lazy** (no top-level
     `decision → runtime_bridge*` import), and that no seam module (`_engine`/`_io`/`_cores`/
     `_composition`/`_retrospective`/`_identity`) creates a top-level cycle back into
     `runtime_bridge` or into `cores` (the import DAG in research.md §Import DAG must stay
     acyclic). Drive this with an AST/import-graph walk over the family (e.g. build the top-level
     import edges and assert no cycle), not a runtime `import` smoke test alone.
     target (~35–40% of the original 3,813 LOC, per the #2464 precedent — guidance, not a frozen
     constant; FR-005).
   - **NFR-006 timing parity** — re-run the WP01 before/after timing harness on the full
     characterization matrix; assert no measurable `decide_next()` latency regression (within
     noise) or explicitly record the waiver in the PR body.
2. Re-run the final acceptance gate (below).

## Acceptance

- `runtime_bridge_identity.py` exists; coord-branch naming / mission-ULID / primary-feature-dir
  relocated; malformed-coord correctness path preserved.
- `_wrap_with_decision_git_log` KEPT-IN-PLACE; `_primary_runtime_feature_dir` (and any other
  sibling-called identity symbol) has re-export **AND** lazy accessor — the 6× patches fire (no
  false-green).
- **Zero `# noqa: C901` remain** anywhere in the `runtime_bridge*` module family (NFR-002/SC-002).
- NFR-005 residual-LOC target asserted; NFR-006 timing parity asserted (or waiver recorded).
- **Final acceptance gate:** WP01 parity oracle green on all 3 entries at the full coverage
  floor; WP02 compat guard green (every relocated symbol's sentinel fires through its reaching
  entry — the identity trio driven through its reaching entries).

## Safeguards

- **Hottest fracture — highest regression risk.** The identity-trio compat symbols are
  KEEP-IN-PLACE / LAZY-ACCESSOR per research §Compat; a plain re-export of
  `_primary_runtime_feature_dir` silently no-ops 6 patches. Do not shortcut the lazy accessor.
- Malformed coord branch must still fail loudly (`git worktree` exit-128 scar) — do not add a
  fallback that swallows it (C-001; no legacy fallback).
- This WP owns the two whole-mission closure checks (zero `# noqa`, NFR-005/NFR-006) — they are
  acceptance-blocking, not advisory.
- `runtime_bridge.py` exists — edited, never created (not in `create_intent`).
- Never stub `next_step` in the oracle; capture-and-assert the coord-branch commit side effect.

## References

- `src/runtime/next/runtime_bridge.py:78` — `_primary_runtime_feature_dir` (patched 6×; re-export + lazy accessor).
- `src/runtime/next/runtime_bridge.py:134` — `_resolve_mission_ulid` (unpatched intra-seam caller of the above).
- `src/runtime/next/runtime_bridge.py:187` — `_wrap_with_decision_git_log` (KEEP-IN-PLACE).
- `tests/runtime/test_runtime_bridge_identity.py:71-222` — the 6× `_primary_runtime_feature_dir` patches.
- `kitty-specs/runtime-bridge-degod-01KX8M1C/research.md` §Compat / §Import DAG — KEEP-IN-PLACE / lazy-accessor mandate.
- `kitty-specs/runtime-bridge-degod-01KX8M1C/plan.md` IC-09 — identity port cut LAST, NFR-006 asserted here.
- `kitty-specs/runtime-bridge-degod-01KX8M1C/spec.md` — FR-001, FR-003, FR-004, FR-005, NFR-002, NFR-005, NFR-006, SC-002.
