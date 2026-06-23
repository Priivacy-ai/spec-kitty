---
work_package_id: WP04
title: 'Semantic .kind collapse: COORDINATION conv + worktree_root (04a) (FR-001b)'
dependencies:
- WP15
requirement_refs:
- C-007
- C-011
- FR-001
- NFR-005
tracker_refs: []
planning_base_branch: feat/single-authority-topology-cleanup
merge_target_branch: feat/single-authority-topology-cleanup
branch_strategy: Planning artifacts for this mission were generated on feat/single-authority-topology-cleanup. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/single-authority-topology-cleanup unless the human explicitly redirects the landing branch.
subtasks:
- T009
- T010
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "1721963"
history:
- Created by /spec-kitty.tasks 2026-06-23
- 'Split into 04a (this WP: COORDINATION conversion + worktree_root preserve) and 04b (WP16: VO-field + enum deletion + absolute-mapping-test rework), sizing squad 2026-06-23. paula coherence weld: the enum deletion stays welded to the absolute-mapping pin in WP16.'
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
- src/specify_cli/coordination/policy.py
- src/specify_cli/events/decision_log.py
- src/mission_runtime/artifacts.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile
Read `src/doctrine/agent_profiles/built-in/python-pedro.agent.yaml` and adopt its
directives/tactics (or `/ad-hoc-profile-load python-pedro`). State which you applied.

## Objective
**FR-001b (semantic half, 04a of 2)** — the **risk** half of the `CommitTargetKind`
eradication, split off the enum-deletion: convert the 3 `kind=COORDINATION`
needs-care sites to the topology predicate, and preserve the `runtime_bridge`
parallel-classifier `worktree_root` selection (C-011). After this WP every live
`CommitTarget(kind=COORDINATION)` construction is converted to the
`routes_through_coordination(topology)` decision over **stored** topology — which
**unblocks WP16** to remove the `.kind` field and delete the enum without a build
break. **WP16 (04b)** removes `.kind` from the `CommitTarget` VO (C-007), deletes
the `CommitTargetKind` enum, and reworks the absolute-mapping cell off the enum.

## Context
- The semantic half was split for risk (sizing squad 2026-06-23): **WP04 (this WP)**
  does the COORDINATION→predicate conversion + the C-011 worktree_root preserve;
  **WP16** does the VO-field removal + enum deletion + absolute-mapping-test rework
  (paula coherence weld: enum-delete ⊗ absolute-mapping pin stay together). Sequential
  lane B, WP04 → WP16.
- WP03/WP14/WP15 already dropped the mechanical `kind=PRIMARY` sites. The remaining
  `.kind` surface is here: the decision read (`context.py:131`), the 3
  `kind=COORDINATION` sites, the 2 `runtime_bridge` parallel-classifier sites. The
  `CommitTarget` VO field + the enum definition (`context.py:51`) are deleted in WP16.
- `routes_through_coordination(topology)` exists from WP02 (topology-taking form).

## Subtasks
### T009 — Convert ALL kind=COORDINATION carrier sites (build-break + #2090-clean)
For each `CommitTarget(... kind=CommitTargetKind.COORDINATION ...)` /
`.kind is COORDINATION` decision: route the decision through
`routes_through_coordination(topology)` over the **stored** topology (the SSOT),
NOT a re-derived `.kind`. The single decision read at `context.py:131` becomes a
call to the predicate over topology. Behavior-identical (COORDINATION ⇔ the
predicate true).

