---
work_package_id: WP05
title: Retirement scrub — re-derive dorny groups + `--cov` targets against live src
dependencies:
- WP02
requirement_refs:
- FR-013
planning_base_branch: feat/ci-pipeline-reinstatement
merge_target_branch: feat/ci-pipeline-reinstatement
branch_strategy: Planning artifacts for this mission were generated on feat/ci-pipeline-reinstatement. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/ci-pipeline-reinstatement unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-ci-pipeline-reinstatement-01M1X35E
base_commit: 1ef1e770da3c5c4c3b852deb355af35dc0ab405b
created_at: '2026-09-07T11:21:29.383123+00:00'
subtasks:
- T023
- T024
- T025
- T026
- T027
history:
- at: '2026-09-07T00:00:00Z'
  actor: planner-priti
  action: created
agent_profile: python-pedro
authoritative_surface: tests/architectural/test_retirement_scrub.py
create_intent:
- tests/architectural/test_retirement_scrub.py
- tests/release/ci_retirement_scrub.json
execution_mode: code_change
owned_files:
- tests/architectural/test_retirement_scrub.py
- tests/release/ci_retirement_scrub.json
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile

Load your assigned agent profile via `/ad-hoc-profile-load <profile>` (role:
implementer) before anything else. Then read `plan.md` (FOUNDATION F5 — scrub half),
`work/ci-reinstatement/PARAMOUNT-constraints.md` (P1), `contracts/p1-census-oracle.md`,
and the charter §"ATDD-First" + SO#5.

## Objective

The **P1 retirement scrub**: re-derive the dorny filter groups and `--cov=<module>`
targets against **live `src/**`** so that **no CI job selects a test over dead/retired
code** (sync/saas/delivery/emit/websockets or any `never-restore` surface). Every
exclusion is **census-authorized** by the WP02 oracle — no bare labels
(`dependencies: [WP02]`). This scrub is sequenced **before** the `--durations`
shard-freeze (WP08): the shard boundaries must be measured on the *scrubbed* live
basis, never re-frozen after (plan §"Why this order"). This WP produces the scrub
**data artefact** + its enforcing test; the actual dorny groups land in the router
(WP07) and registry (WP08), which consume this artefact.

## Subtask guidance

### T023 — Red-first: `test_retirement_scrub.py` (SEPARATE first commit)

As your **first commit**, author `tests/architectural/test_retirement_scrub.py`
asserting: no entry in the scrub artefact maps a filter group or a `--cov` target to a
retired subsystem or a `never-restore` surface, and every exclusion cites a WP02
census entry. Run against base and confirm red for the right reason (the scrub
artefact `ci_retirement_scrub.json` does not yet exist / is empty). Include a
non-vacuity floor: the test fails if the scrub set is empty.

### T024 — Re-derive dorny filter groups against live `src/**`

Enumerate the live `src/**` module set and derive the filter groups that map to it.
**Drop** every group that maps to a retired dir (sync/saas/delivery/emit/websockets)
or a `never-restore` row. Cross-check each candidate against
`test_no_retired_subsystems` + the census. This is the P1 paramount filter in action:
default posture is EXCLUDE; a group earns inclusion only by covering live, imported
code.

### T025 — Re-derive `--cov=<module>` targets

Re-derive the dotted `--cov=<module>` targets against live `src/**`. Exclude any
census-`dead` surface from the coverage denominator (the E3 invariant). Preserve the
dotted form (never path form) and `relative_files=true` (C-005) — those already exist
in `pyproject.toml [tool.coverage.run]`; do not regress them.

### T026 — Persist the scrub result artefact

Write `tests/release/ci_retirement_scrub.json`: per group `{group, roots[], cov_target,
census_evidence}` and the excluded-surface list with per-exclusion census evidence.
This is the single data source WP07 (router groups) and WP08 (registry) consume — they
derive from it, they do not re-scrub.

### T027 — Assert enforcement allowlists stay always-on

Add a test asserting the enforcement allowlists
(`test_no_dead_symbols`/`test_no_dead_modules`/`test_no_retired_subsystems`) are NOT
scrubbed/excluded — they remain always-on blocking gates (C-006 boundary). The scrub
removes *dead-code behavioral tests*, never the allowlists that enforce leanness itself.

## Branch Strategy

- Base/target: `feat/ci-pipeline-reinstatement`; worktree via `spec-kitty implement WP05`.
- Depends on WP02 (census) — claim only after WP02 approved/done.
- Commit order: **T023 red-first FIRST**, then T024–T027.

## Definition of Done

- T023 red on base (evidence captured), green on final.
- `ci_retirement_scrub.json` maps no group/`--cov` to a retired/never-restore surface
  and every exclusion cites census evidence — asserted by `test_retirement_scrub.py`
  (no group/`--cov` resolves to a retired subsystem; every exclusion carries a WP02
  census ref), verified by running that test, not eyeballed off the JSON.
- Enforcement allowlists proven always-on by the T027 assertion in
  `test_retirement_scrub.py` (the three `test_no_*` allowlists are NOT in the exclusion
  set).
- Non-vacuity floor present (empty scrub set reds) — asserted in `test_retirement_scrub.py`.
- **Targeted test surface** (the tests that gate this DoD): `pytest tests/architectural/test_retirement_scrub.py tests/architectural/test_no_retired_subsystems.py -q`.

## Risks

- **Scrub-last footgun**: this MUST land before WP08's shard-freeze; if durations are
  measured on an unscrubbed basis the freeze is invalid and needs a re-freeze loop.
- **Over-scrub (false-positive)**: dropping a live group because its importer-count is
  0 but it is dynamically reached. The WP02 known-live guard is the defense — route
  every drop through the census.
- **C-005 regression**: do not switch `--cov` to path form or drop `relative_files` —
  Sonar/aggregators cannot resolve multi-`<source>` coverage.

## Reviewer guidance

- Confirm T023 red-on-base for the right reason.
- Spot-check that at least one retired-dir group is dropped WITH census evidence, and
  that no live group was dropped on a bare importer-0 (verify dynamic reach).
- Confirm the artefact is the single source WP07/WP08 will consume (no divergent
  second scrub).
