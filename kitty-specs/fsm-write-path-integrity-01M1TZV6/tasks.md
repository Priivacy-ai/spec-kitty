# Work Packages: FSM Write-Path Integrity

**Inputs**: Design documents from `kitty-specs/fsm-write-path-integrity-01M1TZV6/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/ (emit-pipeline, dependency-guard, write-gates, run-state-store), quickstart.md, decisions/ (10 records)

**Tests**: REQUIRED. The spec is ATDD-first: every WP is anchored on a named RED-on-main repro (SC-001..SC-008) and must ship unit tests for every extracted helper (charter Sonar standing order). Red-first repros are transitional (C-009): after green they are deleted or relocated into functional test homes.

**Organization**: Fine-grained subtasks (`Txxx`) roll up into work packages (`WPxx`). Each work package is independently deliverable and testable.

**Prompt Files**: Each work package references a matching prompt file in `tasks/`. Treat this file as the high-level checklist; the deep guidance is in the prompts.

## Mapping to the spec's indicative slicing

The spec proposed five WPs. The tasks phase keeps their numbering where it can and splits the core:

| Spec slice | Tasks-phase WP | Why |
|---|---|---|
| WP01 serialize out-of-pipeline writers | **WP01** | unchanged |
| WP02 layered pipeline extraction (4–5 days) | **WP02** (pipeline + flat shell) + **WP06** (transactional convergence, aggregate, fan-out, docs) | >10 subtasks; two single-owner file sets (`status/emit.py` + new pipeline vs `coordination/status_transition.py` + `status/aggregate.py`) |
| WP03 facade strip + write gates | **WP03** | unchanged (depends on WP01) |
| WP04 dependency guard | **WP04** | depends on WP06 (both shells must exist to supply the verdict) |
| WP05 run-state hardening | **WP05** | unchanged; **no dependencies; merges FIRST** (decision Q10 rider) |

Spec/dossier references to "A-WP02" mean WP02 + WP06 here. The Q4 ADR-amendment note lives in WP06's design note.

## Subtask Format: `[Txxx] [P?] Description`

- **[P]** = can proceed in parallel (different files/components).
- Subtasks are **reference rows**: record completion with `spec-kitty agent tasks mark-status <Txxx> --status done`. The reduced event log is the only completion authority.

## Path Conventions

Single project: `src/specify_cli/`, `src/runtime/`, `tests/`. All paths repo-root-relative.

---

## Work Package WP05: Run-State Hardening (Priority: P3, sequenced FIRST) 🎯 first merge

**Goal**: `feature-runs.json` keyed by `mission_id`; atomic run-cursor + journal writes; pure progress read; loud missing-state error.
**Independent Test**: SC-006 — slug-collision distinct runs; crash-window cursor recoverable; tracked `status.json` byte-identical after the progress query; missing `state.json` raises a structured error.
**Prompt**: `tasks/WP05-run-state-hardening.md`
**Requirement Refs**: FR-015, FR-016, FR-017, C-003

### Included Subtasks

T026 Red-first: two missions with equal slug and distinct `mission_id` resolve the SAME run today (`runtime_bridge_io.py:618`); assert distinct runs
T027 Rekey `feature-runs.json` lookup by `mission_id`; demote slug to a display field; decide and record the Q9 migration shape + legacy key in `design-notes/WP05-run-state.md`
T028 Loud missing-state: live index entry with absent `state.json` raises a structured error instead of a silent fresh run (`:617-627`)
T029 [P] Atomic `_write_snapshot` (tmp + `os.replace`, the `reducer.materialize` shape) and hardened `_append_event` in `_internal_runtime/engine.py`; crash-window test
T030 [P] `decision.py:373` `materialize` → `materialize_snapshot`; byte-identical `status.json` test; logged (not swallowed) fallback; ledger check (`tests/architectural/test_layer_rules.py`)

### Implementation Notes

- Owned files are exactly the four Mission-B-contended runtime files (interference map). Merge this WP first so Mission B is unblocked early.
- No L1 lock involvement: the run journal is per-run, single-writer.

### Parallel Opportunities

T029 and T030 are independent of T026–T028 (different files).

### Dependencies

None.

### Risks & Mitigations

- R13 Windows `os.replace` semantics → same-directory tmp file, `fsync` before replace, Windows CI runs `tests/runtime/`.
- Ledger: if a lazy `specify_cli` reach is removed, update `_RUNTIME_ALLOWED_SPECIFY_CLI` in the same PR.

---

## Work Package WP01: Serialize the Out-of-Pipeline Writers (Priority: P1)

**Goal**: Every raw writer of `status.events.jsonl` appends under `feature_status_lock` with an atomic primitive; lock key = `feature_dir.name`; finite timeouts on outage-shaped takes.
**Independent Test**: SC-001 (rollback-truncate race survives), SC-006a (lock-key collision), SC-008 (lock-held assertion for every family), NFR-003 timeout tests.
**Prompt**: `tasks/WP01-serialize-out-of-pipeline-writers.md`
**Requirement Refs**: FR-001, FR-002, FR-003, FR-004, NFR-001, NFR-003, C-002, C-003, C-009, C-010

### Included Subtasks

T001 Red-first: raw `_append_retro_lifecycle_event` interleaved inside `BookkeepingTransaction._rollback`'s truncate window (`transaction.py:944`) is destroyed today; assert survival
T002 Harden `retrospective/lifecycle_events.py`: `_append_retro_lifecycle_event` + `_next_lamport` under one `feature_status_lock`, atomic primitive (`append_raw_rows_atomic`), root via `resolve_status_lock_root`
T003 [P] Harden `retrospective/events.py:213` (superseded `run_terminus` path): lock + atomic primitive; keep the "do not add new callers" note
T004 [P] Harden `migration/verdict_provenance_backfill.py:419`: lock around the append
T005 [P] Harden `migration/backfill_runtime_state.py`: ONE lock acquisition covering the `:1497` idempotency read and both appends (`:1533`, `:1535`)
T006 Lock key → `feature_dir.name` (`status/locking.py:57-60` via `resolve_status_lock_root`); lock-key collision + legacy-slug tests
T007 Finite timeouts (FR-003 a/b): merge-path retrospective take via `post_merge/retrospective_terminus.py` passes a finite timeout; structured `FeatureStatusLockTimeoutError` names the holder; any L3-reachable take reuses `_in_queue_status_lock_timeout`
T008 Lock-held assertion test per writer family (all seven + batch door marked xfail until WP02 lands); census comment at `orchestrator_api/commands.py:3568-3570` re-labelled historical; document the three lock rules in `design-notes/WP01-lock-rules.md`

### Implementation Notes

- Pattern = `status/lifecycle_events.py:234-254` (`_lifecycle_write_lock`) generalized; the `nullcontext()` no-git degrade is a conscious per-site choice with a one-line comment.
- Never hold the lock across a git subprocess (NFR-001). None of the four sites spawns git.

### Parallel Opportunities

T003, T004, T005 touch different files and can proceed concurrently after T002 establishes the helper shape.

### Dependencies

None (wave 0; runs in parallel with WP02 and WP05).

### Risks & Mitigations

- R10 repro won't go red as "two concurrent appends" → use the rollback-truncate shape (T001).
- R7 new L1 takers under L5 → finite timeout (T007).

---

## Work Package WP02: Status-Owned Transition Pipeline + Flat Shell (Priority: P1)

**Goal**: Promote `_prepare_event` (`coordination/status_transition.py:842-945`) into `status/transition_pipeline.py` as ONE pure, I/O-parameterized `prepare_transition`; compose the flat/primary shell (`status/emit.py` single + batch) over it; batch door takes the lock; fan-out becomes suppressible for the coord arm.
**Independent Test**: pipeline unit tests with in-memory dirs; `validate_transition` called exactly once per emit; NFR-004 call-count assertion; `test_status_module_boundary.py` green; batch door lock-held.
**Prompt**: `tasks/WP02-transition-pipeline-and-flat-shell.md`
**Requirement Refs**: FR-005, FR-018, NFR-004, C-006, C-009

### Included Subtasks

T009 Create `status/transition_pipeline.py`: `PreparedTransition` + `prepare_transition(...)` per `contracts/emit-pipeline.md` §1 (promoted verbatim; injected I/O; imports nothing from `coordination`)
T010 Pipeline unit tests: alias-collapse arm, gate inference only on `in_progress→for_review`, evidence build, single `validate_transition`, event build, `readiness=None` passthrough
T011 Flat shell: `emit_status_transition` composes the pipeline; add `fan_out: bool = True` (or deferred-callable return) so the coord fallback arm can suppress step-7 fan-out
T012 Batch door `emit_status_transition_batch` (`emit.py:808-960`): acquire `feature_status_lock` once, compose the pipeline per request (FR-018)
T013 NFR-004 pin: `_derive_from_lane` ≤1 call and one full-log read per emit (call-count test); decide + document Q6 (privates landing) in `design-notes/WP02-pipeline.md`
T014 Boundary + invariant pins: pipeline module has zero `coordination` imports (extend `test_status_module_boundary.py` expectations if needed); `test_2093_authority_invariant.py` green (frontmatter `lane` mirror unchanged)

### Implementation Notes

- `_prepare_event` stays in `coordination/status_transition.py` until WP06 deletes it; WP02 must NOT edit that file (single-owner). Behaviour parity is proven by WP06's delegation-equivalence tests.
- Keep the ruff C901 ceiling (15): the flat shell is already `# NOSONAR`; extract helpers rather than growing it.

