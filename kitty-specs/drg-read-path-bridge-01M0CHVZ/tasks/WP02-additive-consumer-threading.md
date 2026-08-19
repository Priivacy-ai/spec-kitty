---
work_package_id: WP02
title: Thread org fragments into additive graph consumers
dependencies:
- WP01
requirement_refs:
- FR-001
planning_base_branch: mission/drg-read-path-bridge-01M0CHVZ
merge_target_branch: mission/drg-read-path-bridge-01M0CHVZ
branch_strategy: Planning artifacts for this mission were generated on mission/drg-read-path-bridge-01M0CHVZ. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into mission/drg-read-path-bridge-01M0CHVZ unless the human explicitly redirects the landing branch.
subtasks:
- T008
- T009
- T010
history:
- at: '2026-08-19T14:10:00+00:00'
  actor: claude
  note: WP created by /spec-kitty.tasks
- at: '2026-08-19T15:30:00+00:00'
  actor: python-pedro
  note: 'T009 DEFERRED (research.md D4). The executor pre-probe
    load_graph_or_dir(root) raises DRGLoadError on a fragment-only pack
    (no root graph.yaml/*.graph.yaml), so such a pack is dropped from
    healthy_roots; threading org_fragments=load_org_drg(strict=False) into
    the L362 load would re-fold that same dropped pack via merge_three_layers,
    so the pre-probe degrade decision and the fragment bridge would contradict
    each other for a fragment-only pack. Executor threading is not on SC-001''s
    path and its own load already degrades graphless packs. T008 (gate_bindings)
    + T010 (regression) still deliver the additive extension. Tracked follow-up.'
agent_profile: python-pedro
authoritative_surface: src/specify_cli/review/
create_intent:
- tests/specify_cli/review/test_gate_bindings_fragment_edges.py
execution_mode: code_change
owned_files:
- src/specify_cli/review/gate_bindings.py
- src/specify_cli/mission_step_contracts/executor.py
- tests/specify_cli/review/test_gate_bindings_fragment_edges.py
role: implementer
tags: []
tracker_refs:
- '3572'
---

## ⚡ Do This First: Load Agent Profile

Load your profile: `/ad-hoc-profile-load python-pedro` (or `spec-kitty agent profile show python-pedro` + `spec-kitty charter context --action implement --json`). ATDD; `mypy --strict` + zero new suppressions; keep the diagnostic path untouched (NFR-001).

## Objective

Extend the WP01 fragment bridge to the remaining **runtime** graph consumers so
org `drg/fragment.yaml` edges are visible there too — the review-gate binding load
and (if tractable) the mission-step executor load. This is a coherence extension,
**not** on the SC-001..SC-004 path, so it is deferrable per research.md D4.

## Context

- **Depends on WP01**: `load_validated_graph` already accepts `org_fragments` and
  `load_org_drg(strict=…)` exists. This WP only threads the new argument at two
  more call sites; it introduces no new merge logic.
- `src/specify_cli/review/gate_bindings.py` L295 calls
  `load_validated_graph(repo_root, org_roots=resolve_existing_org_roots(repo_root))`.
- `src/specify_cli/mission_step_contracts/executor.py` L344/L362 call
  `load_validated_graph(repo_root, org_roots=…)` behind a `healthy_roots`
  pre-probe / degrade path (see its docstring).
- Do **not** touch the diagnostic `merge_three_layers` callers or `load_org_drg`'s
  strict default (NFR-001).

## Subtasks

### T008 — Thread `gate_bindings.py` (FR-001)

At `src/specify_cli/review/gate_bindings.py` L295, add
`org_fragments=load_org_drg(repo_root, strict=False)` to the
`load_validated_graph(...)` call. Import `load_org_drg` from `charter.drg`
consistent with the existing `from charter._drg_helpers import load_validated_graph`
neighbourhood. Keep the no-org-pack path (empty fragments) behaviourally
unchanged.

### T009 — Thread `executor.py` (FR-001) — defer if non-trivial

At `src/specify_cli/mission_step_contracts/executor.py` L344/L362, thread
`org_fragments=load_org_drg(repo_root, strict=False)` into the
`load_validated_graph(...)` calls, aligned with the existing `healthy_roots`
degrade logic. **If** the pre-probe/degrade interaction makes this non-trivial or
risks the executor's graphless-degrade behaviour, **drop T009** and record a
one-line rationale in this WP's history (research.md D4 authorises this) — T008 +
T010 still deliver the extension.

### T010 — Focused regression (FR-001, NFR-001)

Add `tests/specify_cli/review/test_gate_bindings_fragment_edges.py` (new): with a
fragment-bearing pack configured, assert the graph the gate-binding path loads
contains the org fragment edge (or that the gate resolves the org-authored
dependency). Assert the no-org-pack path is unchanged. Confirm diagnostic surfaces
(`doctor doctrine` / `charter list`) are unaffected.

**Validation**: `PWHEADLESS=1 python -m pytest tests/specify_cli/review/ -q`
green; `ruff` + `mypy --strict` clean; zero new suppressions.

## Branch Strategy

Same as WP01: planning/base = merge target = `mission/drg-read-path-bridge-01M0CHVZ`
(single_branch). Depends on WP01; branches from WP01's landed base. Merges back
into the mission branch, which later becomes a PR to `main`.

## Definition of Done

- `gate_bindings` graph load contains org fragment edges for a fragment-bearing
  pack (T008); executor threaded (T009) or explicitly deferred with rationale.
- No diagnostic-path change (NFR-001); ruff + mypy --strict clean, zero new
  suppressions.
- Focused regression green (T010).

## Reviewer guidance

- Confirm this WP adds **only** the `org_fragments=` argument at the two call sites
  — no new merge/dedup logic (that lives in WP01 / `merge_three_layers`).
- If T009 was deferred, confirm the rationale is recorded and the executor's
  existing degrade behaviour is untouched.
- Confirm no diagnostic caller changed.
