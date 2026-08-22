---
work_package_id: WP01
title: '#3460 topology-predicate anti-divergence guard'
dependencies: []
requirement_refs:
- FR-004
planning_base_branch: rc3-lane-allocation-single-seam-01M0GGX8
merge_target_branch: rc3-lane-allocation-single-seam-01M0GGX8
branch_strategy: Planning artifacts for this mission were generated on rc3-lane-allocation-single-seam-01M0GGX8. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into rc3-lane-allocation-single-seam-01M0GGX8 unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-rc3-lane-allocation-single-seam-01M0GGX8
base_commit: 2520e7ad4243857b18f3b6c26eb9e14df33b855a
created_at: '2026-08-22T05:59:25.799714+00:00'
subtasks:
- T001
- T002
- T003
history: []
agent_profile: python-pedro
authoritative_surface: tests/specify_cli/coordination/
create_intent:
- tests/specify_cli/coordination/test_topology_predicate_authority.py
execution_mode: code_change
owned_files:
- tests/specify_cli/coordination/test_topology_predicate_authority.py
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave
according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

---

## Objective

Pin `_transaction_topology_available` (`src/specify_cli/coordination/status_transition.py:142`) as the
**single** topology-availability authority, and prevent any future site from re-introducing a
`coordination_branch is None` **surrogate gate** that disagrees with it (#3460, FR-004).

**This WP ships NO source change.** The post-plan squad verified (and you must re-confirm) that all four
residual `coordination_branch is (not) None` sites are legitimate value-reads / already-SSOT-gated, so
there is nothing to remove. The deliverable is an **anti-divergence guard test** plus an
**exclusion-pin** test — enforcement, not behavior. Closure of #3460 is *"single-authority, pinned by
guard"*, never *"removed surrogate gates"*.

## Context

- Authority: `_transaction_topology_available(identity, mission_slug)` — `status_transition.py:142`;
  already gates the transactional emit/batch paths (`:1008`, `:1114`, `:1319`, `:1538`).
- **DO NOT TOUCH** `emit_inner_state_changed_transactional` (`status_transition.py:1481`): it
  deliberately keeps the bare `coordination_branch is None` check. Its docstring (`~:1428-1447`) records
  that reusing the authority "was tried and reverted" — the predicate's legacy-meta fallback arm is
  trivially true for coord-less 083+ missions and would regress #2939
  (`tests/integration/test_2939_move_task_clean_tree_after_rejection.py::test_flat_topology_annotation_still_lands`).
- Residual sites to re-confirm as value-reads (NOT gates): `src/mission_runtime/resolution.py:1284`,
  `:1362`, `:1460`; `src/mission_runtime/context.py:70` (inside `classify_topology` — the classifier itself).
- Contract: `contracts/topology-predicate-and-3536.md` (Part A). Research: `research.md` D3.

## Subtasks

### T001 — `test_topology_predicate_is_single_authority` (red-first via synthetic fixture)
Create `tests/specify_cli/coordination/test_topology_predicate_authority.py`. Because the invariant
already holds on `main`, prove the test is non-vacuous the same way WP3's guard does:
1. Build a **synthetic AST fixture** — a Python source string defining a routing function that gates on
   `coordination_branch is None` in a transactional-routing position.
2. Assert the checker (an `ast`-based scan for a `coordination_branch is None` test used as a routing gate
   in the transactional emit paths of `status_transition.py`) **flags** the synthetic fixture, naming its
   `file:line` + rule.
3. Assert the checker run over the **live** `status_transition.py` transactional paths is **clean** — with
   the `emit_inner_state_changed_transactional` off-axis path explicitly EXEMPTED (see T002).
This makes the test fail if someone deletes the exemption logic or the checker (non-vacuous) and pass on
current clean code.

### T002 — exclusion-pin test (#2939 preservation)
In the same file, add `test_emit_annotation_keeps_narrow_predicate`: assert
`emit_inner_state_changed_transactional` still routes on the bare `coordination_branch is None` (not the
shared authority). This is the regression guard so a future "single-authority cleanup" cannot re-break
#2939. Reference the docstring rationale in a comment.

### T003 — census-verdict docstring
Add a module docstring (or a data table in the test) recording each residual site's verdict with the
one-line reason it is a value-read, not a surrogate gate: `resolution.py:1284/1362/1460`,
`context.py:70`. Cite the SSOT/classifier reasoning so a later reader sees why WP1 changed no source.

## Definition of Done
- `test_topology_predicate_authority.py` exists; both tests pass on current `main`.
- The synthetic-fixture assertion proves non-vacuity (removing the exemption/checker makes T001 red).
- `#2939` guard (`test_flat_topology_annotation_still_lands`) still green: run
  `.venv/bin/python -m pytest tests -k "flat_topology_annotation_still_lands" -q`.
- No source file changed (this is a test-only WP). `ruff` + `mypy` clean on the new test.

## Risks
- Vacuous test → mitigated by the synthetic fixture.
- Accidentally asserting the emit-annotation site uses the authority → that would (correctly) fail; keep
  the exemption.

## Reviewer Guidance
Confirm the checker is a positive/structural assertion (not a substring grep that passes vacuously), that
the emit exclusion is pinned, and that no source changed. Verify the census verdicts against the cited
lines.
