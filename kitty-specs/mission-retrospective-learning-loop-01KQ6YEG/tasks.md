# Tasks: Mission Retrospective Learning Loop

**Mission**: `01KQ6YEGT4YBZ3GZF7X680KQ3V` (mid8: `01KQ6YEG`)
**Spec**: [./spec.md](./spec.md) · **Plan**: [./plan.md](./plan.md) · **Quickstart**: [./quickstart.md](./quickstart.md)
**Branch contract**: planning base `main` → final merge `main` (matches target ✅)
**Date**: 2026-04-27

---

## Subtask Index

| ID | Description | WP | Parallel |
|---|---|---|---|
| T001 | Define `profile:retrospective-facilitator` shipped artifact | WP01 |  | [D] | [D] |
| T002 | Define `action:retrospect` shipped artifact + scope edges | WP01 |  | [D] |
| T003 | Wire DRG context (event stream, mission meta, charter, glossary, etc.) onto the retrospect action | WP01 |  | [D] |
| T004 | DRG resolver + fixture mission test that confirms structured response | WP01 |  | [D] |
| T005 | Pydantic schema models for `RetrospectiveRecord`, `Finding`, `Proposal`, `Mode`, `RecordProvenance`, `RetrospectiveFailure` | WP02 | [D] |
| T006 | Atomic round-trip writer (`writer.py`): tempfile + `os.replace`, schema validation upstream | WP02 |  | [D] |
| T007 | Schema-validating reader (`reader.py`) with structured-error result type | WP02 |  | [D] |
| T008 | Required vs. optional + status-conditional cross-field validation | WP02 |  | [D] |
| T009 | Tests: schema round-trip; writer atomicity; reader malformed/missing/legacy tolerance | WP02 |  | [D] |
| T010 | Pydantic event models for the eight retrospective events (`events.py`) | WP03 | [D] |
| T011 | Event factory + emission helpers wired through `specify_cli.status.emit` (or sibling) | WP03 |  | [D] |
| T012 | Reducer integration: surface `RetrospectiveSnapshot` on `StatusSnapshot` | WP03 |  | [D] |
| T013 | Tests: append-only invariant, retry semantics, name uniqueness vs. existing events | WP03 |  | [D] |
| T014 | Boundary test (skipped, pending upstream `spec_kitty_events` release) | WP03 |  | [D] |
| T015 | `Mode` + `ModeSourceSignal` Pydantic models | WP04 | [D] |
| T016 | `mode.detect()` precedence (charter > flag > env > parent) implementation | WP04 |  | [D] |
| T017 | Charter-override loader integration + structured-error on missing meta/charter | WP04 |  | [D] |
| T018 | Parent-process heuristic w/ conservative non-interactive list | WP04 |  | [D] |
| T019 | Tests: each precedence layer + ambiguous resolution + audit recording | WP04 |  | [D] |
| T020 | `gate.is_completion_allowed()` API + `GateDecision`/`GateReason` shapes | WP05 |  | [D] |
| T021 | Decision matrix (8 rows from `contracts/gate_api.md`) | WP05 |  | [D] |
| T022 | Charter-clause resolution for autonomous-skip override path | WP05 |  | [D] |
| T023 | Operational predicates for "silent auto-run" and "silent skip" | WP05 |  | [D] |
| T024 | Thin caller in `next/_internal_runtime/retrospective_hook.py` | WP05 |  | [D] |
| T025 | Tests: every decision-matrix row + determinism replay | WP05 |  | [D] |
| T026 | Lifecycle terminus hook in `next` (built-in mission flow) | WP06 |  | [D] |
| T027 | HiC offer/skip prompt UX in `next` | WP06 |  | [D] |
| T028 | Autonomous auto-invocation path | WP06 |  | [D] |
| T029 | Compatibility check for custom mission's required `retrospective` marker step | WP06 |  | [D] |
| T030 | Tests: lifecycle hook integration + custom-mission marker compat regression | WP06 |  | [D] |
| T031 | `apply_proposals()` API skeleton in `doctrine.synthesizer.apply` | WP07 |  | [D] |
| T032 | Conflict detection per R-006 predicates (`conflict.py`) | WP07 |  | [D] |
| T033 | Staleness check (evidence event reachability) | WP07 |  | [D] |
| T034 | Provenance sidecar writer (`provenance.py`) | WP07 |  | [D] |
| T035 | Idempotency via provenance presence check | WP07 |  | [D] |
| T036 | Tests: apply (per kind), conflict fail-closed, staleness rejection, idempotency | WP07 |  | [D] |
| T037 | `cli/commands/agent_retrospect.py` `synthesize` subcommand | WP08 |  | [D] |
| T038 | Flag parsing (`--apply`, `--proposal-id`, `--json`, `--actor-id`, etc.) | WP08 |  | [D] |
| T039 | Exit codes per `contracts/cli_surfaces.md` (0/1/2/3/4/5) | WP08 |  | [D] |
| T040 | Rich + JSON output renderers (informational equivalence) | WP08 |  | [D] |
| T041 | Tests: CLI integration tests for synthesize | WP08 |  | [D] |
| T042 | `summary.py` reducer + `SummarySnapshot` Pydantic model | WP09 |  | [D] |
| T043 | Streaming corpus reader for `.kittify/missions/*/retrospective.yaml` | WP09 |  | [D] |
| T044 | Tolerance: malformed / missing / legacy / in-flight / terminus_no_retrospective categories | WP09 |  | [D] |
| T045 | `cli.py` `retrospect summary` subcommand wiring under top-level `retrospect` | WP09 |  | [D] |
| T046 | Rich + JSON renderers (informational equivalence) | WP09 |  | [D] |
| T047 | Tests: rich/brief/skipped/missing/malformed corpus tolerance + 200-mission perf bound | WP09 |  | [D] |
| T048 | §4.5.1 inequality predicate as a calibration helper module | WP10 |  | [D] |
| T049 | Calibration walker: every (profile, action) pair × in-scope missions | WP10 |  | [D] |
| T050 | Per-mission calibration report template + 4 reports (software-dev / research / documentation / ERP custom) | WP10 |  | [D] |
| T051 | DRG edge changes for software-dev and research via project-local overlays | WP10 |  | [D] |
| T052 | DRG edge changes for documentation and ERP custom via project-local overlays | WP10 |  | [D] |
| T053 | Architectural test: no new prompt-builder filtering call sites | WP10 |  | [D] |
| T054 | Tests: §4.5.1 inequality holds for every in-scope step | WP10 |  | [D] |
| T055 | Fixture missions for autonomous + HiC paths under `tests/integration/retrospective/fixtures/` | WP11 |  |
| T056 | Real-runtime integration test: autonomous terminus end-to-end | WP11 |  |
| T057 | Real-runtime integration test: HiC terminus end-to-end (run + skip) | WP11 |  |
| T058 | Real-runtime integration test: silent skip blocked (autonomous) | WP11 |  |
| T059 | Real-runtime integration test: silent auto-run blocked (HiC) | WP11 |  |
| T060 | Real-runtime integration test: next mission sees an applied proposal | WP11 |  |
| T061 | Verify NFR-009/010 + existing built-in/custom mission tests pass | WP11 |  |
| T062 | ADR for AD-001 (gate-shared-module) under `architecture/2.x/adr/` | WP12 |  | [D] |
| T063 | Operator overview doc `docs/retrospective-learning-loop.md` | WP12 |  | [D] |
| T064 | Cutover runbook `docs/migration/retrospective-events-upstream.md` | WP12 |  | [D] |
| T065 | Open upstream `spec_kitty_events` issue + record link in code TODO | WP12 |  | [D] |

