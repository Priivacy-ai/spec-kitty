---
work_package_id: WP16
title: 'CommitTargetKind eradication: drain all references + delete enum/VO field (FR-001b)'
dependencies:
- WP07
requirement_refs:
- C-007
- FR-001
- NFR-003
- NFR-005
tracker_refs: []
planning_base_branch: feat/single-authority-topology-cleanup
merge_target_branch: feat/single-authority-topology-cleanup
branch_strategy: Planning artifacts for this mission were generated on feat/single-authority-topology-cleanup. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/single-authority-topology-cleanup unless the human explicitly redirects the landing branch.
subtasks:
- T011
- T031
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "2156974"
history:
- 'Created by sizing-squad re-slice 2026-06-23 (split 04b of WP04). paula coherence weld: the enum deletion is welded to the absolute-mapping-test rework here — both in one WP so the "everything→PRIMARY" mutant cannot survive.'
- 'RE-SEQUENCED 2026-06-23 (operator-approved): dep WP04→WP07 (runs LAST in lane B); scope expanded to drain the ~27 enum-referencing test files before deleting the enum (WP16 implementer surfaced the circular WP05→WP16 dep + undrained test consumers). WP05 dep re-pointed to WP04.'
agent_profile: python-pedro
authoritative_surface: src/mission_runtime/
create_intent: []
execution_mode: code_change
owned_files:
- src/mission_runtime/context.py
- src/mission_runtime/__init__.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile
Read `src/doctrine/agent_profiles/built-in/python-pedro.agent.yaml` and adopt its
directives/tactics (or `/ad-hoc-profile-load python-pedro`). State which you applied.

## Objective
**FR-001b — the FINAL `CommitTargetKind` eradication WP (runs LAST in lane B).**
Drain **every** remaining `CommitTargetKind` reference — the ~27 enum-referencing
**test files** (imports, enum-contract assertions, fixtures) + any leftover
producer — THEN remove the `kind` field from the `CommitTarget` VO (→ `{ref: str}`,
C-007), DELETE the `CommitTargetKind` enum from `context.py`, fix the
`mission_runtime/__init__.py` exports, and **rework the absolute-mapping equivalence
cell off the doomed enum**. After this WP the WP01 AST guard for `CommitTargetKind`
flips green and **`grep -r CommitTargetKind src/ tests/` returns nothing**.

