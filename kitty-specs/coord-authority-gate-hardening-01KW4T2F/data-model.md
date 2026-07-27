# Data Model — Coord-Authority Gate Hardening (01KW4T2F)

Phase 1. The "entities" here are GATE entities — the static-analysis vocabularies, census sets, and fixtures the hardening operates over. No runtime persisted state, no schema migrations. All sets are defined in `tests/architectural/` (the arm) and `src/mission_runtime/artifacts.py` (the partition), and all fixtures in `tests/integration/coord_topology_fixture.py`.

---

## 1. Read-func families (the call-shape arm vocabulary)

The two kind-read shapes the call-shape arm gates, each bounded to its own scan scope (SC-005 — never red-CI on out-of-scope strangers).

| Family | Read funcs | Scan scope (current) | Scan scope (after FR-002/FR-005) |
|--------|-----------|----------------------|-----------------------------------|
| IDENTITY | `resolve_mission_identity`, `get_mission_type` | `cli/commands/` + `agent_utils/status.py` | **+ `merge/` + `lanes/` + `core/worktree_topology.py`** (FR-002) **+ `src/runtime/next/`** (FR-005) |
| LANES.JSON | `read_lanes_json`, `require_lanes_json` | `merge/` + `lanes/` + `core/worktree_topology.py` | **+ `src/runtime/next/`** (FR-005) |

Defined: `_IDENTITY_READ_FUNCS` / `_LANES_READ_FUNCS` (`test_gate_read_literal_ban.py`); scan dirs `_IDENTITY_SCAN_DIRS` / `_IDENTITY_SCAN_FILES` / `_LANES_SCAN_DIRS` / `_LANES_SCAN_FILES` (`test_coord_read_residuals_closeout.py`).

---

## 2. Coord-aware resolver set (the divergence source)

