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
planning_base_branch: feat/name-vs-authority-remediation-01KTYGTE
merge_target_branch: feat/name-vs-authority-remediation-01KTYGTE
branch_strategy: Planning artifacts for this mission were generated on feat/doctrine-glossary-consolidation-01KTNWFC (mission retargeted to feat/name-vs-authority-remediation-01KTYGTE on 2026-06-12 — PR #1895 branch frozen for review). During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/name-vs-authority-remediation-01KTYGTE unless the human explicitly redirects the landing branch.
created_at: '2026-06-12T18:32:00Z'
subtasks:
- T001
- T002
- T003
- T004
- T005
phase: Phase 1 - Independent lanes
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "1583575"
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
- 2026-06-12T19:22:31Z – claude:opus:python-pedro:implementer – shell_pid=1468206 – Assigned agent via action command
- 2026-06-12T19:37:56Z – claude:opus:python-pedro:implementer – shell_pid=1468206 – P0 quickfixes + pins complete. FIXES: FR-001/#1884 is_committed now verifies via placement-authority ref (resolve_placement_only().ref) on primary-HEAD miss, caller threads ref in mission.py:1821; FR-003/#1885-residual query_current_state raises structured QueryModeValidationError (error_code+next_step) not silent unknown stub; FR-013/#1896 peer-field regex tolerates bullet markers + describe_technical_context_gap names offending format. PINS (FR-004): tests/integration/test_p0_pinning_regressions.py (8 tests) pin #1889 flattened->primary no-crash + bare-unresolvable->structured error, #1885 symptom mid8->real type, #1885 residual structured error, #1884 coord-only-committed->committed; tests/specify_cli/missions/test_substantive_gate_formats.py (8 tests). EVIDENCE: each fix mutation-verified (mutate->pin red, revert->green): #1884 pin red on authority_ref-ignore mutation; #1885-residual pin red on stub-revert mutation; #1896 pin red on bullet-intolerant-regex mutation. TESTS: 16 new pass; tests/next/ 489 pass; boundary+sync+architectural(350) green. LINT: ruff exit 0 + mypy 'no issues' on all 7 touched files. OUT-OF-MAP (justified): next_cmd.py (surface structured error_code/next_step JSON, T003 caller seam) + tests/next/test_query_mode_unit.py (NFR-001 pin-of-defective-behavior exception: updated test_missing_feature_dir to assert structured error, matching sibling 'fail loudly not unknown' tests).
- 2026-06-12T19:38:35Z – claude:opus:reviewer-renata:reviewer – shell_pid=1583575 – Started review via action command
- 2026-06-12T19:44:59Z – user – shell_pid=1583575 – P0-rigor review PASS. C-002: coordination/status_transition.py + cli/commands/merge.py UNTOUCHED (git log base..HEAD empty). C-GATE-1: is_committed authority_ref path uses _resolve_planning_placement->resolve_placement_only (SAME resolver as writer) + git cat-file -e <ref>:<rel>; fail-closed verified (authority_ref None -> unchanged primary False verdict; cat-file miss -> False). C-ERR-1: both query_current_state unknown-stubs replaced by QueryModeValidationError(error_code+next_step); no remaining silent query stub (line 2423 is decide_next blocked-with-reason, out of scope). Mutation proofs: reverting #1896 regex flips 3 pins RED; ignoring authority_ref flips #1884 C-GATE-1 pin RED (fail-closed guards stay green); both restored clean. NFR-001 rename: old test_missing_feature_dir pinned the DEFECTIVE silent-unknown stub FR-003 removes (not a legit contract) -> valid pin-of-defect exception, documented. FR-004 fixtures use REAL git (init/branch/worktree/commit), not mocks. Tests: 16 new + tests/next/ 489 + tests/architectural/ 350 all green. ruff clean on 7 touched files; touched files mypy-clean (4 mypy errors are pre-existing in untouched _internal_runtime/{schema,planner}.py, confirmed on base). NFR-002: one net-new noqa BLE001 on intentional fail-open except (NFR-003 semantics; sibling pattern x6 in same file; inline rationale) -> permitted-exception, NOTE not blocker. No dead code (describe_technical_context_gap called at mission.py:1929). No new --feature flags.
