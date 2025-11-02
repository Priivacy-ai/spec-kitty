---
work_package_id: "WP01"
subtasks:
  - "T001"
  - "T002"
title: "Release Validation Tooling"
phase: "Phase 1 - Foundations"
lane: "doing"
assignee: ""
agent: "codex"
shell_pid: "99987"
history:
  - timestamp: "2025-11-02T16:58:36Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---
*Path: [kitty-specs/002-lightweight-pypi-release/tasks/planned/WP01-release-validation-tooling.md](kitty-specs/002-lightweight-pypi-release/tasks/planned/WP01-release-validation-tooling.md)*


# Work Package Prompt: WP01 – Release Validation Tooling

## Objectives & Success Criteria

- Provide a single entry point (`python scripts/release/validate_release.py`) that verifies readiness in both branch and tag contexts.
- Ensure validator outputs clear remediation guidance for mismatched versions, missing changelog entries, or semantic regressions.
- Guarantee the validator is covered by automated tests to prevent regressions.

## Context & Constraints

- Follow `kitty-specs/002-lightweight-pypi-release/plan.md` for architectural expectations and FR-003/FR-007 gatekeeping requirements.
- Consult `research.md` for chosen tooling (`python -m build`, PyPA workflows) and `data-model.md` entities (ReleaseTag, ManagedSecret).
- The validator must support CI usage (non-interactive) and local maintainer workflows; avoid dependencies beyond stdlib + `packaging` if necessary.
- Do not read or print secrets; focus on filesystem inspection (`pyproject.toml`, `CHANGELOG.md`) and git metadata.

## Subtasks & Detailed Guidance

### Subtask T001 – Implement validator CLI
- **Purpose**: Enforce semantic alignment before releases, blocking bad tags or incomplete branches.
- **Steps**:
  1. Create `scripts/release/validate_release.py` as an executable module (`if __name__ == "__main__":`) with Typer or argparse CLI.
  2. Accept flags: `--tag` (optional), `--mode` (`tag` or `branch`), `--pyproject`, `--changelog`, and `--fail-on-missing-tag`.
  3. Parse `pyproject.toml` (use `tomllib` in Python 3.11 or `tomli`) to extract version and project metadata.
  4. Parse `CHANGELOG.md` to ensure a section exists for the target version and includes non-empty content.
  5. In `tag` mode, reconcile the provided tag or `GITHUB_REF` (`refs/tags/vX.Y.Z`), confirm formatting, and ensure it matches the metadata version.
  6. Detect regressions: compare release version to the most recent semantic tag reachable (`git tag --list 'v*'`) and ensure it is greater.
  7. In `branch` mode, skip tag requirements but ensure version bump is pending (version > latest tag) and changelog entry exists.
  8. Emit structured output: summary table to stdout, actionable errors to stderr; use exit code `0` success, `1` failure.
- **Files**:
  - `scripts/release/validate_release.py`
  - Optionally `scripts/release/__init__.py` (empty) to make the directory a package.
- **Parallel?**: No; script must exist before tests.
- **Notes**:
  - Handle shallow clones by allowing `--fetch-tags` flag or instructing workflow to fetch tags; degrade gracefully if history absent.
  - Keep dependencies minimal—prefer stdlib `subprocess` for git. If using `packaging.version`, add dependency to test requirements if needed.

### Subtask T002 – Add pytest coverage
- **Purpose**: Prevent regressions and codify acceptance criteria (missing changelog, mismatched tag, regression).
- **Steps**:
  1. Create `tests/release/test_validate_release.py`.
  2. Use `tmp_path` fixtures to generate sample `pyproject.toml`, `CHANGELOG.md`, and git repos (initialize with `git init`, commit, tag).
  3. Test success path for branch mode (version > existing tag) and tag mode (tag matches metadata).
  4. Test failure scenarios: mismatched tag/version, missing changelog section, version regression.
  5. Assert exit codes and stderr messages contain remediation hints.
  6. If factoring logic into helper functions, cover them directly to simplify CLI testing.
- **Files**:
  - `tests/release/test_validate_release.py`
  - `tests/release/__init__.py` (optional) for namespace cleanliness.
- **Parallel?**: No; depends on T001 implementation.
- **Notes**:
  - Use `subprocess.run` to call the script via `sys.executable` to exercise CLI entry point.
  - Ensure tests clean up temp git repos; rely on fixtures to isolate state.

## Test Strategy

- Run `python -m pytest tests/release/test_validate_release.py` locally and in CI.
- Provide sample invocation in docstring or README for maintainers: `python scripts/release/validate_release.py --mode branch`.

## Risks & Mitigations

- Test flakiness due to git operations → use disposable repos in temp directories and avoid network calls.
- Future Python version changes → keep CLI free of deprecated modules; rely on stdlib available in Actions runner.

## Definition of Done Checklist

- [ ] `scripts/release/validate_release.py` implements branch + tag validation with clear errors.
- [ ] Pytest suite covers success and failure paths.
- [ ] No secrets or tokens printed; CLI respects non-interactive environments.
- [ ] Documentation references updated CLI (handled in WP04).
- [ ] `tasks.md` updated with status change.

## Review Guidance

- Confirm validator enforces FR-003 (version bump) and FR-007 (actionable errors).
- Validate test coverage demonstrates key edge cases (missing changelog, regression).
- Ensure CLI behavior is deterministic with shallow clones and explicit `--tag`.

## Activity Log

- 2025-11-02T16:58:36Z – system – lane=planned – Prompt created.

---

### Updating Metadata When Changing Lanes

1. Capture your shell PID: `echo $$`.
2. Update frontmatter (`lane`, `assignee`, `agent`, `shell_pid`).
3. Append an entry to the **Activity Log** with timestamp, agent, lane, PID, and note.
4. Use `.kittify/scripts/bash/tasks-move-to-lane.sh 002-lightweight-pypi-release WP01 <lane>` to automate metadata updates.
5. Commit or stage changes to preserve audit history.
- 2025-11-02T17:12:46Z – codex – shell_pid=99987 – lane=doing – Started implementation
