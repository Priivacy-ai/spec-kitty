# Tasks: Glossary DRG Residence and Executor Chokepoint

**Mission:** `glossary-drg-chokepoint-01KPTE0P` (`01KPTE0P5JVQFWESWV07R0XG4M`)
**Branch:** `main` → `main`
**Date:** 2026-04-22
**Spec:** [spec.md](spec.md) | **Plan:** [plan.md](plan.md)

---

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|-----|---------|
| T001 | Add `NodeKind.GLOSSARY = "glossary"` to `doctrine.drg.models` | WP01 | No |
| T002 | Implement `glossary_urn()` with collision detection | WP01 | [P] with T001 |
| T003 | Implement `build_glossary_drg_layer()` | WP01 | No |
| T004 | Implement `_normalize()` suffix-stripper | WP01 | [P] with T003 |
| T005 | Implement `build_index() → GlossaryTermIndex` | WP01 | No |
| T006 | Backward-compat tests for `NodeKind.GLOSSARY` | WP01 | [P] after T001 |
| T007 | Unit tests for `drg_builder.py` | WP01 | No |
| T008 | Implement `GlossaryObservationBundle` frozen dataclass | WP02 | No |
| T009 | Implement `GlossaryChokepoint.__init__()` and lazy `_load_index()` | WP02 | No |
| T010 | Implement `GlossaryChokepoint.run()` | WP02 | No |
| T011 | Wire existing `classify_conflict()` / `score_severity()` / `create_conflict()` into `_run_inner()` | WP02 | [P] with T010 |
| T012 | Write benchmark script `bench_chokepoint.py` | WP02 | [P] after T010 |
| T013 | Draft ADR-5 with benchmark results | WP02 | No |
| T014 | Unit tests for `GlossaryChokepoint` and `GlossaryObservationBundle` | WP02 | No |
| T015 | Extend `InvocationPayload.__slots__` with `glossary_observations` | WP03 | No |
| T016 | Add chokepoint call to `ProfileInvocationExecutor.invoke()` | WP03 | No |
| T017 | Implement severity routing (high → payload, low/medium → trail) | WP03 | No |
| T018 | Add `write_glossary_observation()` to `InvocationWriter` | WP03 | [P] with T015 |
| T019 | Wire `write_glossary_observation()` into `invoke()` | WP03 | No |
| T020 | Update Codex host guidance (`setup-codex-spec-kitty-launcher.md`) | WP03 | [P] with T021, T022 |
| T021 | Find and update gstack host guidance | WP03 | [P] with T020, T022 |
| T022 | Update `docs/trail-model.md` with `"glossary_checked"` event | WP03 | [P] with T020, T021 |
| T023 | Run full e2e suite; fix any `to_dict()` key breakages | WP03 | No |
| T024 | Write 3-event JSONL integration test | WP03 | No |

---

## WP01 — DRG Term Node Model and Index Builder

**Priority:** P0 (blocks WP02 and WP03)
**Estimated size:** ~350 lines
**Prompt:** [tasks/WP01-drg-term-node-model-and-index-builder.md](tasks/WP01-drg-term-node-model-and-index-builder.md)
**Dependencies:** none
**Spec coverage:** FR-001, FR-002, FR-003, FR-004, FR-013, FR-015, NFR-004, NFR-005, C-003, C-004

**Goal:** Establish the `glossary:<id>` URN scheme, the in-memory DRG layer builder, and the `GlossaryTermIndex` that the chokepoint will consume.

**Subtasks:**
- [ ] T001 Add `NodeKind.GLOSSARY = "glossary"` to `doctrine.drg.models` (WP01)
- [ ] T002 Implement `glossary_urn()` with collision detection and warning (WP01)
- [ ] T003 Implement `build_glossary_drg_layer()` — mint DRGNode per active sense, add VOCABULARY edges from all shipped action nodes (WP01)
- [ ] T004 Implement `_normalize()` — pure-Python suffix stripper for lemmatization (WP01)
- [ ] T005 Implement `build_index() → GlossaryTermIndex` — surface_to_urn, surface_to_senses, lemmatized aliases (WP01)
- [ ] T006 Write backward-compat tests in `tests/doctrine/drg/test_glossary_node_kind.py` (WP01)
- [ ] T007 Write unit tests in `tests/specify_cli/glossary/test_drg_builder.py` (WP01)

**Parallel opportunities:** T001 and T002 can be developed in parallel; T004 is independent of T003.
**Risks:** URN regex in DRG validator must accept `glossary:` prefix — verify `NodeKind.GLOSSARY.value == "glossary"` matches the URN validator's prefix-equals-kind rule.
**Success criteria:** `glossary_urn("lane")` returns a deterministic 8-hex ID; `build_index()` returns an index containing both canonical and lemmatized forms; existing DRG YAML files load cleanly.

