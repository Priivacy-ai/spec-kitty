# Lens A — Squash-merge artifact reconciliation (GitHub #2709)

**Lens:** "Mission squash merge overwrites target-newer artifacts and drops acceptance provenance."
**Mode:** READ-ONLY investigation. No product code or tests changed.
**Repo:** `spec-kitty-gate-doctrine` @ `fix/red-handling-policy-and-drg-regression-marks`

---

## 1. Exact clobber site(s)

**Primary clobber — `src/specify_cli/lanes/merge.py:395-403`** (`_merge_branch_into`, the
`MergeStrategy.SQUASH` branch that the mission→target integration runs):

```python
if strategy == MergeStrategy.SQUASH:
    # -X theirs: when the mission branch (source) conflicts with the
    # target on kitty-specs/ planning artifacts, the mission branch
    # version is authoritative (it carries the reviewed, finalized state).
    result = subprocess.run(
        ["git", "merge", "--squash", "-X", "theirs", source_branch],
        cwd=str(tmp_path), capture_output=True, text=True, env=_env,
    )
```

This is the *branch-integration* merge invoked from `integrate_mission_into_target`
(`src/specify_cli/lanes/merge.py:188-264`, calls `_merge_branch_into(..., strategy=SQUASH)`
at line 242). `MergeStrategy.SQUASH` is the default for mission→target (line 193).

