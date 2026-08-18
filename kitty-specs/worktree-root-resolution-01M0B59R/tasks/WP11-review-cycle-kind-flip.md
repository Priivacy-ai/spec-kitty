---
work_package_id: WP11
title: Review-cycle write-side kind-flip
dependencies: []
requirement_refs:
- FR-017
planning_base_branch: fix/worktree-root-resolution
merge_target_branch: fix/worktree-root-resolution
branch_strategy: Planning artifacts for this mission were generated on fix/worktree-root-resolution. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/worktree-root-resolution unless the human explicitly redirects the landing branch.
subtasks:
- T035
- T036
- T037
- T038
phase: Phase 2 - Review-artifact integrity
history:
- at: '2026-08-18T21:17:46Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: implementer-ivan
authoritative_surface: src/specify_cli/review/cycle.py
create_intent:
- tests/specify_cli/review/test_cycle_kind_flip.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/review/cycle.py
- src/specify_cli/cli/commands/agent/tasks_verdict_persistence.py
- tests/specify_cli/review/test_cycle_kind_flip.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP11 – Review-cycle write-side kind-flip

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter (or any user-defined profile), and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `implementer-ivan`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` and `authoritative_surface`.

---

## ⚠️ IMPORTANT: Review Feedback

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_ref` field in the event log.
- **You must address all feedback** before your work is complete.
- **Report progress**: Update the Activity Log as you go.

---

## Markdown Formatting

Wrap HTML/XML tags in backticks. Use language identifiers in code blocks.

---

## Objectives & Success Criteria

Correct the review-cycle **write-side** artifact kind for the safe consumer(s), so verdict facts are written under the review-cycle kind rather than the legacy `WORK_PACKAGE_TASK` — **without** flipping the global write-side default (which is not yet safe; see the disclosure below).

> **NARROWED (post-tasks squad):** `review/cycle.py:106-158` carries an in-code "WP13 finding" disclosure — flipping the write-side **default** to `REVIEW_CYCLE` moves the physical write into the coordination worktree, which **breaks** `tests/coordination/test_analysis_report_rehome.py::test_review_cycle_authored_lands_on_coord_ref_and_is_absent_on_primary`. That full flip requires a physical-write / git-staging separation rework this WP does NOT scope. This WP does the **safe subset only**: opt the specific safe consumer(s) into `kind=REVIEW_CYCLE` where the physical-write location does **not** move.

