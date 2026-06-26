---
work_package_id: WP04
title: Shared teardown seam + persist-before-destroy + mission_type tidy
dependencies:
- WP01
- WP03
requirement_refs:
- FR-004
- FR-005
- FR-006
- FR-008
- FR-009
tracker_refs:
- '#2119'
- '#2133'
- '#2129'
- '#2123'
planning_base_branch: fix/3.2.3-coord-surface-regressions
merge_target_branch: fix/3.2.3-coord-surface-regressions
branch_strategy: Planning artifacts for this mission were generated on fix/3.2.3-coord-surface-regressions. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/3.2.3-coord-surface-regressions unless the human explicitly redirects the landing branch.
subtasks:
- T041
- T042
- T043
- T044
- T045
- T046
- T047
- T048
phase: Phase 1 - Teardown contract (one seam, persist-before-destroy) + adjacent tidy
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "2010647"
history:
- at: '2026-06-25T19:36:37Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks (planner-priti)
agent_profile: python-pedro
authoritative_surface: src/specify_cli/coordination/teardown.py
create_intent:
- src/specify_cli/coordination/teardown.py
- tests/coordination/test_teardown_seam_persist_before_destroy.py
- tests/coordination/test_teardown_single_seam_routing.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/coordination/teardown.py
- src/specify_cli/merge/executor.py
- src/specify_cli/cli/commands/merge.py
- src/specify_cli/cli/commands/mission_type.py
- tests/coordination/test_teardown_seam_persist_before_destroy.py
- tests/coordination/test_teardown_single_seam_routing.py
- tests/merge/test_executor_coverage.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP04 — Shared teardown seam + persist-before-destroy + tidy

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile in the frontmatter
**before parsing the rest of this prompt**, and behave according to its guidance.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If the profile cannot be loaded, run `spec-kitty agent profile list` and select the best
match for `task_type: implement` on `authoritative_surface:
src/specify_cli/coordination/teardown.py`.

---

## Objective

**Consolidate the 3 duplicated coordination-teardown call sites into ONE shared seam that
persists the retrospective BEFORE it destroys the coordination worktree** (persist → flatten →
destroy), with persist running **OUTSIDE the best-effort `except Exception` swallow**. The
duplication is exactly why the ordering bug exists in one path (merge: destroy-before-persist)
and is absent in another (discard: no-persist-at-all). One seam makes the invariant attachable
once and provable by destroy-step fault injection. This WP also folds the adjacent
`mission_type.py` tidy (FR-008 dead helpers, FR-009 stale comments) because it already owns the
whole file via the teardown call site.

> **Why FR-004+FR-005 are one WP, and why FR-008/009 ride along:** FR-005 (persist-before-destroy)
> IS the seam's purpose — splitting it from FR-004 would force two WPs to own the new
> `coordination/teardown.py` + the 3 call sites + the `test_executor_coverage.py` update. FR-008
> (dead helpers `mission_type.py:78/313`) and FR-009 (stale comments `:642/:607`) also live in
> `mission_type.py`, which this WP already owns via the teardown call site at `:910` — folding
> them keeps `mission_type.py` owned by exactly one WP (the `owned_files` no-overlap rule is
> per-file). The tidy edits are line-disjoint from the teardown region.

## The 3 teardown sites + ordering bugs (live-verified on `e36547461`, post-#2133)

