---
work_package_id: WP06
title: Backfill-topology verify + regression + close
dependencies: []
requirement_refs:
- FR-010
tracker_refs: []
planning_base_branch: mission/lifecycle-tooling-friction
merge_target_branch: mission/lifecycle-tooling-friction
branch_strategy: Planning artifacts for this mission were generated on mission/lifecycle-tooling-friction. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into mission/lifecycle-tooling-friction unless the human explicitly redirects the landing branch.
subtasks:
- T015
- T016
phase: Mission-Lifecycle Tooling Friction
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "1768070"
history:
- at: '2026-06-27T00:00:00Z'
  actor: system
  action: Prompt created
agent_profile: python-pedro
authoritative_surface: tests/specify_cli/migration/
create_intent:
- tests/specify_cli/migration/test_backfill_topology_mission_scope.py
execution_mode: code_change
owned_files:
- tests/specify_cli/migration/test_backfill_topology_mission_scope.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP06 – Backfill-topology verify + regression + close

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile named in the frontmatter and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` and `authoritative_surface`.

---

## ⚠️ IMPORTANT: Review Feedback

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_ref` field in the event log (via `spec-kitty agent status` or the Activity Log below).
- **You must address all feedback** before your work is complete.
- **Report progress**: update the Activity Log as you address each item.

---

## Markdown Formatting

Wrap HTML/XML tags in backticks: `` `<div>` ``. Use language identifiers in code blocks: ` ```python `, ` ```bash `.

---

## Objectives & Success Criteria

- A regression test proves `spec-kitty migrate backfill-topology --mission X` in a multi-mission repo touches ONLY `kitty-specs/X/meta.json` — sibling missions are byte-identical (the 203-file blast-radius guard).
- The upstream fix (`--mission` scope + the pure non-persisting `read_topology`) is confirmed wired into the planning/inspection paths.
- #2219 is recorded as **verified-already-fixed** with a commit-pin — NO production change (test-only WP).
- **SC-006** is satisfied. `ruff` + `mypy` clean.

## Context & Constraints

- Spec: [spec.md](../spec.md) — User Story 6, FR-010, SC-006.
- Plan: [plan.md](../plan.md) — IC-06.
- Research: [research.md](../research.md) — #2219 ALREADY FIXED upstream: `--mission <slug>` scope (`src/specify_cli/cli/commands/migrate_cmd.py:315-322` → `src/specify_cli/migration/backfill_topology.py:228-240`) and the pure non-persisting `read_topology()` (`src/specify_cli/migration/backfill_topology.py:68-106`, #1814); idempotent-skip at `src/specify_cli/migration/backfill_topology.py:186-188`; landed via `0e270b10a`/`5b8e317aa`/#2070/#1814. NOTE the source dir is singular `migration/`, not `migrations/`.
- **NFR-002 — do NOT re-implement**: the fix is upstream. This WP VERIFIES + guards only; no production-file change.
- **C-006 — red-first**: author the regression test to assert the scoped behaviour through the real `migrate backfill-topology --mission` surface.

## Branch Strategy

- **Strategy**: {{branch_strategy}}
- **Planning base branch**: {{planning_base_branch}}
- **Merge target branch**: {{merge_target_branch}}

> Populated automatically by `spec-kitty agent mission tasks`. Do NOT edit manually.

## Subtasks & Detailed Guidance

### Subtask T015 – Regression test: single-mission scope, siblings byte-identical