The `[P]` markers indicate parallel-safe items: schema models (T005), event models (T010), and `Mode` models (T015) are independent shapes that can be drafted concurrently. Within a WP, subtasks remain sequential.

---

## Work Packages

### WP01 — Retrospective Profile + Action + DRG Contract

**Goal**: Ship `profile:retrospective-facilitator` and `action:retrospect` as DRG artifacts that resolve through normal lookup, with a fixture mission proving structured retrospective output.

**Priority**: Phase-0 foundation. MVP gate. Other WPs depend on these artifacts being resolvable.

**Independent test**: Run a fixture mission whose terminus invokes `action:retrospect`; assert the response is schema-valid `RetrospectiveRecord`-shaped (using stub schema until WP02 lands a full one — coordinate via simple dict shape until then).

**Spec coverage**: FR-001, FR-002, FR-003, FR-004, FR-028 (built-in mission integration prerequisite).

**Subtasks**:
- [x] T001 Define `profile:retrospective-facilitator` shipped artifact (WP01)
- [x] T002 Define `action:retrospect` shipped artifact + scope edges (WP01)
- [x] T003 Wire DRG context (event stream, mission meta, charter, glossary, etc.) onto the retrospect action (WP01)
- [x] T004 DRG resolver + fixture mission test that confirms structured response (WP01)

