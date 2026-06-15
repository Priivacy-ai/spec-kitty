---
work_package_id: WP04
title: '#1622 verify-and-close (regression lock + ticket close)'
dependencies: []
requirement_refs:
- FR-006
- FR-007
tracker_refs: []
planning_base_branch: mission/codebase-sanitization-1060-1622
merge_target_branch: mission/codebase-sanitization-1060-1622
branch_strategy: Planning artifacts for this mission were generated on mission/codebase-sanitization-1060-1622. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into mission/codebase-sanitization-1060-1622 unless the human explicitly redirects the landing branch.
subtasks:
- T017
- T018
- T019
phase: Phase 3 - Verify-and-close
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "284989"
history:
- at: '2026-06-15T12:04:55Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: tests/specify_cli/coordination/
create_intent:
- tests/specify_cli/coordination/test_1622_dead_symbol_retirement.py
execution_mode: code_change
owned_files:
- tests/specify_cli/coordination/test_1622_dead_symbol_retirement.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP04 – #1622 verify-and-close (regression lock + ticket close)

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If no profile is specified, run `spec-kitty agent profile list` and select the best match.

---

## Markdown Formatting

Wrap HTML/XML tags in backticks. Use language identifiers in code blocks.

---

## Objectives & Success Criteria

#1622 is already resolved in code (research.md R1). Instead of editing
`status_service.py` (which would break the build), this WP **locks the resolved
state with a regression test** and closes the ticket.

**Done when:**
- A new test asserts the resolved `status_service` shape (2 functions absent; 3
  symbols de-exported but live internals).
- The dead-symbol gate is confirmed green with unchanged baselines.
- #1622 is closed with the re-classification recorded.

## Context & Constraints

- Spec FR-006, FR-007. Plan IC-05. Research R1.
- **HARD CONSTRAINT (NFR-001, FR-008)**: do NOT edit
  `src/specify_cli/coordination/status_service.py` or any `src/` file. The 3
  retained symbols are load-bearing live internals — re-deleting breaks the live
  facade + `test_status_transition.py` (per the 01KTPKST closeout review).
- This WP's only file is a NEW test under `tests/specify_cli/coordination/`.

## Branch Strategy

- **Strategy**: lane-per-WP from `lanes.json`
- **Planning base branch**: `mission/codebase-sanitization-1060-1622`
- **Merge target branch**: `mission/codebase-sanitization-1060-1622`
- **Implement command**: `spec-kitty agent action implement WP04 --agent claude --base mission/codebase-sanitization-1060-1622`
  — `--base` REQUIRED (stale `mission_branch` in `lanes.json`; flatten note).

## Subtasks & Detailed Guidance

### Subtask T017 – Regression lock test
- **Purpose**: Make the resolved #1622 state machine-enforced (DIRECTIVE_003 —
  durable evidence).
- **Steps**: Create
  `tests/specify_cli/coordination/test_1622_dead_symbol_retirement.py` with these
  EXACT, non-fakeable assertions (verified against `status_service.py` on
  `upstream/main`):
  1. `assert not hasattr(status_service, "append_event_log_batch")` and
     `assert not hasattr(status_service, "read_wp_lane_actor")`.
  2. De-exported: `assert "StatusReadSource" not in status_service.__all__`
     (and `EventLogWriteTarget`, `StatusContractError`) …
  3. … yet importable: `from ...status_service import StatusReadSource,
     EventLogWriteTarget, StatusContractError` succeeds.
  4. Field-type proof:
     `EventLogReadContract.__dataclass_fields__["source"].type` resolves to
     `StatusReadSource`; `EventLogWriteContract.__dataclass_fields__["target"].type`
     to `EventLogWriteTarget`.
  5. **Runtime raise (load-bearing, NOT fakeable)**: pass a *write* contract to
     the *read* function and assert it raises —
     `with pytest.raises(StatusContractError): read_event_log(EventLogWriteContract.primary_checkout(tmp_path))`
     (this executes the live guard at `status_service.py:146-147`).
  - Add a module docstring citing #1622 + the 01KTPKST resolution so a future
    reader does not "re-delete" the symbols.
  - A `hasattr`/`__all__`-only test (no runtime raise) is NOT acceptable — it is
    tautological and the reviewer will reject it.