### Parallel Opportunities

T009+T010 first; T011, T012 in parallel after; T013, T014 last.

### Dependencies

None (wave 0).

### Risks & Mitigations

- R1 shim direction → the pipeline is in `status/`; `coordination` is untouched here.
- Q6 hard constraint: the frontmatter `lane` mirror remains the tree's only `write_frontmatter` of `lane`.

---

## Work Package WP06: Transactional Convergence, Aggregate, Fan-out, Docs (Priority: P1)

**Goal**: The transactional shells (single `:1318`, batch `:1574`, inner-state `:1446`) and `MissionStatus.transition` converge on the pipeline; batch gains owned-mission/`effective_root` parity; coord fallback arm defers fan-out behind commit (phantom fan-out closed); aggregate's duplicate validation deleted; minimal doc hunks; Q4 ADR-amendment note.
**Independent Test**: SC-002 (zero fan-out for a truncated event), SC-003 (batch owned-mission refusal), SC-007 (no-new-commits plain door), US2-4 (validation exactly once), the #3460/#1848 pins green.
**Prompt**: `tasks/WP06-transactional-convergence.md`
**Requirement Refs**: FR-006, FR-007, FR-008, FR-009, C-001, C-007, C-008, NFR-005

### Included Subtasks

T031 Red-first: coord-topology mission, fallback arm, commit forced to fail ⇒ SaaS/zeitgeist fan-out recorded today (`emit.py:794` pre-commit); assert zero
T032 Red-first: owned-mission (`effective_root`) request via the transactional batch door silently skips the `ActionContextError` refusal (`:1594+` vs `:1342-1345`); plus the immediate-vs-deferred fan-out ordering pin
T033 Pin (green on main, stays green): stored-`LANES` mission through the plain door gains no commits and spawns no identity git subprocess (C-008)
T034 Single transactional door composes `prepare_transition`; delete `_prepare_event`
T035 Batch transactional door: parity (owned-mission check + `effective_root` acquisition) + pipeline; inner-state door composes the pipeline where it validates
T036 Coord fallback arm (`_fallback_emit_single._coord` / `_fallback_emit_batch`): call the flat shell with fan-out suppressed, commit, then fan out; on failure truncate-restore and no fan-out
T037 `MissionStatus.transition` (`aggregate.py:605-698`): delete the pre-duplicated derive/gate/validate; compose over the transactional shell; validation runs once
T038 Docs: minimal stale-sentence hunks (CLAUDE.md status section "single entry point"; `docs/architecture/status-model.md:393`); Q4 ADR-amendment paragraph in `design-notes/WP06-convergence.md`; terminology guard
T039 C-009 swap: divergence pins (T032) replaced by delegation-equivalence tests; #3460 / #1848 / move-task pins green; blast radius recorded

