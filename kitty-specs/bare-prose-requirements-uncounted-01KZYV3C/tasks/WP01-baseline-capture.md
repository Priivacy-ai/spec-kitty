---
work_package_id: "WP01"
subtasks:
  - "T001"
  - "T002"
  - "T003"
  - "T004"
  - "T005"
  - "T006"
  - "T007"
title: "Baseline Capture & Pre-Existing Failure Audit"
task_type: "implement"
phase: "Phase 0 - Baseline"
execution_mode: "planning_artifact"
owned_files: []
authoritative_surface: "kitty-specs/bare-prose-requirements-uncounted-01KZYV3C/"
create_intent: []
agent_profile: ""
role: ""
agent: ""
model: ""
assignee: ""
shell_pid: ""
history:
  - at: "2026-08-14T02:50:21Z"
    actor: "system"
    action: "Prompt authored during tasks-authoring pass (not run via /spec-kitty.tasks)"
---

# Work Package Prompt: WP01 – Baseline Capture & Pre-Existing Failure Audit

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the
frontmatter (or any user-defined profile). If none is specified, run
`spec-kitty agent profile list` and select the best match for an `implement`-typed WP
whose surface is planning/verification, not production code.

---

## Objectives & Success Criteria

Establish this mission's real RED/GREEN starting point **before any code change lands**,
per plan.md's "Baseline Capture on `ab15225ea`" section — verbatim, not the
CLI-computed `planning_base_branch`. Done means: a recorded red-test-ID list from
`ab15225ea`, an explicit diff verdict against issue #3284's ~23-known-red-on-`main`
set, and (if any newly-discovered pre-existing failure exists) an upstream GitHub issue
filed before it is treated as accepted baseline — per the charter's Pre-existing
Failure Reporting Rule.

## Context & Constraints

- Read `.kittify/charter/charter.md`'s Pre-existing Failure Reporting Rule and the
  "⚠️ Test-run baseline-red gotcha" section of `CLAUDE.md` before starting.
- Read plan.md's "Baseline Capture on `ab15225ea`" section in full — it contains the
  exact procedure and the falsifiability note (PLAN-VERIFY-003) about verifying
  commit shapes live, not from a stale count.
- **This mission's real baseline is `ab15225ea`** (tip of
  `origin/op/3394-requirement-citation-scope`), NOT `main`. `spec-kitty plan --json`'s
  own `planning_base_branch` field is wrong for this mission's topology (documented
  tooling gap — see `tracer-tooling-friction.md`'s existing entry). Do not trust that
  CLI-reported value for this one mission.
- No code changes happen in this WP. The deliverable is a recorded finding.

## Branch Strategy

- **Strategy**: Planning/verification artifact — no code branch created by this WP
  itself; work happens in a disposable worktree at a fixed commit.
- **Planning base branch**: `pr/bare-prose-requirements-uncounted` (this mission's own
  planning-artifact home — do not confuse with the `ab15225ea` ATDD/baseline ref below).
- **Merge target branch**: `pr/bare-prose-requirements-uncounted`.

> These "Branch Strategy" fields describe where THIS MISSION's planning artifacts live
> (git topology), a different concept from the `ab15225ea` ref this WP's own procedure
> tests against. Do not conflate them — see plan.md's "ATDD-First" section for why.

## Subtasks & Detailed Guidance

### Subtask T001 – Create the baseline worktree

- **Purpose**: Isolate the `ab15225ea` checkout from the mission's own working tree.
- **Steps**: `git worktree add /tmp/baseline-ab15225ea ab15225ea` (or an isolated clone
  if a worktree is inconvenient in this environment).
- **Files**: None (git metadata only).
- **Parallel?**: No.

### Subtask T002 – Install dependencies

- **Purpose**: A fresh checkout needs its own environment.
- **Steps**: `cd /tmp/baseline-ab15225ea && uv sync --all-extras`.
- **Notes**: Do not skip `--all-extras` — some targeted test surface directories
  depend on optional extras.

### Subtask T003 – Run the Targeted Test Surface

- **Purpose**: Measure the actual baseline red set, not an assumed one.
- **Steps**:
```bash
PWHEADLESS=1 .venv/bin/python -m pytest \
  tests/specify_cli/test_requirement_mapping.py \
  tests/specify_cli/test_requirement_mapping_coord_surface.py \
  tests/next/ tests/specify_cli/next/ tests/runtime/ \
  -n 8 --dist loadfile -q
```
- **Notes**: **NEVER `-n auto`** — deadlocks this 24-core box (repo-wide documented
  trap, `CLAUDE.md`). Always `-n 8 --dist loadfile`.

### Subtask T004 – Record the red set

- **Purpose**: Durable evidence for the #3284 diff and for later WPs' own RED
  verification to compare against.
- **Steps**: Capture the red count and every failing test ID verbatim (copy the pytest
  summary output).

### Subtask T005 – Diff against issue #3284

- **Purpose**: Plan.md explicitly forbids assuming the `ab15225ea` red set matches
  #3284's `main`-measured ~23-known-red set — `ab15225ea` carries #3395's unreviewed
  ~863-line rewrite that `main` does not.
- **Steps**: Compare T004's list against #3284's named tests by ID. State explicitly,
  in `tracer-tooling-friction.md` (append, do not recreate), whether the sets match. If
  they diverge, name the delta.

### Subtask T006 – File upstream issues for new pre-existing reds

- **Purpose**: Charter's Pre-existing Failure Reporting Rule — binding, not advisory.
- **Steps**: For any red test not already covered by a filed, referenced upstream
  issue, open a new GitHub issue with the command run, the failure summary, and why it
  is believed pre-existing (not introduced by this mission's not-yet-started changes),
  **before** treating it as accepted baseline.

### Subtask T007 – Verify commit shape between `ab15225ea` and current tip

- **Purpose**: PLAN-VERIFY-003's falsifiability note — the durable claim is "zero
  implementation-shaped commits above `ab15225ea`," not a fixed hash/count (which goes
  stale with every planning commit).
- **Steps**: `git log --oneline ab15225ea..<current-tip>` and confirm every commit is
  `spec(...)` / `fix(spec: ...)` / `reviews(spec: ...)` / `plan(...)` / meta-add shaped.

## Test Strategy

- No new automated test is added by this WP. The "test" is the recorded pytest run
  itself (T003/T004), which every later ATDD-first WP re-verifies RED against.

## Risks & Mitigations

- Misattributing a genuinely new regression as "pre-existing baseline" — mitigated by
  the explicit #3284-diff requirement (T005) and the mandatory upstream filing (T006).

## Review Guidance

- Confirm the recorded red set, the #3284 diff verdict, and any filed issue links are
  all present in `tracer-tooling-friction.md` before approving.
- Confirm `-n 8 --dist loadfile` was used, not `-n auto`.

## Activity Log

> **CRITICAL**: Activity log entries MUST be in chronological order (oldest first,
> newest last). Append new entries at the end.

- 2026-08-14T02:50:21Z – system – Prompt created.
