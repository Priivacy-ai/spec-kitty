---
work_package_id: WP11
title: Review Workflow Metadata & Dashboard Visibility
lane: "doing"
dependencies: [WP03]
requirement_refs:
- FR-020
- FR-021
- FR-022
- FR-023
- FR-024
- FR-025
planning_base_branch: feature/agent-profile-implementation
merge_target_branch: feature/agent-profile-implementation
branch_strategy: Planning artifacts for this feature were generated on feature/agent-profile-implementation. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feature/agent-profile-implementation unless the human explicitly redirects the landing branch.
base_branch: 058-mission-template-repository-refactor-WP03
base_commit: 3d6a08becdbddea3f8bfd1d9a57e73cea51488ad
created_at: '2026-03-28T07:11:41.071872+00:00'
subtasks:
- T049
- T050
- T051
- T052
- T053
- T054
phase: Phase 1 - New API Foundation
assignee: ''
agent: "opencode"
shell_pid: "26986"
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-03-28T06:30:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: WP added per HiC feedback on review workflow metadata gaps
agent_profile: implementer
---

# Work Package Prompt: WP11 – Review Workflow Metadata & Dashboard Visibility

## Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.
- **You must address all feedback** before your work is complete.
- **Mark as acknowledged**: When you understand the feedback and begin addressing it, update `review_status: acknowledged` in the frontmatter.

---

## Review Feedback

> **Populated by `/spec-kitty.review`**

*[This section is empty initially.]*

---

## Markdown Formatting

Wrap HTML/XML tags in backticks: `` `<div>` ``, `` `<script>` ``
Use language identifiers in code blocks: ````python`, ````bash`

---

## Objectives & Success Criteria

Six behavioural gaps in the review workflow need closing:

1. **`in_review` lane**: WPs enter `in_review` (not `in_progress`) when a reviewer claims them. The existing `for_review` lane means "waiting for a reviewer"; `in_review` means "review is active".
2. **Reviewer agent-profile**: The reviewer's agent-profile (e.g. `architect`) is recorded in WP frontmatter when the review starts.
3. **`role` field**: A `role` frontmatter field captures the role of the current actor (e.g. `architect`, `implementer`), populated alongside `agent_profile`.
4. **`agent` = tool**: The `agent` metadata field stores the LLM tool identifier (e.g. `claude-opus-4-6`), semantically distinct from the profile/role.
5. **`approved_by` field**: When a WP moves to `approved`, an `approved_by` field records the agent-profile (or HiC profile) that approved it.
6. **Dashboard visibility**: All new fields (`role`, `approved_by`, `in_review` lane) are visible in the dashboard kanban cards and WP detail pane.

**Success gate**: After implementation, running a review workflow on a WP should:
- Move it to `in_review` (visible as a lane on the dashboard)
- Populate `role`, `agent_profile`, and `agent` in frontmatter
- On approval, populate `approved_by` in frontmatter
- All fields visible when clicking a card in the dashboard

## Context & Constraints

- **Status model**: `src/specify_cli/status/models.py` defines `Lane` enum (currently 8 lanes). Adding `IN_REVIEW` makes it 9.
- **Transitions**: `src/specify_cli/status/transitions.py` defines `ALLOWED_TRANSITIONS` (currently 16+ pairs) and guards. New transitions needed for `in_review`.
- **Dashboard scanner**: `src/specify_cli/dashboard/scanner.py` extracts frontmatter fields for the UI.
- **Dashboard JS**: `src/specify_cli/dashboard/static/dashboard/dashboard.js` renders cards and detail modal.
- **Dashboard CSS**: `src/specify_cli/dashboard/static/dashboard/dashboard.css` has badge styles.
- **Workflow commands**: `spec-kitty agent workflow review` and `spec-kitty agent tasks move-task` handle lane transitions.
- **Constraint**: Backward compatible — existing WPs without the new fields should render gracefully (empty/missing fields shown as blank).

## Branch Strategy

