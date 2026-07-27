# Implementation Plan: Phase 3 Charter Synthesizer Pipeline

**Branch**: `main` (planning and eventual merge target) | **Date**: 2026-04-17 | **Spec**: `/Users/robert/spec-kitty-dev/charter2/spec-kitty/kitty-specs/phase-3-charter-synthesizer-pipeline-01KPE222/spec.md`
**Input**: [spec.md](./spec.md) · 20 FR, 10 NFR, 12 C · 8 user scenarios · 7 edge cases

## Summary

Deliver a two-layer **Charter Synthesizer** that turns charter interview answers, shipped doctrine, and the shipped Doctrine Reference Graph (DRG) into project-local **directives**, **tactics**, and **styleguides**. Artifact **content** (directive / tactic / styleguide YAMLs and the project DRG overlay) lands under `.kittify/doctrine/` — the tree the existing doctrine repositories and `_drg_helpers` already recognise as a project layer. Synthesis **bookkeeping** (per-artifact provenance sidecars, the commit-marker manifest, and ephemeral staging) lands under `.kittify/charter/` so doctrine consumers see only doctrine and bundle consumers see only bundle state. Orchestration — input normalization, target selection, write staging, validation, path-guard enforcement, topic resolution, manifest commit — is fully deterministic. The actual prose generation is model-driven but lives behind a narrow sync adapter interface with fixture-backed test coverage. The whole pipeline fails closed on schema, DRG, or path-guard violations using a stage-and-promote atomicity model with **manifest-last** as the authoritative commit marker.

Scope is intentionally bounded: `directive`, `tactic`, `styleguide` only; WP3.1/3.2/3.6/3.7/3.8 only; structured `--topic` selectors only; no code-reading, no URL fetching, no free-text topic rewriting, no cross-repo visibility, no migration tooling.

## Technical Context

**Language/Version**: Python 3.11+ (existing spec-kitty baseline)
**Primary Dependencies (existing, reused)**: `typer` (CLI), `rich` (console), `ruamel.yaml` (YAML parsing with preserved ordering/anchors), `pydantic` v2 (schemas), `blake3` (already in charter for hashing), `pytest` (tests), `mypy` strict (type-check)
**New Dependencies**: **None**. No new runtime or test dependency is added by this tranche. The production model adapter's backing client (governed by ADR-6, #521) is a *soft* dependency and lives outside this mission's merge gate.
**Storage**: Filesystem only. New paths under `.kittify/doctrine/` (synthesized content — directives, tactics, styleguides, project DRG graph), `.kittify/charter/` (synthesis bookkeeping — provenance, manifest, staging), and `tests/charter/fixtures/synthesizer/` (test fixtures). No database, no network, no queue.
**Testing**: `pytest`, `mypy --strict`, existing charter/doctrine test harnesses. 100% of tests run with the fixture adapter; no network calls in CI.
**Target Platform**: Local developer machines + CI (Linux + macOS + Windows per existing spec-kitty matrix; the staging/atomic-promote model uses `os.replace` which is POSIX-on-POSIX + atomic-rename-on-Windows).
**Project Type**: Single project (extends existing `src/charter/` package).
**Performance Goals**:
- Full synthesis on a ≤10-answer interview (fixture adapter): < 30s wall-clock (NFR-002).
- Bounded `resynthesize --topic`: < 15s wall-clock (NFR-003).
- Fail-closed from detected violation to return: < 5s (NFR-004).
**Constraints**:
- Zero writes outside `.kittify/doctrine/` (content) and `.kittify/charter/` (bookkeeping) (NFR-008 / C-001 / C-002).
- Zero dangling refs in any committed project DRG layer (NFR-009 / FR-008).
- Zero network calls from the test suite (NFR-010 / C-003).
- `mypy --strict` clean (NFR-007) and ≥ 90% line coverage on orchestration code (NFR-001).
**Scale/Scope**: Small. Tens of artifact files per project at steady state. Dozens of DRG overlay edges. Individual artifact bodies measured in kilobytes, not megabytes. This is not a throughput problem; it is a correctness and determinism problem.