**Implementation sketch**:
1. Add a profile YAML under `src/doctrine/agent_profiles/shipped/retrospective-facilitator.yaml` following existing profile shape.
2. Add an action YAML under `src/doctrine/missions/<each>/actions/retrospect.yaml` (or shared if convention allows; check existing patterns first) that surfaces the required context per FR-003.
3. Wire scope edges in `src/doctrine/graph.yaml` so the resolver can reach event stream / charter / glossary / mission output artifacts.
4. Write `tests/doctrine/test_retrospective_drg.py` that resolves the action against a fixture mission and asserts the surfaced URN set contains the FR-003 minimums.

**Parallel opportunities**: none — single coherent surface.

**Dependencies**: none.

**Risks**: discovering the right convention for the action's home (per-mission vs. shared). Read existing actions before adding; avoid inventing a new pattern.

**Estimated prompt size**: ~280 lines.

---

### WP02 — `retrospective.yaml` Schema, Writer, Reader

**Goal**: Pydantic schema for `retrospective.yaml`, atomic round-trip writer, and schema-validating reader with structured-error result type.

**Priority**: Foundation. Blocks WP03/WP05/WP07/WP09.

**Independent test**: Round-trip a fixture finding set through writer + reader; verify file contents match in-memory model byte-for-byte after re-serialization.

**Spec coverage**: FR-005, FR-006, FR-007, FR-008, FR-009, NFR-001, NFR-002, NFR-005, C-014.

**Subtasks**:
- [x] T005 Pydantic schema models per data-model.md (WP02)
- [x] T006 Atomic round-trip writer: tempfile + `os.replace`, schema validation upstream (WP02)
- [x] T007 Schema-validating reader with structured-error result type (WP02)
- [x] T008 Required vs optional + status-conditional cross-field validation (WP02)
- [x] T009 Tests: schema round-trip; writer atomicity; reader malformed/missing/legacy tolerance (WP02)

**Implementation sketch**:
1. `schema.py` — Pydantic v2 models per data-model.md. Per-proposal-kind payload union via `Annotated[..., Field(discriminator="kind")]`.
2. `writer.py` — accepts an in-memory record, validates, serializes via `ruamel.yaml` round-trip-safe dumper, writes to `<canonical>.tmp.<pid>.<rand>`, fsyncs, `os.replace()`.
3. `reader.py` — returns `Result[RetrospectiveRecord, SchemaError]`-shaped; performs cross-field validation and soft evidence-reachability check.
4. Tests in `tests/retrospective/test_schema_roundtrip.py` and `tests/retrospective/test_writer_atomicity.py`.

**Parallel opportunities**: T005 schema can be drafted in parallel with T010 (events) and T015 (mode), as their fields are independent.

**Dependencies**: none.

**Risks**: getting the discriminated-union for proposal payloads right with Pydantic v2.

**Estimated prompt size**: ~400 lines.

---

### WP03 — Retrospective Events + Reducer Integration

**Goal**: Eight event Pydantic models locally defined, factory + emission helpers, reducer integration that surfaces a `RetrospectiveSnapshot` on `StatusSnapshot`.

