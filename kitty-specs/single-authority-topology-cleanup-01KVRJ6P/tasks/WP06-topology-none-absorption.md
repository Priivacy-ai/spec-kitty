---
work_package_id: WP06
title: 'topology=None absorption: boundary + NFR-002 flip (06a) (FR-004)'
dependencies:
- WP05
- WP01
requirement_refs:
- C-001
- C-003
- C-005
- FR-004
- NFR-001
- NFR-002
- NFR-005
tracker_refs: []
planning_base_branch: feat/single-authority-topology-cleanup
merge_target_branch: feat/single-authority-topology-cleanup
branch_strategy: Planning artifacts for this mission were generated on feat/single-authority-topology-cleanup. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/single-authority-topology-cleanup unless the human explicitly redirects the landing branch.
subtasks:
- T015
- T017
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "1932020"
history:
- Created by /spec-kitty.tasks 2026-06-23
- 'Split into 06a (this WP: boundary absorption + NFR-002 flip) and 06b (WP17: husk-arm collapse + 6th-predicate + corrupt-meta C-004 guard + load_meta conversion), sizing squad 2026-06-23. paula coherence welds: NFR-002-flip ⊗ absorption stay together here; the corrupt-meta C-004 arm stays raising in WP17.'
agent_profile: python-pedro
authoritative_surface: src/specify_cli/missions/
create_intent: []
execution_mode: code_change
owned_files:
- src/specify_cli/missions/_read_path_resolver.py
- src/specify_cli/mission_read_path.py
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
**FR-004 — the one correctness improvement (06a of 2).** Acquire topology at the
read-path **boundary** via the absorbing API (`read_topology` / a pure
`classify_from_meta(meta, feature_dir)`) and thread a **concrete, non-optional**
`MissionTopology` downstream through the resolver chain. This makes the ~8
scattered `topology is None` husk-arms **dead** (WP17 then removes them) and flips
the WP01 **NFR-002 repro GREEN** — the un-backfilled flattened mission now
classifies-on-read to SINGLE_BRANCH/LANES → PRIMARY instead of the stale-coord
husk. This extends the #2062 fix to un-backfilled flattened missions and dissolves
the backfill-everything migration gate.

> **paula coherence weld (do NOT split):** the NFR-002 flip (T017) lives in the
> **same WP** as the boundary absorption (T015) — the repro goes green *because*
> the boundary now threads a concrete topology, so the proof must ship with the fix.
> **WP17 (06b)** then collapses the now-dead husk-arms, completes the 6th-predicate
> consolidation, keeps the corrupt-meta C-004 arm raising, and converts the 4 files'
> `load_meta` calls.

## Context (live anchors + boundary discipline)
- ~8 `topology is None` husk-arms: `_read_path_resolver.py:148/361/724/895` +
  siblings (`surface_resolver`, `candidate_feature_dir`). Their own comments admit
  they are bypassed whenever a stored topology exists.
- `read_topology(feature_dir)` (`backfill_topology.py:68`) already absorbs a
  missing field: returns the stored value, else `_derive_topology(...)` classifies
  once → a CONCRETE topology, never `None`.
- **BOUNDARY DISCIPLINE (C-004)**: collapse ONLY the **absent-field** arms (the
  meta-reader returns `None` for a missing `topology` → classify). The
  **corrupt/unreadable-meta** arm (`load_meta`/read raises) STAYS a typed fallback
  — you cannot classify without readable meta. None vs raise = different paths.

## Subtasks
### T015 — Absorb topology=None at the boundary
At the read-path boundary, replace the optional `topology: MissionTopology | None`
with a concrete value acquired via `read_topology` / `classify_from_meta`, and
thread it non-optional through the resolver chain. The callers stop passing
`None`; downstream signatures become non-optional.

### T017 — Flip NFR-002 green (the welded proof)
Remove the `xfail(strict=True)` from the WP01 NFR-002 repro (`@pytest.mark.xfail`
in `test_surface_resolution_equivalence.py` is WP01-owned — coordinate: this WP
edits that ONE marker line only, recorded as an out-of-map one-liner with
rationale, OR WP01 leaves a hook). The repro must now PASS (un-backfilled
flattened → PRIMARY) **because of T015's boundary absorption** — not because the
husk-arms were removed (those are still present-but-dead until WP17). This is the
correctness proof that must ship with the absorption.

> **Husk-arm collapse, the 6th-predicate consolidation, the corrupt-meta C-004
> guard, and the 4-file `load_meta` conversion are WP17 (06b).** They are dead-code
> removal + dedup that follow the boundary change; keeping them out of this WP holds
> the working set to the absorption + its proof.

## Campsite (#1970)
Remove the dead husk-arm helpers + their stale comments; fix lint/type debt; hoist
S1192 in touched files.

## Test approach (doctrine standard)