**The COORDINATION carriers span MORE than the topology files (post-tasks squad,
build-break fix).** When `T011` deletes the enum, every live
`CommitTarget(kind=CommitTargetKind.COORDINATION)` construction must already be
converted or the build breaks. The carriers are NOT only in the 5 topology files
— they also live in this WP's newly-owned files:
- `src/specify_cli/coordination/policy.py:215`
- `src/specify_cli/events/decision_log.py:95`
- `src/mission_runtime/artifacts.py:127` — a **synthetic** `CommitTarget(ref="", kind=COORDINATION)` carrier that drives `is_coordination_artifact_residue_path` (the single residue authority FR-012 + #2090 derive from).

Convert all of them. **Critically (alphonso / #2090 must-not-do):** the
`artifacts.py:127` carrier must be reworked so `is_coordination_owned` derives
coord-routing from the **stored topology** (the `routes_through_coordination(topology)`
predicate over `COORD`/`LANES_WITH_COORD`), NOT a fabricated `.kind` shim
(do NOT synthesize a `CommitTarget` just to call the old predicate). This keeps
the residue authority a clean topology projection #2090 can build on. Reuse the
SINGLE `routes_through_coordination(topology)` from WP02 — do not introduce a
second `_residue_routes_through_coord` helper.
(WP03 owns these three files for the mechanical `kind=PRIMARY` drops only; the
COORDINATION conversion + enum-dependent edits are WP04's — same lane B,
sequential, so the shared ownership is legal.)

### T010 — Preserve runtime_bridge worktree_root (C-011)
The 2 `runtime_bridge.py` parallel-classifier sites (`:241` producer +
`worktree_root` selection): remove their `.kind` usage but **PRESERVE the
`worktree_root` selection logic exactly** — it is a risk site. Add/keep a focused
test pinning the `worktree_root` value for a coord-routed mission before and after.

> **Hand-off to WP16:** after this WP, no live construction reads `.kind`. WP16
> (04b) removes the `kind` field from the `CommitTarget` dataclass (→ `{ref: str}`,
> C-007 ref-only carrier) and deletes the `CommitTargetKind` enum. Leave the VO
> field + enum definition in place here so WP16's deletion is the single atomic
> "enum gone" step welded to the absolute-mapping-test rework.

## Campsite (#1970)
Remove dead imports/aliases exposed by the COORDINATION conversion; fix lint/type
debt; hoist S1192. KEEP (NFR-005): the C-002 relays + the C-001 husk short-circuit
unchanged — verify.

## Test approach (doctrine standard)

> **Test approach (doctrine standard — DIRECTIVE_034/036/041, #2071 CTn).** Assert the **observable contract** — returned value, resolved surface/ref, persisted JSONL/`meta.json`, CLI `--json` payload, or gate verdict — **never** the internal call graph or "collaborator X was invoked" (CT4/D036). Build mission fixtures by delegating to the **production creation seam** (`create_mission_core` / the existing `_stored_topology` helper), not a hand-rolled `meta.json` writer that rots (CT3); use **production-shaped data** — a real 26-char ULID + 8-char mid8, never a short placeholder (testing-principles). Any architectural guard/ratchet anchors keys on `_ratchet_keys.composite_key` (qualname + token-line) or an AST node — **never `file.py:NNN`** — and reuses `audit.py`/`_ratchet_keys.py` (CT1); resolve symbols by AST, never by grepping a string that collides with a surviving flag (NFR-003). Any xfail/skip is a **RED-by-design ATDD pin that names the WP that drains it** and is removed (not re-keyed) when the fix lands — never a defect mask (CT2). Prove behavior-neutrality via the **differential cell over the `(topology × transient)` matrix** PLUS at least one **absolute** assertion (see below) — never a brittle golden count of sites/LOC/refs (CT5); prefer a **tightening ratchet** (count only drops, keyed by symbol-set) over a fixed `== N`. **Pair every "allow / passes / absorbs / ignores-residue" assertion with its negative control** ("still-blocks / still-raises / wrong-topology-differs") — one-sided gate tests let the over-allow mutant survive. When a touched test goes red, classify it (stale→re-point preserving setup / fakeable→delete / valid→fix the product) and establish causation by **code-path coupling, not git-blame** (D041).

### WP04-specific test-DoD
- **(b) T009 residue predicate cell.** Add a direct test of `is_coordination_artifact_residue_path(path, mission_slug=…)` for a placement-kind path asserting **COORD → True AND flat/SINGLE_BRANCH → False**. The predicate is always-true today; the **flat→False** cell is the over-allow mutation-killer (paired negative control). (The absolute-mapping cell rework lives in WP16, welded to the enum deletion.)
- **(c) T010 worktree_root pin (non-identity).** The C-011 worktree_root pin uses a coord-routed mission whose **primary root ≠ coord root** (non-identity fixture) and asserts the selected `worktree_root` equals the **coord** root — an identity fixture would pass even if the selection broke.
- **(d) CT1 re-key clause.** Re-key any drifted `composite_key` ratchet entry with rationale; never line-bump, never add a raw `file.py:NNN` key.

## Definition of Done
- Every live `CommitTarget(kind=COORDINATION)` construction + the `context.py:131`
  decision read converted to `routes_through_coordination(topology)` over STORED
  topology; the `artifacts.py:127` residue authority derives coord-routing from
  stored topology (no fabricated `.kind` shim). No `.kind` **construction** survives
  for WP16 to trip over — the only `.kind` left is the VO field + enum definition
  WP16 deletes.
- The `is_coordination_artifact_residue_path` cell pins COORD→True AND flat→False;
  the worktree_root pin uses a non-identity (primary≠coord) fixture.
- C-011 worktree_root pinned by a test, value unchanged. KEEP set (C-001 husk
  short-circuit, C-002 relays) verified unchanged.
- `ruff`/`mypy` clean; full `tests/` green (behavior-neutral). The enum still
  imports cleanly (WP16 deletes it).

## Branch Strategy
`feat/single-authority-topology-cleanup`. Lane B (sequential, after WP15). Worktree from `lanes.json`.

## Reviewer guidance
Verify the decision now reads STORED topology via the predicate, not a re-derived
`.kind`. Verify the worktree_root test pins the pre-existing value. Reject if any
`.kind` **read/construction** survives (the enum definition + VO field are WP16's),
or the husk short-circuit / relays changed.

## Activity Log

- 2026-06-23T09:30:05Z – claude:opus:python-pedro:implementer – shell_pid=1680698 – Started implementation via action command
- 2026-06-23T09:47:17Z – claude:opus:python-pedro:implementer – shell_pid=1680698 – Ready: COORDINATION carriers → routes_through_coordination over stored topology; artifacts.py residue derives from topology (no .kind shim, #2090-clean); worktree_root pinned (non-identity); only VO field+enum left for WP16
- 2026-06-23T09:48:13Z – claude:opus:reviewer-renata:reviewer – shell_pid=1721963 – Started review via action command
- 2026-06-23T09:54:41Z – user – shell_pid=1721963 – Review passed: COORDINATION→routes_through_coordination(topology) over STORED topology — no live CommitTarget(kind=COORDINATION) construction survives in owned files (only the transitional VO-field read at context.py:159 + destination_kind_for_topology at resolution.py:148, both WP16's to drain). #2090-clean: artifacts.py kind_is_coordination_residue is a thin projection reusing the SINGLE routes_through_coordination — no fabricated .kind shim, no second predicate; composes with extended residue authority (spec/data-model/research/checklist). Behavior-neutral proven: old is_coordination_owned(COORD ref)==kind in _PLACEMENT_ARTIFACT_KINDS==new projection; resolution destination_kind is COORDINATION ⇔ routes_through_coordination(topology) exactly. C-011 worktree_root selection byte-preserved (only .kind dropped); pin is genuinely non-identity (coord_root != repo_root asserted) and exercises the real materialized-coord arm. Residue cell pins COORD/LANES_WITH_COORD→True + flat(SINGLE_BRANCH/LANES)→False over-allow killer + PRIMARY_METADATA kind negative control + projection==legacy differential. KEEP set intact (status_transition/surface_resolver untouched by diff; resolution hunk far from C-002 relay@765). CT1 ratchet: 10 entries removed as real composite-key drops with per-site rationale (no line-bump, no file.py:NNN); baseline test green. pytest 329 passed/1 xfailed + 20 new green; ruff/mypy clean on owned files no suppressions; 2 named failures (mission_schema_unit, pytest_marker_convention) confirmed pre-existing + unrelated to owned modules.
