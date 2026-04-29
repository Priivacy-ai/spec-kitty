---
work_package_id: WP04
title: CI e2e-cross-cutting mypy availability (FR-008)
dependencies:
- WP01
requirement_refs:
- FR-008
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-charter-contract-cleanup-tranche-1-01KQATS4
base_commit: 44fb73f6824db9b7592ae63a1387f7374a8ae368
created_at: '2026-04-29T05:21:55.341407+00:00'
subtasks:
- T016
- T017
- T018
phase: Phase 2 - Charter CLI contract
agent: "claude:opus-4-7:reviewer-renata:reviewer"
shell_pid: "30920"
history:
- timestamp: '2026-04-28T20:35:00Z'
  lane: planned
  agent: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: implementer-ivan
authoritative_surface: .github/workflows/
execution_mode: code_change
owned_files:
- .github/workflows/ci-quality.yml
role: implementer
tags: []
---

# WP04 — CI `e2e-cross-cutting` mypy availability

## ⚡ Do This First: Load Agent Profile

Before reading anything else in this prompt, load the agent profile:

```
/ad-hoc-profile-load implementer-ivan
```

You are **implementer-ivan**: a general-purpose software implementation specialist. This WP is a one-line CI workflow change plus careful verification.

---

## Branch Strategy

- **Planning/base branch:** `main`
- **Final merge target:** `main`
- Execution worktrees are allocated per computed lane in `lanes.json` after `finalize-tasks`. This WP runs in the lane that owns `.github/workflows/`.
- Implementation command: `spec-kitty agent action implement WP04 --agent <name>`

## Objective

Make the `e2e-cross-cutting` CI job in `.github/workflows/ci-quality.yml` install the `lint` extra alongside `test` so `python -m mypy` is on PATH and `tests/cross_cutting/test_mypy_strict_mission_step_contracts.py` exercises its real contract instead of failing with `python -m mypy: not found`.

This closes spec FR-008 and is the resolved disposition of decision `01KQAVR8S1299R9N67BTFAD67Q`.

## Context

[`spec.md`](../spec.md) FR-008 captures the requirement. [`research.md`](../research.md) §R-006 records the policy decision (install in job, do not skip or fail-actionably). [`contracts/ci-job-mypy-availability.md`](../contracts/ci-job-mypy-availability.md) is the normative environment contract.

The `lint` extra in `pyproject.toml` already pins `mypy>=1.10.0`, plus type stubs and a few other lint tools. `mypy` is the only one the test in this job invokes.