## Charter Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

Charter present at `/Users/robert/spec-kitty-dev/charter2/spec-kitty/.kittify/charter/charter.md`.

| Directive / Tactic | Applicability | Status |
|---|---|---|
| **DIRECTIVE_003 — Decision Documentation** | ADR coverage is material for this mission's load-bearing choices. | **PASS (with action)**: one ADR will be drafted during Phase 1 covering the adapter seam + atomicity model (see Phase 1 output). Module ownership (Q1), atomicity (Q2), and adapter shape (Q3) decisions are captured here in §"Key Decisions" with rationale and rejected alternatives. |
| **DIRECTIVE_010 — Specification Fidelity** | Plan must not contradict spec. | **PASS**: no deviation from 20 FRs, 10 NFRs, 12 Cs; plan only resolves HOW, not WHAT. |
| **adr-drafting-workflow** | Model-selection boundary + atomicity mechanism qualify. | **PASS**: ADR drafting scheduled as part of WP3.1 entry gate (see §"Phase 1 Outputs"). |
| **problem-decomposition** | Already applied — mission decomposed into five coherent WPs with explicit deferrals for WP3.3/3.4/3.5. | **PASS**. |
| **premortem-risk-identification** | R-1…R-6 in spec §11 plus premortem in §"Risks & Premortem" below. | **PASS**. |
| **requirements-validation-workflow** | Every FR traces to at least one US/SC/EC; every NFR carries a threshold. | **PASS** (verified via spec checklist). |
| **review-intent-and-risk-first** | Downstream review order captured in §"Review & Validation Strategy". | **PASS**. |
| **stakeholder-alignment** | Operator, downstream agent, reviewer/mission owner are the stakeholder set; surface interactions are explicit via user scenarios US-1…US-8. | **PASS**. |
| **eisenhower-prioritisation** | WP order (3.1 → 3.2 → 3.6 / 3.7 in parallel → 3.8) reflects importance × unblocking impact. | **PASS**. |
| **Policy — 90% coverage** | Applies to new orchestration code. | **PASS** (NFR-001). |
| **Policy — mypy --strict** | Applies to all new modules. | **PASS** (NFR-007). |
| **Policy — integration tests for CLI commands** | `synthesize` and `resynthesize --topic` both land as CLI commands. | **PASS**: integration tests specified in §"Review & Validation Strategy". |

**No violations. No Complexity Tracking entries required.**

## Key Decisions (locked in planning interrogation)

### KD-1 · Module ownership — single-owner with thin DRG delegation

All synthesizer code lives under `src/charter/synthesizer/`. `src/doctrine/drg/` remains the stable primitives layer — models, loader, validator, query, `merge_layers` — and gains no new code in this mission. The charter-side `project_drg.py` is a thin composer that calls existing doctrine primitives; if it starts inventing reusable DRG write semantics, that is the signal to extract later, not now.

**Rationale**: keeps Phase 3 coherent as a charter feature; correct dependency direction (`charter` → `doctrine/drg`); avoids premature fragmentation across two ownership trees; leaves a clean extraction path later.

**Rejected alternatives**:
- (A) single-owner, no delegation boundary — allowed generic graph logic to leak into charter; bad for eventual extraction.
- (B) cross-package split with DRG write code under `src/doctrine/drg/project_layer.py` — forced doctrine to change in lockstep with a charter-only feature; rejected as premature.

### KD-2 · Atomicity — stage + ordered promote, manifest-last commit