A dir bound from one of these selects the STATUS-only `-coord` husk under coord topology (no `meta.json`/`lanes.json` since #2106). A kind-read off such a dir without a primary fold is the violation.

```
_COORD_AWARE_CALLSHAPE_RESOLVERS = {        # CURRENT — 3 names
    "resolve_feature_dir_for_mission",
    "candidate_feature_dir_for_mission",
    "resolve_feature_dir_for_slug",
}
```

**FR-001 widening (REQUIRED — root cause of the FR-001 hollowness).** This 3-name set is **narrower than the read-arm's `_TOPOLOGY_ROUTED_READ_RESOLVERS` (5 names** — the 3 above plus `_find_feature_directory` and `resolve_handle_to_read_path`). The named one-hop residual `_run_documentation_wiring` ← `setup_plan` binds `feature_dir` from `_resolve_setup_plan_feature_dir` → `_find_feature_directory`, which this 3-name set does NOT recognize as coord-aware → the one-hop check would fire on no live caller. **FR-001 MUST widen the call-shape coord-aware set to align with `_TOPOLOGY_ROUTED_READ_RESOLVERS`** (catalog `_resolve_setup_plan_feature_dir` and/or `_find_feature_directory`) so the residual's binding is recognized. The one-hop check also needs a **module-scoped caller index** (the per-function `callshape_violations(func, *, read_funcs)` signature gains caller/module context). Re-run the NFR-004 census across the widened surface.

## 3. Primary-fold seam set (the sanctioned shape)

A dir bound from / built by one of these lands on the durable PRIMARY `kitty-specs/<slug>-<mid8>/` home for every topology — NEVER flagged.

```
_PRIMARY_FOLD_CALLSHAPE_FUNCS = {
    "_canonicalize_primary_read_handle",
    "primary_feature_dir_for_mission",
    "resolve_planning_read_dir",
}
```

## 4. Sanctioned primary attributes / folds (FR-008)

When a kind-read's first arg is an `ast.Attribute`, it is sanctioned (never flagged) iff it is a primary-attr:

| Sanctioned attribute | Why |
|----------------------|-----|
| `.target_feature_dir` | the primary-surface field on the run/context object |
| a field bound from a primary fold | already folded onto PRIMARY by the caller |

Any other coord-bearing attribute (e.g. `run.feature_dir`) is flagged. Self-mutation anchor: `resolve_mission_identity(run.feature_dir)` in `executor` → RED.

---

## 5. Named shrink-only census + sanctioned-exclusion set (FR-003)

Every in-scope param-/attribute-fed kind-read is either routed or recorded in a NAMED shrink-only census, mirroring `_CALLSHAPE_KNOWN_RESIDUALS` (currently `frozenset()`) and `_DIR_READ_KNOWN_RESIDUALS`.

**Census schema** (per entry): `"<rel_path>::<qualname>"` → tracked residual with a tracker reference. Shrink-only semantics:

- A NEW in-scope flag not in the census → **RED** (cannot hide behind the known set).
- A pinned residual that no longer flags (fixed) → **RED** (remove the stale pin; ratchet stays tight).

**Sanctioned, never-flagged (NOT census entries — true exclusions)**:

| Exclusion | Kind | Why never flagged |
|-----------|------|-------------------|
| `require_lanes_json` | leaf primitive | MUST take a dir; it IS the by-kind resolver leaf (C-006) |
| `_mission_identity_payload` | payload/builder helper | builds a payload from an already-resolved dir, not a read-routing decision |
| **`read_events` STATUS-leg reads** inside `_STATUS_BEARING_MODULES` (`lanes/recovery.py`, `merge/executor.py`) | STATUS leg | **C-007 binding**: a "self-resolve → PRIMARY" remediation here would move a STATUS leg to PRIMARY (C-001/#2155 re-opener) |

**The exclusion is READ-FUNC-SCOPED, not a blanket module exclusion (paula/renata post-plan).** `_STATUS_BEARING_MODULES` pairs with `_STATUS_READ_FUNCS = {"read_events"}` — only the **`read_events` STATUS legs** in `recovery.py`/`executor.py` are excluded. **Identity/lanes reads in the same modules remain IN-SCOPE and flaggable** — in particular an injected `resolve_mission_identity(run.feature_dir)` off a coord-aware dir in `merge/executor.py` (SC-006 / FR-008) MUST be caught. Excluding the whole module would let the SC-006 executor residual escape (FR-008 directly requires it be flagged). `_STATUS_BEARING_MODULES = ("src/specify_cli/lanes/recovery.py", "src/specify_cli/merge/executor.py")`; the `read_events` STATUS leg stays coord-aware (the NFR-001 secondary cross-check already guards this — do not regress it).

---

## 6. PRIMARY/STATUS partition + the per-kind rationale map (FR-006)

### The live partition (`src/mission_runtime/artifacts.py`)

`MissionArtifactKind` (14 members). The two frozensets partition it exactly once (exhaustive + disjoint — asserted today):

| Partition | Members |
|-----------|---------|
| `_PRIMARY_ARTIFACT_KINDS` | `SPEC`, `DATA_MODEL`, `RESEARCH`, `CHECKLIST`, `FINALIZED_EXECUTION_PLAN`, `TASKS_INDEX`, `WORK_PACKAGE_TASK`, `LANE_STATE`, `PRIMARY_METADATA`, `RETROSPECTIVE` |
| `_PLACEMENT_ARTIFACT_KINDS` (COORD) | `ACCEPTANCE_MATRIX`, `ISSUE_MATRIX`, `STATUS_STATE`, `ANALYSIS_REPORT` |

### The net-new machine-read rationale map

```
PARTITION_RATIONALE: dict[MissionArtifactKind, tuple[partition, rationale, load_bearing_consumer]]
```

- One entry per enum member (missing entry → RED).
- The map's derived PRIMARY/STATUS split MUST `==` the live frozensets (re-home a kind without editing its rationale → RED → SC-003).
- A parametrized anti-mutant runs across ALL load-bearing kinds (not just SPEC): forcing each kind into the opposite partition makes its placement-ref assertion go RED.

Keyed on enum members — content-anchored, allowlist-free, zero line-pins (CT7 exemplar, C-004 / NFR-005).

---

## 7. The divergent coord-topology fixture (`tests/integration/coord_topology_fixture.py`)

The behavioral backstop reused for SC-001/SC-002/FR-007. No resolver is patched — real git + filesystem state.

| Fixture | Husk shape | Used by |
|---------|-----------|---------|
| `coord_topology_mission` | PRIMARY: `meta.json` (topology=coord, coordination_branch), `tasks/WP01.md`, `lanes.json`, DECOY `status.events.jsonl`. Coord husk: `status.events.jsonl` ONLY (no `tasks/`, no `lanes.json`, no `meta.json`). | SC-002 (preview revert-fails), FR-007(a) production-shaped STATUS-only husk |
| `coord_topology_mission_sentinel_meta` | as above + husk `meta.json` PRESENT-but-WRONG (`SENTINEL_HUSK_MISSION_ID`, `SENTINEL_HUSK_MISSION_TYPE`=`research`) — wrong-leg read returns a SILENT-WRONG domain value rather than raising | identity revert-fails proofs |
| `flat_topology_mission` | single-branch neutrality | neutrality checks |
| **NEW (owned by IC-C / FR-007)**: `tasks/`-present-non-legacy husk variant | a coord husk carrying a post-3.0 `tasks/` (WP `.md`, no `planned/doing/...` lane subdirs) | FR-007(b) — exercises the `LEGACY_LANE_DIRS`/`.md` branch → still no-op |

**Single-consumer rule (paula post-plan correction — there is NO fixture contention).** IC-B's SC-002 uses the **existing** `coord_topology_mission` fixture (its STATUS-only husk already lacks `tasks/`); IC-B does not need the `tasks/`-present-non-legacy variant. The new variant is consumed **only by IC-C (FR-007(b))**, so **IC-C owns and adds it**. The earlier "extend ONCE in IC-B, IC-C consumes read-only" contention resolution is removed: with a single consumer there is no contention to resolve.

Helpers: `assert_reads_primary`, `assert_status_from_coord`, `assert_both_legs` (existing, reused).

---

## 8. CT7 content-anchor primitive (consumed, not modified)

`tests/architectural/_ratchet_keys.composite_key(source, lineno) -> (qualname, token_line)` — the drift-proof anchor that survives +1 line drift (qualname + string/comment-stripped token line). Every new/extended gate keys off `composite_key`, never `file.py:NNN` (NFR-001).
