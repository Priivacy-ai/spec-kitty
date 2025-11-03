---
work_package_id: "WP03"
subtasks:
  - "T005"
  - "T006"
title: "Release Readiness Guardrails"
phase: "Phase 2 - Quality Gates"
lane: "done"
assignee: ""
agent: "claude-sonnet-4.5"
shell_pid: "16185"
history:
  - timestamp: "2025-11-02T16:58:36Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---
*Path: [kitty-specs/002-lightweight-pypi-release/tasks/planned/WP03-release-readiness-guardrails.md](kitty-specs/002-lightweight-pypi-release/tasks/planned/WP03-release-readiness-guardrails.md)*


# Work Package Prompt: WP03 – Release Readiness Guardrails

## Objectives & Success Criteria

- Provide automated feedback on PRs targeting `main`, confirming readiness checklist items before merge.
- Block direct pushes to `main` by failing a guard workflow when commits skip PR review.
- Surface clear remediation instructions in workflow summaries/logs.

## Context & Constraints

- Tied to User Story 2 (readiness checks) and FR-002 in the feature spec.
- Reference `docs/releases/readiness-checklist.md` for the canonical steps to highlight in job summaries.
- Integrate with the validator built in WP01; reuse the CLI rather than duplicating logic.
- Guard workflows must not interfere with tag pushes or merges conducted via PR.

## Subtasks & Detailed Guidance

### Subtask T005 – Release readiness workflow
- **Purpose**: Automate pre-merge verification and provide maintainers immediate feedback.
- **Steps**:
  1. Create `.github/workflows/release-readiness.yml`.
  2. Triggers: `pull_request` (targeting `main`), `workflow_dispatch`, and optionally a nightly schedule to monitor drift.
  3. Jobs:
     - Checkout with `fetch-depth: 0` to access tags.
     - Setup Python 3.11; install dependencies (`pip install build tomli packaging pytest`).
     - Run `python -m pytest` (optional matrix for OS later).
     - Execute validator: `python scripts/release/validate_release.py --mode branch`.
     - Run `python -m build --wheel` to catch packaging issues early.
     - Emit summary via `$GITHUB_STEP_SUMMARY` listing outstanding checklist items if validator fails.
  4. Configure concurrency group (`pull_request-${{ github.ref }}`) to avoid duplicate runs.
  5. Add `if: github.event_name == 'workflow_dispatch'` block to accept manual tag input for dry runs.
- **Files**:
  - `.github/workflows/release-readiness.yml`
- **Parallel?**: Yes; can iterate alongside T006 once validator contracts finalize.
- **Notes**:
  - Use `continue-on-error: false` so failures block merges.
  - Consider caching pip packages for faster feedback.

### Subtask T006 – Protect main branch workflow
- **Purpose**: Detect and block direct pushes to `main`, guiding maintainers to branch protection rules.
- **Steps**:
  1. Create `.github/workflows/protect-main.yml`.
  2. Trigger on `push` to `refs/heads/main`.
  3. Job: run a short script (bash/python) that inspects `${{ github.event.head_commit.message }}` and `${{ github.event.head_commit.parents }}`:
     - Allow merge commits (`Merge pull request #`), rebase merges (multiple parents), and tag fast-forwards from release pipeline if needed.
     - Fail (`exit 1`) when commit history indicates a direct push (single parent, message lacking merge text).
  4. In failure case, emit `::error::` message referencing `docs/releases/readiness-checklist.md` and GitHub branch protection instructions.
  5. Optionally add a job summary reminding maintainers to create PRs.
- **Files**:
  - `.github/workflows/protect-main.yml`
- **Parallel?**: Yes; independent of T005 once validator is available.
- **Notes**:
  - Ensure workflow exits quickly to minimize CI cost.
  - Document acceptable merge strategies (merge commit, squash, rebase) in README/summary.

## Test Strategy

- Open a PR with a failing condition (e.g., missing changelog entry) and confirm readiness workflow blocks merge with clear message.
- Simulate direct push via `git push origin HEAD:main` in a sandbox and observe guard workflow failing.

## Risks & Mitigations

- Squash merges produce commit messages lacking "Merge pull request" → extend detection to allow commits authored by GitHub with Message `*` and multiple parents.
- False positives during repository initialization (first commit) → guard via `if: github.event.before != '0000000000000000000000000000000000000000'`.

## Definition of Done Checklist

- [ ] `.github/workflows/release-readiness.yml` runs on PRs and blocks merges when readiness criteria fail.
- [ ] Workflow surfaces checklist summary in job output.
- [ ] `.github/workflows/protect-main.yml` fails on direct pushes and references remediation guidance.
- [ ] Tag and release workflows remain unaffected.
- [ ] `tasks.md` updated with status change.

## Review Guidance

- Verify workflows reference validator CLI correctly (mode selection, tag handling).
- Ensure guard workflow condition matches allowed merge strategies.
- Confirm job summaries reference official readiness docs.

## Activity Log

- 2025-11-02T16:58:36Z – system – lane=planned – Prompt created.

---

### Updating Metadata When Changing Lanes

1. Capture your shell PID: `echo $$`.
2. Update frontmatter (`lane`, `assignee`, `agent`, `shell_pid`).
3. Append to the **Activity Log** with timestamp, lane, PID, and action.
4. Use `.kittify/scripts/bash/tasks-move-to-lane.sh 002-lightweight-pypi-release WP03 <lane>` to keep history consistent.
5. Commit or stage updates to preserve workflow audit trail.
- 2025-11-02T18:04:30Z – claude-sonnet-4.5 – shell_pid=13425 – lane=doing – Started implementation
- 2025-11-02T18:12:12Z – claude-sonnet-4.5 – shell_pid=13425 – lane=for_review – Ready for review
- 2025-11-02T22:51:25Z – claude-sonnet-4.5 – shell_pid=16185 – lane=done – Approved - Guardrails working
