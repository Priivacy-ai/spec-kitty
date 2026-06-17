---
work_package_id: WP05
title: Coordination root + surface + write-target adoption (highest risk)
dependencies:
- WP01
requirement_refs:
- FR-001
- FR-003
- FR-004
- FR-007
tracker_refs: []
planning_base_branch: feat/write-side-context-factory-adoption
merge_target_branch: feat/write-side-context-factory-adoption
branch_strategy: Planning artifacts for this mission were generated on feat/write-side-context-factory-adoption. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/write-side-context-factory-adoption unless the human explicitly redirects the landing branch.
subtasks:
- T021
- T022
- T023
- T024
- T025
- T026
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "3054152"
history:
- 2026-06-17 created (/spec-kitty.tasks)
agent_profile: python-pedro
authoritative_surface: src/specify_cli/coordination/status_transition.py
create_intent:
- tests/specify_cli/coordination/test_status_transition_adoption.py
execution_mode: code_change
owned_files:
- src/specify_cli/coordination/status_transition.py
- tests/specify_cli/coordination/test_status_transition_adoption.py
- tests/unit/status/test_mission_status_aggregate.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load python-pedro
```

Then read, carefully — this is the highest-risk WP:
1. `spec.md` — **FR-003** (write-surface → coord authority), **FR-004** (write-target → `destination_ref`),
   **FR-007** (second-factory reduction), **C-007** (per-diff-type routing; status→coord, NEVER `primary_root`),
   **NFR-004** (idempotency), **C-008**.
2. `plan.md` — **IC-COORD**, **D-2** (FR-004 IN scope, the branch-target object's core), **D-5** (equivalence
   gate), and **D-1** (DEFER only the S2 selection ladder / #1716 ~2094-LOC root).
3. `contracts/behavioral-contracts.md` — **C-SURFACE**, **C-TARGET** (the exact MUST/MUST-NOT obligations).
4. `research/write-site-inventory.md` — S1 (surface + target at `status_transition.py:234-295`), R5
   (`_repo_root_for_feature`), and the deferred S2 ladder boundary.
5. `research/reduction-census.md` — randy's FR-004 divergence at `status_transition.py:291`
   (`_current_branch`=git HEAD vs flattened `destination_ref`=`target_branch`).

## Objective

Route the second parallel write-factory in `coordination/status_transition.py` to consume the
factory-projected fragments: **root** (R5) → `workspace.primary_root`; **status write surface** →
`status_surface.status_write_dir` (the COORD authority — C-007, never `primary_root`); **write-target**
(`coord_branch or _current_branch`) → `branch_ref.destination_ref` (FR-004). Reduce `_identity_for_request`
to consume the projection (FR-007). **DEFER** only the S2 write-surface-SELECTION ladder
(`_read_contract_from_transaction_target`, the #1716 topology authority — it computes the *same value* the
factory already does; out of scope, D-1).

This WP finalizes the **branch-target context object's core**. Its safety rests on WP01's net + WP08's
keystone + the idempotency test here.

## Subtask guidance

### T021 — Root (R5)
Route `_repo_root_for_feature`'s bare `.parent.parent` walk to `workspace.primary_root`. (pedro: this is a
*different, simpler* walk than emit/wpl — do not assume it shares their helper.) Delete the walk.

### Mechanism (D-12, post-squad)
Route to the **existing public pure resolvers** — `resolve_status_surface` (surface) and
`resolve_placement_only(...).destination_ref` (write-target), `resolve_canonical_root`/`get_main_repo_root`
(root). NOT a new projection-entry and NOT an edit to `resolution.py` (C-001; the only `resolution.py` touch
in the mission is WP07's deletion). The proof is read+write calling the same resolver (SC-002).

### T022 — Write surface (FR-003, C-007) — assert POSITIVELY
Route the status write directory via `resolve_status_surface`. Under coord topology it MUST resolve to the
**status/coord** authority and MUST NOT degrade to `primary_root` (fail-closed preserved — read-primary/
write-coord, Robert #2007 rule #1). Assert it **positively** (renata S-3): `surface == <coord feature dir>`
AND `surface != primary_root` — a bare "not primary_root" is unfalsifiable against a silently-collapsed fixture.

### T023 — Write target (FR-004, the latent-bug fix) — own the witnessing test
Replace the inline `coord_branch or _current_branch` selector with `resolve_placement_only(...).destination_ref`.
Coord topology → coord branch; flat/base topology → `target_branch` (CWD-invariant, NOT git HEAD). This flip
turns **two** tests: the WP01 topology-true oracle goes green, AND
`tests/unit/status/test_mission_status_aggregate.py::test_save_supports_identity_bearing_legacy_mission`
(owned here) currently asserts the **buggy git-HEAD value** (`destination_ref == "legacy-lane"`) — update its
assertion to the CWD-invariant `target_branch` value with a before→after rationale comment (paula B-1). **Carry
the flat-arm proof inline** (renata S-4): since WP08's keystone lands AFTER this WP, add a DoD assertion here
that the all-base/flat arm yields `target_branch` (not HEAD) so WP05 proves its own correctness.

### T024 — Second-factory reduction (FR-007) — grep-able bar
Reduce the bounded `_identity_for_request` body the adopted resolvers now cover. **Objective bar** (renata S-5):
after this WP, `grep` of `status_transition.py` shows no surviving inline `.parent.parent`,
`coord_branch or _current_branch`, or `mid8`/`mission_id[:8]` recompute — only the named S2 selection ladder
remains (deferred #1716, allow-listed by the WP08 ratchet). Do NOT enlarge into the ~2094-LOC topology authority.

### T025 — Idempotency + equivalence (the gate)
New `test_status_transition_adoption.py`: (a) **before/after on-disk-target idempotency** (NFR-004) — the
coord case writes to the SAME on-disk target as before; the flat case writes to `target_branch`; the FR-004
oracle flips green. (b) **D-5 equivalence** — parameterized over primary/coord/submodule (WP01 fixtures),
read==write resolution for root + surface + target. Drive WITHOUT explicit `repo_root` (paula's trap).

### T026 — Clean
`ruff`/`mypy` clean, complexity ≤15 (watch `_identity_for_request`'s complexity — extract helpers if it nears
the ceiling), no suppressions.

## Definition of Done
- [ ] R5 walk deleted → `workspace.primary_root`; surface → `status_surface.status_write_dir` (coord
      authority, never `primary_root`, C-007); write-target → `branch_ref.destination_ref` (FR-004).
- [ ] `_identity_for_request` reduced to consume the projection (FR-007); S2 ladder untouched (deferred).
- [ ] Idempotency before/after on-disk-target identical (NFR-004); D-5 equivalence green across the 3 topologies.
- [ ] The three fragments (`primary_root`, `status_write_dir`, `destination_ref`) are now load-bearing (SC-002).
- [ ] `ruff`/`mypy` clean ≤15, no suppressions. **C-008**: adjacent breakage fixed in-change.

## Reviewer guidance
This is the WP most likely to silently churn on-disk state or flatten a coord write to primary. Verify: (1)
the surface NEVER resolves to `primary_root` under coord topology (C-007 — a flatten here is the #2004/#2007
regression); (2) the idempotency before/after is asserted, not inspected; (3) the FR-004 oracle actually
flipped green (the bug is fixed, with a witnessing test — C-006 live-evidence); (4) the S2 ladder was NOT
pulled in (scope creep into #1716).

## Activity Log

- 2026-06-17T06:21:29Z – claude:opus:python-pedro:implementer – shell_pid=2897020 – Assigned agent via action command
- 2026-06-17T06:45:58Z – claude:opus:python-pedro:implementer – shell_pid=2897020 – WP05 coord root/surface/target complete (266+572 pass; FR-004 oracle flipped; C-007 surface positive-asserted; idempotency+FR-007 clean). FLAGGED: legacy-lane write-target comes from BookkeepingTransaction (separate path, reads HEAD) — implementer kept its value + flagged for reviewer adjudication. FORCE: flattened-mission guard. Orchestrator-driven.
- 2026-06-17T06:46:00Z – claude:opus:reviewer-renata:reviewer – shell_pid=3054152 – Started review via action command
- 2026-06-17T06:53:32Z – user – shell_pid=3054152 – APPROVE (reviewer-renata). [--force: flattened-mission/parallel-lane guard - lane-e is 80 commits behind feat target due to sibling-lane churn; review was performed against the correct kitty/mission-...01KV9W0X..lane-e diff and the lane content under review is unaffected by the behind-ness; orchestrator reconciles primary.] FR-001 R5 walk->resolve_canonical_root w/ WorkspaceRootNotFound->feature_dir fallback: confirmed. FR-003/C-007 surface->resolve_status_surface POSITIVE-asserted (==coord '-coord' worktree authority AND != primary_surface_dir, never primary_root): confirmed live. FR-004 seam (_identity_for_request:291) routed to resolve_placement_only(...).ref; flat-arm proven CWD-invariant target_branch NOT git HEAD (CWD parked off-target); coord-arm==coord_branch; bootstrap fallback is except-arm-ONLY (happy-path selector is the resolver). FR-007 grep clean: no surviving happy-path .parent.parent / coord_branch-or-_current_branch / mid8-recompute; S2 ladder (#1716) untouched. NFR-004 idempotency before==after ASSERTED not inspected; D-5 equivalence parameterized primary/coord/submodule driven WITHOUT explicit repo_root. WP01-net oracle edits = genuine divergence->convergence flips (B-4 node-id preserved, no xfail/delete) per planned WP01->WP05 handoff. 266 tests pass; ruff clean; new code mypy-clean. 6 pre-existing no-any-return (113/129/252/454/500/678) confirmed BASELINE byte-for-byte on base branch -> boy-scout-later debt, acceptable bounded-diff call. ANTI-PATTERN CHECKLIST: 1 dead-code PASS (_resolve_write_target called :355); 2 synthetic-fixture PASS (tests invoke real _identity_for_request); 3 silent-empty-return PASS (except arm returns documented fallback); 4 FR-coverage PASS; 5 frozen-surface PASS (S2 ladder untouched); 6 locked-decision PASS (no primary_root flatten); 7 shared-ownership PASS (legacy aggregate test coordinated, BookkeepingTransaction NOT edited); 8 production-fragility PASS. LEGACY-LANE ADJUDICATION = CORRECT SCOPE DEFERRAL: independently verified _resolve_legacy_lane_destination (transaction.py:258) exists, reads git symbolic-ref HEAD, OVERRIDES caller destination_ref in _acquire_locked(722-733) for _is_legacy_mission ONLY (meta present + no coord_branch) - a SEPARATE path from the seam WP05 adopted. Keeping test_save_supports_identity_bearing_legacy_mission=='legacy-lane' is CORRECT (flipping=false-green vs real prod); override is #1716 deferred per C-003/D-1; C-TARGET only mandates deleting the inline _identity_for_request selector (done). BINDING WP08 FOLLOW-UP: NFR-006 simple case (full ULID, meta present, no coord_branch, no lanes) is the SAME _is_legacy_mission topology -> end-to-end MissionStatus.save can route through BookkeepingTransaction and override destination_ref to git HEAD. WP08 keystone T036 ('write-target==target_branch NOT git HEAD' end-to-end) MUST drive the FULL save path (not just _identity_for_request) and will expose whether the latent git-HEAD bug persists on the legacy/flat write path; if so it is a #1716 follow-on NOT a WP05 regression. Issue-matrix #1716 row should record the BookkeepingTransaction legacy-override residual. NIT (non-blocking): test comment misattributes deferral to 'C-004' (this mission's C-004='No patch-version prescription'); correct grounding is C-003/D-1.
