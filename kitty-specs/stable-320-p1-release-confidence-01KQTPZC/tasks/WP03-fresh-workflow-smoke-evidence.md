---
work_package_id: WP03
title: Fresh Workflow Smoke Evidence
dependencies:
- WP01
- WP02
requirement_refs:
- FR-010
- FR-011
- FR-012
- FR-013
- NFR-001
- NFR-002
- NFR-004
- C-001
- C-002
- C-003
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T013
- T014
- T015
- T016
- T017
- T018
agent: "codex:gpt-5:python-pedro:reviewer"
history: []
agent_profile: python-pedro
authoritative_surface: kitty-specs/stable-320-p1-release-confidence-01KQTPZC/
execution_mode: planning_artifact
model: ''
owned_files:
- kitty-specs/stable-320-p1-release-confidence-01KQTPZC/smoke-evidence.md
- kitty-specs/stable-320-p1-release-confidence-01KQTPZC/smoke-artifacts/**
role: implementer
tags: []
shell_pid: "10130"
---

# Work Package Prompt: WP03 - Fresh Workflow Smoke Evidence

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `codex`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` and `authoritative_surface`.

---

## Objective

Run and document one fresh local-only lifecycle smoke and one SaaS-enabled lifecycle smoke for the current prerelease line. Every hosted auth, tracker, SaaS, or sync command on this computer must set `SPEC_KITTY_ENABLE_SAAS_SYNC=1`.

Implementation command: `spec-kitty agent action implement WP03 --agent <name>`

## Context

This WP depends on WP01 and WP02 because the smoke should run after the release-confidence fixes or evidence gates are in place. The WP is evidence-focused and owns mission-local smoke artifacts only. If a smoke uncovers a narrow code failure, record it and ask whether to widen or file/link an issue unless the fix is clearly within already-owned files from an earlier WP.

Branch strategy: planning artifacts were generated on `main`; completed changes must merge back into `main`. During implementation, Spec Kitty may allocate a worktree per computed lane from `lanes.json`; follow the workspace path provided by the implement command.

## Subtasks

### Subtask T013: Prepare disposable smoke workspace

**Purpose**: Keep smoke execution isolated from committed mission artifacts.

**Steps**:
1. Create a temporary workspace outside the mission artifact directory.
2. Record the path in `smoke-evidence.md`.
3. Confirm the CLI version under test from `uv run spec-kitty --version`.
4. Ensure the local-only smoke path has no hosted auth, tracker, SaaS, or sync dependency.

**Files**: write evidence only under `kitty-specs/stable-320-p1-release-confidence-01KQTPZC/smoke-evidence.md` and optional `smoke-artifacts/**`.

**Validation**: Smoke evidence names the workspace and version under test.

### Subtask T014: Run local-only lifecycle smoke

**Purpose**: Prove the core CLI lifecycle works without hosted services.

**Steps**:
1. Run init or project setup in the disposable workspace.
2. Run specify.
3. Run plan.
4. Run tasks.
5. Run implement/review or a bounded equivalent fixture path.
6. Run merge.
7. Record PR-ready branch evidence or explain the bounded equivalent used.

**Files**: evidence files only.

**Validation**: `smoke-evidence.md` includes commands, exit statuses, and key output summaries.

### Subtask T015: Prepare SaaS-enabled lifecycle smoke path

**Purpose**: Build a SaaS-enabled smoke that mirrors the local lifecycle where practical, rather than reducing the smoke to status/help probes.

**Steps**:
1. Start from the local lifecycle sequence in T014: setup, specify, plan, tasks, implement/review or bounded equivalent fixture path, merge, and PR-ready evidence.
2. For each lifecycle step, identify whether the current CLI surface has a hosted auth, tracker, SaaS, or sync path that can be exercised safely.
3. Prefix every hosted auth, tracker, SaaS, or sync command with `SPEC_KITTY_ENABLE_SAAS_SYNC=1`.
4. Treat auth/status/help probes only as prerequisites that establish readiness or explain blockers; they do not satisfy the SaaS-enabled lifecycle smoke by themselves.
5. Do not claim tracker rollout gating exists.
6. Record any auth prerequisite, hosted limitation, or blocker precisely before running the smoke.

**Files**: evidence files only.

**Validation**: The planned SaaS-enabled command sequence maps back to the local lifecycle steps, and every hosted/sync command in the evidence shows the env var.

### Subtask T016: Run SaaS-enabled lifecycle smoke

**Purpose**: Prove the current prerelease lifecycle works with SaaS-enabled paths where practical on this machine's dev deployment path.

**Steps**:
1. Run the SaaS-enabled lifecycle sequence prepared in T015, mirroring setup, specify, plan, tasks, implement/review or bounded equivalent fixture path, merge, and PR-ready evidence where current CLI surfaces allow it.
2. Use `SPEC_KITTY_ENABLE_SAAS_SYNC=1` on every command path that touches hosted auth, tracker, SaaS, or sync behavior.
3. Capture success, expected unauthenticated status, or actionable failure for each lifecycle step.
4. If a lifecycle step cannot safely exercise SaaS, record the exact reason and the prerequisite probe output separately.
5. Avoid destructive hosted operations.
6. Preserve logs or summarized outputs in `smoke-artifacts/**` if useful.

**Files**: evidence files only.

**Validation**: Evidence distinguishes lifecycle coverage from prerequisite probes, and any missing SaaS lifecycle coverage is explicitly marked as expected auth limitation, issue-linked failure, or stable-release blocker.

### Subtask T017: Handle failures according to the contract

**Purpose**: Ensure failures are not buried.

**Steps**:
1. For each failure, decide whether it is narrow enough to fix in this mission.
2. If not fixed, file or reference a GitHub issue.
3. If it blocks stable, mark that explicitly.
4. If it is a bounded non-blocking limitation, explain why.

**Files**: evidence files only.

**Validation**: No smoke failure appears without issue/fix/blocker/defer status.

### Subtask T018: Finalize smoke evidence for WP04

**Purpose**: Make release evidence compilation straightforward.

**Steps**:
1. Summarize local-only result.
2. Summarize SaaS-enabled result.
3. List exact command sequence.
4. List artifacts and issue references.

**Files**: `smoke-evidence.md` and optional `smoke-artifacts/**`.

**Validation**: WP04 can cite the smoke evidence without rerunning commands.

## Definition of Done

- Local-only smoke is run and documented.
- SaaS-enabled smoke mirrors the local lifecycle where practical and is documented with required env var use.
- Status/help/auth probes are recorded only as prerequisites, not as standalone proof of SaaS lifecycle success.
- Any failure has a fix, linked issue, or stable-release blocker decision.
- Evidence is committed in mission-owned files.

## Risks

- Hosted auth state may block parts of the SaaS smoke; record this as evidence rather than hiding it.
- Smoke commands may mutate temporary repos; keep them outside committed mission artifacts.
- Do not run destructive hosted operations.

## Reviewer Guidance

Reviewers should check that the local-only smoke truly avoids hosted dependencies, that the SaaS-enabled smoke mirrors the lifecycle where practical, and that every hosted/sync command uses `SPEC_KITTY_ENABLE_SAAS_SYNC=1`. Reject evidence that only runs status/help/auth probes and claims full SaaS smoke success.

## Activity Log

- 2026-05-05T00:52:56Z – codex:gpt-5:python-pedro:implementer – shell_pid=957 – Started implementation via action command
- 2026-05-05T01:01:16Z – codex:gpt-5:python-pedro:implementer – shell_pid=957 – Ready for review: local and SaaS-enabled lifecycle smoke evidence recorded
- 2026-05-05T01:01:35Z – codex:gpt-5:python-pedro:reviewer – shell_pid=10130 – Started review via action command
- 2026-05-05T01:02:31Z – codex:gpt-5:python-pedro:reviewer – shell_pid=10130 – Review passed: local and SaaS-enabled lifecycle smoke evidence mirrors setup/specify/plan/tasks/implement-review/merge with required sync env and documented limitations