The pre-mission install line lives at roughly line ~1768 of `.github/workflows/ci-quality.yml` (in the `e2e-cross-cutting` job's "Install Python dependencies" step):

```yaml
      - name: "[ENFORCED] Install Python dependencies"
        run: |
          python -m pip install --upgrade pip
          pip install -e .[test]
```

The post-mission shape is `pip install -e .[test,lint]`.

**FRs covered:** FR-008 · **NFRs:** NFR-002 (no other CI regressions) · **Decision:** `01KQAVR8S1299R9N67BTFAD67Q`

## Always-true rules

- Only the `e2e-cross-cutting` job is modified. Do not change `lint`, `fast-tests-*`, `slow-tests`, or any other job's install step.
- The change is additive: `[test]` → `[test,lint]`. Existing `[test]` extras remain in place.
- After the change, `tests/cross_cutting/test_mypy_strict_mission_step_contracts.py` must run and pass in the `e2e-cross-cutting` job.
- No other CI check that is currently green may regress.

---

## Subtask T016 — Modify the `e2e-cross-cutting` install step

**Purpose:** Land the one-line policy change.

**Steps:**

1. Open `.github/workflows/ci-quality.yml`.
2. Locate the `e2e-cross-cutting:` job (around line ~1731 in the pre-change file). Inside it, find the step:
   ```yaml
         - name: "[ENFORCED] Install Python dependencies"
           run: |
             python -m pip install --upgrade pip
             pip install -e .[test]
   ```
3. Change the second `pip install` line to:
   ```yaml
             pip install -e .[test,lint]
   ```
4. Save. Do not modify any other line in the file.

**Files to edit:**
- `.github/workflows/ci-quality.yml` (one-line change)

**Validation:**
- `git diff .github/workflows/ci-quality.yml` shows exactly one changed line, in the `e2e-cross-cutting` job.
- `yamllint .github/workflows/ci-quality.yml` (or whatever linter the repo uses) does not raise new findings on the modified region.

---

## Subtask T017 — Verify locally that the modified install line yields a working mypy

**Purpose:** Reproduce the CI install behaviour locally and confirm the strict-typing test passes against it.

**Steps:**

1. In a fresh virtualenv (or via `uv` with a clean cache), reproduce the CI install:
   ```bash
   python -m venv /tmp/wp04-mypy-check
   source /tmp/wp04-mypy-check/bin/activate
   pip install --upgrade pip
   pip install -e ".[test,lint]"
   python -m mypy --version
   python -m pytest tests/cross_cutting/test_mypy_strict_mission_step_contracts.py -q
   deactivate
   rm -rf /tmp/wp04-mypy-check
   ```
   - `python -m mypy --version` must succeed and report a 1.10+ version.
   - The pytest invocation must exit 0.
2. If the test fails for a reason **other than** mypy availability (e.g. a real strict-typing violation in `mission_step_contracts/executor.py`), that is a separate regression. Stop, escalate per C-003, and do not patch around it.
3. Capture terminal output for the PR description.

**Files to edit:** none (verification only).

**Validation:**
- Local reproduction confirms `mypy` is on PATH and the test passes.

---

## Subtask T018 — Confirm no other CI job regresses

**Purpose:** Catch any indirect dependency on the pre-change `[test]`-only install before merge.

**Steps:**

1. Read the `e2e-cross-cutting:` job's `needs:` list — confirm none of the upstream `fast-tests-*` jobs are dependent on this job *not* having the `lint` extra.
2. Search the workflow for any step that asserts the absence of the `lint` extra (e.g. a smoke test that `pip show mypy` fails). The brief implies none exists; confirm by `grep -n 'mypy' .github/workflows/ci-quality.yml` and reading the surrounding context. The existing references are to: a `lint` job (which already installs `lint`), a `mypy` advisory step, and the test we are fixing. None of these gate on mypy *absence*.
3. Confirm the new extras (`bandit`, `pip-audit`, `cyclonedx-bom`, type stubs) are not invoked by any test in `tests/e2e/` or `tests/cross_cutting/`. They will be installed but dormant.
4. Document the inspection in a brief PR-description note ("Verified no other CI job depends on the [test]-only install state in `e2e-cross-cutting`.").

**Files to edit:** none (inspection only).

**Validation:**
- Inspection notes captured for the PR description.

---

## Definition of Done

- [ ] T016 — `.github/workflows/ci-quality.yml` `e2e-cross-cutting` install line is `pip install -e .[test,lint]`.
- [ ] T017 — Local reproduction confirms `python -m mypy` is on PATH and the strict-typing executor test passes.
- [ ] T018 — Inspection confirms no other CI job depends on the pre-change install state.
- [ ] `git diff` for this WP touches only the one install line.

## Risks & Mitigations

| Risk | Mitigation |
|---|---|
| Adding the `lint` extra triggers a slow install on `e2e-cross-cutting` and bumps the timeout | The job's `timeout-minutes: 40` has plenty of headroom. The extras are small; install delta is on the order of seconds |
| `bandit` or `pip-audit` adds noise via dormant log lines | These are CLI tools, not pytest plugins. They are not invoked unless explicitly run |
| The strict-typing test fails because `mission_step_contracts/executor.py` has drifted | This is a real regression to escalate, not something to patch around. C-003 covers this case |
| YAML indentation gets accidentally broken when editing the run block | Use a known-safe editor that preserves YAML indentation; verify with `yamllint` (or equivalent) before committing |

## Reviewer Guidance

- Confirm the diff is one logical change (one install line).
- Confirm no other job's install step changed.
- If you have CI access, observe the `e2e-cross-cutting` job on the PR head: `python -m mypy --version` should print before the strict-typing test runs.

## Implementation Command

```bash
spec-kitty agent action implement WP04 --agent <name>
```

## Activity Log

- 2026-04-29T05:26:13Z – claude – shell_pid=29706 – lint extra added to e2e-cross-cutting; local repro: mypy strict executor test passes; no other job depends on [test]-only state
- 2026-04-29T05:26:41Z – claude:opus-4-7:reviewer-renata:reviewer – shell_pid=30920 – Started review via action command
