---
work_package_id: WP01
title: Characterization net (clean-before-touch, FIRST)
dependencies: []
requirement_refs:
- NFR-001
- NFR-002
tracker_refs: []
planning_base_branch: feat/write-side-context-factory-adoption
merge_target_branch: feat/write-side-context-factory-adoption
branch_strategy: Planning artifacts for this mission were generated on feat/write-side-context-factory-adoption. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/write-side-context-factory-adoption unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "2883119"
history:
- 2026-06-17 created (/spec-kitty.tasks)
agent_profile: python-pedro
authoritative_surface: tests/specify_cli/write_side/
create_intent:
- tests/specify_cli/write_side/__init__.py
- tests/specify_cli/write_side/topology_fixtures.py
- tests/specify_cli/write_side/test_characterization_root_walks.py
- tests/specify_cli/write_side/test_characterization_write_target.py
- tests/specify_cli/write_side/test_lock_root_invariant.py
execution_mode: code_change
owned_files:
- tests/specify_cli/write_side/__init__.py
- tests/specify_cli/write_side/topology_fixtures.py
- tests/specify_cli/write_side/test_characterization_root_walks.py
- tests/specify_cli/write_side/test_characterization_write_target.py
- tests/specify_cli/write_side/test_lock_root_invariant.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before any code, load the implementer profile and the binding contracts. Run:

```
/ad-hoc-profile-load python-pedro
```

Then read, in this order:

1. `kitty-specs/write-side-context-factory-adoption-01KV9W0X/spec.md` — **NFR-001/002/003** (symmetry,
   topology-true fixtures, verification-by-deletion) and **C-006** (live-evidence + TDD-first).
2. `kitty-specs/write-side-context-factory-adoption-01KV9W0X/plan.md` — **D-9** (clean-before-touch, why this
   net lands FIRST) and the **IC-CHARNET** concern.
3. `kitty-specs/write-side-context-factory-adoption-01KV9W0X/contracts/behavioral-contracts.md` — **C-ROOT**,
   **C-TARGET**, **C-SIMPLECASE** (the obligations the net characterizes).
4. `kitty-specs/write-side-context-factory-adoption-01KV9W0X/research/pre-refactor/paula-test-smells.md` — the
   **live-evidence trap** (S-1/A-1): the strongest write-path suite passes `repo_root=` everywhere, so it is
   BLIND to the swap; the FR-004 divergence has ZERO witnessing test. THIS WP fixes that.
5. `kitty-specs/write-side-context-factory-adoption-01KV9W0X/research/reduction-census.md` — randy's FR-004
   divergence (flattened arm `destination_ref`=`target_branch` vs inline `_current_branch`=git HEAD at
   `coordination/status_transition.py:291`).

## Objective

Build the **topology-true characterization net** that turns "the inventory says equivalent" into "the suite
proves equivalent." Every later adoption WP proves itself by **deleting** an inline re-derivation and showing
this net stays green (NFR-003). This is the gate; it lands FIRST.

