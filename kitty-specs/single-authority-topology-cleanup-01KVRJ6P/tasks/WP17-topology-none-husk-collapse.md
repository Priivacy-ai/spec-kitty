---
work_package_id: WP17
title: topology=None husk-arm collapse + 6th predicate + load_meta (06b) (FR-004/005/006)
dependencies:
- WP06
- WP08
requirement_refs:
- C-001
- C-003
- C-004
- C-005
- FR-004
- FR-005
- FR-006
- NFR-001
- NFR-004
- NFR-005
tracker_refs: []
planning_base_branch: feat/single-authority-topology-cleanup
merge_target_branch: feat/single-authority-topology-cleanup
branch_strategy: Planning artifacts for this mission were generated on feat/single-authority-topology-cleanup. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/single-authority-topology-cleanup unless the human explicitly redirects the landing branch.
subtasks:
- T016
- T029
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "2002719"
history:
- 'Created by sizing-squad re-slice 2026-06-23 (split 06b of WP06). paula coherence weld: the corrupt-meta C-004 arm stays raising here, asserted at the point the absent-field arms are collapsed.'
agent_profile: python-pedro
authoritative_surface: src/specify_cli/missions/
create_intent: []
execution_mode: code_change
owned_files:
- src/specify_cli/missions/_read_path_resolver.py
- src/specify_cli/coordination/surface_resolver.py
- src/mission_runtime/resolution.py
- src/specify_cli/coordination/status_transition.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile
Read `src/doctrine/agent_profiles/built-in/python-pedro.agent.yaml` and adopt its
directives/tactics (or `/ad-hoc-profile-load python-pedro`). State which you applied.

## Objective
**FR-004 husk collapse (06b of 2) + FR-005 6th predicate + FR-006 4-file load_meta.**
WP06 (06a) threaded a concrete non-optional `MissionTopology` at the read-path
boundary, making the ~8 `topology is None` husk-arms **dead**. This WP:
1. **removes** those dead absent-field husk-arms (KEEPING the corrupt-meta raise);
2. completes the FR-005 consolidation by collapsing the **6th** coord-routing
   predicate that lives in this WP's owned file (WP02 couldn't reach it);
3. converts the 4 topology files' `load_meta` calls to WP08's canonical reader.

## Context (live anchors + boundary discipline)
- ~8 `topology is None` husk-arms: `_read_path_resolver.py:148/361/724/895` +
  siblings (`surface_resolver`, `candidate_feature_dir`). After WP06's boundary
  absorption threads a CONCRETE topology, `topology is None` is never true → these
  arms are dead. Remove them.
- **BOUNDARY DISCIPLINE (C-004)**: collapse ONLY the **absent-field** arms (the
  meta-reader returns `None` for a missing `topology` → classify). The
  **corrupt/unreadable-meta** arm (`load_meta`/read raises) STAYS a typed fallback
  — you cannot classify without readable meta. None vs raise = different paths.
- **WP08 is a declared dependency** so the canonical polymorphic `load_meta` is in
  this worktree's base — convert directly; no `# TODO(WP08-canonical)` deferral.

## Subtasks
### T016 — Collapse the ~8 husk-arms (absent-field only) + the 6th predicate
Remove the `if topology is None: <consult coordination husk on disk>` band-aids at
the ~8 sites. KEEP, and verify unchanged:
- the husk short-circuit `surface_resolver.py:667-678` (C-001, the `df79f76f4`
  data-loss defense — distinct from these arms; it defends the
  worktree-feature-dir-passed-in entry);