| Site | Anchor | Swallow | Path |
|------|--------|---------|------|
| Merge | `src/specify_cli/merge/executor.py:795` (inside `_phase_cleanup_worktrees_and_branches@717`, called at `:936` from `_run_lane_based_merge_locked@862`) | `except Exception` @`:805` | merge cleanup |
| Abort | `src/specify_cli/cli/commands/merge.py:270` (the `--abort` helper; #2133 left this in `cli/`, did NOT move it to `merge/`) | `except Exception` @`:271` | merge `--abort` |
| Close/discard | `src/specify_cli/cli/commands/mission_type.py:910` (helper `_teardown_coordination_worktree@904`; reached from close call @`:644` and from `_discard_mission@662` at @`:676`, which is itself called at @`:623`) | `except Exception` @`:921` | close / `--discard` |

**Merge-path bug (live):** teardown runs at `executor.py:936` (inside `_run_lane_based_merge_locked`),
while `run_retrospective_postcondition(...)` fires at `merge.py:382` in the OUTER `merge()` only
**after** `_run_lane_based_merge` returns (`:361`) → destroy-before-persist.

**Discard-path bug (live, anchors re-verified on HEAD):** `_discard_mission@662` is invoked from the
close-command body at **`:623`**; INSIDE `_discard_mission`, `_teardown_coordination_worktree`
(destroy) runs at **`:676`** with **NO persist step**. After `_discard_mission` returns, the caller
runs `_verify_discard_complete@634` then `_flatten_discarded_mission@639` — i.e. the live discard
order is **destroy(`:676`) → verify(`:634`) → flatten(`:639`)**, with a *deliberate*
**verify-BEFORE-flatten** invariant (comment `:632-633`: "Verify BEFORE flattening so the
legacy-branch check can still read `coordination_branch` from `meta.json`"). The persist hook MUST
hoist AHEAD of the `_discard_mission` CALL at **`:623`** (not "ahead of `:676`" — `:676` is inside
the helper; persist must precede the whole destructive helper).

**⚠️ Ordering reconciliation (decide explicitly — DIR-001).** ADR Binding B states
**persist → flatten → destroy**. The live discard path is **destroy → verify → flatten** (verify
reads `coordination_branch` from `meta.json`, which flatten *clears* — hence verify must precede
flatten). These two orderings CONFLICT on flatten-vs-destroy. The seam MUST NOT silently break the
verify-before-flatten invariant. **Chosen reconciliation:** the seam owns only **persist** (hoisted
ahead of `_discard_mission@623`, OUTSIDE the best-effort swallow) and **destroy**; the discard
command KEEPS its existing **destroy → verify → flatten** sequence (verify-before-flatten preserved).
So the effective discard order becomes **persist(`:623`-ahead) → destroy(`:676`) → verify(`:634`) →
flatten(`:639`)**. ADR Binding B's "persist → flatten → destroy" describes the MERGE path (no verify
step); on the discard path, persist-before-destroy is the load-bearing invariant and flatten stays
AFTER verify. The seam does NOT move flatten ahead of destroy on the discard path (that would break
verify's `meta.json` read). T041 must encode this decision in the seam's design + docstring; the ADR
Binding B alignment is confirmed in T041 (see below).

**Seam home:** the 3 sites span TWO packages (`merge/executor.py` + `cli/commands/merge.py`) plus
`mission_type.py`, so the shared seam lives in **`src/specify_cli/coordination/teardown.py`** (NEW,
near `CoordinationWorkspace` at `coordination/workspace.py:147`), NOT in `merge/` — `merge/` owns
neither the abort nor the close/discard call site. (`coordination/teardown.py` does NOT exist yet
— verified — so creating it collides with nothing; WP05 owns `coordination/surface_resolver.py`,
a different file.)

## Context & Constraints

Ground truth — read before editing:
- [spec.md](../spec.md) **FR-004** (one seam; anti-rename test) + **FR-005** (persist-before-destroy
  OUTSIDE the swallow; destroy-step fault injection; UPDATE `test_executor_coverage.py:616`) +
  **FR-008** + **FR-009** + **NFR-003** (flattened byte-identical) + **NFR-004** (`maxCC ≤ 15`).
- [data-model.md](../data-model.md) "Entity — `_teardown_coordination_topology` seam".
- [contracts/terminal-artifact-teardown-contract.md](../contracts/terminal-artifact-teardown-contract.md) **C2** + **C5**.
- [research.md](../research.md) **Decision 3** (one seam + persist-before-destroy).

**Negative scope:**
- Do NOT put the seam in `merge/` (`merge/` owns neither the abort nor close/discard site).
- Do NOT absorb a persist failure in the destroy best-effort swallow — persist runs OUTSIDE it.
- Do NOT delete `test_phase_cleanup_coord_teardown_failure_is_non_fatal` — **UPDATE** it (DIR-041).
- Do NOT touch the FR-006 lane exact-set (`_remove_lane_worktrees@970`/`_verify_discard_complete@777`)
  — DONE-by-#2129, regression-reference only.
- Do NOT split `_run_lane_based_merge_locked` (separate debt; C901 passes).

## Branch Strategy

- **Strategy**: depends on **WP01** (read-leg handle-safety) AND **WP03** (the retrospective WRITE
  authority + write-leg handle-canonicalization). **Why WP03 is a hard dependency:** the seam's
  persist step routes the retrospective through `writer.py:48` / `retrospective_terminus.py:68`
  (the WP03 sites). WITHOUT WP03, those sites still resolve via the coord-aware
  `resolve_feature_dir_for_slug`, so the seam's "persist" would write into the coord worktree it is
  about to destroy — defeating persist-before-destroy. WP04 persist is only durable once WP03 has
  re-pointed the write sites onto the primary authority.
- **Lane note:** adding the WP04→WP03 edge causes `finalize-tasks` to recompute lanes on the next
  re-finalize (WP04 now sequences after WP03's lane). Parallel with WP02/WP05 (disjoint files).
- **Planning base branch**: `fix/3.2.3-coord-surface-regressions`
- **Merge target branch**: `fix/3.2.3-coord-surface-regressions`

> WP04 OWNS `coordination/teardown.py` (new), `merge/executor.py`, `cli/commands/merge.py`,
> `cli/commands/mission_type.py` (whole file — includes the FR-008/009 tidy), and
> `tests/merge/test_executor_coverage.py` (the UPDATE). No other WP touches these.

## Subtasks & Detailed Guidance

### Subtask T041 — Extract the `_teardown_coordination_topology` seam

- **Purpose**: One function `persist → flatten → destroy` in `coordination/teardown.py`.
- **Files**: new `src/specify_cli/coordination/teardown.py`.
- **Steps**:
  1. Create `coordination/teardown.py` with a single seam, e.g.
     `teardown_coordination_topology(repo_root, mission_slug, mid8, *, feature_dir, persist=True)`.
  2. Ordered steps: (1) **persist** — write any pending retrospective to its durable PRIMARY home
     (route via the WP03 authority / `record_retrospective` so the file lands at
     `kitty-specs/<slug>/retrospective.yaml`); (2) **flatten** — clear the dangling
     `coordination_branch` from `meta.json` (reuse `_flatten_discarded_mission`'s logic or its
     primitive — do NOT duplicate it); (3) **destroy** — `CoordinationWorkspace.teardown(...)`.
  3. Persist MUST run OUTSIDE any `except Exception` swallow; destroy stays best-effort (its
     failure remains non-fatal per the UPDATED test in T044).
  4. Keep the seam at `maxCC ≤ 15` — extract small helpers if needed (NFR-004).
  5. **Acyclic-import discipline (alphonso):** the seam's retrospective-persist import (pulling in
     `specify_cli.retrospective.*` / the WP03 write authority) MUST be **function-local / lazy**,
     mirroring the established convention at `src/specify_cli/retrospective/gate.py:201` (which
     lazily imports `coordination.surface_resolver` to avoid dragging `coordination/` in at module
     import). A module-top import here would create a `coordination/` → `retrospective/` import
     cycle. Do **NOT** add `teardown` (or the new seam symbol) to `coordination/__init__.__all__` —
     keep the seam reachable only via its module path, so `coordination/__init__` stays free of the
     retrospective dependency.
  6. **ADR Binding B confirmation (DIR-003):** the seam's docstring MUST record the chosen ordering
     reconciliation (merge path: persist→destroy; discard path: persist→destroy→verify→flatten,
     preserving verify-before-flatten) and confirm it matches ADR Binding B as authored. If the
     shipped seam diverges from Binding B's wording, update the ADR's Binding B "Seam-anchor"
     paragraph to match the shipped seam (the ADR is WP01-owned; flag the needed wording in the
     activity log / report rather than editing it from WP04).
- **Notes**: the seam is the single place the invariant lives; the 3 call sites collapse to a
  call into it. The lazy import + `__all__` exclusion keep `coordination/` acyclic.

### Subtask T042 — Re-point the 3 call sites onto the seam

- **Purpose**: Collapse the duplication.
- **Files**: `merge/executor.py:795`, `cli/commands/merge.py:270`, `mission_type.py:910`.
- **Steps**:
  1. `executor.py:795` — replace the `CoordinationWorkspace.teardown(...)` (+ its `:805` swallow)
     with a call to the seam; the merge cleanup phase now persists-before-destroys.
  2. `merge.py:270` — replace the `--abort` `CoordinationWorkspace.teardown(...)` (+ `:271`
     swallow) with the seam.
  3. `mission_type.py:910` — replace the call inside `_teardown_coordination_worktree@904`
     (+ `:921` swallow) with the seam; ensure BOTH the close path (call `:644`) and discard path
     (call `:676`, inside `_discard_mission`) flow through it. **The discard path's persist step is
     hoisted AHEAD of the `_discard_mission` CALL at `:623`** (NOT inside the helper at `:676`) —
     persist must precede the whole destructive helper, OUTSIDE the best-effort swallow. **Preserve
     the existing destroy → verify(`:634`) → flatten(`:639`) sequence** (verify-before-flatten:
     `_verify_discard_complete` reads `coordination_branch` from `meta.json` before
     `_flatten_discarded_mission` clears it). Do NOT move flatten ahead of destroy on the discard
     path — that breaks verify's `meta.json` read (see Ordering reconciliation above).
  4. Preserve idempotency (no-op on legacy / already-torn-down missions).
- **Notes**: after this, the only `CoordinationWorkspace.teardown(` PRODUCTION call is INSIDE the
  seam; legitimate test-side `CoordinationWorkspace.teardown(` primitive calls remain (see T043).

### Subtask T043 — Anti-rename structural test (FR-004) — PRODUCTION scope only

- **Purpose**: Reject a rename that leaves the production duplications.
- **Files**: new `tests/coordination/test_teardown_single_seam_routing.py`.
- **Scope (load-bearing — the assertion is otherwise un-runnable):** the guard greps **production
  code only** — `src/specify_cli/**` + `src/runtime/**` — and EXCLUDES `tests/**` and the seam file
  `src/specify_cli/coordination/teardown.py` itself. There are **legitimate `CoordinationWorkspace
  .teardown(` calls in tests** that exercise the primitive directly and MUST survive: 5 in
  `tests/integration/test_mission_close.py` (`:129`, `:155`, `:159`, `:206`, `:333`) and 5 in
  `tests/specify_cli/coordination/test_workspace.py` (`:159`, `:165`, `:181`, `:196`, `:218`) —
  live-verified on HEAD. These are primitive-level unit tests, NOT production teardown sites; a
  tree-wide "zero outside the seam" assertion would falsely flag them.
- **Steps**:
  1. GREP/AST `src/specify_cli/**` + `src/runtime/**` for `CoordinationWorkspace.teardown(` call
     sites (exclude the seam file + `tests/`).
  2. Assert **zero PRODUCTION** call sites exist outside `coordination/teardown.py` (the seam).
  3. Enumerate over the live three production sites so re-adding a direct call at any of the former
     production sites (`merge/executor.py`, `cli/commands/merge.py`, `cli/commands/mission_type.py`)
     FAILS the test.
  4. **Do NOT use a per-call exclusion allow-list** (no "skip these specific lines" list) — the scope
     is the directory boundary (production dirs minus the seam file), not an enumerated set of
     exempted call sites. A per-call allow-list rots and re-admits a leaked production call.
- **Notes**: count-agnostic enumeration; no hardcoded site list as the *assertion* (assert "only
  the seam in production", derived dynamically over the production dirs). The test-side primitive
  calls are legitimate and intentionally out of scope.

### Subtask T044 — Persist OUTSIDE the swallow + UPDATE the #2133 test (FR-005, DIR-041)

- **Purpose**: Attach the invariant and re-pin the no-persist test to the new contract.
- **Files**: `tests/merge/test_executor_coverage.py:616`
  (`test_phase_cleanup_coord_teardown_failure_is_non_fatal`).
- **Steps**:
  1. **UPDATE** (never delete — DIR-041) `test_phase_cleanup_coord_teardown_failure_is_non_fatal`:
     the old test asserts teardown-failure is swallowed (hard-coding the absence of
     persist-before-destroy). Re-pin it: a **destroy**-step failure stays non-fatal (the merge
     still completes), BUT the retrospective was already persisted to its durable home BEFORE the
     destroy — assert the file exists at `kitty-specs/<slug>/retrospective.yaml` even though
     destroy raised.
  2. Confirm a **persist**-step failure is NOT swallowed (it surfaces) — persist sits outside the
     best-effort handler.
- **Notes**: this is the standing "re-pin a stale assertion, never delete-to-green" framework —
  the test is valid+current, only its asserted contract changed.

### Subtask T045 — Destroy-step fault-injection proof (FR-005, both paths)

- **Purpose**: Prove persist-before-destroy on merge AND close/`--discard`.
- **Files**: new `tests/coordination/test_teardown_seam_persist_before_destroy.py`.
- **Steps (red-first)**:
  1. Genuinely-divergent coord-topology fixture (coord worktree lacks `meta.json`/`lanes.json`),
     real ULID/mid8, with a pending retrospective.
  2. **Inject a fault at the DESTROY step** (force `CoordinationWorkspace.teardown` to raise) on
     (a) the merge path and (b) the `mission_type.py` close/`--discard` path.
  3. Assert `kitty-specs/<slug>/retrospective.yaml` **already exists** despite the destroy failure
     (persist ran first, outside the swallow). RED on pre-WP04 code (the retro is in the coord
     worktree / absent), GREEN after.
  4. Record red-run evidence.
- **Notes**: fault at the DESTROY step (not persist) — NFR-002.

### Subtask T046 — FR-008: remove the 2 dead helpers (prove zero callers FIRST)

- **Purpose**: Remove `_list_active_worktrees@78` + `_print_active_worktrees@313` (one carries a
  latent forbidden-term landmine in its dead string).
- **Files**: `cli/commands/mission_type.py:78`, `:313`.
- **Steps**:
  1. **Prove zero live callers** BEFORE deleting (grep the tree for both symbols; a test/grep
     evidences zero callers — delete-and-trust-green is REJECTED).
  2. Remove both functions and any now-unused imports they alone needed.
  3. Run the terminology guard (`pytest tests/architectural/test_no_legacy_terminology.py`) — the
     dead string's forbidden-term landmine is now gone.
- **Notes**: this is a `mission_type.py` user-facing/prose touch — run the terminology guard.

### Subtask T047 — FR-009: fix the 2 stale comments

- **Purpose**: Remove two landmine comments.
- **Files**: `cli/commands/mission_type.py:642`, `:607`.
- **Steps**:
  1. `:642` — "Same path as merge.py:1568" is stale (`cli/commands/merge.py` is now 575 lines
     post-#2133; `:1568` does not exist). Re-point it at the real teardown region: the
     `merge/executor.py` cleanup phase (`_phase_cleanup_worktrees_and_branches`) + the
     `cli/commands/merge.py:270` `--abort` helper — OR, after T042, simply "routes through the
     shared `coordination/teardown.py` seam".
  2. `:607` — the stale `f"{raw}-"` `.worktrees/` prefix-match prose (a landmine left by #2129's
     de-prefixing; it describes removal code that no longer exists). Correct it so no maintainer
     believes a prefix-match still lives (the exact-set lives in `_expected_lane_worktree_dir_names`).
- **Notes**: prose-only edits; run the terminology guard with T046.

### Subtask T048 — FR-006 regression-reference lock (#2129 sibling-survival — NO code change)

- **Purpose**: Lock the already-shipped (#2129) sibling-survival invariant as a **regression
  test**. FR-006 is **STRUCK** (DONE-by-merge #2129) — this subtask adds NO product code; it only
  locks the invariant the base already satisfies (the spec: "a regression test MAY lock the
  invariant but is not a deliverable"). It is mapped here because the lane exact-set lives in
  `mission_type.py` (which this WP owns).
- **Files**: `tests/coordination/test_teardown_single_seam_routing.py` (or a sibling test file in
  the same dir — reuse, do NOT create a new owned file).
- **Steps**:
  1. Build two missions whose slugs share a prefix (`<slug>` and `<slug>-sibling`), each with its
     own mid8-anchored lane worktrees from `lanes.json`; the sibling carries uncommitted work.
  2. Drive the target mission's `--discard` (the real entry point).
  3. Assert: the target's lane worktrees are gone; the **sibling's worktrees + uncommitted work
     SURVIVE**; exit 0; no spurious abort on the sibling.
  4. This exercises `_remove_lane_worktrees@970` (exact-set via `_expected_lane_worktree_dir_names@950`)
     + `_verify_discard_complete@777` (exact-name + sibling-safe) — already correct on the base.
- **Notes**: NO change to `_remove_lane_worktrees`/`_verify_discard_complete` (DONE-by-#2129). If
  this invariant is already covered by an existing test on the base, this subtask reduces to
  confirming that coverage and recording it in the activity log (do NOT duplicate a passing guard).

> **Upstream gap (logged):** `finalize-tasks --validate-only` enumerates EVERY `FR-NNN` token in
> spec.md via a greedy regex (`requirement_mapping.py:16` `_REF_FIND_PATTERN`) and demands a WP
> mapping for each — it has **no notion of a STRUCK / done-by-merge FR** (`~~FR-006~~` strikethrough
> is ignored). FR-006 is mapped here to its regression-reference home (honest: a guard test on
> already-shipped #2129 behavior, not a re-implementation). The clean fix is an upstream
> struck-FR exclusion in the validator (e.g. honor strikethrough or a `Status: STRUCK` table cell).
> See report — this should be filed as a gap, not worked around silently in future missions.

## Test Strategy

- `PWHEADLESS=1 pytest tests/coordination/test_teardown_seam_persist_before_destroy.py tests/coordination/test_teardown_single_seam_routing.py tests/merge/test_executor_coverage.py -q` — RED first on the fault-injection + UPDATED test, GREEN after.
- Real-port/daemon-free; if any teardown test touches real worktrees, run it `-n0` (serial) per the parallel-test rules.
- Run `tests/architectural/test_no_legacy_terminology.py` (FR-008 dead-string landmine).
- `ruff check` + `mypy --strict` on all touched modules — zero issues, no suppressions; `maxCC ≤ 15` on the
  new seam and every touched function.

## Definition of Done

- [ ] One shared seam in `coordination/teardown.py`; persist OUTSIDE the best-effort
  `except Exception` swallow. Ordering: **merge path persist→destroy; discard path
  persist→destroy→verify(`:634`)→flatten(`:639`)** — the verify-before-flatten invariant is
  PRESERVED (flatten NOT moved ahead of destroy on the discard path).
- [ ] The seam's retrospective-persist import is **function-local/lazy** (mirrors
  `retrospective/gate.py:201`); `teardown`/the seam symbol is **NOT** added to
  `coordination/__init__.__all__` (`coordination/` stays acyclic).
- [ ] The seam docstring records the ordering reconciliation and **confirms ADR Binding B matches the
  shipped seam** (any Binding-B wording drift flagged in the report — ADR is WP01-owned).
- [ ] All 3 production call sites (`executor.py:795`, `merge.py:270`, `mission_type.py:910`) route
  through the seam; the discard path's persist is hoisted ahead of the `_discard_mission` call at
  `:623`.
- [ ] Anti-rename structural test: **zero PRODUCTION `CoordinationWorkspace.teardown(` call sites
  outside the seam** (grep scoped to `src/specify_cli/**` + `src/runtime/**`, EXCLUDING `tests/**` +
  the seam file; the 10 legitimate test-side primitive calls survive; NO per-call exclusion list).
- [ ] Destroy-step fault injection proves the retrospective exists at `kitty-specs/<slug>/` despite
  a destroy failure — on BOTH merge and close/`--discard`.
- [ ] `test_phase_cleanup_coord_teardown_failure_is_non_fatal` (`test_executor_coverage.py:616`)
  UPDATED to the persist-before-destroy contract (NEVER deleted — DIR-041).
- [ ] FR-008: `_list_active_worktrees@78` + `_print_active_worktrees@313` removed (zero-caller
  proof recorded); terminology guard green.
- [ ] FR-009: comments `:642` + `:607` corrected.
- [ ] Flattened-mission teardown byte-identical (NFR-003); ruff + `mypy --strict` clean; `maxCC ≤ 15`.

## Risks & Mitigations

- **Merge-path ordering (highest risk):** the seam must persist before the `executor.py` cleanup
  phase; mitigated by the destroy-step fault injection on the merge path (T045) + the UPDATED
  `test_executor_coverage.py` (T044).
- **Persist failure absorbed by the swallow:** mitigated by placing persist OUTSIDE the
  `except Exception` and asserting a persist failure surfaces (T044 step 2).
- **`maxCC ≤ 15` on the seam:** mitigated by extracting small persist/flatten/destroy helpers.
- **Touching the FR-006 lane exact-set by accident:** mitigated by the negative scope — do NOT
  edit `_remove_lane_worktrees`/`_verify_discard_complete` (DONE-by-#2129).

## Review Guidance

- Confirm the seam lives in `coordination/` (NOT `merge/`) and persist sits OUTSIDE the swallow.
- Confirm the persist import is function-local/lazy (mirrors `retrospective/gate.py:201`) and the
  seam symbol is NOT in `coordination/__init__.__all__` (acyclic `coordination/`).
- Confirm the discard path preserves verify-before-flatten: persist→destroy→verify→flatten (flatten
  NOT hoisted ahead of destroy); persist hoisted ahead of the `_discard_mission` call at `:623`.
- Confirm the seam docstring confirms ADR Binding B alignment (or the report flags Binding-B drift).
- Confirm the anti-rename test is **production-scoped** (`src/specify_cli/**` + `src/runtime/**`,
  excluding `tests/**` + the seam file) with **no per-call exclusion allow-list** — the 10
  legitimate test-side `CoordinationWorkspace.teardown(` calls must survive; a rename leaving the
  production duplications is REJECTED.
- Confirm the fault injection is at the DESTROY step on BOTH paths, on a genuinely-divergent coord
  fixture (NFR-002); ask for red-run evidence.
- Confirm `test_executor_coverage.py:616` was UPDATED, not deleted (DIR-041).
- Confirm FR-008 proved zero callers BEFORE deletion and the terminology guard is green.

## Activity Log

- 2026-06-25T19:36:37Z – system – Prompt created via /spec-kitty.tasks (planner-priti); FR-004/005/008/009.
</content>
- 2026-06-25T22:05:11Z – claude:opus:python-pedro:implementer – shell_pid=1765808 – Assigned agent via action command
- 2026-06-25T22:27:52Z – claude:opus:python-pedro:implementer – shell_pid=1765808 – Shared teardown seam (coordination/teardown.py) + persist-before-destroy on all 3 sites; fault-injection both paths green (red-first verified); FR-008/009 tidy; ruff/mypy/CC15 clean. --force: lane behind target (stale mission-branch base); orchestrator reconciles.
- 2026-06-26T04:01:12Z – claude:opus:python-pedro:implementer – shell_pid=1765808 – Re-targeted onto decomposed base (lane-d acb9817b8): seam in coordination/teardown.py, persist-before-destroy routed into merge/executor.py:803, #2133 test updated, 122 tests green
- 2026-06-26T04:01:14Z – claude:opus:reviewer-renata:reviewer – shell_pid=2010647 – Started review via action command
- 2026-06-26T04:11:51Z – user – shell_pid=2010647 – renata APPROVE: seam single-authority (anti-rename grep zero), persist-before-destroy fault-injection mutation-probed RED on both paths, #2133 test updated DIR-041, FR-008/009 done, gates clean
