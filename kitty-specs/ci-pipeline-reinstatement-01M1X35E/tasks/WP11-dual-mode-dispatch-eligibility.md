---
work_package_id: WP11
title: Dual-mode + manual dispatch + merge-eligibility (skipped≠green)
dependencies:
- WP01
- WP02
- WP03
- WP04
- WP05
- WP06
- WP07
- WP09
requirement_refs:
- FR-018
- FR-019
- NFR-008
planning_base_branch: feat/ci-pipeline-reinstatement
merge_target_branch: feat/ci-pipeline-reinstatement
branch_strategy: Planning artifacts for this mission were generated on feat/ci-pipeline-reinstatement. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/ci-pipeline-reinstatement unless the human explicitly redirects the landing branch.
subtasks:
- T056
- T057
- T058
- T059
- T060
history:
- at: '2026-09-07T00:00:00Z'
  actor: planner-priti
  action: created
agent_profile: python-pedro
authoritative_surface: tests/architectural/test_dual_mode_contract.py
create_intent:
- tests/architectural/test_dual_mode_contract.py
- kitty-specs/ci-pipeline-reinstatement-01M1X35E/dual-mode-dispatch-evidence.md
execution_mode: code_change
owned_files:
- tests/architectural/test_dual_mode_contract.py
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile

Load your assigned agent profile via `/ad-hoc-profile-load <profile>` (role:
implementer) before anything else. Then read `plan.md` (TOPOLOGY T4), `spec.md` US9 +
FR-018/FR-019 + NFR-008 + SC-009/SC-010, `research.md` D3, `data-model.md` E6, and the
charter §"ATDD-First".

**Cluster gate:** claim after ALL FOUNDATION (WP01–WP06) + WP07 (router) + WP09
(shards, mode input threaded) are approved/done.

## Objective

Realize the **two run modes** and the **merge-eligibility invariant**:

- **PR mode** = fail-fast: a red predecessor short-circuits its dependent successors
  (no runner compute burned while a failure stands — NFR-008).
- **Full mode** (nightly + manual "run full") = run-all-regardless: `fail-fast: false`
  + `if: always()` so every job runs and reports the complete failure set (SC-009).
- **Manual dispatch (SC-010/C-009):** every reinstated workflow exposes
  `workflow_dispatch`.
- **Merge-eligibility (FR-019, the pinned invariant):** a successor **skipped** by
  short-circuit MUST NOT count as a pass — the required-check set distinguishes
  short-circuit-skipped from passed, so a short-circuited PR is never mergeable on a
  masked failure.

**Owned_files partition decision (binding):** the `mode` input is *declared* by the
warmup composite (WP04) and *threaded* by the router (WP07) and module-tests (WP09).
The mode-conditioned fail-fast/short-circuit LOGIC and the `workflow_dispatch` trigger
are **authored by each workflow-owning WP inside its own owned workflow file** — WP07
(`ci-router.yml`), WP09 (`module-tests.yml`/`ci-modules.yml`), WP10 (`ci-aggregate.yml`),
WP12 (`sonar.yml`), WP13 (`ci-nightly.yml`), WP14 (`packs.yml`). This WP does **not**
author per-workflow logic. WP11 owns exactly three cross-cutting artefacts: (a) the
**contract test** `test_dual_mode_contract.py` that ASSERTS the threading + the
invariant across the on-disk workflow set, (b) the **dispatched-run evidence doc** (the
short-circuit/run-all/skipped≠green behavior is GitHub *host* behavior, provable only by
a real dispatched run — SC-009), and (c) the **skipped≠green (SC-009) required-check
assertion**. Do NOT edit any workflow-owning WP's owned file here; assert against them
and, where a `mode`/`if:`/`workflow_dispatch` wiring gap is found, coordinate the fix
into the owning WP via the orchestrator — never cross-edit.

## Subtask guidance

### T056 — Red-first: `test_dual_mode_contract.py` (SEPARATE first commit)

As your **first commit**, author `tests/architectural/test_dual_mode_contract.py`
asserting (against the on-disk workflows): PR mode threads `fail-fast: true` + tiered
`needs:` short-circuit; full mode threads `fail-fast: false` + `if: always()`; every
reinstated workflow declares `workflow_dispatch`; and the terminal gate + required-
check set treat a short-circuit-skipped successor as **not green**. Run against base:
red for the right reason (mode wiring / `if: always()` absent).

### T057 — Verify mode threading (PR fail-fast vs full run-all)

Confirm the `mode` input threaded by WP07/WP09 produces PR fail-fast (red predecessor
stops successors) and full run-all (`if: always()` on the terminal gate). Where the
threading is incomplete, record the gap and coordinate the fix into WP07/WP09 (do not
edit their files). The contract test pins the required end state.

### T058 — `workflow_dispatch` everywhere

Assert every reinstated workflow (router, ci-modules, module-tests, ci-aggregate,
sonar, ci-nightly, packs) declares a `workflow_dispatch` trigger (SC-010/C-009). This
is a static assertion over the on-disk YAML set.

### T059 — Merge-eligibility (skipped≠green)

Assert the required-check set distinguishes short-circuit-skipped from passed: a
successor skipped because its predecessor red is NOT counted green for merge. Name the
mechanism (research D3: `if: always()` on the terminal gate + a required-check set that
treats "skipped-due-to-upstream" distinctly). This closes the FR-019 masked-failure
loophole.

### T060 — Dispatched-run evidence doc

Because short-circuit / run-all / skipped≠green are host behaviors, produce
`kitty-specs/ci-pipeline-reinstatement-01M1X35E/dual-mode-dispatch-evidence.md`:
trigger a real dispatched run (or a PR with a deliberately-failing early gate) and
capture evidence that (a) PR mode ran strictly fewer jobs (dependent successors
skipped), (b) a full run with ≥2 failures ran 100% of jobs and reported every failure,
(c) the skipped successor did not count green. This is the SC-009 runtime proof — the
static contract test alone does not establish host behavior.

## Branch Strategy

- Base/target: `feat/ci-pipeline-reinstatement`; worktree via `spec-kitty implement WP11`.
- Depends on all FOUNDATION + WP07 + WP09 — claim after approved/done.
- Commit order: **T056 red-first FIRST**, then T057–T060.

## Definition of Done

- T056 red on base (evidence captured), green on final.
- `test_dual_mode_contract.py` asserts PR fail-fast, full run-all `if: always()`,
  `workflow_dispatch` on every workflow, and skipped≠green.
- The dispatched-run evidence doc records a real run proving strictly-fewer-jobs (PR),
  100%-jobs (full), and skipped-successor-not-green (SC-009).
- No edits to WP07/WP09 owned files; any wiring gap was routed to the owning WP.
- **Targeted test surface**: `pytest tests/architectural/test_dual_mode_contract.py -q`.

## Risks

- **Static-only over-claim**: the contract test proves *wiring*; SC-009 is host
  behavior — the evidence doc (T060) is required, not optional.
- **Cross-WP wiring gap**: if `mode`/`if:` is under-threaded in WP07/WP09, this WP
  cannot fix it in-place (partition) — coordinate, don't cross-edit.
- **Required-check config**: the skipped≠green invariant depends on branch-protection
  required-check config, which is repo settings, not YAML — document the required
  config in the evidence doc.

## Reviewer guidance

- Confirm T056 red-on-base for the right reason.
- Confirm the evidence doc shows a REAL dispatched/failing run (job counts), not a
  described hypothetical.
- Confirm skipped≠green is asserted and evidenced (a short-circuited PR is not
  mergeable).
- Confirm no WP07/WP09 owned file was edited here.
