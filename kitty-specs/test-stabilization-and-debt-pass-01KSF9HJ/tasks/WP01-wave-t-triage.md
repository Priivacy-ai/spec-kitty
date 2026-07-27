---
work_package_id: WP01
title: 'Wave T triage: cluster the 242 remaining failures from #1298 (FR-001)'
dependencies: []
requirement_refs:
- FR-001
planning_base_branch: kitty/mission-test-stabilization-and-debt-pass-01KSF9HJ
merge_target_branch: kitty/mission-test-stabilization-and-debt-pass-01KSF9HJ
branch_strategy: Planning artifacts for this mission were generated on kitty/mission-test-stabilization-and-debt-pass-01KSF9HJ. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into kitty/mission-test-stabilization-and-debt-pass-01KSF9HJ unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
agent: "claude:opus-4-7:reviewer-renata:reviewer"
shell_pid: "2059479"
history:
- by: claude
  at: '2026-05-25T14:00:00+00:00'
  action: generated
agent_profile: researcher-robbie
authoritative_surface: docs/01KSF9HJ-triage/
execution_mode: planning_artifact
mission_id: 01KSF9HJBFKRBC617JVHKZXNE2
mission_slug: test-stabilization-and-debt-pass-01KSF9HJ
owned_files:
- docs/01KSF9HJ-triage/triage.md
priority: P0
role: researcher
tags: []
---

## ⚡ Do This First: Load Agent Profile

Invoke `/ad-hoc-profile-load` with argument `researcher-robbie` before reading further. This WP is structured-research work: enumerate failures, cluster by hypothesised root cause, propose resolutions per cluster. Robbie's investigative discipline (literature-review pattern applied to test output) is the right fit.

## Objective

Produce `./triage.md (mission feature_dir)` — a comprehensive enumeration of every failure in the current `pytest tests/ -q` baseline (242 failures per the post-mission-122 audit), clustered by hypothesised root cause, with an explicit resolution per cluster (fix-here / sub-issue / accepted-skip-with-rationale).

This WP gates Wave T's remaining WPs (WP02, WP03, WP04). Without `triage.md`, those WPs cannot scope their work.

## Branch strategy

- Planning base branch: `kitty/mission-test-stabilization-and-debt-pass-01KSF9HJ`
- Merge target branch: `main`
- Execution: lane workspace allocated by `finalize-tasks`.

## Context

