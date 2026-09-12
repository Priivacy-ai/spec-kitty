# Tasks: Write-Side Seam: Matrix & Tracer Writers

**Mission**: `write-side-seam-matrix-tracer-01KYP3MH` · **Branch**: `feat/write-side-seam-matrix-tracer`
**Input**: [plan.md](./plan.md) (8-concern → 12-sub-concern IC map, 3 lanes), [spec.md](./spec.md) (13 FRs).

> Reference rows below are **not** checkboxes. Subtask completion is event-sourced —
> record with `spec-kitty agent tasks mark-status T0xx --status done`. The reduced
> event-log snapshot is the sole authority (#2816).

> **Standing clause for every WP (post-tasks squad, MAJOR-3):** each implementer runs a
> **Sonar attack-vector census on the files the WP touches** and either fixes the finding
> or records why it is safe (loopback/local-only, tool-wrong) in the PR — do not leave a
> new complexity/injection/dup finding unaddressed. This is part of every WP's Definition
> of Done even where the prompt body does not repeat it.

## Lane / sequencing overview

- **Lane A** — WP01 (FR-009 lane-base topology, ADR-first). Independent. Governs **PRIMARY-partition planning** durability only; per the E-B adjudication (2026-07-29) it is **not** a predecessor of WP11's matrix durability regression (matrix `%O` is coord-resolved).
- **Lane B** — WP02 (FR-010 coord-authority gate + `decisions/emit.py` Move A, **atomic**). Independent: per D-6 the `write_target`-routed writers are gate-invisible, so **no other WP depends on WP02**. Routing `emit.py` off the allow-list and re-pinning the census floor (4→3) is a single atomic change (ADR `2026-06-26-1-single-authority-seam-and-call-site-gate` Move A).
- **Lane C** — WP03 (seam core) → WP04/05/07/10 (writers, dep WP03 core) → WP08 (discovery+gate+reader switch, dep WP05 only — read-only, no seam write) → WP09 (dep WP08) → WP06 (completeness, dep WP05/08/09) → WP11 (driver, dep WP05/WP01). The `write_target`-routed writers depend on the WP03 **core**, not on Lane B; the read-only consumers (WP08/09/06) depend on WP05's canonical reader.

## Requirement → Work-Package coverage

| FR | WP | FR | WP |
|----|----|----|----|
| FR-001 | WP04 | FR-008 | WP11 |
| FR-002 | WP04 + WP05 + WP06/08/09/11 (reader migration) | FR-009 | WP01 |
| FR-003 | WP07 | FR-010 | WP02 |
| FR-004 | WP08 | FR-011 | WP03 |
| FR-005 | WP09 | FR-012 | WP03 |
| FR-006 | WP10 | FR-013 | WP05 |
| FR-007 | WP02 (emit.py) + WP03 (core) | | |

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|----|----------|
| T001 | Author lane-base ADR (recorded planning SHA; resolve coord-status-lineage vs §5+FR-007; no consolidation abort) | WP01 | |
| T002 | Record finalize-tasks planning SHA into `lanes.json`/`meta.json` | WP01 | |
| T003 | Retarget lane base in `worktree_allocator.py` to the recorded SHA (never a moving tip) | WP01 | |
| T004 | Reconcile `auto_rebase` merge-base reasoning + dependent-lane invariant #1684; note #2274 false-positive | WP01 | |
| T005 | Merge/ancestor regression tests (`executor`/`ordering`) | WP01 | |
| T006 | Red-first non-vacuity gate tests: no-`kind` `write_target()` fails; re-introduced kind-blind wrong-surface write fails | WP02 | |
| T007 | Route `decisions/emit.py:71` to the kind-aware seam (`write_target`) | WP02 | |
| T008 | Re-pin `COORD_AUTHORITY_WRITE_FLOOR` 4→3 + baseline; drop `emit.py` from allow-list + `_COORD_WRITE_BY_DESIGN` | WP02 | |
| T009 | Assert the three by-design sites (`widen/state.py`,`agent_tasks_ports.py`,`lanes/recovery.py`) stay kind-blind (floor non-vacuous at 3) | WP02 | |
| T046 | Ratify ADR `2026-06-26-1-single-authority-seam-and-call-site-gate` Proposed→Accepted (HiC-approved) | WP02 | |
| T010 | New shared write-seam helper: `write_target`+`commit_for_mission`, zero-write refusal (FR-011), idempotent structured result (FR-012) | WP03 | |
| T011 | ~~Route #2663 `implement.py` partition arm through the helper~~ **DEFERRED → #3071** (collides with pinned #2160/C-004 verbatim-commit deferral + literal-ref-unification guard) | WP03 | |
| T012 | ~~Route `status/emit.py` write (#2966 slice) through the helper~~ **DEFERRED → #3071** (status/emit.py has no git-commit to route — pure path-I/O; #2966 needs own spec) | WP03 | |
| T013 | Ledger-M16 recursion-guard tests + zero-write refusal disclosing #3033 | WP03 | |
| T014 | Structured acceptance schema half; confirm `overall_verdict` computed-property authoritative | WP04 | |
| T015 | New `acceptance-verdict` command fronting `write_acceptance_matrix` via `write_target(ACCEPTANCE_MATRIX)` | WP04 | |
| T016 | Persist-on-accept: write recomputed `overall_verdict` on all-pass/no-negative-invariant (regression #2318 comment) | WP04 | |
| T017 | Route acceptance-matrix caller sites (`gates_core`,`post_consolidation`,`backfill_provenance`,`accept.py`) through the helper | WP04 | |
| T018 | Tests: verdict determinism, persist-on-accept, idempotence | WP04 | |
| T019 | Red-first **B2**: `artifacts.py` `_MISSION_FILE_KIND_BY_BASENAME` + `"issue-matrix.json"→ISSUE_MATRIX` (keep `.md` failover); +/- recognition tests | WP05 | |
| T020 | `issue-matrix.json` structured schema + canonical writer via `write_target(ISSUE_MATRIX)` | WP05 | |
| T021 | Red-first **B3**: migrate finalize scaffold to author `issue-matrix.json` on COORD, not `.md` on PRIMARY | WP05 | |
| T022 | Migration sub-module (new): failover-read + migrate-on-write + bulk-migration command (FR-013) | WP05 | |
| T023 | **M7** single canonical `load_issue_matrix()→rows`; re-point `_issue_matrix.py` `validate_issue_matrix` to it (failover inside) | WP05 | |
| T024 | Tests: schema round-trip, migrate-on-write, failover-read, bulk migrate, recognition | WP05 | |
| T025 | **M8** doctrine/skills `.md`→`.json` (2× SKILL.md + core glossary-pack); run `test_no_legacy_terminology.py` | WP06 | [P] |
| T026 | **m3** test fallout: judge the `.md`-shaped issue-matrix tests (re-pin `.json` / migrate / delete obsolete markdown-parser tests) | WP06 | [P] |
| T027 | C-008 completeness assertion test: every live consumer reads JSON via the canonical reader; no `issue-matrix.md` emitted | WP06 | [P] |
| T028 | New multi-file discovery module scanning spec+tasks+plan+research+analysis-report+contracts | WP08 | |
| T029 | Repoint the 3 enforcement sites (`doctor.py:374`,`agent/tasks.py:159`,`agent/mission.py:2140`) to the new discovery | WP08 | |
| T030 | New merge-time completeness gate in `merge_gates.py` | WP08 | |
| T031 | Tests: multi-file discovery + gate enforcement | WP08 | |
| T032 | New `issue-verdict` command setting a row's per-item status via `write_target(ISSUE_MATRIX)` | WP07 | |
| T033 | Idempotence + structured result (FR-012); tests | WP07 | |
| T034 | Zero-reference → Gate 4 `not_applicable` in `review/__init__.py` (same definition as finalization) | WP09 | |
| T035 | Retain fail-closed when references exist; both-branch regression | WP09 | |
| T036 | New tracer writer routing `traces/` to COORD via the helper/`commit_for_mission` (leaf, not `read_dir` short-circuit) | WP10 | |
| T037 | New `tracer-append` command; attribution guard #2960 | WP10 | |
| T038 | Tests: lane-origin no `kitty-specs/` commit, `move-task` unblocked, idempotence | WP10 | |
| T039 | Red-first **#2970**: path-injection repro for `merge_driver.py` (5 S2083 BLOCKERs) | WP11 | |
| T040 | Row-aware acceptance+issue drivers over structured JSON (3-way `%O`/`%A`/`%B`, row-key canonicalization, delete-vs-stale) | WP11 | |
| T041 | **M6** registration 3 sites: `lanes/merge.py` repoint issue-matrix pattern `.md`→`.json`, `init.py:73/194`, NEW forward migration | WP11 | |
| T042 | Tests (driver-unit, synthetic %O): disjoint-row union, stale-residue, same-field conflict, intra-side dup-key, byte-determinism, #2970 regression | WP11 | |
| T043 | Reader switch (C-008/B-1): doctor `check_issue_matrix` + `tasks_parsing_validation.py` → dir-based `load_issue_matrix`, delete `.md` `.exists()` precheck; deprecate dead single-file `detect_issue_references` | WP08 | |
| T044 | Reader switch (C-008/B-1): post-merge review `_evaluate_issue_matrix` → dir-based `load_issue_matrix`, delete `.md` `.exists()` precheck | WP09 | |
| T045 | SC-003 durability-integration regression: real-git merge seeding `%O` from the seam-resolved matrix surface per topology (coord lineage here; + a flat-topology case), disjoint rows both survive via row-aware driver — no WP01 dep (E-B) | WP11 | |

---

## Work Packages

### WP01 — Lane-base common ancestor (Lane A) · FR-009
**Prompt**: [tasks/WP01-lane-base-common-ancestor.md](./tasks/WP01-lane-base-common-ancestor.md)
**Goal**: Branch execution lanes from the recorded planning-artifact commit so lane writes share a common ancestor with the consolidation base and survive merge. ADR-first.
**Priority**: P0 (structural). **Independent test**: a lane created at implement time branches from the recorded finalize-tasks SHA and its writes survive consolidation.
**Subtasks**: T001–T005. **Depends on**: none. **Risk**: git-topology P0; must pin a recorded SHA, never a moving tip; resolve coord-status-lineage in the ADR; no consolidation abort. **~220 lines.**

### WP02 — Coord-authority gate + emit.py Move A (Lane B) · FR-010 (+ FR-007 emit.py slice)
**Prompt**: [tasks/WP02-coord-authority-gate-move-a.md](./tasks/WP02-coord-authority-gate-move-a.md)
**Goal**: Route `decisions/emit.py` off the coord-authority allow-list to the kind-aware seam and re-pin the census floor 4→3 — one atomic change — keeping the gate non-vacuous.
**Priority**: P1. **Independent test**: the four named gate tests pass with `emit.py` routed, floor at 3, and the three by-design sites still counted.
**Subtasks**: T006–T009. **Depends on**: none (nothing depends on this WP — routed writers are gate-invisible). **Risk**: interlocking ratchet; a Move B predicate-widen is an ADR amendment. **~200 lines.**

### WP03 — Write-seam adoption core + generic bypasses (Lane C) · FR-007 core, FR-011, FR-012
**Prompt**: [tasks/WP03-write-seam-core.md](./tasks/WP03-write-seam-core.md)
**Goal**: One parameterized write-surface helper (`write_target`+`commit_for_mission`) with a zero-write refusal and idempotent structured results. **Delivered = T010 (helper) + T013 (recursion-guard/refusal).** ~~route the generic non-domain bypasses (#2663 implement partition, status/emit.py #2966)~~ **T011/T012 DEFERRED → #3071** (collide with pinned #2160/#2966 invariants C-006 marks out-of-scope; see write-seam-adoption.md "Deferred out of this mission").
**Priority**: P1 (foundation for all Lane-C writers). **Independent test**: the helper refuses (no write) on a deleted `target_branch` disclosing #3033, and is a no-op on re-run.
**Subtasks**: T010, T013 (delivered); T011, T012 (deferred → #3071). **Depends on**: none. **Risk**: routing the seam's own engine is circular — only the true bypasses; never fall back to writing `main`. **~240 lines.**

### WP04 — Acceptance verdict command + persist-on-accept (Lane C) · FR-001, FR-002 (acceptance half)
**Prompt**: [tasks/WP04-acceptance-verdict-command.md](./tasks/WP04-acceptance-verdict-command.md)
**Goal**: A command fronting `write_acceptance_matrix` via the seam keeping the computed verdict authoritative; canonical acceptance persists the recomputed `overall_verdict`.
**Priority**: P1. **Independent test**: accept an all-pass/no-negative-invariant mission → `acceptance-matrix.json` persists `overall_verdict: pass`.
**Subtasks**: T014–T018. **Depends on**: WP03. **Risk**: must not re-author the computed verdict or clobber invariant provenance. **~240 lines.**

### WP05 — Issue-matrix structured schema + writer + recognition + finalize scaffold + migration (Lane C) · FR-002 (issue half), FR-013
**Prompt**: [tasks/WP05-issue-matrix-structured-core.md](./tasks/WP05-issue-matrix-structured-core.md)
**Goal**: Define `issue-matrix.json` + canonical writer; teach the basename→kind map about `.json` (B2); migrate the finalize scaffold off `.md`-on-PRIMARY (B3); ship the migration sub-module + one canonical reader (M7).
**Priority**: P1. **Independent test**: a new mission scaffolds `issue-matrix.json` on COORD; `kind_for_mission_file("issue-matrix.json")==ISSUE_MATRIX`; a legacy `.md` mission failover-reads then migrates on first write.
**Subtasks**: T019–T024. **Depends on**: WP03. **Risk**: recognition-map/scaffold lag → split-brain; a second reader definition drifting. **~300 lines.**

### WP06 — Reader migration: doctrine/skills + test fallout + completeness (Lane C) · FR-002 reader migration, C-008
**Prompt**: [tasks/WP06-reader-migration-doctrine.md](./tasks/WP06-reader-migration-doctrine.md)
**Goal**: Migrate the doctrine/skills consumers `.md`→`.json` (M8), judge the `.md`-shaped test fallout (m3), and assert migration completeness (C-008) — dashboard & `merge_gates` are net-new, NOT migration targets.
**Priority**: P2. **Independent test**: `test_no_legacy_terminology.py` green; the completeness test proves no live consumer parses markdown.
**Subtasks**: T025–T027. **Depends on**: WP05, WP08, WP09 (its completeness test must run after the code-consumer reader switches in T043/T044/T023). **Risk**: missing a consumer; touching a domain WP's test file (record out-of-map rationale). **~180 lines.**

### WP07 — Issue-matrix verdict command (Lane C) · FR-003
**Prompt**: [tasks/WP07-issue-verdict-command.md](./tasks/WP07-issue-verdict-command.md)
**Goal**: A command setting a row's per-item status on `issue-matrix.json`, routed via `write_target(ISSUE_MATRIX)`.
**Priority**: P1. **Independent test**: set a row status via the command → JSON updates deterministically; re-run = no-op.
**Subtasks**: T032–T033. **Depends on**: WP05, WP03. **Risk**: keep derived fields authoritative. **~160 lines.**

### WP08 — Multi-file discovery + merge-time gate (Lane C) · FR-004
**Prompt**: [tasks/WP08-multifile-discovery-gate.md](./tasks/WP08-multifile-discovery-gate.md)
**Goal**: Generalize issue-reference discovery from single-`spec.md` to all mission artifacts across the three enforcement sites; add the missing merge-time completeness gate.
**Priority**: P1. **Independent test**: an issue referenced only in `tasks/WP01.md` is discovered and enforced at merge.
**Subtasks**: T028–T031, T043. **Depends on**: WP05 (WP03 dropped — this WP is read-only, no write through the seam). **Risk**: use the one canonical reference definition — avoid a fourth; owns the previously-unowned `tasks_parsing_validation.py` reader switch. **~250 lines.**

### WP09 — Zero-reference Gate 4 = not_applicable (Lane C) · FR-005
**Prompt**: [tasks/WP09-zero-reference-not-applicable.md](./tasks/WP09-zero-reference-not-applicable.md)
**Goal**: Post-merge review records Gate 4 `not_applicable` when the spec declares no canonical references; fail-closed retained when references exist.
**Priority**: P1. **Independent test**: zero-reference mission → Gate 4 `not_applicable`, verdict decided by applicable gates.
**Subtasks**: T034–T035, T044. **Depends on**: WP08. **Risk**: both branches need regression; owns the post-merge-review reader switch. **~170 lines.**

### WP10 — Tracer finding writer (Lane C) · FR-006
**Prompt**: [tasks/WP10-tracer-writer.md](./tasks/WP10-tracer-writer.md)
**Goal**: The one genuine must-build — a lane-origin `tracer-append` command routing `traces/` to the coord surface via the helper, leaving the lane branch unblocked with correct attribution.
**Priority**: P1. **Independent test**: append from a lane → lands on coord, zero lane `kitty-specs/` commit, `move-task` not blocked.
**Subtasks**: T036–T038. **Depends on**: WP03. **Risk**: attribution blanking (#2960) — guard `agent` presence; use the leaf, not the `read_dir(RETROSPECTIVE)` short-circuit. **~200 lines.**

### WP11 — Row-aware matrix merge driver (Lane C) · FR-008
**Prompt**: [tasks/WP11-row-aware-merge-driver.md](./tasks/WP11-row-aware-merge-driver.md)
**Goal**: Replace the whole-file "more-filled-side" drivers with row-aware, base-aware drivers over the structured JSON; fold #2970 path-injection hardening; fix driver registration at all 3 sites.
**Priority**: P2. **Independent test**: two lanes editing disjoint rows union with no clobber; a base row deleted on one side is dropped; #2970 injection regression is red-first.
**Subtasks**: T039–T042, T045. **Depends on**: WP05 (WP01 dep dropped per E-B — T045 seeds `%O` from the seam-resolved coord surface, orthogonal to the PRIMARY lane base). **Risk**: row-key stability + intra-side collision; #2970 fix must not weaken the merge contract. **~300 lines.**

---

## MVP scope

**WP03 (seam core) + WP04 (acceptance verdict + persist-on-accept)** is the smallest shippable slice: it closes the headline token-burn win (#2318) and the live stale-`overall_verdict` correctness bug behind the one-seam adoption. WP01/WP02 are structural enablers; the issue-matrix cluster (WP05–WP09) and the driver (WP11) build the deterministic-matrix half.
