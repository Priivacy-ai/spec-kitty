# Tasks: Retrospective Learning Default-On Policy

**Mission**: `retrospective-default-policy-01KS049J` (mission_id `01KS049J4V9CSWBKJHTY2FB69H`)
**Date**: 2026-05-19
**Spec**: [spec.md](./spec.md) · **Plan**: [plan.md](./plan.md) · **Research**: [research.md](./research.md) · **Data model**: [data-model.md](./data-model.md) · **Contracts**: [contracts/](./contracts/) · **Quickstart**: [quickstart.md](./quickstart.md) · **ADR**: [`architecture/3.x/adr/2026-05-19-1-retrospective-default-policy-architecture.md`](../../architecture/3.x/adr/2026-05-19-1-retrospective-default-policy-architecture.md)
**Branch contract**: planning base `main` · merge target `main` · current `main` · matches ✓

## Subtask Index

| ID | Description | WP | Parallel |
|---|---|---|---|
| T001 | Define `RetrospectivePolicy` + `RetrospectivePermissions` domain models with built-in defaults | WP01 | |
| T002 | Implement resolver: charter → config → defaults; return `(policy, source_map)` | WP01 | |
| T003 | Implement charter `retrospective.precedence: config` delegation | WP01 | |
| T004 | Implement `PolicyResolutionError` + malformed-input handling per FR-024 | WP01 | |
| T005 | Wire env-var observation into `source_map` as deprecated source (never wins) | WP01 | |
| T006 | Unit tests for policy resolver covering FR-001/002/003/004/015/024 | WP01 | |
| T007 | Define `RetrospectiveRecord` + `Finding` + `Proposal` + `EvidenceRef` + `Provenance` types per data-model.md | WP02 | |
| T008 | Implement `generate_retrospective(mission_handle, policy, repo_root) -> RetrospectiveRecord` (pure-Python generator) | WP02 | |
| T009 | Implement findings classification (helped/not_helpful/gaps/proposals) from artifact + event evidence | WP02 | |
| T010 | Implement `findings_status` resolution (`has_findings` vs `ran_no_findings`) per FR-007 | WP02 | |
| T011 | Implement proposal `risk_class` classification (low vs structural) per FR-010 | WP02 | |
| T012 | Unit tests + 3 fixture missions for the generator (FR-006/007/010) | WP02 | |
| T013 | Implement `writer.write_record(record, mode)` with overwrite/update/error semantics per data-model.md | WP03 | |
| T014 | Enforce `synthesize_fabricate ⇒ ran_no_findings` invariant in writer validation | WP03 | |
| T015 | Add `RetrospectiveCaptured` + `RetrospectiveCaptureFailed` event types (reuse if existing per FR-024 frozen surface, else add additively) | WP03 | |
| T016 | Verify reducer no-op behavior for retrospective events; add fixture set under `tests/retrospective/fixtures/event_logs/` per FR-025 | WP03 | |
| T017 | Unit tests for writer + events + reducer fidelity (FR-021/025) | WP03 | |
| T018 | Replace `facilitator_callback=None` in `next/runtime_bridge.py` with real generator + policy wiring (FR-005) | WP04 | |
| T019 | Implement default post-completion flow: attempt → write+Captured event on success, warn+Failed event on failure (FR-008) | WP04 | |
| T020 | Implement strict pre-completion gate: block with policy_source citation; `--skip-retrospective` bypass with actor/provenance (FR-009) | WP04 | |
| T021 | Wire `policy_source` attribution on every emitted retrospective event (FR-001) | WP04 | |
| T022 | Anchor gate-evaluation point at canonical "mission completion" per data-model.md (immediately before `MissionCompleted` emit) | WP04 | |
| T023 | Wiring + integration tests under `tests/next/test_retrospective_terminus_wiring.py` and `tests/integration/retrospective/` (FR-005/008/009) | WP04 | |
| T024 | Implement `spec-kitty retrospect create --mission <handle>` per `contracts/retrospect-cli.contract.md` (FR-011) | WP05 | [P] |
| T025 | Add `--overwrite` / `--update` / `--json` flags + structured error codes for `create` | WP05 | [P] |
| T026 | Implement `spec-kitty retrospect backfill --since/--until --mission --dry-run --emit-skipped --emit-failures` (FR-012) | WP05 | [P] |
| T027 | Tighten `retrospect summary` to distinguish `has_findings` / `ran_no_findings` / `missing` / `failed` (FR-013, no semantic change) | WP05 | [P] |
| T028 | Tighten `agent retrospect synthesize` default-path error; add `--fabricate-empty` compat flag with actor-attributed provenance (FR-014) | WP05 | [P] |
| T029 | CLI tests covering all four surfaces + JSON contract assertions | WP05 | [P] |
| T030 | Implement `DeprecationWarning` + Rich stderr notice for `SPEC_KITTY_RETROSPECTIVE` / `SPEC_KITTY_MODE` (FR-015, NFR-006: one warning per process) | WP06 | [P] |
| T031 | Add `SPEC_KITTY_NO_DEPRECATION_WARNINGS=1` suppression env var; documented in WP07 docs | WP06 | [P] |
| T032 | Refactor existing tests to prefer injected `RetrospectivePolicy` over `os.environ` mutations (FR-016) | WP06 | [P] |
| T033 | Resolve shim fate for `retrospective/config.py` + `retrospective/mode.py` per FR-023 — either fold+delete with reference updates, OR retain as documented compat shim with explicit retirement target (deprecation version, follow-up issue, rationale) | WP06 | [P] |
| T034 | Tests for deprecation behavior: one-warn-per-process, durable wins, suppression flag | WP06 | [P] |
| T035 | Update `docs/how-to/use-retrospective-learning.md` as canonical operator how-to (FR-018) | WP07 | [P] |
| T036 | Update `docs/how-to/accept-and-merge.md` (correct PR #1136 wording) + `docs/how-to/merge-feature.md` (FR-018) | WP07 | [P] |
| T037 | Update `docs/explanation/retrospective-learning-loop.md` + `docs/reference/cli-commands.md` + `docs/reference/slash-commands.md` (FR-018) | WP07 | [P] |
| T038 | Update `README.md` retrospective blurb + `docs/tutorials/your-first-feature.md` (FR-018) | WP07 | [P] |
| T039 | Update 4 shipped skills: `spec-kitty-mission-review`, `spec-kitty-implement-review`, `spec-kitty-program-orchestrate`, `spec-kitty-runtime-next` (FR-019) | WP07 | [P] |
| T040 | Review `retrospective-facilitator.agent.yaml`; align boundaries/permissions with FR-001/FR-010 if drift exists (FR-020) | WP07 | [P] |
| T041 | Add `CONTRIBUTING.md` namespace-package diagnostic note for #1137 (FR-017) | WP07 | [P] |

Parallel marker `[P]` indicates parallelism within a single WP (different files / concerns). Inter-WP parallelism is described in each WP's "Dependencies & Parallel Opportunities" section.

## Work Package Map

| WP | Title | Subtasks | Est. lines | Phase | Depends on |
|---|---|---|---|---|---|
| WP01 | RetrospectivePolicy resolver + malformed-input handling | T001-T006 (6) | ~340 | Foundation | — |
| WP02 | Pure-Python retrospective generator + record schema | T007-T012 (6) | ~360 | Foundation | WP01 |
| WP03 | Writer + retrospective lifecycle events + reducer fixtures | T013-T017 (5) | ~310 | Foundation | WP02 |
| WP04 | Runtime wiring: default + strict gate flows | T018-T023 (6) | ~360 | Runtime | WP01, WP02, WP03 |
| WP05 | CLI: `retrospect create` / `backfill` / `summary` tighten / `synthesize` tighten | T024-T029 (6) | ~380 | Surface | WP02, WP03 |
| WP06 | Env-var deprecation + shim retirement (carrier for bulk-edit shape A) | T030-T034 (5) | ~280 | Surface | WP01 |
| WP07 | Docs + shipped skills + CONTRIBUTING note (carrier for bulk-edit shape B) | T035-T041 (7) | ~310 | Polish | WP04, WP05 |

**Total:** 7 WPs, 41 subtasks, ~340 lines/WP average. All in the 200-500 ideal range.

## MVP Scope Recommendation

The default-on retrospective path is unblocked by **WP01 + WP02 + WP03 + WP04** in sequence. After WP04 lands, every new mission completion already produces a useful `retrospective.yaml` under default policy. WP05/WP06/WP07 polish the surface (on-demand authoring, env-var deprecation, docs/skills). Operators get the headline product behavior at WP04.

A reasonable cut for an early-feedback release: ship WP01-WP04 as a "preview" minor (3.2.0rc15?), gather operator feedback on policy resolution and the default-flow generator quality, then ship WP05-WP07 in 3.2.0rc16 (or 3.2.0 GA).

---

## WP01 — RetrospectivePolicy Resolver + Malformed-Input Handling

**Goal**: Land the canonical `RetrospectivePolicy` model with defaults, the resolver that reads from charter + `.kittify/config.yaml` with documented precedence, source-attribution map, and deterministic handling of malformed input.

**Priority**: Foundation (P0). Nothing else in this mission can be tested without it.

**Independent test**: `uv run pytest tests/retrospective/test_policy.py -q` exits 0.

**Requirements covered**: FR-001, FR-002, FR-003, FR-004, FR-015 (env-var observation in source_map), FR-024, NFR-002, NFR-003, NFR-007, C-004.

### Included subtasks

- [x] T001 Define `RetrospectivePolicy` + `RetrospectivePermissions` domain models with built-in defaults (WP01)
- [x] T002 Implement resolver: charter → config → defaults; return `(policy, source_map)` (WP01)
- [x] T003 Implement charter `retrospective.precedence: config` delegation (WP01)
- [x] T004 Implement `PolicyResolutionError` + malformed-input handling per FR-024 (WP01)
- [x] T005 Wire env-var observation into `source_map` as deprecated source (never wins) (WP01)
- [x] T006 Unit tests for policy resolver covering FR-001/002/003/004/015/024 (WP01)

### Implementation sketch

1. Add `src/specify_cli/retrospective/policy.py` with dataclass (or Pydantic v2) models matching `contracts/retrospective-policy.schema.json`.
2. Resolver loads charter frontmatter, then `.kittify/config.yaml#retrospective`, then merges with built-in defaults. Source map records origin per leaf field.
3. Charter wins; charter may set `retrospective.precedence: config` to delegate authority for any field present in config.
4. Wrap config/charter parsing in try/except → return `(default_policy, source_map_with_resolution_error)` and raise `PolicyResolutionError` with structured `source`/`reason`/`detail`.
5. Env-var observation: read `SPEC_KITTY_RETROSPECTIVE` and `SPEC_KITTY_MODE` for source_map attribution only; they never override charter/config.

### Parallel opportunities

Internal: T001 and the test scaffolding for T006 can start in parallel once contracts are read. T002-T005 are sequential within the resolver.

### Dependencies & Risks

- **Dependencies**: none
- **Risks**: charter frontmatter parser must tolerate missing/empty `retrospective:` block without error. Resolver should be byte-deterministic — golden snapshot tests catch drift.

### Prompt

[tasks/WP01-policy-resolver.md](./tasks/WP01-policy-resolver.md)

---

## WP02 — Pure-Python Retrospective Generator + Record Schema

**Goal**: Implement the deterministic pure-Python generator that reads mission artifacts and produces a schema-valid `RetrospectiveRecord` with provenance, evidence references, findings, and proposals.

**Priority**: Foundation (P0).

**Independent test**: `uv run pytest tests/retrospective/test_generator.py -q` exits 0 with at least 3 fixture missions covered.

**Requirements covered**: FR-006, FR-007, FR-010, NFR-004 (partial), NFR-005 (latency budget validated), NFR-007.

### Included subtasks

- [x] T007 Define `RetrospectiveRecord` + `Finding` + `Proposal` + `EvidenceRef` + `Provenance` types per data-model.md (WP02)
- [x] T008 Implement `generate_retrospective(mission_handle, policy, repo_root) -> RetrospectiveRecord` (pure-Python generator) (WP02)
- [x] T009 Implement findings classification (helped/not_helpful/gaps/proposals) from artifact + event evidence (WP02)
- [x] T010 Implement `findings_status` resolution (`has_findings` vs `ran_no_findings`) per FR-007 (WP02)
- [x] T011 Implement proposal `risk_class` classification (low vs structural) per FR-010 (WP02)
- [x] T012 Unit tests + 3 fixture missions for the generator (FR-006/007/010) (WP02)

### Implementation sketch

1. Extend `src/specify_cli/retrospective/schema.py` with the additional types per data-model.md. Existing fields untouched; new fields additive.
2. Create `src/specify_cli/retrospective/generator.py` with the `generate_retrospective` function. Input precedence: meta.json → spec.md → plan/research/data-model/contracts/quickstart → tasks.md + tasks/WP*.md → status.events.jsonl → review/rejection cycles → mission-review-report.md → charter context.
3. Findings classification: derive from rejection cycles (gaps in spec → not_helpful), from completed-without-blockers WPs (helped), from open clarifications (gaps), from successful patterns (proposals for tactic adoption).
4. `findings_status`: `has_findings` if any list non-empty; `ran_no_findings` otherwise. Never produce `missing` or `failed` in a persisted record.
5. Proposal `risk_class`: `low` only for `flag_not_helpful` and similarly-bounded actions; everything touching doctrine/DRG/glossary structurally → `structural`.

### Parallel opportunities

T007 (types) and T012 (test scaffolding + fixtures) can start in parallel. T008-T011 sequential within the generator.

### Dependencies & Risks

- **Dependencies**: WP01
- **Risks**: generator quality (R-4 in spec.md) — low-signal records train users to ignore retrospectives. Mitigation: SC-004 validates against three real completed missions before merge.

### Prompt

[tasks/WP02-generator.md](./tasks/WP02-generator.md)

---

## WP03 — Writer + Retrospective Lifecycle Events + Reducer Fixtures

**Goal**: Persist generated records to disk with overwrite/update/error semantics, emit the `RetrospectiveCaptured` / `RetrospectiveCaptureFailed` events, and prove FR-021's reducer byte-identical guarantee with a fixture set.

**Priority**: Foundation (P0).

**Independent test**: `uv run pytest tests/retrospective/test_writer.py tests/retrospective/test_events.py tests/retrospective/test_reducer_fixtures.py -q` exits 0.

**Requirements covered**: FR-008 (event payloads), FR-013 (summary distinctions), FR-014 (writer enforces invariant), FR-021, FR-025, NFR-007.

### Included subtasks

- [x] T013 Implement `writer.write_record(record, mode)` with overwrite/update/error semantics per data-model.md (WP03)
- [x] T014 Enforce `synthesize_fabricate ⇒ ran_no_findings` invariant in writer validation (WP03)
- [x] T015 Add `RetrospectiveCaptured` + `RetrospectiveCaptureFailed` event types (reuse if existing per FR-024 frozen surface, else add additively) (WP03)
- [x] T016 Verify reducer no-op behavior for retrospective events; add fixture set under `tests/retrospective/fixtures/event_logs/` per FR-025 (WP03)
- [x] T017 Unit tests for writer + events + reducer fidelity (FR-021/025) (WP03)

### Implementation sketch

1. Extend `src/specify_cli/retrospective/writer.py` with three modes:
   - `error` (default): refuse if record exists at canonical path
   - `overwrite`: replace
   - `update`: merge per data-model.md merge semantics (dedup by `(category, summary)`, append evidence_refs with new ids, accumulate `provenance_history[]`)
2. Validation step: reject any record where `provenance.kind == "synthesize_fabricate"` AND `findings_status != "ran_no_findings"`.
3. Investigate `spec_kitty_events` public surface (FR-024 frozen): if `RetrospectiveCaptured` or equivalent already exists, reuse with additive `policy_source` field. Otherwise add new event types in the local emit path that the canonical event log accepts.
4. Reducer fixture set: two fixtures — (a) historical mission with no retrospective events (baseline reduction); (b) same log with new retrospective events appended (additive — lane state byte-identical, additive top-level retrospective keys surface).
5. Tests assert: writer modes behave correctly; invariant rejects bad records; events round-trip through JSONL; reducer baselines hold.

### Parallel opportunities

T013 (writer) and T015 (events) can run in parallel — different files. T016 (fixtures) and T017 (tests) can scaffold in parallel.

### Dependencies & Risks

- **Dependencies**: WP02
- **Risks**: `spec_kitty_events` frozen surface — must confirm `RetrospectiveCaptured` is or isn't already exposed before adding. Mitigation: T015 starts with a `grep` on the consumed public surface, decisions land in WP03 review notes.

### Prompt

[tasks/WP03-writer-events-reducer.md](./tasks/WP03-writer-events-reducer.md)

---

## WP04 — Runtime Wiring: Default + Strict Gate Flows

**Goal**: Replace `facilitator_callback=None` with the real generator + policy pipeline. Default flow attempts post-completion generation (warn on failure); strict flow blocks pre-completion with structured policy_source citation. Anchor evaluation at the canonical "mission completion" point.

**Priority**: Runtime (P0).

**Independent test**: `uv run pytest tests/next/test_retrospective_terminus_wiring.py tests/integration/retrospective/ -q` exits 0.

**Requirements covered**: FR-001 (policy_source on events), FR-005, FR-008, FR-009, NFR-005 (latency budget), NFR-007.

### Included subtasks

- [x] T018 Replace `facilitator_callback=None` in `next/runtime_bridge.py` with real generator + policy wiring (FR-005) (WP04)
- [x] T019 Implement default post-completion flow: attempt → write+Captured event on success, warn+Failed event on failure (FR-008) (WP04)
- [x] T020 Implement strict pre-completion gate: block with policy_source citation; `--skip-retrospective` bypass with actor/provenance (FR-009) (WP04)
- [x] T021 Wire `policy_source` attribution on every emitted retrospective event (FR-001) (WP04)
- [x] T022 Anchor gate-evaluation point at canonical "mission completion" per data-model.md (immediately before `MissionCompleted` emit) (WP04)
- [x] T023 Wiring + integration tests under `tests/next/test_retrospective_terminus_wiring.py` and `tests/integration/retrospective/` (FR-005/008/009) (WP04)

### Implementation sketch

1. `next/runtime_bridge.py`: import the policy resolver + generator + writer + event emitter. Replace the `facilitator_callback=None` call site with a real callback that:
   - resolves policy via `RetrospectivePolicy` resolver
   - if `enabled: false`, no-op (return cleanly)
   - else attempts generation; persists record via writer; emits event with policy_source
2. `next/_internal_runtime/retrospective_terminus.py`: handle the default vs strict branch. Default = catch generator errors → emit Failed → return success (mission completion proceeds). Strict = bubble blocking reason to the runtime caller.
3. `--skip-retrospective` flag: surface on `spec-kitty merge` (or whichever command lands the `MissionCompleted` event). Bypass emits a `RetrospectiveSkipped` (or equivalent — confirm vs FR-024 surface) event with actor/provenance.
4. Wiring test asserts the import-graph regression: `facilitator_callback=None` is no longer reachable from any enabled policy path.
5. Integration tests scaffold a fake mission in `tmp_path` with realistic artifacts, run the completion path under default, strict-success, strict-failure, and opt-out policies; assert artifacts on disk + events in the log + exit codes / block messages.

### Parallel opportunities

T018 sequential (the wiring change). T019, T020 can branch in parallel once T018's interface settles. T023 (tests) runs in parallel with implementation.

### Dependencies & Risks

- **Dependencies**: WP01, WP02, WP03
- **Risks**: latency budget (NFR-005 ≤ 2s). Mitigation: T023 includes a wall-clock assertion in the default-flow integration test using a representative mission size.

### Prompt

[tasks/WP04-runtime-wiring.md](./tasks/WP04-runtime-wiring.md)

---

## WP05 — CLI: `retrospect create` / `backfill` / `summary` Tighten / `synthesize` Tighten

**Goal**: Ship the real authoring surfaces (`create`, `backfill`), tighten `summary` to distinguish 4 record states without semantic change, and replace `synthesize`'s silent fabrication fallback with a default-error path + explicit `--fabricate-empty` flag.

**Priority**: Surface (P0).

**Independent test**: `uv run pytest tests/cli/commands/test_retrospect.py -q` exits 0.

**Requirements covered**: FR-011, FR-012, FR-013, FR-014, NFR-002, NFR-003.

### Included subtasks

- [x] T024 [P] Implement `spec-kitty retrospect create --mission <handle>` per `contracts/retrospect-cli.contract.md` (FR-011) (WP05)
- [x] T025 [P] Add `--overwrite` / `--update` / `--json` flags + structured error codes for `create` (WP05)
- [x] T026 [P] Implement `spec-kitty retrospect backfill --since/--until --mission --dry-run --emit-skipped --emit-failures` (FR-012) (WP05)
- [x] T027 [P] Tighten `retrospect summary` to distinguish `has_findings` / `ran_no_findings` / `missing` / `failed` (FR-013, no semantic change) (WP05)
- [x] T028 [P] Tighten `agent retrospect synthesize` default-path error; add `--fabricate-empty` compat flag with actor-attributed provenance (FR-014) (WP05)
- [x] T029 [P] CLI tests covering all four surfaces + JSON contract assertions (WP05)

### Implementation sketch

1. New module `src/specify_cli/cli/commands/retrospect.py` registers `create` + `backfill` + (re-exports) `summary` under the `spec-kitty retrospect` Typer subapp.
2. `create`: resolve mission handle (mission_id > mid8 > slug), validate mission completion state, call generator, call writer with mode based on flags. JSON shape matches contracts.
3. `backfill`: iterate `kitty-specs/` directories; filter by `--since` / `--until` / `--mission`. Skip with structured reasons. Use Rich progress bar (NFR; respect `--json` mode by emitting per-mission JSON lines or a single aggregate object).
4. `summary` (existing): extend with `findings_status` per record and an aggregate that distinguishes the four states.
5. `agent_retrospect.py` `synthesize`: when no record exists, return the structured `RETROSPECTIVE_RECORD_MISSING` error from contracts. `--fabricate-empty` preserves legacy behavior, logs provenance.
6. Tests use the Typer test client; verify JSON contract shapes byte-for-byte against fixtures.

### Parallel opportunities

T024, T026, T027, T028 are different command implementations — can ship in parallel by different agents/sessions. T025 is part of T024's command shape. T029 (tests) runs in parallel.

### Dependencies & Risks

- **Dependencies**: WP02, WP03
- **Risks**: backfill at scale (≥ 100 missions) — should not OOM or hang. Mitigation: progress reporting via Rich; per-mission JSON streaming in JSON mode.

### Prompt

[tasks/WP05-cli-surfaces.md](./tasks/WP05-cli-surfaces.md)

---

## WP06 — Env-Var Deprecation + Shim Retirement

**Bulk-edit carrier (shape A)**: env-var deprecation messaging.

**Goal**: Demote `SPEC_KITTY_RETROSPECTIVE` and `SPEC_KITTY_MODE` to test/dev-only overrides with one-warning-per-process noise budget. Refactor tests to inject `RetrospectivePolicy` directly. Resolve the fate of legacy `retrospective/config.py` and `retrospective/mode.py` per FR-023 — no half-deleted state.

**Priority**: Surface (P0).

**Independent test**: `uv run pytest tests/retrospective/test_env_deprecation.py -q` exits 0.

**Requirements covered**: FR-015, FR-016, FR-023, NFR-006.

### Included subtasks

- [ ] T030 [P] Implement `DeprecationWarning` + Rich stderr notice for `SPEC_KITTY_RETROSPECTIVE` / `SPEC_KITTY_MODE` (FR-015, NFR-006: one warning per process) (WP06)
- [ ] T031 [P] Add `SPEC_KITTY_NO_DEPRECATION_WARNINGS=1` suppression env var; documented in WP07 docs (WP06)
- [ ] T032 [P] Refactor existing tests to prefer injected `RetrospectivePolicy` over `os.environ` mutations (FR-016) (WP06)
- [ ] T033 [P] Resolve shim fate for `retrospective/config.py` + `retrospective/mode.py` per FR-023 — either fold+delete with reference updates, OR retain as documented compat shim with explicit retirement target (deprecation version, follow-up issue, rationale) (WP06)
- [ ] T034 [P] Tests for deprecation behavior: one-warn-per-process, durable wins, suppression flag (WP06)

### Implementation sketch

1. Add a process-level `_DEPRECATION_EMITTED` set; the deprecation helper emits once per env-var name per process.
2. Deprecation message: `python warnings.warn(...)` plus a Rich `console.print` to stderr. Suppressed when `SPEC_KITTY_NO_DEPRECATION_WARNINGS=1`.
3. Test refactor: replace `monkeypatch.setenv("SPEC_KITTY_RETROSPECTIVE", "1")` with direct `RetrospectivePolicy(enabled=True, ...)` construction. Keep one dedicated test module for the deprecation behavior itself.
4. Shim decision (T033) — runtime is the implementer's call between (a) and (b) of FR-023:
   - **(a) Fold+delete**: imports of `from specify_cli.retrospective.config import …` and `from specify_cli.retrospective.mode import …` updated to the new `policy` module; `config.py` and `mode.py` removed; PR notes the shim retirement.
   - **(b) Retain shim**: `config.py` and `mode.py` become thin re-exports from `policy`; ADR-grade note in the module docstring with deprecation target version (e.g. 3.3.0) and a follow-up issue link.
   - Either decision is acceptable; "half-deleted" is not.

### Parallel opportunities

T030, T031, T032, T033 are different concerns and parallelizable. T034 (tests) parallel.

### Dependencies & Risks

- **Dependencies**: WP01
- **Bulk-edit carrier**: env-var references across code, tests, and docs are the bulk-edit shape A. `occurrence_map.yaml` enumerates each occurrence with action. See [occurrence_map.yaml](./occurrence_map.yaml) (lands at finalize-tasks).

### Prompt

[tasks/WP06-env-deprecation-shim-retirement.md](./tasks/WP06-env-deprecation-shim-retirement.md)

---

## WP07 — Docs + Shipped Skills + CONTRIBUTING Note

**Bulk-edit carrier (shape B)**: doc semantics correction (summary/create/backfill/synthesize).

**Goal**: Update operator-facing docs to reflect the four distinct CLI semantics. Correct PR #1136 wording in-place. Update 4 shipped skills. Review and refine the `retrospective-facilitator.agent.yaml` boundaries. Add the #1137 namespace-package diagnostic note to CONTRIBUTING.md.

**Priority**: Polish (P1).

**Independent test**: `uv run markdownlint --config .markdownlint-cli2.jsonc <touched-paths>` exits 0 (NFR-008); the documented commands in updated how-tos succeed against a fresh project (smoke).

**Requirements covered**: FR-017, FR-018, FR-019, FR-020, FR-022, NFR-008.

### Included subtasks

- [ ] T035 [P] Update `docs/how-to/use-retrospective-learning.md` as canonical operator how-to (FR-018) (WP07)
- [ ] T036 [P] Update `docs/how-to/accept-and-merge.md` (correct PR #1136 wording) + `docs/how-to/merge-feature.md` (FR-018) (WP07)
- [ ] T037 [P] Update `docs/explanation/retrospective-learning-loop.md` + `docs/reference/cli-commands.md` + `docs/reference/slash-commands.md` (FR-018) (WP07)
- [ ] T038 [P] Update `README.md` retrospective blurb + `docs/tutorials/your-first-feature.md` (FR-018) (WP07)
- [ ] T039 [P] Update 4 shipped skills: `spec-kitty-mission-review`, `spec-kitty-implement-review`, `spec-kitty-program-orchestrate`, `spec-kitty-runtime-next` (FR-019) (WP07)
- [ ] T040 [P] Review `retrospective-facilitator.agent.yaml`; align boundaries/permissions with FR-001/FR-010 if drift exists (FR-020) (WP07)
- [ ] T041 [P] Add `CONTRIBUTING.md` namespace-package diagnostic note for #1137 (FR-017) (WP07)

### Implementation sketch

1. Each doc edit replaces the "summary captures retrospective learning" framing with the four-category canonical narrative: `summary` aggregates → `create` authors → `backfill` historical-authors → `synthesize` previews/applies proposals from an existing record.
2. PR #1136 wording lives in `docs/how-to/accept-and-merge.md` — update in place; reference `quickstart.md` from this mission for examples.
3. Skill files: edit the post-merge guidance to say "mission review → author or verify retrospective (`retrospect create`) → surface findings (`summary` aggregates; `synthesize` reviews proposals)" in that order. Reserve the noun "capture" for the event-log fact (`RetrospectiveCaptured`), not the operator verb.
4. `retrospective-facilitator.agent.yaml`: re-read against FR-001 (policy resolver) and FR-010 (no auto-application of structural changes). Adjust permission flags or boundary text only if real drift exists; do not rewrite the profile structurally.
5. CONTRIBUTING.md: append the diagnostic per [research.md R-7 and #1137 closing comment]:

   ```bash
   python -c "import spec_kitty_events; print(spec_kitty_events.__file__, spec_kitty_events.__path__)"
   # Healthy:   prints a path ending in __init__.py
   # Corrupt:   prints None + _NamespacePath(...)  -- this is the FR-024 namespace-package state
   uv sync --reinstall-package spec-kitty-events
   ```

### Parallel opportunities

All seven subtasks touch different files — fully parallelizable.

### Dependencies & Risks

- **Dependencies**: WP04, WP05
- **Bulk-edit carrier**: doc semantics across docs/ and src/doctrine/skills/ is the bulk-edit shape B. Tracked in [occurrence_map.yaml](./occurrence_map.yaml).

### Prompt

[tasks/WP07-docs-skills-contributing.md](./tasks/WP07-docs-skills-contributing.md)

---

## Phasing & Lane Structure

Computed lanes land at finalize-tasks time via `lanes.json`. After this mission's first finalize pass, the actual result is a **single lane `lane-a`** containing all 7 WPs, collapsed by the dependency-rule collapser. Reason: every WP transitively depends on WP01 (via the resolver surface), so the lane computer fuses the entire chain into one execution worktree.

Implication: this mission executes **serially** in `.worktrees/<mission-slug>-lane-a` — one WP at a time, no cross-WP parallelism. Within a single WP, the `[P]` markers in the Subtask Index still indicate parallelism opportunities (e.g. multiple unrelated docs in WP07), but those are sequential subtask choices for one agent, not multi-agent dispatch.

Sequence (by parsed dependency graph):

1. WP01 (foundation) →
2. WP02 (depends on WP01) →
3. WP03 (depends on WP02) →
4. WP04 (depends on WP01, WP02, WP03) →
5. WP05 (depends on WP02, WP03) — could in principle run alongside WP04, but lane collapse keeps them serial →
6. WP06 (depends on WP01) — same; lane collapse keeps it serial →
7. WP07 (depends on WP04, WP05) →
8. Mission review.

An operator who wants real parallelism after the foundation lands can re-finalize with explicit `--no-collapse` (if such a flag exists) or split the mission post-merge. As written, the safer choice is to honor the collapser's output.

## Bulk-Edit Plan (FR-022)

Two bulk-edit shapes per the [plan.md](./plan.md#bulk-edit-classification-fr-022) classification:

- **Shape A — Env-var deprecation messaging** (carrier: WP06). `SPEC_KITTY_RETROSPECTIVE` and `SPEC_KITTY_MODE` are referenced in env reads, tests, and docs. Re-frame as "test/dev override; durable replacements in `retrospective.enabled` and `retrospective.timing`+`retrospective.failure_policy`."
- **Shape B — Doc semantics correction** (carrier: WP07). The phrases "summary captures retrospective learning" and "synthesize generates the retrospective" are split into four distinct category semantics across docs and shipped skills.

`occurrence_map.yaml` lands as part of `/spec-kitty.tasks` finalization with all 8 standard categories (code_symbols, import_paths, filesystem_paths, serialized_keys, cli_commands, user_facing_strings, tests_fixtures, logs_telemetry) covered.

## Next

After finalization commits this file and the WP prompts, the next step is `/spec-kitty.implement` to start the implement-review loop, or invoke the `spec-kitty-implement-review` skill to run all WPs to completion in one orchestrated pass.
