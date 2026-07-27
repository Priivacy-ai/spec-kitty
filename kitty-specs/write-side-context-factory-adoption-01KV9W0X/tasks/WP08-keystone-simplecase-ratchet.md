---
work_package_id: WP08
title: Keystone simple-case test + boundary ratchet
dependencies:
- WP02
- WP03
- WP04
- WP05
- WP06
requirement_refs:
- FR-005
- NFR-006
tracker_refs: []
planning_base_branch: feat/write-side-context-factory-adoption
merge_target_branch: feat/write-side-context-factory-adoption
branch_strategy: Planning artifacts for this mission were generated on feat/write-side-context-factory-adoption. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/write-side-context-factory-adoption unless the human explicitly redirects the landing branch.
subtasks:
- T035
- T036
- T037
- T038
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "3096494"
history:
- 2026-06-17 created (/spec-kitty.tasks)
agent_profile: python-pedro
authoritative_surface: tests/specify_cli/coordination/test_simple_case_flat_topology.py
create_intent:
- tests/specify_cli/coordination/test_simple_case_flat_topology.py
- tests/architectural/test_no_write_side_rederivation.py
execution_mode: code_change
owned_files:
- tests/specify_cli/coordination/test_simple_case_flat_topology.py
- tests/architectural/test_no_write_side_rederivation.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load python-pedro
```

Then read: `spec.md` **NFR-006** (the KEYSTONE — operator's binding requirement) + **SC-007/SC-008** +
**FR-005** (boundary ratchet, optional) + **C-007** (the per-diff-type routing this collapses) + **C-008**;
`plan.md` **D-7** (simple-case keystone) + **IC-SIMPLECASE**; `contracts/behavioral-contracts.md`
**C-SIMPLECASE** (the binding guard) + **C-BOUNDARY**.

## Objective

The **keystone** that makes the whole branch-target context object safe: prove that when every diff-type
target resolves to the **base** branch (no coordination branch declared, no lane worktree), spec-kitty runs
**exactly as it did before lanes/coordination existed** — every adopted fragment resolves to base, **ZERO**
`.worktrees/`/coord paths read or written, byte-identical to the historical flat path. Plus the optional
FR-005 boundary ratchet (lands LAST so it doesn't flag not-yet-adopted sites). **Lands after the adoption WPs
(WP02–WP06) — it integration-tests them.**

## Subtask guidance

### T035 / T036 — The keystone simple-case test (NFR-006/SC-007) — define the baseline concretely
New `test_simple_case_flat_topology.py`: build a **real single-branch repo** (full 26-char ULID, NO
coordination branch in meta.json, NO lane worktree — reuse WP01's `topology_fixtures` primary builder). Drive
the adopted write paths (root, placement, status surface, write-target, lanes) and assert (renata S-1 —
"byte-identical to pre-lane" needs an OBSERVABLE baseline, not a vibe):
- every adopted fragment resolves to the **base** branch / primary root (assert `== base`, the WP01 frozen
  oracle value);
- the **set** of filesystem paths read/written contains **ZERO** entries under `.worktrees/` or any
  coordination surface (assert on the captured path-set, not a spot-check);
- the write-target == `target_branch` (the base), NOT git HEAD (SC-008 flat arm);
- the emitted status **event shape** matches the pre-lane flat event (the observable behavioral baseline).
Drive WITHOUT explicit `repo_root` (paula's trap). This is the binding guard for FR-004 (WP05).

### T037 — FR-005 boundary ratchet (REQUIRED, line-scoped, self-testing — lands last)
New `tests/architectural/test_no_write_side_rederivation.py` (paula SF-2 — NOT optional; a blanket-escape
ratchet is gameable). Flag write-side re-derivation (`feature_dir.parent.parent`, inline
`mission_id[:8]`/`mid8` recompute, `coord_branch or _current_branch`) in the adopted modules (emit, wpl,
lifecycle_events, store, worktree, status_transition). Requirements:
- **Line-scoped allow-list**, not file-scoped — seed it ONLY with the genuinely-deferred S2 #1716 ladder
  lines; a file-level allow-list is a blanket escape and is rejected.
- **"Ratchet bites" self-test**: a companion test that plants a `feature_dir.parent.parent` in an adopted
  module (in a tmp copy / via the detector on a fixture string) and asserts the ratchet FLAGS it — proving
  the guard isn't inert.
- MUST pass on the post-adoption tree (a flag on an adopted module = that module still re-derives = real
  finding). This is the one allowed form-coupled test (NFR-003).

### T038 — Confirm SC-007/SC-008 on the merged tree
Run the keystone + the WP01 net + the ratchet together on the integrated adoption tree. All green = the
branch-target object degrades cleanly to the simple case and the write-target is sourced from
`destination_ref`.

## Definition of Done
- [ ] The keystone simple-case test exists on a real single-branch repo (full ULID, no coord, no lanes):
      every fragment == base; the captured path-set has ZERO `.worktrees/`/coord entries; write-target == base;
      event shape matches the pre-lane flat baseline (SC-007/SC-008).
- [ ] The FR-005 boundary ratchet is **required**, line-scoped (allow-list = only the deferred S2 sites), with
      a "ratchet bites" self-test; passes on the post-adoption tree.
- [ ] **Gate-readiness (renata B-1/B-2):** drive every `in-mission` `issue-matrix.md` row (#1716/#1619/#1993)
      to its terminal verdict with an evidence ref; confirm `acceptance-matrix.json` criteria + the 5
      `negative_invariants` (NI-1..NI-5) have real evidence + pass_fail (no `pending`/`TODO` left at accept).
- [ ] Green alongside the WP01 net on the integrated tree. **C-008**: adjacent breakage fixed in-change.
- [ ] `ruff`/`mypy` clean, no suppressions.

## Reviewer guidance
The keystone is the operator's binding requirement — verify it genuinely proves the flat collapse (no coord
path touched, write-target = base, byte-identical to pre-lane), not a weaker assertion. Confirm the ratchet
actually bites (try planting a `feature_dir.parent.parent` in an adopted module — it must flag) and that its
allow-list isn't a blanket escape. Confirm it lands AFTER the adoptions (it would be red mid-mission otherwise).

## Activity Log

- 2026-06-17T07:01:18Z – user – shell_pid=3069208 – Resume after manual lane-h integration (WP02-06 merged, net 18 green). blocked->in_progress; workspace allocated.
- 2026-06-17T07:20:39Z – claude:opus:reviewer-renata:reviewer – shell_pid=3069208 – WP08 keystone+ratchet complete (29 pass; full-save flat case writes target_branch, NFR-006 holds; #1716 BookkeepingTransaction residual deferred; ratchet line-scoped+bites). FORCE: flattened-mission guard. Orchestrator-driven.
- 2026-06-17T07:20:40Z – claude:opus:reviewer-renata:reviewer – shell_pid=3096494 – Started review via action command
- 2026-06-17T07:24:14Z – user – shell_pid=3096494 – APPROVE (keystone). cycle-1 artifact was an ORCHESTRATION-RECOVERY (lane allocator cross-lane merge conflict, manually resolved; no code feedback) — not a quality rejection; arbiter override justified after independent review on the integrated lane-h tree. Full-save confirmed: test_flat_save_writes_target_branch_via_full_save_path drives MissionStatus.load().save() end-to-end → BookkeepingTransaction.acquire(legacy_mode) → _resolve_legacy_lane_destination reads git symbolic-ref HEAD and OVERRIDES caller destination_ref; fixture stands HEAD==base==target_branch so override yields base; asserts receipt.destination_ref==target_branch AND git-shows artifact committed onto target_branch — WOULD catch a flat-case HEAD divergence (assertion fails if HEAD≠target_branch). Resolver CWD-invariance proven separately (test_flat_write_target_is_cwd_invariant_base_not_head parks HEAD off-target, write-target stays base). Protected-branch fixture is SOUND: main/master protected by git.commit_helpers pre-dating lanes, so genuine simple case = operator on non-protected working branch==target_branch==HEAD; main would model the rejected path. Ratchet REQUIRED, token-based (ignores docstring quote at status_transition.py:261 — test_ratchet_ignores_prose), line-scoped allow-list={status_transition.py:295} = the deferred #1716 HEAD-fallback except-arm (pinned by test_allow_list_is_line_scoped + test_allow_listed_line_is_the_deferred_head_selector), and BITES (3 parametrized planted self-tests). Standalone scan = 1 finding total across all 6 adopted modules = the single allow-listed line; zero un-allow-listed. #1716 residual HONEST (issue-matrix row + keystone docstring record the BookkeepingTransaction HEAD-override deferral; diverges only under topology divergence, benign at HEAD==base). Gate honest: 7/9 criteria pass + 5 NIs pass; FR-006/FR-009 pending (WP07/WP09 docs, not in lane-h tree); overall_verdict pending. 29 tests green; ruff+mypy clean, zero suppressions. Lands on lane-h; primary may lag — orchestrator reconciles.
