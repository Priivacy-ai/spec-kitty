# Tasks — Execution-Context Unification (01KTPKST)

**Branch**: `fixups/code-engine-stabilization` (flattened: planning base == merge target == coordination)
**Spec**: `spec.md` (FR-001..FR-015) · **Plan**: `plan.md` (13 ICs) · **Research**: `research.md` · **Findings**: `research/findings.md`

**Sequencing (operator: facade-first):** WP02 (status facade) + WP01 (parity ratchet, ATDD-first) + WP10
(occurrence-map, adjacent) have no deps and start first. WP03 (context composite) depends on WP02; the
read-path/parser/placement/retrospect-merge conversions depend on WP03; runtime writers (WP07) and
dead-symbol deletion (WP09) run after their prerequisites. Strangler discipline (C-004): convert →
prove parity green → delete. No parallel mechanisms (C-005).

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|----|----------|
| T001 | Dual-CWD parity harness (primary vs lane/coord) | WP01 | [P] |
| T002 | Flattened-topology synthetic fixture (no coord branch) | WP01 | [P] |
| T003 | xfail-gate conversion-dependent assertions + convergence docstring | WP01 | |
| T004 | Route raw primary/coord status readers through MissionStatus facade | WP02 | |
| T005 | `_identity_for_request` consumes resolved surface (#1737) | WP02 | |
| T006 | Lock-serialize `CoordinationWorkspace.resolve` (#1357) | WP02 | |
| T007 | Status visibility parity primary↔coord (#1572); flip WP01 status assertions | WP02 | |
| T008 | Grow `ExecutionContext` into doc-09 fragment/op-composite | WP03 | |
| T009 | `mid8` + `target_branch` single-derivation (FR-012) | WP03 | |
| T010 | `resolve_action_context` assembles fragments; `__all__` (C-007) | WP03 | |
| T011 | Flip WP01 identity/branch parity assertions | WP03 | |
| T012 | Fold `candidate_feature_dir_for_mission` into `_read_path_resolver` | WP04 | |
| T013 | Replace `_find_feature_directory` silent fallback with structured error (F-001/F-003) | WP04 | |
| T014 | Route `prompt_source_dir` via PromptSourceFragment | WP04 | |
| T015 | Flip WP01 read-path parity assertions | WP04 | |
| T016 | `core/paths` becomes the single worktree-pointer parser | WP05 | |
| T017 | Delete `workspace/root_resolver` duplicate parser (~200 LOC); re-point callers | WP05 | |
| T018 | Confirm net LOC down (NFR-005); flip WP01 workspace parity | WP05 | |
| T019 | `implement` artifact-placement via context (#1816) | WP06 | |
| T020 | `record-analysis` context-aware placement + `_find_feature_directory` fix in agent/mission.py (#1814) | WP06 | |
| T021 | analysis-report staleness keying context-aware (#1764) | WP06 | |
| T022 | SC-2: paused 01KTNWFC blockers do not reproduce; flip WP01 placement parity | WP06 | |
| T023 | `materialize_if_stale` git-op guard (#1789/#1062) | WP07 | |
| T024 | Context-aware stale-key (no false-stale across CWDs) | WP07 | |
| T025 | SC-5 long-rebase no-clobber; flip WP01 runtime-write parity | WP07 | |
| T026 | retrospect read/write to canonical surface (#1735/#1771) | WP08 | |
| T027 | merge coord-topology seams via context (#1736/#1770) | WP08 | |
| T028 | Flip WP01 retrospect/merge parity assertions | WP08 | |
| T029 | Confirm zero live callers of the 5 dead symbols (grep) | WP09 | |
| T030 | Delete 5 dead `status_service` symbols (strangler-ordered) | WP09 | |
| T031 | Extend occurrence-map schema with multi-path `moves:` (backward-compatible) | WP10 | [P] |
| T032 | Update bulk_edit gate/inference/diff_check for `moves:` | WP10 | [P] |
| T033 | Update bulk-edit-classification skill/doctrine to teach the moves model | WP10 | |
| T034 | Backward-compat test: legacy single-term map validates unchanged (C-OMAP-1) | WP10 | |
| T035 | Dashboard read paths use read-only `materialize_snapshot` (no tracked status.json write) | WP11 | |
| T036 | Share WP07 git-op detection (no duplicate) | WP11 | |
| T037 | Test: dashboard-no-clobber-during-rebase (SC-6a) | WP11 | |
| T038 | Collapse 3 sync orphan-reapers into ONE canonical reaper (FR-015) | WP12 | |
| T039 | Dedup `_is_process_alive`/health-probe across sync/ + dashboard/lifecycle.py (FR-015) | WP12 | |
| T040 | Singleton one-per-host/auth-scope; wire the ONE reaper into spawn path (#1071) | WP12 | |
| T041 | Tests: multi-interpreter one-daemon/reap + exactly-one-reaper assertion (SC-6b/SC-7) | WP12 | |

---

## Work Packages

### WP01 — Parity ratchet extension (ATDD-first regression guard) — IC-08

- **Goal**: EXTEND `tests/architectural/test_execution_context_parity.py` with dual-CWD assertions + a flattened-topology fixture. Authored first (red), converges green as conversions land. **Do not fork** a second parity test (C-005).
- **Priority**: P0 (gates the whole mission) · **Dependencies**: none · **Independent test**: the parity suite runs and the new assertions are present (xfail until their cluster converts).
- [x] T001 Dual-CWD parity harness (WP01)
- [x] T002 Flattened-topology synthetic fixture (WP01)
- [x] T003 xfail-gate conversion-dependent assertions + convergence docstring (WP01)

### WP02 — Status-facade adoption (Cluster B) — IC-01 — *facade-first, runs first*

- **Goal**: Make `MissionStatus`/OHS facade the sole status surface; fix parallel coord derivation (#1737); lock-serialize coord resolution (#1357); visibility parity (#1572).
- **Priority**: P0 · **Dependencies**: none · **Independent test**: status reads/writes route through the facade; concurrent resolve is serialized; primary↔coord visibility identical.
- [x] T004 Route raw status readers through facade (WP02)
- [x] T005 `_identity_for_request` consumes resolved surface (WP02)
- [x] T006 Lock-serialize `CoordinationWorkspace.resolve` (WP02)
- [x] T007 Visibility parity + flip WP01 status assertions (WP02)

### WP03 — MissionExecutionContext composite (doc-09 fragments) — IC-02

- **Goal**: Grow `mission_runtime.ExecutionContext` into the doc-09 fragment/op-composite; single-derive `mid8`/`target_branch`; `destination_ref` = CommitTarget.
- **Priority**: P0 · **Dependencies**: WP02 · **Independent test**: context resolves once; identity/branch parity assertions (WP01) pass from both CWDs.
- [x] T008 Grow ExecutionContext into fragment composite (WP03)
- [x] T009 `mid8` + `target_branch` single-derivation (WP03)
- [x] T010 `resolve_action_context` assembles fragments; `__all__` (WP03)
- [x] T011 Flip WP01 identity/branch parity assertions (WP03)

### WP04 — Read-path consolidation (Cluster A) — IC-03

- **Goal**: Fold `candidate_feature_dir_for_mission` into `_read_path_resolver`; kill the `_find_feature_directory` silent fallback (structured error); route `prompt_source_dir`. Directly fixes findings F-001/F-003.
- **Priority**: P1 · **Dependencies**: WP03 · **Independent test**: one read primitive; mid8/full-slug resolve identically; missing-surface raises a structured error (no wrong-but-plausible path).
- [x] T012 Fold duplicate read-path resolver (WP04)
- [x] T013 Structured error replaces silent fallback (WP04)
- [x] T014 Route `prompt_source_dir` (WP04)
- [x] T015 Flip WP01 read-path parity assertions (WP04)

### WP05 — Worktree-pointer parser collapse (Cluster C) — IC-04

- **Goal**: `core/paths` becomes the single worktree-pointer parser; delete the `workspace/root_resolver` duplicate (~200 LOC).
- **Priority**: P1 · **Dependencies**: WP03 (parallel with WP04) · **Independent test**: one parser; callers re-pointed; net LOC down.
- [x] T016 Single parser in `core/paths` (WP05)
- [x] T017 Delete duplicate parser; re-point callers (WP05)
- [x] T018 Confirm net LOC down; flip WP01 workspace parity (WP05)

### WP06 — Artifact-placement adoption (Cluster D) — IC-05 — *unblocks paused mission*

- **Goal**: `implement`-claim (#1816) and `record-analysis` (#1814) resolve placement via the context; analysis-report staleness context-aware (#1764).
- **Priority**: P1 · **Dependencies**: WP04 · **Independent test**: SC-2 — paused 01KTNWFC blockers do not reproduce on a fresh mission.
- [x] T019 `implement` placement via context (WP06)
- [x] T020 `record-analysis` context-aware + agent/mission.py `_find_feature_directory` fix (WP06)
- [x] T021 analysis-report staleness context-aware (WP06)
- [x] T022 SC-2 repro; flip WP01 placement parity (WP06)

### WP07 — Runtime writers git-op guard (Cluster E) — IC-06 — *highest-risk, last*

- **Goal**: `materialize_if_stale` never re-materializes tracked status during a git op (#1789/#1062); context-aware stale-key.
- **Priority**: P1 · **Dependencies**: WP02, WP03 · **Independent test**: SC-5 — long rebase completes with no status clobber.
- [x] T023 git-op guard (WP07)
- [x] T024 Context-aware stale-key (WP07)
- [x] T025 SC-5 scenario; flip WP01 runtime-write parity (WP07)

### WP08 — retrospect + merge coord-topology reconciliation — IC-07

- **Goal**: retrospect read/write to the canonical surface (#1735/#1771); merge coord seams (PATH/env, baking, JSONL) consume the context (#1736/#1770).
- **Priority**: P2 · **Dependencies**: WP03 · **Independent test**: retrospect reads canonical surface; merge resolves coord paths via context.
- [x] T026 retrospect canonical surface (WP08)
- [x] T027 merge coord seams via context (WP08)
- [x] T028 Flip WP01 retrospect/merge parity (WP08)

### WP09 — Dead-symbol deletion (strangler-ordered) — IC-09

- **Goal**: Delete the 5 dead `coordination/status_service.py` symbols once consumers are on the facade.
- **Priority**: P2 · **Dependencies**: WP02 · **Independent test**: grep shows zero live callers; symbols removed; suite green.
- [x] T029 Confirm zero live callers (WP09)
- [x] T030 Delete 5 dead symbols (WP09)

### WP10 — Occurrence-map structural-move extension (#1815) — IC-10 — *adjacent*

- **Goal**: Extend the occurrence-map schema + bulk-edit-classification skill to model multi-path structural `moves:`, backward-compatible with existing single-term maps.
- **Priority**: P2 · **Dependencies**: none · **Independent test**: C-OMAP-1 — legacy single-term map validates unchanged; a `moves:` map validates + gates.
- [x] T031 Extend occurrence-map schema with `moves:` (WP10)
- [x] T032 Update bulk_edit gate/inference/diff_check (WP10)
- [x] T033 Update bulk-edit-classification skill/doctrine (WP10)
- [x] T034 Backward-compat test (WP10)

### WP11 — Dashboard read-only status (no tracked write on read) (#1789 dashboard half) — IC-12 — *squad-validated*

- **Goal**: The **dashboard** (not the daemon) writes tracked `status.json` on read via the unguarded `materialize()` (`dashboard/handlers/features.py` + `scanner.py`) → switch its read paths to read-only `materialize_snapshot` and share WP07's git-op detection so background reads never write tracked status.
- **Priority**: P0 (#1789 is P0) · **Dependencies**: WP07 (git-op guard) · **Independent test**: SC-6a — dashboard serves kanban during a rebase with no `status.json` clobber.
- [x] T035 Dashboard read-only `materialize_snapshot` (no tracked write) (WP11)
- [x] T036 Share WP07 git-op detection (WP11)
- [x] T037 SC-6a dashboard-no-clobber test (WP11)

### WP12 — Sync-daemon singleton + reaper consolidation (#1789 daemon half / #1071 + FR-015 collapse) — IC-13

- **Goal**: The **sync daemon** (machine-global, missionless, writes no status) leaks across interpreters. Collapse the **three** duplicate orphan-reapers (`owner.is_orphan`/`list_orphan_records`, `orphan_sweep.sweep_orphans`, `daemon.scan_sync_daemons`/`cleanup_orphan_sync_daemons`, ~390 LOC) into **one** canonical reaper keyed on `DaemonOwnerRecord`, dedup `_is_process_alive`/health-probe shared with `dashboard/lifecycle.py`, and wire that one reaper into the `ensure_sync_daemon_running` spawn path enforcing **one daemon per host/auth-scope**.
- **Priority**: P0 · **Dependencies**: none (daemon lifecycle independent of context/facade) · **Independent test**: SC-6b (one daemon per host/auth-scope across interpreters, stale orphans reaped) + SC-7 (exactly one reaper / one `_is_process_alive` remains).
- [x] T038 Collapse 3 reapers → ONE canonical reaper (WP12)
- [x] T039 Dedup `_is_process_alive`/health-probe across sync/ + dashboard/lifecycle.py (WP12)
- [x] T040 Singleton one-per-host/auth-scope; wire the ONE reaper into spawn path (WP12)
- [x] T041 SC-6b/SC-7 multi-interpreter + one-reaper tests (WP12)

---

## Recommended reviewer profiles (R-07 — finalize-tasks assigns owners)
- **architect-alphonso** deep-review/sign-off: WP02 (status authority), WP03 (doc-09 fragment conformance), WP01 (parity proof), WP10 (occurrence-map schema + doctrine).
- **reviewer-renata**: standard per-WP review across all WPs.
- **doctrine/charter sign-off**: WP10 (bulk-edit doctrine).
- C-005 enforcement (one resolution path) is a cross-cutting acceptance check applied at WP03 + final review.
