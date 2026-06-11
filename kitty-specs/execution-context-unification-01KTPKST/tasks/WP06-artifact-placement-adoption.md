---
work_package_id: WP06
title: Artifact-placement adoption (Cluster D)
dependencies:
- WP04
requirement_refs:
- FR-004
- FR-009
tracker_refs: []
planning_base_branch: fixups/code-engine-stabilization
merge_target_branch: fixups/code-engine-stabilization
branch_strategy: Planning artifacts for this mission were generated on fixups/code-engine-stabilization. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fixups/code-engine-stabilization unless the human explicitly redirects the landing branch.
subtasks:
- T019
- T020
- T021
- T022
phase: Phase 2 - Placement
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "3910461"
history:
- at: '2026-06-09T17:17:15Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: ''
authoritative_surface: src/specify_cli/cli/commands/
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/cli/commands/implement.py
- src/specify_cli/cli/commands/agent/mission.py
role: ''
tags: []
task_type: implement
---

# Work Package Prompt: WP06 – Artifact-placement adoption

## ⚡ Do This First: Load Agent Profile
Use `/ad-hoc-profile-load`; if none set, pick an implementer profile for `code_change` on `src/specify_cli/cli/commands/`.

---

## Objectives & Success Criteria
- Resolve planning-artifact + analysis placement via the context's **ArtifactPlacementFragment** at the two sites that deadlocked the dogfood:
  - `implement._ensure_planning_artifacts_committed_git` (#1816) — implement-claim no longer blocks on a primary↔coord planning-artifact split.
  - `record-analysis` in `agent/mission.py` (#1814) — no coord-residue deadlock; also apply the `_find_feature_directory` structured-error fix here (this file is owned by WP06).
- Make analysis-report staleness keying context-aware (#1764).
- **Done when (SC-2):** a fresh mission reproduces NEITHER the paused 01KTNWFC `record-analysis` nor `implement`-claim blocker; WP01 placement parity flips green.

## Context & Constraints
- Design: `spec.md` FR-004/FR-009; `plan.md` IC-05; `contracts/...` C-PLACE-1; `data-model.md` ArtifactPlacementFragment + CommitTarget.
- **This WP unblocks the paused mission 01KTNWFC** — validate against its recorded blockers (`work/MISSION_01KTNWFC_PAUSED.md`).
- Under flattened topology `CommitTarget.kind == flattened` → there is no primary↔coord split to reconcile; the fix must hold for both flattened and coord topologies.

## Branch Strategy
- **Planning base / merge target**: `fixups/code-engine-stabilization`. Populated by finalize-tasks.

## Subtasks & Detailed Guidance
### T019 — `implement` placement via context (#1816)
- `_ensure_planning_artifacts_committed_git` resolves the placement ref from the context, not independent primary/coord logic.
### T020 — `record-analysis` context-aware (#1814) + `_find_feature_directory` fix
- record-analysis resolves its read/write surface + dirty-tree check against the context's placement ref (no primary-dirty-vs-coord-owned conflict). Apply the WP04 structured-error behaviour to the `_find_feature_directory` call in this file.
### T021 — analysis-report staleness context-aware (#1764)
- Key analysis-report freshness off the resolved context so it is not falsely stale across CWDs.
### T022 — SC-2 repro + parity
- Add an integration test (or fixture) proving the 01KTNWFC blockers do not reproduce; flip WP01 placement parity.

## Test Strategy
- SC-2 repro test; WP01 placement parity green; `ruff`+`mypy` zero issues. See `quickstart.md` SC-2.

## Risks & Mitigations
- *Resume-blocker mission* → correctness over speed; verify against the actual paused-mission state before claiming SC-2.

## Review Guidance
- Recommended: **reviewer-renata**. Confirm SC-2 repro is genuine (not a mocked-away check); confirm no independent placement logic remains.

## Activity Log
- 2026-06-09T17:17:15Z – system – Prompt created.
- 2026-06-10T03:08:47Z – claude:opus:python-pedro:implementer – shell_pid=3879266 – Assigned agent via action command
- 2026-06-10T03:24:59Z – claude:opus:python-pedro:implementer – shell_pid=3879266 – WP06 done: artifact-placement resolved via context ArtifactPlacementFragment/CommitTarget (C-PLACE-1). T019 implement-claim placement via context (#1816); T020 record-analysis dirty-tree preflight context-aware (coord residue no longer deadlocks, #1814) + _find_feature_directory routed through read primitive w/ structured ActionContextError (no silent fallback, C-CTX-4); T021 staleness context-aware via canonical feature_dir+main repo_root (#1764); T022 SC-2 repro (6 tests, incl. negative guards) proves both 01KTNWFC blockers do NOT reproduce — and WP01 placement parity xfail flipped green. ruff clean; mypy clean on changed lines (1 pre-existing unrelated line-229 error). Remaining xfails (WP05/WP07/WP08) left intact.
- 2026-06-10T03:25:43Z – claude:opus:reviewer-renata:reviewer – shell_pid=3910461 – Started review via action command
- 2026-06-10T03:33:37Z – user – shell_pid=3910461 – Review passed (reviewer-renata): #1816/#1814 fixes are REAL not weakened. (1) placement_ref==destination_ref confirmed via resolution.py _assemble_artifact_placement_fragment(branch_ref.destination_ref) + parity test asserts equality (passes, no xfail). (2) #1814 negative guards proven by mutation: disabling dirty-check fails both guards; over-broad filter (if False) fails genuine-edit guard; SC-2 6/6 pass with REAL git porcelain. (3) legacy None-fallback preserves prior meta-derived path, does NOT reintroduce split (C-004 documented). (4) _find_feature_directory raises structured ActionContextError, all 4 callers catch (Value|ActionContext)Error, 5 contract tests pass. (5) #1764 feature_dir+main repo_root CWD-invariant. (6) ruff clean; mypy clean on new code (line-229 error pre-existing, confirmed on base, not in WP06 hunks); 8 pre-existing test failures confirmed identical with WP06 src reverted to base. (7) C-005 honored: one CommitTarget, no parallel placement logic. No dead code, no silent returns, no --feature flags.
