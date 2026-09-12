---
work_package_id: WP12
title: Sonar workflow (net-new, `introduced`)
dependencies:
- WP01
- WP02
- WP03
- WP04
- WP05
- WP06
- WP10
requirement_refs:
- C-008
- FR-010
planning_base_branch: feat/ci-pipeline-reinstatement
merge_target_branch: feat/ci-pipeline-reinstatement
branch_strategy: Planning artifacts for this mission were generated on feat/ci-pipeline-reinstatement. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/ci-pipeline-reinstatement unless the human explicitly redirects the landing branch.
subtasks:
- T061
- T062
- T063
- T064
- T065
history:
- at: '2026-09-07T00:00:00Z'
  actor: planner-priti
  action: created
agent_profile: implementer-ivan
authoritative_surface: .github/workflows/sonar.yml
create_intent:
- .github/workflows/sonar.yml
- tests/release/test_sonar_workflow.py
- kitty-specs/ci-pipeline-reinstatement-01M1X35E/sonar-identity-verification.md
execution_mode: code_change
owned_files:
- .github/workflows/sonar.yml
- sonar-project.properties
- tests/release/test_sonar_workflow.py
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile

Load your assigned agent profile via `/ad-hoc-profile-load <profile>` (role:
implementer) before anything else. Then read `plan.md` (TOPOLOGY T5), `spec.md` US5 +
FR-010 + C-008, `research.md` D6, `work/ci-reinstatement/00-CONSOLIDATED-GROUNDING-BRIEF.md`
§6 (Sonar), and the charter §"ATDD-First" + DIR-051 (SHA-pinned actions).

**Cluster gate:** claim after ALL FOUNDATION (WP01–WP06) + WP10 (coverage aggregation)
are approved/done. Sonar is **net-new** — it depends on WP01's `introduced` schema and
WP10's aggregated coverage.

## Objective

Restore SonarCloud scanning — fully removed at Convergence — as a **net-new**
workflow that aggregates the per-shard coverage artefacts and runs the scan **from the
spec-kitty repository**, **nightly/dispatch** initially (not per-PR), **fork-safe**
(skip-green without `SONAR_TOKEN`), with a documented no-rearchitecture path to per-PR.
The Sonar project identity is a **verify-before-wiring** task (post client-inversion
the `Priivacy-ai_spec-kitty` identity may be cross-org stale — C-008).

## Subtask guidance

### T061 — Red-first: `test_sonar_workflow.py` (SEPARATE first commit)

As your **first commit**, author `tests/release/test_sonar_workflow.py` asserting the
on-disk `sonar.yml` contract: it aggregates `*-reports`, skips-green without
`SONAR_TOKEN`, uses stock runners (`"blacksmith" not in text`), carries no
`SK_CI_TOKEN`, declares `workflow_dispatch`, and runs on `schedule`/`dispatch` (not the
PR merge-blocking `needs:`). Run against base: red for the right reason (`sonar.yml`
absent). Load the YAML lazily/in-test so the file collects.

> **Partition note:** the `introduced`-set *membership* assertion lives in WP01's
> `test_release_ci_ownership.py`; WP01 pre-registers `sonar.yml` in the `introduced`
> set (its T003/T005). This WP's red-first asserts the *workflow's own* fork-safe /
> aggregation / dispatch contract — no overlap with WP01's owned file.

### T062 — Verify Sonar identity BEFORE wiring

Verify the `Priivacy-ai_spec-kitty` / `priivacy-ai` SonarCloud project identity against
the **spec-kitty repository** (current target). Record the finding in
`kitty-specs/ci-pipeline-reinstatement-01M1X35E/sonar-identity-verification.md`: does
the project exist, does its org match, is a new key/org needed post client-inversion?
Do NOT wire the scan to gate anything until identity is confirmed. Reconcile
`sonar-project.properties` (projectKey/org) to the verified identity.