- [`spec.md`](../spec.md) FR-001 (the triage requirement) + spec C-004 (triage.md is a hard prerequisite for other WPs).
- [`plan.md`](../plan.md) Wave T section.
- [#1298](https://github.com/Priivacy-ai/spec-kitty/issues/1298) — the original DIR-013 issue + the post-mission triage comment at https://github.com/Priivacy-ai/spec-kitty/issues/1298#issuecomment-4531958466 (16 visible clusters identified in the post-mission audit).
- The post-mission-122 audit recorded these clusters (counts from the visible FAILED tail):
  - ``tests` subtree `sync/test_events.py`` — ~27
  - `tests/sync/test_lifecycle_readiness.py` — 2
  - `tests/sync/test_sync_e2e_integration.py` — 2
  - `tests/sync/tracker/test_origin_integration.py` — 1
  - `tests/tasks/test_planning_workflow_integration.py` — 9 (fixed in commit `64ddadc5f`)
  - ``tests` subtree `tasks/test_move_task_git_validation_unit.py`` — 1
  - ``tests` subtree `test_dashboard/test_scanner.py`` — 1
  - **Remaining ~190+ failures truncated by pytest's default summary output** — capture them with `-r f` or junitxml.

## Subtask details

### T001 — DIR-012 assign #1298 to HiC

```bash
unset GITHUB_TOKEN
gh issue edit 1298 --add-assignee stijn-dejongh --repo Priivacy-ai/spec-kitty
```

### T002 — Capture all FAILED lines into a file

The previous post-mission run truncated the FAILED list. Use junitxml output (or `pytest --tb=no -r f --no-header --color=no`) to enumerate every failure:

```bash
PWHEADLESS=1 .venv/bin/pytest tests/ --tb=no --no-summary -r f --color=no -q --junitxml=/tmp/01KSF9HJ-baseline.xml 2>&1 | tee /tmp/01KSF9HJ-baseline.txt
# Then extract from junitxml:
python3 -c "
import xml.etree.ElementTree as ET
tree = ET.parse('/tmp/01KSF9HJ-baseline.xml')
for tc in tree.iter('testcase'):
    if tc.find('failure') is not None or tc.find('error') is not None:
        print(f'{tc.get(\"classname\")}.{tc.get(\"name\")}')" > /tmp/01KSF9HJ-failed-tests.txt
wc -l /tmp/01KSF9HJ-failed-tests.txt
```

Expected output: a file with ~242 lines, one per failing test.

### T003 — Cluster failures by test-file + by root cause

For each failing test, group by parent file and by hypothesised root cause. Patterns to look for:
- **ModuleNotFoundError / ImportError** — likely a vendored-events or path drift
- **AssertionError on commit message / file content** — likely a contract drift
- **Sync/queue path failures** — likely the FR-002 cluster
- **Tolerance / approximate equality failures** — likely the FR-003 dashboard scanner pattern
- **Mock failures involving subprocess** — likely missing pytest markers or env

For each test file with ≥2 failures, run one failing test with `--tb=long` to confirm the root-cause hypothesis.

### T004 — Author `triage.md`

Create `./triage.md (mission feature_dir)` with this structure:

```markdown
# Triage — #1298 post-mission-122 baseline

**Baseline date**: <YYYY-MM-DD>
**Baseline commit**: <SHA>
**Total failures**: <N>
**Mission target (NFR-001)**: ≤ 75 failures post-mission.

## Cluster 1 — <name>
- **Test files**: `tests/...` (×N failures)
- **Sample failure**: `<test-id>` — quote the first line of the traceback
- **Hypothesised root cause**: <one paragraph>
- **Resolution**: one of:
  - `fix-here: WP-NN` (with link to the WP file)
  - `defer-to-sub-issue: #1298X` (with the sub-issue's intended title)
  - `accepted-skip-with-rationale: <pytest-mark + rationale>`

## Cluster 2 — <name>
...

## Resolution matrix

| Cluster | Failures | Resolution | Owner WP / Issue |
|---|---|---|---|
| Cluster 1 | N | fix-here | WP02 |
| Cluster 2 | M | defer | #1298a |
...

## Sub-issues to file (per FR-005)

- **#1298a**: <title>; <one-line root cause hypothesis>; <test count>
- **#1298b**: ...
```

## Definition of Done

- [ ] Issue #1298 assigned to HiC.
- [ ] `/tmp/01KSF9HJ-baseline.xml` exists with junitxml of the full suite.
- [ ] `triage.md` exists with one cluster section per failure-cluster + the Resolution matrix.
- [ ] Every cluster has a resolution that is one of `fix-here` / `defer-to-sub-issue` / `accepted-skip-with-rationale`.
- [ ] No cluster is unresolved ("TBD" / "investigating" / blank).
- [ ] Spec C-006 honoured: every `defer` row has a non-trivial root-cause hypothesis ("Failure too broad — defer" is not acceptable).

## Risks

- **Test environment drift**: the post-mission baseline may have shifted by a few failures since the audit. Document the new count in `triage.md` and use it as the WP04 reference number, NOT 242.
- **Junitxml file size**: 242 failures with full tracebacks may produce a multi-MB file. Strip to summary form for `triage.md` quoting.

## Reviewer guidance

1. Verify EVERY cluster has a resolution; reject if any row says "TBD".
2. Verify the count of `fix-here` failures lines up with WP02/WP03/WP04 capacity (≥70% of baseline per FR-005).
3. Spot-check 2 cluster hypotheses against the actual failing tests.

## Activity Log

- 2026-05-25T14:31:20Z – claude:opus-4-7:researcher-robbie:researcher – shell_pid=1852411 – Started implementation via action command
- 2026-05-25T15:19:32Z – claude:opus-4-7:researcher-robbie:researcher – shell_pid=1852411 – Triage complete: docs/01KSF9HJ-triage/triage.md buckets 249 failures across 13 clusters, assigns owners, names DIR-013 issue plan
- 2026-05-25T15:19:55Z – claude:opus-4-7:reviewer-renata:reviewer – shell_pid=2059479 – Started review via action command
- 2026-05-25T15:21:14Z – claude:opus-4-7:reviewer-renata:reviewer – shell_pid=2059479 – Review passed: 249 failures bucketed into 13 named clusters (C1-C12 + C99 sub-clusters); WP02 owns ~127 (events/sync drift), WP03 owns ~57 (surgical fixes), DIR-013 plan enumerates ~10 concrete per-cluster issues; ~74% fix-here ratio meets FR-005 >=70%. Minor arithmetic nit: cluster summary sums to 251 vs 249 (off-by-2, approximate counts in C99-g/j) but every failure category is assigned.