**The non-negotiable design rule (paula's trap — B-3, enforce it POSITIVELY):** the net MUST drive the write
sites **without** passing an explicit `repo_root=` AND without mocking the root/surface — those are escape
hatches that make the net blind to the swap. Concretely:
- **Drive from a non-primary CWD** (a coord worktree / submodule dir), and the FR-004 oracle from a CWD where
  `git HEAD ≠ target_branch`, so the re-derivation is actually exercised.
- **Positive mutation obligation:** the net is only valid if **reverting an adoption swap turns it RED**. WP01
  must include/describe a mutation check (temporarily reintroduce a `.parent.parent` walk or the inline
  `_current_branch` selector → the net MUST fail). A net that stays green under mutation is vacuous and is a
  review rejection.
- **No non-strict `xfail`** on the FR-004 oracle (B-4) — a silently-passing xfail is the removable-oracle
  vector. Pin the oracle by node-id; WP05 may only flip its asserted value, never delete the test.

## Context

The five write-side root walks (`status/emit.py`, `status/work_package_lifecycle.py`,
`status/lifecycle_events.py`, `status/store.py`, `coordination/status_transition.py::_repo_root_for_feature`)
plus the placement join, the status write-surface, the write-target, and the lanes-dir write are all
characterized here BEFORE anyone touches them. The fixtures you build are reused by every adoption WP and by
WP08's keystone — build them once, well.

## Subtask guidance

### T001 — Shared topology-true fixture module
Create `tests/specify_cli/write_side/topology_fixtures.py` with builders for the THREE real topologies
(NFR-002 — production-shaped, NO fabricated short ids):
- **primary**: a real git repo, full 26-char ULID `mission_id`, `kitty-specs/<slug>/` with `meta.json`.
- **coord**: the above PLUS a real coordination worktree (`.worktrees/<slug>-<mid8>-coord` on a real
  `kitty/mission-...` branch) materialized via `git worktree add`.
- **submodule**: the mission repo embedded as a real git submodule (a `.git` *file*, not dir — this is the
  #2011/`core/paths.py` ancestor-walk hazard surface).
Return handles exposing the feature_dir, the coord feature_dir, and the expected root/surface/target per
topology. Reuse Mission A's topology fixtures if present (`tests/mission_runtime/`); do not fabricate.

### T002 — FR-004 write-target divergence (RED-on-HEAD)
Characterize the latent bug the adoption fixes: assert what the inline `coord_branch or _current_branch`
selector resolves to vs what `resolve_placement_only(...).destination_ref` resolves to, **driven without an
explicit repo_root**, from a CWD where `git HEAD ≠ target_branch`. On HEAD this documents the divergence
(flattened/correct arm = `target_branch` CWD-invariant; inline = git HEAD). Pin the oracle by node-id; **no
non-strict xfail** (B-4). Note: a contract test already encodes the buggy value —
`tests/unit/status/test_mission_status_aggregate.py::test_save_supports_identity_bearing_legacy_mission` (WP05
owns updating it). This net adds the **topology-true** oracle that test lacks.

### T003 — Coord-topology root/surface parity
For all 5 root-walk sites, assert the current resolved root + the status write surface under the coord
topology — freeze them as the before/after oracle. These go green-stay-green across the adoption (equivalence).

### T004 — Submodule-topology characterization
Assert root resolution under the submodule fixture (the `.git`-file ancestor-walk surface). This is where a
naive `.parent.parent` and the canonical resolver can diverge — pin both.

### T005 — store + lanes-placement characterization
Cover `store.py::_find_mission_specs_root` (slug-dir / deeper-nesting / non-kitty-specs fallback) and the
real-coord `lanes.json` placement (the FR-008 oracle: coord topology → coord authority; no-coord → flat).

### T006 — Public lock-root behavioral invariant
paula S-4/S-9: the existing lock-root tests assert the **private helper by name**. Add a PUBLIC behavioral
invariant here (the lock root for a mission resolves to its primary root across topologies) so WP02 can
retire the by-name tests without losing coverage.

## Definition of Done
- [ ] `tests/specify_cli/write_side/` net exists; fixtures are topology-true (full ULID, real coord-worktree,
      real submodule) — NO fabricated short ids, NO single-repo stand-in (NFR-002).
- [ ] The net drives the write sites WITHOUT explicit `repo_root=` (paula's trap closed).
- [ ] The FR-004 divergence is witnessed (RED/oracle on HEAD); the equivalence rows are green on HEAD.
- [ ] The public lock-root invariant exists (replaces the private-by-name coverage WP02 retires).
- [ ] `ruff` + `mypy` clean on the new test module; no suppressions (NFR-005).
- [ ] **C-008 Fix-don't-litigate:** any adjacent test/lint breakage you hit while building fixtures is fixed
      in this change, not deferred-with-blame.

## Reviewer guidance (reviewer-renata)
Verify the net actually exercises the re-derivation (grep the tests for `repo_root=` — there should be NONE on
the driven calls). Confirm the fixtures are real git topologies (real `git worktree`, real submodule `.git`
file), not mocked paths. Confirm the FR-004 oracle captures randy's divergence. This net is the foundation —
if it is blind to the swap, every downstream "verification-by-deletion" is vacuous.

## Activity Log

- 2026-06-17T05:55:13Z – claude:opus:python-pedro:implementer – shell_pid=2865475 – Assigned agent via action command
- 2026-06-17T06:08:41Z – claude:opus:python-pedro:implementer – shell_pid=2865475 – Characterization net built (5 modules, tests/specify_cli/write_side/): 3 REAL topologies (full ULID, real coord worktree, real submodule .git-FILE). FR-004 oracle pinned by node-id (no xfail); equivalence rows GREEN (18 passed); root-walk before-oracle pins HEAD divergence; store+lanes+public lock-root invariant; mutation check VERIFIED LIVE (swap line 291 -> oracle RED). ruff+mypy clean; no repo_root= on driven calls. [--force: lane-surface status desync, coord board reads in_progress]
- 2026-06-17T06:11:21Z – claude:opus:python-pedro:implementer – shell_pid=2865475 – FORCE rationale: flattened mission (no coord branch) — status correctly lives on the planning branch feat/write-side-context-factory-adoption, but the kitty-specs-on-lane guard misfires (its own message names the branch I am already on as the legal home). Legitimate in_progress->for_review reconcile after lane-a committed for_review to its lane surface. WP01 net: 18 pass, mutation check bites. Logged to guard-friction trace (#1716/#2017).
- 2026-06-17T06:11:34Z – claude:opus:reviewer-renata:reviewer – shell_pid=2883119 – Started review via action command
- 2026-06-17T06:17:29Z – user – shell_pid=2883119 – Review passed [--force: flattened mission — kitty-specs-on-lane guard false-positive; status legitimately lives on planning branch feat/write-side-context-factory-adoption per the prompt-authorized override]. 3 topologies REAL git (full 26-char ULIDs; real git worktree add coord; real git submodule with .git FILE confirmed via .is_file()); NO repo_root= on driven calls (only a dataclass field assignment + docstrings); NO xfail/skip/mock (monkeypatch chdir-only, drives non-primary CWD); FR-004 oracle pinned by node-id, drives production _identity_for_request. MUTATION INDEPENDENTLY VERIFIED by reviewer: applied WP05 swap (destination_ref via resolve_placement_only) at status_transition.py:291 -> FR-004 oracle went RED (destination_ref='main' != off-target branch), equivalence rows stayed green, reverted src clean. Coverage: 5 root-walk sites + store 3 scan shapes + coord/flat lanes placement + public lock-root invariant. 18 tests pass; ruff+mypy clean; test-only, owned files only, no src edits. (Adjacency: added Follow-up handles to issue-matrix deferred rows #1878/#1970/#2017 on planning branch to clear the accept gate.)
