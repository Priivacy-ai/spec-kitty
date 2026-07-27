---
work_package_id: WP08
title: retrospect + merge coord-topology reconciliation
dependencies:
- WP03
requirement_refs:
- FR-006
- FR-007
tracker_refs: []
planning_base_branch: fixups/code-engine-stabilization
merge_target_branch: fixups/code-engine-stabilization
branch_strategy: Planning artifacts for this mission were generated on fixups/code-engine-stabilization. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fixups/code-engine-stabilization unless the human explicitly redirects the landing branch.
subtasks:
- T026
- T027
- T028
phase: Phase 2 - Retrospect/Merge
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "4032841"
history:
- at: '2026-06-09T17:17:15Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: ''
authoritative_surface: src/specify_cli/merge/
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/mission_loader/retrospective.py
- src/specify_cli/merge/workspace.py
- src/specify_cli/cli/commands/merge.py
role: ''
tags: []
task_type: implement
---

# Work Package Prompt: WP08 – retrospect + merge coord-topology reconciliation

## ⚡ Do This First: Load Agent Profile
Use `/ad-hoc-profile-load`; if none set, pick an implementer profile for `code_change` on `src/specify_cli/merge/`.

---

## Objectives & Success Criteria
- **retrospect** read/write goes to the canonical surface via the context — no primary-checkout-only reads, no gitignored writes (#1735/#1771).
- **merge** coord-topology seams (PATH/env, baking step, mixed JSONL handling) consume the context instead of re-deriving coord paths (#1736/#1770).
- **Done when:** retrospect reads the canonical surface and merge resolves coord paths via the context; WP01 retrospect/merge parity flips green; resumable merge-state machine unaffected.

## Context & Constraints
- Design: `spec.md` FR-006/FR-007; `plan.md` IC-07; `research.md` R-A Cluster D/seam #6.
- Merge is lifecycle-terminal — do NOT regress the resumable `merge-state.json` machine (see CLAUDE.md Merge patterns).
- If a coord-topology seam lives in an adjacent `merge/` file not in `owned_files`, make a small out-of-map edit with a one-line rationale (ownership is "close enough for comfort").

## Branch Strategy
- **Planning base / merge target**: `fixups/code-engine-stabilization`. Populated by finalize-tasks.

## Subtasks & Detailed Guidance
### T026 — retrospect canonical surface (#1735/#1771)
- Route retrospect read/write through the context's StatusSurface/ArtifactPlacement fragments; no primary-only read; no gitignored write target.
### T027 — merge coord seams via context (#1736/#1770)
- PATH/env construction, the baking step, and mixed-JSONL handling resolve coord paths from the context.
### T028 — Flip WP01 retrospect/merge parity
- Make the WP01 retrospect/merge assertions pass from both CWDs.

## Test Strategy
- retrospect + merge tests stay green; WP01 retrospect/merge parity green; `ruff`+`mypy` zero issues.

## Risks & Mitigations
- *Merge regression* → run the merge preflight + resume tests; verify state machine intact.

## Review Guidance
- Recommended: **reviewer-renata**. Confirm no coord-path re-derivation remains in retrospect/merge (C-005).

## Activity Log
- 2026-06-09T17:17:15Z – system – Prompt created.
- 2026-06-10T04:03:44Z – claude:opus:python-pedro:implementer – shell_pid=3972219 – Assigned agent via action command
- 2026-06-10T04:18:44Z – claude:opus:python-pedro:implementer – shell_pid=3972219 – retrospect+merge reconciled to canonical surface; retrospect status reads/commits route via resolve_status_surface (#1735/#1771); merge coord seams already consume resolve_status_surface (WP02-07); flattened CommitTarget.kind classified (no-coord => FLATTENED, IC-12) and flattened parity xfail flipped; merge-state machine green (224 merge/lane/recovery tests); only F-008 xfail remains
- 2026-06-10T04:19:39Z – claude:opus:reviewer-renata:reviewer – shell_pid=3994747 – Started review via action command
- 2026-06-10T04:26:08Z – user – shell_pid=3994747 – Moved to planned
- 2026-06-10T04:56:07Z – claude:opus:python-pedro:implementer – shell_pid=4010062 – Started implementation via action command
- 2026-06-10T05:11:39Z – claude:opus:python-pedro:implementer – shell_pid=4010062 – Cycle-2: #1771 fixed — retrospect record relocated to tracked kitty-specs/<slug>/retrospective.yaml; writer/lifecycle/summary/CLI readers updated + back-compat read-fallback for legacy .kittify records; 7 test files updated; committable-path test (git check-ignore) added; #1735 events-surface work intact; ruff/mypy clean (zero net new), retrospect+merge+parity green
- 2026-06-10T05:12:24Z – claude:opus:reviewer-renata:reviewer – shell_pid=4032841 – Started review via action command
- 2026-06-10T05:17:36Z – user – shell_pid=4032841 – Cycle-2 review passed: #1771 fixed (record relocated to tracked home, committable per git check-ignore); cycle-1 #1735/flattened intact
