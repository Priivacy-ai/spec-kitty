# Seam & Gate Contracts — coord-read-residuals-merge-lanes-and-identity-routing-01KW2M8V

The binding contracts this mission consumes/asserts. Consume the seam, never author it (C-002).

## 1. Read-seam routing contract (`resolve_planning_read_dir(repo_root, slug, kind)`)

| Artifact kind | Partition | Resolves to | Used for |
|---|---|---|---|
| `WORK_PACKAGE_TASK`, `LANE_STATE`, `PRIMARY_METADATA`, `RESEARCH`, `SPEC` | PRIMARY | `primary_feature_dir_for_mission` (topology-blind) | the routed reads in this mission |
| `STATUS_STATE` (events, matrices) | STATUS | coord-aware (`candidate_feature_dir_for_mission`) | KEEP legs — never routed |

- **Routed (PRIMARY):** every `lanes.json` / `meta.json`-identity / `tasks/` READ in the implement/review/merge loop and the merge/lanes/core cluster. `LANE_STATE ∈ _PRIMARY_ARTIFACT_KINDS` (verified `mission_runtime/artifacts.py`).
- **KEEP (coord, C-001 / #2155 — touching re-opens the write-side split-brain):** `lanes/recovery.py:reconcile_status` (feeds `emit_status_transition_transactional`); `recovery.py:scan_recovery_state` events leg (`_get_*_from_events` on a separate `coord_dir`); `merge/executor` `run.feature_dir`/`status_feature_dir`; `agent_utils/status.py:read_events`; `merge/resolve.py` handle-canonicalization (no-fallback boundary, C-005).
- `merge/done_bookkeeping` status-transactional write resolves its target via `resolve_placement_only(STATUS_STATE)` → coordination branch ("MUST NOT be flipped to a primary kind"); the PRIMARY meta-dir is used only for coord-ref *derivation* (the husk lacks meta post-#2106).

## 2. FR-007 call-shape arm gate contract (the static ratchet)

`callshape_violations(func, *, read_funcs)` flags a call whose first arg is a coord-aware-bound dir (two-hop or inline) WITHOUT a primary fold (`_canonicalize_primary_read_handle`/`primary_feature_dir_for_mission`/`resolve_planning_read_dir`), for two shapes:
- **identity:** `resolve_mission_identity` / `get_mission_type` — scope `cli/commands/` + `agent_utils/status.py`.
- **lanes.json:** `read_lanes_json` / `require_lanes_json` — scope `merge/` + `lanes/` + `core/worktree_topology.py`.

Closes the literal-ban ratchet's permanent blind spot (it cannot see `lanes.json`/function-call `meta.json` reads). Wired LIVE over the real tree via `_iter_functions_under` (WP05 close-out): **0 un-pinned** (identity 12/12, lanes.json 10/10), empty `_CALLSHAPE_KNOWN_RESIDUALS` (shrink-only), with an anti-vacuity floor (live counts pinned `>=10`/`>=8`) so a scanner-break that matches nothing fails RED. Identity reads in merge/lanes/core that are NOT in the arm's identity scope are covered behaviorally by §3 (stated honestly in FR-006).

## 3. FR-009 divergent-fixture contract (the behavioral backstop)

Reuse `tests/integration/coord_topology_fixture.py` (genuinely divergent: STATUS-only husk) + the `coord_topology_mission_sentinel_meta` variant. HARD precondition triad, asserted BEFORE any routed drive (proven load-bearing — copying primary artifacts into the husk turns it RED):
- `assert not (coord_husk / "lanes.json").exists()`
- `assert not (coord_husk / "tasks").exists()`
- husk `meta.json mission_id == SENTINEL (6KERGF2ZNFBPR91YEZMARG99KS)` and `!= ctx.mission_id` (the fixture's real primary `01KW2E7AFC…`)

**Revert-fails terminal MUST be a returned DOMAIN VALUE** (forecast WP set / materialized worktrees / recovery lanes / resolved mission type / lifecycle mission_id) — NOT path-equality; the fixture's `assert_reads_primary`/`assert_both_legs` helpers are NOT acceptable as the terminal.

## 4. Floor honesty contract (FR-010)

`ROUTED_CANONICALIZER_FLOOR` only moves when a routed site uses the DIRECT `primary_feature_dir_for_mission(_canonicalize_primary_read_handle(...))` primitive. Seam-routed sites (`resolve_planning_read_dir`) do NOT increment the census. WP01's 7 identity anchors moved it 38→45 total / 35→42 routed; WP02/WP03 went through the seam (no movement) — stated plainly, never a re-pinned-integer "gain".