- **Files**: `tests/specify_cli/coordination/test_1622_dead_symbol_retirement.py`

### Subtask T018 – Confirm gates green
- **Steps**: Run
  `PWHEADLESS=1 pytest tests/specify_cli/coordination/test_1622_dead_symbol_retirement.py tests/architectural/test_no_dead_symbols.py tests/architectural/test_ratchet_baselines.py -q`.
  Confirm green and that `_baselines.yaml` has no `category_c_upstream_status_service`
  entry. Capture the grep proof (`git grep -n 'append_event_log_batch\|read_wp_lane_actor'`
  → none) in the WP activity log / commit message.

### Subtask T019 – Close #1622
- **Purpose**: FR-007.
- **Steps**: Comment on #1622 with the re-classification — the upstream
  01KTPKST dead-symbol directive delivered 2/5 deletions
  (`append_event_log_batch`, `read_wp_lane_actor`); the other 3 are
  retained-because-live and de-exported; verified + locked by this mission's new
  regression test at `<commit>`. Close it as completed. Use `unset GITHUB_TOKEN`
  before `gh` for org-repo auth.
- **Validation**:
  - [ ] New regression test committed and green
  - [ ] `status_service.py` UNCHANGED (`git diff --stat` shows only the new test file)
  - [ ] dead-symbol gate green; baselines unchanged
  - [ ] #1622 closed with the re-classification comment

## Definition of Done
- Regression test added + green; dead-symbol gate green; #1622 closed; zero `src/`
  edits.

## Reviewer Guidance
- Verify NO source file changed (only the new test). Confirm the test actually
  exercises the live behavior (not just `hasattr`). Reject if any
  `status_service.py` change appears or if the test merely tautologically passes.

## Activity Log

- 2026-06-15T13:02:30Z – claude:sonnet:python-pedro:implementer – shell_pid=225207 – Assigned agent via action command
- 2026-06-15T13:07:58Z – user – shell_pid=225207 – Moved to claimed
- 2026-06-15T13:09:16Z – claude:sonnet:python-pedro:implementer – shell_pid=225207 – Ready: #1622 regression-lock test added + ticket closed; zero src edits. NOTE: planning-artifact commits on lane branch are spec-kitty framework status transitions (mark-status auto-commit) + undo-restore; final diff vs mission base is clean (test file only).
- 2026-06-15T13:14:23Z – claude:sonnet:python-pedro:implementer – shell_pid=225207 – Orchestrator sync (flatten misfires lane-purity guard on planning branch); code done+green on lane branch
- 2026-06-15T13:15:25Z – claude:opus:reviewer-renata:reviewer – shell_pid=284989 – Started review via action command
- 2026-06-15T13:19:37Z – user – shell_pid=284989 – Review PASSED (renata) — WP04 meets every criterion: zero src edits (git diff --stat src/ empty); regression-lock test NON-tautological (pytest.raises(StatusContractError) on read_event_log(write_contract) lines 151-164, exercises live guard status_service.py:146-147; primary_checkout_append factory :121); 10/10 tests + dead-symbol gate green; de-export verified real (3 symbols absent from __all__ yet importable); ruff+mypy clean; #1622 CLOSED with re-classification. --force overrides lane-purity guard (FALSE POSITIVE under flattened mission). Mission-level issue-matrix #1059 row was missing its follow-up handle (orthogonal to WP04 ownership) — fixed on planning branch in commit 54a1dd159 to unblock the gate.
- 2026-06-15T14:41:49Z – user – shell_pid=284989 – Done override: Code consolidated onto mission/ (49f4b93ef + e9c311b9b); per-WP renata-approved; PR to upstream pending