- **Purpose**: Lock the blast radius so the repo-global churn (#2219) cannot regress.
- **Steps**:
  1. Create `tests/specify_cli/migration/test_backfill_topology_mission_scope.py`.
  2. **Non-vacuous fixture (required)**: seed a realistic multi-mission repo where the target mission X LACKS the `topology` field AND ≥ 1 sibling mission ALSO LACKS `topology` (real-format slugs/ids, C-007). Both missions lacking `topology` is what makes the test non-vacuous: the sibling is a candidate the backfill COULD touch, so only the `--mission X` SCOPING — not the idempotent-skip at `src/specify_cli/migration/backfill_topology.py:186-188` — can keep the sibling untouched. (A sibling that already had `topology` would be left alone by the idempotent-skip regardless of scoping, making the assertion prove nothing.)
  3. Snapshot sibling `meta.json` bytes; run `spec-kitty migrate backfill-topology --mission X`.
  4. Assert ONLY `kitty-specs/X/meta.json` changed (topology backfilled) and every (topology-lacking) sibling is byte-identical.
  5. Optionally assert idempotent-skip: re-running on an already-set mission is a no-op.
- **Files**: `tests/specify_cli/migration/test_backfill_topology_mission_scope.py` (new — in `owned_files` + `create_intent`).
- **Parallel?**: Parallel-safe with WP01/WP02/WP04/WP05.
- **Notes**: Because the fix is upstream this test should pass first run — it is a guard, not a red-first-for-a-defect. **Reasoned RED cross-check (record in the PR)**: with a topology-lacking sibling present, this test WOULD go RED against the pre-#2070 repo-global behaviour (which backfilled every topology-lacking mission, dirtying the sibling); only the post-#2070 `--mission` scoping keeps the sibling byte-identical. Without a topology-lacking sibling the assertion is a tautology.

### Subtask T016 – Verify wiring + record verified-already-fixed

- **Purpose**: Confirm the upstream fix is actually wired and close #2219.
- **Steps**:
  1. Cross-check that `--mission` scope and the pure `read_topology` are wired into the planning/inspection paths (per research pins: `src/specify_cli/cli/commands/migrate_cmd.py:315-322`, `src/specify_cli/migration/backfill_topology.py:68-106`/`228-240`/`186-188` — singular `migration/`).
  2. Confirm NO production change is required (test-only WP).
  3. Record #2219 as `verified-already-fixed` with the commit-pin (`0e270b10a`/`5b8e317aa`, #2070/#1814) in the PR/issue-matrix close note.
- **Files**: none (verification + close note; the regression test from T015 is the durable artifact).
- **Parallel?**: After T015.
- **Notes**: If the wiring is NOT actually present (verification fails), STOP and escalate — do not re-implement the fix in this WP; that would exceed scope (NFR-002).

## Test Strategy

- New test: `tests/specify_cli/migration/test_backfill_topology_mission_scope.py`.
- Drives the real `migrate backfill-topology --mission X` surface; asserts single-mission scope + byte-identical siblings.
- Run: `PWHEADLESS=1 pytest tests/specify_cli/migration/test_backfill_topology_mission_scope.py -q`.
- Realistic multi-mission fixture (C-007).

## Risks & Mitigations

- **Re-implementing an already-fixed defect**: this is verify-and-guard only (NFR-002); no production change.
- **Test passes trivially**: BOTH the target mission AND ≥ 1 sibling must LACK `topology`, so the sibling is genuinely a backfill candidate that only `--mission` scoping (not the idempotent-skip) protects — otherwise the guard is vacuous.
- **Wiring not present**: escalate rather than patch in-scope.

## Review Guidance

- Confirm the regression test seeds a real multi-mission repo and asserts siblings byte-identical after `--mission X` backfill.
- Confirm NO production file changed (test-only WP).
- Confirm the #2219 verified-already-fixed close note carries the commit-pin.
- Confirm `ruff`/`mypy` clean.

## Activity Log

> **CRITICAL**: Append new entries at the END in chronological order. Format: `- YYYY-MM-DDTHH:MM:SSZ – <agent_id> – <action>`.

- 2026-06-27T00:00:00Z – system – Prompt created.
- 2026-06-27T16:23:56Z – claude:opus:python-pedro:implementer – shell_pid=1735250 – Assigned agent via action command
- 2026-06-27T16:32:14Z – user – shell_pid=1735250 – WP06 implementer transition
- 2026-06-27T16:32:15Z – user – shell_pid=1735250 – WP06 implementer transition
- 2026-06-27T16:34:07Z – claude:opus:python-pedro:implementer – shell_pid=1735250 – Ready: non-vacuous scope regression green; #2219 verified-already-fixed, no production change
- 2026-06-27T16:35:06Z – claude:opus:reviewer-renata:reviewer – shell_pid=1768070 – Started review via action command
- 2026-06-27T16:37:23Z – user – shell_pid=1768070 – Review APPROVE (reverter-renata, isolated): non-vacuous --mission scope regression (sibling lacks topology, unscoped cross-check goes red), test-only, gates green; #2219 verified-already-fixed (#2070/#1814 anchors confirmed)
