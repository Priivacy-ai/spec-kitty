---
work_package_id: WP02
title: Coord-routing predicate + frozenset consolidation (FR-005)
dependencies:
- WP01
requirement_refs:
- FR-005
- NFR-005
tracker_refs: []
planning_base_branch: feat/single-authority-topology-cleanup
merge_target_branch: feat/single-authority-topology-cleanup
branch_strategy: Planning artifacts for this mission were generated on feat/single-authority-topology-cleanup. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/single-authority-topology-cleanup unless the human explicitly redirects the landing branch.
subtasks:
- T005
- T006
- T007
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "1489853"
history:
- Created by /spec-kitty.tasks 2026-06-23
agent_profile: python-pedro
authoritative_surface: src/mission_runtime/
create_intent: []
execution_mode: code_change
owned_files:
- src/mission_runtime/context.py
- src/mission_runtime/resolution.py
- src/runtime/next/runtime_bridge.py
- src/specify_cli/coordination/surface_resolver.py
- src/specify_cli/coordination/status_transition.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile
Read `src/doctrine/agent_profiles/built-in/python-pedro.agent.yaml` and adopt its
directives/tactics (or `/ad-hoc-profile-load python-pedro`). State which you applied.

## Objective
**FR-005** — collapse the six coord-routing predicates and the four verbatim
`{COORD, LANES_WITH_COORD}` frozensets to **ONE** pure
`routes_through_coordination(topology)` and **ONE** shared frozenset constant.
This is Tidy-First: tidy the routing predicate *before* WP04 collapses `.kind`
onto it. Behavior-neutral.

## Context (live anchors)
- 4 verbatim frozensets, two distinct names + an inline literal:
  `resolution.py:139` `_COORD_ROUTING_TOPOLOGIES`, `surface_resolver.py:91`
  `_COORD_SURFACE_TOPOLOGIES`, `runtime_bridge.py:78`, inline `status_transition.py:590`.
- 6 predicates answering "does this topology route through coordination?":
  `destination_kind_for_topology`, `_topology_uses_coord_surface`,
  `_topology_routes_through_coord`, `_mission_routes_through_coordination`,
  `_read_contract_routes_through_coordination`, `routes_through_coordination`
  (`context.py:122/131`, the latter currently takes `CommitTarget` and reads `.kind`).

## Subtasks
### T005 — ONE canonical frozenset
Pick the canonical home (`context.py` or a shared constants module near the
topology enum) and define a single `_COORD_ROUTING_TOPOLOGIES = frozenset({MissionTopology.COORD, MissionTopology.LANES_WITH_COORD})`.
Replace the 4 duplicate definitions/inline literal with imports of the canonical
constant. Hoist per S1192.

### T006 — ONE predicate
Reduce the 6 predicates to a single pure `routes_through_coordination(topology: MissionTopology) -> bool`
over the canonical frozenset. Repoint every caller of the other 5 predicates to it.
NOTE: `routes_through_coordination` currently reads `target.kind` — its
signature/body change to take topology is **entangled with WP04's `.kind`
removal**; in THIS WP, introduce the topology-taking form and have the existing
`.kind`-taking call sites compute the topology to pass (a transitional shim is
acceptable here; WP04 removes the last `.kind` read). Keep it behavior-identical.

### T007 — KEEP map (NFR-005, C-001/C-002)
Do NOT touch and explicitly verify-unchanged (add/keep a pinning test or a
comment mapping each):
- the genuine-fallback **relays** at `status_transition.py:599`,
  `surface_resolver.py:562`, `resolution.py:765` — each reads stored topology
  first and relays via `classify_topology` only on the **exception arm**. These
  are NOT predicates and must NOT be folded into `routes_through_coordination`
  (projection ≠ exception-arm fallback).
- the husk short-circuit `surface_resolver.py:667-678` (`_husk_is_authoritative_surface`, C-001).

## Campsite (#1970)
In the touched files: hoist repeated literals (S1192), remove dead one-call
helpers left after the predicate merge, fix lint/type debt on touched lines.

## Test approach (doctrine standard)

