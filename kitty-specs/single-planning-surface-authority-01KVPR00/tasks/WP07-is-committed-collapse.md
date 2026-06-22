---
work_package_id: WP07
title: Collapse is_committed 3-leg OR to single-surface check (gated, last)
dependencies:
- WP04
- WP05
requirement_refs:
- FR-011
tracker_refs:
- "2062"
- "2069"
planning_base_branch: feat/single-planning-surface-authority
merge_target_branch: feat/single-planning-surface-authority
branch_strategy: Planning artifacts for this mission were generated on feat/single-planning-surface-authority. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/single-planning-surface-authority unless the human explicitly redirects the landing branch.
subtasks:
- T035
- T036
- T037
- T038
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "645645"
history:
- Created by /spec-kitty.tasks
agent_profile: randy-reducer
authoritative_surface: src/specify_cli/missions/_substantive.py
create_intent: []
execution_mode: code_change
owned_files:
- src/specify_cli/missions/_substantive.py
role: implementer
tags: []
---

# WP07 — Collapse `is_committed` 3-leg OR to a single-surface check (IC-07, LAST, live-repro-gated)

## Profile load (REQUIRED FIRST STEP)

Before touching any code, **load the `randy-reducer` profile** from the project doctrine
(`src/doctrine/agent_profiles/built-in/randy-reducer.agent.yaml`, or via the governed
profile-load surface / `ad-hoc-profile-load`). Adopt its identity, governance scope, boundaries,
and initialization declaration.

In your init declaration, state explicitly that you understand:

- This WP is a **behavior-preserving semantic REDUCTION** (the randy-reducer lens), NOT a feature
  change. You are removing a load-bearing workaround, not adding behavior.
- The 3-leg OR in `is_committed` is a **load-bearing workaround for the surface split** that
  WP04 (read path) and WP05 (write authority) close. **It MUST NOT be collapsed until that split
  is structurally gone AND a real flattened-mid-flight repro is green** (C-002 / NFR-001). This
  is the mission's **TOP risk** (plan.md Risk #1, "Load-bearing-workaround collapse").
- The randy method is: (1) map the protected behavioral envelope BEFORE reducing, (2) prove
  equivalence, (3) then reduce. You do not delete a leg you have not first proven dead.
- You are an **implementer** only. Do NOT self-review; the reviewer is `reviewer-renata`
  (a separate role).

---

## Objective

Once the read surface (FR-006, landed by WP04: stored-topology read) and the write surface
(FR-007, landed by WP05: single write authority) are **structurally singular**, the
multi-surface diagnostics workaround in `src/specify_cli/missions/_substantive.is_committed`
(`:317-412`) is no longer load-bearing. Reduce it from a **3-surface OR** to a **single-surface
check on the resolved placement ref**, removing the multi-surface workaround (FR-011).

Additionally — because WP07 owns `_substantive.py` outright — **route the `.kind is COORDINATION`
decision site at `_substantive.py:379`** through WP01's `routes_through_coordination` predicate
(FR-005). This is the one of the nine `.kind is COORDINATION` sites that lives in this file; it
belongs here because no other WP may edit `_substantive.py` (disjoint `owned_files`).

This is a **behavior-preserving reduction** (NFR-003): for the already-correct topologies
(coord-fresh, create-window, single-branch, coord-deleted) and the #1718/#1848 transients, the
single-surface check MUST return **the same result** the 3-leg OR did. You prove this with a
behavioral-envelope equivalence subtask BEFORE the reduction, and with the FR-010 differential
gate (incl. the live flattened-stale-coord row) green AFTER.

---

## Context — ground truth (verified, cite when you work)

Read `src/specify_cli/missions/_substantive.py` end-to-end before editing. Verified facts as of
this WP's authoring (re-verify line numbers — WP00 re-keyed ratchets onto composite keys precisely
so prior WPs could move lines under you; confirm against the live file):