### T063 — Author `sonar.yml`

Create `.github/workflows/sonar.yml`: `on: schedule` (nightly) + `workflow_dispatch`;
download `*-reports` (+ previous-run fallback + cross-workflow by head-SHA), dedup
`coverage-*.xml` by basename, comma-join to `sonar.python.coverage.reportPaths` (no
merged file — Sonar merges server-side); run `SonarSource/sonarqube-scan-action` +
`sonarqube-quality-gate-action`, both **SHA-pinned** (DIR-051). Derive `projectVersion`
from `pyproject.toml`. Informational only (not in the PR merge-blocking `needs:`).
**Declare `workflow_dispatch`; honor the `mode` input** where it applies — Sonar is a
full-mode nightly/dispatch workflow, so it runs run-all (`if: always()`/no PR fail-fast
short-circuit) per FR-018/FR-019; the mode-conditioned behavior lives in this owned
workflow file, verified by WP11's `test_dual_mode_contract`.

### T064 — Fork-safe + per-PR path

Implement fork-safe degradation: without `SONAR_TOKEN`, the job **skips-green**
(advisory), never hard-fails (NFR-004 precedent: `skip_drift` on missing token).
Document (in the verification note) the no-rearchitecture path to promote Sonar from
nightly to per-PR (the artefact flow already supports it — SC-007).

### T065 — Register the `introduced` row + reconcile properties

Ensure `sonar.yml` has its `introduced` row (coordinated with WP01 — do NOT edit WP01's
owned map/test files; WP01 pre-registers). Reconcile `sonar-project.properties` to the
verified identity (T062). Keep stock-runner + no-`SK_CI_TOKEN` invariants.

## Branch Strategy

- Base/target: `feat/ci-pipeline-reinstatement`; worktree via `spec-kitty implement WP12`.
- Depends on all FOUNDATION + WP10 — claim after approved/done.
- Commit order: **T061 red-first FIRST**, then T062 (verify) BEFORE T063 (wire), then T064–T065.

## Definition of Done

- T061 red on base (evidence captured), green on final.
- The identity verification note records the confirmed/updated Sonar project identity
  BEFORE the scan is wired to gate anything (C-008).
- `sonar.yml` aggregates `*-reports`, runs nightly/dispatch, skips-green without
  `SONAR_TOKEN`, uses stock runners, SHA-pinned actions; a documented per-PR path.
- `sonar-project.properties` reconciled; `introduced` row present (via WP01 coordination).
- `sonar.yml` declares `workflow_dispatch` and honors the `mode` input (full-mode
  run-all `if: always()`, no PR fail-fast short-circuit) per FR-018/FR-019 — verified by
  WP11's `test_dual_mode_contract`.
- **Targeted test surface**: `pytest tests/release/test_sonar_workflow.py tests/release/test_release_ci_ownership.py tests/architectural/test_coverage_artefact_contract.py -q`.

## Risks

- **Identity-before-wiring (C-008)**: wiring the scan to a stale cross-org project
  silently mis-reports — verify FIRST (T062), gate nothing until confirmed.
- **Secret leakage (DIR-050)**: never echo `SONAR_TOKEN`; keep it repo-only; no
  `SK_CI_TOKEN` on this public job.
- **Governance-map lockstep**: the `introduced` row is WP01-owned — coordinate, don't
  cross-edit.
- **xunit gap**: the old job stripped `sonar.python.xunit.reportPath` — decide (note in
  the verification doc) whether to drop the property or aggregate + wire it; do not
  leave a dangling half-wired property.

## Reviewer guidance

- Confirm T061 red-on-base for the right reason.
- Confirm identity verification predates wiring (commit order) and the note is concrete
  (project exists? org matches?).
- Confirm fork-safe skip-green and SHA-pinned Sonar actions.
- Confirm no merge-blocking `needs:` on Sonar (informational nightly), and the per-PR
  path is documented, not implemented.
