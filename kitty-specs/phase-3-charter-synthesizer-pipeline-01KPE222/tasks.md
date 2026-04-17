# Tasks — Phase 3 Charter Synthesizer Pipeline

**Mission**: `phase-3-charter-synthesizer-pipeline-01KPE222`
**Mission ID**: `01KPE222CD1MMCYEGB3ZCY51VR`
**Target branch**: `main`
**Generated**: 2026-04-17
**Plan**: [plan.md](./plan.md) · **Spec**: [spec.md](./spec.md) · **Data model**: [data-model.md](./data-model.md)

---

## Execution map

Five work packages, matching the plan-level WP3.1 → WP3.8 contract:

| WP ID | Plan alias | Title | Depends on | Lane |
|---|---|---|---|---|
| WP01 | WP3.1 | Synthesizer skeleton + adapter seam + path guard | — | A |
| WP02 | WP3.2 | Interview-driven synthesis path | WP01 | A |
| WP03 | WP3.6 | Project-local artifact storage + provenance writer | WP02 | A |
| WP04 | WP3.7 | Project DRG writer + no-dangling-ref enforcement | WP02 | B |
| WP05 | WP3.8 | `spec-kitty charter resynthesize --topic` | WP03, WP04 | A (rejoin) |

**Sequencing invariant**: WP01 merges first. WP02 unlocks WP03 and WP04 (both in parallel). WP05 requires WP03 and WP04 durable.

**MVP scope**: WP01 + WP02 + WP03 delivers interview-driven synthesis with atomic writes and provenance — enough for US-1/US-5/US-7/US-8 plus SC-002/SC-003/SC-007. WP04 closes no-dangling-ref + observability gap. WP05 closes targeted resynthesis (US-2/US-3/US-4/US-6).

---

## Subtask Index

| ID | Description | WP | Parallel |
|---|---|---|---|
| T001 | Scaffold `src/charter/synthesizer/` package + `__init__.py` + `errors.py` taxonomy | WP01 | — | [D] |
| T002 | `request.py` — `SynthesisRequest`, `SynthesisTarget`, normalization for hashing | WP01 | [D] |
| T003 | `adapter.py` — `SynthesisAdapter` Protocol + `AdapterOutput` dataclass | WP01 | [D] |
| T004 | `path_guard.py` — `PathGuard` + `PathGuardViolation` + lint-style test | WP01 | [D] |
| T005 | `fixture_adapter.py` — fixture loader with hash-keyed layout + `FixtureAdapterMissingError` | WP01 | — | [D] |
| T006 | `orchestrator.py` — skeleton dispatcher with `synthesize()` / `resynthesize()` entry points | WP01 | — | [D] |
| T007 | Author ADR-2026-04-17-1 (adapter seam) + ADR-2026-04-17-2 (atomicity) | WP01 | [D] |
| T008 | Tests — `test_adapter_contract.py`, `test_path_guard.py`, `test_fixture_adapter.py` + conftest | WP01 | — | [D] |
| T009 | `interview_mapping.py` — interview-section → `SynthesisTarget` table | WP02 | [D] |
| T010 | `targets.py` — target selection, ordering, duplicate-slug detection | WP02 | [D] |
| T011 | `synthesize_pipeline.py` — end-to-end in-memory synthesis flow; wire adapter + schema gate (FR-019) | WP02 | — | [D] |
| T012 | Schema conformance — validate `AdapterOutput.body` against shipped Pydantic models | WP02 | — | [D] |
| T013 | Provenance-object assembly (in-memory; no FS yet) | WP02 | — | [D] |
| T014 | Tests — `test_interview_mapping.py`, `test_orchestrator_synthesize.py` (in-memory), `test_schema_conformance.py` | WP02 | — | [D] |
| T015 | `provenance.py` — `ProvenanceEntry` pydantic model + read/write via ruamel.yaml | WP03 | [P] |
| T016 | `staging.py` — staging dir lifecycle; `.failed` preservation; demux trees | WP03 | [P] |
| T017 | `manifest.py` — `SynthesisManifest` + `ManifestArtifactEntry`; manifest-last commit + read verify | WP03 | [P] |
| T018 | `write_pipeline.py` — ordered `os.replace` promote: content → `.kittify/doctrine/`, bookkeeping → `.kittify/charter/` | WP03 | — |
| T019 | Extend `src/charter/bundle.py` (FR-015) — recognise synthesized artifacts + cross-tree provenance | WP03 | — |
| T020 | Tests — `test_provenance.py`, `test_staging_atomicity.py`, `test_manifest.py`, `test_bundle_validate_extension.py` | WP03 | — |
| T021 | `project_drg.py` — thin composer: emit + persist at `.kittify/doctrine/graph.yaml` | WP04 | [D] |
| T022 | `validation_gate.py` — `validate_graph(merge_layers(shipped, project))` gate before promote (FR-008) | WP04 | [D] |
| T023 | Additive-only enforcement (FR-020) — reject overlay emissions that shadow shipped URNs | WP04 | — | [D] |
| T024 | Extend `src/charter/compiler.py::_default_doctrine_service` — candidate-list extension (FR-009) | WP04 | [D] |
| T025 | Extend `src/charter/context.py::_build_doctrine_service` — same candidate-list extension | WP04 | [D] |
| T026 | Tests — `test_project_drg.py`, `test_validation_gate.py`, `test_charter_compile_project_root.py` (3 cases), `test_context_reflects_synthesis.py` | WP04 | — | [D] |
| T027 | `topic_resolver.py` — 3-tier resolution (local kind+slug → DRG URN → interview section) + `ResolvedTopic` | WP05 | [P] |
| T028 | Structured-error surface — `TopicSelectorUnresolvedError` + Levenshtein top-5 candidate enumeration | WP05 | — |
| T029 | `resynthesize_pipeline.py` — bounded recomputation; manifest rewrite preserves untouched `content_hash` | WP05 | — |
| T030 | CLI subcommands — `spec-kitty charter synthesize` + `resynthesize --topic` via Typer | WP05 | [P] |
| T031 | Performance envelope tests (NFR-002/003/004) | WP05 | [P] |
| T032 | Tests — `test_topic_resolver.py`, `test_orchestrator_resynthesize.py`, CLI integration tests | WP05 | — |

