---
work_package_id: WP11
title: Dashboard JS Terminology Clean Break
dependencies: "[]"
requirement_refs:
- FR-014
planning_base_branch: feature/agent-profile-implementation-rebased
merge_target_branch: feature/agent-profile-implementation-rebased
branch_strategy: Planning artifacts for this mission were generated on feature/agent-profile-implementation-rebased. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feature/agent-profile-implementation-rebased unless the human explicitly redirects the landing branch.
subtasks:
- T039
- T040
- T041
- T042
- T048
agent: "opencode"
shell_pid: "254171"
role: "reviewer"
history:
- at: '2026-04-03T20:00:00Z'
  actor: human
  action: WP added from WP08 architectural review follow-up item 2 (cleanup)
agent_profile: python-implementer
authoritative_surface: src/specify_cli/dashboard/
execution_mode: code_change
lane: planned
owned_files:
- src/specify_cli/dashboard/static/dashboard/dashboard.js
- src/specify_cli/dashboard/handlers/router.py
- tests/test_dashboard/test_missions_handler.py
task_type: cleanup
---

# Work Package Prompt: WP11 -- Dashboard JS Terminology Clean Break

## Objectives & Success Criteria

- Remove dead `data.features` / `data.active_feature_id` fallbacks from `dashboard.js`
- Switch JS fetch URL from `/api/features` to `/api/missions`
- Evaluate removing the `/api/features` route alias from the router
- All dashboard tests pass, Playwright verification if applicable
- Terminology Canon compliance: no `feature*` aliases remain in active dashboard codepaths

## Context & Constraints

- **Origin**: WP08 architectural review finding T029
- **Task type**: Cleanup — no new functionality, just removing dead code and terminology debt
- The backend (`missions.py` handler) only returns `missions` and `active_mission_id` keys — the JS `||` fallbacks for `data.features` / `data.active_feature_id` are dead code
- The router currently serves both `/api/missions` and `/api/features` — the latter is a backward-compat alias
- **Terminology Canon**: `feature*` aliases in active codepaths violate the hard-break policy
- **Depends on WP09**: WP09 modifies `dashboard.js` for in-review lane and card identity; this cleanup should come after to avoid merge conflicts

## Branch Strategy

- **Planning base branch**: `feature/agent-profile-implementation-rebased`
- **Merge target branch**: `feature/agent-profile-implementation-rebased`

**Implementation command**: `spec-kitty implement WP11 --base WP09`

## Subtasks & Detailed Guidance

### Subtask T039 -- Remove JS data.features fallbacks

- **Purpose**: Eliminate dead fallback code that masks potential bugs.
- **Steps**:
  1. In `dashboard.js`, find all instances of `data.features` and `data.active_feature_id`
  2. Replace `data.missions || data.features` with `data.missions`
  3. Replace `data.active_mission_id || data.active_feature_id` with `data.active_mission_id`
  4. Search for any other `feature` references in the JS that are dead code
- **Files**: `dashboard.js`

### Subtask T040 -- Switch fetch URL to /api/missions

- **Purpose**: Use the canonical endpoint, not the backward-compat alias.
- **Steps**:
  1. In `dashboard.js`, find the `fetch('/api/features')` call (approximately line 1241)
  2. Change to `fetch('/api/missions')`
  3. Verify no other fetch calls use the old URL
- **Files**: `dashboard.js`

### Subtask T041 -- Evaluate and optionally remove /api/features route alias

- **Purpose**: Consider removing the backward-compat route alias.
- **Steps**:
  1. In `router.py`, check if `/api/features` is still registered as an alias
  2. If no external consumers depend on it (check docs, SaaS client, etc.), remove the alias
  3. If uncertain, leave the alias but add a deprecation comment with a removal date
- **Files**: `router.py`
- **Decision point**: If there are external consumers, keep the alias and document. If not, remove it.

### Subtask T042 -- Verify dashboard functionality

- **Purpose**: Confirm no regressions.
- **Steps**:
  1. Run dashboard handler tests: `pytest tests/test_dashboard/ -v`
  2. If Playwright tests exist: `PWHEADLESS=1 pytest tests/dashboard/ -v`
  3. Verify mission list loads correctly with the updated fetch URL

### Subtask T048 -- Escape user-controlled text in createCard() badges

- **Purpose**: Fix pre-existing XSS debt in `createCard()`. Card badges render `task.agent`, `task.agent_profile`, and `task.role` without `escapeHtml()`, while the detail modal correctly escapes the same values. Identified during WP09 review.
- **Steps**:
  1. In `dashboard.js`, locate the `createCard()` function
  2. Wrap each badge value with `escapeHtml()`:
     - `${escapeHtml(task.agent)}` instead of `${task.agent}`
     - `${escapeHtml(task.agent_profile)}` instead of `${task.agent_profile}`
     - `${escapeHtml(task.role)}` instead of `${task.role}`
  3. Verify `escapeHtml()` is already defined in the file (it is — used by `showPromptModal`)
- **Files**: `dashboard.js`

## Risks & Mitigations

- External tools or scripts may call `/api/features` directly. Grep the codebase for `/api/features` references before removing the route.
- The SaaS client may depend on the `/api/features` endpoint. Check `tracker/saas_client.py` and any API documentation.

## Review Guidance

- Verify no `feature*` terminology remains in active JS codepaths (backward-compat aliases in Python backend are a separate concern for WP12)
- Verify the fetch URL change doesn't break the dashboard
- If the route alias is kept, verify there's a deprecation comment

## Activity Log

- 2026-04-03T20:00:00Z -- human -- WP created from WP08 review follow-up item 2 (cleanup).
- 2026-04-03T19:38:21Z – opencode:unknown:generic:unknown – shell_pid=254171 – Started implementation via workflow command
- 2026-04-03T19:42:19Z – opencode – shell_pid=254171 – T039+T040+T041+T048 implemented, 28/28 tests pass
- 2026-04-03T19:44:01Z – opencode:unknown:generic:unknown – shell_pid=254171 – Started review via workflow command
- 2026-04-03T19:46:02Z – opencode – shell_pid=254171 – Review passed: All 5 subtasks verified (T039/T040/T041/T042/T048). 28/28 tests green. No feature* terminology in active codepaths. escapeHtml XSS fix correct. Owned-files boundary respected.
- 2026-04-03T19:50:11Z – opencode – shell_pid=254171 – Done override: Merged into feature/agent-profile-implementation-rebased (worktree removed)