**Why `-X theirs` is the clobber:** at every hunk where the mission branch (source =
"theirs" in `git merge`) and the target diverge from the merge-base, git resolves the
conflict by taking the **mission-branch blob wholesale**. `meta.json` and trace files
(`kitty-specs/<mission>/meta.json`, `kitty-specs/<mission>/traces/*.md`) are ordinary text
files with **no semantic merge driver**, so any region where the target added
acceptance/VCS fields *and* the mission branch also touched `meta.json` (planning/impl
edits) becomes a conflict → the target's `accepted_at / accepted_by /
accepted_from_commit / acceptance_mode / accept_commit / acceptance_history / vcs /
vcs_locked_at` fields are replaced by the older mission-branch `meta.json` that never had
them. Same mechanism drops target-newer trace sections.

**Corroborating scope — `.gitattributes:1`:**
```
kitty-specs/**/status.events.jsonl merge=spec-kitty-event-log
```
Only `status.events.jsonl` has a semantic (union) driver, configured/self-healed by
`_ensure_event_log_merge_driver_config` (`lanes/merge.py:293-321`). `meta.json` and
`traces/*.md` are deliberately *outside* that protection and therefore fall to `-X theirs`.

**No post-merge rescue:** the post-target phase (`merge/executor.py:_phase_capture_and_baseline`,
lines 497-548) only writes the #1827 baseline SHA back into target `meta.json`
(`_record_baseline_merge_commit`) and optionally a `mission_number`. It never re-reads or
re-applies the target-newer acceptance/VCS block, so nothing repairs the clobber after the
squash.

## 2. Root-cause mechanism

Concrete: **a `-X theirs` strategy-option on `git merge --squash` makes the mission branch
authoritative on every conflicting file, including `meta.json` and append-only trace
files** — i.e. wholesale blob replacement of the *source* side, not a 3-way reconciliation.
It was introduced intentionally for **planning artifacts** (spec/plan/WP outlines "carry the
reviewed, finalized state") but is *over-broad*: it also captures the two artifact classes
that must be canonical **on the target** — acceptance provenance in `meta.json` and
append-only traces. There is no field-level or append-union treatment for those files, so
"mission-branch wins" silently reverts target-newer canonical state even though the
acceptance commit stays in ancestry.

## 3. The reconciliation seam

The fix belongs at the **squash step in `_merge_branch_into`** (`lanes/merge.py:395-448`),
with per-artifact-class treatment instead of a blanket `-X theirs`:

- **`meta.json` — field-level reconciliation.** Acceptance/VCS keys
  (`accepted_at`, `accepted_by`, `accepted_from_commit`, `acceptance_mode`, `accept_commit`,
  `acceptance_history`, `vcs`, `vcs_locked_at`) are **target-authoritative**; planning keys
  may remain mission-authoritative. `acceptance_history` is a list → **append/union**, not
  replace. Canonical field shapes live in `src/specify_cli/acceptance/__init__.py`
  (dataclass + `to_dict`, lines ~359-378; recorded via `record_acceptance` /
  `_commit_acceptance_meta`) and `src/specify_cli/mission_metadata.py`.
- **`traces/*.md` — append-merge (union).** Target-newer sections must survive alongside
  mission sections; layout is `kitty-specs/<mission>/traces/*.md`
  (`src/specify_cli/retrospective/generator.py:236-242`).

Two viable implementation shapes: (a) add a **semantic merge driver + `.gitattributes`
entries** for `meta.json` (JSON field-merge) and traces (union), mirroring the existing
`spec-kitty-event-log` driver wiring in `_ensure_event_log_merge_driver_config`; or
(b) a **post-squash reconciliation pass** inside `_merge_branch_into`/`integrate_mission_into_target`
that re-reads the pre-merge target `meta.json`/traces and re-applies target-authoritative
fields/sections before the squash commit at lines 436-448. Option (a) is more canonical
(reuses the driver pattern already trusted for the event log) and keeps `-X theirs` only for
true planning artifacts.

## 4. Red-first repro entry point

Drive the **pre-existing** entry point `_run_lane_based_merge` from
`src/specify_cli/cli/commands/merge.py` (the same seam `spec-kitty merge` uses), through the
real `integrate_mission_into_target` → `_merge_branch_into` squash path.

**Harness already exists:** `tests/integration/test_merge_lane_planning_data_loss.py`,
class `TestPlanningArtifactReachesTarget` — it builds a real on-disk git repo, writes a real
`lanes.json` (`write_lanes_json`), and runs the **real** `consolidate_lane_into_mission` /
`integrate_mission_into_target` / `_merge_branch_into` while mocking only out-of-git side
effects (status emit, dossier/SaaS sync, stale-assertion check, sparse-checkout preflight,
merge gates, post-merge invariants). Markers: `pytest.mark.git_repo`, `pytest.mark.non_sandbox`.

**New failing ATDD scenario to add there:** (1) commit older `meta.json` (no acceptance
fields) + older `traces/x.md` on the mission/lane branch; (2) on the target branch, commit
`meta.json` carrying the full acceptance/VCS block + a target-newer trace section; (3) run
`_run_lane_based_merge`; (4) assert the merged target `meta.json` still contains
`accepted_at/accepted_by/accepted_from_commit/acceptance_mode/accept_commit/acceptance_history/vcs/vcs_locked_at`
and the target-newer trace section — **RED today** because `-X theirs` reverts them.
Complementary unit-level pin can target `_merge_branch_into(..., strategy=MergeStrategy.SQUASH)`
directly (see `tests/lanes/test_merge.py`).

## 5. Risks / prior art

- **Regression source identified.** `git blame lanes/merge.py:397-401` → commit **a5f30616e**
  (mission `merge-done-surface-resolver-01KTDVHZ`, **#1732**, 2026-06-06, "fix coord-branch
  write/read surface divergence"). That mission **added `-X theirs`** to make the mission
  branch authoritative for `kitty-specs/` planning artifacts — the exact change that created
  the #2709 acceptance-provenance regression. This was never recognized as clobbering
  target-newer canonical state.
- **Prior merge-hardening missions** that touched this path but did **not** fix #2709:
  `068-post-merge-reliability-and-release-hardening`, `coordination-merge-stabilization-01KTXRVR`,
  `decompose-merge-god-module-01KVXHDK`, `merge-base-diff-ssot-01KX44SD`. None added
  target-newer reconciliation for `meta.json`/traces.
- **Top risk:** naively dropping `-X theirs` (or flipping to `ours`) will re-open #1732 —
  legitimate planning-artifact conflicts would fail the squash or lose reviewed planning
  state. The fix **must be per-artifact-class** (planning = mission-authoritative; acceptance
  `meta.json` fields = target-authoritative field-merge; `acceptance_history` + traces =
  append-union), not a global strategy flip. Secondary risk: the JSON field-merge / union
  driver must be idempotent under `spec-kitty merge --resume` (executor re-runs) and coexist
  with the post-merge `_record_baseline_merge_commit` write to the same `meta.json`.