Done when:
- The safe consumer(s) write under `kind=REVIEW_CYCLE` (the global default is **left unchanged**).
- `resolve_review_verdict_facts` is verified **read-tolerant** of the write-side kind (it was already repointed onto the event authority — see T037; no reader migration is performed).
- `test_analysis_report_rehome` **stays green** (the narrow opt-in must not move the physical write).
- A red-first `@pytest.mark.regression` test (issue #3563) is authored and shown failing on base for the safe consumer, green after.

## Context & Constraints

- Spec: FR-017, SC-004 (verdict path). Contracts: [C-9](../contracts/resolver-and-verdict-contracts.md).
- Verified base anchors: `_review_cycle_wp_dir` at `review/cycle.py:71` with default `kind = WORK_PACKAGE_TASK` at `:76`; the `REVIEW_CYCLE` branch (`:179-197`) falls back to a `WORK_PACKAGE_TASK` read. `resolve_review_verdict_facts` lives at `cli/commands/agent/tasks_verdict_persistence.py:404` (NOT in `cycle.py`).
- This is the deferral D1 filed as **#3563** under epic #3044.

## Branch Strategy

- **Strategy**: coord-lane
- **Planning base branch**: fix/worktree-root-resolution
- **Merge target branch**: fix/worktree-root-resolution

> Populated by `spec-kitty agent mission tasks`. Do NOT change manually.

## Subtasks & Detailed Guidance

### Subtask T035 – Red-first: safe consumer writes WORK_PACKAGE_TASK kind

- **Purpose**: Prove the wrong-kind write for the safe consumer before fixing (NFR-001).
- **Steps**:
  1. Create `tests/specify_cli/review/test_cycle_kind_flip.py`.
  2. Write a `@pytest.mark.regression` test (pinned to #3563) that exercises the **safe consumer** (the one whose physical-write location does not move) and asserts the persisted artifact kind is the review-cycle kind (not `WORK_PACKAGE_TASK`).
  3. On base this is **RED** (the consumer currently writes `WORK_PACKAGE_TASK`).
- **Files**: `tests/specify_cli/review/test_cycle_kind_flip.py` (new).
- **Validation**: red on base; green after T036.

### Subtask T036 – Opt the safe consumer(s) into kind=REVIEW_CYCLE (NOT a default flip)

- **Purpose**: FR-017 — write under the correct review-cycle kind where it is safe to do so.
- **Steps**:
  1. **Do NOT change the `_review_cycle_wp_dir` write-side default** at `review/cycle.py:71/76`. Flipping the default moves the physical write into the coord worktree and breaks the rehome guard (the disclosed WP13 finding).
  2. Instead, pass `kind=REVIEW_CYCLE` explicitly at the specific call site(s) whose physical-write location does **not** move — the docstring at `:106-158` identifies where the narrow opt-in is independently safe. Verify against that disclosure which caller qualifies.
  3. Confirm the opt-in does not relocate the physical write (compare the resolved write path before/after — it must be unchanged).
- **Files**: `src/specify_cli/review/cycle.py`.
- **Validation**: the safe consumer writes under the review-cycle kind; the physical write path is unchanged; `test_analysis_report_rehome` stays green.

### Subtask T037 – Verify resolve_review_verdict_facts read-tolerance (NOT a reader migration)

- **Purpose**: Confirm the reader is unaffected by the write-side kind — it was already fixed.
- **Steps**:
  1. `resolve_review_verdict_facts` (`tasks_verdict_persistence.py:404`) was **already** repointed off kind-based frontmatter reads onto the **event authority** (`event_sourced_review_result` via `_resolve_verdict_read_feature_dir:471`) by mission `verdict-seam-write-unification-01KZ9Q35`. Do **not** "migrate the reader".
  2. Add/extend an assertion that the event-authority reader resolves the verdict correctly **regardless** of the write-side artifact kind (read-tolerant) — proving the T036 opt-in does not disturb verdict resolution.
- **Files**: `src/specify_cli/cli/commands/agent/tasks_verdict_persistence.py` (verification/assertion only; no behavioral change expected).
- **Validation**: verdict facts resolve correctly for both the new-kind write and any legacy artifact.

### Subtask T038 – Re-verify test_analysis_report_rehome stays green

- **Purpose**: Guard the rehome behavior (finding I4) — the narrow opt-in must NOT move the physical write.
- **Steps**:
  1. Run `tests/coordination/test_analysis_report_rehome.py::test_review_cycle_authored_lands_on_coord_ref_and_is_absent_on_primary` against the change.
  2. It must stay **green** unchanged. If it goes red, the opt-in wrongly moved the physical write — revert to a narrower consumer. Do NOT edit this test to accommodate a moved write.
- **Files**: reference `tests/coordination/test_analysis_report_rehome.py` (do not claim ownership; do not edit it).
- **Validation**: `pytest -k analysis_report_rehome` green, unchanged.

## Test Strategy (required)

- Run: `PWHEADLESS=1 pytest tests/specify_cli/review/test_cycle_kind_flip.py -q` and `pytest -k analysis_report_rehome -q`.
- T035 red on `upstream/main`, green after; rehome test green after migration.

## Risks & Mitigations

- **BLOCKED full default-flip (out of scope):** flipping the global `_review_cycle_wp_dir` default to `REVIEW_CYCLE` is **not safe** in this WP — it moves the physical write into the coord worktree and breaks `test_analysis_report_rehome`. The prerequisite physical-write / git-staging separation rework, plus routing the 3 unrouted sites (`workflow.py::review`, `workflow_cores.py::has_prior_rejection`, `workflow_executor.py::implement_try_render_fix_mode_prompt`), is tracked **separately** and is out of scope here. This WP does only the narrow, physically-non-moving opt-in.
- **Opt-in accidentally moves the physical write**: mitigate by comparing the resolved write path before/after (T036 step 3) and by T038 keeping the rehome guard green unchanged.
- **Reader confusion**: none expected — the reader is already event-authority-based (T037 is verification only, not migration).

## Review Guidance

- Confirm the write-side kind is flipped; the reader resolves it; legacy reads still work; the rehome test is green; any out-of-map edit is justified.

## Activity Log

- 2026-08-18T21:17:46Z – system – Prompt created.

---

### Updating Status

Status is managed via `status.events.jsonl`. Use `spec-kitty agent tasks move-task WP11 --to <status>`.
- 2026-08-18T22:06:02Z – claude – shell_pid=3053390 – WP11 finding (narrowed opt-in): the FR-017 safe narrow opt-in is ALREADY in effect on base. review/cycle.py::_commit_review_cycle_artifact already passes kind=REVIEW_CYCLE (prior missions 191/WP10), and commit_for_mission path-classification lands review-cycle-N.md on the COORD partition while the physical write stays in the PRIMARY tasks home; resolve_review_verdict_facts already reads the STATUS_STATE event authority (read-tolerant of write-side kind). Committed tests/specify_cli/review/test_cycle_kind_flip.py (#3563, 3 tests) locking this + verifying read-tolerance (T037) + guarding the physical-write-does-not-move invariant (T038). NO owned-file default/resolver flip shipped: empirically, flipping the _review_cycle_wp_dir write-side default reds test_analysis_report_rehome (physical write moves into coord worktree); flipping _resolve_verdict_wp_dir or the pointer read seam reds the test_verdict_dir_co_resolution GREEN SENTINEL (NFR-004). The only safe consumer the disclosure names (post_merge merge-time gate) is NOT in owned_files. Per the WP STOP directive, did not flip the default. test_cycle_kind_flip + test_analysis_report_rehome both GREEN; ruff+mypy clean. Escalating red-first (T035) feasibility + move-task decision to orchestrator.