**Priority**: Foundation for the gate (WP05) and summary (WP09).

**Independent test**: Append the eight events to a fixture event log and assert `materialize()` returns a `StatusSnapshot` with the expected `retrospective: RetrospectiveSnapshot`.

**Spec coverage**: FR-017, FR-018, NFR-005.

**Subtasks**:
- [x] T010 Pydantic event models for the eight retrospective events (WP03)
- [x] T011 Event factory + emission helpers wired through `specify_cli.status.emit` (or sibling) (WP03)
- [x] T012 Reducer integration: surface `RetrospectiveSnapshot` on `StatusSnapshot` (WP03)
- [x] T013 Tests: append-only invariant, retry semantics, name uniqueness vs existing events (WP03)
- [x] T014 Boundary test (skipped, pending upstream `spec_kitty_events` release) (WP03)

**Implementation sketch**:
1. `events.py` — eight Pydantic models with payload shapes from `contracts/retrospective_events_v1.md`.
2. Emission helper in retrospective package (don't modify `status.emit` shape; add a sibling `retrospective.events.emit_event(...)` that calls `status.store.append_event(...)` with a retrospective envelope).
3. Extend `status.models.StatusSnapshot` to include `retrospective: RetrospectiveSnapshot | None`. Update `status.reducer.materialize()` to compute it from retrospective events.
4. Add `tests/architectural/test_retrospective_events_boundary.py` with a `pytest.skip()` placeholder citing the upstream issue.

**Parallel opportunities**: T010 with T005 and T015.

**Dependencies**: WP02 (schema; specifically the `RecordProvenance`, `Mode` types are referenced from event payloads — this WP can proceed against draft shapes if WP02 is in flight, but final merge sequencing should land WP02 first).

**Risks**: the reducer change touches existing code; verify no existing snapshot consumer breaks (additive only).

**Estimated prompt size**: ~370 lines.

---

### WP04 — Mode Detection

**Goal**: Resolve mission mode through the precedence charter > flag > env > parent process, with the source signal recorded.

**Priority**: Required for the gate (WP05).

**Independent test**: For each layer of precedence, set up only that layer's signal and verify `mode.detect()` returns the correct value with the correct source.

**Spec coverage**: FR-016, C-013.

**Subtasks**:
- [x] T015 `Mode` + `ModeSourceSignal` Pydantic models (WP04)
- [x] T016 `mode.detect()` precedence (charter > flag > env > parent) implementation (WP04)
- [x] T017 Charter-override loader integration + structured-error on missing meta/charter (WP04)
- [x] T018 Parent-process heuristic w/ conservative non-interactive list (WP04)
- [x] T019 Tests: each precedence layer + ambiguous resolution + audit recording (WP04)

**Implementation sketch**:
1. `mode.py` — `Mode`, `ModeSourceSignal`, `detect(repo_root, *, flag=None, env=None, parent_process=None)` that allows test injection.
2. Charter loader integration: read `.kittify/charter/charter.md` policy declarations; fail closed on parse errors with a structured error.
3. Parent-process heuristic: small constant list of non-interactive parent process names (CI runners, agent harnesses). When in doubt → HiC.
4. Tests in `tests/retrospective/test_mode_detection.py` covering each precedence layer.

**Parallel opportunities**: T015 with T005 and T010.

**Dependencies**: WP02 (uses `Mode` / `ModeSourceSignal` types).

**Risks**: parent-process heuristic correctness; conservative default (HiC) is the safe fallback.

**Estimated prompt size**: ~340 lines.

---

### WP05 — Lifecycle Gate + Thin `next` Caller

**Goal**: Single source of truth for the retrospective gate; thin caller in `next` that consults it.

**Priority**: Critical. Implements the autonomous/HiC enforcement.

**Independent test**: Replay every row of the decision matrix (`contracts/gate_api.md`) and assert the expected `GateDecision`. Replay determinism: same inputs → same outputs.

**Spec coverage**: FR-011, FR-012, FR-013, FR-014, FR-015, NFR-007, NFR-008.

**Subtasks**:
- [x] T020 `gate.is_completion_allowed()` API + `GateDecision`/`GateReason` shapes (WP05)
- [x] T021 Decision matrix (8 rows from `contracts/gate_api.md`) (WP05)
- [x] T022 Charter-clause resolution for autonomous-skip override path (WP05)
- [x] T023 Operational predicates for "silent auto-run" and "silent skip" (WP05)
- [x] T024 Thin caller in `next/_internal_runtime/retrospective_hook.py` (WP05)
- [x] T025 Tests: every decision-matrix row + determinism replay (WP05)

**Implementation sketch**:
1. `gate.py` — `is_completion_allowed(mission_id, *, feature_dir, repo_root, mode_override=None) -> GateDecision`.
2. Decision matrix as a typed dispatch on `(mode.value, latest_retrospective_event_kind)`.
3. Charter clause lookup: for `autonomous + retrospective.skipped`, check whether the charter authorizes operator-skip; if yes, allow with `reason.code == "skipped_permitted"` and `reason.charter_clause_ref` set.
4. Silent auto-run: in HiC mode, if a `retrospective.completed` event exists but its upstream `retrospective.requested` was emitted by `actor.kind == "runtime"`, return `silent_auto_run_attempted`.
5. Thin caller in `next`: `retrospective_hook.before_mark_done(...)` calls the gate, raises `MissionCompletionBlocked(decision)` on `allow=False`.
6. Tests in `tests/retrospective/test_gate_decision.py` walk every matrix row.

**Parallel opportunities**: none within this WP.

**Dependencies**: WP02, WP03, WP04.

**Risks**: silent-auto-run predicate must be tight enough to reject runtime-driven completion in HiC, but not block legitimate operator-driven completion.

**Estimated prompt size**: ~470 lines.

---

### WP06 — Lifecycle Terminus Hook (`next` Integration)

**Goal**: Wire the retrospective lifecycle into `next` for built-in missions; preserve custom-mission marker step compatibility.

**Priority**: Required for end-to-end flows.

**Independent test**: Run a fixture mission through `next` and assert the lifecycle emits `retrospective.requested` at terminus in autonomous mode and shows the operator prompt in HiC mode.

**Spec coverage**: FR-013, FR-014, FR-028, FR-029.

**Subtasks**:
- [x] T026 Lifecycle terminus hook in `next` (built-in mission flow) (WP06)
- [x] T027 HiC offer/skip prompt UX in `next` (WP06)
- [x] T028 Autonomous auto-invocation path (WP06)
- [x] T029 Compatibility check for custom mission's required `retrospective` marker step (WP06)
- [x] T030 Tests: lifecycle hook integration + custom-mission marker compat regression (WP06)

**Implementation sketch**:
1. Identify the spot in `next/` where built-in mission terminus is recognized; insert a hook that invokes `action:retrospect`.
2. HiC: prompt the operator (Rich `Prompt.ask(...)`) before invoking. Skip path captures a `skip_reason` and emits `retrospective.skipped`.
3. Autonomous: invoke directly, then call `gate.is_completion_allowed()` before signaling mission done.
4. Custom-mission flow: the existing required `retrospective` marker step in custom missions resolves to the same `action:retrospect`; verify and add a regression test for the loader contract (FR-029).
5. Tests in `tests/integration/retrospective/test_lifecycle_hook.py`.

**Parallel opportunities**: none.

**Dependencies**: WP01, WP05.

**Risks**: touching `next/` is high-blast-radius. Keep the hook minimal and route everything through `retrospective.gate` and `retrospective.lifecycle`.

**Estimated prompt size**: ~420 lines.

---

### WP07 — Synthesizer Core (apply / conflict / provenance)

**Goal**: Implement `doctrine.synthesizer` that applies accepted proposals to project-local doctrine/DRG/glossary with conflict + staleness checks and provenance.

**Priority**: Required for FR-019 / FR-024 acceptance.

**Independent test**: Apply a fixture finding set; assert applied artifacts, provenance sidecars, and emitted events match expectations. Force a conflict; assert nothing applies and `retrospective.proposal.rejected` is emitted for each conflicting proposal.

**Spec coverage**: FR-019, FR-020, FR-022, FR-023, NFR-006, C-012.

**Subtasks**:
- [x] T031 `apply_proposals()` API skeleton in `doctrine.synthesizer.apply` (WP07)
- [x] T032 Conflict detection per R-006 predicates (WP07)
- [x] T033 Staleness check (evidence event reachability) (WP07)
- [x] T034 Provenance sidecar writer (WP07)
- [x] T035 Idempotency via provenance presence check (WP07)
- [x] T036 Tests: apply (per kind), conflict fail-closed, staleness rejection, idempotency (WP07)

**Implementation sketch**:
1. `apply.py` — `apply_proposals(...)` returns `SynthesisResult`.
2. `conflict.py` — pairwise predicates per R-006 plus the unit tests from the contract table.
3. `provenance.py` — writes sidecar provenance YAML colocated with the applied artifact.
4. Auto-apply policy: only `flag_not_helpful` is auto-included; everything else must be in `approved_proposal_ids`.
5. Idempotency: re-running with the same approved set on the same project state is a no-op (detected via provenance presence).
6. Tests in `tests/doctrine/synthesizer/test_apply.py`, `test_conflict_failclosed.py`, `test_provenance.py`.

**Parallel opportunities**: none within this WP (subtasks are tightly coupled).

**Dependencies**: WP02, WP03.

**Risks**: subtleties around the per-proposal-kind application logic. Prefer to ship `add_glossary_term` + `flag_not_helpful` first, then layer in `*_edge` and `synthesize_*`.

**Estimated prompt size**: ~520 lines.

---

### WP08 — Synthesizer CLI Surface

**Goal**: Wire `spec-kitty agent retrospect synthesize` per `contracts/cli_surfaces.md`.

**Priority**: Required for operator-driven application.

**Independent test**: Dry-run on a fixture record, assert printed plan matches expected proposals; `--apply` then asserts applied changes match.

**Spec coverage**: FR-021.

**Subtasks**:
- [x] T037 `cli/commands/agent_retrospect.py` `synthesize` subcommand (WP08)
- [x] T038 Flag parsing (`--apply`, `--proposal-id`, `--json`, `--actor-id`, etc.) (WP08)
- [x] T039 Exit codes per `contracts/cli_surfaces.md` (0/1/2/3/4/5) (WP08)
- [x] T040 Rich + JSON output renderers (informational equivalence) (WP08)
- [x] T041 Tests: CLI integration tests for synthesize (WP08)

**Implementation sketch**:
1. New typer subcommand under existing `spec-kitty agent` namespace.
2. Default `--dry-run`; `--apply` is the explicit opt-in.
3. JSON envelope `{schema_version, command, generated_at, dry_run, result}`.
4. Tests in `tests/cli/test_agent_retrospect_synthesize.py`.

**Parallel opportunities**: none.

**Dependencies**: WP07.

**Risks**: exit-code matrix is non-trivial; keep tests exhaustive.

**Estimated prompt size**: ~360 lines.

---

### WP09 — Cross-Mission Summary Reducer + CLI

**Goal**: Streaming reducer + `spec-kitty retrospect summary` operator command emitting both Rich and JSON.

**Priority**: Required for FR-025–FR-027.

**Independent test**: Run summary against a fixture corpus mixing rich/brief/skipped/missing/malformed records; assert the output matches expected counts and `malformed` rows.

**Spec coverage**: FR-025, FR-026, FR-027, NFR-003, NFR-004.

**Subtasks**:
- [x] T042 `summary.py` reducer + `SummarySnapshot` Pydantic model (WP09)
- [x] T043 Streaming corpus reader for `.kittify/missions/*/retrospective.yaml` (WP09)
- [x] T044 Tolerance: malformed / missing / legacy / in-flight / terminus_no_retrospective categories (WP09)
- [x] T045 `cli.py` `retrospect summary` subcommand wiring under top-level `retrospect` (WP09)
- [x] T046 Rich + JSON renderers (informational equivalence) (WP09)
- [x] T047 Tests: rich/brief/skipped/missing/malformed corpus tolerance + 200-mission perf bound (WP09)

**Implementation sketch**:
1. `summary.py` — pure reducer over a list of `RetrospectiveRecord | MalformedSummaryEntry`.
2. `cli.py` — top-level `spec-kitty retrospect` typer app with a `summary` subcommand.
3. Performance: linear in mission count, single-thread. Test with a 200-fixture corpus to verify NFR-003 ≤5 s.
4. Tests in `tests/retrospective/test_summary_tolerance.py`.

**Parallel opportunities**: none within this WP.

**Dependencies**: WP02, WP03.

**Risks**: corpus tolerance edge cases. Cover them all in tests.

**Estimated prompt size**: ~440 lines.

---

### WP10 — Action-Surface Calibration Reports + DRG Edge Changes

**Goal**: Calibration reports for software-dev / research / documentation / ERP custom mission, with recommended DRG edge changes applied via project-local overlays only.

**Priority**: Required for FR-030–FR-032 and the no-prompt-filtering constraint.

**Independent test**: For each in-scope mission, assert that the §4.5.1 inequality holds for every step after calibration is applied.

**Spec coverage**: FR-030, FR-031, FR-032, C-011.

**Subtasks**:
- [x] T048 §4.5.1 inequality predicate as a calibration helper module (WP10)
- [x] T049 Calibration walker: every (profile, action) pair × in-scope missions (WP10)
- [x] T050 Per-mission calibration report template + 4 reports (WP10)
- [x] T051 DRG edge changes for software-dev and research via project-local overlays (WP10)
- [x] T052 DRG edge changes for documentation and ERP custom via project-local overlays (WP10)
- [x] T053 Architectural test: no new prompt-builder filtering call sites (WP10)
- [x] T054 Tests: §4.5.1 inequality holds for every in-scope step (WP10)

**Implementation sketch**:
1. `tests/calibration/inequality.py` — `assert_inequality_holds(mission, step) -> Result`.
2. Walker uses the existing DRG resolver to enumerate `(profile, action)` pairs per mission.
3. Per-mission report markdown generated under `architecture/calibration/<mission>.md`.
4. DRG edge changes recorded in project-local overlays under `.kittify/doctrine/overlays/calibration-<mission>.yaml` (NOT in the shipped `src/doctrine/graph.yaml`, to avoid ownership conflict with WP01).
5. Architectural test in `tests/architectural/test_no_prompt_filtering_added.py` greps for new prompt-builder filter call sites.

**Parallel opportunities**: T051 and T052 are independent missions and can be implemented in parallel.

**Dependencies**: WP01, WP05.

**Risks**: calibration may surface so many issues that the four reports balloon. Keep the report template tight; offload long-form analysis to follow-up issues if needed.

**Estimated prompt size**: ~510 lines.

---

### WP11 — Real-Runtime Integration Tests + Dogfood Gate

**Goal**: End-to-end coverage of the lifecycle path through `next` for autonomous + HiC; silent-skip and silent-auto-run negative cases; next-mission-sees-it scenario.

**Priority**: Acceptance gate. Without this the spec's FR-033 is not satisfied.

**Independent test**: All six integration tests pass; existing built-in mission and custom mission loader tests still pass.

**Spec coverage**: FR-033, NFR-009, NFR-010, plus regression coverage for C-001…C-010.

**Subtasks**:
- [ ] T055 Fixture missions for autonomous + HiC paths (WP11)
- [ ] T056 Real-runtime integration test: autonomous terminus end-to-end (WP11)
- [ ] T057 Real-runtime integration test: HiC terminus end-to-end (run + skip) (WP11)
- [ ] T058 Real-runtime integration test: silent skip blocked (autonomous) (WP11)
- [ ] T059 Real-runtime integration test: silent auto-run blocked (HiC) (WP11)
- [ ] T060 Real-runtime integration test: next mission sees an applied proposal (WP11)
- [ ] T061 Verify NFR-009/010 + existing built-in/custom mission tests pass (WP11)

**Implementation sketch**:
1. Fixture missions live under `tests/integration/retrospective/fixtures/`. Use the smallest mission shape that exercises the terminus.
2. Tests drive `spec-kitty next` (or the runtime entry point) and assert event log + retrospective record contents.
3. Coverage check via `pytest-cov` confirms ≥90% for new modules per NFR-009.
4. mypy --strict run is included as a CI gate.

**Parallel opportunities**: T056–T060 are independent tests that can be drafted in parallel within the same file or separate files.

**Dependencies**: WP06, WP07, WP09.

**Risks**: real-runtime tests are slow; mark them under a marker or in a separate suite to keep unit-test feedback fast.

**Estimated prompt size**: ~520 lines.

---

### WP12 — ADR + Docs + Upstream Events Tracking

**Goal**: Write the AD-001 ADR, an operator overview doc, the upstream-events cutover runbook, and open the upstream `spec_kitty_events` issue.

**Priority**: Documentation polish; required for charter DIRECTIVE_003 conformance.

**Independent test**: ADR file exists and references AD-001; docs render cleanly in the existing docs site (`mkdocs` or equivalent if used); upstream issue link is present in `events.py` as a TODO.

**Spec coverage**: cross-cutting; charter directives (DIRECTIVE_003, DIRECTIVE_010).

**Subtasks**:
- [x] T062 ADR for AD-001 (gate-shared-module) under `architecture/2.x/adr/` (WP12)
- [x] T063 Operator overview doc `docs/retrospective-learning-loop.md` (WP12)
- [x] T064 Cutover runbook `docs/migration/retrospective-events-upstream.md` (WP12)
- [x] T065 Open upstream `spec_kitty_events` issue + record link in code TODO (WP12)

**Implementation sketch**:
1. ADR uses the project's existing ADR template.
2. Operator doc is essentially a polished version of `quickstart.md`.
3. Cutover runbook describes the exact steps from `contracts/retrospective_events_v1.md` "Cutover note."
4. Upstream issue link recorded in `events.py` near the `pytest.skip()` boundary test.

**Parallel opportunities**: T062, T063, T064 are independent.

**Dependencies**: WP05 (for AD-001 content), WP07 (for migration runbook details).

**Risks**: low.

**Estimated prompt size**: ~270 lines.

---

## Execution Order and Lanes

Suggested lane assignment (`finalize-tasks` will compute the actual lanes from dependencies):

| Lane | WPs |
|---|---|
| A (foundation) | WP01, WP02 |
| B (events / mode) | WP03, WP04 (after WP02 lands) |
| C (gate / lifecycle) | WP05 (after WP02/WP03/WP04), WP06 (after WP01/WP05) |
| D (synthesizer) | WP07 (after WP02/WP03), WP08 (after WP07) |
| E (summary) | WP09 (after WP02/WP03) |
| F (calibration) | WP10 (after WP01/WP05) |
| G (integration) | WP11 (after WP06/WP07/WP09) |
| H (docs) | WP12 (after WP05/WP07) |

WP01 and WP02 are the only WPs with zero dependencies and can run in parallel as the first move.

---

## MVP Scope

Minimum viable shipping unit (acceptance-complete for the bulk of FR coverage): **WP01 + WP02 + WP03 + WP04 + WP05 + WP06 + WP09 + WP11**. This delivers profile/action, schema, events, mode/gate, lifecycle hook, summary, and integration tests — the lifecycle learning loop without the synthesizer mutation surface (WP07/WP08) or the calibration tranche (WP10).

Full acceptance requires all 12 WPs.

---

## Validation Snapshot

- 12 WPs · 65 subtasks · ideal range hit (3–7 subtasks per WP).
- Estimated prompt sizes: 270–520 lines · all within the 200–700 target.
- Average: ~410 lines per WP.
- Parallelization: at least three independent first-move lanes (WP01, WP02, plus T015/T010/T005 within their WPs).
- All FR/NFR/C IDs from `spec.md` are mapped via `requirement_refs` (registered in the next step).
