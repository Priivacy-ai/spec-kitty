---
work_package_id: WP04
title: Canary local verification (scenarios 1, 2, 4 green)
dependencies:
- WP01
- WP02
- WP03
requirement_refs:
- NFR-003
- NFR-004
- C-001
- C-002
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T017
- T018
- T019
- T020
- T021
- T023
agent: claude
history:
- at: '2026-05-19T08:46:23Z'
  actor: spec-kitty.tasks
  note: Generated initial WP prompt.
agent_profile: python-pedro
authoritative_surface: kitty-specs/unblock-sync-identity-boundary-canary-01KRZJ07/canary-evidence/
execution_mode: planning_artifact
mission_slug: unblock-sync-identity-boundary-canary-01KRZJ07
model: claude-sonnet-4-6
owned_files:
- kitty-specs/unblock-sync-identity-boundary-canary-01KRZJ07/canary-evidence/**
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else in this prompt, load your agent profile:

```
/ad-hoc-profile-load python-pedro
```

The profile defines your identity, governance scope, and boundaries for this work. Apply it for the entire duration of this work package.

## Objective

Run the deployed-dev sync identity-boundary canary against a release-candidate build of `spec-kitty-cli` that bundles WP01–WP03 fixes, and prove that scenarios 1, 2, and 4 of `Priivacy-ai/spec-kitty-end-to-end-testing#42` turn green. Capture canary artifacts in this repo under `kitty-specs/unblock-sync-identity-boundary-canary-01KRZJ07/canary-evidence/`.

Scenario 3 may remain RED until `Priivacy-ai/spec-kitty-end-to-end-testing#43` lands; that is acceptable per spec constraint C-002 and does not gate this mission.

## Branch Strategy

- Planning base: `main`
- Final merge target: `main`
- **Depends on**: WP01, WP02, WP03 must all be approved and merged before WP04 starts.
- Execution worktree allocated per lane by `finalize-tasks`. Enter with `spec-kitty agent action implement WP04 --agent <name>`.

## Context

### Why this WP exists

The mission's done criterion (spec.md, C-002) is "canary scenarios 1, 2, 4 turn green on a re-run against the rc bump that bundles these fixes." The canary lives in a **sibling repo** (`Priivacy-ai/spec-kitty-end-to-end-testing`); this WP must run it locally and commit the evidence here. Decision `01KRZKFYKHE9V2PE5FJD0QCS69` (resolved: `final_wp_local_canary_verification`) chose this path over a post-merge operator step so the proof is part of the mission PR review.

### What scenarios you are validating

- **Scenario 1**: Fresh mission does not auto-create TeamSpace blockers (WP01 fix).
- **Scenario 2**: `sync now` connects on a fresh mission (WP01 fix).
- **Scenario 4**: `sync status --check` text output preserves the queue DB path verbatim (WP02 fix).
- **Scenario 3**: NOT in scope. Expected to remain RED until `#43` lands in the sibling repo.

The canary harness lives at `Priivacy-ai/spec-kitty-end-to-end-testing` and uses `pytest tests/identity_boundary/` with fixture-driven `DaemonOwnerRecord` injection.

## Subtasks

### T017 — Document sibling-repo canary checkout + invocation

**Purpose**: Create a runbook so reviewers can reproduce the canary outcome.

**Steps**:
1. Create `kitty-specs/unblock-sync-identity-boundary-canary-01KRZJ07/canary-evidence/RUNBOOK.md`.
2. The runbook MUST capture:
   - The exact sibling-repo URL: `https://github.com/Priivacy-ai/spec-kitty-end-to-end-testing.git`.
   - The exact `HEAD` commit of the sibling repo used for the canary run (record it after step T018).
   - The rc bump version of `spec-kitty-cli` used (e.g., `3.2.0rc14`).
   - The exact `pytest` invocation: `pytest tests/identity_boundary/ -v --capture=no`.
   - Environment notes: Python version, OS (`uname -a`), virtualenv path.
3. Reference [quickstart.md](../quickstart.md) Step 3 as the procedure source; do not duplicate it — runbook is the *record* of what was actually done, not the *manual*.

**Files**:
- `kitty-specs/unblock-sync-identity-boundary-canary-01KRZJ07/canary-evidence/RUNBOOK.md` (new; ~60 lines)

**Validation**:
- [ ] Runbook lists the actual sibling-repo HEAD commit, rc version, Python version, and OS used.

### T018 — Run the canary

**Purpose**: Generate fresh canary artifacts against the rc bump containing WP01–WP03.

**Steps**:
1. Confirm WP01, WP02, WP03 are merged into `main` of this repo and an rc bump (`3.2.0rc14` or later) has been built. If the rc bump does not yet exist, halt this WP and request the maintainer cut it.
2. Clone (or refresh) the sibling repo next to this repo:
   ```bash
   cd ..
   git clone https://github.com/Priivacy-ai/spec-kitty-end-to-end-testing.git || (cd spec-kitty-end-to-end-testing && git fetch && git checkout main && git pull)
   ```
3. Note the sibling repo's `HEAD` commit hash:
   ```bash
   (cd spec-kitty-end-to-end-testing && git rev-parse HEAD)
   ```
4. Create / refresh the canary venv and install both the canary's deps and the rc bump:
   ```bash
   cd spec-kitty-end-to-end-testing
   python3 -m venv .venv && source .venv/bin/activate
   pip install -e .
   pip install spec-kitty-cli==<rc-bump-version>
   ```
5. Run the canary, capturing the run log:
   ```bash
   pytest tests/identity_boundary/ -v --capture=no 2>&1 | tee /tmp/canary-run.log
   ```
6. Note the exit code (will be non-zero because scenario 3 is expected to fail; that is OK).

**Files**: none modified in this repo at this step.

**Validation**:
- [ ] `/tmp/canary-run.log` contains pytest output covering scenarios 1, 2, 3, 4.
- [ ] Sibling-repo `HEAD` commit captured for the runbook.

### T019 — Capture artifacts under `canary-evidence/`

**Purpose**: Commit the canary outcome into this repo for archival.

**Steps**:
1. Copy the canary's recorded artifacts:
   ```bash
   cp spec-kitty-end-to-end-testing/artifacts/sync_identity_boundary/<rc-bump>/latest.json \
      kitty-specs/unblock-sync-identity-boundary-canary-01KRZJ07/canary-evidence/latest.json
   cp spec-kitty-end-to-end-testing/artifacts/sync_identity_boundary/<rc-bump>/run-1.json \
      kitty-specs/unblock-sync-identity-boundary-canary-01KRZJ07/canary-evidence/run-1.json
   ```
2. Also copy the run log:
   ```bash
   cp /tmp/canary-run.log kitty-specs/unblock-sync-identity-boundary-canary-01KRZJ07/canary-evidence/canary-run.log
   ```
3. Verify each artifact is non-empty and contains the expected scenario summaries (scenarios 1, 2, 3, 4 named).

**Files**:
- `kitty-specs/unblock-sync-identity-boundary-canary-01KRZJ07/canary-evidence/latest.json` (new)
- `kitty-specs/unblock-sync-identity-boundary-canary-01KRZJ07/canary-evidence/run-1.json` (new)
- `kitty-specs/unblock-sync-identity-boundary-canary-01KRZJ07/canary-evidence/canary-run.log` (new)

**Validation**:
- [ ] All three artifacts present and non-empty.

### T020 — Verify scenarios 1, 2, 4 GREEN

**Purpose**: Read the captured artifacts and confirm the mission's done criterion is met.

**Steps**:
1. Inspect `canary-evidence/latest.json` (and `run-1.json`) for per-scenario results.
2. Assert:
   - Scenario 1 status == passed.
   - Scenario 2 status == passed.
   - Scenario 4 status == passed.
   - Scenario 3 status == failed (or skipped) is acceptable.
3. If scenario 1, 2, or 4 is RED:
   - Capture the failure detail from the run log.
   - Open a tracking issue describing the regression.
   - Halt this WP and route back to the relevant earlier WP (WP01 if 1/2 red; WP02 if 4 red).
4. If scenario 3 is GREEN: noteworthy — likely means `#43` landed in the meantime. Document it in the runbook but do not gate on it.

**Files**: none modified.

**Validation**:
- [ ] Scenarios 1, 2, 4: GREEN in captured artifacts.
- [ ] Scenario 3: red is acceptable; green is a bonus.

### T023 — Full pytest gate (NFR-004)

**Purpose**: Confirm the rc bump (carrying WP01+WP02+WP03 fixes) does not regress any pre-existing detector, sync, doctor, or unrelated test suite.

**Steps**:
1. From the canary's perspective the rc bump is opaque, so run the full pytest from a checkout of `Priivacy-ai/spec-kitty` at the same commit that produced the rc bump (sibling clone to the one used for the canary):
   ```bash
   cd ../spec-kitty
   git fetch && git checkout <rc-bump-tag-or-commit>
   pytest tests/ -q 2>&1 | tee /tmp/full-pytest.log
   ```
2. Note the exit code and the failure summary. Acceptable outcomes:
   - **0 failures** → ideal.
   - **Failures only in test files that exist on `main` of `spec-kitty` and also failed on the same commit before this mission landed**: per charter, open a GitHub issue first (cite command + summary + evidence the failure is pre-existing). Continue.
   - **Any new failure attributable to WP01/WP02/WP03 changes**: HALT, route back to the responsible WP, document in a GH issue, do NOT mark this WP done.
3. Copy `/tmp/full-pytest.log` (or at least its tail) into `kitty-specs/unblock-sync-identity-boundary-canary-01KRZJ07/canary-evidence/full-pytest.log`.

**Files**:
- `kitty-specs/unblock-sync-identity-boundary-canary-01KRZJ07/canary-evidence/full-pytest.log` (new)

**Validation**:
- [ ] Log captured under `canary-evidence/`.
- [ ] Exit code 0, OR all failures pre-existing AND a GitHub issue opened for them.

### T021 — Record final outcome summary

**Purpose**: Make the canary outcome readable directly from the PR description without unzipping artifacts.

**Steps**:
1. Append a short summary section to `canary-evidence/RUNBOOK.md`:
   - rc bump version used
   - sibling-repo HEAD commit
   - per-scenario results (1/2/3/4)
   - pytest exit code
   - any remediation notes for a red scenario 3 (i.e., a pointer back to `#43`)
2. This summary will be quoted in the WP04 PR description.

**Files**:
- `kitty-specs/unblock-sync-identity-boundary-canary-01KRZJ07/canary-evidence/RUNBOOK.md` (modify; append outcome section)

**Validation**:
- [ ] RUNBOOK.md ends with a clear outcome summary keyed by scenario number.

## Definition of Done

- [ ] All six subtasks complete; each `[ ]` above checked.
- [ ] Spec-side NFR-003 satisfied (scenarios 1, 2, 4 green in captured artifacts).
- [ ] Spec-side NFR-004 satisfied (full `pytest tests/` shows 0 new failures, or any failures pre-existing and tracked).
- [ ] Constraint C-001 respected (no commits to the sibling repo).
- [ ] Constraint C-002 honored (scenario 3 red is acceptable).
- [ ] `canary-evidence/` contains `latest.json`, `run-1.json`, `canary-run.log`, `RUNBOOK.md`, `full-pytest.log`.

## Reviewer Guidance

- Open the runbook first; confirm the sibling-repo HEAD commit, rc version, and OS are recorded.
- Open `latest.json` / `run-1.json`; confirm scenarios 1, 2, 4 are GREEN.
- Confirm no commits or changes leaked into the sibling repo's working tree (review the PR diff: only files under `kitty-specs/unblock-sync-identity-boundary-canary-01KRZJ07/canary-evidence/` should be added).
- If scenario 3 is RED: confirm the runbook explicitly attributes it to `Priivacy-ai/spec-kitty-end-to-end-testing#43` (not to a regression in this mission).
