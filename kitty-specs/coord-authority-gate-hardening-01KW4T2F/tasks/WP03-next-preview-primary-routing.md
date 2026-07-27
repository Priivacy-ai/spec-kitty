---
work_package_id: WP03
title: '#2197 spec-kitty next claimable-preview primary routing (caller-only)'
dependencies:
- WP02
requirement_refs:
- FR-004
tracker_refs: []
planning_base_branch: feat/coord-authority-gate-hardening
merge_target_branch: feat/coord-authority-gate-hardening
branch_strategy: Planning artifacts for this mission were generated on feat/coord-authority-gate-hardening. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/coord-authority-gate-hardening unless the human explicitly redirects the landing branch.
subtasks:
- T011
- T012
- T013
phase: Phase 2 - Routing
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "2021205"
history:
- at: '2026-06-27T15:59:26Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/runtime/next/runtime_bridge.py
create_intent:
- tests/integration/test_next_preview_primary_routing.py
execution_mode: code_change
model: ''
owned_files:
- src/runtime/next/runtime_bridge.py
- tests/integration/test_next_preview_primary_routing.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP03 – #2197 spec-kitty next claimable-preview primary routing (caller-only)

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter (or any user-defined profile), and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

---

## Markdown Formatting

Wrap HTML/XML tags in backticks. Use language identifiers in code blocks (```python`, ```bash`).

---

## Objectives & Success Criteria

