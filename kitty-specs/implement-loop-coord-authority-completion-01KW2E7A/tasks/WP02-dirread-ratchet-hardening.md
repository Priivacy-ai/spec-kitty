---
work_package_id: WP02
title: Dir-read ratchet hardening + residual pinning
dependencies: []
requirement_refs:
- FR-007
- FR-008
- FR-015
- NFR-001
tracker_refs: []
planning_base_branch: design/coord-authority-remediation-2160
merge_target_branch: design/coord-authority-remediation-2160
branch_strategy: Planning artifacts for this mission were generated on design/coord-authority-remediation-2160. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into design/coord-authority-remediation-2160 unless the human explicitly redirects the landing branch.
subtasks:
- T004
- T005
- T006
- T007
- T008
phase: Phase 1 - Foundation
assignee: ''
agent: "claude:sonnet:python-pedro:implementer"
shell_pid: "3901291"
history:
- at: '2026-06-26T18:29:45Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: tests/architectural/
create_intent: []
execution_mode: code_change
owned_files:
- tests/architectural/test_gate_read_literal_ban.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP02 – Dir-read ratchet hardening + residual pinning

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

## Objectives & Success Criteria

Make the dir-read ratchet's census **non-vacuous** so the routing WPs can drain it, then
pin the full surfaced residual set with tracking-issue references.

Done when:
- The scanner flags the **inline-call shape** `resolver(...) / "<dir|.md>"` (callee ∈ the
  coord-aware resolvers) in addition to the two-hop form.
- The scan scope is **all of `src/specify_cli/`** (not just `cli/commands/`).
- A **mandatory self-test** asserts a synthetic pre-fix inline snippet is flagged AND a
  routed (seam) snippet is NOT flagged.
- Every site the widened scanner surfaces is in `_DIR_READ_KNOWN_RESIDUALS` with a comment
  reference: out-of-scope pins cite **#2185** (merge/lanes/core-worktree-topology), **#2186**
  (meta.json identity reads), **#2167** (scripts/tasks legacy reader); in-loop sites are
  pinned "pending route — this mission WP03–WP06".
- The dir-read baseline census is recounted and recorded; the gate is GREEN.

## Context & Constraints

- Spec FR-007, FR-008, FR-015 (pin citations); NFR-001. Plan IC-01a. research.md FR-008 sweep
  has the full classified inventory.
- **No silent skip** — every surfaced site is routed (later WPs) or pinned now.
- gate-unmask-cannot-self-validate: the scope widening only bites POST-merge — do not expect
  it to catch new offenders within this mission's own diff (the mission close-out runs the
  merged-branch dry-run, NFR-005).
- This file (`test_gate_read_literal_ban.py`) is **owned here**; WP03–WP06 will make
  justified out-of-map edits to remove their own pins as they route (FR-009).

## Branch Strategy

- **Strategy**: already-confirmed
- **Planning base branch**: design/coord-authority-remediation-2160
- **Merge target branch**: design/coord-authority-remediation-2160

## Subtasks & Detailed Guidance

### Subtask T004 – Inline-call-shape detection arm
- **Purpose**: Close the structural blind spot (the scanner only sees `d = resolver(); d / "x"`).
- **Steps**: Extend the AST visitor so a `BinOp`/`/` whose **left operand is an `ast.Call`**
  to a coord-aware resolver and whose right is a PRIMARY-kind dir/`.md` literal is flagged,
  not just `Name`-rooted two-hop joins. Keep the existing two-hop detection.
- **Files**: `tests/architectural/test_gate_read_literal_ban.py`.

### Subtask T005 – Widen scan scope to all src/specify_cli/
- **Steps**: Replace the `cli/commands/`(+`acceptance/`) walk with a walk over all of
  `src/specify_cli/`. Keep performance within the gate budget.
- **Files**: same.

