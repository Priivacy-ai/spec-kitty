---
work_package_id: WP04
title: 'Branch-identity authority seam (FR-006, closes #1860 class)'
dependencies: []
requirement_refs:
- FR-006
tracker_refs: []
planning_base_branch: feat/name-vs-authority-remediation-01KTYGTE
merge_target_branch: feat/name-vs-authority-remediation-01KTYGTE
branch_strategy: Planning artifacts for this mission were generated on feat/doctrine-glossary-consolidation-01KTNWFC (mission retargeted to feat/name-vs-authority-remediation-01KTYGTE on 2026-06-12 — PR #1895 branch frozen for review). During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/name-vs-authority-remediation-01KTYGTE unless the human explicitly redirects the landing branch.
created_at: '2026-06-12T18:32:00Z'
subtasks:
- T013
- T014
- T015
phase: Phase 1 - Independent lanes
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "1640931"
history:
- at: '2026-06-12T18:32:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: ''
authoritative_surface: src/specify_cli/lanes/branch_naming.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/lanes/branch_naming.py
- src/specify_cli/lanes/compute.py
- src/specify_cli/lanes/recovery.py
- src/specify_cli/core/vcs/detection.py
- src/specify_cli/cli/commands/sync.py
- src/specify_cli/manifest.py
- src/specify_cli/orchestrator_api/commands.py
- tests/specify_cli/lanes/test_branch_naming*.py
role: ''
tags: []
task_type: implement
---

# Work Package Prompt: WP04 – Branch-identity authority seam

## ⚡ Do This First: Load Agent Profile
Load the assigned profile via `spec-kitty agent profile show <profile-id> --all` (pick the best implementer match if none assigned) and operate within its boundaries before reading further.

---
## Objectives & Success Criteria
Per `research-authority-seams.md` (NORMATIVE — seam 2; no new module):
- **T013 (ATDD FIRST):** extend `lanes/branch_naming.py` with fail-closed `mission_branch_name_required(...)` + `BranchIdentityUnresolved` (StructuredError subclass, `error_code="BRANCH_IDENTITY_UNRESOLVED"`, next_step), fed `mission_id` from meta. **Dual-era rule (binding):** legacy `\d{3}-` and mid8-era names both RESOLVE; only unresolvable-modern rejects. Unit tests: both eras, the `mid8=''` bare-slug case, the unresolvable case.
- **T014:** migrate the owned consumer sites per the normative site list — legacy-shape-only parsers `core/vcs/detection.py:143-176` (currently silently drops ALL mid8 missions!), `sync.py:823` regex, `src/specify_cli/manifest.py:156 (feature-branch name-shape scan; NOT lanes/)`, `orchestrator_api/commands.py:771` workspace compose, `lanes/compute.py` ×3 composes, `lanes/recovery.py` ×2. Each: name proposes, grammar+meta dispose. Verify exact paths against the research doc (e.g. which sync module hosts :823) before editing.
- **T015:** #1860 regression test (mid8 HANDLE through the resolution path → works or structured error, never raw-path 'no canonical status') + dual-era integration tests.

## Context & Constraints (read before coding)
- Design (absolute): `kitty-specs/name-vs-authority-remediation-01KTYGTE/{spec.md, plan.md, data-model.md, contracts/authority-seams.md}` + the mission `research/` — **`research-authority-seams.md` is NORMATIVE** for seam APIs/site lists/decision table; `research-p0-rootcauses.md` for defect mechanics; `research-fold-cluster.md` for ready deltas.
- NFR-003 binding: fail-closed over fallback — never introduce a silent name-derived fallback.
- ATDD: pinning/contract tests FIRST where the WP names them. New code: ruff + mypy zero issues, zero suppressions. No existing passing test modified (NFR-001; pin-of-defective-behavior exceptions justified per case).
- C-002: in `coordination/status_transition.py` and `cli/commands/merge.py`, touch ONLY the ranges this WP names — upstream coord-merge-stabilization owns adjacent ranges.
- move-task/mark-status: run from the PRIMARY checkout with the FULL mission slug (`name-vs-authority-remediation-01KTYGTE`). No kitty-specs commits on the lane.

## Definition of Done
Zero shape-decomposition outside branch_naming in owned files; legacy parsers resolve BOTH eras; #1860 class pinned; suites + architectural green; ruff/mypy clean.

## Review Guidance
reviewer-renata. Adversarial: feed a legacy `042-foo` AND a modern `<slug>-<mid8>` branch through every migrated site; prove no silent None/drop remains.

## Activity Log
- 2026-06-12T18:32:00Z – system – Prompt created.
- 2026-06-12T19:23:09Z – claude:opus:python-pedro:implementer – shell_pid=1470114 – Assigned agent via action command
- 2026-06-12T19:45:04Z – claude:opus:python-pedro:implementer – shell_pid=1470114 – FR-006 branch-identity seam: added BranchIdentityUnresolved (StructuredError, BRANCH_IDENTITY_UNRESOLVED) + mission_branch_name_required() in lanes/branch_naming.py (dual-era: legacy NNN- and mid8 resolve, unresolvable-modern raises). Migrated cluster-B sites: detection.py worktree parse, sync.py lane parse, manifest.py branch discovery (all via parse_mission_slug_from_branch, was \d{3}- only), compute.py x3 (mission_branch_name mission_id=...), recovery.py x2 (mission_branch_name_required from meta, fail-closed). orchestrator_api:771 left as-is (legacy workspace-path, not branch-identity; STOP-hatch recorded). ATDD grammar tests + #1860 dual-era regression suite (21 new tests). ruff clean, mypy 0 new errors (87 pre-existing tree-wide), architectural suite 350 passed, dead-symbol gate green. Commit 71e8705e4.
- 2026-06-12T19:45:51Z – claude:opus:reviewer-renata:reviewer – shell_pid=1640931 – Started review via action command
- 2026-06-12T19:52:43Z – user – shell_pid=1640931 – Review PASSED (reviewer-renata). FR-006 branch-identity seam sound. (a) STOP-hatch orchestrator_api/commands.py:771 EXEMPTION SOUND: it composes f'{mission}-{wp}' for a .worktrees/ workspace-path label, contains NO 'kitty/mission-' literal and interpolates {mission}/{wp} not {slug}; WP09 ratchet (§4.2 scans JoinedStr with 'kitty/mission-' + {mission_slug}/{slug}) will NOT match it. Not a branch-identity site; correctly left untouched. (b) DUAL-ERA over-rejection PROBE PASSED: legacy NNN- slugs and mid8-era slugs both RESOLVE at every migrated seam (parser, composer, compute_lanes B5, recovery _resolve_mission_branch, manifest discovery), only modern-bare-slug-no-mission_id raises BranchIdentityUnresolved; verified in code AND 11-test regression suite feeding 042-foo + foo-01KNXQS9 through each seam. (c) manifest.py legacy bare-NNN fallback is era-correct: kitty/mission- branches route through dual-era parse_mission_slug_from_branch FIRST; the branch[0].isdigit() fallback only fires for bare non-kitty NNN- branches (legacy), never re-deriving names for modern missions (NFR-003 honored). C-002: zero edits to status_transition.py/merge.py/aggregate.py. compute.py threads raw mission_id (None->legacy) + _empty_manifest converts slug-sentinel back to None. mypy 87==base (the 2 isolated-file StructuredError->Any errors are a follow_imports=skip artifact, absent in whole-package check). ruff clean. 21 new tests + architectural 350 + 139 dependent + 352 manifest/skills + 32 vcs all green. NFR-001: no existing test modified. Test placement tests/lanes/ + tests/regression/ matches canonical convention (owned-glob tests/specify_cli/lanes/ is a planning-artifact typo; canonical test_branch_naming.py lives in tests/lanes/). NON-BLOCKING note for record: deprecated legacy .worktrees/<feature>-WP## dir shape no longer resolves VCS via detection.py (pre-lanes.json layout, outside dual-era slug rule, no live user) - acceptable. recovery.py:134 git-branch glob is pre-existing, not a B-site.
