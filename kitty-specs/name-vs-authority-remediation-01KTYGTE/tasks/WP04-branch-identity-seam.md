---
work_package_id: WP04
title: 'Branch-identity authority seam (FR-006, closes #1860 class)'
dependencies: []
requirement_refs:
- FR-006
tracker_refs: []
planning_base_branch: feat/doctrine-glossary-consolidation-01KTNWFC
merge_target_branch: feat/doctrine-glossary-consolidation-01KTNWFC
branch_strategy: Planning artifacts for this mission were generated on feat/doctrine-glossary-consolidation-01KTNWFC. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/doctrine-glossary-consolidation-01KTNWFC unless the human explicitly redirects the landing branch.
created_at: '2026-06-12T18:32:00Z'
subtasks:
- T013
- T014
- T015
phase: Phase 1 - Independent lanes
assignee: ''
agent: ''
history:
- at: '2026-06-12T18:32:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: ''
authoritative_surface: src/specify_cli/lanes/branch_naming.py
execution_mode: code_change
model: ''
owned_files: []
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
- **T014:** migrate the owned consumer sites per the normative site list — legacy-shape-only parsers `core/vcs/detection.py:143-176` (currently silently drops ALL mid8 missions!), `sync.py:823` regex, `lanes/manifest.py:156`, `orchestrator_api/commands.py:771` workspace compose, `lanes/compute.py` ×3 composes, `lanes/recovery.py` ×2. Each: name proposes, grammar+meta dispose. Verify exact paths against the research doc (e.g. which sync module hosts :823) before editing.
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
