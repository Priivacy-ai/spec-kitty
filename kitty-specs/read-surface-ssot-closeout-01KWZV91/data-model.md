# Data Model — Read-Surface SSOT Completion

This is a routing/consolidation mission; the "data model" is the small set of runtime concepts the routing
introduces or reshapes. No persistent schema changes.

## PartitionedCommitBatch (IC-01 / FR-007)

The reshaped input contract for `commit_for_mission`.

| Field | Type | Notes |
|-------|------|-------|
| `files` | `list[Path]` | The batch to commit (may be mixed-partition). |
| `partition_of(file)` | `Surface` (PRIMARY \| PLACEMENT) | Derived per-file via `kind_for_mission_file(path, mission_slug)` → `is_primary_artifact_kind(kind)`. |
| `groups` | `dict[Surface, list[Path]]` | Files grouped by partition. |
| `target_of(surface)` | `CommitTarget` | Each group commits to its own ref (primary target / coord ref) via `resolve_placement_only(kind=…)`. |

**Invariant (INV-C1)**: every file in a group resolves to the same `CommitTarget`; a group is never committed to
another partition's ref. **Behaviour rule**: a single-partition batch keeps the existing fast path (no
regression); a mixed-partition batch is split into per-partition commits (or guard-rejected — the WP chooses
one and pins it with a red-first test). Replaces the current single-`kind`-for-whole-batch resolution at
`commit_router.py:152`.

## CoordAuthorityDrain (IC-04 / FR-002/FR-003)

The state transition of the `coord_authority` ratchet.

| Field | Type | Notes |
|-------|------|-------|
| `floor` | `int` | `7 → 2` (re-pinned AFTER FR-003 predicate widen). |
| `margin` | `int` | `COORD_AUTHORITY_WRITE_FLOOR_MARGIN`; `live − margin ≤ floor < live` must hold. |
| `permanent` | `set[CompositeKey]` | `decisions/emit.py:71`, `widen/state.py:63` (by-design). |
| `site.direction` | `READ \| WRITE` | **Manual** adjudication, not the scanner's `is_write` flag. |

**Reclassified-as-write (never routed)**: `lanes/recovery.py:755`, `agent_tasks_ports.py:322`.
**Genuine write routed via `write_target`**: `workflow.py:2747`. **Reads routed via `read_dir`**: the rest.

## MetaReadRatchetState (IC-06 / FR-006)

The new, non-vacuous gate (mirrors `resolution_gate_allowlist.yaml` mechanics).

| Field | Type | Notes |
|-------|------|-------|
| `floor` | `int` | Concrete integer floor (post-drain count). |
| `margin` | `int` | Shrink-only guard. |
| `routed_count_floor` | `int` | **Anti-mass-allow-list**: the count of *routed* sites cannot regress; the allow-list cannot silently swallow the census. |
| `allow_list[entry]` | `CompositeKey + rationale + issue_ref` | Each deferred site (e.g. `m_0_13_*`) carries a rationale AND a filed follow-up issue number; **stale-entry detection** fails if an allow-list key no longer matches a live site. |

**Invariant (INV-C2)**: a re-introduced inline `json.loads(<meta>)` read goes RED; a mass-allow-list attempt
trips the routed-count floor.

## Read/write authorities (consumed, unchanged)

| Authority | Role | Source |
|-----------|------|--------|
| `PlacementSeam.read_dir(kind)` | feature-dir READ | `mission_runtime/resolution.py` (#2462) |
| `PlacementSeam.write_target(kind)` | feature-dir WRITE | idem |
| `load_meta` / `load_meta_strict` / `load_meta_or_empty` | meta.json READ | `specify_cli/mission_metadata.py` |
| `kind_for_mission_file` | per-file kind classifier | `mission_runtime/artifacts.py` |

The kind→partition mapping (`_PRIMARY_/_PLACEMENT_ARTIFACT_KINDS`) is **read-only** this mission (C-002).