> **Test approach (doctrine standard — DIRECTIVE_034/036/041, #2071 CTn).** Assert the **observable contract** — returned value, resolved surface/ref, persisted JSONL/`meta.json`, CLI `--json` payload, or gate verdict — **never** the internal call graph or "collaborator X was invoked" (CT4/D036). Build mission fixtures by delegating to the **production creation seam** (`create_mission_core` / the existing `_stored_topology` helper), not a hand-rolled `meta.json` writer that rots (CT3); use **production-shaped data** — a real 26-char ULID + 8-char mid8, never a short placeholder (testing-principles). Any architectural guard/ratchet anchors keys on `_ratchet_keys.composite_key` (qualname + token-line) or an AST node — **never `file.py:NNN`** — and reuses `audit.py`/`_ratchet_keys.py` (CT1); resolve symbols by AST, never by grepping a string that collides with a surviving flag (NFR-003). Any xfail/skip is a **RED-by-design ATDD pin that names the WP that drains it** and is removed (not re-keyed) when the fix lands — never a defect mask (CT2). Prove behavior-neutrality via the **differential cell over the `(topology × transient)` matrix** PLUS at least one **absolute** assertion (see below) — never a brittle golden count of sites/LOC/refs (CT5); prefer a **tightening ratchet** (count only drops, keyed by symbol-set) over a fixed `== N`. **Pair every "allow / passes / absorbs / ignores-residue" assertion with its negative control** ("still-blocks / still-raises / wrong-topology-differs") — one-sided gate tests let the over-allow mutant survive. When a touched test goes red, classify it (stale→re-point preserving setup / fakeable→delete / valid→fix the product) and establish causation by **code-path coupling, not git-blame** (D041).

### WP06-specific test-DoD
- **(b) Cross-reference the absolute-mapping cell (over-collapse killer).** Confirm the "everything→PRIMARY" mutant dies: a **COORD** mission must still resolve → **coordination** (reference / re-assert the reworked `test_pure_stored_topology_projects_surface_placement` absolute pin from WP16). The absorption must not flatten COORD to PRIMARY.
- **(c) Red-first drain protocol.** Run the NFR-002 repro on the **pre-WP06 base** WITHOUT the xfail; confirm it is **RED because it resolves to the stale-coord husk** (the symptom, not a generic failure); then make it GREEN via T015's boundary absorption and **remove** the marker (drain — not re-key).
- **(d) CT1 re-key clause.** Re-key any drifted `composite_key` ratchet entry with rationale; never line-bump.
- **(e) KEEP set verified unchanged.** The boundary threading must not disturb the C-001 husk short-circuit (`surface_resolver.py:667-678`), the C-003 5-hop feature-dir path, or the C-005 transient probes — confirm by the existing tests staying green. (WP17 pins these by **executable** assertions when it collapses the now-dead arms.)

> **Corrupt-meta C-004 cell lives in WP17.** The absent-field-vs-corrupt-meta
> boundary (absorb the absent field; KEEP the corrupt-meta raise) is asserted where
> the arms are collapsed (WP17), so the over-collapse mutant is killed at the point
> of removal.

## Definition of Done
- Concrete non-optional topology acquired at the boundary and threaded downstream;
  the ~8 `topology is None` husk-arms rendered **dead** (WP17 removes them);
  NFR-002 repro GREEN (xfail removed) via the boundary absorption; differential cell
  green.
- A COORD mission still resolves → coordination (cross-ref WP16 absolute cell); the
  NFR-002 drain was red-first against the stale-coord husk on the pre-WP06 base; the
  C-001/C-003/C-005 KEEP set verified unchanged (existing tests green).
- `ruff`/`mypy` clean; full `tests/` green.

## Branch Strategy
`feat/single-authority-topology-cleanup`. Lane B (sequential, after WP05). Worktree from `lanes.json`.

## Reviewer guidance
Run the NFR-002 repro WITHOUT the prior xfail on the pre-WP06 base to confirm it
was genuinely RED, then confirm WP06 makes it GREEN **via the boundary absorption**
(not via husk-arm removal — those are WP17's). Reject if the absorption flattened a
COORD mission to PRIMARY, or any C-001/C-003/C-005 KEEP item changed. (The
corrupt-meta C-004 arm and the husk-arm collapse are reviewed in WP17.)

## Activity Log

- 2026-06-23T10:45:42Z – claude:opus:python-pedro:implementer – shell_pid=1859763 – Started implementation via action command
- 2026-06-23T11:16:23Z – claude:opus:python-pedro:implementer – shell_pid=1859763 – Boundary absorption + NFR-002 flip GREEN; finalized by orchestrator after implementer stalled at handoff (work verified: ruff/mypy clean, 36 passed)
- 2026-06-23T11:16:57Z – claude:opus:reviewer-renata:reviewer – shell_pid=1932020 – Started review via action command
- 2026-06-23T11:17:38Z – user – shell_pid=1932020 – Ready: concrete topology threaded at boundary; NFR-002 repro GREEN (un-backfilled flattened → PRIMARY, was RED on stale-coord husk); COORD still resolves coordination; husk-arm removal is WP17
- 2026-06-23T11:24:30Z – user – shell_pid=1932020 – Review passed: FR-004 boundary absorption genuine + complete. classify_from_meta acquires concrete non-optional topology at read boundary; wired through BOTH live entries (resolve_handle_to_read_path:958, _stored_topology_best_effort:1213) — no half-edit. NFR-002 drain VERIFIED red-first: reverted resolver to 00da354ef, both repro tests RED resolving the stale -coord husk (the #2062 symptom, observable-dir assert not tautology), GREEN under WP06. xfail genuinely DRAINED not re-keyed (3->2 markers; 4 matrix xfail_reason cells untouched; only NFR-002 flipped). Over-collapse killer confirmed: classify_from_meta keeps COORD->coordination (absent-field+coord_branch->COORD routes_through_coord=True; stored-coord authoritative; flattened->SINGLE_BRANCH->PRIMARY); WP16 absolute pin (4-topology, hardcoded kinds) green. C-004 corrupt/empty-meta arm preserved (empty meta->None legacy probe; _stored_topology_best_effort still except->None). Error-contract convergence (canonical coord-empty fail-closed -> Option-B primary+warning) is legit, NOT silent: warning asserted as negative control; genuine fail-closed/deleted-coord paths still raise (60 fail-closed/coord-deleted tests green). KEEP set untouched (surface_resolver/resolution/status_transition/mission_read_path not in diff; C-001 husk short-circuit 667-678 intact). CT1 ratchet re-keyed with rationale (composite key, not line-bump); inventory.md disposition unchanged. ruff+mypy clean; 214 suite + 24 architectural/error-contract green.
