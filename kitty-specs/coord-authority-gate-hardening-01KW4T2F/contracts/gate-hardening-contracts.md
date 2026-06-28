# Gate Contracts — Coord-Authority Gate Hardening (01KW4T2F)

Phase 1 contracts. Four gate contracts that the WPs must satisfy. Each is content-anchored (CT7/NFR-001), non-vacuous, and self-mutation-tested (NFR-002). These are the binding acceptance shapes for `/spec-kitty.tasks` to decompose against.

---

## Contract A — Call-shape arm flag-rule (FR-001 + FR-008 + exclusions)

**Subject**: `callshape_violations(func, *, read_funcs)` in `tests/architectural/test_gate_read_literal_ban.py`.

**FLAG a kind-read** (`read_funcs` ∈ {IDENTITY, LANES}) iff its first arg is one of:

1. **(existing) two-hop local Name** bound (same function) from `_COORD_AWARE_CALLSHAPE_RESOLVERS` and NOT also bound from `_PRIMARY_FOLD_CALLSHAPE_FUNCS`.
2. **(existing) inline Call** to a coord-aware resolver.
3. **(FR-001 NEW) function PARAMETER** whose caller (one hop up) binds that arg from a coord-aware resolver WITHOUT a primary fold. **Requires (a) WIDENING `_COORD_AWARE_CALLSHAPE_RESOLVERS` to align with the read-arm's `_TOPOLOGY_ROUTED_READ_RESOLVERS` (5 names — add `_find_feature_directory` / `_resolve_setup_plan_feature_dir`), without which the `_run_documentation_wiring` ← `setup_plan` binding is not recognized as coord-aware and the residual is unreachable; and (b) a MODULE-SCOPED CALLER INDEX (the per-function `callshape_violations(func, *, read_funcs)` signature gains caller/module context).** Re-run the NFR-004 census over the widened surface.
4. **(FR-008 NEW) Attribute** that is coord-bearing and NOT a sanctioned primary attribute (`.target_feature_dir` / primary-fold-bound field).

**NEVER FLAG**:
- A first arg bound from / built by a primary-fold seam (sanctioned routed shape).
- A plain parameter whose caller-binding is primary/seam-bound or non-coord-aware (FR-001 boundary — re-pin `test_callshape_arm_identity_passes_parameter_dir` to stay consistent; do NOT leave it contradictory).
- The sanctioned exclusions: leaf primitive `require_lanes_json`, payload helper `_mission_identity_payload`, and the **`read_events` STATUS-leg reads** inside `_STATUS_BEARING_MODULES` (C-007). **Read-func-scoped, NOT blanket-module:** the exclusion is `_STATUS_READ_FUNCS = {"read_events"}` only — identity/lanes reads in `executor.py`/`recovery.py` (incl. an injected `resolve_mission_identity(run.feature_dir)`, SC-006) stay IN-SCOPE and flaggable.

**Self-mutation (NFR-002 / SC-001 / SC-006)** — each shape ships its own:
- `_VIOLATION_CROSS_FUNCTION` (param bound from coord-aware caller) → RED; clean counterpart (param from primary-fold caller) → GREEN.
- `_VIOLATION_ATTRIBUTE` (`resolve_mission_identity(run.feature_dir)` in executor-shape) → RED; `.target_feature_dir` counterpart → GREEN.

**Scope-unify (FR-002)**: the IDENTITY scan family also covers `merge/` + `lanes/` + `core/worktree_topology.py`. SC-006: an injected identity read off a coord-aware dir in `merge/executor.py` — BOTH the parameter shape AND the `run.feature_dir` attribute shape — is caught post-mission.

**Anti-vacuity**: the live scan SEES the in-scope read call sites (the `_count_read_call_sites` floors; raise the floor census after FR-002 widens scope).

---

## Contract B — Named shrink-only census (FR-003)

**Subject**: `_CALLSHAPE_KNOWN_RESIDUALS` (and its sibling for the widened identity scope) in `test_coord_read_residuals_closeout.py`.

- Every in-scope param/attribute-fed kind-read is **routed** OR present in the census with a tracker reference.
- **Shrink-only**: a NEW un-pinned flag → RED; a stale pin no longer flagged → RED (remove it).
- The sanctioned exclusions (Contract A) are NOT census entries — they are never-flagged true exclusions.
- **C-005**: coordinate (do not rot) the shrink-only `_DIR_READ_KNOWN_RESIDUALS` #2167 pin.
- **NFR-004**: full `tests/architectural/` green on the current tree; the census enumerates every in-scope param/attribute read site with a route-or-pin disposition (zero false positives).

