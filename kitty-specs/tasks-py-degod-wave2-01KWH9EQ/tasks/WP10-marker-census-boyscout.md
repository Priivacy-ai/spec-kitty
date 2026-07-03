---
work_package_id: WP10
title: 'Boyscout: marker census + #2034 refresh'
dependencies:
- WP09
requirement_refs:
- FR-009
- FR-010
tracker_refs: []
planning_base_branch: degod-follow-ups
merge_target_branch: degod-follow-ups
branch_strategy: Planning artifacts for this mission were generated on degod-follow-ups. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into degod-follow-ups unless the human explicitly redirects the landing branch.
subtasks:
- T044
- T045
- T046
phase: Phase 4 - Closure
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "991308"
history:
- at: '2026-07-02T12:53:55Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: tests/architectural/
create_intent:
- tests/architectural/test_tasks_domain_gate_visibility.py
execution_mode: code_change
model: ''
owned_files:
- tests/architectural/test_tasks_domain_gate_visibility.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP10 – Boyscout: marker census + #2034 refresh

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter (or any user-defined profile), and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

---

## ⚠️ IMPORTANT: Review Feedback

Check the `review_ref` field in the event log before starting; address all feedback.

---

## Objectives & Success Criteria

Deliver the domain-matched #2034 slice (FR-009/FR-010, SC-005) with non-gameable
evidence: a committed marker-census artifact proving every tasks-domain test file
(including everything this mission added) is selected by at least one CI gate; a
standing assertion that no tasks-domain path enters the orphan-ratchet baseline; and the
drafted final #2034 refresh.

Pre-plan squad ground truth: the domain was FULLY gate-visible on the mission base (all
34 files carry selected markers; the baseline holds 4 orphan paths, none tasks-domain) —
this WP's job is EVIDENCE + PERMANENCE + the mission's new files, not mass fixing.

## Context & Constraints

- Spec FR-009 (the committed glob — verbatim): `tests/tasks/**`,
  `tests/specify_cli/cli/commands/agent/test_tasks*`, plus every test file this mission
  added (byte-freeze suite, `test_tasks_command_surface.py`, `test_tasks_shared_seam.py`,
  and THIS WP's gate-visibility test).
- `research.md` D8 (census facts) + the #2034/#2283/#2295/#2296/#2297 relationships in
  `issue-matrix.md` and `post-spec-squad-findings.md` (Plan-time carry-forwards).
- C-006: absorbing a tasks-domain path into `_gate_coverage_baseline.json` via
  `--update-baseline` is a violation, not a fix.
- CI gate model: markers selected by `ci-quality.yml` (`fast`, `slow`, `git_repo`,
  `integration`, `architectural`, `timing`, path-based e2e) — read the workflow, don't
  guess.

## Branch Strategy

- **Strategy**: {{branch_strategy}}
- **Planning base branch**: degod-follow-ups
- **Merge target branch**: degod-follow-ups

## Subtasks & Detailed Guidance

### Subtask T044 – Marker-census artifact

- **Steps**:
  1. Enumerate every file matching the FR-009 glob on the CURRENT tree.
  2. For each: extract its effective markers (pytestmark + any conftest auto-marking — `tests/charter/`-style `pytest_collection_modifyitems` does not apply here, but verify no local conftest interferes) and name the ci-quality.yml gate expression(s) that select it.
  3. Write `kitty-specs/tasks-py-degod-wave2-01KWH9EQ/marker-census.md`: a table `file | markers | selecting gate(s)` + a zero-unselected summary line + the generation command so it's reproducible.
  4. If ANY file is unselected (including mission-added ones): fix its markers (explicit pytestmark matching its true cost profile — `fast` for in-process CliRunner tests) and re-census.
- **Files**: the census artifact (mission dir — commits to the coordination branch on coord-topology missions; verify with `spec-kitty agent tasks status` where artifacts land).

### Subtask T045 – Baseline-growth assertion

- **Purpose**: Make the FR-009 prohibition PERMANENT, not a one-time check.
- **Steps**: New `tests/architectural/test_tasks_domain_gate_visibility.py`: load
  `tests/architectural/_gate_coverage_baseline.json`, assert no `orphan_files` entry
  matches the FR-009 glob (hardcode the glob patterns with a comment citing FR-009 and
  the mission). Include a theater test (a synthetic baseline dict containing a
  tasks-domain path → assertion fires). Markers per the architectural-directory
  convention (gate-visible itself — add it to the census).
- **Files**: new test (~60–90 lines).

### Subtask T046 – Draft the final #2034 comment + issue-matrix verdicts

- **Steps**:
  1. Draft (do NOT post — the orchestrator posts at mission review) the final #2034
     comment into the Activity Log or a `#2034-refresh-draft.md` in the mission dir:
     final census numbers, what FR-009 delivered for the tasks domain, #2283 named as
     the 3-cause structural parent (this mission closed cause (a) for its domain only),
     #2296/#2297 as the blocked/structural repo-wide paths.
  2. Update `issue-matrix.md`: #2034 slice → evidence ref updated (still
     `deferred-with-followup` upstream); #2306 → `fixed` with the WP05 evidence; #2116 →
     evidence updated with the final shim state.
