---
work_package_id: WP12
title: 'Accept gates topology-aware (FR-008/FR-009, #2084/#2085a)'
dependencies:
- WP01
- WP04
requirement_refs:
- C-010
- FR-008
- FR-009
tracker_refs: []
planning_base_branch: feat/single-authority-topology-cleanup
merge_target_branch: feat/single-authority-topology-cleanup
branch_strategy: Planning artifacts for this mission were generated on feat/single-authority-topology-cleanup. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/single-authority-topology-cleanup unless the human explicitly redirects the landing branch.
subtasks:
- T023
- T024
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "1777650"
history:
- Created by /spec-kitty.tasks 2026-06-23
agent_profile: python-pedro
authoritative_surface: src/specify_cli/acceptance/
create_intent:
- tests/specify_cli/test_acceptance.py
execution_mode: code_change
owned_files:
- src/specify_cli/acceptance/__init__.py
- tests/specify_cli/test_acceptance.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile
Read `src/doctrine/agent_profiles/built-in/python-pedro.agent.yaml` and adopt its
directives/tactics (or `/ad-hoc-profile-load python-pedro`). State which you applied.

## Objective
Two accept-gate fixes that strand finished missions:
- **FR-008 (#2084)** — make the `accept` dirty-tree check **topology-aware**:
  under ACTUAL coordination topology it ignores recognized coordination residue,
  while still blocking author-owned files and a flat mission's real primary artifacts.
- **FR-009 (#2085a)** — derive unchecked-tasks completion from WP terminal status.

## Context (converge, do NOT widen)
- The reference-correct pattern ALREADY EXISTS at
  `cli/commands/agent/mission.py:862` (`_enforce_analysis_report_write_preflight`):
  `if routes_through_coordination(placement_ref): <filter via is_coordination_artifact_residue_path>`.
  FR-008 must **converge** the accept dirty gate onto that pattern — NOT widen the
  hardcoded `ACCEPT_OWNED_PATHS` frozenset (`acceptance/__init__.py:71`).
- `is_coordination_artifact_residue_path` (`mission_runtime/artifacts.py:113`) +
  `routes_through_coordination` are imported, not new.
- `_find_unchecked_tasks` (`acceptance/__init__.py:396`) currently demands ticked
  `tasks.md` checkboxes. C-010: the acceptance-MATRIX gate is genuine verification
  — leave it UNCHANGED.

## Subtasks
### T023 — FR-008 topology-aware dirty gate
In the accept dirty-tree check: when the mission routes through coordination
(stored topology via `routes_through_coordination`), exclude paths recognized by
`is_coordination_artifact_residue_path(path, mission_slug=…)` from the dirty set,
in addition to the existing `ACCEPT_OWNED_PATHS`. Keep blocking author-owned files
(e.g. `spec.md`) and — critically — a FLAT mission's real primary artifacts (the
topology gate is what distinguishes them). Add tests: (a) coord-topology mission
with only residue → dirty gate passes; (b) same residue paths under a flat mission
→ still blocks; (c) author-owned `spec.md` under coord → still blocks.

### T024 — FR-009 derive completion from WP status
In `_find_unchecked_tasks` (or its caller): when every WP is `approved`/`done`,
treat the unchecked-tasks gate as satisfied without requiring ticked `tasks.md`
checkboxes. Do NOT alter the acceptance-matrix gate (C-010). Add a test: an
orchestrated mission (all WPs approved/done, checkboxes unticked) passes the
unchecked-tasks gate; a mission with a non-terminal WP still reports unchecked.

## Campsite (#1970)
De-pin / fix any **fakeable** accept tests in this file in-slice (assertions that
pass without exercising the gate). Hoist S1192; fix lint/type debt.

## Test approach (doctrine standard)

> **Test approach (doctrine standard — DIRECTIVE_034/036/041, #2071 CTn).** Assert the **observable contract** — returned value, resolved surface/ref, persisted JSONL/`meta.json`, CLI `--json` payload, or gate verdict — **never** the internal call graph or "collaborator X was invoked" (CT4/D036). Build mission fixtures by delegating to the **production creation seam** (`create_mission_core` / the existing `_stored_topology` helper), not a hand-rolled `meta.json` writer that rots (CT3); use **production-shaped data** — a real 26-char ULID + 8-char mid8, never a short placeholder (testing-principles). Any architectural guard/ratchet anchors keys on `_ratchet_keys.composite_key` (qualname + token-line) or an AST node — **never `file.py:NNN`** — and reuses `audit.py`/`_ratchet_keys.py` (CT1); resolve symbols by AST, never by grepping a string that collides with a surviving flag (NFR-003). Any xfail/skip is a **RED-by-design ATDD pin that names the WP that drains it** and is removed (not re-keyed) when the fix lands — never a defect mask (CT2). Prove behavior-neutrality via the **differential cell over the `(topology × transient)` matrix** PLUS at least one **absolute** assertion (see below) — never a brittle golden count of sites/LOC/refs (CT5); prefer a **tightening ratchet** (count only drops, keyed by symbol-set) over a fixed `== N`. **Pair every "allow / passes / absorbs / ignores-residue" assertion with its negative control** ("still-blocks / still-raises / wrong-topology-differs") — one-sided gate tests let the over-allow mutant survive. When a touched test goes red, classify it (stale→re-point preserving setup / fakeable→delete / valid→fix the product) and establish causation by **code-path coupling, not git-blame** (D041).

### WP12-specific test-DoD
- **WP04 is a declared dependency (frontmatter).** T023's flat-mission-blocks cell needs WP04's topology-gated residue predicate (`is_coordination_artifact_residue_path` returning **flat→False**). Today the predicate is always-true, so without WP04 the cell would be RED-by-construction and an implementer might weaken it to pass. With WP04 in the base, the flat→still-blocks cell is genuinely exercisable.
- **The 5 tests drive the accept gate's observable verdict** — passes / blocks + which paths — not the predicate-call wiring.
- **T024 non-terminal cell uses a near-terminal status.** The "non-terminal WP still reports unchecked" cell uses a **near-terminal** status (`in_review` / `for_review`), not `planned` — `planned` is trivially non-terminal and would pass even a broken gate; the near-terminal boundary is the real mutation-killer.

## Definition of Done
- Both gates fixed with the 5 acceptance tests above; acceptance-matrix gate
  untouched (C-010). `ruff`/`mypy` clean; full `tests/` green.
- The flat-mission-still-blocks cell genuinely exercises WP04's flat→False residue
  predicate (WP04 dep declared); the 5 tests assert observable verdict; T024's
  non-terminal cell uses a near-terminal status (`in_review`/`for_review`), not
  `planned`.

## Branch Strategy
`feat/single-authority-topology-cleanup`. Lane E. Worktree from `lanes.json`.

## Reviewer guidance
Confirm FR-008 converges on the `mission.py:862` predicate pattern and did NOT
just widen `ACCEPT_OWNED_PATHS`. Confirm the flat-mission-still-blocks test exists
(the topology gate is the whole point). Confirm the acceptance-matrix gate is
unchanged.

## Activity Log

- 2026-06-23T09:55:44Z – claude:opus:python-pedro:implementer – shell_pid=1734389 – Assigned agent via action command
- 2026-06-23T10:11:19Z – claude:opus:python-pedro:implementer – shell_pid=1734389 – Ready: accept dirty-gate topology-aware (coord residue ignored, flat still blocks); unchecked-tasks from WP terminal status; acceptance-matrix gate untouched (C-010)
- 2026-06-23T10:16:17Z – claude:opus:reviewer-renata:reviewer – shell_pid=1777650 – Started review via action command
- 2026-06-23T10:20:17Z – user – shell_pid=1777650 – Review passed: FR-008 converges on routes_through_coordination(placement_ref)+is_coordination_artifact_residue_path per mission.py:862 pattern, ACCEPT_OWNED_PATHS UNCHANGED, fail-closed on ActionContextError (NFR-003). FR-009 derives completion from WP terminal status via _all_work_packages_terminal; _find_unchecked_tasks stays a pure parser. C-010 matrix/lane-gate verdict UNTOUCHED (only docstring/comment hits). Both-sided cells real: coord-passes/flat-blocks use IDENTICAL plan.md edit differing only by stored topology, production-shaped ULID+mid8, assert observable summary.git_dirty; coord+source-edit and coord+scratch-file STILL block; FR-009 orchestrated passes vs near-terminal in_review/for_review STILL reports. Stale regression assertion re-pointed preserving coord-worktree-read intent via unchanged needs_clarification. 49 passed; ruff clean; mypy 5 pre-existing errors (identical on base, zero new).