---

## Contract C — Rationale-map ↔ frozenset cross-check (FR-006)

**Subject**: a machine-read `PARTITION_RATIONALE: dict[MissionArtifactKind, tuple[partition, rationale, load_bearing_consumer]]` in `test_write_surface_placement_guard.py`, cross-checked against `_PRIMARY_ARTIFACT_KINDS` / `_PLACEMENT_ARTIFACT_KINDS` (`src/mission_runtime/artifacts.py`).

- (a) **Exhaustive**: every `MissionArtifactKind` member has an entry (missing → RED).
- (b) **Split equality**: the map's derived PRIMARY/STATUS split `==` the live frozensets (re-home a kind without editing its rationale → RED → SC-003).
- (c) **All-kinds anti-mutant**: parametrized across ALL load-bearing kinds — forcing each kind into the opposite partition makes its `resolve_placement_only(...).ref` assertion go RED (not just SPEC).
- **Net-new only / NFR-005**: exhaustive + disjoint + the SPEC anti-mutant already exist (`test_full_partition_resolves_per_membership`); add NO line-pins; keep allowlist-free (CT7 exemplar, C-004).

---

## Contract D — #2197 routing + husk no-op (FR-004 / FR-005 / FR-007)

### D.1 Routing (FR-004, caller-only)

**Subject**: `runtime_bridge.py::_build_finalized_override_query_decision` (the `preview_claimable_wp(feature_dir)` call).

- Pass a PRIMARY `planning_dir` (kind-aware seam / `primary_feature_dir_for_mission`) AND the coord `status_dir=` (coord-aware leg), mirroring `workflow.py::_preview_claimable_wp_for_mission`.
- `discovery.preview_claimable_wp` already carries the `status_dir=` leg-split — this is a CALLER-ONLY change (C-003: the single sanctioned production routing edit).
- **C-001/C-002**: the status leg stays coord-aware; consume `resolve_planning_read_dir`, do not author `_read_path_resolver` internals.

**SC-002 (behavioral revert-fails)**: an EXECUTED test against the divergent coord fixture asserts the returned DOMAIN value `preview.wp_id` (NOT a resolved-path equality). Reverting the FR-004 routing → coord husk → wrong/empty `wp_id` → RED.

### D.2 Scan-scope un-mask (FR-005)

- Extend the live identity/lanes scan families to include `src/runtime/next/`, with a `runtime/next` read-site floor (mirroring `_count_read_call_sites`) proving non-vacuity. **Non-vacuous on the current tree:** `runtime_bridge.py` already carries ≥3 in-family identity reads (`get_mission_type(feature_dir)` at ~:2547/:3237/:3392); each gets an explicit **route-or-pin disposition** under the Contract B census so the scope extension lands NFR-004-green.
- **DECOUPLING (binding)**: the FR-004 read is a `tasks/`-dir, parameter-fed shape the call-shape arm cannot see — it is gated BEHAVIORALLY by SC-002, NOT by this scan. The scan does NOT "gate FR-004"; it closes the runtime/next blind spot for the identity/lanes families.
- **NFR-003 (gate-unmask-cannot-self-validate)**: pair with a pre-merge verbatim full-`tests/architectural/` dry-run recorded in the PR body.

### D.3 Husk no-op (FR-007 / SC-004)

**Subject**: `check_pre30_layout` (`src/specify_cli/upgrade/pre30_guard.py`).

- Clean no-op against (a) a production-shaped STATUS-only husk (real `status.events.jsonl` + `meta.json`, no `tasks/` — via the fixture, NOT an empty dir which short-circuits identically).
- Clean no-op against (b) a `tasks/`-present-but-non-legacy variant (exercises the `LEGACY_LANE_DIRS`/`.md` branch in `is_legacy_format` → still no-op).
- **Fixture ownership (single consumer — no contention)**: SC-002 (IC-B) uses the EXISTING `coord_topology_mission` fixture; the `tasks/`-present-non-legacy husk variant is consumed ONLY by FR-007, so **IC-C owns and adds it**.

---

## Cross-cutting (all contracts)

- **NFR-001 (CT7)**: zero new `file.py:NNN` ratchet anchors; content-anchor via `composite_key`.
- **NFR-002**: every new/extended gate ships a self-mutation test (synthetic offender → RED, revert → GREEN) + an anti-vacuity floor.
- **NFR-005**: net test-suite-friction non-positive — no new allowlist/manual-denylist maintenance surface beyond the reused auto-discovery pattern.