---

## WP01 — Synthesizer skeleton + adapter seam + path guard

**Plan alias**: WP3.1 · **Depends on**: — · **Lane**: A · **Prompt**: [tasks/WP01-synthesizer-skeleton.md](./tasks/WP01-synthesizer-skeleton.md)

**Goal**: Land the `src/charter/synthesizer/` package with a frozen adapter seam (`SynthesisAdapter` Protocol + `AdapterOutput`), the path guard that prevents any write under `src/doctrine/`, a fixture adapter keyed by normalized-request hash, the orchestrator skeleton, the two ADRs (adapter seam + atomicity), and the test harness that later WPs build on.

**Priority**: must-merge-first. Every downstream WP imports from here.

**Independent test**: `pytest tests/charter/synthesizer/test_adapter_contract.py tests/charter/synthesizer/test_path_guard.py tests/charter/synthesizer/test_fixture_adapter.py` and `mypy --strict src/charter/synthesizer/`.

**Subtasks**:
- [x] T001 Scaffold package + errors taxonomy (WP01)
- [x] T002 `request.py` — `SynthesisRequest` + `SynthesisTarget` + normalization (WP01)
- [x] T003 `adapter.py` — Protocol + `AdapterOutput` (WP01)
- [x] T004 `path_guard.py` + lint-style negative test (WP01)
- [x] T005 `fixture_adapter.py` — hash-keyed fixture loader (WP01)
- [x] T006 `orchestrator.py` skeleton (WP01)
- [x] T007 Two ADRs under `architecture/adrs/` (WP01)
- [x] T008 Tests — `test_adapter_contract.py`, `test_path_guard.py`, `test_fixture_adapter.py` + conftest (WP01)

**Parallel opportunities**: T002, T003, T004, T007 can proceed in parallel after T001. T005 and T006 sequence after T003.

**Risks**: R-1 (seam leak) — keep adapter Protocol minimal, no prompt-engineering surface. R-10 (path guard bypass) — the lint-style test must fail if any `open(..., 'w')`, `Path.write_text`, or `shutil.move` appears outside `path_guard.py`.

**Requirement refs**: FR-001, FR-002, FR-003, FR-004, FR-016 · NFR-007, NFR-008, NFR-010 · C-001, C-003, C-005, C-006.

---

## WP02 — Interview-driven synthesis path

**Plan alias**: WP3.2 · **Depends on**: WP01 · **Lane**: A · **Prompt**: [tasks/WP02-interview-driven-synthesis.md](./tasks/WP02-interview-driven-synthesis.md)