Every synthesis run stages **all** writes (content and bookkeeping) under a single root at `.kittify/charter/.staging/<runid>/`, with the promote step demultiplexing into the final locations: content files land under `.kittify/doctrine/`, bookkeeping files under `.kittify/charter/`. Full validation runs against the staged tree; only on pass does the pipeline promote via ordered `os.replace` calls, writing the final **synthesis manifest** (at `.kittify/charter/synthesis-manifest.yaml`) last. The synthesis manifest is the authoritative "this bundle is valid and committed" marker. Readers that encounter a missing or internally inconsistent manifest treat the synthesized content as partial-and-rerunable, not authoritative.

**Constraint**: the live tree is never read as authoritative unless the manifest is present *and* internally consistent with the promoted files (manifest lists artifact URNs + content hashes; reader verifies hash-match before trusting).

**Staging-dir disposition**:
- Success → staging dir wiped.
- Failure (validation, adapter error, SIGKILL, disk full) → staging dir preserved with a `.failed` sibling marker for operator diagnosis.

**Rejected alternatives**:
- Pure in-memory stage — no recovery story for partial writes on SIGKILL or disk-full.
- Journal + replay — correct but overkill for kilobyte-scale writes; dragged complexity into Phase 3 without buying anything over (B).

### KD-3 · Adapter interface — sync, one-shot + optional batch, override-first provenance identity

Minimum contract:
```python
class SynthesisAdapter(Protocol):
    id: str
    version: str
    def generate(self, request: SynthesisRequest) -> AdapterOutput: ...
    # Optional; orchestration detects presence at runtime.
    def generate_batch(self, requests: Sequence[SynthesisRequest]) -> Sequence[AdapterOutput]: ...
```

Orchestration is synchronous. When `generate_batch` is present on an adapter, orchestration uses it; otherwise it falls back to sequential `generate` calls. No asyncio introduction in this tranche.

`AdapterOutput` carries optional `adapter_id_override` and `adapter_version_override` so long-lived adapters that rotate models can stamp per-call identity. Orchestration records whichever identity was effective for that call.

### KD-4 · Fixture-adapter keying — `<kind>/<slug>/<blake3-short>.yaml`, normalized inputs

Fixtures live at `tests/charter/fixtures/synthesizer/<kind>/<slug>/<blake3-short>.yaml`. The hash is computed over the **normalized** `SynthesisRequest` — fields in canonical order, stable JSON serialization, no mutable ordering — so semantically identical requests do not fragment fixtures.

The fixture adapter computes the expected path for each incoming request and fails loudly with the expected path when the fixture is missing: `FixtureAdapterMissingError(expected_path=..., kind=..., slug=..., inputs_hash=...)`. This makes fixture authoring ergonomic: operator runs once, captures output, checks it in at the exact printed path.

### KD-5 · Fail-closed path-guard integrated at write seam

The write seam (`PathGuard` class) wraps every filesystem mutation path inside the synthesizer. Any attempted write under `src/doctrine/` raises `PathGuardViolation` *before* the filesystem is touched. The guard is testable at the unit level — orchestration does not gain "smart" write logic; it goes through the guard.

### KD-6 · ADR set scheduled for WP3.1

Two ADRs are required before WP3.1 can merge (DIRECTIVE_003):
- **ADR-<date>-1: Charter Synthesizer — Adapter Seam and Provenance Identity** — documents KD-3, KD-4 and the narrow seam rationale.
- **ADR-<date>-2: Charter Synthesizer — Atomicity via Stage + Ordered Promote + Manifest-Last Commit** — documents KD-2, including rejected alternatives and recovery semantics.

