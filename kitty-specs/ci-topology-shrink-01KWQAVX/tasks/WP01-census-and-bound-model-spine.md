---
work_package_id: WP01
title: 'Census + bound-model spine: construction-derived worklist + additive _gate_coverage relations'
dependencies: []
requirement_refs:
- FR-001
- NFR-001
- NFR-002
- NFR-003
- NFR-006
- C-001
tracker_refs: []
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-ci-topology-shrink-01KWQAVX
base_commit: aa998ede7e31927286e78e7819757e03c2f2c604
created_at: '2026-07-04T21:00:00+00:00'
subtasks:
- T001
- T002
- T003
phase: Phase 1 - Spine
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "1073255"
history:
- at: '2026-07-04T21:00:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: tests/architectural/_gate_coverage.py
create_intent:
- tests/architectural/ci_topology_census.json
execution_mode: code_change
model: ''
owned_files:
- tests/architectural/_gate_coverage.py
- tests/architectural/ci_topology_census.json
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP01 – Census + bound-model spine

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter (or any user-defined profile), and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`

---

## ⚠️ IMPORTANT: Review Feedback

Check the `review_ref` field in the event log before starting; address all feedback.

---

## Objectives & Success Criteria

Two enablers everything downstream stacks on (C-001 additive — consume the bound `_gate_coverage` model, never rebuild the marker→job substrate):

1. **NFR-006 census (the critical deliverable)**: commit `tests/architectural/ci_topology_census.json` as the construction-derived worklist authority WP02's SC-001 test iterates — with a **freshness-guard** so a stale hand-edit reds. The metric must measure coverage, NOT the implementer's constant.
2. **IC-04 parse extension**: extend `tests/architectural/_gate_coverage.py` ADDITIVELY with every parsed relation WP02 consumes (differential-matrix per dir; same-tier per test; always-on arch-job recognition). This file is a single-owner spine: after this WP it is **READ-ONLY** for the rest of the mission (Wave-2 spine lesson).

## Subtasks & Detailed Guidance

### Subtask T001 – Construction-derived census artifact + freshness-guard
Re-derive the census LIVE (do NOT hand-copy research.md numbers — research is a snapshot; the tree may have moved). Reproduce the research §1.1 command:
```bash
for d in src/specify_cli/*/; do
  n=$(find "$d" -name '*.py' | xargs wc -l 2>/dev/null | tail -1 | awk '{print $1}')
  echo "$n $d"
done | sort -rn
```
Write `tests/architectural/ci_topology_census.json` per data-model.md:
- `t_loc` (int, committed constant — recommended 500; the plan-time floor, NEVER a literal in the WP02 test).
- `rule` (str): `D ∈ worklist ⟺` direct child of `src/specify_cli/` ∧ `sum(LOC *.py under D) ≥ t_loc` ∧ no src-backed dorny group globs `src/specify_cli/<D>/**`.
- `worklist[]`: each `{ dir, loc, cone_roots[], target_group, target_shard }`.
- `mapped_dirs[]`: the already-mapped dirs (the negative-assertion oracle, research §1.2).
- `arch_blind_groups[]`: the 13 Mode-B groups (un-blind targets, research §1.4B).
- `timings_baseline`: `{ fast_core_misc_min, arch_shard_min, critical_path_min, next_lane_min, source_run_id }` (NFR-001 — the 29.4-min baseline; cite the live run id).
- **Freshness-guard**: expose a **pure re-derivation function** `live_derived_worklist()` (importable from `_gate_coverage.py`, no side effects) that re-derives the worklist from the LIVE tree, so WP02's `test_ci_topology_worklist.py` asserts `census.worklist == live_derived_worklist()` as a pytest-collected `architectural` assertion. A stale/hand-trimmed census MUST then red in CI. The assertion lives in WP02's test file, not this module (this module stays pure/assertion-free); a `--verify-census` CLI mode may wrap the same function but the mechanized guarantee is the WP02 assertion.

### Subtask T002 – Additive `_gate_coverage.py` parse extensions (additive only)
Read `_gate_coverage.py` end-to-end first (the #2368 mission already extended it with `WorkflowModel`, `filter_groups`, `job_needs`, `job_gating_groups`, `cov_targets`, `diff_cover_critical_paths`). Extend ADDITIVELY (new functions / dataclass fields; do NOT change existing behavior — every existing consumer test must pass untouched):
- **Differential-matrix relation (NFR-002)**: `{ dir → arch_selected: bool }` over every `src/specify_cli/*` dir. Arch-selected iff the dir's touch selects the arch/adversarial suite. With WP03's always-on arch job (no src path filter) every dir is selected by construction; this relation is what proves the job stays unconditional (a regression re-adding a filter-group gate to it reds NFR-002).
- **Same-tier uniqueness relation (NFR-003)**: `{ test → count_fast_shards, count_integration_shards }` over the parsed `Gate` list. Distinct from the existing report-only cross-tier duplicate count (3550).
- **Always-on arch-job recognition**: recognize a group-less `if: always()` suite job (like `lint`) as legitimately absent from `JOB_GROUPS`/`src_backed_groups` — so it does not perturb the FR-010 relations (research §4.2).
Keep it PURE parsing — NO assertions in this module (the invariants live in WP02's test files). Docstring each new surface with the FR/NFR it serves.

### Subtask T003 – Gates
- `PWHEADLESS=1 uv run pytest tests/architectural/test_gate_coverage.py tests/architectural/test_src_filter_coverage.py tests/architectural/test_workflow_coherence.py tests/architectural/test_marker_job_completeness.py -q` — all existing consumers green, UNTOUCHED (`git diff --stat` shows only `_gate_coverage.py` + the census json).
- A self-check script exercising each new parse surface against the LIVE workflows; paste the outputs (worklist size, arch-blind group count, the 8-marker routed set, needs-map sizes, the differential-matrix arch-blind count on TODAY's topology — expected 13) into the Activity Log. **These recorded counts are WP02/WP03's ground truth.**
- Diff-scoped `ruff check` exit 0; `uv run mypy` on the touched file stays Success.

## Implementation Notes

- **Sonar S3776 (complexity ≤15)**: the differential-matrix (dir → arch_selected, tests × gates) and same-tier uniqueness relations are the two complexity risks in this extension. Extract deterministic helpers (stable inputs/outputs — e.g. a pure `arch_selected_for_dir(dir, model)` and a pure `shard_counts_for_test(test, gates)`) so each new function stays ≤15 cyclomatic complexity, and add focused tests exercising those helper branches directly (Sonar new-code coverage).
- **Sonar S1192 (repeated literals)**: hoist any repeated census-path literal (`tests/architectural/ci_topology_census.json`) to a single named module constant rather than duplicating the string ≥3 times across the module/CLI/self-check.

## Campsite cleaning (standing rule; ride the WP's normal review)

Sonar: verify zero open issues in `_gate_coverage.py` before landing. Run a local `ruff --select ALL` census on the touched surface and clear auto-fixables in one `ruff check --fix` pass (SAFE only — no behavior change). Adjudicate anything load-bearing OUT with an inline rationale. Do NOT expand scope beyond the two owned files.

## Definition of Done (non-fakeable — every anchor is a green test or parsed assertion)

- **Census freshness-guard mechanized in WP02**: expose the freshness check as a **pure re-derivation function** (`live_derived_worklist()` — importable from `_gate_coverage.py`, no side effects, re-derives the worklist from the LIVE tree) so WP02's `test_ci_topology_worklist.py` can assert `census.worklist == live_derived_worklist()` as a pytest-collected `architectural` assertion. The DoD anchor is **the WP02 `census.worklist == live_derived_worklist()` assertion is green** — NOT a pasted live self-check output in the Activity Log (a stale/hand-trimmed census must red in CI, not merely in a manual log paste). WP01's own `git diff --stat` self-check counts still get recorded for WP02/WP03 ground truth per T003, but the freshness *guarantee* is the mechanized WP02 assertion.
- **Additive relations exist and parse**: differential-matrix returns 13 arch-blind on today's topology (the pre-WP03 red baseline); same-tier relation returns per-test shard counts; always-on-arch recognition returns the current group-less always-on jobs. All exercised by the self-check, counts recorded.
- **Existing consumers untouched-green**: the four listed consumer suites pass with zero edits to them (`git diff --stat` proves only `_gate_coverage.py` + census changed).
- `ruff` + `mypy` clean on the diff.

## Risks / Reviewer Guidance

- The census must be construction-derived: reject any hand-picked worklist — the freshness-guard is the teeth (NFR-006).
- Reject any change to existing parse behavior (additive-only by contract). Any downstream discrepancy in a recorded count is WP01 feedback (re-open), NOT a downstream workaround — the cross-check is explicit.

## Activity Log

> Append at the END, chronological. Format: `- YYYY-MM-DDTHH:MM:SSZ – agent_id – <action>`

- 2026-07-04T21:00:00Z – system – Prompt created.
- 2026-07-04T22:05:57Z – claude:opus:python-pedro:implementer – shell_pid=960974 – Assigned agent via action command
- 2026-07-05T00:20:00Z – claude:opus:python-pedro:implementer – T001 census: emitted construction-derived `tests/architectural/ci_topology_census.json` via new `--emit-census` CLI (32 worklist dirs, 23 mapped_dirs, 13 arch_blind_groups, t_loc=500). Live LOC re-derivation `src_package_loc()` verified byte-exact against the research §1.1 shell census (`find … | wc -l`) for cli/sync/retrospective/auth/task_utils — 0 mismatches. Freshness guard = pure importable `live_derived_worklist()` (dir+loc re-derived live from the tree + live dorny filter parse; committed `_COMPOSITE_ROUTING` plan overlay for group/shard/cone_roots); `--verify-census` reports "census fresh: 32". WP02 anchors `census.worklist == live_derived_worklist()`.
- 2026-07-05T00:20:00Z – claude:opus:python-pedro:implementer – T002 additive relations (all pure, no assertions): (a) `differential_arch_matrix()` NFR-002 over all 65 `src/specify_cli/*` dirs → **13 arch-blind** on today's topology [agent_utils, charter_runtime, cli, dashboard, lanes, merge, missions, post_merge, release, review, runtime, sync, upgrade]; `arch_trigger_groups()`={acceptance, core_misc, execution_context}; `always_on_arch_present()`=False (pre-WP03 red baseline). (b) `same_tier_shard_counts(gates, universe)` NFR-003 over live universe (28673 tests): max fast-shard count/test=2, max integration-shard count/test=7, tests-in->1-fast-shard=2494, tests-in->1-integration-shard=796 (the pre-shrink same-tier duplication WP03 drives to ≤1). (c) `group_less_suite_jobs()` always-on recognition → 6 group-less suite jobs [build-release, drift-detector, lint, quarantine-visibility, slow-tests, unit-contract-residual] (legitimately absent from JOB_GROUPS/src_backed_groups; the seam WP03's always-on arch job uses without perturbing FR-010).
- 2026-07-05T00:20:00Z – claude:opus:python-pedro:implementer – T003 gates: 4 consumer suites GREEN + UNTOUCHED (test_gate_coverage / test_src_filter_coverage / test_workflow_coherence / test_marker_job_completeness — 57 passed, only the pre-existing report-only ≥2-gate duplicate warning). `git diff --stat` = only `_gate_coverage.py` (+547) + new `ci_topology_census.json`. Diff-scoped `ruff check` exit 0; `mypy` Success. Campsite `ruff --select ALL` census: 29 findings, all project-ignored categories (T201 print in this `python -m` CLI module; D400/D401 pydocstyle docstring-mood, consistent with existing module style) — no safe autofixes, nothing load-bearing; adjudicated OUT. Needs-map sizes: ci-quality job_needs=51 (46 non-empty)/filter_groups=23; ci-windows 2/1; drift-detector 1/0; release 4/3. routed-by-marker set (existing relation)=10 [architectural, contract, fast, git_repo, integration, quarantine, slow, timing, unit, windows_ci]. Lane commit: 8daa01752.
- 2026-07-04T22:29:45Z – claude:opus:python-pedro:implementer – shell_pid=960974 – Ready for review: census + additive relations, 4 consumer suites green untouched, 13 arch-blind baseline recorded
- 2026-07-04T22:30:55Z – claude:opus:reviewer-renata:reviewer – shell_pid=984315 – Started review via action command
- 2026-07-04T22:36:03Z – user – shell_pid=984315 – Review passed (reviewer-renata, DIR-030/041 + non-fakeable-assertion + additive-contract lenses): freshness-guard has real teeth — verified live_derived_worklist re-derives dir+LOC live (byte-exact vs shell census incl. boundary dir task_utils=505>t_loc=500); hand-trimmed census diverges; t_loc shift changes membership 32->31->39, so LOC is genuinely live not echoed. differential_arch_matrix=13 arch-blind (always_on_arch=False pre-WP03 baseline), worklist=32, module assertion-free & side-effect-free (census mtime unchanged after pure calls; only CLI --emit-census writes). 4 consumer suites 57 passed UNTOUCHED (only pre-existing report-only dup warning). Diff = only the 2 owned files (+547/+396). ruff+mypy clean, C901<=15. Nit (non-blocking): Activity Log narrates '65 src dirs' but differential_arch_matrix iterates 66 direct-child dirs; count-narration only, the load-bearing 13 arch-blind is verified.
- 2026-07-04T23:45:28Z – user – shell_pid=984315 – Moved to planned
- 2026-07-04T23:45:42Z – claude:opus:python-pedro:implementer – shell_pid=1058736 – Started implementation via action command
- 2026-07-04T23:54:15Z – claude:opus:python-pedro:implementer – cycle-1 fix (re-opened from approved; cycle-2 feedback is the identical re-emission): `live_derived_worklist()` now subtracts a **frozen** committed baseline `_PRE_MISSION_MAPPED_SRC_DIRS` (23 dirs, identical to census `mapped_dirs`: acceptance, agent_utils, charter_runtime, cli, coordination, core, dashboard, delivery, doctrine_synthesizer, event_journal, lanes, merge, missions, post_merge, release, review, runtime, saas, state, status, sync, tool_surface, upgrade) instead of the LIVE `mapped_src_dirs(models)`. Root defect: deriving against the live mapped set made the mission's own success (WP03 globbing the 32 worklist dirs) empty the worklist, making WP02's freshness/routing/non-empty assertions mutually unsatisfiable. `mapped_src_dirs()` left UNCHANGED (still live for differential_arch_matrix + WP02 routing test); dropped the now-unused `models` param from `live_derived_worklist()` (build_census call updated). Kept `_gate_coverage.py` self-contained — the frozen baseline is a committed literal, NOT read from the census JSON it validates. Lane commit fc350dde6.
- 2026-07-04T23:54:15Z – claude:opus:python-pedro:implementer – Census REGENERATED via `--emit-census`: `git diff tests/architectural/ci_topology_census.json` EMPTY (worklist still 32, mapped_dirs still 23) — only the derivation function changed, not the census content. Pre-WP03 freshness `census.worklist == live_derived_worklist()` GREEN (32==32). 4 #2368 consumer suites (test_gate_coverage / test_src_filter_coverage / test_workflow_coherence / test_marker_job_completeness) 57 passed, UNTOUCHED. Diff-scoped `ruff check` exit 0; `mypy` Success on `_gate_coverage.py`.
- 2026-07-04T23:54:15Z – claude:opus:python-pedro:implementer – RECONCILIATION PROVED BY SIMULATION (throwaway self-check, NOT committed; injected a synthetic src-backed dorny group globbing all 32 worklist dirs to simulate WP03). Output — [pre-WP03] freshness census==live: True (n=32); [POST-WP03 SIM] [1] freshness census.worklist == live_derived_worklist(): True (32==32); [2] routing worklist ⊆ mapped_src_dirs(sim): True (mapped=55=23+32, worklist=32); [3] worklist non-empty: True (n=32); ALL THREE GREEN TOGETHER: True. Frozen baseline keeps the worklist at 32 post-mapping (55 live-mapped ⊇ 32 worklist), so WP02's three assertions are now simultaneously satisfiable. Teeth strengthened: a new hot dir (≥ t_loc, ∉ frozen baseline) now grows live derivation beyond the committed census → reds.
- 2026-07-04T23:57:18Z – claude:opus:python-pedro:implementer – shell_pid=1058736 – cycle-1 fix: frozen-baseline worklist derivation; post-WP03 reconciliation simulated green; census unchanged; 4 consumer suites green untouched
- 2026-07-04T23:58:34Z – claude:opus:reviewer-renata:reviewer – shell_pid=1073255 – Started review via action command
- 2026-07-05T00:05:19Z – user – shell_pid=1073255 – cycle-1 fix (fc350dde6) approved on re-review: supersedes review-cycle-2 rejection whose prescribed frozen-baseline fix is now implemented. Post-WP03 reconciliation independently proven by reviewer simulation — freshness(32==32)/routing(32 subset 55 mapped)/non-empty all GREEN together; frozen baseline == census.mapped_dirs == live-mapped-today (23, exact); teeth strengthened (new hot dir grows live_derived -> reds); census unchanged by fix commit; 57 consumer tests + ruff + mypy clean
- 2026-07-05T01:30:00Z – claude:opus:python-pedro:implementer – PRE-MERGE SQUAD REMEDIATION (reviewer-renata aggregate finding, integration-tip polish — WP stays approved). The census `mapped_dirs` (23) and `arch_blind_groups` (13) shipped STALE: computed pre-WP03 and never regenerated, so the artifact literally listed the 13 Mode-B blind groups the mission ELIMINATED — contradicting `test_arch_unblind_matrix.py::test_no_src_dir_is_architecturally_blind` (0 blind). Root cause: the freshness guard covered ONLY `worklist`, not the other two `build_census()`-derived fields. FIX: (1) regenerated `ci_topology_census.json` via `--emit-census` — `git diff` shows ONLY `mapped_dirs` 23→55 and `arch_blind_groups` 13→[] changed; `worklist` unchanged at 32 (derives from frozen `_PRE_MISSION_MAPPED_SRC_DIRS`, not the live mapped set), `t_loc` unchanged at 500. (2) Widened the freshness guard to all 3 derived fields: two new `architectural`-marked sibling tests in `test_ci_topology_worklist.py` (`test_census_mapped_dirs_matches_live_derivation` asserts `census["mapped_dirs"] == sorted(mapped_src_dirs(models))`; `test_census_arch_blind_groups_matches_live_derivation` asserts `census["arch_blind_groups"] == build_census()["arch_blind_groups"]` and its dir-set == `arch_blind_src_dirs()`), and widened `_verify_census` (still pure — no asserts in module) to compare `worklist`/`mapped_dirs`/`arch_blind_groups` against `build_census()`. BITE PROOF: hand-staled the census (mapped_dirs→23-subset, arch_blind_groups→1 synthetic row) → both new tests RED and `--verify-census` exit 1 naming `['mapped_dirs', 'arch_blind_groups']`; reverted via `--emit-census`. VERIFY: `test_ci_topology_worklist.py` (8 passed, was 6) + `test_arch_unblind_matrix.py` + `test_gate_coverage.py` = 29 passed; `--verify-census` "census fresh: 32 worklist, 55 mapped, 0 arch-blind"; `--check` orphans=0 (new tests are in an already-gated file → no new orphan file → baseline needs NO re-refresh); ruff + mypy clean on both owned files.