Route the out-of-loop `spec-kitty next` claimable-preview read onto the kind-aware PRIMARY/STATUS leg-split so a coord-topology mission previews from the **authoritative PRIMARY surface**, not the STATUS-only coord husk (#2197).

- **FR-004 — caller-only routing.** In `runtime_bridge.py::_build_finalized_override_query_decision`, change `preview_claimable_wp(feature_dir)` to pass a PRIMARY `planning_dir` + the coord `status_dir=`, mirroring the reference impl. `discovery.preview_claimable_wp` already carries the `status_dir=` leg-split signature — **this is a caller-only change** (C-003: the single sanctioned production routing edit in this mission).
- **SC-002 — behavioral proof.** An executed revert-fails test asserts the returned DOMAIN value `preview.wp_id` (NOT a path equality); reverting the routing → coord husk → wrong/empty `wp_id` → RED.

**Done means:**
- The preview call uses the leg-split (PRIMARY `planning_dir` + coord `status_dir`) and threads `main_root` correctly (T011).
- The `tasks/`-absent None / `selection_reason` handling is preserved (T012).
- A behavioral revert-fails integration test asserting `preview.wp_id` is green and genuinely RED on revert (T013).

## Context & Constraints

- **Design docs**: [spec.md](../spec.md) (FR-004, SC-002, C-001, C-002, C-003), [plan.md](../plan.md) IC-B, [contracts/gate-hardening-contracts.md](../contracts/gate-hardening-contracts.md) Contract D.1.
- **The reference implementation to mirror** is `src/specify_cli/cli/commands/agent/workflow.py::_preview_claimable_wp_for_mission` (lines ~1054–1078). **NOTE: the plan/contract cited `runtime/next/workflow.py`, which is wrong — the real path is `cli/commands/agent/workflow.py`.** It builds the split as:
  ```python
  main_root = get_main_repo_root(repo_root)
  planning_dir = resolve_planning_read_dir(
      main_root, mission_slug, kind=MissionArtifactKind.WORK_PACKAGE_TASK
  )
  if not (planning_dir / "tasks").is_dir():
      return None
  status_dir = candidate_feature_dir_for_mission(main_root, mission_slug)
  return preview_claimable_wp(planning_dir, status_dir=status_dir)
  ```
- **The caller to change** is `runtime_bridge.py::_build_finalized_override_query_decision` (~:3051). Today (~:3076–3081):
  ```python
  from runtime.next.discovery import preview_claimable_wp
  preview = preview_claimable_wp(feature_dir)
  override_wp_id = preview.wp_id
  if preview.wp_id is None and preview.selection_reason is not None:
      reason = preview.selection_reason
  ```
  The function receives `feature_dir: Path` and `mission_slug: str` but **not** `repo_root`/`main_root` — you must thread a repo/main root into the function (or derive it). `runtime_bridge.py` already imports/uses `primary_feature_dir_for_mission` (see `_primary_runtime_feature_dir`, ~:78) and the kind-aware seam; reuse those rather than authoring resolver internals (C-002).
- **C-001 (binding)**: the status leg stays coord-aware (`candidate_feature_dir_for_mission` is the STATUS-partition leg). Do NOT move a status read to PRIMARY. Only the `tasks/`/WP-selection (PRIMARY) leg changes surface; the status-event leg keeps reading the coord husk.
- **C-002**: consume `resolve_planning_read_dir` / `primary_feature_dir_for_mission`; do NOT author `_read_path_resolver` internals.
- **C-003**: this is the ONLY production routing edit in the mission. Do not make other production routing changes.
- **DECOUPLING**: this FR-004 read is invisible to the call-shape arm (it's a `tasks/`-dir, parameter-fed shape). It is gated **behaviorally** by SC-002 — not by WP02's scan. Do not rely on the static gate to catch a regression here.
- **Dependency on WP02**: the runtime/next scan-scope + read-site floor (WP02) is pinned before this WP edits `runtime_bridge.py`, so the census/floor is computed against a stable surface. FR-004 changes the `preview_claimable_wp` call (not an identity-family read), so it does not move WP02's `get_mission_type` floor — but landing after WP02 keeps the ordering clean.

## Branch Strategy

- **Strategy**: lane-based (allocated from `lanes.json` after finalize-tasks)
- **Planning base branch**: feat/coord-authority-gate-hardening
- **Merge target branch**: feat/coord-authority-gate-hardening

> Execution worktrees are allocated per computed lane from `lanes.json`. Do not change these fields manually.

## Subtasks & Detailed Guidance

### Subtask T011 – Re-point the preview read to the PRIMARY/STATUS leg-split

- **Purpose**: Preview from the authoritative PRIMARY surface so a coord-topology mission is never reported as having no claimable WP.
- **Steps**:
  1. Thread a `repo_root`/`main_root` into `_build_finalized_override_query_decision` (add a parameter and pass it from the call sites — there is one at ~:3288). Use `get_main_repo_root(...)` to normalize, matching the reference impl.
  2. Build `planning_dir = resolve_planning_read_dir(main_root, mission_slug, kind=MissionArtifactKind.WORK_PACKAGE_TASK)` (PRIMARY leg) and `status_dir = candidate_feature_dir_for_mission(main_root, mission_slug)` (coord STATUS leg).
  3. Call `preview_claimable_wp(planning_dir, status_dir=status_dir)`.
  4. Confirm imports/symbols are available in `runtime_bridge.py` (it already references `primary_feature_dir_for_mission` and the seam); add imports as needed, consistent with the module's existing import style.
- **Files**: `src/runtime/next/runtime_bridge.py`
- **Notes**: Keep the change minimal and caller-only. Do NOT modify `discovery.preview_claimable_wp` (it already has the leg-split signature).

### Subtask T012 – Preserve the `tasks/`-absent / selection-reason handling

- **Purpose**: Don't regress the existing decision semantics.
- **Steps**:
  1. The reference impl returns `None` when `planning_dir/tasks` is absent. Decide the equivalent behavior here: if the preview is unavailable (no tasks on PRIMARY), preserve today's `override_wp_id = None` + `selection_reason` → `reason` path so the `Decision` is still well-formed.
  2. Keep the existing `if preview.wp_id is None and preview.selection_reason is not None: reason = preview.selection_reason` logic working against the new leg-split preview.
- **Files**: `src/runtime/next/runtime_bridge.py`
- **Notes**: Guard against `preview is None` if you adopt the reference's None-return shape for the tasks-absent case.

### Subtask T013 – SC-002 behavioral revert-fails test

- **Purpose**: Prove the routing fix behaviorally — the only gate on FR-004 (the static arm can't see it).
- **Steps**:
  1. Create `tests/integration/test_next_preview_primary_routing.py`.
  2. Use the **existing** `coord_topology_mission` fixture (`tests/integration/coord_topology_fixture.py`) — its STATUS-only husk already lacks `tasks/`. Do NOT edit the fixture file (WP04 owns it); import/consume it read-only.
  3. Drive `_build_finalized_override_query_decision` (or the nearest executed entry point that reaches it) on the coord-topology mission and assert the returned `preview`/`Decision` `wp_id` **equals the known expected PRIMARY-surface WP id** the fixture seeds (e.g. `assert decision.wp_id == "WP01"`), **NOT** `wp_id is not None` and **NOT** a resolved-path equality.
  4. **NON-FAKEABLE DoD (squad CRITICAL — SC-002 must EXECUTE the revert, not document it)**: `assert wp_id is not None` + a `# revert would be empty` comment is vacuous. The test must *execute* the wrong-leg behavior and assert it differs: drive the **coord-husk leg** directly (e.g. call `preview_claimable_wp(<coord husk dir>)` the way the pre-fix code did) and assert it yields a wrong/empty `wp_id` — so the test body itself contains both the routed (correct → `"WP01"`) and unrouted (coord husk → empty/wrong) outcomes and asserts they differ. A reviewer reverting T011 must watch the primary assertion go RED.
- **Files**: `tests/integration/test_next_preview_primary_routing.py`
- **Notes**: Real git + filesystem state via the fixture; no resolver patching. This is a behavioral test (SC-002), distinct from the architectural arm. The fixture must expose (or the test must know) the expected PRIMARY WP id so the assertion is value-exact, not existence-only.

## Test Strategy

- Tests REQUIRED. Run: `PWHEADLESS=1 pytest tests/integration/test_next_preview_primary_routing.py -q`.
- Also run `PWHEADLESS=1 pytest tests/architectural/ -q` to confirm the production edit doesn't trip the (now-hardened) arm.
- Ruff + mypy clean on both touched files.

## Risks & Mitigations

- **Threading `main_root`**: the function lacks `repo_root`. **Mitigation**: add a parameter and update the single call site (~:3288); verify no other caller path.
- **C-001 regression**: accidentally routing the STATUS leg to PRIMARY. **Mitigation**: keep `status_dir=candidate_feature_dir_for_mission(...)`; only the WP-selection leg moves to PRIMARY.
- **Vacuous SC-002**: a test that asserts a path or always-passes. **Mitigation**: assert the domain `wp_id`; include the revert-fails reasoning.
- **Wrong reference path**: the plan cited `runtime/next/workflow.py`. **Mitigation**: use `cli/commands/agent/workflow.py::_preview_claimable_wp_for_mission` (verified to exist).

## Review Guidance

- Confirm the change is caller-only — `discovery.preview_claimable_wp` is untouched.
- Confirm the status leg stays coord-aware (`candidate_feature_dir_for_mission`) and only the WP-selection leg routes to PRIMARY (C-001).
- Confirm SC-002 asserts `preview.wp_id` (domain value) and is genuinely RED on revert — reviewer should temporarily revert T011 and watch it fail.
- Confirm ruff/mypy clean and the architectural suite stays green.

## Activity Log

- 2026-06-27T15:59:26Z – system – Prompt created.
- 2026-06-27T18:04:15Z – claude:opus:python-pedro:implementer – shell_pid=1975360 – Assigned agent via action command
- 2026-06-27T18:25:28Z – claude:opus:python-pedro:implementer – shell_pid=1975360 – FR-004 caller-only leg-split: preview_claimable_wp(planning_dir=PRIMARY, status_dir=coord) in _build_finalized_override_query_decision, threaded repo_root from single call site. SC-002 executed revert-fails test (routed==WP01 vs coord-husk unrouted==None). ruff exit 0 on both files; mypy adds 0 new errors (only pre-existing _internal_runtime/schema.py:26). arch suite 582 passed, 1 pre-existing worktree-path failure.
- 2026-06-27T18:26:07Z – claude:opus:reviewer-renata:reviewer – shell_pid=2021205 – Started review via action command
