---
work_package_id: WP14
title: Packs workflow (built-in + internal lanes) + retired-dir `__pycache__` sweep
dependencies:
- WP01
- WP02
- WP03
- WP04
- WP05
- WP06
- WP07
requirement_refs:
- FR-011
planning_base_branch: feat/ci-pipeline-reinstatement
merge_target_branch: feat/ci-pipeline-reinstatement
branch_strategy: Planning artifacts for this mission were generated on feat/ci-pipeline-reinstatement. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/ci-pipeline-reinstatement unless the human explicitly redirects the landing branch.
subtasks:
- T072
- T073
- T074
- T075
- T076
history:
- at: '2026-09-07T00:00:00Z'
  actor: planner-priti
  action: created
agent_profile: implementer-ivan
authoritative_surface: .github/workflows/packs.yml
create_intent:
- .github/workflows/packs.yml
- tests/architectural/test_pycache_sweep.py
execution_mode: code_change
owned_files:
- .github/workflows/packs.yml
- tests/architectural/test_pycache_sweep.py
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile

Load your assigned agent profile via `/ad-hoc-profile-load <profile>` (role:
implementer) before anything else. Then read `plan.md` (TOPOLOGY T7), `spec.md` US6 +
FR-011, `work/ci-reinstatement/00-CONSOLIDATED-GROUNDING-BRIEF.md` §7 (packs two-lane
model), and the charter §"ATDD-First" + the CLAUDE.md "Template Source Location" +
"regen-assets gate" notes.

**Cluster gate:** claim after ALL FOUNDATION (WP01–WP06) + WP07 (router — for
`packs/**` trigger independence) are approved/done.

## Objective

A **dedicated packs workflow**, independent from the code CI, with two lanes:

- **Built-in lane** (`packs/built-in/**`, PUBLIC, ships in the wheel): regen-assets
  `--check` (source→generated fixture drift), DRG `regenerate-graph --check` (14
  fragments), pack-manifest freshness + authored-only guard, the `-m corpus` suite
  (`--cov=src/doctrine`), plugin build + `claude plugin validate --strict` (zero errors
  AND warnings).
- **Internal lane** (`packs/internal/**`, MAINTAINER-only, must NEVER ship): DRG-fragment
  validity + `refines`-edge resolution, `org-charter.yaml` required-id validation, and
  the **packaging-safety negative guard** (proves the internal pack never ships in the
  wheel).

Plus the **retired-dir `__pycache__` sweep** edge case: a retired test directory
lingering only as `__pycache__` orphans must NOT be re-collected; the orphans are
swept.

## Subtask guidance

### T072 — Red-first: `test_pycache_sweep.py` (SEPARATE first commit)

As your **first commit**, author `tests/architectural/test_pycache_sweep.py` that plants
a retired-dir `__pycache__` orphan (a `.pyc` with no live `.py`) and asserts the sweep
removes it / the router does not re-collect it. Run against base: red for the right
reason (sweep step/logic absent). This gives the orphan edge case a WP home.
**Collection-red lazy-load hygiene:** any import of a not-yet-existing module/helper is
lazy/in-test so the file still *collects* green on base — the red is a failed behavioral
assertion, never a collection/import error.

### T073 — Built-in lane

Author the built-in lane in `.github/workflows/packs.yml`: regen `--check`, DRG
`regenerate-graph --check`, pack-manifest freshness + authored-only guard, `-m corpus`
suite (`--cov=src/doctrine`), plugin build + `claude plugin validate --strict`. SHA-pin
all actions. Surface the regen diff with the exact remediation command (`spec-kitty
regen`) on drift — the spec edge case.

### T074 — Internal lane

Author the internal lane: DRG-fragment validity + `refines`-edge resolution,
`org-charter.yaml` required-id validation, and the packaging-safety **negative** guard
(`test_packaging_safety` — the internal pack never ships). Fire the internal lane on
`packs/internal/**`.

### T075 — Trigger independence + corpus floor

Wire `packs/**` (+ regen render paths + generated `.claude/`, `.agents/skills/`,
manifests) triggers; the code CI **excludes** `packs/**`/`tests/doctrine/**` so neither
drags the other (NFR-002 for packs-only PRs). Keep Gate-0 (`on.paths`) and Gate-1
(dorny `filters:`) in **lockstep** OR run on every PR with Gate-0 dropped (#3008
hazard). Keep the `-m corpus` **exit-5 floor** (zero corpus tests selected → loud fail).
**Declare `workflow_dispatch`; honor the `mode` input** (PR=fail-fast/short-circuit,
full=`if: always()`/run-all) in this packs workflow's own fail-fast/`needs` behavior per
FR-018/FR-019 — the mode-conditioned logic lives in this owned workflow file, verified
by WP11's `test_dual_mode_contract`.

### T076 — Sweep step + `introduced` row

Add the `__pycache__` sweep step to the workflow. Ensure `packs.yml` has its
`introduced` row (coordinated with WP01 — do NOT edit WP01's owned files; WP01
pre-registers).

## Branch Strategy

- Base/target: `feat/ci-pipeline-reinstatement`; worktree via `spec-kitty implement WP14`.
- Depends on all FOUNDATION + WP07 — claim after approved/done.
- Commit order: **T072 red-first FIRST**, then T073–T076.

## Definition of Done

- T072 red on base (evidence captured), green on final.
- `packs.yml` has both lanes (built-in + internal), `packs/**` trigger independence
  (Gate-0/Gate-1 lockstep), the corpus exit-5 floor, and the `__pycache__` sweep;
  SHA-pinned actions; `workflow_dispatch` present and the `mode` input honored (PR
  fail-fast vs full `if: always()`) in this workflow's own fail-fast/`needs` behavior
  (FR-018/FR-019) — verified by WP11's `test_dual_mode_contract`.
- A packs-only PR runs the packs workflow and no code shards; a src-only PR does not run
  packs.
- `introduced` row present (via WP01 coordination).
- **Targeted test surface**: `pytest tests/architectural/test_pycache_sweep.py -q` plus
  `pytest tests/architectural/test_pack_manifest_no_author_edit.py -m corpus -q` (corpus
  floor + manifest guard neighbours).

## Risks

- **regen-assets gate (memory)**: this workflow *validates* packs SOURCE; if the mission
  itself edits a `packs/` template SOURCE elsewhere, `spec-kitty regen` must be run and
  derived fixtures committed — surface the exact remediation command in the lane.
- **#3008 Gate-0/Gate-1 drift**: silent no-op if `on.paths` and dorny `filters:` drift —
  keep lockstep or drop Gate-0.
- **Internal pack ship-safety**: the packaging-safety negative guard is high-signal —
  never weaken it; the internal pack must never enter the wheel.
- **Governance-map lockstep**: `introduced` row is WP01-owned — coordinate, don't
  cross-edit.

## Reviewer guidance

- Confirm T072 red-on-base for the right reason.
- Confirm both lanes fire on the right paths and the corpus exit-5 floor is present.
- Confirm the `__pycache__` sweep actually removes a planted orphan.
- Confirm a packs-only PR runs 0 code shards (trigger independence).
