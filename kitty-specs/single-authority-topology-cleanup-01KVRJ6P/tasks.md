# Tasks: Single-Authority Topology Cleanup & Dedup

**Mission**: `single-authority-topology-cleanup-01KVRJ6P` | **Branch**: `feat/single-authority-topology-cleanup`
**Planning base**: `feat/single-authority-topology-cleanup` | **Merge target**: `feat/single-authority-topology-cleanup` (→ `main` via PR at close)

18 work packages across 6 lanes. Behavior-neutral cleanup + dedup (PR #2086 SSOT
follow-on) with ONE correctness improvement (FR-004). Lane B is the entangled
`CommitTargetKind` core (the enum touches 17 files) — a **sequential same-lane
chain** sharing the topology files (allowed: same-lane sequential WPs may share
`owned_files`). Every WP carries the #1970 campsite directive.

> **Sizing re-slice (2026-06-23).** A 3-lens sizing squad (pedro context-fit /
> paula split-seams / randy effort+model) split the four largest/riskiest WPs for
> subagent context-window fit, keeping three coherence welds intact:
> WP03→{WP03,WP14,WP15} (15-file mechanical drop), WP04→{WP04,WP16} (enum delete ⊗
> absolute-mapping test stays in WP16), WP06→{WP06,WP17} (NFR-002-flip ⊗ absorption
> stay in WP06; corrupt-meta C-004 raise stays in WP17), WP10→{WP10,WP18}
> (silent-empty-dict sites in WP18). New WP IDs WP14–WP18 are appended; the
> execution order follows the dependency graph below, not the numeric ID order.

## Lanes & sequencing

