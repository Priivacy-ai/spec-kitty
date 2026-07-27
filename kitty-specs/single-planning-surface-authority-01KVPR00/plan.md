# Implementation Plan: MissionTopology SSOT + structural planning-surface coherence

**Mission**: `single-planning-surface-authority-01KVPR00`
**Branch**: `feat/single-planning-surface-authority` (planning base = merge target; later PR to `main`)
**Driver**: #2069 (MissionTopology seam — *goes first*) + #1716 · structurally closes #2062 / #2063 / #2064 · parent epic #2007 / #1619

> **REVISION NOTE (2026-06-22).** Rewritten after #2069 finalized ("new design goes first")
> and the operator **carved the independent block C** (verb #1890, guard #2008, de-godding
> #2059/#2056, doctrine prompt, folds #2066/#1891/#2037/#2048) to a separate follow-up mission.
> THIS mission is a focused **seam + structural-fix** scope: FR-001..FR-011. The
> #2062/#2063/#2064 fix is **structural** — the read path consults a **stored** topology, never
> re-inferring shape from on-disk husk existence (C-004). Codebase-wide `CommitTargetKind`
> eradication + universal resolver adoption remain a further follow-on **Mission B** (C-007).

## Summary

Land the **#2069 design** as the structural fix for the coord/primary surface-desync class:
name the four mission shapes (`MissionTopology`), **store** the shape in `meta.json`, resolve it
**once** through a **pure** `resolve_context_for_mission(mission_id, topology) ->
ExecutionContext` projection over the existing `build_execution_context` door, and retire the
per-call derivation heuristic + delete `CommitTargetKind` (at the ≤8 touched sites). Then the
planning read/write commands adopt the seam, so a flattened mission resolves PRIMARY because its
**stored** topology says so — not because a band-aid out-voted an on-disk husk. **This is a
projection over an SSOT door (C-003) — not a new resolver.** Opportunistic #1970 campsite cleanup
applies to touched lines; the named de-godding extractions carved to the block-C mission (C-008).

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: typer, rich, ruamel.yaml (CLI surfaces); pytest, pytest-xdist, mypy, ruff (gates); `spec_kitty_events` / `spec_kitty_tracker` public imports only (shared-package boundary)
**Storage**: filesystem — `kitty-specs/<slug>/` (primary checkout) and `.worktrees/<slug>-<mid8>-coord/` (coordination worktree); `status.events.jsonl` append-only log; `meta.json` identity + **new `topology` field** (stored mission shape)
**Testing**: pytest (`tests/`), parallel `-n auto --dist loadfile` with per-worker HOME isolation; the differential equivalence gate `tests/missions/test_surface_resolution_equivalence.py` (extended with a **pure** stored-topology cell + the retained on-disk flattened-stale-coord row); architectural gates under `tests/architectural/`
**Target Platform**: Linux/macOS dev CLI (Spec Kitty toolkit)
**Project Type**: single (Python CLI package `src/specify_cli` + `src/mission_runtime`)
**Performance Goals**: no measurable regression — the pure resolver removes per-call git/derivation on the resolve hot-path (stored topology read once); no new subprocess on the common case
**Constraints**: ruff + mypy zero-issue on new/changed code; cyclomatic complexity ≤15; no new S1192; behavior-preserving adoption for already-correct topologies; live-evidence proof for #2062; the resolver is PURE (no FS/git I/O — NFR-005)
**Scale/Scope**: the topology SSOT seam (enum + stored field + backfill migration + pure resolver + CommitTargetKind deletion at ≤8 sites) + structural surface adoption across ~6 planning surfaces. Refactor mission with expected linearized shared-surface overlap. Codebase-wide CommitTargetKind eradication + universal adoption are CARVED to Mission B (C-007); the verb/guard/de-godding/campsite work to a block-C mission (C-008).

## Charter Check

*GATE: software-dev-default, compact mode (DIR-001..013). Re-checked post-#2069-design + block-C carve.*

- **DIR-001 (architectural integrity / separation of concerns)**: PASS — the mission names the
  mission-shape cross-product as one stored value and resolves it through one pure door,
  collapsing N ad-hoc per-seam inferences. The resolver is a pure functional core; FS/git live
  in the imperative shell (NFR-005). No parallel resolver (C-003).
- **DIR (testing standards)**: PASS — the differential gate gains a pure stored-topology cell AND
  retains the on-disk flattened-stale-coord row (FR-010); the pure resolver is unit-testable with
  zero fixtures; #2062 carries a live repro (NFR-001).
- **DIR (canonical sources / no improvisation)**: PASS — project over `build_execution_context`;
  reuse the `backfill-identity` migration precedent + the `doctor identity`/`doctor topology`
  audit pairing.
- No charter conflicts; no gate waivers required.

## Project Structure

### Documentation (this mission)
```
kitty-specs/single-planning-surface-authority-01KVPR00/
├── spec.md              # committed (32691dc — seam + structural fix, FR-001..011)
├── plan.md              # this file
├── research.md          # Phase 0 (decisions/rationale; #2069 design record)
├── data-model.md        # Phase 1 (MissionTopology enum, stored field, ExecutionContext projection)
├── quickstart.md        # Phase 1 (live flattened-mission repro + pure-resolver unit recipe)
├── research/observations.md  # dogfooding observations (carried)
└── tasks.md             # Phase 2 (/spec-kitty.tasks — NOT created here)
```

### Source Code (repository root) — surfaces touched
```
# --- A. Topology SSOT seam (foundation) ---
src/mission_runtime/context.py                     # NEW MissionTopology enum; routes_through_coordination predicate (anchor)
src/mission_runtime/resolution.py                  # resolve_context_for_mission projection; retire :705-718 derivation (anchor)
src/runtime/next/runtime_bridge.py                 # retire the SECOND derivation :144-211 (alphonso gap, FR-004)
src/specify_cli/core/mission_creation.py           # mint topology into meta.json at create
src/specify_cli/migrate/<backfill_topology>.py     # NEW backfill migration (backfill-identity precedent)
src/specify_cli/cli/commands/doctor.py             # NEW `doctor topology` audit subcommand ONLY (no de-godding here — carved)
# --- B. Structural surface-coherence adoption ---
src/specify_cli/missions/_read_path_resolver.py    # read path consults stored topology (#2062 structural; anchor)
src/specify_cli/cli/commands/safe_commit_cmd.py    # seam-resolved write target (FR-007)
src/specify_cli/cli/commands/spec_commit_cmd.py    # seam-resolved write target (FR-007)
src/specify_cli/cli/commands/agent/tasks.py        # map-requirements one surface (FR-008)
src/specify_cli/cli/commands/agent/mission.py      # setup_plan/finalize_tasks seam routing (anchor; helpers edited, NOT extracted — extraction carved to block C)
src/specify_cli/status/emit.py                     # event write-surface via seam (FR-009)
src/specify_cli/missions/_substantive.py           # is_committed single-surface collapse (FR-011)
tests/missions/test_surface_resolution_equivalence.py  # pure cell + retained on-disk row (FR-010)
```

## Complexity Tracking

No charter-gate violations to justify. Two structural risks:
1. **`is_committed` 3-leg OR collapse (FR-011)** is a load-bearing workaround; its collapse is
   gated on the structural surface-singularity (FR-006/FR-007 via stored topology) AND a live
   flattened-mission repro (NFR-001) — sequenced after the seam + adoption, never before.
2. **Backfill sequencing (FR-003)** — THIS mission's own `meta.json` must be topology-backfilled
   BEFORE any caller reads the stored field, else the dogfooding loop reads an absent field.

## Implementation Concern Map

Linearization law (NFR refactor overlap): the shared anchors — `mission_runtime/context.py`
(enum + CommitTargetKind), `mission_runtime/resolution.py` (seam + derivation retirement),
`missions/_read_path_resolver.py` (read leg), `core/mission_creation.py` (mint),
`cli/commands/agent/mission.py` (write path) — are touched by multiple ICs and MUST land on a
linearized chain. **#1970 opportunistic cleanup is active for every IC** (touched lines only;
named extractions carved to block C).

