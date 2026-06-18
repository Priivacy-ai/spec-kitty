---
work_package_id: WP05
title: merge.py baseline extract (behavior-preserving)
dependencies:
- WP01
requirement_refs:
- FR-010
- NFR-001
- NFR-004
tracker_refs:
- '#2027'
planning_base_branch: feat/governed-state-surface-coherence
merge_target_branch: feat/governed-state-surface-coherence
branch_strategy: Planning artifacts for this mission were generated on feat/governed-state-surface-coherence. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/governed-state-surface-coherence unless the human explicitly redirects the landing branch.
subtasks:
- T040
- T041
- T042
- T043
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "4160248"
history:
- 2026-06-18 created (/spec-kitty.tasks)
agent_profile: python-pedro
authoritative_surface: src/specify_cli/merge/
create_intent:
- src/specify_cli/merge/baseline.py
- tests/specify_cli/merge/test_baseline_module.py
execution_mode: code_change
owned_files:
- src/specify_cli/cli/commands/merge.py
- src/specify_cli/merge/baseline.py
- src/specify_cli/merge/__init__.py
- tests/specify_cli/merge/test_baseline_module.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before any code, load the implementer profile and binding context. Run:

```
/ad-hoc-profile-load python-pedro
```

Then read, in this order:
1. `kitty-specs/governed-state-surface-coherence-01KVCGQC/spec.md` — **FR-010, NFR-001, NFR-004, C-002, C-004, C-006**.
2. `kitty-specs/governed-state-surface-coherence-01KVCGQC/research.md` — Goal C table (functions, line numbers, no-cycle, callers, test net).

## Objective