- **`is_committed(file_path, repo_root, placement=None, *, target_branch=None,
  primary_repo_root=None, diagnostics=None) -> bool`** at `:317-412`. Its docstring (`:326-363`)
  documents the **three ORed legs** explicitly:
  - **Leg 1 — coordination-branch ref** (`:371-388`): only when `placement.kind is
    CommitTargetKind.COORDINATION` (the `.kind` read at **`:379`** — this is the FR-005 site you
    must also route). Runs `_ref_carries_path(git_cwd, coord_ref, tree_path)`.
  - **Leg 2 — HEAD of the file's worktree** (`:390-395`): `_head_carries_path(git_cwd, tree_path)`.
  - **Leg 3 — primary-target-branch ref** (`:397-410`, "FR-005 / #7"): when `target_branch` is
    supplied, `_ref_carries_path(primary_root, target_branch, tree_path)` against
    `primary_repo_root or repo_root`.
- **Why the 3-leg OR exists (the load-bearing-workaround):** before this mission, the read path
  could hand a caller *the wrong surface* (the coord worktree for a mission that actually wrote to
  PRIMARY, or vice-versa) because the surface was re-inferred ad-hoc at many seams. Leg 3 was added
  ("#7 false-negative") precisely because "a spec committed only on the primary target branch is
  found here even when legs 1 and 2 both miss because the read-path handed us the coord surface"
  (verbatim from the docstring `:336-341`). **The OR masks the surface split.** WP04/WP05 remove the
  split at the root (stored topology drives the read path; one write authority places the artifact),
  so the resolved placement ref alone is now authoritative and the cross-surface fallback legs
  become dead masking.
