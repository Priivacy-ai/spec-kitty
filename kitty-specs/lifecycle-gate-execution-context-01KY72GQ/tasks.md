---
description: "Work package task list for Lifecycle Gate Execution Context and Tool-Artifact Ownership"
---

# Work Packages: Lifecycle Gate Execution Context and Tool-Artifact Ownership

**Inputs**: Design documents from `kitty-specs/lifecycle-gate-execution-context-01KY72GQ/`
**Prerequisites**: plan.md (13 implementation concerns IC-01..IC-13), spec.md (US1-US6, FR-001..FR-018), data-model.md, contracts/ (gate-execution-context, negative-invariant-provenance, tool-artifact-owner), research/sibling-mission-coordination.md, quickstart.md ("Order of work" is authoritative).

**Tests**: Explicitly required — this is a brownfield remediation whose every FR carries an observable acceptance signal (ATDD-first). NFR-008 forbids shape-scanning tests except the one negative registry-backed structural exception (WP10).

**Base**: `upstream/main` `6d9ed490d` (contains #2832, #2835, #2818, sibling #2888). C-001 discharged; exemption-7 (group f) unblocked. Compat golden is **156** on this base.

**Topology**: coordination. This mission dogfoods coord topology (C-003); IC-01 must fix the claim-time consolidation blocker before any WP reaches its terminal step (C-002).

**Prompt Files**: Each work package references a matching prompt file in `tasks/`. This file is the high-level checklist; deep implementation detail lives in the prompt files.

## Subtask Format: `[Txxx] [P?] Description`

- **[P]** indicates the subtask/WP can proceed in parallel (file-disjoint from the main chain).
- The file graph is **one large connected component**; most work is roughly serial (lane A). Genuine parallelism: WP06, WP07 (conditional), WP10, WP15, WP16, WP17 (partial), WP19.

## Ownership Model (binding)

`owned_files` lists each WP's **authoritative surface** and is strictly non-overlapping (the finalizer's real guard against concurrent-WP collision). Where a file is touched by more than one concern, it is **owned by exactly one WP** and edited by the sequential others under **rationale-backed leeway** (recorded per-WP). Every leeway edit is serialized by a dependency edge, so no two *concurrent* WPs ever touch the same file. See plan.md "File Ownership (B4)".

---

## Phase 1 — Foundation & Claim-Blocker

## Work Package WP01: Claim-time consolidation blocker — live reproduction & fix (Priority: P1) 🎯 MVP

**Goal**: Reproduce and fix the real mechanism that blocks consolidation after a claim (the reported "dirty coord meta.json" is refuted — the VCS-lock write targets the PRIMARY partition), and capture the NFR-005 latency baseline as the very first action before any tree mutation.
**Independent Test**: A mission runs claim→consolidation on coord topology with zero manual intervention in the coord working tree (SC-003); a RED regression repro through the pre-existing entry point turns green.
**Prompt**: `tasks/WP01-claim-blocker-and-baseline.md`
**Requirement Refs**: FR-011, NFR-005, C-002

### Included Subtasks

- [ ] T001 Capture NFR-005 baseline (`spec-kitty accept --diagnose` timing on coord + flat fixtures) as the FIRST action, before any WP mutates the tree (WP01)
- [ ] T002 RED-first repro of the claim-time blocker through the pre-existing entry point; confirm the VCS-lock write targets PRIMARY via `placement_seam(...).read_dir(SPEC)` (WP01)
- [ ] T003 Fix the blocker at the reproduced site (`implement.py` lock write; `ref_advance` dirty scan; `preflight`) (WP01)
- [ ] T004 C-002 fallback: if no repro within timebox, convert to a documented finding and choose `auto_commit=True` or self-flatten, recording the decision (WP01)
- [ ] T005 Turn the RED repro green; verify merge preflight classifies the lock write correctly (WP01)
- [ ] T006 Confirm escape-hatch/rollback regression tests remain green unmodified (NFR-004) (WP01)

### Dependencies

- None (starting package). **Must be first** (C-002; the NFR-005 baseline can only be captured before any surface mutation).

### Risks & Mitigations

- Repro may show the blocker is on the primary checkout, not coord → the fix changes; timeboxed, with the recorded C-002 fallback.

---

## Phase 2 — Schema Root: Surface Translation Seam

## Work Package WP02: Surface→filesystem translation seam (the true schema root) (Priority: P1)

