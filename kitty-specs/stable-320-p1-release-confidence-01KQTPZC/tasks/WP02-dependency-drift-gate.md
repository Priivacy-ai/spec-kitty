---
work_package_id: WP02
title: Dependency Drift Gate
dependencies: []
requirement_refs:
- FR-005
- FR-006
- FR-007
- FR-008
- FR-009
- NFR-001
- NFR-003
- NFR-007
- C-001
- C-007
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-stable-320-p1-release-confidence-01KQTPZC
base_commit: f6cf56ed5300af79d85330e5a3f58e3f47aa7057
created_at: '2026-05-05T00:37:04.877625+00:00'
subtasks:
- T007
- T008
- T009
- T010
- T011
- T012
agent: "codex:gpt-5:python-pedro:reviewer"
shell_pid: "98482"
history: []
agent_profile: python-pedro
authoritative_surface: scripts/release/
execution_mode: code_change
model: ''
owned_files:
- scripts/release/check_shared_package_drift.py
- scripts/release/check_exact_install.py
- tests/release/test_check_shared_package_drift.py
- tests/release/test_exact_install_drift_guard.py
- .github/workflows/check-spec-kitty-events-alignment.yml
- .github/workflows/release-readiness.yml
- .github/workflows/ci-quality.yml
- .github/workflows/release.yml
role: implementer
tags: []
---

# Work Package Prompt: WP02 - Dependency Drift Gate

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `codex`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` and `authoritative_surface`.

---

## Objective

Verify #848 first, then either produce closure evidence or add a focused installed-vs-lock drift guard for `spec-kitty-events`. Do not loosen dependency constraints and do not widen beyond `spec-kitty-tracker` unless the same drift risk is proven and the fix remains small.

Implementation command: `spec-kitty agent action implement WP02 --agent <name>`

## Context

Existing release surfaces already include `uv lock --check`, shared package drift checks, exact wheel installability, and release-readiness jobs. The risk to prove or close is whether review/release evidence can still execute against an installed `spec-kitty-events` version that differs from `uv.lock`.

Branch strategy: planning artifacts were generated on `main`; completed changes must merge back into `main`. During implementation, Spec Kitty may allocate a worktree per computed lane from `lanes.json`; follow the workspace path provided by the implement command.

## Subtasks

### Subtask T007: Inventory existing drift and release gates

**Purpose**: Establish whether current CI already satisfies #848.

**Steps**:
1. Inspect `.github/workflows/ci-quality.yml` for `uv lock --check` and release jobs.
2. Inspect `.github/workflows/check-spec-kitty-events-alignment.yml`.
3. Inspect `.github/workflows/release-readiness.yml` and `.github/workflows/release.yml`.
4. Inspect `scripts/release/check_shared_package_drift.py` and `check_exact_install.py`.
5. Identify whether any gate compares the active installed version to `uv.lock`.

**Files**: owned workflow files and release scripts.

**Validation**: You can answer whether #848 is already fully covered before making code changes.

### Subtask T008: Capture current installed and lockfile evidence

**Purpose**: Produce current-state evidence for #848.

**Steps**:
1. Compare `importlib.metadata.version("spec-kitty-events")` in the active `uv run` environment with `uv.lock`.
2. Confirm `pyproject.toml` constraint contains the lockfile version.
3. Run `uv lock --check`.
4. Record command output for WP04.

**Files**: no source write required unless adding tests or docs in owned files.

**Validation**: Evidence names installed version, lockfile version, and constraint.

### Subtask T009: Decide closure-evidence versus guard implementation

**Purpose**: Avoid unnecessary code if current gates are already enough.

**Steps**:
1. If current gates check installed-vs-lock drift before evidence is trusted, prepare closure notes for #848.
2. If not, design a minimal guard in an existing release script.
3. Keep the guard local-only and deterministic.
4. Include `spec-kitty-events` at minimum.

**Files**: likely `scripts/release/check_shared_package_drift.py` or `check_exact_install.py`.

**Validation**: The selected path maps directly to FR-006 or FR-007.

### Subtask T010: Add or harden guard if needed

**Purpose**: Detect installed package drift reliably.

**Steps**:
1. Parse `uv.lock` for the resolved package version.
2. Read installed package version from active environment metadata.
3. Fail on mismatch with package name, installed version, lockfile version, and remediation.
4. Use `uv sync --extra test --extra lint` as the preferred remediation guidance.
5. Keep output suitable for CI logs.

**Files**: release scripts and corresponding tests only.

**Validation**: A simulated mismatch fails with the expected diagnostic.

### Subtask T011: Add regression tests

**Purpose**: Prove the guard or closure behavior.

**Steps**:
1. Add tests for lockfile extraction and installed-version matching if a guard is added.
2. Add mismatch tests with exact diagnostic assertions.
3. Keep tests under `tests/release/`.
4. Avoid network and hosted dependencies.

**Files**: `tests/release/test_check_shared_package_drift.py` and/or `tests/release/test_exact_install_drift_guard.py`.

**Validation**: `uv run pytest tests/release -q` covers the new behavior.

### Subtask T012: Update workflow invocation if needed

**Purpose**: Ensure the new guard actually runs where release evidence depends on it.

**Steps**:
1. Add the guard to the relevant GitHub Actions workflow only if existing invocation is insufficient.
2. Preserve release-readiness behavior and exact install smoke behavior.
3. Avoid broad CI restructuring.
4. Record workflow/job names for WP04 evidence.

**Files**: owned workflow files.

**Validation**: Workflow snippets call the guard with the same package set tested locally.

## Definition of Done

- #848 is either closed with concrete current-gate evidence or protected by a focused guard.
- `spec-kitty-events` is always included in verification.
- Mismatch diagnostics include installed version, lockfile version, and remediation.
- Tests cover any new code path.
- No dependency constraints are loosened as a substitute for drift detection.

## Risks

- Workflow-only checks may not cover local review evidence; verify the actual environment path.
- Release scripts may be used outside `uv run`; error messages must be clear.
- Adding `spec-kitty-tracker` can widen scope; include it only if the risk is equivalent and small.

## Reviewer Guidance

Reviewers should ask whether the final evidence is enough to close #848. If code was added, confirm the guard is actually invoked by the relevant release/review path.

## Activity Log

- 2026-05-05T00:37:06Z – codex:gpt-5:python-pedro:implementer – shell_pid=87130 – Assigned agent via action command
- 2026-05-05T00:45:36Z – codex:gpt-5:python-pedro:implementer – shell_pid=87130 – Ready for review: installed shared-package drift guard added and release tests passed
- 2026-05-05T00:47:38Z – codex:gpt-5:python-pedro:reviewer – shell_pid=98482 – Started review via action command
- 2026-05-05T00:52:15Z – codex:gpt-5:python-pedro:reviewer – shell_pid=98482 – Review passed: installed shared-package drift guard is implemented, invoked by release workflows, and release tests passed