- **Strategy**: workspace-per-WP
- **Planning base branch**: feature/agent-profile-implementation
- **Merge target branch**: feature/agent-profile-implementation

**Implementation command**: `spec-kitty implement WP11 --base WP03`

## Subtasks & Detailed Guidance

### Subtask T049 – Add `IN_REVIEW` lane to status model

- **Purpose**: Distinguish "waiting for reviewer" (`for_review`) from "review in progress" (`in_review`).
- **Steps**:
  1. In `src/specify_cli/status/models.py`, add `IN_REVIEW = "in_review"` to the `Lane` enum between `FOR_REVIEW` and `APPROVED`.
  2. Update the class docstring to say "9-lane" instead of "8-lane".
  3. In `src/specify_cli/status/transitions.py`:
     - Add `"in_review"` to the `_KNOWN_LANES` set (if one exists) or ensure it's recognized.
     - Add transitions to `ALLOWED_TRANSITIONS`:
       - `("for_review", "in_review")` — reviewer claims the WP
       - `("in_review", "approved")` — reviewer approves
       - `("in_review", "done")` — reviewer approves directly to done
       - `("in_review", "planned")` — reviewer requests changes
       - `("in_review", "in_progress")` — reviewer sends back for rework
       - `("in_review", "blocked")` — reviewer blocks the WP
       - `("in_review", "canceled")` — reviewer cancels
     - Add appropriate guards for the new transitions (reuse existing guard patterns).
  4. Add `"in_review"` as an alias resolution target if needed (check `resolve_lane_alias`).
  5. Update any lane-ordering or phase-mapping logic that assumes a fixed set of lanes.
- **Files**: `src/specify_cli/status/models.py`, `src/specify_cli/status/transitions.py`
- **Verify**: Existing tests in `tests/specify_cli/status/` still pass after adding the new lane.

### Subtask T050 – Add `role` and `approved_by` frontmatter fields

- **Purpose**: Record the role of the acting agent and provenance of approval.
- **Steps**:
  1. In `src/specify_cli/dashboard/scanner.py`, extract two new fields from frontmatter:
     ```python
     "role": frontmatter.get("role", ""),
     "approved_by": frontmatter.get("approved_by", ""),
     ```
     Add to both the normal return dict and the error/fallback return dict.
  2. In the workflow review command (find via `grep -r "workflow review" src/`), ensure that when a reviewer claims a WP:
     - `role` is set to the reviewer's agent-profile role (e.g. `architect`)
     - `agent_profile` is set to the reviewer's profile name
  3. In the `move-task --to approved` path, populate `approved_by` with the agent-profile of the approver.
  4. Clarify the `agent` field semantics: ensure it stores the tool/model name (e.g. `claude-opus-4-6`), not the profile name. Check existing code that sets `agent` and verify it already uses the tool name.
- **Files**: `src/specify_cli/dashboard/scanner.py`, workflow command files (find via grep), `move-task` command
- **Verify**: `pytest tests/specify_cli/dashboard/ -v` passes.

### Subtask T051 – Update workflow review to use `in_review` lane

- **Purpose**: When a reviewer claims a WP via `spec-kitty agent workflow review`, move to `in_review` instead of `in_progress`.
- **Steps**:
  1. Find the workflow review command implementation (grep for `workflow review` or `"review"` in CLI commands).
  2. Change the lane transition from `for_review → in_progress` to `for_review → in_review`.
  3. Ensure the reviewer's `agent_profile` and `role` are passed through to the frontmatter update.
  4. Ensure `agent` field is set to the tool identifier (model name), not the profile.
- **Files**: Workflow command implementation (likely in `src/specify_cli/cli/commands/agent/`)
- **Verify**: Running `spec-kitty agent workflow review WP## --agent <name>` moves WP to `in_review`.

### Subtask T052 – Update move-task to populate `approved_by`

- **Purpose**: When `move-task --to approved` is called, record who approved it.
- **Steps**:
  1. Find the `move-task` command implementation.
  2. When moving to `approved`, set `approved_by` in the WP frontmatter to the agent-profile (or actor identity) of the approver.
  3. The approver identity should come from `--agent` flag or be inferred from the current agent context.
  4. If the profile is passed (e.g. `--profile architect`), use that. Otherwise fall back to the `--agent` value.
