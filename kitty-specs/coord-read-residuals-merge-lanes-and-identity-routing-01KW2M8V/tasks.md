---
description: "Work package task list — coord-read-residuals merge/lanes + identity routing (#2185 + #2186 + #2187)"
---

# Work Packages: Coord-Read Residuals — Merge/Lanes + Identity Routing

**Mission**: `coord-read-residuals-merge-lanes-and-identity-routing-01KW2M8V`
**Branch**: `mission/coord-read-residuals-2185-2186` | **Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md) | **Research**: [research.md](./research.md)

Routes the PRIMARY-partition reads that still resolve through coord-aware resolvers (landing on the empty `-coord` status husk post-#2106) onto the existing read-path seam. **Lane A (#2185 + #2187)** = `merge/`/`lanes/`/`core/worktree_topology`/`agent_utils/status.py` reads of `lanes.json`/`tasks/`/`meta.json`. **Lane B (#2186)** = command-layer identity/type reads + a net-new call-shape scan arm covering the two shapes the ratchet's literal vocabulary cannot see.

**Tests**: required (NFR-004 integration-over-stubs; gate self-tests; RED-first per-site + integration proof).

## ⚠️ C-SEQ landing precondition (read before implementing Lane A)

This mission **lands after** the implement-loop sibling (`implement-loop-coord-authority-completion-01KW2E7A`). Before implementing Lane A (WP02/WP03):

1. **Rebase** this branch onto post-implement-loop-merge `main`.
2. **Re-resolve every line citation** below against the merged tree. Lane A files (`merge/`, `lanes/`, `core/worktree_topology.py`, `agent_utils/status.py`) are C-009-protected so their lines are stable; the Lane B citations (`next_cmd.py`, `implement.py`, `agent/workflow.py`) sit inside functions the sibling rewrites and **must be re-confirmed** (verified on merged `main` at planning time: `next_cmd.py` `get_mission_type` `:631`→`:619`; `implement.py` `:1389`→`:1394`; `workflow.py` `:1274`→`:1282`, `:1636`→`:1644`, `:2732`→`:2739`).
3. **FR-011 preflight** (T010, narrowed): assert the single **#2187** pin (`agent_utils/status.py::show_kanban_status`) is present in `_DIR_READ_KNOWN_RESIDUALS` on the rebased base before WP03/T021 drains it. **The merge/lanes/core #2185 cluster has ZERO pins and none can be added** — the ratchet vocabulary (`tasks`/`.md` literals) is structurally blind to `lanes.json` (LANE_STATE) and to `meta.json` function-call reads. Their absence is the EXPECTED permanent state, NOT a landing-timing signal — **never STOP on it**. The #2185 regression backstop is the FR-009 divergent-fixture revert-fails test (WP04) plus the FR-007 lanes.json call-shape arm (WP01).

Lane B (WP01) is otherwise **self-contained** (its call-shape arm is net-new, not inherited from the sibling) and is not blocked except for the citation re-resolution above.

## Ownership / lane note (disjoint owned_files)

`owned_files` are **strictly disjoint** across WPs (no file is owned by two WPs):

- **WP01** owns the gate/ratchet test files (`tests/architectural/test_gate_read_literal_ban.py` — the dir-read ratchet + the new call-shape arm; `tests/architectural/test_resolution_authority_gates.py` — the canonicalizer floor), the **shared divergent fixture** (`tests/integration/coord_topology_fixture.py`, T001 — owned here as the FOUNDATIONAL deliverable so every consumer shares ONE divergence definition), and the **Lane B identity src** (`next_cmd.py`, `implement.py`, `agent/workflow.py` owned legs) + its RED-first identity test.
- **WP02** owns the `merge/` cluster (`forecast.py`, `executor.py`, `resolve.py`, `done_bookkeeping.py`) + `cli/commands/merge.py` + its RED-first merge test.
- **WP03** owns the `lanes/` cluster (`merge.py`, `recovery.py`, `worktree_allocator.py`), `core/worktree_topology.py`, and **`agent_utils/status.py`** (both legs of `show_kanban_status`: the #2187 `:126` `tasks/` drain AND the #2186 `:132` identity route) + its RED-first lanes/core test + recovery-helper tests.
- **WP04** owns the integration proof test.
- **WP05** owns the close-out artifacts (`issue-matrix.md`, `traces/`).

> **Decision (Directive 003) — `agent_utils/status.py` single-file ownership.** The Surface Inventory places the #2187 `:126` `tasks/` drain and the #2186 `:132` identity read in the SAME function `show_kanban_status`. The #2187 drain must follow WP02's FR-011 pin-present preflight, so it lands in WP03. To honor "no overlapping owned_files / disjoint module sets", **`agent_utils/status.py` is owned wholly by WP03**, which routes **both** legs (T021). WP01's FR-007 identity arm scope still includes `agent_utils/status.py`, so the `:132` leg is **statically gated** by the arm even though WP01 does not edit the file; WP01 routes the other five Lane B identity sites (`next_cmd.py`, `implement.py`, `workflow.py`). This is the only deviation from a literal site→WP reading and exists solely to keep ownership disjoint.

**C-009-mirror:** never edit the implement-loop ROUTE surface (`cli/commands/agent/tasks.py`, the `workflow.py` route legs, `tasks_dependency_graph.py`, `workspace/context.py`, …) or the `scripts/tasks/` legacy reader (#2167). Lane B touches only the **owned identity legs** in `workflow.py`/`implement.py`. Never edit `_read_path_resolver` internals (C-002) and never remove `candidate_feature_dir_for_mission` (C-005 STATUS primitive).

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|----|----------|
| T001 | **(FOUNDATIONAL)** Extend `tests/integration/coord_topology_fixture.py` with the **sentinel-husk-meta variant** (reuse merged divergent husk; husk `meta.json` present-but-wrong `mission_id=6KERGF2ZNFBPR91YEZMARG99KS` ≠ PRIMARY `01KW2E7AFC0000000000000001`; `lanes.json`+`tasks/` PRIMARY-only). Divergence is a HARD precondition (the triad), defined in ONE place — shared by T009/T016/T022/T023 | WP01 | |
| T002 | Build the **call-shape scan arm** covering BOTH shapes — identity (`resolve_mission_identity`/`get_mission_type`, scope `cli/commands/` **+ `agent_utils/status.py`**) AND lanes.json (`read_lanes_json`/`require_lanes_json`, scope `merge/`+`lanes/`+`core/worktree_topology.py`) — whose dir arg is coord-aware-resolved without a primary fold | WP01 | | [D] |
| T003 | Mandatory synthetic-AST non-vacuity self-test for **both** shapes (pre-fix snippet flagged; routed snippet not) | WP01 | [D] |
| T004 | Emit the complete per-site ROUTE/KEEP/owned-by-implement-loop table (cross-check vs sibling ROUTE+KEEP; re-resolve citations on merged main); no Lane B site left in the gap | WP01 | | [D] |
| T005 | Route `next_cmd.py:187/:253` — primary-anchor the `resolve_mission_identity` reads (lifecycle records no longer silently swallowed) | WP01 | | [D] |
| T006 | Route `next_cmd.py:619` (was `:631`) — `get_mission_type` primary fold (fixes wrong-run-type routing in `get_or_start_run`) | WP01 | | [D] |
| T007 | Route `implement.py:1394` (own primary anchor, survives `:1018` fallback removal) + owned `workflow.py` identity legs (`:1282` clean / `:1644` own-anchor shared-var / `:2739` clean) — citations re-resolved on merged main | WP01 | | [D] |
| T008 | Recompute `ROUTED_CANONICALIZER_FLOOR` from the before/after census + explicit list of new DIRECT-primitive call sites; if seam-routing did not move the census, record that plainly (no re-pinned-integer "gain") | WP01 | | [D] |
| T009 | RED-first per-site identity tests on the divergent fixture (T001) — each routed site returns the PRIMARY id/type on a **returned domain value**, not the sentinel/default; revert → fail | WP01 | | [D] |
| T010 | FR-011 preflight (assert the single **#2187** pin present) + FR-006 honest-scope note (vocabulary blind to lanes.json/meta.json; **absence of merge/lanes/core pins is EXPECTED, never a STOP**) | WP02 | |
| T011 | Route `merge/forecast.py:153` (lanes, LANE_STATE) + `:159` (review-artifact preflight, WORK_PACKAGE_TASK) | WP02 | | [D] |
| T012 | Route `merge/executor.py` `:976` legs **DIRECTLY, per-leg** (`:981`/`:1003`→META, `:997`→LANE_STATE) — NOT thread `:887` (different function `_run_lane_based_merge` def `:947` vs `_run_lane_based_merge_locked` def `:866`); keep `run.feature_dir` STATUS leg coord-aware | WP02 | | [D] |
| T013 | Route `merge/resolve.py:98` (meta, PRIMARY_METADATA); leave `:63` (handle→name canonicalization at the no-silent-fallback boundary) on `candidate_` | WP02 | | [D] |
| T014 | Route `merge/done_bookkeeping.py:237` WP-path leg (`kind=WORK_PACKAGE_TASK`); **remove the misleading "do not use the read-path resolver" comment**; keep status-transactional legs on the meta-bearing primary dir | WP02 | | [D] |
| T015 | Route `cli/commands/merge.py:269` (meta, PRIMARY_METADATA; verify `--abort` coord-teardown semantics first) | WP02 | | [D] |
| T016 | RED-first per-site merge tests (both legs) on the divergent fixture (T001); revert-fails on a **returned domain value** (NFR-004 integration-over-stubs) | WP02 | | [D] |
| T017 | Route `lanes/merge.py:68/:198` (lanes, LANE_STATE) | WP03 | |
| T018 | Extract `scan_recovery_state` PRIMARY-planning + status-events helpers, **drop `# noqa: C901`**, route `:356` per-leg + `:611`; **KEEP `:664` coord-aware** (STATUS-write leg feeding `emit_status_transition_transactional` @ `:686`); focused helper tests | WP03 | | [D] |
| T019 | Route `lanes/worktree_allocator.py:360` (meta; `kind=PRIMARY_METADATA` topology-blind — correct for the chicken-and-egg coord discovery) | WP03 | | [D] |
| T020 | Route `core/worktree_topology.py:138` (single swap co-resolves the three PRIMARY legs `:139`/`:140`/`:141`) | WP03 | | [D] |
| T021 | **`agent_utils/status.py::show_kanban_status` — both legs.** (a) #2187 `:126` `tasks/` glob → `resolve_planning_read_dir(kind=WORK_PACKAGE_TASK)` and **drain the #2187 `_DIR_READ_KNOWN_RESIDUALS` pin** (the sole ratchet-visible Lane A drain); (b) #2186 `:132` `resolve_mission_identity` → `kind=PRIMARY_METADATA` (the identity class, statically gated by WP01's FR-007 arm). **Keep `:151` `read_events` STATUS leg coord-aware** (C-001) | WP03 | | [D] |
| T022 | RED-first per-site lanes/core tests (both legs) on the divergent fixture (T001); revert-fails on a **returned domain value**; `show_kanban_status` renders a non-empty board (unit stub handing in a primary dir does NOT satisfy — #2187 AC) | WP03 | | [D] |
| T023 | Coord-topology merge/recovery/topology integration test on T001 (drive real `_run_lane_based_merge` / `scan_recovery_state` / `materialize_worktree_topology`); PRIMARY reads return the seeded lanes/WPs on a **returned domain value**; reverting any routed read to coord-aware FAILS on the domain value | WP04 | |
| T024 | NFR-001 STATUS-from-husk assertions (events / `recovery.py:664` / `status_feature_dir` legs still read the coord husk) + explicit revert-fails guard (no STATUS leg silently re-routed to PRIMARY) | WP04 | | [D] |
| T025 | Flat-topology parity assertions (NFR-003) — routing is a no-op on flat topology; existing flat-topology merge/lanes/next tests stay green | WP04 | [D] |
| T026 | Pre-merge full-gate dry run (`tests/architectural/` green incl. the new arm both shapes; no un-pinned strangers; `ruff`+`mypy` clean) **+ demonstrate RED-on-revert** by actually running the WP04 integration test + the per-site tests | WP05 | |
| T027 | Confirm floor recompute consistency + zero STATUS legs re-routed (NFR-001 primary evidence = the WP04 STATUS-from-husk assertions; diff-grep is the secondary cross-check) | WP05 | [D] |
| T028 | Issue-matrix #2185/#2186/#2187 → terminal verdict (**#2185 cites WP04 behavioral revert-fails evidence**, not a pin drain; pins admissible only for #2187); append implement-phase entries to the three `traces/` files; validate the quickstart | WP05 | [D] |

---

## Work Package WP01: Lane B — Call-shape arm + identity routing + floor + shared fixture (Priority: P1) 🎯

**Goal**: Extend the divergent coord fixture (T001, FOUNDATIONAL), build the net-new **call-shape scan arm** covering BOTH the lanes.json shape and the identity shape (with self-tests), route the genuinely-owned #2186 identity sites onto PRIMARY (arm + remediation co-land), and recompute the canonicalizer floor honestly.
**Independent Test**: On the divergent fixture, `next_cmd` lifecycle records carry the PRIMARY `mission_id` and `get_mission_type` returns the PRIMARY type; the arm flags an injected unguarded read for **both** shapes and passes after routing.
**Prompt**: `/tasks/WP01-lane-b-arm-identity-floor-fixture.md`
**Requirement Refs**: FR-004, FR-005, FR-007, FR-009 (fixture extension), FR-010, NFR-002, C-003 | **Tracker Refs**: #2186

### Included Subtasks
- [x] T001 (FOUNDATIONAL fixture extension — first), T002, T003, T004, T005, T006, T007, T008, T009

### Dependencies
- None (self-contained; net-new arm + owns the shared fixture). Re-resolve `workflow.py`/`implement.py`/`next_cmd.py` citations after the C-SEQ rebase.

### Risks & Mitigations
- Gate-unmask-cannot-self-validate → arm + routing co-land in this WP, validated by the WP05 full-gate dry run. Identity-arm scope bounded to `cli/commands/` + `agent_utils/status.py`; lanes.json-arm scope bounded to `merge/`+`lanes/`+`core/worktree_topology.py` — avoid red-CI on out-of-scope strangers (sync/acceptance/policy).
- Fixture-divergence drift → the divergence definition lives in ONE place (T001); all consumers (T009/T016/T022/T023) import it.

---

## Work Package WP02: Lane A — Merge cluster routing (Priority: P1)

**Goal**: Route the `merge/` + `cli/commands/merge.py` PRIMARY reads by their real kind (per-leg split where mixed). **No merge-cluster pins exist to drain** (vocabulary-blind); coverage is the FR-007 lanes.json arm (WP01) + the FR-009 divergent fixture (WP04).
**Independent Test**: Merge/forecast on the divergent fixture (T001) reads lanes/meta/WP-tasks off PRIMARY; the status leg stays coord-aware; reverting any routed read fails the test on a returned domain value.
**Prompt**: `/tasks/WP02-lane-a-merge-cluster.md`
**Requirement Refs**: FR-001, FR-002, FR-003, FR-006, FR-008, FR-011, NFR-001 | **Tracker Refs**: #2185

### Included Subtasks
- [x] T010, T011, T012, T013, T014, T015, T016

### Dependencies
- Depends on WP01 (owns the gate file + the T001 shared fixture). C-SEQ rebase + T010 (#2187 pin-presence) preflight first.

### Risks & Mitigations
- Over-routing a STATUS leg (NFR-001) → per-leg split; keep `status_feature_dir`/status-transactional legs coord-aware/primary as appropriate. Don't reintroduce #2139's silent `main` target-branch fallback.

---

## Work Package WP03: Lane A — Lanes/core cluster + recovery extraction + #2187/#2186 status.py (Priority: P1)

**Goal**: Route the `lanes/` + `core/worktree_topology` PRIMARY reads; extract helpers out of the over-complex `scan_recovery_state` and drop its `# noqa: C901`; keep the `recovery.py:664` STATUS-write leg coord-aware; and route **both** legs of `agent_utils/status.py::show_kanban_status` — the #2187 `:126` `tasks/` drain (the sole ratchet-visible Lane A drain) and the #2186 `:132` identity read.
**Independent Test**: Recovery scan + topology materialization + `show_kanban_status` read lanes/tasks/meta off PRIMARY on the divergent fixture (T001); the events/status legs (incl. `:664`) stay coord-aware.
**Prompt**: `/tasks/WP03-lane-a-lanes-core-cluster.md`
**Requirement Refs**: FR-001, FR-002, FR-008, NFR-001 | **Tracker Refs**: #2185, #2186, #2187

### Included Subtasks
- [x] T017, T018, T019, T020, T021, T022

### Dependencies
- Depends on WP02 (sequential gate-file chain; transitively WP01) and WP01 (the T001 shared divergent fixture).

### Risks & Mitigations
- A per-leg split inside `scan_recovery_state` (already `# noqa: C901`) worsens complexity → extract named helpers + drop the noqa + add tests, don't add a branch. `worktree_allocator` chicken-and-egg → `kind=PRIMARY_METADATA` is topology-blind. Never route the `:664` STATUS-write leg (C-001/#2155 analog).

---

## Work Package WP04: Lane A — Coord-topology integration proof (Priority: P1)

**Goal**: Add the real `git worktree` coord-topology integration test (on the WP01/T001 divergent fixture) that proves the routed reads land on PRIMARY (returned domain value), the STATUS legs stay on the husk, and flat-topology routing is a no-op.
**Independent Test**: The integration test is green and fails (on a returned domain value) if any routed Lane A read is reverted to the coord-aware resolver; STATUS-from-husk assertions hold.
**Prompt**: `/tasks/WP04-lane-a-integration-proof.md`
**Requirement Refs**: FR-009, NFR-001, NFR-003, NFR-004, SC-001

### Included Subtasks
- [x] T023, T024, T025

### Dependencies
- Depends on WP01 (the T001 divergent fixture) + WP02 + WP03 (routed code under test).

### Risks & Mitigations
- Non-divergent husk = false-green (the squad's CRITICAL finding) → the HARD divergence assertions in WP01/T001 (husk lacks `lanes.json`/`tasks/`; husk meta `mission_id` = sentinel ≠ PRIMARY) are the guard; review them explicitly.

---

## Work Package WP05: Verify & close (Priority: P2)

**Goal**: Cross-cutting verification and mission close-out: full architectural gate green (incl. the new call-shape arm — both shapes), floor consistent with the recorded census, zero STATUS legs re-routed, and a terminal issue-matrix for #2185/#2186/#2187.
**Independent Test**: Full `tests/architectural/` green; floor consistent with census; no STATUS leg re-routed; issue-matrix terminal with #2185 backed by WP04 behavioral evidence.
**Prompt**: `/tasks/WP05-verify-and-close.md`
**Requirement Refs**: FR-010, NFR-001, NFR-003, C-SEQ

### Included Subtasks
- [x] T026, T027, T028

### Dependencies
- Depends on WP01, WP02, WP03, WP04.

### Risks & Mitigations
- Gate-added-in-mission can't catch offenders in its own merge → the pre-merge full-gate dry run (T026) is the backstop; it must demonstrate RED-on-revert, not just static green.

---

## Dependency & Execution Summary

- **Sequence**: WP01 → WP02 → WP03 → WP04 → WP05. WP01 linearizes the gate-file edits and delivers the T001 shared fixture consumed by WP02/WP03/WP04; WP02→WP03 chain the `merge/`→`lanes/`/`status.py` routing; WP04 needs the routed code; WP05 closes. The DAG is fully linearized (every pair is dependency-ordered), so the lane allocator runs them on one lane and `owned_files` are additionally disjoint by construction.
- **Parallelization**: WP01 is independent of the implement-loop landing (Lane B + arm + fixture); Lane A (WP02–WP04) waits on the C-SEQ rebase. T003/T025/T027/T028 are `[P]` within their WPs.
- **MVP Scope**: WP01 (Lane B identity fix + call-shape arm + shared divergent fixture) is independently shippable and not blocked on the sibling.

## Requirements Coverage Summary

| Requirement ID | Covered By Work Package(s) |
|----------------|----------------------------|
| FR-001 | WP02, WP03 |
| FR-002 | WP02, WP03 |
| FR-003 | WP02 |
| FR-004 | WP01 |
| FR-005 | WP01 |
| FR-006 | WP02 |
| FR-007 | WP01 |
| FR-008 | WP02 (honest-scope note), WP03 (#2187 sole drain); merge/lanes/core covered by FR-007 arm + FR-009 fixture |
| FR-009 | WP01 (T001 fixture), WP04 |
| FR-010 | WP01, WP05 |
| FR-011 | WP02 (T010 — #2187 pin only) |
| NFR-001 | WP02, WP03, WP04, WP05 |
| NFR-002 | WP01 |
| NFR-003 | WP04, WP05 |
| NFR-004 | WP04 |
| C-001 | WP02, WP03 |
| C-002 | WP01, WP02, WP03 |
| C-003 | WP01 |
| C-009-mirror | all |

## Subtask Index (Reference)

| Subtask ID | Summary | Work Package | Priority | Parallel? |
|------------|---------|--------------|----------|-----------|
| T001 | Shared divergent-fixture extension (sentinel husk meta) — FOUNDATIONAL | WP01 | P1 | No |
| T002 | Call-shape scan arm (lanes.json + identity, both scopes) | WP01 | P1 | No | [D] |
| T003 | Arm non-vacuity self-test (both shapes) | WP01 | P1 | Yes | [D] |
| T004 | ROUTE/KEEP ownership table | WP01 | P1 | No | [D] |
| T005 | Route next_cmd :187/:253 | WP01 | P1 | No | [D] |
| T006 | Route next_cmd :619 | WP01 | P1 | No | [D] |
| T007 | Route implement.py:1394 + owned workflow.py legs (:1282/:1644/:2739) | WP01 | P1 | No | [D] |
| T008 | Floor recompute (honest census) | WP01 | P1 | No | [D] |
| T009 | RED-first identity tests (returned domain value) | WP01 | P1 | No | [D] |
| T010 | FR-011 preflight (#2187 pin only) + FR-006 honest-scope note | WP02 | P1 | No |
| T011 | Route forecast :153/:159 | WP02 | P1 | No | [D] |
| T012 | Route executor :976 legs directly (NOT thread :887) | WP02 | P1 | No | [D] |
| T013 | Route resolve :98 | WP02 | P1 | No | [D] |
| T014 | Route done_bookkeeping :237 + remove comment | WP02 | P1 | No | [D] |
| T015 | Route merge.py :269 | WP02 | P1 | No | [D] |
| T016 | RED-first merge tests | WP02 | P1 | No | [D] |
| T017 | Route lanes/merge :68/:198 | WP03 | P1 | No |
| T018 | recovery extraction + route (KEEP :664 STATUS) | WP03 | P1 | No | [D] |
| T019 | Route worktree_allocator :360 | WP03 | P1 | No | [D] |
| T020 | Route worktree_topology :138 | WP03 | P1 | No | [D] |
| T021 | status.py show_kanban_status both legs (#2187 :126 drain + #2186 :132 identity) | WP03 | P1 | No | [D] |
| T022 | RED-first lanes/core tests | WP03 | P1 | No | [D] |
| T023 | Coord integration test (returned domain value) | WP04 | P1 | No |
| T024 | NFR-001 STATUS-from-husk + revert-fails guard | WP04 | P1 | No | [D] |
| T025 | Flat-topology parity | WP04 | P1 | Yes | [D] |
| T026 | Full-gate dry run + RED-on-revert | WP05 | P2 | No |
| T027 | Floor + NFR-001 confirm | WP05 | P2 | Yes | [D] |
| T028 | Issue-matrix terminal + traces | WP05 | P2 | Yes | [D] |
