# Implementation Plan: Single-Authority Topology Cleanup & Dedup

**Branch**: `feat/single-authority-topology-cleanup` | **Date**: 2026-06-23 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `kitty-specs/single-authority-topology-cleanup-01KVRJ6P/spec.md`
**Mission ID**: `01KVRJ6PC66DWS32M30YVPAE28` (mid8 `01KVRJ6P`)

## Summary

Behavior-neutral cleanup + deduplication follow-on to the landed MissionTopology
SSOT seam (PR #2086). The seam stored `MissionTopology` in `meta.json`, routed all
coordination-routing **decisions** through `routes_through_coordination`, and left
the mechanical cleanup carved to this mission (#2070). This plan translates the
13 FRs into 8 Implementation Concerns: a **verification safety net first**
(differential cell + AST guard), then a **linearized topology/resolution anchor
chain** (the `CommitTargetKind` eradication, `FLATTENED` deletion, `topology=None`
absorption, and predicate/frozenset consolidation all touch the same surfaces),
then **disjoint parallel lanes** for the C2 meta-reader unification, the C6
shadow-module retirement, the accept gates, the merge residue-gate sweep, and the
standalone #1891 JSON-serialization fix. The mission carries **zero correctness
regression** on backfilled missions, with exactly **one** intentional correctness
improvement (FR-004 extends the #2062 fix to un-backfilled missions) that is
proven on a live repro before any husk-arm is collapsed.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: typer, rich, ruamel.yaml (existing — **no new dependencies**); internal `mission_runtime`, `specify_cli.status`, `specify_cli.coordination`, `specify_cli.git` packages
**Storage**: `meta.json` per-mission (filesystem), git refs / worktrees; the stored `topology` field is the SSOT this mission consumes
**Testing**: pytest (`tests/architectural/`, `tests/missions/`); the differential-equivalence gate `tests/missions/test_surface_resolution_equivalence.py` is the central acceptance lever; AST guard reuses `tests/architectural/audit.py` + `_ratchet_keys.py`; `ruff` + `mypy` zero-issue on new code; diff-coverage ≥90% on critical paths
**Target Platform**: CLI (Linux / macOS); spec-kitty mission lifecycle
**Project Type**: single (Python CLI + library)
**Performance Goals**: behavior-neutral; `topology=None` absorption is O(1) classify-on-read (no extra I/O beyond the existing meta read)
**Constraints**: complexity ceiling 15 (ruff C901 / Sonar S3776); no suppression of lint/type checks; Terminology Canon (Mission not feature); canonical-sources discipline (C-009 — adoption only, no parallel resolver/auditor)
**Scale/Scope**: ~17 `src/` files for the type eradication (45 refs + ~139 test refs); C2 footprint re-baselined to ≥66 named + ~107 inline meta reads; net reduction target ≥750–1,000 LOC (floor)

## Charter Check

*GATE: software-dev-default template; DIR-001..013. Compact-mode governance loaded.*

| Gate | Status | Note |
|------|--------|------|
| Canonical sources (C-009) | PASS | Consumes the existing SSOT API + differential gate; builds no parallel resolver/auditor. |
| Terminology Canon | PASS | No `feature*` aliases introduced; "Mission" canonical; touched prose reworded if needed (pre-push terminology guard). |
| Tests-as-scaffold (DIRECTIVE_041) | PASS | FR-010 cell asserted **green**, not parked behind an `_XFAIL_*_OUT_OF_SCOPE` marker; FR-011 guard is non-fakeable (AST/symbol, NFR-003). |
| Tiered rigour / complexity ≤15 | PASS | Consolidations extract small pure helpers; the polymorphic `load_meta` (FR-006) keeps cyclomatic ≤15 via adapter split. |
| No-suppression | PASS | No new `# noqa` / `# type: ignore`; deletions reduce surface. |
| Behavior-neutrality (NFR-001) | PASS (gated) | Differential gate + full `tests/architectural/` sweep on the merged branch are the proof; FR-004's one improvement is live-repro gated (NFR-002). |

No charter conflicts. No version prescription (C-008 — PO assigns at release).

## Implementation Concern Map (IC-01 … IC-08)

The IC map is the architectural decomposition. `/spec-kitty.tasks` will slice ICs
into right-sized WPs (IC-to-WP is **not** 1-to-1; the large ICs split). Every WP
carries the #1970 campsite directive (remediate adjacent debt in the touched
surface in-slice, bounded to mission goals) and maps its KEEP items (C-001..C-007)
to unchanged/test-pinned sites (NFR-005).

### IC-01 — Verification safety net (LANDS FIRST; gates the deletions)
- **FRs**: FR-010 (differential classify-on-read ≡ backfill-then-read cell across every `(topology × transient)` combination, asserted **green**), FR-011 (non-fakeable AST/symbol guard failing CI on `CommitTargetKind` / former `FLATTENED.value` reintroduction), NFR-002 (live un-backfilled-flattened-mission repro that **fails on pre-FR-004 code**).
- **Surfaces**: `tests/missions/test_surface_resolution_equivalence.py` (extend the existing 37 KB harness — it already parametrizes `flattened-stale-coord` / `coord-deleted` / `coord-empty` cells and has a `_stored_topology` helper), `tests/architectural/` (new guard reusing `audit.py` + `_ratchet_keys.py`).
- **Why first**: the deletions (IC-02) and the husk-arm collapse (FR-004) are only safe once the differential gate proves equivalence and the AST guard pins non-reintroduction. The NFR-002 repro must exist and be RED before FR-004 turns it green.
- **KEEP check**: the new cell must NOT ride the existing `_XFAIL_*_OUT_OF_SCOPE` markers (those guard the orthogonal C-005 transient probes).

### IC-02 — Topology/resolution anchor chain (LINEARIZED, single lane, sequential)
The shared-surface core. FR-001/FR-002/FR-004/FR-005 all mutate the same topology
files, so they land sequentially on one lane (refactor-mission shared-surface
overlap, linearization law). **Internal Tidy-First order:**
1. **FR-005** (C1) — consolidate the six coord-routing predicates and the four verbatim `{COORD, LANES_WITH_COORD}` frozensets (two distinct constant names `_COORD_ROUTING_TOPOLOGIES` / `_COORD_SURFACE_TOPOLOGIES` + an inline literal) to ONE pure `routes_through_coordination(topology)` + ONE shared frozenset. *Tidy the predicate before collapsing `.kind` onto it.*
2. **FR-001** — collapse `.kind` → the consolidated predicate over stored topology; remove `.kind` from the `CommitTarget` VO (kept as ref-only carrier, C-007); delete the `CommitTargetKind` enum + its ~45 `src/` refs across the categorized footprint (2 topology-derived, 11 mechanical `kind=PRIMARY` drop-arg, 3 `kind=COORDINATION` needs-care, 2 `runtime_bridge` parallel-classifier **preserving `worktree_root`** — C-011, plus imports/annotations/enum).
3. **FR-002** — delete `CommitTargetKind.FLATTENED` (symbol-verified write-only dead; producers at `resolution.py:156` / `runtime_bridge.py:241` / `upgrade.py:214` emit PRIMARY); preserve the separate `flattened` provenance meta-flag (C-006); confirm by AST that nothing serializes the former `.value`.
   - **Campsite (brownfield, randy)**: also remove the dead `safe_commit` re-export shim at `cli/commands/agent/mission.py:54-58` (0 external importers repo-wide; the stated "external callers" reason is unproven). In-slice with FR-001's commit-routing cleanup. (`mission.py` is a consumer of the `.kind` rework, not one of the 6 IC-02 topology files — scope the ownership to those 5 lines.)
4. **FR-004** (gated on IC-01's RED repro) — absorb `topology=None` at the read-path boundary via `read_topology` / a pure `classify_from_meta(meta, feature_dir)`; thread a **concrete non-optional** `MissionTopology` downstream; collapse the ~8 `topology is None` husk-arms (`_read_path_resolver.py:148/361/724/895` + siblings). **Boundary discipline (decision 3):** collapse only the **absent-field** arms (`load_meta` returns `None` → classify); the **corrupt/unreadable-meta** arm (`load_meta` raises) stays a typed fallback (C-004).
- **Surfaces (owned by this lane)**: `src/mission_runtime/context.py`, `src/mission_runtime/resolution.py`, `src/runtime/next/runtime_bridge.py`, `src/specify_cli/coordination/surface_resolver.py`, `src/specify_cli/coordination/status_transition.py`, `src/specify_cli/missions/_read_path_resolver.py`.
- **KEEP (NFR-005)**: surface_resolver husk short-circuit `:667-678` (C-001, the `df79f76f4` data-loss site); the genuine-fallback relays at `status_transition.py:599` / `surface_resolver.py:562` / `resolution.py:765` (C-002 — exception-arm meta-read fallbacks, **disjoint** from FR-005's projection predicates: do not collapse a relay); the 5-hop feature-dir path (C-003); transient probes (C-005).

### IC-03 — `ensure_topology` shim removal (small; rides the anchor lane tail or a quick disjoint slice)
- **FR**: FR-003 — remove the dead persist shim (zero `src/` callers) and retarget its tests onto `read_topology` + `backfill_mission_topology`.
- **Surface**: `src/specify_cli/migration/backfill_topology.py` + `tests/specify_cli/migration/test_backfill_topology.py`. Mostly disjoint from IC-02, but conceptually part of the topology cleanup; tasks may attach it to the anchor lane's tail to avoid a one-WP lane.

### IC-04 — C2 `meta.json` reader unification (DISJOINT lane; LARGE — will split)
- **FR**: FR-006 — collapse the meta-read sites to ONE polymorphic `load_meta(dir, *, allow_missing, on_malformed)`. Footprint re-baselined + **brownfield-corrected (alphonso)**: **66 named** call sites (✓) + **~71 inline** `json.loads(meta_path)` (the earlier ~107 figure was ~1.5× high; floor still holds). **3 distinct error contracts, not 2 adapters**: canonical `mission_metadata.load_meta:252` (None-on-missing, raise-on-malformed); the `task_helpers.load_meta:420` / `task_utils/support.load_meta:363` pair (raise-on-missing, **utf-8-sig BOM-tolerant** decode); the silent-empty-dict readers (`retrospective/generator._load_meta:126`, `review/__init__._load_meta:382`). `on_malformed` must cover **silent-empty-dict, raise, AND None-return**, and preserve the utf-8-sig nuance.
- **Surface**: the canonical meta-reader module + the call sites it replaces (broad). **Ownership risk (brownfield-sharpened)**: BINDING — IC-04's `tasks.py` / `mission.py` WPs MUST land **after** IC-06/IC-08 (file-level `owned_files` cannot be split by line range; `finalize-tasks --validate-only` enforces file granularity). **NEW collision the plan under-named: IC-02 × IC-04** — four IC-02 topology files (`resolution.py` @401/716/782, `surface_resolver.py` @651/692, `status_transition.py` @359, `_read_path_resolver.py` @771/787) also carry `load_meta` calls. RESOLUTION: **IC-02 owns those four files' meta-read conversions in-slice** (fold that C2 sub-piece into the anchor lane); IC-04 explicitly EXCLUDES the four IC-02 files. The `task_helpers.load_meta` symbol is owned by **IC-05** (C6), not IC-04. **The single biggest LOC-reduction lane** (~250–300).
- **Boundary**: the 3 contracts collapse into the `allow_missing` / `on_malformed` parameters; the **absent vs malformed** split here is the same boundary FR-004 relies on (None vs raise) — keep them consistent.

### IC-05 — C6 `task_helpers` shadow-module retirement (DISJOINT lane)
- **FR**: FR-007 — reduce `scripts/tasks/task_helpers.py` (481 LOC, 18 duplicated independent impls) to a thin re-export of `task_utils/support.py`, honoring the `acceptance_support` compat contract.
- **Surface**: `scripts/tasks/task_helpers.py` + its tests / the dead-module allowlist entry.

### IC-06 — accept gates (DISJOINT lane)
- **FRs**: FR-008 (#2084 — accept dirty-tree gate topology-aware; **converge on the `agent/mission.py:862` reference pattern** `routes_through_coordination(placement_ref)` + `is_coordination_artifact_residue_path`, do NOT widen the hardcoded `ACCEPT_OWNED_PATHS` frozenset), FR-009 (#2085a — unchecked-tasks completion derived from WP terminal status; acceptance-matrix gate unchanged, C-010).
- **Surface**: `src/specify_cli/acceptance/__init__.py` (`ACCEPT_OWNED_PATHS` :71, `_find_unchecked_tasks` :396).

### IC-07 — merge residue-gate sweep (DISJOINT lane; #1887)
- **FR**: FR-012 — the three merge `advance_branch_ref(...)` callers (`cli/commands/merge.py:1284`, `lanes/merge.py:458`, `lanes/merge.py:485`) pass `coord_owned_filenames=COORD_OWNED_STATUS_FILES`; the post-merge invariant (`cli/commands/merge.py:~2625`) consults `is_coordination_artifact_residue_path` instead of its hardcoded `{status.events.jsonl, status.json, meta.json}` literal; the recognized-residue set is expressed ONCE and consumed by accept (IC-06), the post-merge invariant, ref-advance, **and the 4th consumer below**.
- **4th residue site (brownfield, alphonso — the plan's I-4 was incomplete)**: `src/specify_cli/lanes/auto_rebase.py:154` `_is_coordination_owned_artifact` (consumed at `:351-352`, the "take theirs" lane-auto-rebase conflict arm) hardcodes a **drifting subset** `{tasks.md, lanes.json, acceptance-matrix.json}` of the canonical `_COORD_RESIDUE_FILENAMES` (`mission_runtime/artifacts.py:71-80`) — it **omits `plan.md`, `issue-matrix.md`, `analysis-report.md`**. Converge it onto `is_coordination_artifact_residue_path` / `_COORD_RESIDUE_FILENAMES` (or carve with explicit rationale). Until then, I-4 ("single residue authority") is asserted but not achieved.
- **Surface**: `src/specify_cli/cli/commands/merge.py`, `src/specify_cli/lanes/merge.py`, `src/specify_cli/lanes/auto_rebase.py`. The `coord_owned_filenames` param + `COORD_OWNED_STATUS_FILES` constant already exist (`git/ref_advance.py:220`, `status/__init__.py:202`) — this is wiring, not new API. **IC-06 × IC-07 is CLEAN** (disjoint files; both import the existing `is_coordination_artifact_residue_path` — **no shared-constant predecessor WP needed**, contrary to the earlier note).

### IC-08 — #1891 `CommitResult` JSON-serialization (DISJOINT small lane; STANDALONE)
- **FR**: FR-013 — **conditional gate RESOLVED in planning (decision 2): `CommitResult` is DISJOINT from FR-001's `.kind` removal** (`CommitResult = {sha, destination_ref, worktree_root: Path}`, no `.kind` / `CommitTargetKind`). The #1891 bug is the un-serializable `Path` field, not the `.kind` work. Therefore FR-013 does **not** fold into IC-02; it lands as its own small lane: make `CommitResult` JSON-serializable (serialize `worktree_root`), scoped to the `agent tasks map-requirements --json` surface. The "`--json` flag missing from `agent action implement`" half of #1891 stays OUT of scope.
- **Surface**: `src/specify_cli/git/commit_helpers.py` (the `CommitResult` dataclass, :422) + the narrow `--json` emit site in `cli/commands/agent/tasks.py`. Disjoint from IC-04's meta-reader sweep — tasks must scope the `tasks.py` ownership to the CommitResult-emit lines only.

## Sequencing & Linearization

```
IC-01 (safety net) ─── must land BEFORE ──▶ IC-02 (anchor chain) ──▶ IC-03 (shim, tail)
   │  (differential cell + AST guard +                  │
   │   NFR-002 RED repro)                               │
   └──────────────────────────────────────┐            ▼
                                           │   FR-004 turns NFR-002 GREEN
DISJOINT lanes (after their anchors,       │
 parallelizable, careful owned_files):     ▼
   IC-04 (C2 meta-reader, large/split)  IC-05 (C6 shadow)  IC-06 (accept)  IC-07 (merge)  IC-08 (#1891)
```

- **IC-01 → IC-02 is a hard barrier** for the FR-004 husk-arm collapse and the FR-001/FR-002 deletions (the gate must be green and the repro RED first).
- **IC-04 is the ownership pressure point** (brownfield-sharpened): BINDING — IC-04's `tasks.py`/`mission.py` WPs land **after** IC-06/IC-08 (file-level ownership, not splittable by line). **IC-02 × IC-04** also collide on four topology files carrying `load_meta` calls → IC-02 owns those four files' meta-read conversions in-slice; IC-04 excludes them.
- **IC-06 and IC-07 both consume the existing `is_coordination_artifact_residue_path`** — CLEAN, disjoint files, **no shared-constant predecessor WP needed** (brownfield correction; the symbol already exists at `artifacts.py:113`).

## Risks

| Risk | Mitigation |
|------|------------|
| **Dogfooding hazard** — this mission's own coordination topology exercises the very paths under cleanup (accept/merge/resolve). | The #2086 seam fix should keep the loop clean; the setup-plan run already resolved cleanly to the coord worktree write surface (a good live signal). Friction in the implement loop is itself a finding — capture, don't paper over. |
| **FR-004 over-collapse** deleting the corrupt-meta fallback (C-004). | Boundary discipline: collapse only the `None`-returning absent-field arms; the `raise`-ing malformed arm stays. The differential gate's `(topology × transient)` matrix + a corrupt-meta cell pin it. |
| **FR-005/C-002 confusion** — collapsing a genuine-fallback relay as if it were a duplicate predicate. | Relays read stored topology first and relay via `classify_topology` only on the exception arm; they are projections' opposite. NFR-005 maps each relay to an unchanged site. |
| **IC-04 owned_files collisions** with smaller lanes on `tasks.py`/`mission.py`. | Linearize the C2 sweep or scope per-subdirectory WPs; `finalize-tasks --validate-only` must pass (no overlap). |
| **C-011 `runtime_bridge` worktree_root regression** during `.kind` removal. | The parallel-classifier WP pins the `worktree_root` selection with a focused test before removing `.kind`. |
| **AST guard fakeability** (FR-011) given `FLATTENED.value == "flattened"` string-collision with the surviving flag. | Symbol/AST resolution, never grep (NFR-003); a planted `"flattened"` literal must not read as dead. |

## Project Structure

### Documentation (this mission)
```
kitty-specs/single-authority-topology-cleanup-01KVRJ6P/
├── spec.md              # committed (635cf4b → 60c2720)
├── plan.md              # this file
├── issue-matrix.md      # #2070/#2084/#2085/#1887/#1891 in-mission; #1716 carve
├── research.md          # Phase 0 (this command)
├── data-model.md        # Phase 1 (this command) — the topology/CommitTarget VO shapes
├── quickstart.md        # Phase 1 (this command) — the live FR-004 repro + differential run
└── tasks.md             # Phase 2 (/spec-kitty.tasks — NOT created here)
```

### Source Code (repository root) — surfaces by IC
```
src/mission_runtime/context.py          # IC-02: .kind decision + CommitTargetKind enum
src/mission_runtime/resolution.py       # IC-02: destination_kind_for_topology, FLATTENED producer, frozenset, relay(KEEP)
src/runtime/next/runtime_bridge.py      # IC-02: parallel-classifier producer + worktree_root(KEEP C-011)
src/specify_cli/coordination/surface_resolver.py   # IC-02: frozenset, relay(KEEP), husk short-circuit(KEEP C-001)
src/specify_cli/coordination/status_transition.py  # IC-02: frozenset, relay(KEEP)
src/specify_cli/missions/_read_path_resolver.py    # IC-02: ~8 topology is None husk-arms (FR-004)
src/specify_cli/migration/backfill_topology.py     # IC-03: ensure_topology shim removal
<meta-reader module + call sites>                  # IC-04: polymorphic load_meta (FR-006)
scripts/tasks/task_helpers.py                       # IC-05: shadow-module → re-export
src/specify_cli/acceptance/__init__.py              # IC-06: accept gates (FR-008/009)
src/specify_cli/cli/commands/merge.py               # IC-07: merge residue-gate sweep (FR-012)
src/specify_cli/lanes/merge.py                      # IC-07: advance_branch_ref callers
src/specify_cli/git/commit_helpers.py               # IC-08: CommitResult JSON-serialization (FR-013)
tests/missions/test_surface_resolution_equivalence.py   # IC-01: differential cell (FR-010)
tests/architectural/                                # IC-01: AST guard (FR-011)
```

## Phase 0 / Phase 1 artifacts

- **research.md** (Phase 0): records the four resolved unknowns — (a) the FR-013 `CommitResult`-disjoint probe outcome; (b) the FR-005 predicate/relay disjointness proof; (c) the FR-004 absent-vs-malformed boundary (`load_meta` None-vs-raise); (d) the IC-04 ownership strategy. No open `[NEEDS CLARIFICATION]`.
- **data-model.md** (Phase 1): the `CommitTarget` VO post-`.kind` (ref-only), the `MissionTopology` projection (`routes_through_coordination`), the `CommitResult` serialization shape, and the single residue-authority contract.
- **quickstart.md** (Phase 1): how to run the differential gate + the live FR-004 un-backfilled-flattened repro (RED→GREEN), and the AST-guard self-check.

## Post-Planning Brownfield Check (squad: randy-reducer + architect-alphonso, 2026-06-23)

Read-only, live-evidence-grounded, run after plan.md before `/spec-kitty.tasks`
(standing brownfield rule: foldable-issue search + split-brain/LOC scan +
deprecation check). The pre-plan fold/duplication angle was already exhausted by
the post-spec squad; this pass found three actionable additions, now folded above.

**Deprecation sweep (randy):**
- **One due deprecation to remove in-slice** → folded into IC-02/FR-002: the dead `safe_commit` re-export shim at `cli/commands/agent/mission.py:54-58` (0 external importers repo-wide).
- **Not this mission**: the `src/specify_cli/next/` 3.3.0 shim is routed through **zero** IC surfaces. KEEP (live callers / intentional): the `destination_ref` compat shim (49 live `destination_ref=` callers — C-007 territory), `ProtectedBranchCommitError`/`assert_not_protected_branch`, the public `ActionContext = ExecutionContext` alias.
- **Record-and-defer (out of IC scope)**: `acceptance/__init__.py:354` `detect_mission_slug` has vestigial sunk params (`repo_root`/`env`/`cwd`/`announce_fallback`); one caller (`tasks_cli.py:674`) still passes `cwd=`. Boy-Scout item outside the touched surfaces — not folded (DIRECTIVE_024 locality).
- **No dead helpers** — every `refs=1` private helper across the IC surfaces is a live single-caller helper.

**Split-brain / LOC / collision (alphonso) — verdict: COHERENT-FOR-TASKS with the 3 gaps now recorded:**
1. **4th residue literal** → folded into IC-07/FR-012: `lanes/auto_rebase.py:154` `_is_coordination_owned_artifact` (drifting subset, missing `plan.md`/`issue-matrix.md`/`analysis-report.md`). I-4 is not single until this converges.
2. **IC-02 × IC-04 file collision** → resolved above: IC-02 owns the four shared topology files' meta-read conversions; IC-04 excludes them. IC-04's `tasks.py`/`mission.py` WPs land after IC-06/IC-08 (binding).
3. **Meta-reader contract count** → corrected in IC-04: 3 distinct error contracts (not 2 adapters) + utf-8-sig BOM nuance; inline figure ~71 (not ~107). NFR-004 ≥750 LOC floor still realistic (C6 ~400 + C2 ~250–300 + enum/predicate ~200).

**Verified-exact estimates (alphonso spot-check)**: CommitTargetKind 45 src + 139 test refs (exact); FLATTENED write-only-dead (2 producers, 0 decision reads, sole `.kind` read at `context.py:131`); `task_helpers.py` 490 LOC / 20 defs / 17 overlap (≈481/18, immaterial); named `load_meta` 66 (✓ ≥66).

## Branch Strategy (restated)

Current branch at plan start: `feat/single-authority-topology-cleanup`. Planning/base
branch: `feat/single-authority-topology-cleanup`. Completed changes merge into
`feat/single-authority-topology-cleanup`, then to `main` via PR at mission close
(no direct pushes to `origin/main`). `branch_matches_target`: true.