> **Test approach (doctrine standard — DIRECTIVE_034/036/041, #2071 CTn).** Assert the **observable contract** — returned value, resolved surface/ref, persisted JSONL/`meta.json`, CLI `--json` payload, or gate verdict — **never** the internal call graph or "collaborator X was invoked" (CT4/D036). Build mission fixtures by delegating to the **production creation seam** (`create_mission_core` / the existing `_stored_topology` helper), not a hand-rolled `meta.json` writer that rots (CT3); use **production-shaped data** — a real 26-char ULID + 8-char mid8, never a short placeholder (testing-principles). Any architectural guard/ratchet anchors keys on `_ratchet_keys.composite_key` (qualname + token-line) or an AST node — **never `file.py:NNN`** — and reuses `audit.py`/`_ratchet_keys.py` (CT1); resolve symbols by AST, never by grepping a string that collides with a surviving flag (NFR-003). Any xfail/skip is a **RED-by-design ATDD pin that names the WP that drains it** and is removed (not re-keyed) when the fix lands — never a defect mask (CT2). Prove behavior-neutrality via the **differential cell over the `(topology × transient)` matrix** PLUS at least one **absolute** assertion (see below) — never a brittle golden count of sites/LOC/refs (CT5); prefer a **tightening ratchet** (count only drops, keyed by symbol-set) over a fixed `== N`. **Pair every "allow / passes / absorbs / ignores-residue" assertion with its negative control** ("still-blocks / still-raises / wrong-topology-differs") — one-sided gate tests let the over-allow mutant survive. When a touched test goes red, classify it (stale→re-point preserving setup / fakeable→delete / valid→fix the product) and establish causation by **code-path coupling, not git-blame** (D041).

### WP02-specific test-DoD
- **(a) CT1 re-key clause.** If this WP's edits drift the `composite_key` of any entry in `tests/architectural/test_single_mission_surface_resolver.py::_ALLOWLISTED_RAW_JOINS` or the `test_no_write_side_rederivation.py` seed, re-key the entry onto the new `composite_key` with rationale — never bump a line number, never add a raw `file.py:NNN` key, never re-pin the C-012-carved `status_transition.py:336` `_current_branch` fallback (re-key only; the drain is #1716's).
- **(b) 4-member truth-table test.** Add a standalone test for `routes_through_coordination(topology)` asserting all four enum members: `COORD`/`LANES_WITH_COORD` → True; `SINGLE_BRANCH`/`LANES` → False.
- **(c) T007 KEEP-map as executable pin.** Make the T007 KEEP-map an **executable pin** — a test driving each relay's EXCEPTION arm and asserting it relays via `classify_topology` — and drop the "OR a comment" option.

## Definition of Done
- One frozenset, one predicate; the other 3 frozenset defs + 5 predicates gone or
  reduced to thin call-throughs that are then removed.
- A 4-member truth-table test pins `routes_through_coordination` over all topology
  members; the T007 KEEP-map is an executable relay-exception-arm pin (no comment-only
  form); any drifted ratchet entry is re-keyed on `composite_key`, never line-bumped.
- `ruff`/`mypy` clean on owned files; full `tests/` green (behavior-neutral);
  the WP01 differential cell still green.
- KEEP map: the 3 relays + husk short-circuit demonstrably unchanged.

## Branch Strategy
`feat/single-authority-topology-cleanup` base/merge. Lane B (shared with
WP03-WP07, sequential). Worktree from `lanes.json`.

## Reviewer guidance
Confirm no C-002 relay was collapsed into the predicate. Confirm the frozenset is
defined exactly once. Reject if a relay's exception-arm semantics changed.

## Activity Log

- 2026-06-23T07:37:52Z – claude:opus:python-pedro:implementer – shell_pid=1326489 – Assigned agent via action command
- 2026-06-23T08:12:05Z – claude:opus:python-pedro:implementer – shell_pid=1326489 – Ready: 6->1 coord-routing predicate + 4->1 frozenset (FR-005); C-002 relays (status_transition:599, surface_resolver:562, resolution:765) + C-001 husk short-circuit pinned UNCHANGED via executable exception-arm tests. CT1 ratchets re-keyed (composite-key allowlist + untrusted-path inventory), never line-bumped. ruff+mypy clean diff-scoped; arch suite green (sole failure test_pytest_marker_convention is pre-existing/env-coupled, proven via stash). --force: lane base is 51 commits behind feat but the gap is status-chore + one unrelated #2091 runtime-identity fix; a full rebase replays stripped planning artifacts (flat-mission hazard). Reviewer to rebase at integration.
- 2026-06-23T08:13:21Z – claude:opus:reviewer-renata:reviewer – shell_pid=1489853 – Started review via action command
- 2026-06-23T08:20:20Z – user – shell_pid=1489853 – Review passed (--force: lane 67 commits behind feat is the known stale-base; reviewer verified WP02 disjoint from #2091, rebase required at integration). T005 ONE frozenset (context.py:128; 4 dups gone, AST-pinned exactly-one). T006 ONE predicate routes_through_coordination; single surviving .kind read clearly marked WP04-transitional shim. T007 KEEP set intact — 3 C-002 relays (status_transition:599/surface_resolver:562/resolution:765) + C-001 husk short-circuit unchanged, each pinned by executable EXCEPTION-arm tests with coord/flat negative controls; prefers-stored-over-relay test kills the collapse mutant. 4-member truth table + differential (topology×kind) cell assert real values, not tautology. CT1 re-keys (489→494/494→499 _coord_mid8 + inventory.md) are composite-key (qualname+token-line) re-points, NOT raw file.py:NNN bumps; WP01 CommitTargetKind AST guard green. #2091 NOT clobbered/reverted — disjoint functions; #2091 absent from lane base so integration needs git rebase onto feat (conflict only on import line + _mission_routes_through_coordination; both fixes preserved). pytest 114 passed/1 known xfail; architectural 28+15 passed; ruff clean no new suppressions; remaining mypy errors pre-existing outside WP02 hunk. Behavior-neutral: all 4 topologies match pre-WP02 per-site logic (verified directly against lane src).