- **Files**: mission-dir artifacts (coordination-branch write path).

## Test Strategy

```bash
PWHEADLESS=1 pytest tests/architectural/test_tasks_domain_gate_visibility.py tests/architectural/test_gate_coverage.py -q
PWHEADLESS=1 pytest tests/specify_cli/cli/commands/agent/ tests/tasks/ -q -p no:cacheprovider   # census subjects still green
python -m mypy --strict tests/architectural/test_tasks_domain_gate_visibility.py
```

## Risks & Mitigations

- **Definition-shrinking** (the squad's gameability finding): the glob is FIXED by
  FR-009 — the census must cover exactly it, no reinterpretation.
- **Coord-topology write path**: mission-dir artifacts land on the coordination branch —
  Wave 1's close friction; commit in the right checkout.
- **Marker guessing**: read `ci-quality.yml` gate expressions; name the exact expression
  per file in the census.

## Review Guidance

- Reproduce the census with the recorded command; diff against the artifact.
- Verify the theater test in T045 actually fires on the synthetic violation.
- Verify the #2034 draft's numbers match the census artifact.

## Activity Log

> Append at the END, chronological. Format: `- YYYY-MM-DDTHH:MM:SSZ – agent_id – <action>`

- 2026-07-02T12:53:55Z – system – Prompt created.
- 2026-07-02T20:13:48Z – claude:fable:python-pedro:implementer – shell_pid=974282 – Assigned agent via action command
- 2026-07-02T21:05:00Z – claude:fable:python-pedro:implementer – T044: FR-009 marker census generated via the canonical selection model (_gate_coverage): 43 files / 754 tests / ZERO unselected; no marker fixes needed (conftest adds skip-markers only, no selection interference). Artifact: marker-census.md (commit e133615c8).
- 2026-07-02T21:05:30Z – claude:fable:python-pedro:implementer – T045: tests/architectural/test_tasks_domain_gate_visibility.py added in lane-j (commit 09c4d1d36): baseline-growth assertion (FR-009 glob hardcoded) + synthetic theater test driving the same check function; architectural+fast markers; mypy --strict + ruff clean; 2 passed.
- 2026-07-02T21:06:00Z – claude:fable:python-pedro:implementer – T046: 2034-refresh-draft.md drafted (NOT posted — orchestrator posts at mission review); issue-matrix.md updated: #2306→fixed (WP05 evidence), #2116 final shim state (1206 LOC, 5 families relocated), #2034 evidence→FR-009 delivered + FR-010 draft ready.
- 2026-07-02T21:07:00Z – claude:fable:python-pedro:implementer – Validation: architectural trio (gate_visibility + gate_coverage + tasks_command_surface) 32 passed; parity sanity (byte suite + CLI contract + 6 seam suites) 236 passed. WP10 → for_review.
- 2026-07-02T20:25:18Z – claude:fable:python-pedro:implementer – shell_pid=974282 – T044 census: 43 files/754 tests, ZERO unselected, no marker fixes (marker-census.md, e133615c8). T045 standing assertion tests/architectural/test_tasks_domain_gate_visibility.py (lane 09c4d1d36): baseline-growth prohibition + theater test, mypy --strict + ruff clean. T046 draft 2034-refresh-draft.md (not posted) + issue-matrix: #2306 fixed, #2116/#2034 evidence finalized (4b6fce57a). Validation: architectural trio 32 passed; parity byte+contract+seams 236 passed.
- 2026-07-02T20:26:23Z – claude:opus:reviewer-renata:reviewer – shell_pid=991308 – Started review via action command
- 2026-07-02T20:33:30Z – user – shell_pid=991308 – Review passed: census reproduces byte-for-byte via embedded _gate_coverage script (43 files/754 tests/0 unselected, table identical); glob==FR-009 exactly (15 tests-tasks + 26 agent/test_tasks* + 2 architectural, all 9 mission-added files inside); 3 gate exprs verified vs ci-quality.yml; baseline-growth test drives the REAL tasks_domain_orphans fn (real+theater), FR-009 glob hardcoded w/ anti-shrink comment, architectural+fast, in census; baseline 4 orphans none tasks-domain, _gate_coverage_baseline.json untouched by all mission commits (no --update-baseline); draft carries numbers + #2283 3-cause + cause(a) domain-only + #2296/#2297, NOT posted; #2306 fixed (untrusted_path_containment 5 passed), #2116 tasks.py==1206 LOC exact; mypy --strict + ruff clean; lane commit = 1 test file only.
