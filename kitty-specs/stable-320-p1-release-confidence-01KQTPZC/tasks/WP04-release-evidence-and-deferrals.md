---
work_package_id: WP04
title: Release Evidence And Deferrals
dependencies:
- WP03
requirement_refs:
- FR-014
- FR-015
- NFR-001
- NFR-005
- C-002
- C-003
- C-004
- C-005
- C-006
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T019
- T020
- T021
- T022
- T023
- T024
agent: "codex:gpt-5:curator-carla:reviewer"
history: []
agent_profile: curator-carla
authoritative_surface: kitty-specs/stable-320-p1-release-confidence-01KQTPZC/
execution_mode: planning_artifact
model: ''
owned_files:
- kitty-specs/stable-320-p1-release-confidence-01KQTPZC/release-evidence.md
- kitty-specs/stable-320-p1-release-confidence-01KQTPZC/deferrals.md
- kitty-specs/stable-320-p1-release-confidence-01KQTPZC/issue-closure-notes.md
role: curator
tags: []
shell_pid: "15276"
---

# Work Package Prompt: WP04 - Release Evidence And Deferrals

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `curator-carla`
- **Role**: `curator`
- **Agent/tool**: `codex`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` and `authoritative_surface`.

---

## Objective

Compile the final release-confidence evidence for #966, #848, both smoke runs, current ruff status, #971 included/deferred status, and P2/P3 deferrals. This WP makes the mission reviewable without requiring reviewers to reconstruct prior command output.

Implementation command: `spec-kitty agent action implement WP04 --agent <name>`

## Context

This WP depends on WP03 so smoke evidence is available. It is a planning-artifact WP and should not modify source code. If missing source-level evidence is discovered, send the work back to the relevant WP instead of patching outside owned files.

Branch strategy: planning artifacts were generated on `main`; completed changes must merge back into `main`. During implementation, Spec Kitty may allocate a worktree per computed lane from `lanes.json`; follow the workspace path provided by the implement command.

## Subtasks

### Subtask T019: Compile #966 evidence

**Purpose**: Document task-board progress semantics fix evidence.

**Steps**:
1. Summarize the implemented semantics.
2. Link relevant tests and commands.
3. Include approved-only, done-only, mixed, and empty state coverage.
4. Note any JSON compatibility decision.

**Files**: `release-evidence.md`, `issue-closure-notes.md`.

**Validation**: A reviewer can decide whether #966 is closable from the evidence.

### Subtask T020: Compile #848 evidence

**Purpose**: Document dependency drift closure or guard evidence.

**Steps**:
1. Summarize whether current gates were sufficient or a guard was added.
2. Include installed `spec-kitty-events` version and `uv.lock` version evidence.
3. Include remediation command for mismatch cases.
4. Draft closure notes or remaining issue notes.

**Files**: `release-evidence.md`, `issue-closure-notes.md`.

**Validation**: Evidence is suitable for closing or updating #848.

### Subtask T021: Incorporate smoke evidence

**Purpose**: Bring WP03 local-only and SaaS-enabled smoke results into release evidence.

**Steps**:
1. Cite `smoke-evidence.md`.
2. Summarize pass/fail/blocker outcomes.
3. List linked issues or blockers for any failures.
4. Confirm `SPEC_KITTY_ENABLE_SAAS_SYNC=1` use on hosted/sync commands.

**Files**: `release-evidence.md`.

**Validation**: Both smoke requirements are clearly satisfied or blocked with rationale.

### Subtask T022: Record #971 included/deferred decision

**Purpose**: Avoid ambiguity around the strict mypy gate.

**Steps**:
1. If #971 was included, record the WP and strict mypy command evidence.
2. If #971 remains deferred, link #971 and explain why it stayed outside this mission.
3. Ensure `deferrals.md` has the final decision.
4. Ensure `release-evidence.md` mirrors the decision.

**Files**: `deferrals.md`, `release-evidence.md`.

**Validation**: #971 is explicitly included or deferred.

### Subtask T023: Record P2/P3 deferrals

**Purpose**: Keep release-scope boundaries explicit.

**Steps**:
1. Record P2 deferrals: #662, #630, #629, #631 unless touched and fixed.
2. Record P3 deferrals: #771, #726, #728, #729, #644, #740, #323, #306, #303, #317, #973 unless a current repro blocks stable.
3. Record #869 as stale unless a fresh repro appeared.
4. Record prior P0 issues #967, #904, #968, #964 as fixed by PR #972 unless a fresh regression appeared.

**Files**: `deferrals.md`, `release-evidence.md`.

**Validation**: The deferral artifact matches the mission spec.

### Subtask T024: Run final evidence commands and summarize

**Purpose**: Produce final acceptance evidence.

**Steps**:
1. Run `uv run ruff check src tests`.
2. Include focused commands from WP01 and WP02.
3. Include strict mypy only if #971 was included.
4. Summarize pass/fail status and residual risks.

**Files**: `release-evidence.md`.

**Validation**: Final evidence includes current ruff status and all required release-confidence outcomes.

## Definition of Done

- `release-evidence.md` exists and covers #966, #848, both smoke runs, ruff, and #971.
- `deferrals.md` exists and records #971 plus all listed P2/P3 deferrals.
- `issue-closure-notes.md` exists with notes suitable for #966/#848 updates.
- No source files are modified by this WP.

## Risks

- Evidence can become stale if commands are rerun later; include dates and exact commands.
- Do not overstate smoke success if hosted auth prevented coverage.
- Do not silently include #971 without a separate scoped decision.

## Reviewer Guidance

Reviewers should verify that evidence is concrete, current, and scoped. Check that deferrals are explicit rather than vague and that any stable-release blocker is named directly.

## Activity Log

- 2026-05-05T01:02:50Z – codex:gpt-5:curator-carla:curator – shell_pid=12275 – Started implementation via action command
- 2026-05-05T01:04:37Z – codex:gpt-5:curator-carla:curator – shell_pid=12275 – Ready for review: release evidence, deferrals, and issue closure notes compiled
- 2026-05-05T01:04:54Z – codex:gpt-5:curator-carla:reviewer – shell_pid=15276 – Started review via action command
- 2026-05-05T01:05:39Z – codex:gpt-5:curator-carla:reviewer – shell_pid=15276 – Review passed: release evidence, #971 decision, P2/P3 deferrals, issue closure notes, and ruff status are concrete and scoped