> **RE-SEQUENCED 2026-06-23 (operator-approved):** the original WP04↔WP16 split
> sequenced this enum deletion BEFORE WP05 (FLATTENED producers) + before the ~27
> enum-referencing test files were drained — a circular/undersized-scope defect the
> WP16 implementer correctly surfaced (the recurring "spec/plan undersizes deletion
> scope"). Fix: WP05 now depends on WP04 (not WP16); **this WP depends on WP07 and
> runs LAST**, so all producers (WP05) + all source consumers (WP04/05/06/17) are
> already drained at this base. This WP owns the remaining **test-consumer drain** +
> the deletion. Deleting a widely-referenced type requires owning all its references.

## Context (the final eradication — base = full lane-B chain WP04..WP07)
- By this WP's base: WP03/14/15 dropped `kind=PRIMARY`; WP04 converted the
  `kind=COORDINATION` carriers + decision reads to `routes_through_coordination`;
  WP05 converted the FLATTENED producers (`upgrade.py:214` / `resolution.py:156` /
  `runtime_bridge.py:241`) to plain `CommitTarget(ref=…)` + AST-verified FLATTENED
  write-only-dead. So **zero live `.kind` constructions remain in `src/`** — only the
  VO field definition, the enum definition, the transitional `routes_through_coordination(CommitTarget)` arm + `destination_kind_for_topology`, and the **~27 test
  files** that still import/assert the enum.
- **paula coherence weld (do NOT split):** the enum deletion + the absolute
  per-topology mapping assertion land together here (the "everything→PRIMARY" mutant).
- **Ownership:** the ~27 enum-referencing test files are pre-existing (they pre-date
  the mission) — converting/removing them here is justified work for the eradication
  WP, **dependency-ordered LAST** (after every WP that owns a source file), so the
  touches are exemption-covered. Record each as a one-line rationale if a guard flags
  it. Resolve every reference by **AST/symbol**, NEVER by grepping the string
  `CommitTargetKind`/`"flattened"` (NFR-003 — `"flattened"` collides with the
  surviving C-006 provenance meta-flag; do NOT delete the flag).

## Subtasks
### T011 — Drain the remaining producers + the test-consumers
1. Re-verify (by AST, reusing WP01's `discover_references`) that `src/` has **zero**
   live `CommitTargetKind` constructions/reads except the VO field + enum def +
   the transitional `routes_through_coordination(CommitTarget)` arm +
   `destination_kind_for_topology`. If any producer survives (a WP04/WP05 escape),
   convert it to plain `CommitTarget(ref=…)` here and note it.
2. **Drain the ~27 enum-referencing TEST files.** For each: an import-only fixture
   reference → convert the construction to `CommitTarget(ref=…)` and drop the import;
   an **enum-contract test** (e.g. `test_context_fragments.py` asserting the member
   set, `test_commit_router.py`/`test_resolve_context_for_mission_pure.py` pinning
   per-topology `.kind`) → these test a DELETED contract, so **remediate them to
   assert the new contract** (`routes_through_coordination(topology)` / the surface
   placement) preserving their load-bearing intent, OR delete a test that existed
   ONLY to pin the enum (classify per D041: stale→re-point, enum-only→delete). Do NOT
   leave a broken collection import.

### T031 — Remove the VO field + delete the enum + rework the absolute cell
3. Drain the transitional `routes_through_coordination(CommitTarget)` arm +
   `destination_kind_for_topology` (now dead once the VO field goes). Keep the
   `routes_through_coordination(MissionTopology)` form (WP02's single predicate).
4. Remove the `kind` field from the `CommitTarget` dataclass (→ `{ref: str}`, C-007;
   this also removes the WP03 transitional default).
5. Delete the `CommitTargetKind` enum from `context.py`; drop the
   `mission_runtime/__init__.py` export + any dead alias (AST-resolved).
6. **Rework `test_pure_stored_topology_projects_surface_placement`** (in
   `test_surface_resolution_equivalence.py`): drop the `CommitTargetKind` import,
   assert via `routes_through_coordination(topology)`, **preserving the absolute
   per-topology pin** (COORD/LANES_WITH_COORD → coordination, SINGLE_BRANCH/LANES →
   PRIMARY) — the WP01 (a) absolute cell relocated off the enum (the weld).

## Campsite (#1970)
Remove dead imports/aliases exposed by the enum deletion; fix lint/type debt; hoist
S1192. KEEP (NFR-005): the C-002 relays + the C-001 husk short-circuit unchanged —
verify they did not get caught in the deletion.

## Test approach (doctrine standard)

> **Test approach (doctrine standard — DIRECTIVE_034/036/041, #2071 CTn).** Assert the **observable contract** — returned value, resolved surface/ref, persisted JSONL/`meta.json`, CLI `--json` payload, or gate verdict — **never** the internal call graph or "collaborator X was invoked" (CT4/D036). Build mission fixtures by delegating to the **production creation seam** (`create_mission_core` / the existing `_stored_topology` helper), not a hand-rolled `meta.json` writer that rots (CT3); use **production-shaped data** — a real 26-char ULID + 8-char mid8, never a short placeholder (testing-principles). Any architectural guard/ratchet anchors keys on `_ratchet_keys.composite_key` (qualname + token-line) or an AST node — **never `file.py:NNN`** — and reuses `audit.py`/`_ratchet_keys.py` (CT1); resolve symbols by AST, never by grepping a string that collides with a surviving flag (NFR-003). Any xfail/skip is a **RED-by-design ATDD pin that names the WP that drains it** and is removed (not re-keyed) when the fix lands — never a defect mask (CT2). Prove behavior-neutrality via the **differential cell over the `(topology × transient)` matrix** PLUS at least one **absolute** assertion (see below) — never a brittle golden count of sites/LOC/refs (CT5); prefer a **tightening ratchet** (count only drops, keyed by symbol-set) over a fixed `== N`. **Pair every "allow / passes / absorbs / ignores-residue" assertion with its negative control** ("still-blocks / still-raises / wrong-topology-differs") — one-sided gate tests let the over-allow mutant survive. When a touched test goes red, classify it (stale→re-point preserving setup / fakeable→delete / valid→fix the product) and establish causation by **code-path coupling, not git-blame** (D041).

### WP16-specific test-DoD
- **(a) Absolute-mapping cell reworked off the enum (the weld).** The reworked
  `test_pure_stored_topology_projects_surface_placement` asserts via
  `routes_through_coordination(topology)` (no `CommitTargetKind` import) and pins the
  **absolute** per-topology placement: COORD/LANES_WITH_COORD → coordination,
  SINGLE_BRANCH/LANES → PRIMARY. This is the over-collapse mutation-killer that must
  ship in the same WP as the deletion.
- **(b) WP01 AST guard flips green here.** The `CommitTargetKind`-symbol AST guard
  (WP01) goes from RED-by-design to green at this WP — confirm it asserts **symbol
  absence by AST**, not a string grep (the `"flattened"` value collides), and that
  the `flattened` provenance meta-flag (C-006) is still present.
- **(c) CT1 re-key clause.** Re-key any drifted `composite_key` ratchet entry with
  rationale; never line-bump, never add a raw `file.py:NNN` key.

## Definition of Done
- **`grep -r CommitTargetKind src/ tests/` returns NOTHING** — the ~27 test
  consumers drained (re-pointed to the new contract or deleted if enum-only), zero
  `.kind` reads/fields/constructions in `src/`, `CommitTargetKind` enum deleted,
  `CommitTarget` is `{ref}` only, `mission_runtime/__init__.py` export removed.
- WP01 AST guard green for `CommitTargetKind` (symbol-absence by AST, not grep); the
  `flattened` provenance meta-flag (C-006) untouched.
- `test_pure_stored_topology_projects_surface_placement` reworked to assert via
  `routes_through_coordination` (no `CommitTargetKind` import) preserving the absolute
  per-topology pin; drained enum-contract tests re-point to the topology/predicate
  contract (preserving load-bearing intent) — none left asserting a deleted member set.
- `ruff`/`mypy` clean; **full `tests/` green** (no collection break) — behavior-neutral.

## Branch Strategy
`feat/single-authority-topology-cleanup`. Lane B (sequential, runs LAST — after WP07). Worktree from `lanes.json`.

## Reviewer guidance
Reject if `grep -r CommitTargetKind src/ tests/` finds ANY surviving reference (the
eradication is incomplete) or if a drained enum-contract test was left asserting a
deleted member set instead of re-pointed to the topology/predicate contract. Reject if
the enum was deleted WITHOUT the absolute-mapping cell reworked in the same WP (the
weld), or if symbol resolution used a string grep that could clip the `flattened`
meta-flag. Confirm `CommitTarget` is ref-only and the WP01 AST guard is green.

## Activity Log

- 2026-06-23T09:55:22Z – claude:opus:python-pedro:implementer – shell_pid=1733005 – Started implementation via action command
- 2026-06-23T10:04:05Z – claude:opus:python-pedro:implementer – shell_pid=1733005 – BLOCKED — planning/sequencing defect, not a code obstacle. WP16 premise ('zero live .kind constructions; clean compile') is false at the WP04 base. Reality after merging the required WP15 (lane-c) base into lane-b: deleting the CommitTargetKind enum breaks (1) live src producer upgrade.py:214 (kind=CommitTargetKind.FLATTENED) which is explicitly WP05-OWNED yet WP05 runs AFTER WP16 (WP05 dep=[WP16]) — a circular ordering bug; and (2) 27 test files importing the enum at module level (collection break), owned across WP02/WP05/WP06/WP14 + mission_runtime unit tests, none scoped for conversion before this deletion (WP05/WP06 are downstream of WP16). Converting all of these would violate locality/ownership across 6+ other WPs and pre-empt their planned work. The WP01 AST guard itself can be flipped green here (empty baseline + assert-empty), but DoD 'full tests/ green' is unreachable in WP16's scope. Recommend re-slice: either (a) move the enum DELETION to run after WP05/WP06 (after all producers+test consumers are drained), or (b) fold the 27 test-file conversions + upgrade.py into WP16's scope explicitly and re-order WP05 before WP16. No edits made; lane worktree clean (lane-c merge attempted then aborted).
- 2026-06-23T10:15:45Z – user – Moved to planned
- 2026-06-23T12:19:10Z – claude:opus:python-pedro:implementer – shell_pid=2054077 – Started implementation via action command
- 2026-06-23T13:20:42Z – claude:opus:python-pedro:implementer – shell_pid=2054077 – Ready: CommitTargetKind fully eradicated (rg src/ tests/ returns nothing outside the WP01 guard's own sentinel); enum + VO kind field deleted (CommitTarget is ref-only, C-007); routes_through_coordination collapsed to MissionTopology-only + new public resolve_topology(handle-canonicalizing) seam; ~30 test files drained (ref-only fixtures + enum-contract tests re-pointed to topology predicate + enum-only tests deleted); absolute-mapping weld reworked off the enum; WP01 AST guard GREEN (baseline empty, terminal stays-empty assertion); C-006 flattened meta-flag intact; ruff+mypy clean on new code; untrusted-path inventory CT1 re-key. Pre-existing failures (test_mission_schema_unit, test_support_helper_tree_exempt, test_map_requirements x2) verified via stash.
- 2026-06-23T13:22:07Z – claude:opus:reviewer-renata:reviewer – shell_pid=2156974 – Started review via action command
- 2026-06-23T13:32:05Z – user – shell_pid=2156974 – Arbiter override: review-cycle-2 was the operator-approved BLOCKED/re-sequence record (plan-sequencing defect correctly surfaced), NOT an unaddressed quality rejection; re-sequenced impl (WP16 LAST, dep WP07) delivers the expanded scope. Review PASSED: CommitTargetKind fully eradicated (rg src/ tests/ -> nothing but WP01 guard sentinel; no runtime attr; CommitTarget ref-only C-007). resolve_topology seam is a clean stored-topology READ delegating to pure _resolve_topology (WP02 SSOT), canonicalizing handle identically to resolve_placement_only. All 8 rewired sites behavior-neutral (old .kind-is-COORDINATION == routes_through_coordination over SAME stored topology; resolve_placement_only runs first so swallow-arm unreachable; mission_slug-None guard unreachable). is_coordination_owned deletion safe (zero callers; kind_is_coordination_residue live). Weld preserved (absolute per-topology table + negative controls, no enum import). WP01 AST guard green-by-emptiness + bites-on-reintroduction + ignores-flattened-string controls. C-006 meta.setdefault('flattened',False) intact. ruff+mypy clean on changed src (zero NEW issues). 4 test failures + 4 no-any-return mypy ALL verified pre-existing via HEAD^. Behavior spot-check passed all 4 topology cases. Scope eradication-necessary, no creep.