| Lane | WPs (in dependency order) | Concern |
|------|---------------------------|---------|
| A | WP01 | IC-01 verification safety net (HARD BARRIER before deletions) |
| B | WP02 → WP03 → WP14 → WP15 → WP04 → WP16 → WP05 → WP06 → WP17 → WP07 | IC-02 topology/type anchor + IC-03 + FR-013 |
| C | WP08 → {WP09, WP10, WP18} | IC-04 C2 meta-reader unification |
| D | WP11 (after WP08) | IC-05 C6 task_helpers retirement |
| E | WP12 | IC-06 accept gates |
| F | WP13 | IC-07 merge residue-gate sweep (#1887) |

Dependency edges: WP01←(all deletion/absorption WPs gate on it). Lane B chain:
WP02←WP01; WP03←WP02; WP14←WP03; WP15←WP14; WP04←WP15; WP16←WP04; WP05←WP16;
WP06←WP05,WP01; WP17←WP06,WP08; WP07←WP17. Lane C: WP08←WP01; WP09←WP08;
WP10←WP08; WP18←WP08. WP11←WP08. WP12←WP01,WP04; WP13←WP01.

## Model tiers (sizing squad — randy effort + model discipline)

Dispatch each WP at the indicated tier (`--agent <tool>:<model>:python-pedro:implementer`).

| Tier | WPs | Rationale |
|------|-----|-----------|
| **STRONG** (opus) | WP01, WP02, WP04, WP16, WP05, WP06, WP17, WP07, WP08, WP12, WP13 | Analytical / risk-bearing: enum semantics, boundary absorption, residue authority, AST guards, the welds. |
| **MID** (sonnet) | WP09, WP10, WP18 | Mechanical-but-judged meta-reader contract matching (per-site missing/malformed). |
| **CHEAP** (sonnet/haiku) | WP03, WP14, WP15, WP11 | Repetitive mechanical `kind=PRIMARY` drops + a thin re-export; behavior-neutral, ratchet-pinned. |

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|----|----------|
| T001 | Extend differential gate with classify-on-read ≡ backfill-then-read cell (GREEN) | WP01 | |
| T002 | Add NFR-002 un-backfilled-flattened live repro (xfail(strict) RED-by-design) | WP01 | |
| T003 | Build non-fakeable AST guard for CommitTargetKind / FLATTENED.value reintroduction | WP01 | [P] |
| T004 | Planted-literal self-test proving the AST guard fails on a phantom | WP01 | [P] |
| T005 | Define ONE canonical `_COORD_ROUTING_TOPOLOGIES` frozenset + collapse the 4 verbatim defs | WP02 | |
| T006 | Collapse the 6 coord-routing predicates to ONE `routes_through_coordination` | WP02 | |
| T007 | Pin the C-002 relays + C-001 husk short-circuit unchanged (KEEP map) | WP02 | |
| T008 | Drop mechanical `kind=PRIMARY` args + imports — CLI agent surface (1/3) | WP03 | |
| T027 | Drop mechanical `kind=PRIMARY` args + imports — coordination/events/runtime (2/3) | WP14 | |
| T028 | Drop mechanical `kind=PRIMARY` args + imports — core/git/upgrade (3/3) | WP15 | |
| T009 | Convert the 3 `kind=COORDINATION` needs-care sites to the topology predicate | WP04 | |
| T010 | Preserve runtime_bridge parallel-classifier `worktree_root` selection (C-011) | WP04 | |
| T011 | Remove `.kind` from CommitTarget VO; delete the enum; rework the absolute-mapping cell | WP16 | |
| T012 | Delete `CommitTargetKind.FLATTENED` (AST-verified write-only dead; KEEP flattened meta-flag) | WP05 | |
| T013 | Remove dead `ensure_topology` persist shim; retarget its tests | WP05 | |
| T014 | Campsite: remove dead `safe_commit` re-export shim (mission.py:54-58) | WP05 | |
| T015 | Absorb `topology=None` at read-path boundary via `read_topology`/`classify_from_meta` | WP06 | |
| T017 | Flip the NFR-002 repro GREEN (welded to the absorption) | WP06 | |
| T016 | Collapse the ~8 `topology is None` husk-arms + the 6th predicate (KEEP corrupt-meta) | WP17 | |
| T029 | Convert the 4 topology files' load_meta calls; corrupt-meta C-004 cell | WP17 | |
| T018 | Make CommitResult JSON-serializable (serialize worktree_root); fix map-requirements --json | WP07 | |
| T019 | Build the polymorphic `load_meta(dir, *, allow_missing, on_malformed)` + 3-contract adapters | WP08 | |
| T020 | C2 sweep cluster 1: status / migration / coordination meta-readers → canonical | WP09 | [P] |
| T021 | C2 sweep cluster 2a: cli / dashboard / doc meta-readers → canonical | WP10 | [P] |
| T030 | C2 sweep cluster 2b: retrospective / review / tracker / upgrade / verify (silent-empty) | WP18 | [P] |
| T022 | Retire scripts/tasks/task_helpers.py to a thin re-export of task_utils/support.py | WP11 | [P] |
| T023 | FR-008 accept dirty-gate topology-aware (converge on mission.py:862 pattern) | WP12 | |
| T024 | FR-009 derive unchecked-tasks completion from WP terminal status | WP12 | |
| T025 | FR-012 merge advance_branch_ref callers + post-merge invariant → single residue authority | WP13 | |
| T026 | FR-012 converge auto_rebase.py:154 4th residue site onto canonical _COORD_RESIDUE_FILENAMES | WP13 | |

---

## WP01 — Verification safety net (Lane A) · STRONG
**Goal**: Land the differential cell + AST guard + RED repro that GATE every deletion/collapse downstream. **Priority**: P0 (hard barrier). **Independent test**: the new differential cell is GREEN; the AST guard fails on a planted phantom; the NFR-002 repro is RED-by-design (xfail strict).
**Requirements**: FR-010, FR-011, NFR-002, NFR-003.
- [x] T001 Extend differential gate with classify-on-read ≡ backfill-then-read cell (GREEN) (WP01)
- [x] T002 Add NFR-002 un-backfilled-flattened live repro (xfail strict, RED-by-design) (WP01)
- [x] T003 Build non-fakeable AST guard for CommitTargetKind / FLATTENED.value reintroduction (WP01)
- [x] T004 Planted-literal self-test proving the AST guard fails on a phantom (WP01)

**Prompt**: [tasks/WP01-verification-safety-net.md](tasks/WP01-verification-safety-net.md)
**Dependencies**: none. **Risks**: the differential cell may need FR-006/FR-004 to be fully green — scope it to assert the equivalence contract, not a not-yet-landed behavior.

## WP02 — Coord-routing predicate + frozenset consolidation (Lane B) · STRONG
**Goal**: FR-005 — collapse the 6 predicates + 4 verbatim frozensets to ONE predicate + ONE frozenset (Tidy-First). **Independent test**: 5 of the 6 call sites route through the single `routes_through_coordination`; the 4 frozenset defs become one import. (The 6th predicate lives in `_read_path_resolver.py` — collapsed in WP17.)
**Requirements**: FR-005, NFR-005 (KEEP map), C-002.
- [x] T005 Define ONE canonical `_COORD_ROUTING_TOPOLOGIES` frozenset + collapse the 4 verbatim defs (WP02)
- [x] T006 Collapse the 6 coord-routing predicates to ONE `routes_through_coordination` (WP02)
- [x] T007 Pin the C-002 relays + C-001 husk short-circuit unchanged (KEEP map) (WP02)

**Prompt**: [tasks/WP02-coord-routing-consolidation.md](tasks/WP02-coord-routing-consolidation.md)
**Dependencies**: WP01. **Risks**: do NOT collapse a C-002 relay (projection ≠ exception-arm fallback).

## WP03 — Mechanical `.kind` drop 1/3: CLI agent surface (Lane B) · CHEAP
**Goal**: FR-001a — drop the mechanical `kind=PRIMARY` args + CommitTargetKind imports across the **CLI agent-command** construction sites (5 files; the enum still exists). **Independent test**: those files construct `CommitTarget(ref=…)` with no `kind=`; no behavior change.
**Requirements**: FR-001, NFR-001.
- [x] T008 Drop mechanical `kind=PRIMARY` args + imports — CLI agent surface (1/3) (WP03)

**Prompt**: [tasks/WP03-mechanical-kind-drop.md](tasks/WP03-mechanical-kind-drop.md)
**Dependencies**: WP02. **Risks**: leave the 3 `kind=COORDINATION` + 2 runtime_bridge sites for WP04.

## WP14 — Mechanical `.kind` drop 2/3: coordination/events/runtime (Lane B) · CHEAP
**Goal**: FR-001a — same mechanical drop on `policy.py`/`transaction.py`/`decision_log.py`/`artifacts.py`/`mission_runtime/__init__.py` (5 files). **Independent test**: PRIMARY sites converted; COORDINATION carriers untouched (WP04's).
**Requirements**: FR-001, NFR-001.
- [x] T027 Drop mechanical `kind=PRIMARY` args + imports — coordination/events/runtime (2/3) (WP14)

**Prompt**: [tasks/WP14-mechanical-kind-drop-coord-events.md](tasks/WP14-mechanical-kind-drop-coord-events.md)
**Dependencies**: WP03. **Risks**: do NOT convert the `artifacts.py:127` / `policy.py:215` / `decision_log.py:95` COORDINATION carriers (WP04 owns those).

## WP15 — Mechanical `.kind` drop 3/3: core/git/upgrade (Lane B) · CHEAP
**Goal**: FR-001a — same mechanical drop on `core/mission_creation.py`/`invocation/executor.py`/`orchestrator_api/commands.py`/`git/commit_helpers.py`/`cli/commands/upgrade.py` (5 files). Tail of the mechanical drop — unblocks WP04. **Independent test**: PRIMARY sites converted; enum still imports.
**Requirements**: FR-001, NFR-001.
- [x] T028 Drop mechanical `kind=PRIMARY` args + imports — core/git/upgrade (3/3) (WP15)

**Prompt**: [tasks/WP15-mechanical-kind-drop-core-git.md](tasks/WP15-mechanical-kind-drop-core-git.md)
**Dependencies**: WP14. **Risks**: leave the `upgrade.py` FLATTENED producer for WP05; commit_helpers.py shared with WP07 (sequential).

## WP04 — Semantic `.kind`: COORDINATION conv + worktree_root (04a) (Lane B) · STRONG
**Goal**: FR-001b (risk half) — convert every `kind=COORDINATION` site + the `context.py:131` decision read to `routes_through_coordination(topology)` over STORED topology; rework `artifacts.py:127` residue authority as a topology projection; preserve runtime_bridge `worktree_root` (C-011). Unblocks WP16's enum deletion. **Independent test**: no `.kind` construction survives; residue predicate pins COORD→True AND flat→False; worktree_root pinned (non-identity fixture).
**Requirements**: FR-001, C-007, C-011, NFR-005.
- [x] T009 Convert the 3 `kind=COORDINATION` needs-care sites to the topology predicate (WP04)
- [x] T010 Preserve runtime_bridge parallel-classifier `worktree_root` selection (C-011) (WP04)

**Prompt**: [tasks/WP04-semantic-kind-enum-delete.md](tasks/WP04-semantic-kind-enum-delete.md)
**Dependencies**: WP15. **Risks**: derive residue from stored topology — no fabricated `.kind` shim (#2090-clean); C-011 worktree_root regression.

## WP16 — CommitTarget VO-field + enum deletion (04b) (Lane B) · STRONG
**Goal**: FR-001b (enum deletion) — remove `.kind` from the CommitTarget VO (ref-only, C-007), DELETE the `CommitTargetKind` enum, fix exports, and **rework the absolute-mapping equivalence cell off the enum in the same WP** (paula weld). **Independent test**: enum absent; WP01 AST guard green; `test_pure_stored_topology_projects_surface_placement` asserts via `routes_through_coordination` with the absolute per-topology pin preserved.
**Requirements**: FR-001, C-007, NFR-003, NFR-005.
- [x] T011 Remove `.kind` from CommitTarget VO; delete the enum; rework the absolute-mapping cell (WP16)

**Prompt**: [tasks/WP16-commit-target-kind-enum-delete.md](tasks/WP16-commit-target-kind-enum-delete.md)
**Dependencies**: WP04. **Risks**: resolve symbols by AST (the `"flattened"` value collides); KEEP the `flattened` meta-flag (C-006). Do NOT split the enum delete from the absolute-mapping test.

## WP05 — FLATTENED delete + ensure_topology removal + shim campsite (Lane B) · STRONG
**Goal**: FR-002 + FR-003 + campsite. Delete `CommitTargetKind.FLATTENED` producers/assertions (the enum member is removed by WP16; KEEP the `flattened` meta-flag, C-006); remove the dead `ensure_topology` shim + retarget its tests; remove the dead `safe_commit` re-export shim. **Independent test**: FLATTENED absent; `ensure_topology` gone with tests on `read_topology`/backfill; no `safe_commit` shim.
**Requirements**: FR-002, FR-003, NFR-003, NFR-004, C-006.
- [x] T012 Delete `CommitTargetKind.FLATTENED` (AST-verified write-only dead; KEEP flattened meta-flag) (WP05)
- [x] T013 Remove dead `ensure_topology` persist shim; retarget its tests (WP05)
- [x] T014 Campsite: remove dead `safe_commit` re-export shim (mission.py:54-58) (WP05)

**Prompt**: [tasks/WP05-flattened-shim-removal.md](tasks/WP05-flattened-shim-removal.md)
**Dependencies**: WP16. **Risks**: `FLATTENED.value == "flattened"` collides with the meta-flag — verify by AST/symbol, not grep.

## WP06 — topology=None absorption: boundary + NFR-002 flip (06a) (Lane B) · STRONG
**Goal**: FR-004 — acquire topology via `read_topology`/`classify_from_meta` at the read-path boundary, thread concrete non-optional `MissionTopology`, making the ~8 husk-arms **dead**; flip the NFR-002 repro GREEN via the absorption (welded). **Independent test**: NFR-002 repro passes (red-first proven on the pre-WP06 base); a COORD mission still resolves → coordination; C-001/C-003/C-005 unchanged.
**Requirements**: FR-004, NFR-001, NFR-002, NFR-005, C-001, C-003, C-005.
- [x] T015 Absorb `topology=None` at read-path boundary via `read_topology`/`classify_from_meta` (WP06)
- [x] T017 Flip the NFR-002 repro GREEN (welded to the absorption) (WP06)

**Prompt**: [tasks/WP06-topology-none-absorption.md](tasks/WP06-topology-none-absorption.md)
**Dependencies**: WP05, WP01. **Risks**: the absorption must not flatten COORD→PRIMARY; husk-arm removal is WP17's.

## WP17 — topology=None husk-arm collapse + 6th predicate + load_meta (06b) (Lane B) · STRONG
**Goal**: FR-004 (collapse) + FR-005 (6th predicate) + FR-006 (4-file load_meta). Remove the now-dead absent-field husk-arms KEEPING the corrupt-meta raise (C-004); collapse the 6th coord-routing predicate (`_topology_routes_through_coord`) in `_read_path_resolver.py`; convert the 4 topology files' load_meta calls to canonical. **Independent test**: corrupt-meta still raises (paired with absent-field absorbed); 6th predicate gone (AST); KEEP set pinned; load_meta contracts unchanged.
**Requirements**: FR-004, FR-005, FR-006, NFR-001, NFR-004, NFR-005, C-001, C-003, C-004, C-005.
- [x] T016 Collapse the ~8 `topology is None` husk-arms + the 6th predicate (KEEP corrupt-meta) (WP17)
- [x] T029 Convert the 4 topology files' load_meta calls; corrupt-meta C-004 cell (WP17)

**Prompt**: [tasks/WP17-topology-none-husk-collapse.md](tasks/WP17-topology-none-husk-collapse.md)
**Dependencies**: WP06, WP08. **Risks**: over-collapse deleting the corrupt-meta fallback — boundary discipline (None vs raise).

## WP07 — CommitResult JSON-serialization (#1891) (Lane B) · STRONG
**Goal**: FR-013 — make `CommitResult` JSON-serializable (serialize `worktree_root` Path) so `agent tasks map-requirements --json` emits valid JSON. Standalone (probe-confirmed disjoint from `.kind`); co-located in lane B because it shares `commit_helpers.py`/`tasks.py` with the enum eradication. **Independent test**: `map-requirements --json` parses as valid JSON.
**Requirements**: FR-013.
- [x] T018 Make CommitResult JSON-serializable (serialize worktree_root); fix map-requirements --json (WP07)

**Prompt**: [tasks/WP07-commitresult-json.md](tasks/WP07-commitresult-json.md)
**Dependencies**: WP17 (lane B tail). **Risks**: scope `tasks.py` ownership to the CommitResult-emit lines; the `--json` missing from `agent action implement` is OUT.

## WP08 — Polymorphic load_meta + 3-contract adapters (Lane C) · STRONG
**Goal**: FR-006a — build the ONE polymorphic `load_meta(dir, *, allow_missing, on_malformed)` absorbing the 3 distinct error contracts (None-on-missing+raise-on-malformed; raise-on-missing+utf-8-sig BOM; silent-empty-dict) + the 2 genuinely-distinct adapters. **Independent test**: the polymorphic reader covers all 3 contracts with focused tests.
**Requirements**: FR-006, NFR-001.
- [x] T019 Build the polymorphic `load_meta(dir, *, allow_missing, on_malformed)` + 3-contract adapters (WP08)

**Prompt**: [tasks/WP08-polymorphic-load-meta.md](tasks/WP08-polymorphic-load-meta.md)
**Dependencies**: WP01. **Risks**: preserve the utf-8-sig BOM-tolerant decode; keep absent-vs-malformed consistent with FR-004's boundary.

## WP09 — C2 sweep cluster 1: status/migration/coordination (Lane C) · MID
**Goal**: FR-006b — convert the status/migration/coordination meta-readers to the canonical polymorphic `load_meta`. **Independent test**: cluster-1 sites use the canonical reader; behavior unchanged.
**Requirements**: FR-006, NFR-001, NFR-004.
- [x] T020 C2 sweep cluster 1: status / migration / coordination meta-readers → canonical (WP09)

**Prompt**: [tasks/WP09-c2-sweep-status-migration.md](tasks/WP09-c2-sweep-status-migration.md)
**Dependencies**: WP08. **Risks**: EXCLUDE lane-B-owned files (resolution/surface_resolver/status_transition/_read_path_resolver/mission.py/tasks.py/commit_helpers).

## WP10 — C2 sweep cluster 2a: cli/dashboard/doc (Lane C) · MID
**Goal**: FR-006c — convert the cli/dashboard/doc meta-readers to the canonical reader (5 files). **Independent test**: cluster-2a sites use the canonical reader; behavior unchanged.
**Requirements**: FR-006, NFR-001, NFR-004.
- [x] T021 C2 sweep cluster 2a: cli / dashboard / doc meta-readers → canonical (WP10)

**Prompt**: [tasks/WP10-c2-sweep-cli-misc.md](tasks/WP10-c2-sweep-cli-misc.md)
**Dependencies**: WP08. **Risks**: EXCLUDE lane-E/F-owned files, task_helpers (lane D), and WP18's 5 files.

## WP18 — C2 sweep cluster 2b: retrospective/review/tracker/upgrade/verify (Lane C) · MID
**Goal**: FR-006c — convert the retrospective/review/tracker/upgrade/verify meta-readers, incl. the **silent-empty-dict** contract sites (`retrospective`, `review`) (5 files). **Independent test**: cluster-2b sites use the canonical reader; silent-empty sites return `{}` on a malformed file.
**Requirements**: FR-006, NFR-001, NFR-004.
- [x] T030 C2 sweep cluster 2b: retrospective / review / tracker / upgrade / verify (silent-empty) (WP18)

**Prompt**: [tasks/WP18-c2-sweep-retrospective-review.md](tasks/WP18-c2-sweep-retrospective-review.md)
**Dependencies**: WP08. **Risks**: the silent-empty-dict sites must stay silent-empty on malformed; disjoint from WP10's files.

## WP11 — task_helpers shadow-module retirement (Lane D) · CHEAP
**Goal**: FR-007 — reduce `scripts/tasks/task_helpers.py` (~490 LOC / 20 defs / 17 overlap) to a thin re-export of `task_utils/support.py`, honoring the `acceptance_support` compat contract. **Independent test**: task_helpers re-exports; the 17 duplicated impls gone; `acceptance_support` contract intact.
**Requirements**: FR-007, NFR-004.
- [x] T022 Retire scripts/tasks/task_helpers.py to a thin re-export of task_utils/support.py (WP11)

**Prompt**: [tasks/WP11-task-helpers-retire.md](tasks/WP11-task-helpers-retire.md)
**Dependencies**: WP08. **Risks**: the `acceptance_support` compat contract — keep the public names re-exported.

## WP12 — Accept gates topology-aware (Lane E) · STRONG
**Goal**: FR-008 + FR-009 — converge the accept dirty-gate on the `mission.py:862` reference pattern (`routes_through_coordination` + `is_coordination_artifact_residue_path`), don't widen `ACCEPT_OWNED_PATHS`; derive unchecked-tasks completion from WP terminal status; acceptance-matrix gate UNCHANGED (C-010). **Independent test**: a coord-topology mission with only residue passes the dirty gate; a flat mission's primary artifacts still block; orchestrated mission (all WPs approved/done, unticked checkboxes) passes the unchecked-tasks gate.
**Requirements**: FR-008, FR-009, C-010.
- [x] T023 FR-008 accept dirty-gate topology-aware (converge on mission.py:862 pattern) (WP12)
- [x] T024 FR-009 derive unchecked-tasks completion from WP terminal status (WP12)

**Prompt**: [tasks/WP12-accept-gates.md](tasks/WP12-accept-gates.md)
**Dependencies**: WP01, WP04 (the flat→False residue predicate). **Risks**: do NOT touch the acceptance-matrix gate (C-010); de-pin any fakeable accept tests in-slice.

## WP13 — Merge residue-gate sweep + 4th site (#1887) (Lane F) · STRONG
**Goal**: FR-012 — the 3 `advance_branch_ref` callers pass `coord_owned_filenames=COORD_OWNED_STATUS_FILES`; the post-merge invariant consults `is_coordination_artifact_residue_path`; the lane-auto-rebase 4th site (`auto_rebase.py:154`) converges onto `_COORD_RESIDUE_FILENAMES` (drops the drifting `{tasks.md, lanes.json, acceptance-matrix.json}` subset). **Independent test**: post-write ff-advance with coordination residue does not raise; a non-residue dirty path still raises; no gate carries its own residue literal.
**Requirements**: FR-012.
- [x] T025 FR-012 merge advance_branch_ref callers + post-merge invariant → single residue authority (WP13)
- [x] T026 FR-012 converge auto_rebase.py:154 4th residue site onto canonical _COORD_RESIDUE_FILENAMES (WP13)

**Prompt**: [tasks/WP13-merge-residue-sweep.md](tasks/WP13-merge-residue-sweep.md)
**Dependencies**: WP01. **Risks**: merge uses a fresh temp worktree — residue presence is situational; the gate is provably blind regardless.

---

## MVP / sequencing note
WP01 is the foundation (P0 barrier). Lane B is the critical path
(WP02→WP03→WP14→WP15→WP04→WP16→WP05→WP06→WP17→WP07). Lanes C/D/E/F parallelize
after WP01/WP08. No version prescription (C-008). The post-tasks adversarial
anti-laziness + test-suite-pitfall squads + the sizing squad have all run; the
WP re-slice (18 WPs) reflects their convergent findings.
