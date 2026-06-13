---
work_package_id: WP05
title: Cross-seam consumers + fabrication eradication (FR-007 + A/B residual sites)
dependencies:
- WP03
- WP04
requirement_refs:
- FR-007
tracker_refs: []
planning_base_branch: feat/name-vs-authority-remediation-01KTYGTE
merge_target_branch: feat/name-vs-authority-remediation-01KTYGTE
branch_strategy: Planning artifacts for this mission were generated on feat/doctrine-glossary-consolidation-01KTNWFC (mission retargeted to feat/name-vs-authority-remediation-01KTYGTE on 2026-06-12 — PR #1895 branch frozen for review). During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/name-vs-authority-remediation-01KTYGTE unless the human explicitly redirects the landing branch.
created_at: '2026-06-12T18:32:00Z'
subtasks:
- T016
- T017
- T018
- T019
phase: Phase 2 - Integration
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "1727186"
history:
- at: '2026-06-12T18:32:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: ''
authoritative_surface: src/specify_cli/status/aggregate.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/status/aggregate.py
- src/specify_cli/coordination/status_transition.py
- src/specify_cli/cli/commands/implement.py
- tests/integration/test_cross_seam_consumers.py
role: ''
tags: []
task_type: implement
---

# Work Package Prompt: WP05 – Cross-seam consumers + fabrication eradication

## ⚡ Do This First: Load Agent Profile
Load the assigned profile via `spec-kitty agent profile show <profile-id> --all` (pick the best implementer match if none assigned) and operate within its boundaries before reading further.

---
## Objectives & Success Criteria
Files needing BOTH seams (hence deps WP03+WP04 — your lane must contain both):
- **T016:** `status/aggregate.py` — migrate its cluster-A topology predicate (`:278-280`) to WP03's classifier AND its cluster-B site (`:669`) to WP04's grammar.
- **T017 (FR-007):** `coordination/status_transition.py:265` — the fabrication idiom names the ON-DISK transaction dir; route through WP04's authority or fail closed. C-002: touch ONLY this range + its topology predicate (`:114-125`) — upstream coord-merge-stab owns adjacent ranges; also preserve the #1848 deleted-branch carve-out (`:432-437`) exactly.
- **T018 (FR-007):** `cli/commands/implement.py:395` — same eradication.
- **T019:** integration tests: transaction-dir naming for a bare-slug mission (pre-fix would fabricate; post-fix resolves-or-raises); grep-zero fabrication idiom in owned files.

## Context & Constraints (read before coding)
- Design (absolute): `kitty-specs/name-vs-authority-remediation-01KTYGTE/{spec.md, plan.md, data-model.md, contracts/authority-seams.md}` + the mission `research/` — **`research-authority-seams.md` is NORMATIVE** for seam APIs/site lists/decision table; `research-p0-rootcauses.md` for defect mechanics; `research-fold-cluster.md` for ready deltas.
- NFR-003 binding: fail-closed over fallback — never introduce a silent name-derived fallback.
- ATDD: pinning/contract tests FIRST where the WP names them. New code: ruff + mypy zero issues, zero suppressions. No existing passing test modified (NFR-001; pin-of-defective-behavior exceptions justified per case).
- C-002: in `coordination/status_transition.py` and `cli/commands/merge.py`, touch ONLY the ranges this WP names — upstream coord-merge-stabilization owns adjacent ranges.
- move-task/mark-status: run from the PRIMARY checkout with the FULL mission slug (`name-vs-authority-remediation-01KTYGTE`). No kitty-specs commits on the lane.

## Definition of Done
Both fabrication sites dead; aggregate/status_transition/implement consume the seams; #1848 carve-out untouched (test proves); suites + architectural green.

## Review Guidance
reviewer-renata. Verify the C-002 range discipline with the diff; adversarial bare-slug transaction test.

## Activity Log
- 2026-06-12T18:32:00Z – system – Prompt created.
- 2026-06-12T20:08:24Z – claude:opus:python-pedro:implementer – shell_pid=1690609 – Assigned agent via action command
- 2026-06-12T20:29:47Z – claude:opus:python-pedro:implementer – shell_pid=1690609 – FR-007 + A/B residual sites complete. T016 aggregate.py: _is_coord_dir delegates to is_registered_coord_worktree (registry authority); unmaterialized gate uses is_under_worktrees_segment; cluster-B compose routes through mission_branch_name_required; removed unused _WORKTREES_SEGMENT. T017/T018: fabrication idiom eradicated -> new resolve_transaction_mid8 (dual-era, topology-gated fail-closed) in branch_naming.py. Empty mid8 (bare surface) when no coordination_branch (legacy/flattened/orphaned-event - preserves pre-fix routing); raises BranchIdentityUnresolved only when coord topology declared but mid8 unrecoverable. C-002 honored: status_transition touches only named range + import; #1848 carve-out untouched. T019: 10 cross-seam tests green (adversarial bare-slug, grep-zero idiom, aggregate dual-seam). Evidence: 529 affected-suite tests pass; ruff exit 0; mypy 82 baseline zero-new; full architectural suite (350) green; 7 remaining integration failures are PRE-EXISTING (fail identically on clean stashed branch).
- 2026-06-12T20:32:04Z – claude:opus:reviewer-renata:reviewer – shell_pid=1727186 – Started review via action command
- 2026-06-12T20:40:54Z – user – shell_pid=1727186 – Review passed (reviewer-renata). C-002 RANGE DISCIPLINE PASS: status_transition.py has exactly 2 WP05 hunks (import @22, fabrication @262-274); topology predicates @108-126 and #1848 deleted-branch carve-out @455-459 byte-identical/untouched; cli/commands/merge.py untouched entirely. ADJ-a (empty-mid8 degrade): LEGITIMATE not silent fallback — empty mid8 only when coordination_branch is None; ALL coord routing (status_transition._read_contract_from_transaction_target L438, _transaction_topology_available L92) is gated on coordination_branch presence, which is precisely the case where resolve_transaction_mid8 RAISES BranchIdentityUnresolved. Verified: empty mid8 can NEVER reach a coord worktree/branch write; it routes to primary_checkout/legacy-lane (BookkeepingTransaction._is_legacy_mission + _resolve_legacy_lane_destination = pre-fix CWD-branch behavior). NFR-003 honored. ADJ-c (out-of-map branch_naming.py): resolve_transaction_mid8 added with rationale (WP04 grammar home, DRY); honors dual-era (mid8/mission_id[:8]/mid8_from_slug all resolve; raise only coord+unrecoverable); 2 live prod callers (no dead code); in __all__ (C-007); behavioral coverage in test_cross_seam_consumers (coord-raises, meta-less-degrades, backfilled-resolves, legacy-bare, mid8-tail). ADJ-d (allowlist non-removal): WP05 does not touch test_no_dead_symbols or CoordinationBranchDeleted; transitive consumption via except StatusReadPathNotFound; dead-symbols ratchet still passes. ADJ-e (unmaterialized-coord gate): is_under_worktrees_segment is correct — registry cannot dispose a not-yet-materialized path (not resolved_dir.exists()); genuine R2 create->first-write shape gate, not convention-as-authority routing. Tests: 11 cross-seam GREEN; 376 status/topology/lanes GREEN; 350 architectural GREEN incl fabrication+dead-symbols+terminology ratchets; ruff exit 0 on all 5 touched files; mypy 87->87 ZERO NEW (baseline confirmed at base 76344b110; implementer's '82' stale but zero-new holds); grep-zero +00000000 idiom in 3 owned files AND repo-wide src; 8 integration failures (impl said 7) ALL confirmed PRE-EXISTING on base (spot-checked all 8), zero introduced by WP05 (NFR-001 PASS). Anti-patterns 1-8 PASS.
