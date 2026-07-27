---
work_package_id: WP10
title: CI collection completeness
dependencies:
- WP01
- WP05
requirement_refs:
- FR-013
- NFR-005
planning_base_branch: remediation/doctrine-silence-guards
merge_target_branch: remediation/doctrine-silence-guards
branch_strategy: Planning artifacts for this mission were generated on remediation/doctrine-silence-guards. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into remediation/doctrine-silence-guards unless the human explicitly redirects the landing branch.
subtasks:
- T050
- T051
- T052
- T053
- T054
- T055
- T056
phase: Phase 1 - Guards
history:
- at: '2026-07-26T19:45:15Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: architect-alphonso
authoritative_surface: .github/workflows/ci-quality.yml
create_intent:
- tests/architectural/test_ci_collection_completeness.py
execution_mode: code_change
model: ''
owned_files:
- .github/workflows/ci-quality.yml
- tests/architectural/test_ci_collection_completeness.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP10 – CI collection completeness

## ⚡ Do This First: Load Agent Profile

Load the `architect-alphonso` profile via `/ad-hoc-profile-load` and behave according to its guidance before parsing the rest of this prompt.

---

## Objectives & Success Criteria

- Every test file is collected by **at least one** main-branch job.
- A meta-test diffs the union of job collections against the **full** collection and fails on a planted uncollected file.
- `generate_schemas.py --check` runs in CI (WP05's deliverable, wired here).

**Requirement refs**: FR-013, NFR-005, SC-013, SC-004 (CI wiring) · [#2957](https://github.com/Priivacy-ai/spec-kitty/issues/2957)

## Context & Constraints

A frozen-contract test that no main-branch job collects is exactly as inert as a schema slot nothing produces — **WP01's defect one layer up**, which is why it is in this mission and not a CI ticket.

Verified in-tree: `fast-tests-cli` and `integration-tests-cli` both gate on `needs.changes.outputs.cli == 'true'`, and the `cli` filter covers only `src/specify_cli/cli/**`, `tests/cli/**`, `tests/specify_cli/cli/**`. **On any main push whose diff misses those paths, neither job runs.**

The `fast-tests-core-misc` split compounds it: `specify-cli-rest` carries `--ignore=tests/specify_cli/cli`, `specify-cli-rest-2` does not include it, `core-misc` ignores `tests/specify_cli` wholesale.

**Binding, every WP in this mission:**

- **Never run the full `tests/architectural/` directory** (C-003) — a known harness issue kills the session. Targeted single-file runs only.
- The 6 inherited `arch-adversarial` reds stay red (C-004). No greenwashing, no retry-to-green.
- **ATDD (C-006)**: the failing test is the **first commit** of this WP, RED on the planning base and GREEN at the final commit.
- New code passes `ruff` and `mypy --strict` with zero issues. No `# noqa` / `# type: ignore` to get there.
- Charter: `.kittify/charter/charter.md`. Spec: `../spec.md`. Plan: `../plan.md`. Manifest: `../tasks.md`.

## Branch Strategy

- **Planning base branch**: `remediation/doctrine-silence-guards`
- **Merge target branch**: `remediation/doctrine-silence-guards` → draft PR to `main`; the operator merges.

## Subtasks & Detailed Guidance

### Subtask T050 – Failing-first test.

The union of main-branch job collections currently omits `tests/specify_cli/cli/` and `tests/cli/`. Prove it.

### Subtask T051 – Root-cause the gap.

Start from the `changes` paths-filter and the job `if:` conditions — **not** from the shard globs. Record the finding.

### Subtask T052 – Implement the meta-test.

Union of per-job collections vs the **full** collection.

### Subtask T053 – Self-mutation test (NFR-005).

Plant an uncollected file; assert RED.

### Subtask T054 – Close the gap.

So the union is complete.

### Subtask T055 – Report, do not fix.

Whatever reds this newly surfaces are **honest pre-existing reds** under ADR `2026-07-17-1`. Report them; do not fix them here; **never** satisfy the gate by reclassifying a red as expected.

### Subtask T056 – Wire `generate_schemas --check` into CI.

WP05's SC-004 deliverable; this WP owns the workflow file.

## ⚠️ Four traps found by the post-tasks squad — read before starting

1. **A sanctioned greenwashing path already exists, and it is on your route.** `test_gate_coverage.py` ratchets against `_gate_coverage_baseline.json`, and its own assertion message ends *"regenerate the baseline with `--update-baseline`"* (`:603`, `:627`). Add gating-awareness and you get ~950 new orphans plus one documented command that erases them. **The new gate must be baseline-free and must not read `_gate_coverage_baseline.json`.** Reviewers: check this explicitly.
2. **Do not build a new parser.** `_gate_coverage.py:457` already carries `WorkflowModel.job_gating_groups` (job → dorny group, populated at `:556`). The existing `analyze()` is blind only because `Gate` (`:194`) has no gating-group field, so a test counts as covered if any selector matches regardless of whether that job runs — which is why the committed baseline records `orphan_test_count: 0`, true in the "all jobs run" model and vacuous in reality. The fix is `analyze(..., active_groups=…)`, not a rewrite.
3. **The naive fix breaks an existing invariant.** `test_src_filter_coverage.py:180-192` (`test_every_named_group_gates_a_test_running_job_live`) asserts every named group gates ≥1 test-running job. Deleting `needs.changes.outputs.cli == 'true'` orphans the `cli` group and reds it. The `|| github.event_name == 'push'` disjunct preserves the reference and keeps it green.
4. **This WP's own new test file would be inert.** All three `arch-adversarial` legs run the same four paths and partition by the `arch_shard_N` marker applied from `tests/_arch_shard_map.py` (`ci-quality.yml:1916`, `:1933`). An unregistered new file under `tests/architectural/` is collected and then **deselected by every leg**. **Register it in `tests/_arch_shard_map.py` as part of T052.**

5. **A fifth instance of this defect class, observed live during WP01.** Its `move-task --to for_review` ran the pre-review regression gate and the gate reported, verbatim: `no_coverage — excluded scope — unverified: every changed file landed only in a catch-all group (core_misc/e2e/any_src) or matched no dorny group at all`. **It ran, it passed, and it verified nothing** — a green check that is evidence of nothing, produced by the same dorny-group mechanism this WP is fixing. Treat the pre-review gate as in scope for the collection-completeness argument: a file that matches only a catch-all group is the same failure as a job that never runs.

**Cost note, so nobody builds the wrong thing:** one whole-tree `--collect-only` is ~50 s for 33,665 tests and `collect_universe()` already runs in CI, so gate simulation is in-process and sub-second — zero marginal cost. The subprocess-per-job approach took ~25 minutes wall-clock at 6-way parallelism. Design for one collection.

## Test Strategy

- `PYTHONPATH=src python -m pytest tests/architectural/test_ci_collection_completeness.py -q`
- Confirm the four files named in #2957 are collected by a main-branch job.

## Risks & Mitigations

- **The existing completeness check is scoped to the split, not the tree.** Its comment records "Verified disjoint + union-complete locally: 3241 + 3079 == 6320" — that verified the bin-split preserved a selection which **already had the hole**. Diff against the **full** collection or reproduce the same vacuity in a new place.
- T055 is a **reporting** subtask. The obvious way to make a new meta-test green is to mask what it finds — that is the greenwashing the charter forbids.

## Review Guidance

- Verify red→green: the WP's first commit was RED on `remediation/doctrine-silence-guards` and is GREEN at the final commit.
- Verify every gate added is **non-vacuous**: it must reject a planted violation, and its allowlist must be empty.
- Verify the graph invariant where the WP claims it (311 nodes / 774 edges).

## Activity Log

> **CRITICAL**: entries in chronological order, oldest first. **Append** new entries at the END.

- 2026-07-26T19:45:15Z – system – Prompt created.
- 2026-07-27T11:55:00Z – architect-alphonso – **T055 report — what the completeness gate found on its first live runs.** Recorded here rather than in a commit message: NFR-005 requires the meta-test to *report honestly*, and a commit message is not a durable report.

  **Measurement basis.** All figures below were re-measured on
  lane branch `kitty/mission-doctrine-silence-guards-01KYFV7Q-lane-j` at its WP10 tip (lane shas
  are rewritten by rebase; the gate re-derives every figure live), rebased onto
  `remediation/doctrine-silence-guards` at `1764b4c0b`. One whole-tree `--collect-only` pass;
  job activation evaluated for `event_name=push`, `branch=main`, `active_groups=∅` (the worst
  reachable filter state). **Universe: 33,822 collected test NODES across 2,174 files.**

  | | suite jobs started | test NODES uncollected | files with ≥1 such node |
  |---|---|---|---|
  | **Before** (workflow topology at `1764b4c0b`) | 10 of 50 | **31,547** (93.3%) | 1,966 of 2,174 |
  | **After** (this lane) | 49 of 50 | **0** | 0 |

  (56 vs 17 counts the *whole* job graph including non-suite jobs such as `changes`, `lint` and
  `build-wheel`; 49 vs 10 counts only jobs that actually invoke pytest. Both pairs are correct
  measurements of different things — the suite-job pair is the one that bears on collection.)

  All four files named in **#2957** were uncollected before and are collected after.

  **Superseded figures.** The `950 of 2166 files / 14,870 of 33,665 nodes` in SC-013 and the
  `31,540 of 33,771` first written into the `ci-quality.yml` header are both withdrawn; SC-013 is
  amended in `spec.md` and the `ci-quality.yml` header is corrected on the lane. The `33,771` universe
  predated two files: WP10's own gate module and the campsite roster test (see below).
  `33,771 + 34 + 7 = 33,812`, and the gate module then grew from 34 to 44 nodes during review
  remediation, giving today's `33,822`. Nothing else moved; the earlier reviewer/implementer
  discrepancy is fully accounted for by measurement timing, not by a tree difference.

  **Green-path qualifier.** `needs.<job>.result == 'success'` is the model's one deliberate
  fail-OPEN conjunct, so the guarantee is *"collected on a push to `main` on the green path"* and
  the before-figure is a **lower bound** on a run where an upstream job fails. Both docstrings now
  state this rather than asserting the property unconditionally.

- 2026-07-27T11:56:00Z – architect-alphonso – **T055 report — reds and gaps the gate surfaced. Reported, not repaired.**

  **1. `tests/release/test_dogfood_command_set.py` — a routed file with no tier marker.** Its 5
  nodes carry only `skipif`; no `unit`, `fast` or `integration`. Both `ci-quality.yml` release jobs
  deselected it on their `-m` expressions, and the only gate that selected it was
  `release.yml::build-release`, which triggers on `v*.*.*` tags — never on a push to `main`. So the
  file was uncollectable on `main` for a reason that has nothing to do with the dorny topology:
  it is under a routed *path* and invisible to the *marker* partition. WP10's topology-fix commit widened
  `integration-tests-release` to `… or not fast`, which catches marker-less files. **That is
  containment, not a fix**, and it is fragile in an unusual direction — verified by counterfactual
  against the live gate model: give the file a `fast` marker and it moves cleanly to
  `fast-tests-release`; give it `fast` while the `not fast` fallback is the only thing holding it
  and it would have gone dark again. The real fix is a tier marker on the file.

  **2. `tests/specify_cli/cli/commands/agent/test_mark_status_authored_roster.py` — the gate's
  first live catch, on a file that had existed for eleven hours.** It landed on
  `remediation/doctrine-silence-guards` in campsite commit `f65646ae7` (2026-07-27 00:08) with **no
  markers at all** — not `unit`, not `fast`, nothing — so no job's `-m` expression selected any of
  its 7 nodes and they ran in no CI job on any event. Neither the ratchet
  (`test_gate_coverage.py`, which models every job as running) nor any review caught it; the
  completeness gate did, on its first green-topology run. Fixed on the planning branch in
  `1764b4c0b` (`pytestmark = [pytest.mark.unit, pytest.mark.fast]`, the sibling convention for
  pure-logic `tmp_path` tests) — **not** by this WP, and **not** by relaxing the gate.

  **3. The class is open.** Both instances are the same defect: a test file with no tier marker is
  invisible to a marker-partitioned CI, and nothing in the repository rejects one at authoring
  time. WP10 closes the *topology* half (a job that never starts) and leaves the *taxonomy* half
  (a file no `-m` expression selects) open, filed as a follow-up rather than folded in — the fix is
  a new always-on marker-completeness gate plus a sweep of existing offenders, which is
  mission-sized. Follow-up issue: see the issue-matrix row for #2957.

  **No red was reclassified, no baseline was regenerated, and no allowlist was added.** The gate
  has none of the three to offer.
