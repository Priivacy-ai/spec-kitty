# Phase 1 Data Model — Single-Authority Topology Cleanup & Dedup

This is a behavior-neutral refactor; no new persisted entities. The "model" is the
set of value objects and the single-authority contracts the mission converges on.

## `CommitTarget` (post-FR-001 — ref-only carrier, C-007)
- **Before**: `{ref: str, kind: CommitTargetKind}` where `kind ∈ {PRIMARY, COORDINATION, FLATTENED}`.
- **After**: `{ref: str}` — a pure ref carrier. The `.kind` attribute is removed.
- **Decision projection** (the single bit `.kind` used to carry): `routes_through_coordination(topology: MissionTopology) -> bool` over the **stored** topology, read in exactly one decision place (`mission_runtime/context.py:131`). The enum disappears entirely.

## `CommitTargetKind` (DELETED)
- 3-valued enum `{PRIMARY="primary", COORDINATION="coordination", FLATTENED="flattened"}`.
- `FLATTENED` is write-only dead (producers `resolution.py:156` / `runtime_bridge.py:241` / `upgrade.py:214` emit PRIMARY; zero `is/== FLATTENED` decision reads).
- **Collision hazard**: `FLATTENED.value == "flattened"` collides with the surviving `flattened` provenance meta-flag — deletion verified by AST/symbol, never grep (NFR-003).

## `flattened` provenance meta-flag (KEPT — C-006)
- A boolean key in `meta.json` recording that a mission was flattened. **Distinct** from the deleted enum member; provenance is still recorded. Producers `mission_creation.py` / `doctor.py` (`meta.setdefault("flattened", False)`).

## `MissionTopology` (SSOT — unchanged, consumed not modified)
- Enum `{SINGLE_BRANCH, LANES, COORD, LANES_WITH_COORD}` stored in `meta.json.topology`.
- **Coord-routing set** (FR-005 single authority): `{COORD, LANES_WITH_COORD}` — collapsed from 4 verbatim definitions (`resolution.py:139` `_COORD_ROUTING_TOPOLOGIES`, `surface_resolver.py:91` `_COORD_SURFACE_TOPOLOGIES`, `runtime_bridge.py:78`, inline `status_transition.py:590`) to ONE shared frozenset + ONE predicate.
- **Absorbing reader** (FR-004): `read_topology(feature_dir) -> MissionTopology` (`backfill_topology.py:68`) — returns the stored value, else `classify_from_meta(meta, feature_dir)` derives a concrete topology. Never returns `None`. The read-path boundary threads this concrete value downstream, killing the `topology is None` husk-arms.

## `CommitResult` (post-FR-013 — JSON-serializable)
- `{sha: str, destination_ref: str, worktree_root: Path}` (`git/commit_helpers.py:422`).
- **Change**: add JSON serialization (serialize `worktree_root` Path → str) so the `agent tasks map-requirements --json` surface emits valid JSON (#1891). No field change; **disjoint from `.kind`** (R1).

## Single residue authority (FR-008 + FR-012 converge)
- **Predicate**: `is_coordination_artifact_residue_path(path, *, mission_slug)` (`mission_runtime/artifacts.py:113`).
- **Constant**: `COORD_OWNED_STATUS_FILES = frozenset({EVENTS_FILENAME, SNAPSHOT_FILENAME})` (`status/__init__.py:202`).
- **Consumers after the mission** (no gate carries its own residue literal):
  - `acceptance/__init__.py` accept dirty gate (FR-008) — converges on the `agent/mission.py:862` pattern (`routes_through_coordination(placement_ref)` + the predicate), retiring the hardcoded `ACCEPT_OWNED_PATHS`-only check.
  - `cli/commands/merge.py:1284` + `lanes/merge.py:458/485` ref-advance callers (FR-012) — pass `coord_owned_filenames=COORD_OWNED_STATUS_FILES`.
  - `cli/commands/merge.py:~2625` post-merge invariant (FR-012) — consults the predicate instead of `{status.events.jsonl, status.json, meta.json}`.
  - `lanes/auto_rebase.py:154` `_is_coordination_owned_artifact` (FR-012, 4th site) — consults `_COORD_RESIDUE_FILENAMES` instead of the drifting subset `{tasks.md, lanes.json, acceptance-matrix.json}` (which omits `plan.md`/`issue-matrix.md`/`analysis-report.md`).

## Invariants
- **I-1 (behavior neutrality)**: on a backfilled mission, every resolution/routing/commit decision is byte-identical pre/post mission (differential gate).
- **I-2 (one decision bit)**: coordination routing is decided by exactly one predicate over stored topology; `.kind` is not read anywhere post-mission (AST guard, FR-011).
- **I-3 (absorption correctness)**: an un-backfilled flattened mission resolves to PRIMARY (classify-on-read), not the stale-coord husk (FR-004 / NFR-002).
- **I-4 (single residue authority)**: the recognized-coordination-residue set is expressed once and consumed by **all four** dirty/conflict gates — accept (FR-008), the post-merge invariant + ref-advance callers (FR-012), and the lane-auto-rebase conflict arm `auto_rebase.py:154` (FR-012, 4th site found by the post-plan brownfield squad; previously a drifting subset). No gate carries its own residue literal.
- **I-5 (corrupt-meta preserved)**: unreadable meta still raises a typed error; absorption never silences it (C-004).