### Subtask T006 – Mandatory self-test + C-008 sub-path exclusion
- **Steps**: Add a self-test that feeds a synthetic inline pre-fix snippet (coord-aware
  resolver + `/ "tasks"`) and asserts FLAGGED; feeds a routed `resolve_planning_read_dir(...)`
  snippet and asserts NOT flagged. **MANDATE** (not "may"): capture the pre-T004 RED output
  inline, and add a coverage assertion that every real inline site in research.md's inventory
  is flagged before any WP unpins it.
- **C-008 sub-path exclusion (squad HIGH — root cause):** the scanner is function-granular, so
  `workflow.py::implement`/`::review` stay FLAGGED because of their `tasks/<wp_slug>/…`
  review-cycle reads (C-008 KEEP-coord) even after their PRIMARY leg routes. Teach the scanner
  to NOT treat a `… / "tasks" / <wp_slug> / …` sub-artifact join as a PRIMARY-kind residual
  (it is a per-WP review-cycle artifact, matched read/write, legitimately coord). Add a
  self-test for this exclusion.
- **Files**: same.

### Subtask T007 – Pin the full surfaced set with citations (three categories)
- **Steps**: Run the widened scanner, capture every surfaced site, and populate
  `_DIR_READ_KNOWN_RESIDUALS` in THREE comment-grouped categories: (a) in-loop "pending
  WP03–WP06" (drained by routing); (b) out-of-scope citing #2185 / #2186 / #2167; (c)
  **C-008 permanent-coord** — any `implement`/`review` review-cycle sub-artifact read that
  legitimately stays coord and is NOT routable (only if the T006 exclusion does not fully
  suppress it at function granularity). Cross-check against research.md's inventory.
- **Files**: same.

### Subtask T008 – Recount + record the baseline census
- **Steps**: Update the recorded baseline count(s) to the post-widening reality; document
  the number in a comment so later shrink is visible.
- **Files**: same.

## Test Strategy

`PWHEADLESS=1 pytest tests/architectural/test_gate_read_literal_ban.py -q` must be GREEN
with the full pin set. The self-test (T006) is the key new assertion.

## Risks & Mitigations

- **Missed surfaced site** → gate red or a silent hole. Mitigation: diff the scanner output
  against research.md's 111-site inventory; every PRIMARY-read site is accounted for.
- **Over-broad inline detection** flags legitimate STATUS reads → false positives. Mitigation:
  gate on the join base name being a PRIMARY-kind dir/file.

## Review Guidance

- Confirm the self-test genuinely fails without the T004 arm (reviewer may revert T004 to check).
- Confirm out-of-scope pins cite the right issues; no site silently skipped.

## Activity Log

- 2026-06-26T18:29:45Z – system – Prompt created.
- 2026-06-26T19:02:18Z – claude:sonnet:python-pedro:implementer – shell_pid=3901291 – Assigned agent via action command
- 2026-06-26T19:22:28Z – user – shell_pid=3901291 – Moved to planned
- 2026-06-26T19:43:16Z – user – shell_pid=3901291 – flat claim
- 2026-06-26T19:43:18Z – user – shell_pid=3901291 – flat; scanner hardening on design branch
- 2026-06-26T20:03:58Z – claude:sonnet:python-pedro:implementer – shell_pid=3901291 – Scanner hardened (6aea96439): inline-shape + whole-src + C-008 exclusion; 17 passed; census 10 in-loop/2 out-of-scope
- 2026-06-26T20:11:19Z – user – shell_pid=3901291 – renata review done
- 2026-06-26T20:11:20Z – user – shell_pid=3901291 – Approved (flat; arbiter after renata cycle-1). renata verified core correct (inline arm, whole-src, C-008 per-node precision, empirically non-vacuous self-test). 2 blocking fixes applied + verified: (1) show_kanban_status pin now cites filed #2187; (2) census discloses lanes.json out-of-vocabulary (fixture-only coverage). Gate 17 passed. Stale review-cycle-1.md is my reset-feedback, not a genuine rejection.
