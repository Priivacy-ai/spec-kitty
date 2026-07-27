---
work_package_id: WP03
title: '`mission.py` planning-entry adoption'
dependencies:
- WP01
requirement_refs:
- FR-004
- FR-005
- FR-006
tracker_refs: []
planning_base_branch: feat/read-path-error-fidelity
merge_target_branch: feat/read-path-error-fidelity
branch_strategy: Planning artifacts for this mission were generated on feat/read-path-error-fidelity. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/read-path-error-fidelity unless the human explicitly redirects the landing branch.
subtasks:
- T013
- T014
- T015
- T016
- T017
- T018
- T019
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "2566958"
history:
- 2026-06-16 created (/spec-kitty.tasks)
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/agent/mission.py
create_intent:
- tests/specify_cli/cli/commands/agent/test_mission_planning_entry.py
execution_mode: code_change
owned_files:
- src/specify_cli/cli/commands/agent/mission.py
- src/specify_cli/missions/_substantive.py
- tests/specify_cli/cli/commands/agent/test_mission_planning_entry.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before any code, load the implementer profile so your identity, governance scope, and
boundaries are active for this session:

```
/ad-hoc-profile-load python-pedro
```

Then read, in this order, so the behavior you implement matches the canonical intent:

- `kitty-specs/read-path-error-fidelity-adoption-01KV8NPC/spec.md` — FR-004, FR-005, FR-006;
  US-3, US-4; SC-003, SC-004; the #2007 issue matrix (bugs #4, #7).
- `kitty-specs/read-path-error-fidelity-adoption-01KV8NPC/plan.md` — IC-03 (purpose, affected
  surfaces, risks), decisions **D-5** and **D-6**, and the sequencing note (WP03 depends on WP01).
- `kitty-specs/read-path-error-fidelity-adoption-01KV8NPC/contracts/behavioral-contracts.md` —
  **C-IC04** (planning-entry adoption) is your acceptance contract.
- `research/live-repro.md` — repros **#4**, **#7**, **#7 secondary**, and the **#11** caveat.
- `research/call-site-inventory.md` — call-sites **C8, C9, C10, C11, C15** and the §5 leg analysis
  and §6 line-number drift table (treat §6 as authoritative over any earlier line cite).

## Objective

Finish the adoption of the canonical read-path authority at the **planning-entry** surface of
`agent/mission.py` (and its committed-check collaborator `missions/_substantive.py`), so that:

1. **FR-004** — `setup-plan` auto-selects the sole mission when exactly one is resolvable, instead
   of hard-requiring `--mission`; `>1` still returns the structured `MISSION_AMBIGUOUS_SELECTOR`
   error with no silent fallback.
2. **FR-005** — `is_committed` consults a **primary-target-branch** leg (ORed with the existing
   coord/HEAD legs) so `spec_committed` is true when the spec is committed on the primary target
   branch, and emits diagnostics listing every ref/surface checked.
3. **FR-006 (D-5, narrowed)** — `_commit_to_branch` reports the **real commit hash** on success and
   distinguishes a *genuine-unchanged* no-op from a *no-op-against-the-wrong-surface*, the latter
   surfacing a typed diagnostic instead of a silent `commit_created: None`.
4. **#11** — `finalize-tasks` anchors its reads on the **primary root** so it does not fail-closed
   on a materialized-empty coord worktree before the primary read.

WP03 is the **SOLE owner** of `agent/mission.py` and `missions/_substantive.py` (NFR-005 bounded
conflict surface — call-site-inventory §9 IC-C). No other WP edits these files.

## Context

**C-001: adopt, do not build.** The typed authority `resolve_action_context → ExecutionContext /
ActionContextError` already exists and is correct. Every change here is a consumer-side adoption or
a missing git leg — **no new resolver, root authority, or error type.** WP01 (single context
factory + build invariant) is your dependency; consume the trustworthy context it produces, never
re-derive `target_branch`/identity independently (D-6 write-projection boundary).