Both ADRs follow the existing `architecture/adrs/` naming convention. ADR-6 (synthesizer model selection, #521) is referenced but *not authored* by this mission.

## Project Structure

### Documentation (this feature)

```
kitty-specs/phase-3-charter-synthesizer-pipeline-01KPE222/
├── spec.md                 # /spec-kitty.specify output (complete)
├── plan.md                 # This file (/spec-kitty.plan output)
├── research.md             # Phase 0 output (this command)
├── data-model.md           # Phase 1 output (this command)
├── quickstart.md           # Phase 1 output (this command)
├── contracts/              # Phase 1 output (this command)
│   ├── adapter.py          # SynthesisAdapter Protocol + AdapterOutput dataclass shape
│   ├── provenance.schema.yaml  # Provenance record schema (documented, not code)
│   ├── synthesis-manifest.schema.yaml  # Manifest schema (commit marker)
│   └── topic-selector.md   # Structured selector grammar + error-shape contract
├── checklists/
│   └── requirements.md     # Spec quality checklist (complete, all pass)
└── tasks.md                # (NOT created here — /spec-kitty.tasks)
```

### Source Code Layout (new + modified)

**New package** — `src/charter/synthesizer/`:

```
src/charter/synthesizer/
├── __init__.py             # Public API re-exports (orchestrator.synthesize, resynthesize, errors)
├── orchestrator.py         # Top-level entry points: synthesize() + resynthesize(topic)
├── request.py              # SynthesisRequest, SynthesisTarget dataclasses + normalize()
├── adapter.py              # SynthesisAdapter Protocol + AdapterOutput dataclass
├── fixture_adapter.py      # FixtureAdapter + FixtureAdapterMissingError
│                           #   (lives in src/ not tests/ so integration tests can import it,
                            #    but it is only wired in test entrypoints — never in production CLI path)
├── interview_mapping.py    # Interview answer → list[SynthesisTarget] mapping
├── targets.py              # target selection + ordering
├── provenance.py           # Provenance dataclass + writer + reader
├── project_drg.py          # THIN composer over src/doctrine/drg primitives
│                           #   (emit_project_layer, validate_merged, persist)
├── topic_resolver.py       # TopicSelector parsing + 3-tier resolution
├── staging.py              # Staging dir lifecycle + ordered-promote
├── manifest.py             # SynthesisManifest schema + write/read
├── path_guard.py           # PathGuard + PathGuardViolation
└── errors.py               # Structured error taxonomy (synthesis-scoped)
```

**Modified existing files**:

```
src/charter/compiler.py          # FR-009: extend _default_doctrine_service project-root candidate list
                                 #   to include .kittify/doctrine/ (in addition to repo_root/src/doctrine
                                 #   and repo_root/doctrine). Discovery is conditional on directory presence.
src/charter/context.py           # FR-009 / FR-018: extend _build_doctrine_service with the same candidate.
src/charter/_drg_helpers.py      # Already reads .kittify/doctrine/graph.yaml for the project DRG layer;
                                 #   no change required. Listed here as a touchpoint for reviewers, not a diff.
src/charter/bundle.py            # FR-015: manifest-v1 gains optional synthesis-bridging fields that cross
                                 #   the .kittify/charter/ ↔ .kittify/doctrine/ boundary (backwards-compatible).
src/specify_cli/cli/commands/charter.py  # FR-010 / FR-011: add `synthesize` and `resynthesize` subcommands
```

**DO NOT TOUCH** (constraint):

```
src/doctrine/**       # read-only at runtime; KD-1 preserves stable primitives
```

**Tests**:

```
tests/charter/synthesizer/
├── __init__.py
├── conftest.py                              # shared fixtures (doctrine snapshot, drg snapshot)
├── test_orchestrator_synthesize.py          # US-1, US-8; FR-001/002/005/006/014
├── test_orchestrator_resynthesize.py        # US-2, US-3, US-4; FR-011/012/017
├── test_adapter_contract.py                 # FR-003
├── test_fixture_adapter.py                  # KD-4; FixtureAdapterMissingError diagnostics
├── test_interview_mapping.py                # interview-section → target mapping (plus A-3 sentinel)
├── test_provenance.py                       # FR-006, NFR-006 (byte-reproducibility)
├── test_project_drg.py                      # FR-007 / FR-020; additive-only invariants
├── test_topic_resolver.py                   # FR-012 / FR-013; ambiguous + unresolvable + zero-match
├── test_staging_atomicity.py                # KD-2; US-5 fail-closed; EC-5 interrupted run
├── test_manifest.py                         # manifest-last commit marker, hash verification
├── test_path_guard.py                       # FR-016 / NFR-008 / US-7
├── test_validation_gate.py                  # FR-008 / NFR-009; dangling-ref / duplicate / cycle
├── test_schema_conformance.py               # FR-019 / NFR-005
├── test_context_reflects_synthesis.py       # FR-018 / SC-005 (end-to-end observable difference)
├── test_bundle_validate_extension.py        # FR-015
├── test_charter_compile_project_root.py     # FR-009
├── test_performance_envelopes.py            # NFR-002/003/004
└── fixtures/
    └── synthesizer/
        ├── directive/<slug>/<hash>.directive.yaml   # per-target fixtures (extension matches
        ├── tactic/<slug>/<hash>.tactic.yaml         #   shipped repository globs so fixtures
        └── styleguide/<slug>/<hash>.styleguide.yaml #   round-trip through the same loaders)

tests/agent/cli/commands/
├── test_charter_synthesize_cli.py           # CLI integration: synthesize
└── test_charter_resynthesize_cli.py         # CLI integration: resynthesize --topic
```

**Structure Decision**: Single-project extension. All new code lives under `src/charter/synthesizer/` as a self-contained subpackage. All tests live under `tests/charter/synthesizer/` mirroring the module layout. Cross-package edits are limited to *extending a candidate list* in `src/charter/compiler.py` and `src/charter/context.py` (FR-009); `src/doctrine/**` is strictly read-only.

**Storage Decision (Path D)**: Synthesized artifact content (directives, tactics, styleguides, project DRG graph) is written under `.kittify/doctrine/` using filenames that match the existing repository globs (`*.directive.yaml`, `*.tactic.yaml`, `*.styleguide.yaml`, plus `graph.yaml`). This is the tree the existing `DirectiveRepository`, `TacticRepository`, `StyleguideRepository`, and `_drg_helpers` project-layer loader already recognise — no consumer-side reshape is required beyond extending the project-root candidate list. Synthesis bookkeeping (per-artifact provenance sidecars at `.kittify/charter/provenance/`, commit-marker manifest at `.kittify/charter/synthesis-manifest.yaml`, ephemeral staging at `.kittify/charter/.staging/<runid>/`) is kept separate so `bundle validate` can bridge the two trees without doctrine loaders seeing bundle artifacts.

**Directive ID scheme (provisional, tranche-1 default)**: Synthesized directives use `PROJECT_<NNN>` IDs (matches `Directive.id` regex `^[A-Z][A-Z0-9_-]*$`; disjoint from shipped `DIRECTIVE_<NNN>`). The scheme is not locked — if the WP3.2 implementation finds semantic IDs produce cleaner provenance, the regex accepts alternatives without a plan change.

## Phase 0: Research

See [research.md](./research.md) for the consolidated findings. All questions below are resolved there — no outstanding `[NEEDS CLARIFICATION]` markers remain.

**Questions resolved in Phase 0**:
1. R-0-1: What interview-answer surfaces drive which artifact kinds? (Interview → target mapping table)
2. R-0-2: Where does the project DRG layer live on disk? (Canonical path decision)
3. R-0-3: Provenance storage format — single file or per-artifact sidecar? (Format decision)
4. R-0-4: Bundle manifest extension — v1.0.0 additive vs v1.1.0 bump? (Extension strategy)
5. R-0-5: Production-adapter fallback — what happens when no production adapter is configured? (Fallback semantics)
6. R-0-6: Minimum content-hash hygiene — which blake3 variant, how short is "short"? (Hash spec)
7. R-0-7: Existing DRG validator error shape — does it already give us enough to surface structured errors? (Validator reuse)

## Phase 1: Design & Contracts

Generated Phase 1 artifacts:

- **[data-model.md](./data-model.md)** — concrete entity shapes (`SynthesisRequest`, `SynthesisTarget`, `AdapterOutput`, `ProvenanceEntry`, `SynthesisManifest`, `ProjectDRGOverlay`, `TopicSelector`, error taxonomy), field-by-field, with validation rules and invariants.
- **[contracts/adapter.py](./contracts/adapter.py)** — `SynthesisAdapter` Protocol + `AdapterOutput` dataclass. This is the frozen seam contract; changes require an ADR amendment.
- **[contracts/provenance.schema.yaml](./contracts/provenance.schema.yaml)** — YAML schema for provenance entries.
- **[contracts/synthesis-manifest.schema.yaml](./contracts/synthesis-manifest.schema.yaml)** — YAML schema for the commit-marker manifest.
- **[contracts/topic-selector.md](./contracts/topic-selector.md)** — structured-selector grammar + error-shape contract.
- **[quickstart.md](./quickstart.md)** — operator quickstart for a fresh-project synthesis + a targeted resynthesis.

**Post-Phase-1 Charter Re-Check**: re-ran §"Charter Check" after Phase 1 artifacts existed. No new violations surfaced. Adapter seam and atomicity model are now concrete enough that the scheduled ADRs (ADR-<date>-1, ADR-<date>-2) have authored-ready material — those ADRs will be drafted inside WP3.1 before the WP closes.

## Review & Validation Strategy

Validation is layered so the adapter's non-determinism never contaminates the deterministic surface.

| Layer | Covers | How |
|---|---|---|
| **Adapter seam** | FR-003, FR-004, KD-3 | Protocol conformance tests; fixture adapter round-trip. |
| **Fixture keying** | KD-4 | Hash-stability tests; missing-fixture diagnostic tests. |
| **Interview mapping** | FR-001, FR-002 | Table-driven; one test per interview section → target-kind pair. |
| **Provenance** | FR-006, NFR-006 | Byte-reproducibility under fixed inputs; round-trip read-back. |
| **Staging / atomicity** | KD-2, FR-008, EC-5 | Inject failures at stage / validation / promote; assert atomic rollback; assert manifest-last semantics; simulate SIGKILL via partial-write fixtures. |
| **Path guard** | FR-016, NFR-008, US-7 | Table-driven negative tests over every write site in the synthesizer. |
| **Project DRG** | FR-007, FR-008, FR-020, NFR-009 | Accept / reject-dangling / reject-duplicate / reject-cycle cases; additive-only assertion via shipped-graph snapshot diffing. |
| **Topic resolver** | FR-012, FR-013, US-6, SC-008 | One test per tier × (hit / miss / ambiguous / zero-match) — 12 cells minimum. |
| **Schema conformance** | FR-019, NFR-005 | Adapter produces invalid body → orchestration rejects before provenance write. |
| **Context observability** | FR-018, SC-005 | Run full synthesis → invoke `charter context --action specify` → assert at least one project-specific item present. |
| **Bundle validate** | FR-015 | Regression fixtures for valid / orphan-artifact / orphan-provenance / schema-invalid bundles. |
| **CLI integration** | FR-010, FR-011 | `typer` CLI runners for `synthesize` and `resynthesize --topic` with subprocess-level assertions. |
| **Performance envelopes** | NFR-002, NFR-003, NFR-004 | CI-tolerant timing assertions using fixture adapter; thresholds at spec values. |
| **Determinism** | FR-014, NFR-006 | Identical-inputs run produces byte-identical provenance + artifact hashes. |

Review order for each WP follows `review-intent-and-risk-first`: intent summary → invariants touched → risk surface → code changes → tests.

## Work Package Breakdown

Concrete plan-level view. Final WP files are authored by `/spec-kitty.tasks`; this table is the scope anchor + dependency contract.

| WP | Title | Scope | Depends on | Parallelisable with |
|---|---|---|---|---|
| **WP3.1** | Synthesizer skeleton + provider seam + path guard | `src/charter/synthesizer/{adapter,fixture_adapter,path_guard,request,errors}.py`; `orchestrator.py` skeleton with write stubs; both ADRs drafted; fixture-adapter diagnostics landed; test harness scaffolded. | none | — |
| **WP3.2** | Interview-driven synthesis path | `interview_mapping.py`, `targets.py`; orchestrator.synthesize() populated end-to-end but writes are still stubbed; adapter calls real; provenance objects assembled in memory. | WP3.1 | — |
| **WP3.6** | Project-local artifact storage + provenance writer | `provenance.py`, `staging.py`, `manifest.py`; staging→promote→manifest-last pipeline; filesystem layout under `.kittify/charter/`; bundle.py extension for FR-015; `charter bundle validate` updates. | WP3.2 (artifact body contract) | WP3.7 |
| **WP3.7** | Project DRG layer writer + no-dangling-ref enforcement | `project_drg.py` (thin composer over `src/doctrine/drg`); validation-gate wiring before staging promote; additive-only enforcement; DoctrineService `project_root` activation in `compiler.py`/`context.py`. | WP3.2 (artifact → URN mapping) | WP3.6 |
| **WP3.8** | `spec-kitty charter resynthesize --topic <selector>` | `topic_resolver.py`; CLI command `resynthesize`; bounded-recomputation orchestrator path; diagnostic UX for ambiguous / zero-match / unresolvable selectors. | WP3.6 + WP3.7 durable | — |

**Sequencing invariant**: WP3.1 must merge before WP3.2/3.6/3.7/3.8 begin. WP3.6 and WP3.7 run in parallel once WP3.2's artifact-body contract is frozen. WP3.8 depends on WP3.6+WP3.7 committed.

**Execution-lane hint (for `/spec-kitty.tasks`)**: two natural lanes — Lane A: WP3.1 → WP3.2 → WP3.6 → WP3.8; Lane B: WP3.7. Lane B rejoins the main sequence at the WP3.6/3.7 sync point before WP3.8 begins. Final lane assignment is the `tasks` phase's job; this is guidance, not prescription.

## Risks & Premortem

Applying `premortem-risk-identification` — "imagine this mission failed in six months; why?"

| Risk | Premortem scenario | Mitigation in this plan |
|---|---|---|
| **R-1 · Seam leak** | "The adapter interface turned out to carry prompt-engineering logic, so production + fixture adapters diverged in non-obvious ways and CI passed while production regressed." | KD-3 freezes `generate` / `generate_batch` as the sole entry points; prompt shaping lives inside each adapter implementation. Contracts file `contracts/adapter.py` is the frozen source of truth. |
| **R-2 · DoctrineService candidate-list ripple** | "Extending the project-root candidate list surfaced `.kittify/doctrine/` as a project layer for projects that never ran `charter synthesize`, and the empty directory caused surprising downstream behaviour." | FR-009 discovery is **conditional on directory presence**: if `.kittify/doctrine/` does not exist, the candidate is skipped and `DoctrineService` falls back to the existing `src/doctrine` / `doctrine` candidates exactly as today. Legacy projects see byte-identical behaviour until they run `charter synthesize`. `test_charter_compile_project_root.py` locks this: (a) no `.kittify/doctrine/` → same project_root as 3.x today; (b) `.kittify/doctrine/` present → project_root points there; (c) empty `.kittify/doctrine/` → project_root points there but repositories resolve to empty overlays with no shipped-layer impact. |
| **R-3 · Bundle manifest drift** | "Bundle v1.0.0 consumers broke because the synthesized block was interpreted as a schema bump." | R-0-4 resolves to additive-only extension. `bundle.py` changes preserve v1.0.0 schema_version; new fields are optional. Regression fixtures in `test_bundle_validate_extension.py` pin backwards-compat. |
| **R-4 · Provenance brittle under model churn** | "Adapter id rotated in production and every provenance entry became untrustworthy." | KD-3 makes adapter id + version first-class provenance fields with per-call override; invalidation is observable. |
| **R-5 · Topic-selector ambiguity** | "Operators pushed back on structured-only selectors and we added free-text support without the right error UX." | C-004 (free-text rejection) + FR-013 (structured error enumerating candidates) make the affordance teachable; SC-008 gives a testable threshold. |
| **R-6 · ADR-6 dependency creep** | "WP3.1 stalled waiting for ADR-6 to resolve model policy, blocking the whole tranche." | C-006 + KD-6: this mission ships with a pinned default adapter and fixture adapter. ADR-6 resolves the *production policy*, not the architecture. |
| **R-7 · Staging-dir accumulation** | "Failed runs left `.staging-*` dirs behind and eventually filled `.kittify/charter/`." | KD-2 preserves failed staging with a `.failed` marker; add a `charter doctor` extension (out of scope for this mission but flagged) OR a staging-dir size warning in `bundle validate`. Noted in research.md §R-0-8 as follow-up. Staging stays under `.kittify/charter/` so doctrine consumers never traverse it. |
| **R-8 · Normalization drift in fixture keying** | "Two semantically identical interview answers produced different fixture hashes because JSON ordering drifted across dependency upgrades." | KD-4 pins normalization: sorted keys + canonical JSON + stable int/float repr. `test_fixture_adapter.py` asserts normalization invariance under key-order permutations. |
| **R-9 · Silent project-layer DRG reads during interview** | "Interview-time resolver accidentally picked up a stale project DRG from a previous run and skewed interview defaults." | `interview.py` explicitly uses shipped-only DRG for interview-time resolution (no project layer merge during interview). Test lock in `test_interview_mapping.py`. |
| **R-10 · Path-guard false-sense-of-security** | "Path guard existed but some code path bypassed it via `Path.write_text` direct." | PathGuard wraps *every* write seam; orchestration uses only guard methods. Static-check (grep-level lint test) in `test_path_guard.py` asserts no direct `open(..., 'w')` / `Path.write_text` / `shutil.move` outside the guard module. |

## File Clusters (orientation for reviewers)

- **Charter package**: `src/charter/synthesizer/*` (new), `src/charter/compiler.py`, `src/charter/context.py`, `src/charter/bundle.py` (modified — small diffs; `compiler.py` / `context.py` edits are candidate-list extensions only). `src/charter/_drg_helpers.py` is a read touchpoint (already resolves project DRG from `.kittify/doctrine/graph.yaml`) but requires no diff.
- **CLI**: `src/specify_cli/cli/commands/charter.py` (two new Typer subcommands).
- **Doctrine** (unchanged): `src/doctrine/drg/**` is consumed only; do not expect diffs here.
- **Tests**: `tests/charter/synthesizer/*` (new), `tests/charter/fixtures/synthesizer/*` (new), `tests/agent/cli/commands/test_charter_synthesize_cli.py` + `test_charter_resynthesize_cli.py` (new).
- **ADRs**: `architecture/adrs/2026-04-XX-1-charter-synthesizer-adapter-seam.md`, `architecture/adrs/2026-04-XX-2-charter-synthesizer-atomicity.md` (new, authored in WP3.1).
- **Migrations / upgrade**: none in this tranche (deliberately — ADR-7 is out of scope).

## Complexity Tracking

*Not applicable.* Charter Check passes cleanly with no violations. No justifications required.

## Branch Contract (repeat — mandatory)

- Current branch at workflow start: **`main`**
- Planning / base branch: **`main`**
- Final merge target for completed changes: **`main`**
- `branch_matches_target`: **true**
- Summary: *Current branch at workflow start: main. Planning/base branch for this feature: main. Completed changes must merge into main.*

## Next Step

This command is **complete** after Phase 1 artifacts land. The next step is **`/spec-kitty.tasks`** — the user must invoke it explicitly. Do not proceed to task generation from here.
