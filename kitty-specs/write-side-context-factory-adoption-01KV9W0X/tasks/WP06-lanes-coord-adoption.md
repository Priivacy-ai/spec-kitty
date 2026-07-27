---
work_package_id: WP06
title: Lanes/coord adoption FR-008 #1993 deeper grain
dependencies:
- WP01
requirement_refs:
- FR-008
tracker_refs: []
planning_base_branch: feat/write-side-context-factory-adoption
merge_target_branch: feat/write-side-context-factory-adoption
branch_strategy: Planning artifacts for this mission were generated on feat/write-side-context-factory-adoption. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/write-side-context-factory-adoption unless the human explicitly redirects the landing branch.
subtasks:
- T027
- T028
- T029
- T030
agent: "claude:sonnet:reviewer-renata:reviewer"
shell_pid: "2955713"
history:
- 2026-06-17 created (/spec-kitty.tasks)
agent_profile: python-pedro
authoritative_surface: src/specify_cli/lanes/
create_intent: []
execution_mode: code_change
owned_files:
- src/specify_cli/lanes/persistence.py
- src/specify_cli/cli/commands/implement.py
- tests/lanes/test_persistence.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load python-pedro
```

Then read: `spec.md` **FR-008** + **C-001** + **C-007** (lanes → coordination) + **C-008**; `plan.md`
**IC-LANES** + **D-6** (prefer deriving from the existing `status_surface` + the `resolve_lanes_dir` seam
over a raw factory field); `contracts/behavioral-contracts.md` **C-LANES** (C-LANES-1/#1991 — lanes.json on
the coordination authority, never `primary_root` under coord topology).

## Objective

Route the lanes-dir write so `lanes.json` resolves from the **coord** surface (the coordination authority,
C-LANES-1/#1991). Today `cli/commands/implement.py:984` sets `_lanes_feature_dir = feature_dir` (the bare
primary feature_dir) and `:1140` calls `require_lanes_json(_lanes_feature_dir)`. Adopt:
`_lanes_feature_dir` MUST derive from the context's coord surface —
`resolve_lanes_dir(<coord feature dir from status_surface>)`. Completes the third artifact family
(#1993's deeper grain). **Minimal factory touch (C-001): derive from the existing `status_surface` +
`resolve_lanes_dir` seam — both already exist (Mission A) — add a thin lanes projection ONLY if the
derivation genuinely needs one.**

## Subtask guidance

### T027 — Route the lanes-dir write (D-12 mechanism)
In the `_lanes_feature_dir` C-LANES-1 region (`implement.py:979-984`), today `_lanes_feature_dir = feature_dir`
(the bare primary dir) — `implement.py` resolves it directly, with no `status_surface` in scope (alphonso S-3 /
pedro framing). Adopt by deriving the **coord feature dir** from the existing public resolver
`resolve_status_surface(primary_root, mission_slug)` (the coord/status authority under coord topology; the
primary dir under no-coord), then `resolve_lanes_dir(<that dir>)`. Public-resolver route, no `ExecutionContext`
threading (D-12).

### T028 — Thin projection only if needed
If the derivation reads cleanly off `resolve_status_surface` + the existing `resolve_lanes_dir`, do NOT add a
factory field or a new resolver (C-001). Add a thin helper in `lanes/persistence.py` ONLY if the coord-dir
derivation has no clean existing seam — and keep it pure consumer-routing (no new authority).

### T029 — Verify coord-vs-flat placement
Use the WP01 net's real-coord lanes-placement oracle (S-8): coord topology → coord authority; no-coord → flat.
Idempotency (NFR-004): lanes.json on-disk location unchanged for the coord case.

### T030 — Clean
`ruff`/`mypy` clean. The `implement.py` edit is scoped to the lanes-dir region only (ownership note: this WP
owns implement.py solely for that region within this mission).

## Definition of Done
- [ ] The lanes-dir write resolves from the coord surface (`resolve_lanes_dir(<coord feature dir>)`); lands on
      the coordination authority under coord topology, flat under no-coord (C-LANES, FR-008).
- [ ] No raw factory field added unless genuinely required (C-001); derivation prefers `status_surface` + the
      existing seam.
- [ ] WP01 lanes-placement oracle green; idempotency preserved (NFR-004).
- [ ] `ruff`/`mypy` clean, no suppressions. **C-008**: adjacent breakage fixed in-change.

## Reviewer guidance
Confirm lanes.json NEVER resolves to `primary_root` under coord topology (C-007/C-LANES-1 — a flatten here is
the #1991 regression). Confirm no new authority was built (C-001) — it should be `status_surface` +
`resolve_lanes_dir`, not a new resolver. Confirm the implement.py edit is scoped to the lanes region.

## Activity Log

- 2026-06-17T06:21:33Z – claude:sonnet:python-pedro:implementer – shell_pid=2897020 – Assigned agent via action command
- 2026-06-17T06:29:59Z – claude:sonnet:python-pedro:implementer – shell_pid=2897020 – WP06 lanes/coord complete (routed via status-surface resolver; 339 pass; C-007 coord-authority preserved). FORCE: flattened-mission guard false-positive. Orchestrator-driven.
- 2026-06-17T06:30:00Z – claude:sonnet:reviewer-renata:reviewer – shell_pid=2955713 – Started review via action command
- 2026-06-17T06:33:30Z – user – shell_pid=2955713 – C-LANES-1 routing correct: _lanes_feature_dir = _status_feature_dir (coord surface, not primary feature_dir). No new resolver/authority/factory (C-001). Test oracle asserts both arms (coord path under .worktrees, primary path not). 339 pass. ruff + mypy clean. implement.py edit scoped to lanes-dir region only. --force: flattened-mission kitty-specs-on-lane guard false-positive (target branch ahead by 59 commits from parallel lanes; no divergence in WP06 owned files).
