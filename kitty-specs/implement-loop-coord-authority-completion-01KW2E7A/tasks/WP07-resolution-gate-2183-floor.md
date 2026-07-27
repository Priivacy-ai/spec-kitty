---
work_package_id: WP07
title: 'Resolution gate: #2183 fold + floor recompute'
dependencies:
- WP06
requirement_refs:
- C-005
- FR-011
- FR-012
- NFR-001
tracker_refs: []
planning_base_branch: design/coord-authority-remediation-2160
merge_target_branch: design/coord-authority-remediation-2160
branch_strategy: Planning artifacts for this mission were generated on design/coord-authority-remediation-2160. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into design/coord-authority-remediation-2160 unless the human explicitly redirects the landing branch.
subtasks:
- T031
- T032
- T033
- T034
phase: Phase 3 - Gate
assignee: ''
shell_pid: ''
agent: claude
history:
- at: '2026-06-26T18:29:45Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: tests/architectural/
create_intent: []
execution_mode: code_change
owned_files:
- tests/architectural/test_resolution_authority_gates.py
- tests/architectural/resolution_gate_allowlist.yaml
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP07 – Resolution gate: #2183 fold + floor recompute

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

## Objectives & Success Criteria

Fold #2183 and recompute the routed-canonicalizer floor against the **post-fix** live census
(which rose as WP03–WP06 routed sites — hence the WP06 dependency).

Done when: `is_def_use_canonical` recognizes the `_canonicalize_bare_modern_handle` fold seam;
the 4 hand-sanctioned entries auto-route; the permanent allowlist shrinks **7→3**;
`ROUTED_CANONICALIZER_FLOOR` is set strictly below the post-fix live census (not hardcoded 31);
the shrink-only twin-guard passes; a gate self-mutation test covers the new discriminator branch.

## Context & Constraints

- Spec FR-011, FR-012, NFR-001, C-005. Plan IC-01b + IC-05.
- The 4 auto-routing entries: `resolve_handle_to_read_path:950/972/1023`,
  `_stored_topology_best_effort:1208` (all via `_canonicalize_bare_modern_handle`).
- **Keep** the other 3 permanent sanctions — they use raw parameters (not a self-fold):
  `_canonicalize_bare_modern_handle:454` (raw param), `read_primary_meta:820` (bare param),
  `MissionStatus._find_meta_path:533` (uses `resolve_bare_modern_mission_dir_name`).
- **Floor math:** pre-mission floor 27, live was 31; after WP03–WP06 routing + the 4
  bare-modern auto-routes the live census is higher — **compute it, set floor strictly below**
  (NFR-002 anti-vacuous; the guard is `floor < live`). Document the computed number.
- Behavior-preserving (C-005): the discriminator change must not alter runtime resolution.
- Depends on WP06 so the routed census is final before the floor is pinned.

## Branch Strategy

- **Strategy**: already-confirmed
- **Planning base branch**: design/coord-authority-remediation-2160
- **Merge target branch**: design/coord-authority-remediation-2160

## Subtasks & Detailed Guidance

### Subtask T031 – Teach `is_def_use_canonical` the bare-modern fold
- Add `BARE_MODERN_FOLD_SEAM = "_canonicalize_bare_modern_handle"`; extend the callee-name
  check to `in (CANONICAL_FOLD_SEAM, BARE_MODERN_FOLD_SEAM)` in `_names_assigned_from_fold`
  (or the equivalent discriminator).

### Subtask T032 – Auto-route the 4 entries; assert allowlist == exactly 3
- Remove the 4 now-auto-detected entries from `resolution_gate_allowlist.yaml`; **assert
  `len(permanent_allowlist) == 3`** (shrink-only alone would pass at 4 — squad MED) AND that
  the exact 4 named fold entries (`:950/972/1023/1208`) were removed and the 3 raw-param
  permanents remain. Tighten the `canonicalizer_baseline` scalar accordingly.

### Subtask T033 – Recompute the floor with a tightness bound
- Compute the post-fix live routed count; set `ROUTED_CANONICALIZER_FLOOR` to a documented
  integer. **Gate-assert BOTH bounds** `live − MARGIN <= floor < live` (MARGIN a named
  constant): the lower bound prevents a loose ratchet (squad MED), the upper is the existing
  anti-vacuous guard. Do NOT hardcode 31.

### Subtask T034 – Gate self-mutation test for the new branch
- Add a test exercising the new discriminator branch (a site routed via the bare-modern fold
  is classified canonical / auto-routed), so the branch has direct coverage (NFR-003).

## Test Strategy

`PWHEADLESS=1 pytest tests/architectural/test_resolution_authority_gates.py -q`. Confirm
allowlist length 3, floor < live, twin-guard green, the new branch covered.

## Risks & Mitigations

- **Stripping a raw-param permanent sanction** by mistake → gate breaks. Mitigation: the 3
  permanents are enumerated above; assert they remain.
- **Hardcoding the floor** → stale/vacuous. Mitigation: compute from the live census; document.

## Review Guidance

- Confirm only the 4 fold-routed entries were removed.
- Confirm the floor is computed (strictly below live), not a magic 31.

## Activity Log

- 2026-06-26T18:29:45Z – system – Prompt created.
- 2026-06-27T04:04:30Z – user – flat
- 2026-06-27T04:04:32Z – user – flat; #2183 discriminator fold + floor recompute
- 2026-06-27T05:06:38Z – claude – 23bf23ac4 + docstring fix; renata APPROVE
- 2026-06-27T05:06:40Z – user – renata
- 2026-06-27T05:06:42Z – user – Approved by reviewer-renata (flat): #2183 FR-011/012. Discriminator folds bare-modern seam (test-only, C-005); allowlist 7→3 asserted ==3, 4 entries provably auto-route, 3 raw-param permanents un-foldable; floor 31 with tight bounds (35-4<=31<35); branch-coverage test red-first-capable; coord re-pins coherent at 14. 35 passed. LOW stale docstring (17→14) fixed.