Relocate the cohesive **`baseline_merge_commit` record/verify cluster** out of the 3460-LOC `cli/commands/merge.py` into a named `src/specify_cli/merge/baseline.py`. This is **pure relocation + import redirect — behavior-preserving (NFR-001), no logic change rides along.** It advances the merge.py god-module decomposition (epic #2026) and is thematically the mission's *mission-state-surface ownership* theme (`baseline_merge_commit` is a `meta.json` field written here, read by `review --mode post-merge`).

**Functions to move (current lines):** `BaselineMergeCommitError` (:180), `_record_baseline_merge_commit` (:1678), `_recorded_baseline_from_working_meta` (:1756), `_read_committed_meta_json` (:1768), `_assert_baseline_merge_commit_on_target` (:1803). Deps are only `load_meta`/`write_meta`/`run_command`/`json`/`logging`/`Path` — zero `console`/`typer.Exit` coupling. `merge/` does NOT import `cli.commands.merge`, so **no import cycle**.

**Explicit NON-GOALS:** the `_run_lane_based_merge[_locked]` mega-function split (S3776 164/129) is OUT (C-002). The `merge.py:845` `S2083` BLOCKER is the canonical-seams branch's own correct path-trust guard — do NOT change it; it is a PR-body Sonar-hotspot-rationale item (C-004). Do NOT strip existing `# noqa`/`# type: ignore` (C-006).

## Subtasks

### T040 — Relocate the 5 functions verbatim (FR-010)

**Steps:**
1. Create `src/specify_cli/merge/baseline.py`. Move the 5 functions **verbatim** (logic byte-identical). Public names get clean public spellings: `record_baseline_merge_commit`, `assert_baseline_merge_commit_on_target`, and `BaselineMergeCommitError` (keep the class name). The two private helpers `_recorded_baseline_from_working_meta` / `_read_committed_meta_json` move with them and stay module-private.
2. Bring only the needed imports (`load_meta`/`write_meta` from `mission_metadata`, `run_command` from `core.git_ops`, `json`, `logging`, `Path`). Add a module docstring naming the concern.
3. Do NOT change any control flow, error messages, or raise sites.

**Validation:** `python -c "from specify_cli.merge.baseline import record_baseline_merge_commit, assert_baseline_merge_commit_on_target, BaselineMergeCommitError"` succeeds; no cycle.

### T041 — Re-export + back-compat private aliases + redirect call sites (FR-010, NFR-001) — ⚠️ blocker-fix

> ⚠️ **BINDING (squad-pedro+debbie):** **6 existing test suites import the PRIVATE names** directly `from specify_cli.cli.commands.merge import _record_baseline_merge_commit, _assert_baseline_merge_commit_on_target` (and `test_1827_baseline_regression.py` also imports `_recorded_baseline_from_working_meta`). If you only re-export the public names, those suites fail at **import** (`ImportError`) — contradicting "pass unchanged." You MUST keep all three private names importable from `cli/commands/merge.py`.

**Steps:**
1. In `src/specify_cli/merge/__init__.py`, re-export `record_baseline_merge_commit`, `assert_baseline_merge_commit_on_target`, `BaselineMergeCommitError` (add to `__all__`).
2. In `cli/commands/merge.py`: remove the moved definitions and add back-compat imports so the legacy surface still exposes BOTH the error class AND the old private names:
   ```python
   from specify_cli.merge.baseline import (
       BaselineMergeCommitError,
       record_baseline_merge_commit as _record_baseline_merge_commit,
       assert_baseline_merge_commit_on_target as _assert_baseline_merge_commit_on_target,
       _recorded_baseline_from_working_meta,   # imported by test_1827_baseline_regression.py
       _read_committed_meta_json,
   )
   ```
   Confirm `BaselineMergeCommitError` stays in `merge.py.__all__` (:3437).
3. Redirect the 2 call sites (:2675, :2842) to the public names (or keep using the `_`-aliases — identical). Keep the surrounding try/except + console/Exit translation in `merge.py` exactly as-is (callers catch `BaselineMergeCommitError`).

**Validation:** `from specify_cli.cli.commands.merge import _record_baseline_merge_commit, _assert_baseline_merge_commit_on_target, _recorded_baseline_from_working_meta, BaselineMergeCommitError` succeeds; `from specify_cli.merge import record_baseline_merge_commit, assert_baseline_merge_commit_on_target, BaselineMergeCommitError` succeeds. The 2 call sites behave identically.

### T042 — Hoist META_JSON constant (S1192)

**Steps:**
1. In `merge/baseline.py`, hoist `META_JSON = "meta.json"` as a module constant and use it for the occurrences in the moved code (the literal appeared ×6 across merge.py; hoist for the ones that travel into baseline.py).
2. Do NOT chase the other `"meta.json"` occurrences left in `merge.py` — those are out of this WP's moved scope.

**Validation:** no bare `"meta.json"` literal in the moved functions; ruff S1192 satisfied for baseline.py.

### T043 — Verify the test net + verbatim-equivalence artifact + quality gate (NFR-001, NFR-004)

**Steps:**
1. Run the baseline/merge test suites that import these names — `tests/specify_cli/merge/test_1827_baseline_regression.py`, `tests/merge/test_merge_done_recording.py`, `tests/cli/commands/test_merge_status_commit.py`, `tests/integration/test_merge_lane_planning_data_loss.py`, `tests/specify_cli/cli/commands/test_merge_coord_worktree_resync_1826.py`, `tests/specify_cli/cli/commands/test_merge_coord_topology_1772.py`, plus review suites referencing baseline. They MUST pass UNCHANGED (import-redirect is the regression net).
2. **Verbatim-equivalence artifact (F7 — resolves the "verbatim" vs "META_JSON hoist" tension):** produce a `diff` of each moved function body against its original where the ONLY permitted differences are (a) the `"meta.json"` → `META_JSON` substitution and (b) the public rename (`_record_…` → `record_…`, `_assert_…` → `assert_…`). Paste this bounded diff into the handoff note. ANY other line-level change is a NFR-001 violation — call it out + justify or revert. (Note: the `logger = logging.getLogger(__name__)` channel becomes `specify_cli.merge.baseline` — benign, expected, mention it.)
3. Add a small `tests/specify_cli/merge/test_baseline_module.py` asserting the public API is importable from both surfaces, the 3 private aliases import from `merge.py`, and a round-trip record→assert works.
4. `ruff` + `mypy` clean on `baseline.py`, `merge/__init__.py`, the touched region of `merge.py`; complexity ≤15; zero new suppressions; do not strip existing load-bearing suppressions (C-006).

**Validation:** all baseline suites green unchanged; the equivalence diff shows only the 2 permitted change classes; new module test green; ruff+mypy clean.

## Branch Strategy

Planning branch `feat/governed-state-surface-coherence`; merge target `main` (PR). Depends on **WP01**. Independent of WP02/WP03/WP04 (disjoint owned_files). Worktree per `lanes.json`.

## Definition of Done

- [ ] The 5 functions live in `merge/baseline.py`, byte-identical logic (NFR-001).
- [ ] `record_baseline_merge_commit` / `assert_baseline_merge_commit_on_target` / `BaselineMergeCommitError` importable from BOTH `specify_cli.merge` and the legacy `merge.py` surface (SC-004).
- [ ] **Back-compat private aliases** `_record_baseline_merge_commit` / `_assert_baseline_merge_commit_on_target` / `_recorded_baseline_from_working_meta` remain importable from `cli.commands.merge` (6 suites depend on them — blocker fix).
- [ ] A verbatim-equivalence diff artifact (only META_JSON + rename changes) is in the handoff (F7).
- [ ] merge.py's 2 call sites redirected; try/except translation unchanged.
- [ ] `META_JSON` hoisted for the moved occurrences (S1192).
- [ ] All 6+ baseline test suites pass UNCHANGED; new module test green.
- [ ] ruff + mypy clean ≤15, zero new suppressions; existing suppressions untouched (C-006).
- [ ] PR body will note: merge.py:845 S2083 is correct path-trust guard code → Sonar hotspot rationale, NOT a code change (C-004).
- [ ] Issue-matrix row for #2027 set to a verdict; #2027 carries a tracker comment naming mission `01KVCGQC` (SC-007).

## Reviewer Guidance

Confirm: the move is verbatim (diff the moved bodies against the originals — no logic change); both import surfaces expose the 3 names; the 2 merge.py call sites and their error translation are unchanged; no import cycle (`merge/` still doesn't import `cli.commands.merge`); the mega-function split was NOT attempted (C-002); existing suppressions intact (C-006). The strongest signal is the pre-existing baseline suites passing with zero edits.

## Activity Log

- 2026-06-18T06:20:45Z – claude:sonnet:python-pedro:implementer – shell_pid=4098966 – Assigned agent via action command
- 2026-06-18T06:37:47Z – claude:sonnet:python-pedro:implementer – shell_pid=4098966 – Extracted baseline_merge_commit cluster to merge/baseline.py verbatim (NFR-001); public + back-compat private import surfaces intact; 76+ baseline/merge tests pass; ruff+mypy clean.
- 2026-06-18T06:38:36Z – claude:opus:reviewer-renata:reviewer – shell_pid=4160248 – Started review via action command
- 2026-06-18T06:44:51Z – user – shell_pid=4160248 – Verbatim extraction VERIFIED: independently diffed all 5 moved bodies against lane base — only permitted deltas (meta.json->META_JSON, public rename _record_/_assert_ -> record_/assert_, and consequent docstring :func: cross-ref). Error class + 3 helpers byte-identical. Import surfaces: specify_cli.merge, specify_cli.merge.baseline, AND legacy cli.commands.merge private aliases all import; aliases identity-equal to public funcs; no import cycle. PATCH-SEAM DEVIATION RATIFIED (faithful=YES): run_command monkeypatch retarget to specify_cli.merge.baseline.run_command in 2 non-owned test files is genuinely required (patched callee _read_committed_meta_json relocated). test_merge_done_recording: pure target swap, assertions byte-unchanged. test_merge_status_commit: ADDITIVE patch (keeps merge.run_command + adds baseline.run_command, identical side_effect) since run_command fires from both namespaces; ExitStack conversion mechanical same-order translation forced by CPython nesting limit, all as-bindings preserved, assert count 17->17, bodies unchanged. No assertion weakened. Justified ownership-leeway. Tests 76 baseline + 286 broader merge GREEN unchanged. C-002 mega-func NOT split. C-004 S2083 guard byte-identical (line-offset only). C-006 suppressions 12->12, none stripped. ruff+mypy clean, C901<=15. New test is real git round-trip. SC-007 #2027 hygiene = orchestrator action.