**Phase ordering: A (seam) → B (structural adoption).** The seam lands first because every B
adoption resolves through it.

### IC-01 — MissionTopology enum + routes_through_coordination predicate (SEAM, sequence FIRST)
- **FRs**: FR-001, FR-005. **Surfaces**: `mission_runtime/context.py` (anchor).
- Add the `MissionTopology {SINGLE_BRANCH, LANES, COORD, LANES_WITH_COORD}` enum (FLATTENED =
  history flag, not a value). Add the `routes_through_coordination(target)` `MissionTopology`-derived
  per-ref predicate and route the **9** `.kind is COORDINATION` decision sites (commit_router ×2,
  implement, mission.py ×2, tasks.py, orchestrator_api, _substantive, artifacts) through it. The
  `CommitTargetKind` TYPE eradication (~143 value-literal refs/41 files) is behavior-neutral and is
  Mission B (C-007) — leave the constructor field vestigial here.

### IC-02 — Store + backfill the topology (SEAM, after IC-01)
- **FRs**: FR-002, FR-003. **Surfaces**: `core/mission_creation.py` (mint), NEW
  `migrate/backfill_topology`, `doctor.py` (`doctor topology` audit subcommand only).
- Mint `topology` into `meta.json` at create; `migrate backfill-topology` computes+persists for
  legacy missions (backfill-identity precedent) + `doctor topology --json` audit.