**Goal**: Build the ONE total `TopologySurface`→path translation, consuming the **existing** `probe_coord_state`/`CoordState` classifier — never a new one beside it — and declare `LANE`/`CONSOLIDATED`/`TEMP` **with** the seam. Repoint or demolish every translator it touches in the same pass; register any genuine survivor in the ratchet registry so it is visible and shrinking.
**Independent Test**: Every enum member resolves to a real location (operator's resolvability test); no translator adds a thirteenth while twelve survive.
**Prompt**: `tasks/WP02-surface-translation-seam.md`
**Requirement Refs**: FR-001, NFR-001, NFR-003, C-004, C-005

### Included Subtasks

- [ ] T007 Extend `TopologySurface` with `LANE`/`CONSOLIDATED`/`TEMP` declared WITH the seam; confirm the `Surface`→`TopologySurface` rename (ADR 2026-07-23-1) already landed, else complete it (WP02)
- [ ] T008 Build the one total translation consuming `probe_coord_state`/`CoordState` (`_read_path_resolver.py:256`) — no new classifier (WP02)
- [ ] T009 Totality test: every member resolves to a real location; no phantom member (WP02)
- [ ] T010 Repoint `gates_core.py::_acceptance_matrix_read_dir` onto the seam — collapse the `coord_read_dir_for(...) or feature_dir` fallback to affirmative declared-home resolution (WP02)
- [ ] T011 [P] Repoint `accept.py::_coord_worktree_root`, `forecast.py::feature_dir_for_preview`, `review_artifact_consistency.py::_resolve_review_cycle_read_dir` (WP02)
- [ ] T012 Repoint/demolish remaining translators in `resolution.py`; register any survivor in the ratchet registry (WP02)
- [ ] T013 C-005: if a seam symbol lands on the task-command compat surface, register in `test_tasks_compat_surface.py` and move the golden 156→157 in THIS WP (WP02)

### Dependencies

- Depends on WP01 (baseline captured first; claim-blocker understood).

### Risks & Mitigations

- **Most likely to fail by becoming additive.** A seam that adds a 13th translator while 12 survive has made the problem worse. Mitigation: repoint-or-demolish in the same pass; register survivors in the shrinking registry.
- Leeway edits (sequential): `gates_core.py` (owned WP03), `forecast.py`/`review_artifact_consistency.py` (owned WP07) — this WP touches only their translator functions.

---

## Phase 3 — Gate Execution Context

## Work Package WP03: Gate Execution Context + total resolvers (Priority: P1)

**Goal**: Introduce the `(surface, ref, phase)` value a gate is handed and cannot derive, the *cannot-evaluate* outcome, `LifecyclePhase`, and make the resolvers total (four `CoordState` answers), stamping every verdict with its surface.
**Independent Test**: A gate handed a context whose `surface` differs from both `repo_root` and cwd — all three seeded with different answers — returns the verdict seeded at `context.surface` (C1); a gate whose subject cannot exist returns cannot-evaluate (C2), never pass/fail.
**Prompt**: `tasks/WP03-gate-execution-context.md`
**Requirement Refs**: FR-001, NFR-001, NFR-003, C-004

### Included Subtasks

- [ ] T014 Introduce `GateExecutionContext` value object (surface, surface_kind, ref, phase, mission_slug); GEC-1 not-derivable (WP03)
- [ ] T015 Introduce `LifecyclePhase` (`REVIEW`<`ACCEPT`<`POST_CONSOLIDATION`) + PH-1 `NOT_APPLICABLE_IN_PHASE` (WP03)
- [ ] T016 cannot-evaluate outcome (C2) + GEC-5 (a stamp is not permission: COORD-homed kind on PRIMARY-stamped surface → cannot-evaluate) (WP03)
- [ ] T017 Total resolution per C3/C4/GEC-3: DELETED→raise `CoordinationBranchDeleted`; EMPTY+UNMATERIALIZED→resolve primary + stamp PRIMARY; MATERIALIZED→coord; GEC-2 ref-agreement raises (WP03)
- [ ] T018 C6 every verdict names its surface; C7 topology neutrality — reuse the decoy-marker idiom + `test_cwd_independence_resolves_identical_authority` (WP03)
- [ ] T019 C-005 compat golden check if a new task-surface symbol is exported (WP03)

### Dependencies

- Depends on WP02 (the resolved-surface seam).

### Risks & Mitigations

- Must not be named/shaped around coordination topology (C-004) or the flat case stays broken (#1834 reproduces on flat). Must not add new dependence on `flattened`.
- Leeway: `mission_runtime/artifacts.py` (resolver totality only; owned WP02).

---

## Phase 4 — Provenance, Deferral & Migration

## Work Package WP04: Negative-invariant provenance, deferral & single home (folds IC-09) (Priority: P1)

**Goal**: Every recorded judgement states its surface and ref; a pending invariant that cannot hold in the current surface records `deferred_to_consolidation` with a reason instead of a false `still_present`; the acceptance record is authored once to its declared home.
**Independent Test**: A `custom_command` invariant whose subject cannot exist pre-consolidation is recorded deferred with a reason and acceptance is not blocked (US1.1); provenance round-trips through `to_dict`/`from_dict` and is enforced by `validate_matrix_evidence`.
**Prompt**: `tasks/WP04-provenance-and-deferral.md`
**Requirement Refs**: FR-002, FR-003, FR-010, NFR-003

### Included Subtasks

- [ ] T020 Add provenance fields (`verified_ref`, `verified_surface_kind`, `deferred_reason`, `deferred_to_phase`, `provenance_origin`) + `deferred_to_consolidation` Result; round-trip (C2) (WP04)
- [ ] T021 NI-1 validation: `recorded` requires ref+surface; `legacy_unrecorded` permits null — one typed legacy escape (WP04)
- [ ] T022 NI-2: move the preservation guard from `result != "pending"` to terminal-set membership (`matrix.py:351`) so `deferred_to_consolidation` is not frozen — same WP as the fourth value (WP04)
- [ ] T023 NI-3/C4/C9 defer semantics: pending whose subject cannot exist → `deferred_to_consolidation` (never `still_present`); scoped `grep_absence` stays judgeable pre-consolidation (WP04)
- [ ] T024 NI-5/C5: `overall_verdict` gains `pass_pending_consolidation`; acceptance not blocked; `done` unreachable while any invariant deferred (WP04)
- [ ] T025 FR-010/C8/AH-3 single authoritative copy — no primary-scaffold second copy (finalize-tasks scaffolder) (WP04)
- [ ] T026 Provenance + deferral tests on realistic fixtures (WP04)

### Dependencies

- Depends on WP03 (gate execution context).

### Risks & Mitigations

- `pending` is the scaffolded default — this path is the common one. NI-2 guard change is load-bearing: without it, deferral is frozen and C6 impossible.
- Leeway: `gates_core.py` (deferral wiring; owned WP03).

---

## Work Package WP05: FR-014 provenance backfill migration (Priority: P2)

**Goal**: A one-time migration bringing all existing on-disk matrices onto the provenance schema, writing `provenance_origin: legacy_unrecorded` for pre-schema non-`pending` results, its own write enrolled in a commit-or-revert transaction.
**Independent Test**: Over a fixture matrix corpus (153 matrices, 40 non-`pending`, 0 with provenance), every non-`pending` result ends with a valid `provenance_origin` and `validate_matrix_evidence` passes on the migrated corpus.
**Prompt**: `tasks/WP05-provenance-backfill-migration.md`
**Requirement Refs**: FR-014

### Included Subtasks

- [ ] T027 One-time migration walking on-disk matrices, writing `legacy_unrecorded` for pre-schema non-`pending` results (WP05)
- [ ] T028 Enrol the migration's ~153-file write in a commit-or-revert transaction (explicit one-off transaction — the generalized owner is half-2) (WP05)
- [ ] T029 AM-4: migration never auto-archives; its failure path never reaches archive (WP05)
- [ ] T030 Migration oracle test over the fixture corpus (WP05)

### Dependencies

- Depends on WP04 (schema settled).

### Risks & Mitigations

- If the migration must use the generalized owner instead of a one-off transaction, add a dependency on WP09 and defer to half 2. Default: one-off transaction, stays in half 1.

---

## Phase 5 — Post-Consolidation & Preview

## Work Package WP06: Post-consolidation verification seam (zero merge/ footprint) (Priority: P1) [P]

**Goal**: A new `acceptance/post_consolidation.py` — dispatched as a governed Op, **nothing else** — that judges `deferred_to_consolidation` invariants against the consolidated tree and writes outcomes back with `verified_surface_kind = CONSOLIDATED`; a genuine violation fails **its Op**, not the consolidation.
**Independent Test**: A deferred invariant genuinely violated on the consolidated tree fails the verification Op and names the invariant, while the completed consolidation is left untouched (US1.4).
**Prompt**: `tasks/WP06-post-consolidation-verification.md`
**Requirement Refs**: FR-004, FR-005

### Included Subtasks

- [ ] T031 New `acceptance/post_consolidation.py` dispatched via `spec-kitty dispatch`; reads consolidated tree + matrix, writes outcomes — ZERO `merge/` coupling (WP06)
- [ ] T032 C6: judge deferred invariants against the consolidated tree; write `verified_surface_kind = CONSOLIDATED` + consolidation commit as `verified_ref` (WP06)
- [ ] T033 C7/FR-005: a `still_present` deferred invariant fails THE OP (names it); consolidation untouched; no rollback; no abort path inside consolidation (WP06)
- [ ] T034 Preserve the decoupling from `merge/executor.py` and the rollback machinery IC-06 is collapsing (WP06)
- [ ] T035 Tests on a consolidated fixture (confirmed_absent + still_present); register the new `tests/acceptance/` dir with BOTH gate-coverage baselines deliberately (C-006) (WP06)

### Dependencies

- Depends on WP04 (schema). **File-disjoint** — genuine lane-B parallelism.

### Risks & Mitigations

- Enforcement is the external CI check (FR-016 / WP18), not a loop guardrail — do not add a matrix-reader guardrail here.
- First creator of `tests/acceptance/` → trips gc3b (orphan, `--update-baseline`) and gc2b (selection, `--freeze-baselines`); update both deliberately.

---

## Work Package WP07: Two-partition consolidation-readiness preview (Priority: P1)

**Goal**: The readiness preview resolves lane-state and review-cycle from their own declared homes rather than one caller-supplied directory, so preview and real consolidation agree.
**Independent Test**: On a coord mission holding a genuinely rejected review outcome, the preview reports not-ready and names the WP (US2.1); a stale leftover review file does not cause a false not-ready (US2.2).
**Prompt**: `tasks/WP07-two-partition-preview.md`
**Requirement Refs**: FR-006, C-007

### Included Subtasks

- [ ] T036 `forecast.py`: resolve lane-state and review-cycle each from its own declared home (two partitions), not one caller-supplied dir (WP07)
- [ ] T037 `review_artifact_consistency.py`: partition split + remove the silent-degradation branch (WP07)
- [ ] T038 Harvest the two coord integration tests from PR #2834 **with attribution to @rayjohnson** (C-007) — do not rewrite (WP07)
- [ ] T039 SC-002: preview and real consolidation agree on the rejected-review case; stale leftover does not cause false not-ready (WP07)
- [ ] T040 Conditional: if the fix changes `run_review_artifact_consistency_preflight`'s signature it pulls in `merge/preflight.py` (IC-01's surface) — do NOT co-own preflight; edit under leeway (WP01 already landed) (WP07)

### Dependencies

- Depends on WP03. Serial after WP02 (shares `forecast.py`/`review_artifact_consistency.py` — WP02 touched only their translators). Conditionally lane-B.

### Risks & Mitigations

- **Verify the T040 signature check before assuming lane B exists** (plan File Ownership note).

---

## Phase 6 — Owner: Campsite & Generalization

## Work Package WP08: Campsite — split transaction.py before the owner opens it (Priority: P1)

**Goal**: Behaviour-free extraction so the owner generalisation lands in a module with room. Net **1345 → ~914 LOC**.
**Independent Test**: `tests/specify_cli/coordination/test_transaction.py` (1046 LOC) stays green **unchanged** through the extraction (its existing oracle).
**Prompt**: `tasks/WP08-transaction-campsite-split.md`
**Requirement Refs**: NFR-007

### Included Subtasks

- [ ] T041 Extract confined-atomic-write cluster (~170 LOC) into a sibling module — behaviour-free (WP08)
- [ ] T042 Extract legacy-mission resolution (~189 LOC), folding 3 redundant `load_meta` reads on the same path into 1 (WP08)
- [ ] T043 Extract the error hierarchy (~67 LOC) (WP08)
- [ ] T044 Delete the dead `threading.local()` sentinel (~5 LOC, zero repo-wide references) (WP08)
- [ ] T045 Verify net ~914 LOC; `test_transaction.py` green unchanged. Do NOT remove the 6 `flattened` references here (separate track R-005) (WP08)

### Dependencies

- Depends on WP01 (baseline). **Must precede WP09.** Independent of the acceptance chain (transaction.py is file-disjoint from acceptance surfaces).

### Risks & Mitigations

- Low by construction — no behaviour change. Keep it a separate WP from WP09: a behaviour-free refactor inside a behaviour-changing diff is unreviewable.

---

## Work Package WP09: Tool-Artifact Owner — generalise, enrol subprocess byproducts, adopt in merge executor (Priority: P1)

**Goal**: Generalise `BookkeepingTransaction` to any surface, add subprocess-byproduct enrolment, adopt it in the merge executor — collapsing the duplicate compensator in `merge/bookkeeping_projection.py`. One canonical churn classifier (FR-012).
**Independent Test**: For every enrolment-inventory row, interrupting the step leaves the artifact byte-identical to its pre- or committed post-state (NFR-002); the second compensator's symbols (`_capture_bookkeeping_snapshots`, `_restore_final_bookkeeping_snapshots`) are absent (C4b).
**Prompt**: `tasks/WP09-tool-artifact-owner.md`
**Requirement Refs**: FR-007, FR-008, FR-012, NFR-002

### Included Subtasks

- [ ] T046 Generalise `BookkeepingTransaction`: non-coord destination capability (WP09)
- [ ] T047 Subprocess-byproduct enrolment (TAO-1/C3) — replace the "detected, warned, abandoned" behaviour (WP09)
- [ ] T048 Adopt the owner in `merge/executor.py`; collapse `merge/bookkeeping_projection.py` (retire `_capture_bookkeeping_snapshots`/`_restore_final_bookkeeping_snapshots` — C4b) (WP09)
- [ ] T049 One canonical churn classifier (FR-012) consumed by every gate; `coherence.py` adoption (WP09)
- [ ] T050 TAO-2/NFR-002: fork+SIGKILL harness (≥100 trials, both-outcomes floor, POSIX-gated) in the `test_intake_atomic_writes.py` idiom; commit-spanning verified by recovery (WP09)
- [ ] T051 C6/C-010: preserve behaviour the exemptions got right; no previously-succeeding operation now fails (WP09)
- [ ] T052 C10: `coordination/transaction.py` ≤ 1000 LOC (WP09)

### Dependencies

- Depends on WP08 (campsite) and, transitively, WP01 (its findings inform what must be enrolled).

### Risks & Mitigations

- Highest-LOC surface. Do not open `merge/executor.py` until the owner has a non-coord destination.
- Leeway: `coordination/transaction.py` (owned WP08 — the enduring generalisation edits it under sequential leeway) and the sibling modules WP08 created.

---

## Phase 7 — Ratchet & Registry (lands EARLY — second in the owner track, before any retirement)

## Work Package WP10: Exemption registry + anti-ninth ratchet + enrolment inventory + cross-gate agreement (Priority: P1) [P]

**Goal**: A **negative, registry-backed** structural scan (the single NFR-008 exception) asserting no filename/basename/suffix/prefix churn predicate exists outside an explicit, shrinking registry; the tool-artifact enrolment inventory (owner C1); and the cross-gate agreement test (owner C7, RED on base). Each retirement WP later deletes its own registry row.
**Independent Test**: Adding a new filename-based exemption fails the suite and names the owner as the route (C9); the cross-gate test goes RED immediately on base (`git_probes.py:173` exempts `meta.json` while `ref_advance.py` does not).
**Prompt**: `tasks/WP10-registry-ratchet-inventory.md`
**Requirement Refs**: FR-012, FR-013, NFR-006, NFR-008

### Included Subtasks

- [ ] T053 Exemption registry: enumerated rows for every mechanism (≥11, rule-derived), initially expected-present; negative structural scan; registry only shrinks (WP10)
- [ ] T054 Anti-ninth ratchet (C9): a new filename-based exemption fails + names the owner — behavioural, not a literal source scan (WP10)
- [ ] T055 Tool-artifact enrolment inventory (owner C1): tool-derived, self-asserts both directions; clone `tests/architectural/untrusted_path_audit/` shape; drift-proof composite key (WP10)
- [ ] T056 Cross-gate agreement test (owner C7): same corpus → identical classification across all churn-classifying gates; RED on base — red-first for #2795 (WP10)
- [ ] T057 C-006: register new arch test file(s) with the shard map; keep NEGATIVE (absence outside registry), never a positive count; avoid golden-count-ban collision (WP10)
- [ ] T058 C8 rename-invariance behavioural test: C8a same-kind-different-basename unchanged; C8b operator-authored basename-collision NOT generated (WP10)

### Dependencies

- Depends on WP09 (owner) ONLY. **Lands before the first retirement** (R-017 stall countermeasure). File-disjoint (tests only) — parallel.

### Risks & Mitigations

- Deliberately structural, which NFR-008 forbids by default — keep it negative (absence outside a shrinking registry), never a positive literal count.

---

## Phase 8 — Exemption Retirements (strangler; each deletes its own registry row)

## Work Package WP11: Retire `is_self_bookkeeping_path` (IC-07a) (Priority: P2)

**Goal**: Retire `is_self_bookkeeping_path` and its filename/suffix sets, migrating behaviour to the owner (4 consumers).
**Independent Test**: The symbol is absent from `src/` (C5, per-symbol); its registry row is deleted (WP10 turns green); no previously-succeeding operation now fails (C6/C-010).
**Prompt**: `tasks/WP11-retire-self-bookkeeping-path.md`
**Requirement Refs**: FR-009, NFR-006, C-010

### Included Subtasks

- [ ] T059 Retire `is_self_bookkeeping_path` + sets; migrate behaviour to the owner/canonical classifier (WP11)
- [ ] T060 Delete this mechanism's registry row (WP11)
- [ ] T061 C6/C-010: preserve correct behaviour — notably `git_probes.py:173` `meta.json` handling now via the canonical classifier (WP11)
- [ ] T062 Migrate mechanism-asserting tests to the owner (WP11)

### Dependencies

- Depends on WP02, WP09, WP10. The **WP02** edge is load-bearing: `is_self_bookkeeping_path` and `is_coordination_artifact_residue_path` are *defined* in `mission_runtime/artifacts.py` (WP02-owned), so the retirement chain (WP11→WP12→WP17) must serialize after the seam rebuild. Sequential with WP12 (shares 5 consumer files).

### Risks & Mitigations

- Leeway (owned elsewhere, serial): `artifacts.py`, `mission_runtime/__init__.py` (WP02); `acceptance/__init__.py`, `review/dirty_classifier.py` (WP17); the registry row (WP10). Owns `merge/git_probes.py`, `cli/commands/agent/mission_record_analysis.py`.

---

## Work Package WP12: Retire `is_coordination_artifact_residue_path` (IC-07b) (Priority: P2)

**Goal**: Retire `is_coordination_artifact_residue_path` (7 consumers incl. `lanes/auto_rebase.py`, which aborts a rebase on unrecognised dirt), migrating behaviour to the owner.
**Independent Test**: The symbol is absent from `src/`; `auto_rebase.py`'s correct abort-on-dirt behaviour is preserved via the owner (C6/C-010).
**Prompt**: `tasks/WP12-retire-residue-path.md`
**Requirement Refs**: FR-009, NFR-006, C-010

### Included Subtasks

- [ ] T063 Retire `is_coordination_artifact_residue_path` (7 consumers); migrate to the owner (WP12)
- [ ] T064 `lanes/auto_rebase.py`: preserve the correct abort-on-unrecognised-dirt behaviour via the owner (WP12)
- [ ] T065 Delete this mechanism's registry row (WP12)
- [ ] T066 Migrate mechanism-asserting tests (WP12)

### Dependencies

- Depends on WP11 (shares `git_probes.py`, `mission_record_analysis.py`, `acceptance/__init__.py`, `artifacts.py`, `mission_runtime/__init__.py`).

### Risks & Mitigations

- **Plan ownership-table gap (surfaced during tasking):** (b) also lives in `implement.py`/`implement_cores.py`, which the table attributed only to (a)/(c)/(d). The a→b→c→d chain serializes it. Owns `lanes/auto_rebase.py`; all other sites are leeway serialized by the chain.

---

## Work Package WP13: Retire `COORD_OWNED_STATUS_FILES` + `advance_branch_ref` param + coord-staging skip (IC-07c) (Priority: P2)

**Goal**: Retire the one mechanism with 8 consumer sites (inseparable by C5). Scheduled **late** — two consumers (`merge/ordering.py`, `lanes/merge.py`) are in the `merge/` package; re-fetch before starting.
**Independent Test**: `COORD_OWNED_STATUS_FILES` and its `advance_branch_ref` parameter are absent from `src/`; behaviour preserved via the owner.
**Prompt**: `tasks/WP13-retire-coord-owned-status-files.md`
**Requirement Refs**: FR-009, FR-012, NFR-006, C-001, C-010

### Included Subtasks

- [ ] T067 Re-fetch upstream (C-001 residual). Retire `COORD_OWNED_STATUS_FILES` + `advance_branch_ref` param + coord-staging skip across all 8 sites atomically (C5) (WP13)
- [ ] T068 Migrate behaviour to the owner/canonical classifier (WP13)
- [ ] T069 Delete this mechanism's registry row (WP13)
- [ ] T070 Preserve correct behaviour (C-010); `merge/` package care (WP13)
- [ ] T071 Migrate mechanism-asserting tests (WP13)

### Dependencies

- Depends on WP12 (shares `commit_router.py`, `implement.py`, `implement_cores.py`).

### Risks & Mitigations

- Owns `status/__init__.py`, `merge/ordering.py`, `lanes/merge.py`, `coordination/commit_router.py`. Leeway: `coherence.py` (WP09), `implement.py` (WP01), `implement_cores.py` (WP14), `git/ref_advance.py` (WP01).

---

## Work Package WP14: Deduplicate `_drop_*` siblings into one `_drop_if` (IC-07d) (Priority: P2)

**Goal**: Deduplicate `_drop_vcs_lock_only_meta`, `_drop_runtime_frontmatter_only_wp` (+ its `_WP_FILENAME_PATTERN`/`_is_wp_filename` twin) and `_exclude_coord_owned` — applied on the same two call lines — into ONE `_drop_if(paths, predicate)`. Do NOT retire sequentially.
**Independent Test**: All three `_drop_*` symbols + the filename-pattern twin are absent; a single `_drop_if` replaces them; behaviour preserved.
**Prompt**: `tasks/WP14-dedupe-drop-if.md`
**Requirement Refs**: FR-009, NFR-006, C-010

### Included Subtasks

- [ ] T072 Deduplicate the three `_drop_*`/`_exclude_coord_owned` sites + retire the `_WP_FILENAME_PATTERN`/`_is_wp_filename` twin into one `_drop_if(paths, predicate)` (WP14)
- [ ] T073 Check IC-01 pre-emption: if WP01 committed the VCS lock rather than dropping it, part of (d) is pre-empted — re-check before slicing (WP14)
- [ ] T074 Delete this mechanism's registry rows (symbols 5 + 8) (WP14)
- [ ] T075 Migrate mechanism-asserting tests; preserve behaviour (C-010) (WP14)

### Dependencies

- Depends on WP13 (shares `implement_cores.py`).

### Risks & Mitigations

- **Owns `_exclude_coord_owned`** — it is retired HERE (d), not in WP17 (g), resolving the plan's double-listing. Owns `cli/commands/implement_cores.py`, `frontmatter.py`. Leeway: `implement.py` (WP01).

---

## Work Package WP15: Retire `RUNTIME_STATE_ALLOWLIST` (IC-07e) (Priority: P2) [P]

**Goal**: Retire `RUNTIME_STATE_ALLOWLIST` / `_runtime_state_exemption` — single file, fully isolated.
**Independent Test**: Both symbols absent from `src/`; behaviour preserved via the owner.
**Prompt**: `tasks/WP15-retire-runtime-state-allowlist.md`
**Requirement Refs**: FR-009, NFR-006, C-010

### Included Subtasks

- [ ] T076 Retire `RUNTIME_STATE_ALLOWLIST`/`_runtime_state_exemption` in `bulk_edit/diff_check.py`; migrate to the owner/canonical classifier (WP15)
- [ ] T077 Delete this mechanism's registry row (WP15)
- [ ] T078 Migrate mechanism-asserting tests; preserve behaviour (WP15)

### Dependencies

- Depends on WP09, WP10. **File-disjoint — parallel.**

### Risks & Mitigations

- Owns `bulk_edit/diff_check.py` only. Genuinely isolated.

---

## Work Package WP16: Retire `new_checkout_paths` (IC-07f) (Priority: P2) [P]

**Goal**: Retire `new_checkout_paths` "preserved without cleanup" across ~10 sites (`:1115-1632`) in `tasks_move_task.py` — a parameter threaded through four signatures + a dataclass field, not a console block. Sibling-gate CLEARED (#2888).
**Independent Test**: `new_checkout_paths` absent from `src/`; the "preserved without cleanup" byproduct is enrolled in the owner instead; behaviour preserved.
**Prompt**: `tasks/WP16-retire-new-checkout-paths.md`
**Requirement Refs**: FR-009, NFR-006, C-010

### Included Subtasks

- [ ] T079 Re-confirm line numbers at implement time (`_TransitionGateInputs` :1172, `dirty_before` :1182, `new_checkout_paths` :1076/:1494/:1545) — the sibling may have folded further (WP16)
- [ ] T080 Retire `new_checkout_paths` across ~10 sites `:1115-1632` (param through 4 signatures + dataclass field + JSON emit + docstring + dirty capture/threading + console emit + `dirty_after - dirty_before`) (WP16)
- [ ] T081 Delete this mechanism's registry row (WP16)
- [ ] T082 Migrate mechanism-asserting tests; preserve behaviour (WP16)

### Dependencies

- Depends on WP09, WP10. **File-disjoint — parallel.**

### Risks & Mitigations

- Size for the ~10-site footprint, not the console block. Owns `cli/commands/agent/tasks_move_task.py` only.

---

## Work Package WP17: Retire the R-014 additions — `ACCEPT_OWNED_PATHS`, dirty_classifier bundle, dead field (IC-07g) (Priority: P2)

**Goal**: Retire `ACCEPT_OWNED_PATHS` (the most on-thesis instance — the accept gate ignoring the accept pipeline's own writes), the `dirty_classifier` bundle (with the review-handoff path), and delete the dead `ignores_primary_coord_residue` field (zero external consumers).
**Independent Test**: `ACCEPT_OWNED_PATHS` and `ignores_primary_coord_residue` absent from `src/`; the dirty_classifier bundle retired against the owner; behaviour preserved.
**Prompt**: `tasks/WP17-retire-r014-additions.md`
**Requirement Refs**: FR-009, NFR-006, C-010

### Included Subtasks

- [ ] T083 Retire `ACCEPT_OWNED_PATHS` (`acceptance/__init__.py`) against the owner (WP17)
- [ ] T084 Retire the `dirty_classifier` bundle (`review/dirty_classifier.py`) with the review-handoff path (WP17)
- [ ] T085 Delete the dead `ignores_primary_coord_residue` field (`mission_runtime/artifacts.py`) — zero external consumers (WP17)
- [ ] T086 Delete group (g) registry rows; note `_exclude_coord_owned` is retired by WP14 (d), NOT here — avoid double-retirement (WP17)
- [ ] T087 Migrate mechanism-asserting tests; preserve behaviour (WP17)

### Dependencies

- Depends on WP12 (shares `acceptance/__init__.py`, `review/dirty_classifier.py`, `artifacts.py`). Parallel to WP13/WP14 (file-disjoint from them).

### Risks & Mitigations

- Owns `acceptance/__init__.py`, `review/dirty_classifier.py`. Leeway: `artifacts.py` (dead field; WP02).

---

## Phase 9 — Enforcement, Docs & Archiving

## Work Package WP18: External enforcement, disclosure & deferral-contract docs (IC-10) (Priority: P2)

**Goal**: A CI consistency check that fails any PR carrying a dangling `deferred_to_consolidation` invariant (FR-016); assignment-time disclosure (FR-017); and the operator-facing guide (FR-018). Written AFTER the deferral semantics land.
**Independent Test**: A PR with an unresolved `deferred_to_consolidation` invariant fails the CI check; assigning the deferral emits the disclosure; `accept-and-merge.md` describes the contract; `check_docs_freshness --ci` and `test_no_legacy_terminology.py` pass.
**Prompt**: `tasks/WP18-enforcement-disclosure-docs.md`
**Requirement Refs**: FR-016, FR-017, FR-018

### Included Subtasks

- [ ] T088 FR-016: CI consistency check at the front of the quality run — fail any PR with a dangling `deferred_to_consolidation` invariant (WP18)
- [ ] T089 FR-017: assignment-time disclosure emitted when the status path writes `deferred_to_consolidation` (WP18)
- [ ] T090 FR-018: `docs/guides/accept-and-merge.md` explains deferral + post-consolidation verification + required gate; cross-link `docs/context/orchestration.md` (WP18)
- [ ] T091 Refresh generated doc indexes (`freshen_adr_inventory.py` then `docs_index.py --write`, `PYTHONPATH=.`); run `test_no_legacy_terminology.py` + `check_docs_freshness --ci` (WP18)
- [ ] T092 Write docs AFTER semantics land; avoid stale docs (WP18)

### Dependencies

- Depends on WP04 (schema settled) and WP06 (post-consolidation seam exists to describe).

### Risks & Mitigations

- Docs written ahead of behaviour go stale silently. Leeway: the disclosure emit site (owned WP04's matrix/gates surface — sequential, documented).

---

## Work Package WP19: Mission archiving as a first-class lifecycle operation (IC-13) (Priority: P3) [P]

**Goal**: A first-class archive operation producing an immutable, explicitly-legacy `ArchivedMission` snapshot excluded from live validation but kept enumerable — with the four `AM` guards so it can never be an escape from acceptance failure.
**Independent Test**: The four US6 scenarios (SC-008): non-terminal refused; `still_present` refused; clean terminal archived, enumerable, excluded from live validation; migration never auto-archives.
**Prompt**: `tasks/WP19-mission-archiving.md`
**Requirement Refs**: FR-015

### Included Subtasks

- [ ] T093 New archive command/verb + `ArchivedMission` record (mission_id, archived_by, archived_at, reason, terminal_state_at_archive) (WP19)
- [ ] T094 AM-1 terminal-only refuse; AM-2 refuse while any invariant `still_present` (WP19)
- [ ] T095 AM-3 excluded from live validation but enumerable (`doctor`); AM-5 cancellation clears deferrals to a `canceled` disposition — abandonment is not a deadlock (WP19)
- [ ] T096 AM-4 never automatic; not reachable from the FR-014 migration failure path (WP19)
- [ ] T097 Tests: the four US6 scenarios (SC-008) (WP19)
- [ ] T098 C-006: register any new sink/command surface (WP19)

### Dependencies

- Depends on WP04 (references invariant `still_present`/matrix state). **Orthogonal to both seams** — the first concern to cut if scope must shrink.

### Risks & Mitigations

- An ungoverned archive is a one-command escape from acceptance failure; the four `AM` invariants exist precisely to prevent that.

---

## Dependency & Execution Summary

- **Half 1 (Seam 1)**: WP01 → WP02 → WP03 → WP04 → {WP05, WP06[P], WP07}; docs WP18 and archiving WP19[P] hang off WP04/WP06.
- **Half 2 (Seam 2)**: WP08 → WP09 → WP10 → retirements. WP08 forks off WP01 in parallel with the acceptance chain.
- **Retirement order**: WP11 → WP12 → WP13 → WP14 (shared-file chain); WP15[P], WP16[P] off WP09/WP10; WP17 off WP12 (parallel to WP13/WP14).
- **Ratchet lands EARLY** (WP10, before any retirement) — R-017 stall countermeasure. **The registry is structured as one row artifact per mechanism** (a per-mechanism row file under a WP10-owned directory, or an equivalent structure whose rows delete independently), so each retirement deletes **its own** row (red→green) without editing a file a sibling retirement also edits. This honors the plan's explicit reason for rejecting golden-count mode ("makes all retirement WPs co-own one file") and is what keeps the `[P]` retirements (WP15/WP16) and WP17-parallel-to-WP13/WP14 genuinely collision-free: WP10 is every retirement's ancestor (serializing create-vs-delete), and no two retirements touch the same row artifact.
- **Genuine parallelism**: WP06, WP07 (conditional), WP10, WP15, WP16, WP17 (partial), WP19. Everything else is roughly serial (one connected file graph, lane A).
- **MVP scope**: WP01 (unblocks the mission's own consolidation) + the half-1 chain WP02→WP07 (the three live defects #1834/#2885/#2882 + schema + deferral contract).
- **Pre-agreed Fallback Split** (plan.md): ship half 1 (WP01–WP07, WP18) and defer half 2 (WP08–WP17, WP19) to a follow-on if IC-07(f) or the merge-package tension delays the retirement half. Default stays ONE mission.

---

## Requirements Coverage Summary

| Requirement ID | Covered By Work Package(s) |
|----------------|----------------------------|
| FR-001 | WP02, WP03 |
| FR-002 | WP04 |
| FR-003 | WP04 |
| FR-004 | WP06 |
| FR-005 | WP06 |
| FR-006 | WP07 |
| FR-007 | WP09 |
| FR-008 | WP09 |
| FR-009 | WP11, WP12, WP13, WP14, WP15, WP16, WP17 |
| FR-010 | WP04 |
| FR-011 | WP01 |
| FR-012 | WP09, WP10, WP13 |
| FR-013 | WP10 |
| FR-014 | WP04, WP05 |
| FR-015 | WP19 |
| FR-016 | WP18 |
| FR-017 | WP18 |
| FR-018 | WP18 |
| NFR-001 | WP02, WP03 |
| NFR-002 | WP09 |
| NFR-003 | WP03, WP04 |
| NFR-004 | WP01 (baseline; every WP keeps escape-hatch/rollback tests green unmodified) |
| NFR-005 | WP01 |
| NFR-006 | WP10, WP11, WP12, WP13, WP14, WP15, WP16, WP17 |
| NFR-007 | WP08 (every WP: ruff/mypy clean, complexity ≤15) |
| NFR-008 | WP10 (the single negative registry-backed structural exception) |
| C-001 | WP13 |
| C-002 | WP01 |
| C-004 | WP02, WP03 |
| C-005 | WP02, WP03 |
| C-006 | WP06, WP10, WP19 |
| C-007 | WP07 |
| C-010 | WP11, WP12, WP13, WP14, WP15, WP16, WP17 |

---

## Subtask Index (Reference)

| Subtask ID | Summary | Work Package | Priority | Parallel? |
|------------|---------|--------------|----------|-----------|
| T001 | NFR-005 baseline capture (first action) | WP01 | P1 | No |
| T002 | RED-first claim-blocker repro | WP01 | P1 | No |
| T003 | Fix the blocker at the reproduced site | WP01 | P1 | No |
| T004 | C-002 fallback if no repro | WP01 | P1 | No |
| T005 | Turn repro green; preflight classifies lock write | WP01 | P1 | No |
| T006 | Escape-hatch/rollback tests green (NFR-004) | WP01 | P1 | No |
| T007 | Extend TopologySurface (LANE/CONSOLIDATED/TEMP) | WP02 | P1 | No |
| T008 | One total translation via CoordState | WP02 | P1 | No |
| T009 | Totality/resolvability test | WP02 | P1 | No |
| T010 | Repoint _acceptance_matrix_read_dir | WP02 | P1 | No |
| T011 | Repoint accept/forecast/review translators | WP02 | P1 | Yes |
| T012 | Repoint/demolish resolution.py translators | WP02 | P1 | No |
| T013 | C-005 compat golden if seam symbol exported | WP02 | P1 | No |
| T014 | GateExecutionContext value object | WP03 | P1 | No |
| T015 | LifecyclePhase + PH-1 | WP03 | P1 | No |
| T016 | cannot-evaluate + GEC-5 | WP03 | P1 | No |
| T017 | Total resolution (four CoordState answers) | WP03 | P1 | No |
| T018 | C6 surface-named + C7 topology neutrality | WP03 | P1 | No |
| T019 | C-005 compat golden if new symbol | WP03 | P1 | No |
| T020 | Provenance fields + deferred_to_consolidation | WP04 | P1 | No |
| T021 | NI-1 validation (typed legacy escape) | WP04 | P1 | No |
| T022 | NI-2 terminal-set guard change | WP04 | P1 | No |
| T023 | NI-3/C4/C9 defer semantics | WP04 | P1 | No |
| T024 | NI-5 pass_pending_consolidation | WP04 | P1 | No |
| T025 | FR-010/C8/AH-3 single home | WP04 | P1 | No |
| T026 | Provenance + deferral tests | WP04 | P1 | No |
| T027 | Migration walks matrices → legacy_unrecorded | WP05 | P2 | No |
| T028 | Enrol migration write in commit-or-revert txn | WP05 | P2 | No |
| T029 | AM-4 migration never auto-archives | WP05 | P2 | No |
| T030 | Migration oracle test | WP05 | P2 | No |
| T031 | New post_consolidation.py Op (zero merge/) | WP06 | P1 | Yes |
| T032 | C6 judge against consolidated tree | WP06 | P1 | Yes |
| T033 | C7/FR-005 fail the Op not consolidation | WP06 | P1 | Yes |
| T034 | Preserve decoupling from executor/rollback | WP06 | P1 | Yes |
| T035 | Tests + register tests/acceptance/ baselines | WP06 | P1 | Yes |
| T036 | forecast.py two-partition resolution | WP07 | P1 | No |
| T037 | review_artifact_consistency partition split | WP07 | P1 | No |
| T038 | Harvest PR #2834 tests (attrib @rayjohnson) | WP07 | P1 | No |
| T039 | SC-002 preview↔consolidation agreement | WP07 | P1 | No |
| T040 | Conditional preflight-signature check | WP07 | P1 | No |
| T041 | Extract confined-atomic-write cluster | WP08 | P1 | No |
| T042 | Extract legacy-mission resolution | WP08 | P1 | No |
| T043 | Extract error hierarchy | WP08 | P1 | No |
| T044 | Delete dead threading.local() sentinel | WP08 | P1 | No |
| T045 | Verify ~914 LOC; test_transaction.py green | WP08 | P1 | No |
| T046 | Generalise owner: non-coord destination | WP09 | P1 | No |
| T047 | Subprocess-byproduct enrolment | WP09 | P1 | No |
| T048 | Adopt in executor; collapse projection | WP09 | P1 | No |
| T049 | One canonical churn classifier (FR-012) | WP09 | P1 | No |
| T050 | NFR-002 fork+SIGKILL harness | WP09 | P1 | No |
| T051 | C6/C-010 preserve behaviour | WP09 | P1 | No |
| T052 | C10 transaction.py ≤1000 LOC | WP09 | P1 | No |
| T053 | Exemption registry (negative scan) | WP10 | P1 | Yes |
| T054 | Anti-ninth ratchet C9 | WP10 | P1 | Yes |
| T055 | Enrolment inventory (owner C1) | WP10 | P1 | Yes |
| T056 | Cross-gate agreement test (C7, RED) | WP10 | P1 | Yes |
| T057 | C-006 shard-map registration | WP10 | P1 | Yes |
| T058 | C8 rename-invariance test | WP10 | P1 | Yes |
| T059 | Retire is_self_bookkeeping_path | WP11 | P2 | No |
| T060 | Delete registry row | WP11 | P2 | No |
| T061 | Preserve git_probes meta.json behaviour | WP11 | P2 | No |
| T062 | Migrate mechanism tests | WP11 | P2 | No |
| T063 | Retire is_coordination_artifact_residue_path | WP12 | P2 | No |
| T064 | Preserve auto_rebase abort-on-dirt | WP12 | P2 | No |
| T065 | Delete registry row | WP12 | P2 | No |
| T066 | Migrate mechanism tests | WP12 | P2 | No |
| T067 | Retire COORD_OWNED_STATUS_FILES (8 sites) | WP13 | P2 | No |
| T068 | Migrate to owner/canonical classifier | WP13 | P2 | No |
| T069 | Delete registry row | WP13 | P2 | No |
| T070 | Preserve behaviour; merge/ care | WP13 | P2 | No |
| T071 | Migrate mechanism tests | WP13 | P2 | No |
| T072 | Deduplicate _drop_* into _drop_if | WP14 | P2 | No |
| T073 | Check IC-01 pre-emption | WP14 | P2 | No |
| T074 | Delete registry rows (5+8) | WP14 | P2 | No |
| T075 | Migrate tests; preserve behaviour | WP14 | P2 | No |
| T076 | Retire RUNTIME_STATE_ALLOWLIST | WP15 | P2 | Yes |
| T077 | Delete registry row | WP15 | P2 | Yes |
| T078 | Migrate tests; preserve behaviour | WP15 | P2 | Yes |
| T079 | Re-confirm line numbers | WP16 | P2 | Yes |
| T080 | Retire new_checkout_paths (~10 sites) | WP16 | P2 | Yes |
| T081 | Delete registry row | WP16 | P2 | Yes |
| T082 | Migrate tests; preserve behaviour | WP16 | P2 | Yes |
| T083 | Retire ACCEPT_OWNED_PATHS | WP17 | P2 | No |
| T084 | Retire dirty_classifier bundle | WP17 | P2 | No |
| T085 | Delete dead ignores_primary_coord_residue | WP17 | P2 | No |
| T086 | Delete group (g) registry rows | WP17 | P2 | No |
| T087 | Migrate tests; preserve behaviour | WP17 | P2 | No |
| T088 | FR-016 CI consistency check | WP18 | P2 | No |
| T089 | FR-017 assignment-time disclosure | WP18 | P2 | No |
| T090 | FR-018 accept-and-merge.md guide | WP18 | P2 | No |
| T091 | Refresh doc indexes; freshness gates | WP18 | P2 | No |
| T092 | Write docs after semantics land | WP18 | P2 | No |
| T093 | Archive command + ArchivedMission record | WP19 | P3 | Yes |
| T094 | AM-1/AM-2 refusals | WP19 | P3 | Yes |
| T095 | AM-3 enumerable-not-live + AM-5 cancellation | WP19 | P3 | Yes |
| T096 | AM-4 never automatic | WP19 | P3 | Yes |
| T097 | Four US6 scenario tests (SC-008) | WP19 | P3 | Yes |
| T098 | C-006 register new surface | WP19 | P3 | Yes |
