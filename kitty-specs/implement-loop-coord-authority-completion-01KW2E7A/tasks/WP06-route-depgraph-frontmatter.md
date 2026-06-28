---
work_package_id: WP06
title: Route dependency-graph / WP-frontmatter readers
dependencies:
- WP01
- WP05
requirement_refs:
- FR-004
- FR-006
- FR-009
tracker_refs: []
planning_base_branch: design/coord-authority-remediation-2160
merge_target_branch: design/coord-authority-remediation-2160
branch_strategy: Planning artifacts for this mission were generated on design/coord-authority-remediation-2160. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into design/coord-authority-remediation-2160 unless the human explicitly redirects the landing branch.
subtasks:
- T026
- T027
- T028
- T029
- T030
phase: Phase 2 - Routing
assignee: ''
shell_pid: ''
agent: claude
history:
- at: '2026-06-26T18:29:45Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/
create_intent:
- tests/integration/test_coord_loop_depgraph.py
execution_mode: code_change
owned_files:
- src/specify_cli/cli/commands/agent/tasks_dependency_graph.py
- src/specify_cli/cli/commands/agent/tasks_parsing_validation.py
- src/specify_cli/cli/commands/validate_tasks.py
- tests/integration/test_coord_loop_depgraph.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP06 – Route dependency-graph / WP-frontmatter readers

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

## Objectives & Success Criteria

Route the remaining in-loop PRIMARY-kind reads in the dependency-graph / WP-frontmatter /
ready-for-review readers; remove the pins. This drains the in-loop residual set to zero.

Done when, on the WP01 coord fixture: the dependency-graph build, the research-artifact
read, and the validate-tasks frontmatter read resolve **primary**; status legs stay
**coord**; pins removed; the dir-read gate shows **zero in-loop residuals** (only the
#2185/#2186/#2167-ticketed out-of-scope pins remain); RED-first tests pass.

## Context & Constraints

- Spec FR-004, FR-006, FR-009. Sites (verify live): `tasks_dependency_graph.py:118`
  (in-loop `build_dependency_graph` caller), `tasks_parsing_validation.py:935`
  (research-artifact `git status` read), `validate_tasks.py:113` (**MIXED**: WP-frontmatter
  lane PRIMARY + canonical status lane COORD).
- **Do NOT change `build_dependency_graph`'s signature** — route by passing the primary
  planning dir at the `:118` caller. Out-of-loop callers `merge/ordering:95` and
  `policy/merge_gates:238` must remain on their current path (TICKET-class; C-009).
- **FR-009:** remove the dep-graph cluster pins from the WP02-owned ratchet file this commit.
- This is the last routing WP — confirm the in-loop residual set is fully drained.

## Branch Strategy

- **Strategy**: already-confirmed
- **Planning base branch**: design/coord-authority-remediation-2160
- **Merge target branch**: design/coord-authority-remediation-2160

## Subtasks & Detailed Guidance

### Subtask T026 – Route the in-loop `build_dependency_graph` caller
- At `tasks_dependency_graph.py:118`, pass `resolve_planning_read_dir(...,WORK_PACKAGE_TASK)`
  as the dir argument. Do not touch the function signature.

### Subtask T027 – Route `tasks_parsing_validation.py:935`
- Route the research-artifact read to the seam (kind = the appropriate PRIMARY planning kind).

### Subtask T028 – Split `validate_tasks.py:113` mixed read
- The `scan_all_tasks_for_mismatches(feature_dir)` helper compares WP-frontmatter lane
  (PRIMARY) vs canonical status lane (COORD). Pass both surfaces (frontmatter from primary,
  status from coord) rather than one dir; do not collapse them.

### Subtask T029 – Remove the dep-graph cluster pins (same commit)
- Delete the corresponding `_DIR_READ_KNOWN_RESIDUALS` entries (out-of-map edit to WP02's file).
- **Verify (squad correction):** after this, the only remaining pins are (a) the out-of-scope
  #2185 / #2186 / #2167 clusters and (b) WP02's **C-008 permanent-coord** category (the
  `implement`/`review` review-cycle sub-artifact reads that legitimately stay coord). I.e.
  zero *routable in-loop* residuals remain — NOT literally zero pins. Cross-check the removed
  pins against the WP03–WP06 routed-site + test inventory (1:1 map, FR-009).

### Subtask T030 – RED-first per-site tests (both legs)
- On the WP01 fixture, assert primary frontmatter/research reads + coord status reads.
  File: `test_coord_loop_depgraph.py`. Prove RED pre-fix.

## Test Strategy

`PWHEADLESS=1 pytest tests/integration/test_coord_loop_depgraph.py tests/architectural/test_gate_read_literal_ban.py -q`.
Also assert the in-loop pin set is empty (only ticketed pins remain).

## Risks & Mitigations

- **Signature change leaks to out-of-loop callers** → route at the caller only; assert
  `merge/ordering`/`policy/merge_gates` paths unchanged.
- **Collapsing the validate_tasks mixed read** → wrong lane comparison. Mitigation: pass both
  surfaces; per-leg test.

## Review Guidance

- Confirm zero in-loop residuals remain (only #2185/#2186/#2167 pins).
- Confirm `build_dependency_graph` signature unchanged.

## Activity Log

- 2026-06-26T18:29:45Z – system – Prompt created.
- 2026-06-27T03:19:12Z – user – flat
- 2026-06-27T03:19:14Z – user – flat; route dep-graph/frontmatter readers
- 2026-06-27T03:50:27Z – claude – dep-graph/frontmatter routed (4e2ae5f61); in-loop pins drained to 0; 28 + 88 broad passed
- 2026-06-27T04:04:15Z – user – renata cycle-1 review
- 2026-06-27T04:04:17Z – user – Approved (flat; arbiter after renata cycle-1). Functional routing was correct (graph→PRIMARY, status→COORD, research→PRIMARY via RESEARCH kind, sig unchanged, in-loop pins drained to 0). renata BLOCKING fix applied + verified (1adc45f17): dead-threaded status_dir + false C-001-split prose removed; validate_tasks routed single-leg PRIMARY (correct — scan_all_tasks is frontmatter-vs-subdir, not MIXED); test renamed+RED-first; research.md mis-classification corrected. 28+4 passed.
