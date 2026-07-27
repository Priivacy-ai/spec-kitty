# Tasks — Coord-Authority Gate Hardening (01KW4T2F)

**Mission**: coord-authority-gate-hardening-01KW4T2F | **Epic**: #2160 (umbrella, stays open) | **Closes**: #2197, #2198, #2199, #2214
**Branch**: `feat/coord-authority-gate-hardening`
**Source design**: [spec.md](./spec.md) · [plan.md](./plan.md) · [research.md](./research.md) · [data-model.md](./data-model.md) · [contracts/gate-hardening-contracts.md](./contracts/gate-hardening-contracts.md) · [quickstart.md](./quickstart.md)

## Decomposition rationale (IC → WP)

The plan's implementation concerns (IC-A1/A2/A3, IC-B, IC-C) are repackaged into **four ownership-disjoint WPs partitioned by file**, because the no-overlap ownership rule must hold and the arm has a clean two-file layering:

- `test_gate_read_literal_ban.py` = the **arm logic** (pure AST scanner `callshape_violations` + resolver vocab + self-mutation snippets) → **WP01** (IC-A2 + IC-A1's attribute half).
- `test_coord_read_residuals_closeout.py` = the **scan harness** (scan-dir scope + census + floors; imports the arm) → **WP02** (IC-A1's scope-unify half + IC-A3 census + IC-B's FR-005 scan-scope).
- `src/runtime/next/runtime_bridge.py` (+ behavioral test) = the **#2197 production routing** → **WP03** (IC-B's FR-004 + SC-002).
- partition guard + coord fixture (+ husk no-op test) = the **partition/husk coverage** → **WP04** (IC-C, fully parallel).

WP02 depends on WP01 (the census enumerates what the hardened arm flags; scope-unify is exercised against the hardened arm). WP03 depends on WP02 (runtime/next scan-scope + floor pinned before `runtime_bridge.py` is edited). WP04 is parallel (disjoint files, no dep).

```
WP01 (arm logic: FR-001 + FR-008)
   └─> WP02 (scan harness + census + runtime/next floor: FR-002 + FR-003 + FR-005)
          └─> WP03 (#2197 routing + SC-002: FR-004)
WP04 (partition map + husk no-op: FR-006 + FR-007)  — PARALLEL, no deps
```

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|----|----------|
| T001 | Widen `_COORD_AWARE_CALLSHAPE_RESOLVERS` to align with `_TOPOLOGY_ROUTED_READ_RESOLVERS` (5 names) | WP01 | | [D] |
| T002 | Add the `ast.Attribute` branch to `callshape_violations` (FR-008 attribute-discipline) | WP01 | | [D] |
| T003 | Add module-scoped caller index + one-hop parameter caller-binding detection (FR-001) | WP01 | | [D] |
| T004 | Re-pin `test_callshape_arm_identity_passes_parameter_dir` consistent with FR-001 | WP01 | | [D] |
| T005 | Ship per-shape self-mutation snippets+tests (`_VIOLATION_CROSS_FUNCTION`, `_VIOLATION_ATTRIBUTE`) | WP01 | | [D] |
| T006 | FR-002 — widen identity scan family to `merge/` + `lanes/` + `core/worktree_topology.py` | WP02 | | [D] |
| T007 | FR-005 — extend identity+lanes scan families to `src/runtime/next/` + read-site floor | WP02 | | [D] |
| T008 | FR-003 — named shrink-only census with per-arm stale-pin split; route-or-pin the 3 `get_mission_type` reads | WP02 | | [D] |
| T009 | FR-003 — read-func-scoped sanctioned exclusions (C-007); keep identity/lanes reads in status modules in-scope | WP02 | | [D] |
| T010 | SC-006 live-scope coverage + raise anti-vacuity floor; full `tests/architectural/` green | WP02 | | [D] |
| T011 | FR-004 — re-point `preview_claimable_wp` to the PRIMARY/STATUS leg-split (caller-only) | WP03 | |
| T012 | Preserve the `tasks/`-absent None / `selection_reason` handling around the routed call | WP03 | |
| T013 | SC-002 — behavioral revert-fails test asserting `preview.wp_id` (domain value) | WP03 | |
| T014 | FR-006 — add machine-read `PARTITION_RATIONALE` map | WP04 | [D] |
| T015 | FR-006 — exhaustive + split-equality + all-load-bearing-kinds anti-mutant assertions | WP04 | [D] |
| T016 | FR-007 — add the `tasks/`-present-non-legacy husk fixture variant (IC-C owns it) | WP04 | [D] |
| T017 | FR-007 — `check_pre30_layout` no-op test against both husk shapes | WP04 | [D] |

---

## WP01 — Call-shape arm logic: one-hop cross-function + attribute-discipline

- **Goal**: Harden the AST scanner `callshape_violations` so it catches (a) a coord-aware dir bound one hop up and passed in as a **parameter** (FR-001) and (b) a coord-bearing **attribute** like `run.feature_dir` (FR-008), keying off the read-arm-aligned resolver vocabulary. Pure arm logic + its self-mutation tests — no scan-harness or census changes here.
- **Priority**: P1 (MVP spine — the only arm-signature change; everything else builds on it).
- **Requirements**: FR-001, FR-008; NFR-001, NFR-002, NFR-004; C-006, C-007; SC-001 (synthetic), SC-006 (synthetic-attribute half).
- **Independent test**: `PWHEADLESS=1 pytest tests/architectural/test_gate_read_literal_ban.py -q` — the new `_VIOLATION_CROSS_FUNCTION` and `_VIOLATION_ATTRIBUTE` self-mutation tests are present and green; `test_callshape_arm_identity_passes_parameter_dir` re-pinned and consistent.
- **Owned files**: `tests/architectural/test_gate_read_literal_ban.py`
- **Dependencies**: none
- **Subtasks**: T001, T002, T003, T004, T005
- **Estimated size**: ~5 subtasks, ~360 lines

## WP02 — Scan-scope unify + named census + runtime/next floor

- **Goal**: Drive the hardened arm over a widened, asymmetry-closed scan surface (identity arm gains `merge/` + `lanes/` + `core/worktree_topology.py`; both arms gain `src/runtime/next/`), record every in-scope param/attribute read as routed-or-pinned in a **named shrink-only census** with read-func-scoped sanctioned exclusions, and prove the runtime/next extension non-vacuous with a read-site floor.
- **Priority**: P1 (closes the SC-006 scope asymmetry; lands the census the whole arm relies on).
- **Requirements**: FR-002, FR-003, FR-005; NFR-001..NFR-004; C-005, C-007; SC-006 (live-scope half).
- **Independent test**: `PWHEADLESS=1 pytest tests/architectural/test_coord_read_residuals_closeout.py -q` then `PWHEADLESS=1 pytest tests/architectural/ -q` — both green; the identity scan covers `merge/`+`lanes/`+`core/worktree_topology.py`+`runtime/next/`, the runtime/next read-site floor is present, and the 3 `get_mission_type(feature_dir)` reads in `runtime_bridge.py` each carry a route-or-pin disposition.
- **Owned files**: `tests/architectural/test_coord_read_residuals_closeout.py`
- **Dependencies**: WP01
- **Subtasks**: T006, T007, T008, T009, T010
- **Estimated size**: ~5 subtasks, ~340 lines

## WP03 — #2197 `spec-kitty next` claimable-preview routing (caller-only)

- **Goal**: Re-point the out-of-loop `_build_finalized_override_query_decision` preview read onto the kind-aware PRIMARY/STATUS leg-split so a coord-topology mission previews from the authoritative PRIMARY surface (not the STATUS-only coord husk), mirroring the reference impl `_preview_claimable_wp_for_mission`. The single sanctioned production routing edit (C-003).
- **Priority**: P2 (depends on the hardened arm + census being in place).
- **Requirements**: FR-004; NFR-003; C-001, C-002, C-003; SC-002.
- **Independent test**: `PWHEADLESS=1 pytest tests/integration/test_next_preview_primary_routing.py -q` — the behavioral revert-fails test asserts `preview.wp_id` is the PRIMARY-surface WP; reverting the routing yields a wrong/empty `wp_id` → RED.
- **Owned files**: `src/runtime/next/runtime_bridge.py`, `tests/integration/test_next_preview_primary_routing.py`
- **Dependencies**: WP02
- **Subtasks**: T011, T012, T013
- **Estimated size**: ~3 subtasks, ~240 lines

## WP04 — Partition-stability rationale map + husk no-op (parallel)

- **Goal**: Make re-homing an artifact kind across the PRIMARY/STATUS partition a conscious CI-red decision via a net-new machine-read per-kind rationale map cross-checked against the live frozensets, and cover `check_pre30_layout` as a clean no-op against a production-shaped STATUS-only husk and a `tasks/`-present-non-legacy variant.
- **Priority**: P2 (independent, fully parallel with WP01–WP03).
- **Requirements**: FR-006, FR-007; NFR-001, NFR-002, NFR-005; C-004; SC-003, SC-004.
- **Independent test**: `PWHEADLESS=1 pytest tests/architectural/test_write_surface_placement_guard.py tests/integration/test_pre30_layout_coord_husk_noop.py -q` — the rationale map is exhaustive, its split equals the live frozensets, the all-load-bearing-kinds anti-mutant fires on re-home, and `check_pre30_layout` is a verified no-op against both husk shapes.
- **Owned files**: `tests/architectural/test_write_surface_placement_guard.py`, `tests/integration/coord_topology_fixture.py`, `tests/integration/test_pre30_layout_coord_husk_noop.py`
- **Dependencies**: none (parallel)
- **Subtasks**: T014, T015, T016, T017
- **Estimated size**: ~4 subtasks, ~300 lines

---

## Cross-cutting acceptance (all WPs)

- **NFR-001 (CT7)**: zero new `file.py:NNN` ratchet anchors — content-anchor every new/extended gate via `tests/architectural/_ratchet_keys.composite_key`. Grep-verify: no new `file.py:NNN` keys.
- **NFR-002**: every new/extended gate ships a self-mutation test (synthetic offender → RED, revert → GREEN) + an anti-vacuity floor.
- **NFR-003 (gate-unmask-cannot-self-validate)**: the FR-005 scan-scope un-mask (WP02) MUST be paired with a **verbatim full-`tests/architectural/` dry-run recorded in the PR body** — see [[feedback_gate_unmask_cannot_self_validate]].
- **NFR-004**: full `tests/architectural/` green on the current tree with zero false positives; the census enumerates every in-scope param/attribute read site with a route-or-pin disposition.
- **NFR-005**: net test-suite-friction non-positive — no new allowlist/manual-denylist maintenance surface beyond the reused auto-discovery pattern; FR-006 adds no line-pins.