---

## WP02 — Chokepoint Class and Observation Bundle

**Priority:** P0 (blocks WP03)
**Estimated size:** ~380 lines
**Prompt:** [tasks/WP02-chokepoint-class-and-observation-bundle.md](tasks/WP02-chokepoint-class-and-observation-bundle.md)
**Dependencies:** WP01
**Spec coverage:** FR-005, FR-006, FR-007, FR-008, FR-009, FR-010, FR-013, NFR-001, NFR-002, NFR-003, NFR-004, NFR-005, C-001, C-002

**Goal:** Implement the `GlossaryObservationBundle` data model, the `GlossaryChokepoint` class (lazy index, tokenize+match+classify), the latency benchmark, and ADR-5.

**Subtasks:**
- [ ] T008 Implement `GlossaryObservationBundle` frozen dataclass with `to_dict()` (WP02)
- [ ] T009 Implement `GlossaryChokepoint.__init__()` (lazy, no I/O) and `_load_index()` (WP02)
- [ ] T010 Implement `GlossaryChokepoint.run()` — tokenize, normalize, lookup, classify, time (WP02)
- [ ] T011 Wire existing `classify_conflict()` / `score_severity()` / `create_conflict()` from `specify_cli.glossary.conflict` into `_run_inner()` — no new classifier (WP02)
- [ ] T012 Write benchmark script `tests/specify_cli/glossary/bench_chokepoint.py` (WP02)
- [ ] T013 Draft `architecture/adrs/2026-04-22-5-glossary-chokepoint-p95-measurement.md` with results (WP02)
- [ ] T014 Write unit tests in `tests/specify_cli/glossary/test_chokepoint.py` (WP02)

**Parallel opportunities:** T011 can be written in parallel with T010 after the function signature is agreed; T012 can be written after T010 is passing.
**Risks:** Chokepoint may exceed 50ms on large request texts — benchmark early (T012) before finalising T013.
**Success criteria:** `GlossaryChokepoint.run()` returns a bundle with `error_msg=None` on happy path; exception injection returns error-bundle without propagating; benchmark p95 within target.

---

## WP03 — Executor Integration, Trail, and Host Guidance

**Priority:** P1 (final integration)
**Estimated size:** ~480 lines
**Prompt:** [tasks/WP03-executor-integration-trail-and-host-guidance.md](tasks/WP03-executor-integration-trail-and-host-guidance.md)
**Dependencies:** WP01, WP02
**Spec coverage:** FR-005, FR-008, FR-010, FR-011, FR-012, FR-014, C-001, C-005, C-007, C-008, NFR-005

**Goal:** Wire `GlossaryChokepoint` into `ProfileInvocationExecutor.invoke()`, add `write_glossary_observation()` to the trail writer, implement the severity routing contract in code, update host guidance docs, and verify the full e2e suite.

**Subtasks:**
- [ ] T015 Extend `InvocationPayload.__slots__` with `"glossary_observations"` and update `__init__` (WP03)
- [ ] T016 Add lazy `GlossaryChokepoint` instantiation and call to `invoke()` with try/except boundary (WP03)
- [ ] T017 Build `high_severity` tuple from classified conflicts (`Severity.HIGH` only) in the bundle (WP03)
- [ ] T018 Add `write_glossary_observation()` to `InvocationWriter` — best-effort, append-only (WP03)
- [ ] T019 Wire `write_glossary_observation()` call into `invoke()` after `write_started()` (WP03)
- [ ] T020 Update `docs/how-to/setup-codex-spec-kitty-launcher.md` with `glossary_observations` contract [P] (WP03)
- [ ] T021 Find and update gstack host guidance doc with `glossary_observations` contract [P] (WP03)
- [ ] T022 Update `docs/trail-model.md` with `"glossary_checked"` event type under Tier 1 section [P] (WP03)
- [ ] T023 Run existing invocation e2e suite; fix any breakages caused by new `to_dict()` key (WP03)
- [ ] T024 Write 3-event JSONL integration test verifying `started` + `glossary_checked` + `completed` (WP03)

**Parallel opportunities:** T020, T021, T022 (doc updates) are independent and can run in parallel after T019 is complete.
**Risks:** `InvocationPayload.to_dict()` change adds a new key — any test asserting exact dict contents will need updating (T023). The `mark_loaded=False` invariant in `build_charter_context()` must not be disturbed (C-008).
**Success criteria:** `invoke()` returns payload with `glossary_observations` always set; JSONL file for a non-clean invocation has 3 lines; Codex and gstack docs describe the rendering contract; e2e suite green.