- the 5-hop feature-dir path `candidate_feature_dir_for_mission`→…→`resolve_handle_to_read_path`
  (C-003, each hop ticket-anchored #1718/#1589/#1848/#2062);
- the transient probes (`probe_coord_state` EMPTY/DELETED, #1718/#1848, C-005 —
  orthogonal to shape);
- the corrupt-meta exception arm (C-004).

**6th coord-routing predicate (completes FR-005).** The
`_topology_routes_through_coord` predicate at `_read_path_resolver.py:138`
(callers `:340/:650/:894`) is the 6th of the six coord-routing predicates FR-005
collapses — but it lives in THIS WP's owned file, not WP02's, so WP02 cannot
reach it. Repoint its callers to the canonical `routes_through_coordination(topology)`
(WP02's single predicate) and delete the local `_topology_routes_through_coord`,
so the "6 → 1" consolidation is actually complete (it otherwise silently survives).

### T029 — Convert the 4 files' load_meta calls (FR-006)
Convert the `load_meta` calls in the 4 lane-B topology files owned here
(`resolution.py` @401/716/782, `surface_resolver.py` @651/692,
`status_transition.py` @359, `_read_path_resolver.py` @771/787) to the canonical
polymorphic `load_meta` from WP08, choosing `allow_missing`/`on_malformed` to
reproduce each site's CURRENT behavior exactly. Remove the now-dead local readers.
(These 4 files are EXCLUDED from WP09/WP10's C2 sweep — they are converted here so
the topology lane owns its own meta-reader migration.)

## Campsite (#1970)
Remove the dead husk-arm helpers + their stale comments; the dead local meta-readers;
fix lint/type debt; hoist S1192 in touched files.

## Test approach (doctrine standard)

> **Test approach (doctrine standard — DIRECTIVE_034/036/041, #2071 CTn).** Assert the **observable contract** — returned value, resolved surface/ref, persisted JSONL/`meta.json`, CLI `--json` payload, or gate verdict — **never** the internal call graph or "collaborator X was invoked" (CT4/D036). Build mission fixtures by delegating to the **production creation seam** (`create_mission_core` / the existing `_stored_topology` helper), not a hand-rolled `meta.json` writer that rots (CT3); use **production-shaped data** — a real 26-char ULID + 8-char mid8, never a short placeholder (testing-principles). Any architectural guard/ratchet anchors keys on `_ratchet_keys.composite_key` (qualname + token-line) or an AST node — **never `file.py:NNN`** — and reuses `audit.py`/`_ratchet_keys.py` (CT1); resolve symbols by AST, never by grepping a string that collides with a surviving flag (NFR-003). Any xfail/skip is a **RED-by-design ATDD pin that names the WP that drains it** and is removed (not re-keyed) when the fix lands — never a defect mask (CT2). Prove behavior-neutrality via the **differential cell over the `(topology × transient)` matrix** PLUS at least one **absolute** assertion (see below) — never a brittle golden count of sites/LOC/refs (CT5); prefer a **tightening ratchet** (count only drops, keyed by symbol-set) over a fixed `== N`. **Pair every "allow / passes / absorbs / ignores-residue" assertion with its negative control** ("still-blocks / still-raises / wrong-topology-differs") — one-sided gate tests let the over-allow mutant survive. When a touched test goes red, classify it (stale→re-point preserving setup / fakeable→delete / valid→fix the product) and establish causation by **code-path coupling, not git-blame** (D041).

### WP17-specific test-DoD
- **(a) Corrupt/malformed-meta cell (C-004 over-collapse killer).** Add a cell: an un-backfilled mission with **malformed `meta.json`** → the read path **raises the typed corrupt-meta error**, NOT silently classified to PRIMARY. This kills the over-collapse mutant (collapsing the corrupt-arm too) — the absent-field collapse must not touch it. Pair it with the absent-field positive case (no `topology` key → concrete topology, never None) as the negative/positive control pair.
- **(b) KEEP set as executable pins.** Pin the C-001 husk short-circuit (`surface_resolver.py:667-678`), the C-003 5-hop feature-dir path, and the C-005 transient probes (`probe_coord_state` EMPTY/DELETED) by **executable assertions**, not comments — the collapse must not clip them.
- **(c) 6th-predicate consolidation proof.** After the repoint, assert by **AST/symbol** that `_topology_routes_through_coord` no longer exists and its callers route through the single `routes_through_coordination` — reuse WP02's consolidation ratchet (tighten its symbol-set, do not add a new `file.py:NNN` key).
- **(d) load_meta contract cells.** For each distinct (missing, malformed) contract among the 4 converted files, assert **both arms' observable RETURN value** (None / raise / `{}`) — NOT the `load_meta` call args (CT4).
- **(e) CT1 re-key clause.** Re-key any drifted `composite_key` ratchet entry with rationale; never line-bump.

## Definition of Done
- The ~8 absent-field husk-arms collapsed; the 6th predicate
  (`_topology_routes_through_coord`) deleted and its callers repointed to
  `routes_through_coordination`; the 4 files' `load_meta` calls on the canonical reader.
- Corrupt-meta still **raises** (C-004) — asserted alongside the absent-field
  positive case; KEEP set (C-001 husk short-circuit, C-003 5-hop path, C-005
  transient probes) pinned by executable assertions, unchanged.
- The 6th-predicate-gone proof is AST/symbol-based (tighten WP02's ratchet); the
  load_meta conversions are behavior-neutral per the contract cells.
- `ruff`/`mypy` clean; full `tests/` green. Net LOC down.

## Branch Strategy
`feat/single-authority-topology-cleanup`. Lane B (sequential, after WP06). Worktree from `lanes.json`.

## Reviewer guidance
Reject if the corrupt-meta arm was collapsed (C-004) — the malformed-meta cell must
raise. Reject if any C-001/C-003/C-005 KEEP item changed, or if
`_topology_routes_through_coord` survives (the 6→1 consolidation must be complete).
Spot-check 2 load_meta conversions reproduce the exact missing/malformed contract.

## Activity Log

- 2026-06-23T11:25:54Z – claude:opus:python-pedro:implementer – shell_pid=1946945 – Started implementation via action command
- 2026-06-23T11:53:39Z – claude:opus:python-pedro:implementer – shell_pid=1946945 – Ready: 6th predicate _topology_routes_through_coord DELETED (6->1 FR-005 complete), 3 callers repointed to canonical routes_through_coordination; absent-field absorbed at all read boundaries (resolve_feature_dir_for_slug threaded) so topology=None is now ONLY the corrupt-meta C-004 path which still RAISES; dead local _declares_coordination_branch json.loads reader + import json removed; 4 files' load_meta on WP08 canonical polymorphic reader with explicit contract args; KEEP set (C-001 husk short-circuit, C-003 5-hop, C-005 EMPTY/DELETED probes) pinned by executable assertions; 17 WP17 cells + 533 target tests green incl NFR-002; ruff clean; mypy clean on 3/4 owned files (status_transition no-any-return pre-existing at lane base); CT1 re-key 1244->1240 qualname-anchored + inventory.md
- 2026-06-23T11:54:54Z – claude:opus:reviewer-renata:reviewer – shell_pid=2002719 – Started review via action command
- 2026-06-23T12:02:23Z – user – shell_pid=2002719 – Review passed: resolve_feature_dir_for_slug topology-threading is behavior-NEUTRAL (verified empirically: backfilled COORD->coord worktree, un-backfilled flattened->PRIMARY; makes leg consistent with sibling candidate_feature_dir_for_mission, absent-field case = WP06 FR-004 win, not new behavior). C-004 corrupt-meta RAISES: read_primary_meta uses load_meta default on_malformed=raise->typed ValueError on guarded leg; lenient legs catch->None probe-fallback (distinct paths). 6th predicate _topology_routes_through_coord DELETED (AST-confirmed gone in src/), 3 callers route through canonical routes_through_coordination. load_meta conversions behavior-neutral (defaults made explicit+documented, except-ValueError handlers preserved; _declares_coordination_branch on_malformed=none preserves silent-degrade). KEEP set C-001/C-003/C-005 pinned by executable assertions. WP08 cherry-pick clean (mission_metadata.py-only). 493 tests pass; ruff clean; mypy 5 pre-existing no-any-return (was 6, WP17 removed one). CT1 re-key 1244->1240 qualname-anchored+rationale in test+inventory.md.