**Function-over-form + verification-by-deletion.** Tests assert observable behavior (the JSON
contract, the resolved surface, the diagnostic), NOT internal structure. The proof of FR-004 is the
absence of the `--mission required` raise on the exact-one path; the proof of FR-005 is the
committed spec reporting `true`. Where a shadow path is removed, the behavioral suite stays green.

**TDD-first (C-002).** All three behavioral fixes (#4, #7, #7-secondary) reproduce on HEAD; write
the failing test first, watch it fail for the right reason (the real symptom from `live-repro.md`),
then make it pass. The #11 read-anchor fix gets a focused test too.

**Topology-true fixtures (NFR-002 — binding).** Use production-shaped data only:
- Full **26-char ULID** `mission_id` (e.g. `01KV8NPCDEBBIECOMMIT7B0000` shape — never a short slug).
- A **real coordination worktree** (`.worktrees/<slug>-<mid8>-coord`) with the mid8-suffixed mission
  dir, for the #7 and #11 cases.
- The **#7 false-negative is surface-specific**: it requires the coord worktree to **carry the
  mission dir** while the spec is committed **only on the primary target branch** (absent on the
  coord branch). A fabricated single-repo fixture masks the bug (the exact NFR-002 trap). Build the
  coord-worktree-with-mission-dir topology, with the spec present on `main` and absent on coord.

**Quality gates (NFR-004).** New/changed code passes `ruff` and `mypy` with zero issues, complexity
≤ 15, **no suppressions** (`agent/mission.py` is a 3942-LOC god-module — keep edits surgical and
extract small private helpers rather than inflating an existing function past the ceiling). No
`# noqa`/`# type: ignore` additions.

## Subtasks

### T013 — TDD: setup-plan exact-one auto-select; >1 structured error
- Write `tests/specify_cli/cli/commands/agent/test_mission_planning_entry.py` (NEW).
- Case A: a repo with **exactly one** substantive mission (topology-true, full ULID, spec committed
  on `main`). Invoke `setup-plan --json` with **no `--mission`**; assert it auto-selects the sole
  mission (no `PLAN_CONTEXT_UNRESOLVED` / `--mission required`). Mirror the live repro in
  `research/live-repro.md#4` (`/tmp/debbie-single`).
- Case B: a repo with **two** missions; assert `setup-plan --json` (no `--mission`) still returns the
  structured `MISSION_AMBIGUOUS_SELECTOR` / detection error — **no silent fallback**.
- **Validation:** both tests FAIL first (Case A returns the disambiguate error on HEAD per repro #4).

### T014 — Add exact-one auto-select in `setup_plan` (NOT the shared helper)
> ⚠️ **Line drift — re-locate by symbol.** The line cites below drifted post-WP01 / #2004. Anchor on
> the symbols: `setup_plan` def is ~`:1905` (the earlier `:2054+` cites are interior to it),
> `_build_setup_plan_detection_error` def is ~`:1300` (NOT `:1332`). Re-locate by symbol, not by line.
- In `setup_plan` (`agent/mission.py`, def ~`:1905`), **before** the call into the shared
  `_find_feature_directory`, enumerate substantive missions and, if **exactly one** is resolvable,
  pass it as `explicit_feature`; otherwise let the existing structured detection-error path fire.
- **DO NOT** add auto-select inside the shared `_find_feature_directory` (raise inside def `~:1214`) —
  it is also used by `finalize-tasks` and others; changing it alters behavior for every caller
  (call-site-inventory §3). The `>1` raise of the structured ambiguity error stays intact.
- If `_build_setup_plan_detection_error` (`agent/mission.py` def ~`:1300`) unconditionally emits the
  disambiguate message even when `n == 1`, gate that branch so the `n == 1` path is the auto-select,
  not the disambiguate message.
- **Validation:** T013 Case A passes; Case B still errors structurally; `ruff`/`mypy` clean.

### T015 — TDD: is_committed true on primary-target-branch commit
- Add a test that builds the **coord-worktree-with-mission-dir** topology (T-context above): coord
  branch + coord worktree materialized carrying `kitty-specs/<slug>-<mid8>/` but **no `spec.md`**;
  the substantive `spec.md` committed **only on `main`** (the primary target branch). Mirror
  `research/live-repro.md#7` (`/tmp/debbie-committed7b`).
- **Non-vacuity guard (BLOCKER — make the NFR-002 trap detectable in DoD, not just prose):** the
  fixture MUST be topology-true so that **BOTH** existing legs (coord-ref + HEAD) miss — i.e. the spec
  is committed **only on the primary target branch** AND a coord worktree exists carrying the mission
  dir but **no** `spec.md`. **FORBIDDEN:** a single-repo / mission-dir-absent-on-coord fixture, or a
  spec committed on both branches — those green vacuously (the resolver falls back to the primary dir
  and `is_committed` already returns `True` on HEAD; the NFR-002 trap).
- **Captured-red:** assert that on HEAD (pre-fix tree)
  `is_committed(resolved_coord_spec, repo_root, placement=COORDINATION) == False` for **this** fixture
  (capture the red and paste it into the Activity Log) → **True** after the fix. If this pre-fix
  `False` does not hold, the fixture is wrong (vacuous) and the implementer must build the real
  topology. Also assert the resolved spec path is **under `.worktrees/…-coord/`**, proving the coord
  surface is the one being checked (not the primary dir).
- Assert the diagnostic lists every ref/surface checked.
- **Validation:** test FAILS first (both existing legs miss on HEAD per repro #7).

### T016 — Add primary-target-branch leg to is_committed + diagnostics
- In `is_committed` (`missions/_substantive.py`, def `:286`, existing legs `:330-339` coord-ref and
  `:341-355` HEAD), add a **primary-target-branch leg**: `git -C <primary_repo_root> cat-file -e
  {target_branch}:{primary_tree_path}` — **ORed** with the existing legs. The check MUST run against
  the **primary** repo root with the **primary** tree-path (not the worktree-relative one).
- Caller C10 in `setup-plan` (`agent/mission.py:2112-2116`) must supply the target-branch surface; it
  already has `target_branch` from `_show_branch_context` — thread it through.
- Emit diagnostics enumerating each ref/surface checked (the issue's own fix direction, FR-005).
- **Validation:** T015 passes; the existing single-repo `spec_committed:true` case (repro #7 caveat,
  `/tmp/debbie-committed`) still passes — add a guard test if not already covered.

### T017 — TDD: _commit_to_branch hash report + no-op-vs-wrong-surface
- Add tests for two cases against the resolved placement:
  - **Success** — assert the result reports a **real commit hash** (not `None`), threaded into the
    caller's `commit_created`.
  - **No-op against the wrong surface** — artifact NOT present at the resolved placement: assert a
    **typed diagnostic** surfaces, not a silent `commit_created: None`.
- Keep a third case for **genuine-unchanged** (artifact present & already committed at placement):
  assert it stays a benign no-op.
- **Validation:** success/wrong-surface cases FAIL first (the function returns `None` on HEAD,
  `agent/mission.py:1120`; no-op paths `:1165,:1180-1184,:1192-1194` swallow silently per repro #7
  secondary).

### T018 — Fix _commit_to_branch (hash; distinguish no-op classes)
- `_commit_to_branch` (def `agent/mission.py:1120`, handlers `:1180-1197`): on **success** report the
  real commit hash (give it a typed result or thread the hash into the caller's `commit_created` —
  the plan caller assigns `commit_created` ~`:3759`/`:3819`, **NOT** `:2195`; re-locate by symbol). The
  **hard**-failure swallow is already fixed on HEAD (`_warn_commit_failed`
  + `raise` at `:1186-1188`, `:1196-1198`) — **do not touch that**; D-5 narrows the work to the
  hash + no-op classification.
- Distinguish **genuine-unchanged** (artifact present & committed at the resolved placement → may stay
  benign via `_print_artifact_unchanged`) from **no-op-against-wrong-surface** (artifact NOT present at
  the resolved placement → surface a typed diagnostic in the JSON contract).
- **Validation:** T017 passes; `ruff`/`mypy` clean, complexity ≤ 15.

### T019 — finalize-tasks: anchor read on primary root (#11 fail-closed)
- `finalize-tasks` reads via the coord-aware `_find_feature_directory` (in `finalize_tasks`, def
  ~`:2656` — NOT `:2754`; re-locate by symbol — `require_exists=True`), which can fail-closed on a
  **materialized-empty coord worktree** before the **primary** read; writes are already correctly
  re-anchored via `primary_feature_dir_for_mission` (`:1865-1867`).
- Anchor the **read** on the primary root so a materialized-but-empty coord does not pre-empt the
  primary surface (#11/#1718/#1692 class). Do **not** fail-closed before the primary read.
- Add a focused test: coord worktree materialized but empty, mission dir present on primary →
  `finalize-tasks` reads the primary surface and succeeds (does not raise `STATUS_READ_PATH_NOT_FOUND`
  / fail-closed).
- **Validation:** new test passes; existing finalize-tasks tests stay green.

## Branch Strategy

Planning artifacts were generated on `feat/read-path-error-fidelity`. During
`/spec-kitty.implement` this WP may branch from a dependency-specific base (it depends on WP01), but
completed changes merge back into `feat/read-path-error-fidelity` unless the human explicitly
redirects the landing branch. Do not push to `origin/main`; the mission lands via PR.

## Definition of Done

- [ ] `/ad-hoc-profile-load python-pedro` invoked; spec/plan/contracts/research read.
- [ ] **T013–T014 (FR-004):** exact-one `setup-plan` auto-select implemented in `setup_plan` (NOT the
      shared helper); `>1` still returns the structured `MISSION_AMBIGUOUS_SELECTOR` (no silent fallback).
- [ ] **T015–T016 (FR-005):** `is_committed` has a primary-target-branch leg ORed with existing legs,
      run against the primary root + primary tree-path; diagnostics list every ref/surface checked; the
      coord-worktree-with-mission-dir topology test passes.
- [ ] **T017–T018 (FR-006/D-5):** `_commit_to_branch` reports the real commit hash on success and
      surfaces a typed diagnostic for a no-op-against-wrong-surface; genuine-unchanged stays benign; the
      already-fixed hard-failure raise is untouched.
- [ ] **T019 (#11):** `finalize-tasks` anchors reads on the primary root; no fail-closed on a
      materialized-empty coord before the primary read.
- [ ] All new tests use topology-true fixtures (full 26-char ULID, real coord worktree, mission dir on
      coord + spec on primary only for #7).
- [ ] Each behavioral fix landed **test-first** and the test **FAILED FIRST on HEAD with the captured
      red pasted into the Activity Log** (not a prose claim). For T015 specifically: the captured red
      shows `is_committed(...) == False` on the non-vacuous coord-worktree-with-mission-dir +
      spec-on-primary-only fixture (proving the fixture triggers the bug), flipping to `True` after the
      fix. A test that passes on HEAD, or one written after the fix, is a gaming defect.
- [ ] The shared `_find_feature_directory` was **not** modified for auto-select (verification-by-deletion
      of the bypass is consumer-side only).
- [ ] `ruff` and `mypy` clean on changed code; complexity ≤ 15; no `# noqa`/`# type: ignore` added.
- [ ] Full behavioral suite green (`PWHEADLESS=1 pytest tests/specify_cli/cli/commands/agent/ tests/specify_cli/missions/ -n0 -q`).

## Risks / reviewer guidance

- **`agent/mission.py` is the one true collision surface** (C8/C10/C11/C15). WP03 must be its sole
  editor; if a reviewer sees another WP touching it, that is an NFR-005 violation.
- **Do NOT add auto-select inside `_find_feature_directory`** — it is shared; changing it alters
  behavior for `finalize-tasks` and every other caller. The auto-select lives in `setup_plan` only.
- **#7 is surface-specific.** A reviewer must confirm the regression fixture builds the
  coord-worktree-with-mission-dir + spec-on-primary-only topology — a single-repo fixture passes
  vacuously and masks the bug (NFR-002 trap; see the repro #7 caveat).
- **FR-006 is narrowed by D-5** — the hard-failure swallow is already fixed on HEAD; do not "re-fix"
  it. The residual is the success-hash report + the no-op classification only.
- **Line numbers** are from HEAD `87697e5e4` per `research/call-site-inventory.md` §6 (treat §6 as
  authoritative); expect drift after WP01 lands and re-locate by symbol, not by line.
- Consume WP01's frozen context; never re-derive `target_branch`/`mission_id`/`mid8` here (D-6).

## Activity Log

- 2026-06-16 — Prompt generated via /spec-kitty.tasks (IC-03; FR-004/005/006 + #11; C8/C9/C10/C11/C15).
- 2026-06-16T21:03:42Z – claude:opus:python-pedro:implementer – shell_pid=2432976 – Assigned agent via action command
- 2026-06-16T21:24:08Z – claude:opus:python-pedro:implementer – shell_pid=2432976 – Implementation complete + committed (9f95846c5). T013-T019 marked done. move-task to for_review from the lane worktree was BLOCKED by stale lane status (worktree-local read = planned; canonical coord-branch board = in_progress) — orchestrator must run 'spec-kitty agent tasks move-task WP03 --to for_review' from the PRIMARY checkout. FR-004/005/006 + #11 all landed test-first; ruff/mypy clean on diff; relevant suites green.
- 2026-06-16T21:25:32Z – claude:opus:python-pedro:implementer – shell_pid=2432976 – Ready: 4 fixes + non-vacuous captured-red; 9/9 new tests, 109+290 suite green
- 2026-06-16T21:25:33Z – claude:opus:reviewer-renata:reviewer – shell_pid=2566958 – Started review via action command
- 2026-06-16T21:32:12Z – user – shell_pid=2566958 – Review PASSED (reviewer-renata). FR-004: exact-one auto-select lives in setup_plan via _sole_mission_slug_or_none; shared _find_feature_directory byte-identical to base; >1 still returns structured PLAN_CONTEXT_UNRESOLVED (no silent fallback). FR-005: primary-target-branch leg ORed with coord+HEAD legs in is_committed, run against primary root (get_main_repo_root) + primary tree-path; diagnostics enumerate every surface; target_branch sourced from _show_branch_context (not re-derived, D-6 ok). FR-006/D-5: _commit_to_branch returns typed CommitToBranchResult with real CommitResult.sha on success, no_op_wrong_surface typed diagnostic vs benign unchanged; already-fixed hard-failure raise untouched. #11: finalize-tasks resolves primary-anchored first, no fail-closed before primary read. NON-VACUITY BLOCKER CLEARED: verified by reverting prod code to base while keeping tests — T015 captured-red is genuine (test_is_committed_false_without_primary_leg passes on base proving BOTH existing legs miss for the coord-worktree-with-mission-dir + spec-on-primary-only topology; full 26-char ULID; resolved spec under .worktrees/-coord/), flips False->True after fix; 6/9 fail on base for the right symptoms (repro #4/#7/#7-sec/#11). Quality: ruff+C901(<=15)+mypy clean on all 3 files, zero added suppressions. Ownership: WP03 commit touches only the 3 owned files. Pre-existing test_wrapper_delegation x2 failures reproduce identically on clean base (worktree-env artifact, untouched surfaces) — not attributable to WP03.