### Implementation Notes

- The three failure policies stay explicit per shell/arm (C-007). Do not merge them into the pipeline.
- Doc hunks are the minimal stale-sentence correction only; Mission C owns final text (FR-009).

### Parallel Opportunities

T031–T033 (pins) can be written in parallel before T034.

### Dependencies

Depends on WP02 (the pipeline and the fan-out suppression seam must exist).

### Risks & Mitigations

- R2 plain-door callers gain commits → T033 pin.
- R3 phantom fan-out → T031 + T036.
- R12 doc contention → minimal hunks only.

---

## Work Package WP03: Facade Strip + Write Gates (Priority: P2)

**Goal**: `append_event*` exports move to `status/_unsafe.py` behind a shrink-only caller allowlist; an AST writes-gate rejects any out-of-pipeline write to `status.events.jsonl`; both gates carry non-vacuity floors.
**Independent Test**: SC-004 — a synthetic out-of-pipeline writer reds the gate; a zero-match scan reds the gate; allowlist growth is refused.
**Prompt**: `tasks/WP03-facade-strip-and-write-gates.md`
**Requirement Refs**: FR-010, FR-011

### Included Subtasks

T015 Create `status/_unsafe.py` re-exporting the six `append_event*` store primitives; declare `ALLOWED_CALLERS` seeded from WP01's fixed census
T016 Remove the six names from `status/__init__.__all__` (`:518-537`); repoint every census importer to `specify_cli.status._unsafe`
T017 [P] `tests/architectural/test_status_unsafe_allowlist.py`: AST scan of `src/` for `_unsafe` importers ⊆ `ALLOWED_CALLERS` ⊆ committed BASELINE; shrink-only; non-vacuity floor (synthetic disallowed importer reds; stale allowlist entry reds)
T018 [P] `tests/architectural/test_status_events_writes_gate.py`: AST writes-gate per `contracts/write-gates.md` §2 with positive census + non-vacuity floor; `feature_status_lock` composition-site census (R14)
T019 Draft the census-gate-rule note for #3895 in `design-notes/WP03-gates.md` (operator posts); C-009 cleanup

