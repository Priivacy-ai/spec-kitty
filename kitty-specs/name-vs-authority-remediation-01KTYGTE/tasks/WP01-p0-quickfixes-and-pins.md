---
work_package_id: WP01
title: P0 quick fixes + verification pins (FR-001/003/004/013)
dependencies: []
requirement_refs:
- FR-001
- FR-003
- FR-004
- FR-013
tracker_refs: []
planning_base_branch: feat/doctrine-glossary-consolidation-01KTNWFC
merge_target_branch: feat/doctrine-glossary-consolidation-01KTNWFC
branch_strategy: Planning artifacts for this mission were generated on feat/doctrine-glossary-consolidation-01KTNWFC. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/doctrine-glossary-consolidation-01KTNWFC unless the human explicitly redirects the landing branch.
created_at: '2026-06-12T18:32:00Z'
subtasks:
- T001
- T002
- T003
- T004
- T005
phase: Phase 1 - Independent lanes
assignee: ''
agent: ''
history:
- at: '2026-06-12T18:32:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: ''
authoritative_surface: src/specify_cli/missions/_substantive.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/missions/_substantive.py
- src/specify_cli/cli/commands/agent/mission.py
- src/runtime/next/runtime_bridge.py
- tests/integration/test_p0_pinning_regressions.py
- tests/specify_cli/missions/test_substantive_gate_formats.py
role: ''
tags: []
task_type: implement
---

# Work Package Prompt: WP01 – P0 quick fixes + verification pins

## ⚡ Do This First: Load Agent Profile
Load the assigned profile via `spec-kitty agent profile show <profile-id> --all` (pick the best implementer match if none assigned) and operate within its boundaries before reading further.

---
## Objectives & Success Criteria
Close the small live P0 roots and pin the already-fixed ones:
- **T001 (ATDD FIRST, FR-004):** pinning regression tests for the two VERIFIED-FIXED P0s — #1889 (flattened fixture: meta declares `coordination_branch`, worktree absent → resolver returns primary, structured error for bare-slug, NO crash) and #1885 symptom (fully-planned coord fixture → `query_current_state` returns the real mission type, not `unknown`). Repro recipes: `research/research-p0-rootcauses.md`. New test file `tests/integration/test_p0_pinning_regressions.py`. These must pass on the CURRENT tree (they pin fixes from PR #1850).
- **T002 (FR-001, #1884 ROOT-α):** `setup-plan`'s committed-spec gate verifies against the placement authority: extend `_substantive.is_committed` (or its caller seam) so presence is checked via `git cat-file -e <resolve_placement_only(repo_root, slug).ref>:<rel>` when the primary-HEAD check misses. ATDD: fixture with spec committed ONLY on a coord branch → gate passes. NOTE: the caller line lives in `cli/commands/agent/mission.py:~1821` — that file is NOT owned here; if the fix needs a caller-side change, make the MINIMAL out-of-map edit with a one-line rationale.
- **T003 (FR-003, #1885 residual):** `runtime_bridge.py:3068-3087` — unresolvable handle returns a structured error (StructuredError subclass or the bridge's structured payload with `error_code` + `next_step`), never `mission=unknown, reason=None`.
- **T004 (FR-013, #1896):** `_has_substantive_technical_context` — peer-field regex tolerates bullet markers (`^\s*(?:[-*]\s+)?\*\*`); blocked_reason names the offending format when fields exist but fail to parse. Pinning test: bulleted-but-real Technical Context passes (new test file `test_substantive_gate_formats.py`).
- **T005:** evidence pack — proof notes for #1889/#1885 closure (repro outputs + pinning-test ids) recorded in the handoff note.

## Context & Constraints (read before coding)
- Design (absolute): `kitty-specs/name-vs-authority-remediation-01KTYGTE/{spec.md, plan.md, data-model.md, contracts/authority-seams.md}` + the mission `research/` — **`research-authority-seams.md` is NORMATIVE** for seam APIs/site lists/decision table; `research-p0-rootcauses.md` for defect mechanics; `research-fold-cluster.md` for ready deltas.
- NFR-003 binding: fail-closed over fallback — never introduce a silent name-derived fallback.
- ATDD: pinning/contract tests FIRST where the WP names them. New code: ruff + mypy zero issues, zero suppressions. No existing passing test modified (NFR-001; pin-of-defective-behavior exceptions justified per case).
- C-002: in `coordination/status_transition.py` and `cli/commands/merge.py`, touch ONLY the ranges this WP names — upstream coord-merge-stabilization owns adjacent ranges.
- move-task/mark-status: run from the PRIMARY checkout with the FULL mission slug (`name-vs-authority-remediation-01KTYGTE`). No kitty-specs commits on the lane.

## Definition of Done
T001 pins green on the current tree; #1884 fixture flips red→green at T002; #1885 residual + #1896 fixed with pins; ruff/mypy clean; focused suites + `tests/architectural/ -q` green.

## Review Guidance
reviewer-renata. Verify the pins genuinely repro the original defects (mutate the fix → pin fails); verify T002 reads via the SAME authority the writer uses (C-GATE-1).

## Activity Log
- 2026-06-12T18:32:00Z – system – Prompt created.