**Goal**: Populate `orchestrator.synthesize()` end-to-end in memory. Interview section → target mapping, target selection with duplicate-slug guard, adapter dispatch, schema conformance gate (FR-019), provenance objects assembled. **No filesystem writes yet** — WP03 owns that.

**Priority**: unblocks WP03 + WP04.

**Independent test**: in-memory synthesis through the fixture adapter produces a valid list of `(body, ProvenanceEntry)` tuples; `test_orchestrator_synthesize.py` runs without touching disk (besides fixture reads).

**Subtasks**:
- [x] T009 `interview_mapping.py` — section → target table (WP02)
- [x] T010 `targets.py` — selection + ordering + duplicate-slug detection (WP02)
- [x] T011 `synthesize_pipeline.py` — end-to-end flow (WP02)
- [x] T012 Schema conformance against shipped Pydantic models (WP02)
- [x] T013 In-memory provenance-object assembly (WP02)
- [x] T014 Tests — interview mapping, orchestrator synthesize (in-memory), schema conformance (WP02)

**Parallel opportunities**: T009, T010 can proceed in parallel. T011–T013 sequence after both.

**Risks**: R-9 (silent project-layer DRG reads during interview) — interview-time resolver uses shipped-only DRG; test in `test_interview_mapping.py` locks this. R-8 (fixture hash drift) — keep normalization rules consistent with WP01's `request.normalize`.

**Requirement refs**: FR-001, FR-002, FR-014, FR-019 · NFR-001, NFR-006.

---

## WP03 — Project-local artifact storage + provenance writer

**Plan alias**: WP3.6 · **Depends on**: WP02 · **Lane**: A (parallel with WP04) · **Prompt**: [tasks/WP03-storage-and-provenance.md](./tasks/WP03-storage-and-provenance.md)

**Goal**: Stage-and-promote filesystem pipeline. Stage all writes under `.kittify/charter/.staging/<runid>/{doctrine,charter}/`; on validation pass, ordered `os.replace` demultiplexes into `.kittify/doctrine/` (content) and `.kittify/charter/` (bookkeeping); manifest is written last. Provenance sidecars, commit-marker manifest, and `charter bundle validate` extension (FR-015) all land here.

**Priority**: required for any durable synthesis output.

**Independent test**: `pytest tests/charter/synthesizer/test_staging_atomicity.py test_manifest.py test_provenance.py test_bundle_validate_extension.py` passes; staging dir is preserved under `.failed/` on injected failure; manifest-last semantics verified.

**Subtasks**:
- [ ] T015 `provenance.py` — `ProvenanceEntry` pydantic model + IO (WP03)
- [ ] T016 `staging.py` — staging lifecycle + `.failed` preservation (WP03)
- [ ] T017 `manifest.py` — `SynthesisManifest` + `ManifestArtifactEntry` (WP03)
- [ ] T018 `write_pipeline.py` — ordered promote + demux (WP03)
- [ ] T019 Extend `src/charter/bundle.py` for FR-015 (WP03)
- [ ] T020 Tests — provenance, staging atomicity, manifest, bundle validate (WP03)

**Parallel opportunities**: T015, T016, T017 proceed in parallel. T018 integrates them. T019 is independent.

**Risks**: R-7 (staging accumulation) — `.failed` marker documented; `bundle validate` warns on stale staging. R-3 (bundle manifest drift) — extension stays v1.0.0 additive; regression fixtures pin backwards-compat.

**Requirement refs**: FR-005, FR-006, FR-014, FR-015 · NFR-001, NFR-004, NFR-006, NFR-008 · C-002, C-012.

---

## WP04 — Project DRG writer + no-dangling-ref enforcement + consumer wiring

**Plan alias**: WP3.7 · **Depends on**: WP02 · **Lane**: B (parallel with WP03) · **Prompt**: [tasks/WP04-project-drg-and-wiring.md](./tasks/WP04-project-drg-and-wiring.md)

**Goal**: Emit additive project DRG overlay at `.kittify/doctrine/graph.yaml`; gate promote on `validate_graph(merge_layers(shipped, project))` returning zero errors; enforce additive-only invariants (FR-020); extend `_default_doctrine_service` / `_build_doctrine_service` candidate lists so `DoctrineService` sees `.kittify/doctrine/` as a project layer (FR-009).

**Priority**: closes no-dangling-ref guarantee + observable project-specific context (SC-005).

**Independent test**: `pytest tests/charter/synthesizer/test_project_drg.py test_validation_gate.py test_charter_compile_project_root.py test_context_reflects_synthesis.py` passes; three candidate-list cases (legacy / present / empty) hold.