### Implementation Notes

- Seed the allowlist from the census as it stands after WP01 (families ②③⑤⑥⑦, `status/emit.py`, `coordination/status_transition.py` if it imports `_unsafe`).

### Parallel Opportunities

T017 and T018 are independent gate files.

### Dependencies

Depends on WP01 (fixed census).

### Risks & Mitigations

- Vacuous gate (report 27 §3.3) → floors are mandatory in the same PR.

---

## Work Package WP04: Dependency Readiness Guard (Priority: P2)

**Goal**: `GuardContext.dependency_ready: bool | None` (fail-open on `None`), enforced on `planned→claimed` / `claimed→in_progress`; both shells resolve readiness in-lock against their write surface; the six pre-flight sites demoted to UX.
**Independent Test**: SC-005 — verdict-less shell emit claiming a dep-blocked WP is refused; probe sites pass with `None`; force + chain matrix; replay purity.
**Prompt**: `tasks/WP04-dependency-readiness-guard.md`
**Requirement Refs**: FR-012, FR-013, FR-014, NFR-002, C-004, C-005

### Included Subtasks

T020 Red-first: verdict-less emit through a shell, `planned→claimed`, dependency `in_progress` ⇒ succeeds today; assert refusal after
T021 `GuardContext.dependency_ready` field (`status/models.py:885`) + one guard clause in `status/wp_state.py` on the two entry edges, fail-open on `None`
T022 Shells supply the verdict in-lock against their write surface (`status/emit.py` flat shell; `coordination/status_transition.py` transactional shells) — declared out-of-map leeway, one-line rationale each
T023 Pipeline threads `readiness` into the `GuardContext` build (`status/transition_pipeline.py`, out-of-map leeway)
T024 Tests: probe-site `None` pins (`lanes/recovery.py:78`, `agent/tasks_transition_core.py:337`); force + same-mission chain matrix; coord-surface resolution; replay purity (`reducer.py` zero guard refs; audit ignores guards)
T025 Demote the six pre-flight sites (re-comment as UX; no logic change); `implement` no-op-resume pin; record polarity rationale in `design-notes/WP04-guard.md`