- **Files**: `move-task` command implementation
- **Verify**: After `move-task WP## --to approved`, the WP frontmatter contains `approved_by: architect` (or equivalent).

### Subtask T053 – Dashboard: render `in_review` lane, `role`, and `approved_by`

- **Purpose**: Make all new metadata visible in the dashboard UI.
- **Steps**:
  1. In `dashboard.js`:
     - Add `in_review` as a recognized lane in the kanban board (new column between `for_review` and `approved`/`done`).
     - In `createCard()`, add a `role` badge if present:
       ```javascript
       ${task.role ? `<span class="badge role">${task.role}</span>` : ''}
       ```
     - In `showPromptModal()`, add `role` and `approved_by` to the metadata section:
       ```javascript
       if (task.role) metaItems.push(`<span>Role: ${escapeHtml(task.role)}</span>`);
       if (task.approved_by) metaItems.push(`<span>Approved by: ${escapeHtml(task.approved_by)}</span>`);
       ```
  2. In `dashboard.css`:
     - Add styles for the `in_review` lane column.
     - Add badge style for `.badge.role` (pick a distinct color, e.g. amber/orange).
  3. In `dashboard.js` lane formatting, add `in_review` → `"In Review"` display name.
- **Files**: `src/specify_cli/dashboard/static/dashboard/dashboard.js`, `src/specify_cli/dashboard/static/dashboard/dashboard.css`
- **Verify**: Start dashboard (`spec-kitty dashboard`), confirm `In Review` column appears, badges render, modal shows new fields.

### Subtask T054 – Update dashboard scanner for new fields

- **Purpose**: Ensure the scanner passes `role` and `approved_by` through to the JSON API.
- **Steps**:
  1. This may already be done in T050. Verify that `_process_wp_file()` returns `role` and `approved_by` in both the success and error paths.
  2. Add the fields to any API serialization or JSON response formatting if the scanner output goes through additional processing.
- **Files**: `src/specify_cli/dashboard/scanner.py`
- **Verify**: `pytest tests/specify_cli/dashboard/ -v` passes. Hit the dashboard API endpoint and confirm `role` and `approved_by` appear in the JSON response.

## Test Strategy

```bash
# Status model tests
PYTHONPATH=src pytest tests/specify_cli/status/ -v --timeout=60

# Dashboard tests
PYTHONPATH=src pytest tests/specify_cli/dashboard/ -v --timeout=60

# Smoke test: verify in_review lane is valid
PYTHONPATH=src python -c "
from specify_cli.status.models import Lane
assert hasattr(Lane, 'IN_REVIEW'), 'IN_REVIEW lane missing'
print(f'Lane.IN_REVIEW = {Lane.IN_REVIEW}')
"
```

## Risks & Mitigations

1. **Risk**: Adding a 9th lane breaks hardcoded lane lists in templates, tests, or dashboard. **Mitigation**: Grep for hardcoded lane lists and update them.
2. **Risk**: Existing `for_review → in_progress` transitions in workflow code may be used by other commands (not just review). **Mitigation**: Only change the review workflow path; keep `for_review → in_progress` as a valid transition for "send back for rework" scenarios.
3. **Risk**: Dashboard column layout breaks with 9 lanes. **Mitigation**: The kanban board should already handle dynamic lane counts; verify CSS doesn't assume a fixed number of columns.

## Review Guidance

- Verify `IN_REVIEW` lane is correctly positioned in the state machine with all necessary transitions
- Verify backward compatibility: WPs without `role`/`approved_by` fields render without errors
- Verify `agent` field semantics: should contain tool name, not profile name
- Verify dashboard renders the new lane as a visible column
- Run dashboard tests + status model tests

## Activity Log

- 2026-03-28T07:11:41Z – opencode – shell_pid=26986 – lane=doing – Assigned agent via workflow command
