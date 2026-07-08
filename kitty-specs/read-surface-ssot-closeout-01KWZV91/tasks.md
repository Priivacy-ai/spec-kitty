# Tasks: Read-Surface SSOT Completion & #1716 Closeout

**Mission**: `read-surface-ssot-closeout-01KWZV91`
**Branch**: `design/read-surface-ssot-closeout` (planning + merge target)
**Base**: rebased onto merged `upstream/main` (#2462 landed, 38257f737)
**WP count**: 17 · **Threads**: C (seam foundation) · A (feature_dir reads) · B (meta reads) · D (closeout)

> **Decomposition guardrails (binding).**
> - **Cross-thread linearization:** the 8 A∩B collision files each co-own their A-edit + B-edit in ONE WP
>   (WP05/06/07) — never split across lanes. Verified 8 collisions: `_identity_audit.py`, `implement.py`,
>   `context/resolver.py`, `decisions/service.py`, `doctrine_synthesizer/apply.py`, `lanes/recovery.py`,
>   `plan_interview.py`, `specify_interview.py`. `orchestrator_api/commands.py` is FR-004-only (WP10), NOT a collision.
> - **C-006 at the seam:** WP01 makes `commit_for_mission` per-file partition-aware — fixes `spec_commit_cmd.py` +
>   `mission_finalize.py` BY CONSTRUCTION (no per-caller patch). Red-first.
> - **FR-003 precedes FR-002:** WP11 does predicate-widen (recovery.py:755 + agent_tasks_ports.py:322 → by-design
>   writes, never routed) BEFORE the coord_authority floor 7→2 re-pin (predicate change moves the live write count).
> - **NFR-001 (post-#2462):** routing resolves the **kind-correct** surface. For PRIMARY-kind reads under coord
>   topology the seam legitimately moves coord→primary (that IS the #2453 fix). Characterization tests assert the
>   post-fix surface; NEVER pin the old kind-blind coord dir (Directive-041). Carry a coord-topology divergence regression.
> - **C-002:** no kind→partition change anywhere. **C-004:** `transaction.py:751-771` byte-unchanged.
> - **Every WP** appends to `traces/{design-decisions,approach,tooling-friction}.md` when relevant.
> - Implementers **sonnet**, reviewers **opus**.

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|----|----------|
| T001 | Red-first: mixed-partition batch misroutes; None-file batch still lands | WP01 | |
| T002 | Per-file partition classify + group in `commit_for_mission` | WP01 | |
| T003 | None-classified files keep caller-`kind` fallback; single-partition fast path | WP01 | |
| T004 | Per-group commit via existing materialize-then-retry; INV-C1 test | WP01 | |
| T005 | ruff/mypy/complexity ≤15; tracer append | WP01 | |
| T006 | Red-first: accept residual commit misroutes coord artifact to primary | WP02 | |
| T007 | Route `_commit_residual_acceptance_artifacts` through partition-aware seam | WP02 | |
| T008 | Reconcile dirty-detection: scan coord worktree where matrix is written (M2) | WP02 | |
| T009 | FR-008 regression + ruff/mypy; tracer append | WP02 | |
| T010 | Build coord-topology fixture ON #2462 golden-path + lane_test_utils | WP03 | |
| T011 | Assert matrix via spec-commit lands coord + read back | WP03 | |
| T012 | Assert matrix via finalize lands coord + read back | WP03 | |
| T013 | Assert matrix via accept-residual lands coord + read back (SC-003) | WP03 | |
| T014 | Campsite: delete redundant return @1281 (S3626) | WP04 | |
| T015 | Campsite: extract `_render_isolation_banner` (S1192) + test | WP04 | |
| T016 | Campsite: extract `_render_wp_prompt_wrapper` + test | WP04 | |
| T017 | Route ALL 3 workflow.py reads (@1468 + @1663 implement, @2710 review) → `read_dir(kind)` | WP04 | |
| T018 | Route workflow.py @2747 write → `write_target(kind)` (genuine write; do NOT dedupe with reads) | WP04 | |
| T019 | Collision c1: route implement.py A-read + B-meta (co-owned) | WP05 | [P] |
| T020 | Collision c1: route _identity_audit.py A-reads + B-meta (co-owned) | WP05 | [P] |
| T021 | Collision c1: FR-005 per-site allow_missing (post-#2091); tracer | WP05 | [P] |
| T022 | Collision c2: route context/resolver.py A-read + B-meta | WP06 | [P] |
| T023 | Collision c2: route decisions/service.py A-reads + B-meta | WP06 | [P] |
| T024 | Collision c3: route doctrine_synthesizer/apply.py A-reads + B-meta | WP07 | [P] |
| T025 | Collision c3: lanes/recovery.py — route B-meta @245; @755 by-design write, NEVER route | WP07 | [P] |
| T026 | Collision c3: route plan_interview.py + specify_interview.py A-read + B-meta | WP07 | [P] |
| T027 | Route A-only agent/* cmd cluster (tasks/tasks_finalize/tasks_dependency_graph) | WP08 | [P] |
| T028 | Route A-only agent_utils/status.py; agent_tasks_ports.py @322 never-route note | WP08 | [P] |
| T029 | Route A-only cli/commands (decision, mission_type, next_cmd) | WP09 | [P] |
| T030 | Route A-only + 4 slug sites (materialize, research, validate_encoding, workspace/context) | WP09 | [P] |
| T031 | Route A-only acceptance/__init__.py, manifest.py, verify_enhanced.py | WP09 | [P] |
| T032 | Red-first: FR-004 fail-closed at orchestrator_api/commands.py | WP10 | [P] |
| T033 | Replace `CommitTarget(ref=current_branch)` fallback with structured raise | WP10 | [P] |
| T034 | FR-003: predicate-widen recovery.py:755 + agent_tasks_ports.py:322 as by-design writes | WP11 | |
| T035 | FR-002: coord_authority floor 7→2 + margin + allow-list; freshen stale locators (2670→2747) | WP11 | |
| T036 | NFR-002 non-vacuity: re-introduced raw read goes RED | WP11 | |
| T037 | Route B-only status/* + merge/* + sync/emitter meta reads | WP12 | [P] |
| T038 | FR-005 per-site post-#2091 contract for WP12 sites; tracer | WP12 | [P] |
| T039 | Route B-only retrospective/* + post_merge + runtime/next (boundary-gated) + charter/* | WP13 | [P] |
| T040 | runtime/next shared-package-boundary adjudication (route only where sanctioned) | WP13 | [P] |
| T041 | Route B-only cli/commands + context/core/missions cluster | WP14 | [P] |
| T042 | transaction.py: route reads OUTSIDE 751-771; byte-unchanged guard on the block (C-004) | WP14 | [P] |
| T043 | Route B-only migration/{backfill_identity,backfill_topology,mission_state,rebuild_state} + audit + acceptance/matrix | WP15 | [P] |
| T044 | Defer m_0_13_* as allow-list entries (rationale + filed issue), NOT path-exclude | WP15 | [P] |
| T045 | Meta-read scanner (AST/heuristic) over src/ excluding mission_metadata + task_utils | WP16 | |
| T046 | Gate: integer floor + margin + routed-count floor + composite-key allow-list w/ stale-entry detection | WP16 | |
| T047 | 3 self-tests: plant→RED, stale-entry twin-guard, mass-allowlist→RED | WP16 | |
| T048 | Verify 69dd1fa46 on base; close #2088 early | WP17 | |
| T049 | Close #2100; enumerate #1716 open children; close epic #1716 (post-#2462) | WP17 | |
| T050 | issue-matrix verdicts terminal; SC-004 confirmation | WP17 | |

---

## Thread C — Seam foundation

### WP01 — Partition-aware `commit_for_mission` seam (IC-01 / FR-007)
**Priority**: P0 (foundation). **Independent test**: red-first mixed batch lands each file on its partition; None-file batch still lands. **Deps**: none.
- [x] T001 Red-first: mixed-partition batch misroutes; None-file batch still lands (WP01)
- [x] T002 Per-file partition classify + group in `commit_for_mission` (WP01)
- [x] T003 None-classified files keep caller-`kind` fallback; single-partition fast path (WP01)
- [x] T004 Per-group commit via existing materialize-then-retry; INV-C1 test (WP01)
- [x] T005 ruff/mypy/complexity ≤15; tracer append (WP01)
**Sketch**: `commit_router.py:152` — replace single `resolve_placement_only(kind=kind)` with per-file `kind_for_mission_file` → group by `is_primary_artifact_kind` → commit each group to its ref. `None`→caller-`kind` fallback; single-partition fast path unchanged. C-006/C-002. ~300 lines.

### WP02 — Accept residual routing + M2 dirty-surface (IC-02 / FR-008)
**Priority**: P0. **Independent test**: accept-residual matrix lands coord; dirty-detection sees coord-worktree edit. **Deps**: WP01.
- [x] T006 Red-first: accept residual commit misroutes coord artifact to primary (WP02)
- [x] T007 Route `_commit_residual_acceptance_artifacts` through partition-aware seam (WP02)
- [x] T008 Reconcile dirty-detection: scan coord worktree where matrix is written (M2) (WP02)
- [x] T009 FR-008 regression + ruff/mypy; tracer append (WP02)
**Sketch**: `accept.py` — replace raw `run_git(["commit",...])` (@~105) with `commit_for_mission`; `_spec_artifact_dirty_paths` (@~46) must detect coord-worktree dirt (where `write_acceptance_matrix` writes), not only primary `git_status_lines`. ~250 lines.

### WP03 — #2404 coord-topology characterization (IC-03 / FR-009 / SC-003)
**Priority**: P0. **Independent test**: matrix via all 3 paths lands coord + read back. **Deps**: WP01, WP02.
- [x] T010 Build coord-topology fixture ON #2462 golden-path + lane_test_utils (WP03)
- [x] T011 Assert matrix via spec-commit lands coord + read back (WP03)
- [x] T012 Assert matrix via finalize lands coord + read back (WP03)
- [x] T013 Assert matrix via accept-residual lands coord + read back (SC-003) (WP03)
**Sketch**: new `tests/integration/test_accept_matrix_coord_partition.py`; reuse `test_placement_partition_golden_path.py` scaffolding + `lane_test_utils` minted mid8. ~220 lines.

---

## Thread A — feature_dir read routing (#2453)

### WP04 — workflow.py campsite-first + route (IC-04 / FR-001 / FR-002)
**Priority**: P1. **Independent test**: SAFE extractions behave identically; @2710 reads via read_dir, @2747 writes via write_target. **Deps**: none.
- [x] T014 Campsite: delete redundant return @1281 (S3626) (WP04)
- [x] T015 Campsite: extract `_render_isolation_banner` (S1192) + test (WP04)
- [x] T016 Campsite: extract `_render_wp_prompt_wrapper` + test (WP04)
- [x] T017 Route ALL 3 workflow.py reads (@1468 + @1663 implement, @2710 review) → `read_dir(kind)` (WP04)
- [x] T018 Route workflow.py @2747 write → `write_target(kind)` — do NOT dedupe with reads (WP04)
**Sketch**: DIRECTIVE_025 tidy-first — SAFE campsite (T014-16, tested) BEFORE routing (T017-18). workflow.py has 4 coord_authority sites (3 reads @1468/@1663/@2710 + 1 write @2747) — ALL routed here or WP11 can't drain to floor 2. The reads and @2747 write DIVERGE — keep distinct. ~290 lines.

### WP05 — Collision cluster 1: implement.py + _identity_audit.py (A+B co-owned)
**Priority**: P1. **Deps**: none.
- [x] T019 Collision c1: route implement.py A-read + B-meta (co-owned) (WP05)
- [x] T020 Collision c1: route _identity_audit.py A-reads + B-meta (co-owned) (WP05)
- [x] T021 Collision c1: FR-005 per-site allow_missing (post-#2091); tracer (WP05)
**Sketch**: co-own both files' A (`resolve_feature_dir_for_mission`→`read_dir`) + B (`json.loads(meta)`→`load_meta*`) edits in one WP (linearization). ~230 lines.

### WP06 — Collision cluster 2: context/resolver.py + decisions/service.py (A+B co-owned)
**Priority**: P1. **Deps**: none.
- [x] T022 Collision c2: route context/resolver.py A-read + B-meta (WP06)
- [x] T023 Collision c2: route decisions/service.py A-reads + B-meta (WP06)
**Sketch**: co-own A+B for both. resolver.py is itself a read authority — route its own kind-blind reads carefully (NFR-001 kind-correct surface). ~200 lines.

### WP07 — Collision cluster 3: doctrine/apply + recovery + interviews (A+B co-owned)
**Priority**: P1. **Deps**: none.
- [x] T024 Collision c3: route doctrine_synthesizer/apply.py A-reads + B-meta (WP07)
- [x] T025 Collision c3: lanes/recovery.py — route B-meta @245; @755 by-design write, NEVER route (WP07)
- [x] T026 Collision c3: route plan_interview.py + specify_interview.py A-read + B-meta (WP07)
**Sketch**: recovery.py is triple-loaded — route ONLY the B-meta @245; @755 carries "MUST stay coord-aware — never route" (feeds `emit_status_transition_transactional`); FR-003 reclassifies it in WP11's gate. ~250 lines.

### WP08 — A-only routing cluster 1: agent/* commands + status (FR-001)
**Priority**: P1. **Deps**: none.
- [x] T027 Route A-only agent/* cmd cluster (tasks/tasks_finalize/tasks_dependency_graph) (WP08)
- [x] T028 Route A-only agent_utils/status.py; agent_tasks_ports.py @322 never-route note (WP08)
**Sketch**: `read_dir(kind)` per-kind. agent_tasks_ports.py @322 (`feature_write_dir`) is a by-design write (FR-003) — do NOT route; owned here only to keep the never-route note co-located. ~180 lines.

### WP09 — A-only routing cluster 2: cli/commands + slug sites + misc (FR-001)
**Priority**: P1. **Deps**: none.
- [x] T029 Route A-only cli/commands (decision, mission_type, next_cmd) (WP09)
- [x] T030 Route A-only + 4 slug sites (materialize, research, validate_encoding, workspace/context) (WP09)
- [x] T031 Route A-only acceptance/__init__.py, manifest.py, verify_enhanced.py (WP09)
**Sketch**: the 4 `resolve_feature_dir_for_slug` sites route onto `read_dir(kind)` per-kind. acceptance/__init__.py file-granular (NOT dir-level — package 3-way). ~200 lines.

### WP10 — FR-004 fail-closed fix (orchestrator_api/commands.py)
**Priority**: P1. **Independent test**: `ActionContextError` raises structured error, never `CommitTarget(ref=current_branch)`. **Deps**: none.
- [x] T032 Red-first: FR-004 fail-closed at orchestrator_api/commands.py (WP10)
- [x] T033 Replace `CommitTarget(ref=current_branch)` fallback with structured raise (WP10)
**Sketch**: FR-004-only file (NOT a B collision — its `json.loads` is `--evidence-json`). Red-first per C-005. ~150 lines.

### WP11 — coord_authority drain: FR-003 → FR-002 (NFR-002)
**Priority**: P1 (join). **Independent test**: floor at 2; re-introduced raw read goes RED. **Deps**: WP04, WP05, WP06, WP07, WP08, WP09, WP10.
- [x] T034 FR-003: predicate-widen recovery.py:755 + agent_tasks_ports.py:322 as by-design writes (WP11)
- [x] T035 FR-002: coord_authority floor 7→2 + margin + allow-list; freshen stale locators (2670→2747) (WP11)
- [x] T036 NFR-002 non-vacuity: re-introduced raw read goes RED (WP11)
**Sketch**: `test_resolution_authority_gates.py` + `resolution_gate_allowlist.yaml`. **T034 BEFORE T035** (predicate moves the live write count). 2 permanent keepers: `decisions/emit.py:71`, `widen/state.py:63`. ~200 lines.

---

## Thread B — inline meta.json read routing (#2100)

### WP12 — B-only: status/* + merge/* + sync (FR-005)
**Priority**: P2. **Deps**: none.
- [x] T037 Route B-only status/* + merge/* + sync/emitter meta reads (WP12)
- [x] T038 FR-005 per-site post-#2091 contract for WP12 sites; tracer (WP12)
**Sketch**: `load_meta`/`load_meta_strict`/`load_meta_or_empty` per site's POST-#2091 contract (hard-fail sites → strict, never `allow_missing=True` that masks the guard). ~200 lines.

### WP13 — B-only: retrospective + post_merge + runtime/next + charter (FR-005)
**Priority**: P2. **Deps**: none.
- [x] T039 Route B-only retrospective/* + post_merge + runtime/next (boundary-gated) + charter/* (WP13)
- [x] T040 runtime/next shared-package-boundary adjudication (route only where sanctioned) (WP13)
**Sketch**: `runtime/next/*` respects the shared-package boundary — route onto `specify_cli.mission_metadata.load_meta` only where a `specify_cli` import is already sanctioned; else defer with allow-list entry. ~230 lines.

### WP14 — B-only: cli/commands + context/core/missions + transaction.py (FR-005 / C-004)
**Priority**: P2. **Deps**: none.
- [x] T041 Route B-only cli/commands + context/core/missions cluster (WP14)
- [x] T042 transaction.py: route reads OUTSIDE 751-771; byte-unchanged guard on the block (C-004) (WP14)
**Sketch**: transaction.py is half-in/half-out — route its OTHER meta reads; the 751-771 legacy HEAD override stays byte-unchanged (C-004) + a regression asserting it. ~240 lines.

### WP15 — B-only: migration + audit + matrix (FR-005) + m_0_13_* deferral
**Priority**: P2. **Deps**: none.
- [x] T043 Route B-only migration/{backfill_identity,backfill_topology,mission_state,rebuild_state} + audit + acceptance/matrix (WP15)
- [x] T044 Defer m_0_13_* as allow-list entries (rationale + filed issue), NOT path-exclude (WP15)
**Sketch**: `migration/backfill_*` + `mission_state` + `rebuild_state` are #2100-in-scope (route them). ONLY `m_0_13_*` deferred, per-entry allow-list with a filed issue — no wholesale `migration/` exclude. ~210 lines.

### WP16 — Non-vacuous meta-read ratchet (IC-06 / FR-006 / NFR-002)
**Priority**: P2 (join). **Independent test**: plant a raw read → RED; mass-allowlist → RED; stale entry → RED. **Deps**: WP05, WP06, WP07, WP12, WP13, WP14, WP15.
- [x] T045 Meta-read scanner (AST/heuristic) over src/ excluding mission_metadata + task_utils (WP16)
- [x] T046 Gate: integer floor + margin + routed-count floor + composite-key allow-list w/ stale-entry detection (WP16)
- [x] T047 3 self-tests: plant→RED, stale-entry twin-guard, mass-allowlist→RED (WP16)
**Sketch**: new `tests/architectural/test_inline_meta_read_gate.py` + `inline_meta_read_allowlist.yaml`, modeled on `test_resolution_authority_gates.py`. All 4 mechanics required (contract). ~300 lines.

---

## Thread D — closeout

### WP17 — #2088 / #2100 / #1716 closeout (IC-07 / FR-010 / SC-004)
**Priority**: P3 (last). **Independent test**: issue-matrix verdicts all terminal; #1716 children enumerated + closed. **Deps**: WP03, WP11, WP16.
- [ ] T048 Verify 69dd1fa46 on base; close #2088 early (WP17)
- [ ] T049 Close #2100; enumerate #1716 open children; close epic #1716 (post-#2462) (WP17)
- [ ] T050 issue-matrix verdicts terminal; SC-004 confirmation (WP17)
**Sketch**: tracker/issue-matrix (planning artifact). #2088 verify-only (already fixed 69dd1fa46). #1716 epic-close gated on #2462-merged (GREEN) + children-enumeration ({2088, 2100}). Closing-keyword discipline. ~150 lines.

---

## Dependency graph

```
WP01 → WP02 → WP03 ─────────────────────────┐
WP04 ─┐                                       │
WP05 ─┤ (also → WP16)                         │
WP06 ─┤ (also → WP16)                         │
WP07 ─┤ (also → WP16)                         │
WP08 ─┼→ WP11 ───────────────────────────────┤
WP09 ─┤                                       ├→ WP17
WP10 ─┘                                       │
WP12 ─┐                                       │
WP13 ─┤                                       │
WP14 ─┼→ WP16 ───────────────────────────────┘
WP15 ─┘
```

**MVP / first WP**: WP01 (the seam foundation — everything Thread-C routes through).
**Parallelizable at start**: WP01, WP04, WP05, WP06, WP07, WP08, WP09, WP10, WP12, WP13, WP14, WP15 (12 WPs, disjoint ownership).
**Join points**: WP11 (all Thread A), WP16 (all Thread B incl. collision B-edits), WP17 (all threads).