- **Sequencing landmine (dogfooding):** backfill THIS mission's `meta.json` BEFORE any caller
  reads the stored field. Until backfilled, the shell computes-and-persists once via the legacy
  derivation, then reads the stored value.

### IC-03 — Pure resolve_context_for_mission + retire BOTH derivations (SEAM, after IC-01/IC-02)
- **FRs**: FR-004, FR-006 (status-surface leg). **Surfaces**: `mission_runtime/resolution.py` (anchor),
  `mission_runtime/context.py` (return VO), `src/runtime/next/runtime_bridge.py` (second derivation),
  `coordination/surface_resolver.py` (status-surface re-inference — squad scope expansion, owned by WP03).
- **Scope expansion (research squad, 2026-06-22):** also route
  `surface_resolver.resolve_status_surface_with_anchor:600`'s surface classification through the
  STORED topology (it feeds `_assemble_core_fragments` → `StatusSurfaceFragment` → the projected
  `ExecutionContext`), keeping `probe_coord_state` ONLY for the C-006 DELETED/EMPTY transients — so
  no parallel `coordination_branch is None` surface derivation survives inside the seam's own door.
- Add the PURE `resolve_context_for_mission(mission_id, topology) -> ExecutionContext` as a thin
  projection over `build_execution_context` (no FS/git I/O — NFR-005; shell passes id+topology).
  Optional input-assertion: fail-closed on supplied-vs-resolved mismatch. Retire **BOTH** hand-rolled
  `coordination_branch is None ⇒ FLATTENED` derivations: `_resolve_coordination_branch` /
  `resolution.py:705-718` AND the independent `runtime_bridge.py:144-211` ladder (keys on
  `_coord_path.exists()` — the disk-`stat` signal C-004 forbids; alphonso's scope gap). Both gated
  under NFR-001 live proof. Leaving EITHER alive is the parallel-inference death-spiral.

### IC-04 — Read path consults stored topology (STRUCTURAL #2062) + differential gate
- **FRs**: FR-006, FR-010. **Surfaces**: `missions/_read_path_resolver.py` (anchor),
  `tests/missions/test_surface_resolution_equivalence.py`.
- `_resolve_existing_for_slug` (and the legs it feeds) resolve via the seam/stored topology;
  `CoordState.MATERIALIZED` is no longer the deciding signal — a `SINGLE_BRANCH`/`LANES` mission
  resolves PRIMARY regardless of an on-disk husk (C-004 structural). Correct the stale `:263`
  "No branch is supplied here" comment.
- Differential gate: add the PURE input→output cell (feed (id, topology) for all 4 cells, assert
  ExecutionContext fields) AND RETAIN the on-disk flattened-stale-coord row × every handle form
  (until those legs are deleted); type+error_code assertion unweakened. The gate asserts ALL THREE
  read legs agree (`_read_path_resolver`, `surface_resolver.resolve_status_surface_with_anchor`,
  `status_transition` read-contract) + a per-leg mutation note (squad expansion).
- **Live-evidence (NFR-001/C-002):** prove on a real flattened-mid-flight repro; the pure cell
  ADDS a proof, never replaces the live one.

### IC-05 — Write-authority adoption across planning commits
- **FRs**: FR-007, FR-009. **Surfaces**: `cli/commands/safe_commit_cmd.py`, `spec_commit_cmd.py`,
  `status/emit.py`, `cli/commands/agent/mission.py` (setup_plan write path).
- Route every planning-artifact commit + status-event emission through the seam; no command
  resolves a write target from `HEAD` (#2063 root: `safe-commit._resolve_commit_target`). Separate
  `safe-commit`'s generic-operator-file responsibility from the mission-aware path (NFR-002 — keep
  generic intact + tested). **NOTE:** the `mission.py` helpers are EDITED for routing but NOT
  extracted to `commit_router.py` — that de-godding (#2056) is carved to block C (C-008);
  opportunistic cleanup of touched lines only.
- **Scope expansion (research squad, 2026-06-22):** also route
  `status_transition._read_contract_from_transaction_target:558`'s status read-contract through the
  STORED topology (the `coordination_branch is None` surface decision; FR-006 status-read leg),
  keeping the C-006 transient arms probe-discriminated — folded into the WP05 FR-009 status subtask.

### IC-06 — map-requirements / finalize-tasks one WP-frontmatter surface
- **FRs**: FR-008. **Surfaces**: `cli/commands/agent/tasks.py` (map-requirements),
  `cli/commands/agent/mission.py` (finalize read region — LINEARIZE after IC-05 anchor edits).
- Both read+write WP `requirement_refs` through one seam-resolved surface (primary INPUT, staged
  to coord at commit-time). Consolidate the duplicated READ surface to one place; `compute_coverage`
  is already single-source — do NOT chase the coverage math.

### IC-07 — Collapse is_committed 3-leg OR (DEPENDS IC-04 + IC-05 + live repro)
- **FR**: FR-011. **Surface**: `missions/_substantive.py:317-412`.
- Reduce to a single-surface check on the resolved placement ref; remove the multi-surface
  diagnostics workaround. **Gated**: only after the seam adoption makes the surface structurally
  singular (IC-04/IC-05) AND a live flattened repro is green (top risk).

## Test-friction front-load (epic #2071 mission-impact, adjudicated 2026-06-22)

A paula + alphonso adjudication of the test-suite friction audit (`docs/development/
test-suite-friction-audit.md`, epic #2071) determined two items touch this mission:

- **WP00 (NEW, test-only, lands BEFORE IC-01) — composite-key re-key of the gating ratchets**
  (#2072 obligation A, pulled to the front). Convert the `file:line` allowlists in
  `tests/architectural/test_no_write_side_rederivation.py` and
  `tests/architectural/test_single_mission_surface_resolver.py` onto `_ratchet_keys.composite_key`
  (content-addressed `(qualname, token_line)` — already exists, mechanical, no new infra); delete the
  duplicated private `_code_tokens_by_line` copy. Rationale: composite keys survive line drift, so
  the seam WPs (IC-02 edits `mission_creation.py:328`, IC-04 rewrites `_read_path_resolver.py:885`)
  no longer false-red the architectural gate — a plain line re-key is NOT front-loadable (would
  re-key to a line the seam then moves). Leave `surface_resolver.py:472/:477` + `cycle.py:185`
  content as-is (untouched seam joins; their PERMANENT-vs-DEFERRED classification stays #2072).
- **`status_transition.py:336` drain — live-evidence-gated subtask of the IC-05 write-authority WP**
  (NOT WP00, NOT a certain drain). `:336` is the `_resolve_write_target` *fallback arm* reached only
  in the pre-meta create window. The WP instruments the fallback and proves on a real
  create→first-write repro whether FR-002/FR-003 (stored topology at create) make the
  `_current_branch` arm unreachable for real missions. **Proven dead → drain** (delete line +
  allowlist entry + flip `test_allow_listed_line_is_the_deferred_head_selector`). **Still reachable →
  leave + re-key only.** Do not drain speculatively (regression) or re-pin a dead line (immortalized
  exemption).
- **CT4 (#2075) — reactive only**, folded into the IC-05/FR-009 WP: preserve `safe_commit`'s
  signature; re-point only the *planning* assertion if the seam adoption changes its call shape.

## Lane mapping (for /spec-kitty.tasks)

- **WP00 (test-only, FIRST)**: composite-key re-key of the two gating architectural guards (above).
- **Linearized seam chain (sequential, after WP00)**: IC-01 (enum/predicate) → IC-02 (store/backfill)
  → IC-03 (pure resolver/derivation retirement). Shared anchors `context.py` / `resolution.py`.
- **Structural adoption (after the seam)**: IC-04 (read path, anchor `_read_path_resolver.py`) →
  IC-05 (write authority, anchor `mission.py`) → IC-06 (map/finalize, linearize after IC-05) →
  IC-07 (is_committed collapse, LAST, gated on live repro).
- **WP slicing is NOT 1:1 with ICs** — slice for reasonable size (3–7 subtasks each); split large
  ICs and keep disjoint owned_files. Target ~7 WPs.

## Risks

1. **Load-bearing-workaround collapse (TOP).** The `is_committed` 3-leg OR masks the surface
   split; its collapse (IC-07) is sequenced last, gated on the structural seam adoption AND a real
   flattened-mid-flight repro (NFR-001).
2. **Backfill sequencing landmine (dogfooding).** FR-003 must backfill THIS mission's `meta.json`
   topology BEFORE any caller reads the stored field; the implement loop runs on a coord-topology
   mission that itself exercises the bugs under fix. Flatten friction expected — carry the
   live-evidence rule throughout.
3. **Enum does NOT subsume transient states (C-006).** The create-window (#1718) and coord-deleted
   (#1848) states are orthogonal to the 4 cells; they MUST stay probe-discriminated. A re-route that
   assumes stored topology answers "is the coord worktree materialized / branch alive?" regresses
   #1718/#1848 — keep the probe.
4. **safe-commit overload regression (NFR-002).** The mission-aware planning path must not break
   `safe-commit`'s generic-operator-file use — separate the two responsibilities, keep generic tested.
5. **Scope creep into Mission B / block C.** Resist eradicating ALL `CommitTargetKind` references /
   adopting the resolver at ALL 29+28 sites (Mission B), and resist pulling the verb/guard/de-godding
   back in (block C). This mission touches ≤8 branch sites + the planning commands only.

## Campsite directive (#1970) — opportunistic only

Operator-mandated for touched LINES: remediate adjacent debt in a surface this mission actually
edits, bounded to mission goals. The *named* de-godding extractions (#2059 doctor cluster, #2056
mission.py helpers) and the cheap fold tickets (#2066/#1891/#2037/#2048) were CARVED to the block-C
follow-up mission (C-008) — do NOT perform them here.

## Post-planning brownfield checks

Two-agent brownfield sweep (randy-reducer + architect-alphonso), 2026-06-22. After the block-C
carve, the folded tickets below moved OUT of this mission:

### Carved to the block-C follow-up mission (C-008)
- #1890 (worktree-repair verb), #2008 (command-reference guard), #2059 (doctor coord-recovery
  de-godding → `_coord_recovery.py`), #2056 (mission.py placement/commit → `commit_router.py`),
  the charter-prompt `safe-commit`→`spec-commit` migration, and folds #2066/#1891/#2037/#2048.

### New brownfield consideration for the seam (in-scope here)
- **Backfill migration is a NEW surface.** Mirror `migrate backfill-identity`; reuse that command's
  structure + the `doctor identity`/`doctor topology` audit pairing. Do NOT hand-roll a parallel
  migration framework.
- **CommitTargetKind has codebase-wide reach (~152 refs/41 files).** Deleting it wholesale is
  Mission B (C-007); this mission deletes/derives only the ≤8 touched branch sites and leaves the
  rest behind a derived projection so the codebase still compiles.

### Deprecations — none due now (LEAVE all)
- `safe_commit_cmd.py:189-212` `--to-branch` "required in v3.3" — NOT-YET-DUE (current 3.2.2). LEAVE.
- `src/specify_cli/next/` shim ("removed in 3.3.0") — not a touched surface. LEAVE.

### Explicitly left OUT (each its own mission-sized effort)
#1357 (lock redesign), #2049 (broad audit), #1887 (squash-merge dup artifacts), #2031 (post-merge
analyzer), the full `doctor.py`/`mission.py`/`tasks.py` decompositions, **the codebase-wide
CommitTargetKind eradication + universal resolver adoption (Mission B, C-007)**, and **the block-C
independent work (C-008)**.

### Relationship to epic #645 — ORTHOGONAL (separate architectural track)
#645 = "Stable Application API Surface (UI/CLI/MCP/SDK)" — a consumer/transport read-API epic. This
mission = internal **git-topology placement authority** (now a stored `MissionTopology` + pure
projection). **Zero file/seam overlap.** Tracker action: cross-reference only, do NOT parent under
#645 — anchors remain #2007 → #1716 → #1619, with #2069 as the design driver.