### Implementation Notes

- Reuse `dependency_readiness_for_wp` (`core/dependency_graph.py:34`) verbatim. No edge/force/terminal changes (non-goal 6).

### Parallel Opportunities

T024 test authoring can start alongside T021.

### Dependencies

Depends on WP06 (which depends on WP02): both shells must exist. Also depends on WP03 (analysis finding I2): the fail-open-on-`None` polarity is sound only once the write gates guarantee no durable write bypasses the shells.

### Risks & Mitigations

- R4 fail-closed breaks probes → T024 pins; R5 wrong surface/pre-lock → T022 + coord-surface test.

---

## Work Package WP07: Writer Census Addendum (Priority: P2, minted during implementation)

**Goal**: Harden the two out-of-pipeline writers WP03's AST writes-gate found that the dossier census (FR-001, families ①–⑦) missed: `decisions/emit.py:100-112` (raw unlocked append of `DecisionPointOpened` rows) and `migration/rebuild_state.py:758-766` (unlocked whole-log rewrite). SC-008 ("0 unlocked writer families") requires it.
**Independent Test**: rollback-truncate race for `decisions/emit.py` RED before / GREEN after; both gates green with the FINDING labels removed; nine-family lock-held test green.
**Prompt**: `tasks/WP07-writer-census-addendum.md`
**Requirement Refs**: FR-001, FR-002, NFR-001

### Included Subtasks

T040 Harden `decisions/emit.py` `_append_raw_event`: lock + `append_raw_rows_atomic` via `_unsafe`; ALLOWED_CALLERS/BASELINE +1; FINDING ledger entry removed; RED-first race test
T041 [P] Lock the `rebuild_state.py` whole-log rewrite; relabel its gate ledger entry; interleaving test
T042 Census addendum (families ⑧/⑨) in the lock-held parametrized test + design-note addendum (scratch → orchestrator lands)

### Dependencies

Depends on WP03 (the `_unsafe` door and both gates).

### Risks & Mitigations

- Same as WP01 (re-entrancy, NFR-001); both regions must not spawn git under the lock.

---

## Dependency & Execution Summary