- **The one in-file caller of `is_committed`** (for behavioral-envelope mapping — it is NOT yours
  to edit, owned by IC-05's WP, but you must preserve its contract): `setup-plan` in
  `src/specify_cli/cli/commands/agent/mission.py:2118-2168`. It calls `is_committed(spec_file,
  repo_root, placement=_resolve_planning_placement(...), target_branch=target_branch,
  primary_repo_root=get_main_repo_root(repo_root), diagnostics=_commit_diagnostics)` and surfaces
  `spec_commit_surfaces_checked` (the diagnostics list) in the blocked payload. **Whatever you do to
  the signature/diagnostics MUST keep this caller's `spec_committed` verdict and its diagnostics
  contract intact** unless the dependency WPs (WP04/WP05) have already re-pointed it — confirm at
  implement time. Do NOT silently break the `spec_commit_surfaces_checked` payload key.
- **Tests that pin `is_committed` behavior** (your equivalence-envelope evidence base — run these,
  do not delete or weaken them to make red go green):
  - `tests/integration/test_specify_plan_commit_boundary.py`
  - `tests/integration/test_p0_pinning_regressions.py` (#1718/#1848 P0 pins — the create-window and
    coord-deleted carve-outs)
  - `tests/runtime/test_setup_plan_sync_evidence.py`
  - `tests/specify_cli/cli/commands/agent/test_mission_planning_entry.py`
  - the differential equivalence gate `tests/missions/test_surface_resolution_equivalence.py`
    (extended by WP04 with the pure stored-topology cell + the on-disk flattened-stale-coord row).

**The protected behavioral envelope (NFR-003) — what the single-surface check MUST still return:**

| Topology / transient | Pre-reduction (3-leg OR) verdict | Post-reduction (single-surface) MUST match |
| --- | --- | --- |
| `SINGLE_BRANCH` (no coord) — artifact on HEAD | committed via Leg 2 | committed on the resolved (PRIMARY) ref |
| `LANES` — artifact on lane/primary | committed via Leg 2/3 | committed on the resolved ref |
| `COORD` / `LANES_WITH_COORD` — artifact on coord ref | committed via Leg 1 | committed on the resolved (COORD) ref |
| create-window (#1718: coord declared, worktree not materialized) — artifact on PRIMARY | committed via Leg 2/3 | committed on the resolved (PRIMARY) ref — probe still discriminates |
| coord-deleted (#1848: coord branch gone) | hard-fails upstream (`CoordinationBranchDeleted`) | **unchanged** — preserved, not subsumed (C-006) |
| flattened-stale-coord (#2062: stored SINGLE_BRANCH/LANES + stale `-coord` husk) | committed via Leg 2/3 (Leg 1 mis-targets husk) | committed on the resolved (PRIMARY) ref — husk structurally not consulted |

---

## Subtasks

### T035 — Map the behavioral envelope BEFORE reducing (randy equivalence-evidence)

- Produce the **pre-reduction behavioral envelope** for `is_committed`: enumerate, against the live
  code, exactly which inputs reach each leg and what each returns for all four `MissionTopology`
  cells PLUS the create-window, coord-deleted, and flattened-stale-coord transients (the table
  above, verified against the actual code paths — cite `:line` for each leg).
- Capture this envelope as **test evidence**, not prose. The behavioral-envelope table above MUST
  become a **REQUIRED parametrized characterization test** (do NOT defer it to "add if a row is
  unpinned" — envelope coverage is not the implementer's to self-assess away). Parametrize **one row
  per (topology × transient)**:
  - the **4 `MissionTopology` cells** (`SINGLE_BRANCH`, `LANES`, `COORD`, `LANES_WITH_COORD`), AND
  - the **#1718 create-window** transient (coord declared, worktree not materialized), AND
  - the **#1848 coord-deleted** transient (coord branch gone).

  Each parametrized case asserts that `is_committed`'s result is **IDENTICAL before and after the
  reduction** (the pre-reduction 3-leg-OR verdict and the post-reduction single-surface verdict must
  match for that row). The test goes in the existing `_substantive` `is_committed` test surface
  (`tests/specify_cli/missions/test_is_committed_coord_aware.py`) — extend it, do NOT create a
  parallel test file (so `create_intent` stays empty).
- **Output:** a short equivalence-evidence note in the WP's review notes mapping each leg of the OR
  to the single-surface check that subsumes it, citing the verified line numbers. This is the
  "prove equivalence before reduce" gate — a reduction without it is a regression risk.

### T036 — Route the `.kind is COORDINATION` site (FR-005) through `routes_through_coordination`

- At `_substantive.py:~379` replace the direct `placement.kind is CommitTargetKind.COORDINATION`
  read with WP01's `routes_through_coordination(placement)` predicate (import from
  `mission_runtime` per WP01's public surface — confirm the exact import path WP01 published; keep
  the module-level circular-import-avoidance pattern that the current code documents at `:374-376`).
- This is one of the nine FR-005 decision sites; it lives here because WP07 owns `_substantive.py`.
  Do NOT delete the `CommitTargetKind` type or its construction — eradication is Mission B (C-007).
  You only stop *reading* `.kind` to decide.
- Preserve the existing `except AttributeError: coord_ref = None` defensive fallback semantics
  unless the predicate makes it provably unreachable; if so, remove it WITH a test that proves it.

### T037 — Reduce the 3-leg OR to a single-surface check on the resolved placement ref (FR-011)

- **Gate first (binding, non-fakeable):** do NOT begin this reduction until BOTH dependency
  conditions hold and you have witnessed them:
  - (a) WP04's differential gate `tests/missions/test_surface_resolution_equivalence.py` is GREEN,
    **including the on-disk `flattened-stale-coord` row** and the pure stored-topology cell (run it,
    paste the result into review notes — do not assert "should pass").
  - (b) A **witnessed live flattened-mid-flight repro** (the #2062 topology) shows the
    single-surface check returns the SAME `is_committed` verdict the 3-leg OR returned for every
    handle form. (Use the live-repro recipe from `quickstart.md`; carry the dogfooding-friction
    rule — this mission's own `meta.json` is topology-backfilled per FR-003.)
- Reduce the body of `is_committed` (`:364-412`) so it checks **the single resolved placement ref**
  for the surface the read/write authority now guarantees, removing the masking fallback legs that
  WP04/WP05 made dead. Keep the `_git_commit_check_context` worktree-relative tree-path resolution
  (`:263-283`, `:364-369`) — that is path mechanics, not a surface-split leg, and is still needed.
- **Required reduction step — orphan the dead leg helper, with grep proof.** Collapsing the 3-leg
  OR to one surface-check **structurally orphans one of the two private leg helpers**: Leg 2 used
  `_head_carries_path`; Legs 1/3 used `_ref_carries_path`. The single-surface form keeps the helper
  for the surface it now checks and **leaves the other with no remaining caller**. This is NOT an
  optional campsite afterthought — a dead private helper on this touched surface MUST be removed
  in-slice (DIRECTIVE_025 Boy-Scout half: leaving it is under-cleaning the change you just made).
  After the collapse, `grep` BOTH `_ref_carries_path` AND `_head_carries_path` for remaining callers
  across `src/` and the test surface, then either:
  - **REMOVE** the now-orphaned helper (delete its definition), pasting the grep output that proves
    zero remaining callers as evidence in review notes; OR
  - if both helpers still carry a caller, **document why each survives** (paste the grep showing the
    surviving call sites).

  Keep randy's discipline: **only delete a helper you have PROVEN dead via `grep`** — no speculative
  deletion, no removing a helper "because it looks unused". The proof (grep output) is the gate, not
  the eyeball. Suggested sweep: `grep -rn "_ref_carries_path\|_head_carries_path" src/ tests/`.
- Keep the `diagnostics` sink contract: it MUST still append a human-readable line per ref/surface
  checked (now one surface), so the `setup-plan` caller's `spec_commit_surfaces_checked` payload
  stays populated and truthful. Do not strip diagnostics in the name of reduction.
- Update the function docstring (`:326-363`) to describe the single-surface semantics — remove the
  now-false "Three legs are ORed together" narrative and the "#7 false-negative" rationale; replace
  with the stored-topology / single-resolved-surface contract. A stale docstring documenting a
  removed workaround is itself debt (campsite #1970 on touched lines).

### T038 — Prove behavior-preserving + clean gates (NFR-003 / NFR-004)

- Run the full pinned set from Context plus the differential gate. **All MUST be green**, including
  the #1718 (create-window) and #1848 (coord-deleted) P0 pins. If any go red, the reduction is NOT
  equivalence-preserving — fix the reduction, do NOT weaken/delete the pin (these are data-loss and
  false-negative carve-outs; deleting a test to go green is forbidden).
- `ruff check` and `mypy` zero issues/warnings on `_substantive.py`; cyclomatic complexity ≤15 on
  the reduced `is_committed` (the reduction should LOWER it); no new S1192 (the reduction should
  remove the duplicated diagnostics literals — hoist any literal that now appears ≥3×). No `# noqa`
  / `# type: ignore` / suppression added (NFR-004).
- **Campsite #1970 — touched lines only.** Opportunistically clean adjacent debt on the lines you
  actually edit (e.g. dead helpers `_ref_carries_path` / `_head_carries_path` if the reduction
  orphans one — but only delete a helper you prove has no remaining caller via `grep`). Do NOT
  refactor untouched regions; the named de-godding extractions are carved to block C (C-008).
- **FR-005 repo-wide completeness check (integrating, because WP07 is LAST).** Run a repo-wide
  grep/AST sweep and assert that the **ONLY surviving `target.kind is CommitTargetKind.COORDINATION`
  *decision* comparison is the one INSIDE `routes_through_coordination`**. All nine FR-005 decision
  sites are split across WP01/WP05/WP06/WP07; as the final WP you own the integrating proof that
  every one has been routed and **zero decision-reads leaked**. The legitimate `CommitTarget(...)`
  *constructions* and the `CommitTargetKind` enum members remain (those are Mission B / C-007, not
  decision-reads) — distinguish a `.kind is COORDINATION` comparison from a `kind=...COORDINATION`
  construction. Paste the sweep command + its (single-hit) output into review notes. This is cheap
  insurance against a death-spiral-class regression where a stray decision-read re-opens the split.
  Suggested sweep: `grep -rn "\.kind is CommitTargetKind.COORDINATION" src/` (or
  `grep -rn "is CommitTargetKind.COORDINATION"`) — confirm the single match resolves to the body of
  `routes_through_coordination`.

---

## Branch Strategy

Planning artifacts for this mission were generated on `feat/single-planning-surface-authority`.
During `/spec-kitty.implement` this WP may branch from a dependency-specific base (it depends on
WP04 and WP05 — the implement loop auto-merges the approved dependency-lane tips into your base).
Completed changes MUST merge back into `feat/single-planning-surface-authority` unless the human
explicitly redirects the landing branch. This WP runs **LAST** in the mission ordering; do not
start it before WP04 and WP05 are approved/done.

---

## Definition of Done — non-fakeable

A reviewer can FALSIFY each of these; "looks fixed on static read" is explicitly insufficient
(MEMORY: live-evidence over static-fixed; a workaround collapsed speculatively regresses live
missions — the duct-tape death-spiral in reverse).

1. **Gate witnessed, not asserted.** Review notes contain the actual GREEN run output of
   `tests/missions/test_surface_resolution_equivalence.py` showing BOTH the pure stored-topology
   cell AND the on-disk `flattened-stale-coord` row passing, AND the `type(a) is type(b)` +
   `error_code` assertions present/unweakened. A claim without pasted evidence fails DoD.
2. **Live flattened repro witnessed.** Review notes contain a witnessed live flattened-mid-flight
   run (the #2062 topology) demonstrating the reduced `is_committed` returns the SAME verdict the
   3-leg OR returned, for every handle form. No live repro ⇒ NOT done (C-002 — #2062 never closes
   on static reading).
3. **Equivalence envelope recorded + parametrized (T035).** The pre-reduction → single-surface
   mapping table is in review notes with verified `:line` citations, AND a REQUIRED parametrized
   characterization test exists in `tests/specify_cli/missions/test_is_committed_coord_aware.py`
   with one row per (topology × transient) — the 4 `MissionTopology` cells PLUS the #1718
   create-window and #1848 coord-deleted transients — each asserting `is_committed` returns an
   IDENTICAL verdict before and after the reduction. "Add a test if a row is unpinned" does NOT
   satisfy this; every row must be a green parametrized case.
4. **3-leg OR is gone (FR-011).** `is_committed` checks a single resolved surface; the coord-ref and
   primary-target-branch fallback legs are removed; the docstring no longer claims "Three legs are
   ORed". `grep` for the removed leg helpers shows no orphaned dead code.
4a. **Orphaned leg helper removed, grep-proven (T037 reduction step).** The reduction is INCOMPLETE
   if it lowers the OR but leaves a now-dead private helper. Collapsing the 3-leg OR structurally
   orphans one of `_ref_carries_path` / `_head_carries_path` (Leg 2 used `_head_carries_path`; Legs
   1/3 used `_ref_carries_path`). The PR MUST show the orphan grep
   (`grep -rn "_ref_carries_path\|_head_carries_path" src/ tests/`) AND either the now-orphaned
   helper's removal (grep proving zero remaining callers) OR an explicit survival rationale per
   helper (grep showing the surviving call sites). A helper deleted without a grep-proof of zero
   callers — or a dead helper left in place — both fail DoD.
5. **FR-005 site routed.** `_substantive.py:~379` reads `routes_through_coordination(...)`, not
   `.kind is COORDINATION`; `CommitTargetKind` type/construction is NOT deleted (Mission B).
5a. **FR-005 repo-wide completeness proven (integrating, last-WP).** Review notes contain the
   pasted repo-wide grep/AST sweep showing the ONLY surviving
   `target.kind is CommitTargetKind.COORDINATION` *decision* comparison is the one INSIDE
   `routes_through_coordination` — proving all nine FR-005 sites (WP01/WP05/WP06/WP07) are routed and
   zero decision-reads leaked. Legitimate `CommitTarget(...)` constructions / enum members survive
   (Mission B) and are excluded from the assertion.
6. **Behavior preserved (NFR-003).** Full pinned set green incl. #1718 create-window and #1848
   coord-deleted P0 pins; no pin weakened or deleted.
7. **Clean gates (NFR-004).** `ruff` + `mypy` zero issues on `_substantive.py`; complexity ≤15; no
   new S1192; no suppression added. Complexity of `is_committed` is LOWER than before the reduction.
8. **Diagnostics contract intact.** The `setup-plan` caller's `spec_commit_surfaces_checked` payload
   is still populated with truthful per-surface lines.
9. **`owned_files` respected.** Only `src/specify_cli/missions/_substantive.py` is modified by this
   WP (plus the in-place `_substantive` test surface for T035's characterization, which is part of
   the same module's pinning — confirm it does not collide with another WP's `owned_files`).

---

## Risks

1. **Speculative collapse regresses live missions (TOP — plan.md Risk #1).** The 3-leg OR is
   load-bearing for the surface split. Collapsing it before WP04/WP05 structurally close the split,
   or before the live repro is green, re-opens #2062 as a false-negative ("spec.md not committed")
   that blocks real planning flows. **Mitigation:** the T037 gate is binding and witnessed; this WP
   runs last by construction (depends on WP04 + WP05).
2. **The reduction silently drops a transient carve-out (C-006).** The create-window (#1718) and
   coord-deleted (#1848) states are orthogonal to the four enum cells. If the single-surface check
   assumes the resolved ref always exists, it can regress these. **Mitigation:** the #1718/#1848 P0
   pins are in the DoD; T035 maps them explicitly; they stay probe-discriminated upstream, untouched.
3. **Diagnostics contract breakage.** Stripping diagnostics during reduction breaks the `setup-plan`
   blocked-payload `spec_commit_surfaces_checked` key and the operator-facing surface enumeration.
   **Mitigation:** DoD #8 + preserve the sink.
4. **Mistaking dead-leg removal for type eradication.** FR-005 routing does NOT delete
   `CommitTargetKind` (Mission B / C-007). Deleting the type here breaks ~143 references across 41
   files and is out of scope. **Mitigation:** T036 scope note; DoD #5.

---

## Reviewer Guidance (`reviewer-renata`)

- **Demand the witnessed evidence, not the code.** This WP's correctness is NOT verifiable from the
  diff alone — it is a load-bearing-workaround collapse. Reject if review notes lack: (a) the green
  differential-gate run output incl. the on-disk flattened-stale-coord row, and (b) the witnessed
  live flattened-mid-flight repro showing verdict-equivalence. "The code looks right" is an
  automatic rejection here (C-002 / live-evidence-over-static-fixed).
- **Check the envelope mapping (T035).** Every leg of the removed OR must map to a single-surface
  check that provably subsumes it, with a green test exercising the row. An unmapped row = a
  potential silent regression.
- **Verify the #1718 / #1848 pins are green and UNWEAKENED.** A reduction that goes green by
  loosening a P0 data-loss/false-negative pin is a regression masquerading as a fix — reject.
- **Confirm FR-005 routing did not delete `CommitTargetKind`.** The type and its construction must
  survive (vestigial); only the `.kind`-read decision is replaced by `routes_through_coordination`.
- **Demand the FR-005 repo-wide completeness sweep (DoD #5a).** Because WP07 is LAST, require the
  pasted grep/AST output proving the only surviving `.kind is COORDINATION` *decision* comparison is
  inside `routes_through_coordination`. A missing or stale sweep = unproven that all nine sites were
  routed; reject. Verify the sweep excludes `CommitTarget(...)` constructions (Mission B), not just
  greps a substring.
- **Demand the parametrized envelope test (DoD #3).** It must be a real parametrized test with one
  green case per (topology × transient) — the 4 enum cells plus #1718 and #1848 — not a prose table
  or a single happy-path test. Reject "add if unpinned" framing.
- **Confirm campsite stayed bounded.** Only touched lines cleaned; no excursion into the carved
  block-C de-godding. Orphaned helper deletions must carry a `grep`-proof of zero callers.
- Incorrect doc/path references in the WP output are blocking, not warnings (project review policy).

## Activity Log

- 2026-06-22T17:10:41Z – claude:opus:randy-reducer:implementer – shell_pid=574851 – Assigned agent via action command
- 2026-06-22T17:24:58Z – claude:opus:randy-reducer:implementer – shell_pid=574851 – GATE-BLOCKED (FR-011 collapse, T037/T038): witnessed live repro shows the single-surface check DIVERGES from the 3-leg OR for the #1718 create-window. resolve_placement_only returns COORDINATION(coord_ref) for a declared-but-unmaterialized coord (materialization deferred to commit boundary, #1718) while spec.md is committed on PRIMARY HEAD — a single-surface coord-ref check returns False where the OR returns True via the still-load-bearing HEAD leg. The surface is NOT yet structurally single for the create-window transient; collapsing regresses live #1718 (false-negative 'spec.md not committed' blocking first-write planning — plan.md Risk #1 / C-006). Per the binding gate (do-not-collapse-on-divergence), T037 NOT performed. Delivered the safe, in-ownership parts: T036 FR-005 routing (routes_through_coordination) + T035 protected-envelope characterization test (incl. the create-window guard row). WP04 differential gate GREEN (21 passed incl flattened-stale-coord + pure stored-topology). Residual placement-vs-artifact reconciliation for the create-window is a resolver concern (outside _substantive.py ownership) and must close before FR-011 collapse is safe.
- 2026-06-22T17:25:13Z – claude:opus:randy-reducer:implementer – shell_pid=574851 – T035+T036 DONE; T037 (FR-011 collapse) GATE-BLOCKED — see below. GATE EVIDENCE: (a) WP04 differential gate GREEN: tests/missions/test_surface_resolution_equivalence.py = 21 passed (incl on-disk flattened-stale-coord rows + pure stored-topology cell; type(a) is type(b)+error_code assertions intact). (b) WITNESSED live verdict-equivalence repro (resolve_placement_only seam, real git): 6/8 envelope rows preserve verdict under a single-surface check, but the #1718 CREATE-WINDOW DIVERGES — resolved placement is COORDINATION(coord_ref) while spec.md is on PRIMARY HEAD, so single-surface coord-check returns False vs OR's True (HEAD leg still load-bearing). => surface NOT yet structurally single; collapse would regress live #1718 (TOP risk). T037 correctly NOT performed; 3-leg OR preserved. DELIVERED safe in-ownership parts: T036 routes _substantive.py:379 through routes_through_coordination (FR-005, byte-identical, AttributeError fallback kept); T035 parametrized protected-envelope characterization test in test_is_committed_coord_aware.py (4 topology cells + #1718 + #1848 via live seam) — guards the envelope so a future collapse regressing any row goes red. Orphan-helper grep: BOTH _ref_carries_path AND _head_carries_path retain live callers (OR preserved) — neither orphaned, none removed. FR-005 sweep: my owned site routed; tasks.py:359 = WP06 (concurrent lane-g, disjoint); resolution.py:936 = construction-time ref selection (prior-WP surface). Tests: pinned set 63 passed (incl #1718/#1848 P0); runtime+planning-entry 19 passed; ruff+mypy clean (exit 0) on _substantive.py + test. RECOMMEND: reviewer/operator adjudicate — FR-011 needs the create-window placement-vs-artifact reconciliation (resolver, outside _substantive.py) before the collapse is safe.
- 2026-06-22T17:44:43Z – user – shell_pid=574851 – Moved to planned
- 2026-06-22T17:44:57Z – claude:opus:randy-reducer:implementer – shell_pid=616762 – Started implementation via action command
- 2026-06-22T18:06:09Z – claude:opus:randy-reducer:implementer – shell_pid=616762 – FR-011 collapse RE-IMPLEMENTED (cycle 2): is_committed reduced from 3-leg OR to single read-surface HEAD check on file_path's own git context. Cycle-1 block was correct for the WRITE placement; the collapse lands on the READ surface (the sole caller setup-plan feeds the read-resolved spec_file). 6-cell PARITY (single-via-read == retired-OR), all match: SINGLE_BRANCH-committed/uncommitted, LANES, COORD, LANES_WITH_COORD, create-window-1718. coord-deleted-1848 NEVER REACHED (read path raises CoordinationBranchDeleted before is_committed; caller Exit(1)). LIVE create-window repro witnessed read->PRIMARY HEAD->True. Adjudicated FR-005/#7 primary-only-inversion: UNREACHABLE at caller (read-resolved spec_file absent on disk -> SPEC_FILE_MISSING/StatusReadPathNotFound before is_committed); FR-011 removes that workaround 'once FR-001 holds'. Orphan grep: _ref_carries_path REMOVED; _head_carries_path + _git_commit_check_context survive. Re-keyed architectural ratchet onto post-collapse contract + 4 P0 pins + 2 FR-005 tests onto read-resolved surface. FR-005 sweep: only surviving .kind is COORDINATION decision-read is routes_through_coordination. 31 diff-scoped tests green; ruff+mypy clean (3 pre-existing mypy + 7 arch + 1 e2e all PRE-EXISTING at base 98c4bdffc). Net -94 LOC. Moved with --force from PRIMARY (lane behind feat by 105 commits; owned file _substantive.py identical at base, conflict-free, NOT rebased per flat-mission protocol).
- 2026-06-22T18:08:31Z – claude:opus:reviewer-renata:reviewer – shell_pid=645645 – Started review via action command
- 2026-06-22T18:14:24Z – user – shell_pid=645645 – FR-011 is_committed collapse: genuine single read-surface unification (3-leg OR + #7 workaround DELETED, net -64 LOC, _ref_carries_path removed). NOT parity-chasing (rescue scenario now correctly False). #1718 create-window (read->primary->True) + #1848 coord-deleted (read-raises-before-is_committed) witnessed live + source-re-verified. ruff/mypy clean, complexity ~3, 12/12+8/8+9/9 green.