**Subtasks**:
- [x] T021 `project_drg.py` — composer + persist (WP04)
- [x] T022 `validation_gate.py` — pre-promote validation gate (WP04)
- [x] T023 Additive-only enforcement (FR-020) (WP04)
- [x] T024 Extend `src/charter/compiler.py::_default_doctrine_service` (WP04)
- [x] T025 Extend `src/charter/context.py::_build_doctrine_service` (WP04)
- [x] T026 Tests — project_drg, validation_gate, charter_compile_project_root (3 cases), context_reflects_synthesis (WP04)

**Parallel opportunities**: T021, T022, T024, T025 in parallel. T023 sequences after T021.

**Risks**: R-2 (candidate-list ripple) — discovery MUST be conditional on directory presence; legacy projects see byte-identical behaviour. Lock via the 3-case test.

**Requirement refs**: FR-007, FR-008, FR-009, FR-018, FR-020 · NFR-001, NFR-009 · C-001, C-009.

---

## WP05 — `spec-kitty charter resynthesize --topic`

**Plan alias**: WP3.8 · **Depends on**: WP03, WP04 · **Lane**: A (rejoin) · **Prompt**: [tasks/WP05-resynthesize-topic.md](./tasks/WP05-resynthesize-topic.md)

**Goal**: Structured-selector resolver (local kind+slug → DRG URN → interview section), bounded recomputation that reuses WP03's staging/promote machinery, manifest rewrite that preserves untouched `content_hash`, and the CLI subcommands (`synthesize` + `resynthesize --topic`) via Typer.

**Priority**: closes US-2/US-3/US-4/US-6 + CLI FR-010/FR-011.

**Independent test**: `pytest tests/charter/synthesizer/test_topic_resolver.py test_orchestrator_resynthesize.py test_performance_envelopes.py tests/agent/cli/commands/test_charter_*_cli.py`. SC-008 threshold: unresolved selector error returns in < 2s.

**Subtasks**:
- [ ] T027 `topic_resolver.py` — 3-tier resolution (WP05)
- [ ] T028 Structured-error surface + candidate enumeration (WP05)
- [ ] T029 `resynthesize_pipeline.py` — bounded recomputation (WP05)
- [ ] T030 CLI subcommands via Typer (WP05)
- [ ] T031 Performance envelope tests (NFR-002/003/004) (WP05)
- [ ] T032 Tests — topic_resolver, orchestrator_resynthesize, CLI integration (WP05)

**Parallel opportunities**: T027, T030, T031 in parallel. T028 builds on T027. T029 builds on T027 + WP03/WP04.

**Risks**: R-5 (selector ambiguity) — structured error enumeration teaches the affordance; C-004 rejects free-text.

**Requirement refs**: FR-010, FR-011, FR-012, FR-013, FR-017 · NFR-002, NFR-003 · C-004.

---

## Dependency graph

```
WP01 ──▶ WP02 ──┬──▶ WP03 ──┐
                │           ├──▶ WP05
                └──▶ WP04 ──┘
```

WP03 and WP04 run in parallel after WP02. WP05 needs both durable.

---

## Validation rollup

| Requirement | Covered in |
|---|---|
| FR-001, FR-002, FR-003, FR-004 | WP01 |
| FR-005, FR-006, FR-015 | WP03 |
| FR-007, FR-008, FR-009, FR-018, FR-020 | WP04 |
| FR-010, FR-011, FR-012, FR-013, FR-017 | WP05 |
| FR-014 | WP02 + WP03 |
| FR-016 | WP01 |
| FR-019 | WP02 |
| NFR-001 | all WPs (≥90% coverage gate on new modules) |
| NFR-002, NFR-003 | WP05 (performance envelope tests) |
| NFR-004 | WP03 (fail-closed timing) |
| NFR-005 | WP02 (schema conformance gate) |
| NFR-006 | WP02 + WP03 (byte-reproducibility) |
| NFR-007 | all WPs (`mypy --strict`) |
| NFR-008 | WP01 (path guard) + WP03 (staging) |
| NFR-009 | WP04 (pre-commit validator) |
| NFR-010 | WP01 (fixture adapter) |

---

## Next command

After any tasks.md or WP prompt edits, run:

```bash
spec-kitty agent mission finalize-tasks --json --mission phase-3-charter-synthesizer-pipeline-01KPE222
```

This parses dependencies, validates ownership, normalizes branch-strategy metadata, writes `lanes.json`, and commits the finalized task set.