- **Sequence**: wave 0 = WP05 ∥ WP01 ∥ WP02; wave 1 = WP06 (after WP02) ∥ WP03 (after WP01); wave 2 = WP04 (after WP03 and WP06) ∥ WP07 (after WP03; minted mid-implementation from WP03's gate findings).
- **Merge order**: WP05 first (frees Mission B's four files); then **WP01 before WP02** (WP01 T006 carries the one-line lock-key hunks in `status/emit.py:634` and `coordination/transaction.py:290`; WP02 rebases over them — analysis finding I3); then WP03/WP06; then WP04.
- **Parallelization**: three independent lanes in wave 0 with disjoint owned files.
- **MVP Scope**: WP01 + WP02 + WP06 close the two P1 stories (SC-001, SC-002, SC-003, SC-007, SC-008). WP03 makes them durable; WP04 and WP05 close P2/P3.

---

## Requirements Coverage Summary

| Requirement ID | Covered By Work Package(s) |
|----------------|----------------------------|
| FR-001 | WP01, WP07 |
| FR-002 | WP01, WP07 |
| FR-003 | WP01 |
| FR-004 | WP01 |
| FR-005 | WP02 |
| FR-006 | WP06 |
| FR-007 | WP06 |
| FR-008 | WP06 |
| FR-009 | WP06 |
| FR-010 | WP03 |
| FR-011 | WP03 |
| FR-012 | WP04 |
| FR-013 | WP04 |
| FR-014 | WP04 |
| FR-015 | WP05 |
| FR-016 | WP05 |
| FR-017 | WP05 |
| FR-018 | WP02 |
| NFR-001 | WP01, WP07 |
| NFR-002 | WP04 |
| NFR-003 | WP01 |
| NFR-004 | WP02 |
| NFR-005 | WP06 |
| C-001 | WP06 |
| C-002 | WP01 |
| C-003 | WP01, WP05 |
| C-004 | WP04 |
| C-005 | WP04 |
| C-006 | WP02 |
| C-007 | WP06 |
| C-008 | WP06 |
| C-009 | WP01, WP02 |
| C-010 | WP01 |

---

## Subtask Index (Reference)

| Subtask ID | Summary | Work Package | Priority | Parallel? |
|------------|---------|--------------|----------|-----------|
| T001 | Red-first rollback-truncate race | WP01 | P1 | No |
| T002 | Harden retrospective lifecycle writer | WP01 | P1 | No |
| T003 | Harden retrospective events writer | WP01 | P1 | Yes |
| T004 | Harden verdict-provenance backfill | WP01 | P1 | Yes |
| T005 | Harden runtime-state backfill (one lock) | WP01 | P1 | Yes |
| T006 | Lock key → feature_dir.name | WP01 | P1 | No |
| T007 | Finite timeouts on outage-shaped takes | WP01 | P1 | No |
| T008 | Lock-held assertions + lock-rules note | WP01 | P1 | No |
| T009 | Create transition_pipeline.py | WP02 | P1 | No |
| T010 | Pipeline unit tests | WP02 | P1 | No |
| T011 | Flat shell composes pipeline + fan_out seam | WP02 | P1 | Yes |
| T012 | Batch door takes lock + pipeline | WP02 | P1 | Yes |
| T013 | NFR-004 call-count pin; Q6 note | WP02 | P1 | No |
| T014 | Boundary + 2093 invariant pins | WP02 | P1 | No |
| T015 | Create status/_unsafe.py + allowlist | WP03 | P2 | No |
| T016 | Strip facade exports; repoint importers | WP03 | P2 | No |
| T017 | Allowlist gate + floor | WP03 | P2 | Yes |
| T018 | AST writes-gate + floor | WP03 | P2 | Yes |
| T019 | #3895 note draft; C-009 cleanup | WP03 | P2 | No |
| T020 | Red-first dep-blocked claim succeeds | WP04 | P2 | No |
| T021 | GuardContext field + guard clause | WP04 | P2 | No |
| T022 | Shells resolve readiness in-lock | WP04 | P2 | No |
| T023 | Pipeline threads readiness | WP04 | P2 | No |
| T024 | Probe/force/chain/replay tests | WP04 | P2 | Yes |
| T025 | Demote pre-flight sites; polarity note | WP04 | P2 | No |
| T026 | Red-first slug-collision same run | WP05 | P3 | No |
| T027 | Rekey index by mission_id; Q9 note | WP05 | P3 | No |
| T028 | Loud missing-state error | WP05 | P3 | No |
| T029 | Atomic cursor + journal writes | WP05 | P3 | Yes |
| T030 | Pure progress read; ledger check | WP05 | P3 | Yes |
| T031 | Red-first phantom fan-out | WP06 | P1 | Yes |
| T032 | Red-first batch parity + ordering pins | WP06 | P1 | Yes |
| T033 | No-new-commits plain-door pin | WP06 | P1 | Yes |
| T034 | Single txn door composes pipeline | WP06 | P1 | No |
| T035 | Batch txn parity + inner-state | WP06 | P1 | No |
| T036 | Coord arm deferred fan-out | WP06 | P1 | No |
| T037 | Aggregate de-duplication | WP06 | P1 | No |
| T038 | Doc hunks + ADR amendment note | WP06 | P1 | No |
| T039 | C-009 swap; pins green; blast radius | WP06 | P1 | No |
| T040 | Harden decisions/emit.py writer | WP07 | P2 | No |
| T041 | Lock rebuild_state.py rewrite | WP07 | P2 | Yes |
| T042 | Census addendum rows + note | WP07 | P2 | No |
