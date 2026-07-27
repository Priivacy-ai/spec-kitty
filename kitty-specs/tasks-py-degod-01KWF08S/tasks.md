---
description: "Work packages — Degod tasks.py (Wave 1): thin CLI over pure cores behind injected ports"
---

# Work Packages: Degod tasks.py — thin CLI over pure cores (Wave 1)

**Inputs**: Design documents from `kitty-specs/tasks-py-degod-01KWF08S/`
**Prerequisites**: plan.md (required), spec.md, research.md (D1–D10), data-model.md, contracts/ports-and-cores.md, quickstart.md

**Tests**: Explicitly required (NFR-001 golden parity guard + NFR-002 per-core `--cov-branch` tests are the mission's spine).

**Organization**: 9 **strictly-linear** work packages (`WP01→…→WP09`); one dependency chain → one execution lane per WP, edits stack sequentially. Behavior-preserving (pure-parity): the golden characterization (WP01) is frozen and every WP keeps it byte-identical. Post-4-lens-squad shape: WP07 (body-thinning) split into a **core-backed** slice (WP07) and a **coreless** slice (WP08); render+shim+census is WP09.

**Ownership model (mission.py-degod template)**: each WP owns the **new** modules/tests it creates; the god-file `src/specify_cli/cli/commands/agent/tasks.py` is authoritatively owned **only by the shim WP (WP09)**. The rewire WPs (WP03–WP08) edit `tasks.py` under **documented leeway** (disjoint command bodies, sequential — no parallel collision).

## Path Conventions

- Source: `src/specify_cli/cli/commands/agent/`
- Tests: `tests/specify_cli/cli/commands/agent/`, `tests/architectural/`

---

## Work Package WP01: Golden CLI-characterization harness (Priority: P0)

**Goal**: Freeze the full observable `agent tasks` contract — **every** `move_task` decision branch, not just skip/refuse — before any extraction, gated by a from-harness branch-coverage measurement.
**Independent Test**: The golden harness is green against the mission base, exercises all 9 subcommands + the coord-topology fixture + every named guard arm, and reverting it is the only way it fails.
**Prompt**: `/tasks/WP01-golden-cli-characterization.md`
**Requirement Refs**: FR-001, C-004, NFR-001

### Included Subtasks

- [x] T001 Assert the 9-command set + per-command flag/option surface via `CliRunner --help` introspection (extend `test_tasks_cli_contract.py`) (WP01)
- [x] T002 Freeze per-command exit codes {0,1,2} + `--json` top-level key sets for all 9 subcommands (human + json) (WP01)
- [x] T003 Build the coord-topology + protected-branch fixture class (real on-disk coord-worktree state) (WP01)
- [x] T004 Freeze the `move_task` skip-exit-0 arm with **distinguishing** evidence: primary HEAD unchanged + coord event emitted + conditional `--json` keys (`wp_file_update`/`status_events_path`) — NOT exit-0 + key-presence alone (WP01)
- [x] T005 Freeze `mark_status`/`map_requirements` refuse-exit-1 arms under the same fixture (current behavior; inconsistency deferred #2300) (WP01)
- [x] T006 Freeze **every other named `move_task` decision branch** — arbiter-override, rejected-verdict, planning-artifact-WP arm, review-currency, for_review→in_progress force — as explicit cases (WP01)
- [x] T007 Freeze the no-stdout side-effect set (coord-vs-primary emission, WP-file writes, tracker-ref frontmatter, review-artifact override to both dirs) + add a **from-harness branch-coverage gate** on `move_task`/`status`/`map_requirements` ≥ stated threshold (WP01)

### Dependencies

- None (must be first — C-004).

### Risks & Mitigations

- The skip arm + refuse arms + the other move_task branches are NOT covered by the existing harness (docstring punts them). A non-skip success also exits 0 → T004 must assert primary HEAD unchanged, not exit-0. Missing any branch (T006) means WP03 extracts it unguarded.

---

## Work Package WP02: TasksPorts co-design (stratified, two-capability WRITE) (Priority: P0)

**Goal**: Define the injected capability boundary — stratified, with a **two-capability** coord WRITE port so Wave 2 reuses it — plus the FR-010 dir-equivalence proof.
**Independent Test**: Ports resolve with Fakes injected; the stratification invariants hold; the Typer command exposes no `--ports` flag; the per-kind coord-fixture equivalence test is green.
**Prompt**: `/tasks/WP02-tasks-ports-codesign.md`
**Requirement Refs**: FR-003, FR-009, FR-010, C-001, C-002, C-005

### Included Subtasks

- [x] T008 Define the 4 Protocols in `tasks_ports.py` — `FsReader` (coord READ); `CoordCommitRouter` with **two methods** `commit_status`(over the transactional emitter, `GuardCapability`) + `commit_artifact`(over `commit_for_mission`, `MissionArtifactKind`+policy, event-less); `GitOps`; `Render` (dual-arm) (WP02)
- [x] T009 Implement Real adapters (FsReader wraps `resolve_planning_read_dir` + the primitive & `_canonicalize_primary_read_handle` fold **co-located**; CoordCommitRouter over `emit_status_transition_transactional` + `commit_for_mission`; result types named off `CommitResult` to avoid the `git/commit_helpers.py` collision) (WP02)
- [x] T010 [P] Implement Fake adapters for all 4 (in-memory, deterministic) (WP02)
- [x] T011 Define the `TasksPorts` bundle + `default_ports()`; registration-introspection test proving `_do_<cmd>(*, ports=None)` and **no** `--ports` Typer flag (C-005) (WP02)
- [x] T012 Unit-test stratification invariants: FsReader≠CoordCommitRouter (INV-1/C-001), `commit_status`/`commit_artifact` are co-equal methods over disjoint seams, canonicalizer fold intra-adapter (C-002), exactly 4 ports (WP02)
- [x] T013 **FR-010 dir-equivalence proof artifact**: for each in-scope `MissionArtifactKind` on the coord fixture, assert `resolve_feature_dir_for_mission == resolve_planning_read_dir(kind=…)` for the pre30 guard (delivered here, before any read fold) (WP02)

### Dependencies

- Depends on WP01. (#2072 predecessor already landed — allowlist composite-keyed.)

### Risks & Mitigations

- A fused single `commit()` mis-shapes the program (Wave-2 consumers use disjoint halves). Keep two capabilities. Splitting the canonicalizer fold across the port boundary turns the C-002 gate RED.

---

## Work Package WP03: move_task transition decision core (pure) (Priority: P0)

**Goal**: Lift `move_task`'s transition decision into one pure function reproducing exact behavior; wire it by **deleting** the inline block + a sentinel test proving it drives behavior.
**Independent Test**: `test_tasks_transition_core.py` (`--cov-branch` gated) covers every `TransitionOutcome` branch from the WP01 harness; the sentinel test flips observable output when the core's outcome is perturbed; golden byte-identical.
**Prompt**: `/tasks/WP03-move-task-transition-core.md`
**Requirement Refs**: FR-004, FR-002, NFR-002, C-003

### Included Subtasks

- [x] T014 Author the failing-first (RED-on-base) per-branch unit test enumerating `TransitionOutcome` branches from the WP01 harness (Emit/SkipExit0/RefuseExit1 + every guard) — `--cov-branch` on the module (WP03)
- [x] T015 Implement `decide_transition(TransitionRequest)->TransitionOutcome` in `tasks_transition_core.py` — PURE; reproduce exact behavior (WP03)
- [x] T016 Wire `move_task`: **delete** the inline decision block and route through `decide_transition` (execution stays inline; the old logic is gone, not shadowed) (WP03)
- [x] T017 Add a **fake-core sentinel test**: injecting a sentinel outcome flips the command's observable result (proves the core drives behavior, not merely called); golden byte-identical (WP03)

### Dependencies

- Depends on WP02.

### Risks & Mitigations

- "grep-for-callers" is insufficient — a result-discarding call passes it while old inline logic runs. T016 deletes the block; T017 proves drive. Ambiguous selectors must raise `MissionSelectorAmbiguous` (C-003).

---

## Work Package WP04: Requirement-mapping decision core (pure) (Priority: P1)

**Goal**: Extract `map_requirements`' FR↔WP mapping/validation into a pure decision, separated from the frontmatter write; wire by delete-and-sentinel.
**Independent Test**: `test_tasks_mapping_core.py` (`--cov-branch`) covers offenders/unmapped/modes; sentinel test proves drive; golden byte-identical.
**Prompt**: `/tasks/WP04-requirement-mapping-core.md`
**Requirement Refs**: FR-005, FR-002, NFR-002

### Included Subtasks

- [x] T018 Failing-first per-branch unit test for `plan_mapping` (offenders: malformed/unknown_spec_id, unmapped_fr, modes wp_refs/batch/tracker/replace) — `--cov-branch` (WP04)
- [x] T019 Implement `plan_mapping(MappingRequest)->MappingPlan` in `tasks_mapping_core.py` — pure; consumes injected reads; no frontmatter write (WP04)
- [x] T020 Wire `map_requirements`: **delete** the inline mapping block, route through `plan_mapping` (write applied via port) (WP04)
- [x] T021 Fake-core sentinel test proves drive + golden byte-identical (WP04)

### Dependencies

- Depends on WP03.

### Risks & Mitigations

- Leaking the frontmatter write into the core breaks purity (INV-4) — return the plan, orchestrator applies it.

---

## Work Package WP05: status aggregation core (pure) (Priority: P1)

**Goal**: Extract the `status` compute/aggregation into a pure core, separated from rendering; wire by delete-and-sentinel.
**Independent Test**: `test_tasks_status_view.py` (`--cov-branch`) covers each aggregation branch; sentinel proves drive; golden byte-identical.
**Prompt**: `/tasks/WP05-status-aggregation-core.md`
**Requirement Refs**: FR-006, FR-002, NFR-002

### Included Subtasks

- [x] T022 Failing-first per-branch unit test for `build_status_view` (stale-fallback, dependency_readiness, kanban rollup, progress) — `--cov-branch` (WP05)
- [x] T023 Implement `build_status_view(StatusRequest)->StatusView` in `tasks_status_view.py` — pure aggregation; no rendering/I/O (WP05)
- [x] T024 Wire `status`: **delete** the inline aggregation block, route through `build_status_view` (rendering stays inline) (WP05)
- [x] T025 Fake-core sentinel test proves drive + golden byte-identical (WP05)

### Dependencies

- Depends on WP04.

### Risks & Mitigations

- Keep `StatusView` a pure data structure the Render port later draws.

---

## Work Package WP06: move_task thin-orchestrator rewire + read fold (Priority: P0)

**Goal**: Reduce `move_task` to ≤150 LOC over its core + ports, migrate its read to the kind-aware authority (pinned kind).
**Independent Test**: `move_task` ≤150 LOC; golden byte-identical incl. skip-exit-0; the read migration resolves the same dir (per the WP02 equivalence proof).
**Prompt**: `/tasks/WP06-move-task-orchestrator-rewire.md`
**Requirement Refs**: FR-007, FR-010, C-001, C-002, NFR-004

### Included Subtasks

- [x] T026 Route `move_task`'s execution (event via `commit_status`, coord-vs-primary write via `commit_artifact`, WP-file writes) through ports; body ≤150 LOC (WP06)
- [x] T027 Migrate `move_task:1138` kind-blind read → `resolve_planning_read_dir` via `FsReader` with the **pinned kind** (per WP02 proof); byte-identical (WP06)
- [x] T028 Extract glue helpers ≤150 LOC/CC≤15; ruff+mypy clean (WP06)
- [x] T029 Golden byte-identical (incl. skip-exit-0 arm) + `move_task` orchestration test green (WP06)

### Dependencies

- Depends on WP05.

### Risks & Mitigations

- Preserve the `skip_target_branch_commit` fall-through control shape through the `commit_status` routing (the skip arm carries `.skipped`), or the golden breaks.

---

## Work Package WP07: Core-backed rewire — map_requirements + status (Priority: P0)

**Goal**: Thin the two **core-backed** bodies to ≤150 LOC orchestrators over the WP04/WP05 cores + ports.
**Independent Test**: both bodies ≤150 LOC; golden byte-identical for each.
**Prompt**: `/tasks/WP07-core-backed-rewire.md`
**Requirement Refs**: FR-007, NFR-004

### Included Subtasks

- [x] T030 Thin `map_requirements` to a thin orchestrator over the WP04 `plan_mapping` core + ports (write via port); ≤150 LOC (WP07)
- [x] T031 Thin `status` to a thin orchestrator over the WP05 `build_status_view` core + the `Render` port; ≤150 LOC (WP07)
- [x] T032 Golden byte-identical for both + orchestration test green; ruff+mypy clean (WP07)

### Dependencies

- Depends on WP06.

### Risks & Mitigations

- `status`'s Render migration here must be scoped so WP09's render sweep doesn't re-conflict it.

---

## Work Package WP08: Coreless rewire — mark_status + finalize_tasks + read folds (Priority: P0)

**Goal**: Thin the two **coreless** bodies via ports + existing seam modules (no borrowed core), migrate the remaining reads, and add a structural non-import gate.
**Independent Test**: both bodies ≤150 LOC; golden byte-identical; the non-import AST gate is green; read migrations resolve same dirs.
**Prompt**: `/tasks/WP08-coreless-rewire.md`
**Requirement Refs**: FR-007, FR-010, NFR-004

### Included Subtasks

- [x] T033 Thin `mark_status` via ports + existing `tasks_finalize_validation`/parsing seams (coreless — no borrowed core); ≤150 LOC (WP08)
- [x] T034 Thin `finalize_tasks` via ports + existing seams; ≤150 LOC (WP08)
- [x] T035 Migrate `finalize_tasks:2373` + `list_dependents:3568` kind-blind reads → `resolve_planning_read_dir` via `FsReader` (pinned kinds per WP02 proof); byte-identical (WP08)
- [x] T036 Add a **structural non-import AST gate**: `tasks_transition_core` is NOT reachable from the `mark_status`/`finalize_tasks` code paths (guards the deferred-unification boundary structurally); golden byte-identical + orchestration test green (WP08)

### Dependencies

- Depends on WP07.

### Risks & Mitigations

- Borrowing `move_task`'s core to hit ≤150 LOC changes their refuse-exit-1 behavior (#2300) — the AST gate (T036) catches it structurally, not just behaviorally.

---

## Work Package WP09: Resolution-authority census cleanup (shrink-only) (Priority: P0)

**Goal**: (SLIMMED — Render seam + ≤1400 shim relocation DEFERRED to a follow-up mission.) Drain the coord-authority census debt the WP01–WP08 rewires created so the arch gates are green.
**Independent Test**: the 4 currently-red gate tests go green; `COORD_AUTHORITY_WRITE_FLOOR` lowered 12→9 (shrink-only); 5 stale allowlist entries re-pinned/drained with an enumerated cross-base artifact + margin gate; full `tests/architectural/` cross-base sweep (only documented pre-existing failures remain).
**Prompt**: `/tasks/WP09-render-seam-shim-census.md`
**Requirement Refs**: FR-011, NFR-005, C-002

### Included Subtasks

- [ ] T037 Census drain + floor-lower + baseline + margin gate: re-measure live WRITE census (9); re-pin moved entries / drain removed ones (`list_dependents:3568`, `list_tasks:2198`, `move_task:1138/1396`, `validate_workflow:2995`); lower `COORD_AUTHORITY_WRITE_FLOOR` 12→9 shrink-only; fix stale `coord_authority_baseline`; enumerated cross-base drain artifact for reviewer sign-off (WP09)
- [ ] T038 Assert the C-002 canonicalizer gate stays non-vacuous; 0 new arch-ratchet entries (shrink-only holds) (WP09)
- [ ] T039 Run the full `tests/architectural/` sweep + mission-base-vs-lane-base cross-diff; the 4 named gate tests green; report (do NOT fix) any identical-on-base pre-existing failures for a DIR-013 follow-up (WP09)

### Dependencies

- Depends on WP08.

### Risks & Mitigations

- The floor gate is a lower-bound owned by this WP → over-lowering is self-attestable. The enumerated cross-base artifact + reviewer sign-off + margin gate are the guard. Never ADD an allowlist entry to pass a gate. **Do NOT touch `tasks.py`** — the render/shim relocation is the follow-up mission's.

---

## Dependency & Execution Summary

- **Sequence (strictly linear)**: WP01 → WP02 → WP03 → WP04 → WP05 → WP06 → WP07 → WP08 → WP09.
- **Parallelization**: none — one lane per WP by design (shared `tasks.py` rewire surface).
- **MVP / spine**: WP01 (safety net) + WP02 (ports + FR-010 proof) + WP03 (highest-value core); WP09 is the closeout gate.

---

## Requirements Coverage Summary

| Requirement ID | Covered By Work Package(s) |
|----------------|----------------------------|
| FR-001 | WP01 |
| FR-002 | WP03, WP04, WP05 |
| FR-003 | WP02 |
| FR-004 | WP03 |
| FR-005 | WP04 |
| FR-006 | WP05 |
| FR-007 | WP06, WP07, WP08 |
| FR-009 | WP02 |
| FR-010 | WP02 (proof), WP06, WP08 |
| FR-011 | WP09 |
| NFR-001 | WP01 (guard re-run every WP) |
| NFR-002 | WP03, WP04, WP05 |
| NFR-003 | every WP local (strict mypy on src) |
| NFR-004 | WP06, WP07, WP08 (per-body/helper ≤150 met; whole-file ≤1400 shim DEFERRED) |
| NFR-005 | WP09 |
| C-001 | WP02, WP06 |
| C-002 | WP02, WP09 |
| C-003 | WP03 |
| C-004 | WP01 |
| C-005 | WP02 |

---

## Subtask Index (Reference)

| Subtask ID | Summary | Work Package | Priority | Parallel? |
|------------|---------|--------------|----------|-----------|
| T001 | 9-command + flag surface | WP01 | P0 | No |
| T002 | Exit codes + `--json` keys | WP01 | P0 | No |
| T003 | Coord-topology fixture | WP01 | P0 | No |
| T004 | Skip-exit-0 distinguishing freeze | WP01 | P0 | No |
| T005 | Refuse-exit-1 freeze | WP01 | P0 | No |
| T006 | Freeze other move_task branches | WP01 | P0 | No |
| T007 | Side-effects + branch-cov gate | WP01 | P0 | No |
| T008 | Define 4 ports (2-capability WRITE) | WP02 | P0 | No |
| T009 | Real adapters | WP02 | P0 | No |
| T010 | Fake adapters | WP02 | P0 | Yes |
| T011 | Bundle + injection test | WP02 | P0 | No |
| T012 | Stratification invariants | WP02 | P0 | No |
| T013 | FR-010 dir-equivalence proof | WP02 | P0 | No |
| T014 | RED-first transition test | WP03 | P0 | No |
| T015 | `decide_transition` core | WP03 | P0 | No |
| T016 | Delete inline + wire | WP03 | P0 | No |
| T017 | Fake-core sentinel test | WP03 | P0 | No |
| T018 | RED-first mapping test | WP04 | P1 | No |
| T019 | `plan_mapping` core | WP04 | P1 | No |
| T020 | Delete inline + wire | WP04 | P1 | No |
| T021 | Sentinel test | WP04 | P1 | No |
| T022 | RED-first status test | WP05 | P1 | No |
| T023 | `build_status_view` core | WP05 | P1 | No |
| T024 | Delete inline + wire | WP05 | P1 | No |
| T025 | Sentinel test | WP05 | P1 | No |
| T026 | Route move_task via ports | WP06 | P0 | No |
| T027 | move_task read fold (pinned kind) | WP06 | P0 | No |
| T028 | Glue helper ≤150 | WP06 | P0 | No |
| T029 | Golden + integration green | WP06 | P0 | No |
| T030 | Thin map_requirements | WP07 | P0 | No |
| T031 | Thin status | WP07 | P0 | No |
| T032 | Golden + integration green | WP07 | P0 | No |
| T033 | Thin mark_status (coreless) | WP08 | P0 | No |
| T034 | Thin finalize_tasks (coreless) | WP08 | P0 | No |
| T035 | finalize/list_dependents read folds | WP08 | P0 | No |
| T036 | Non-import AST gate + green | WP08 | P0 | No |
| T037 | Census drain + floor-lower 12→9 + baseline + margin gate | WP09 | P0 | No |
| T038 | Non-vacuity assert | WP09 | P0 | No |
| T039 | Full arch cross-base sweep (4 gates green) | WP09 | P0 | No |
