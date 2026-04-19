# Feature Specification: Phase 3 Charter Synthesizer Pipeline

| Field | Value |
|---|---|
| Mission ID | `01KPE222CD1MMCYEGB3ZCY51VR` |
| Mission Slug | `phase-3-charter-synthesizer-pipeline-01KPE222` |
| Mission Type | `software-dev` |
| Target Branch | `main` |
| Created | 2026-04-17 |
| Status | Draft (specify) |

**Roadmap anchors**: Charter EPIC #461 · Phase 3 tracker #465 · WPs #485 #483 #487 #488 #489 · ADR-7 #523 · ADR-8 #522

---

## 1. Problem Statement

Phases 0–2 of the charter engineering EPIC are complete and merged. `DoctrineService` already supports an additive shipped + project layer, and `charter compile` / `charter context` already instantiate it with a non-`None` `project_root`. The real gap is that `project_root` is resolved only from code-local candidates (`repo_root/src/doctrine` or `repo_root/doctrine`), which are the *shipped-layer* locations — there is no supported project-local doctrine path under `.kittify/` for runtime doctrine resolution, and no code path writes a project-local artifact. The result is that the charter interview collects project-specific signal — mission type, language scope, directive/tactic/styleguide selections, neutrality posture — and then discards the opportunity to materialize *project-tuned* doctrine from it. (The project-layer DRG overlay is a partial exception: `_drg_helpers` already reads `.kittify/doctrine/graph.yaml` when present, but no code path writes it.)

Phase 3 closes that gap by introducing a Charter Synthesizer: a pipeline that turns (interview answers + shipped doctrine + shipped DRG) into project-local directives, tactics, and styleguides, stored in a layout that the existing doctrine repositories and DRG helpers already recognise — artifact **content** under `.kittify/doctrine/`, synthesis **bookkeeping** (provenance, commit manifest, staging) under `.kittify/charter/`. Synthesis must be deterministic in its orchestration, validation, and bookkeeping, while the actual doctrine text remains harness-owned. This forces a specific architectural split: a narrow provider-agnostic seam for the generation step, with a file-backed generated-artifact adapter for real operator flows and a fixture-backed adapter for tests, surrounded by deterministic machinery that can be byte-reproducibly tested and guarded.

The mission must preserve the hard invariants established by earlier phases: shipped doctrine in `src/doctrine/` is read-only at runtime; synthesized content lives only under `.kittify/doctrine/`; synthesis bookkeeping lives only under `.kittify/charter/`; the merged DRG (shipped + project) contains no dangling references; every synthesized artifact carries provenance. It must also resist scope creep — autonomous code-reading, URL-fetching, cross-repo charter visibility, and free-text topic rewriting belong to later tranches or separate missions, not Phase 3.

## 2. Scope

### In Scope (Tranche 1)

- Synthesizer orchestration layer: input normalization, synthesis target selection, artifact writing, provenance recording, project DRG emission, cross-layer validation.
- Narrow provider-agnostic synthesis adapter interface, with a generated-artifact adapter for harness-authored YAML and a fixture adapter usable by the full test suite.
- Interview-driven synthesis path: a fresh `spec-kitty charter synthesize` run that takes current interview answers and produces a full project-local artifact set.
- Project-local artifact storage for three artifact kinds only: **directives**, **tactics**, **styleguides**. Content lives under `.kittify/doctrine/{directives,tactics,styleguides}/` using the filename conventions the existing repositories already glob (`*.directive.yaml`, `*.tactic.yaml`, `*.styleguide.yaml`).
- Provenance writer: per-artifact record of inputs, adapter identity, adapter version, inputs hash, source references (interview section and/or DRG URNs), and generation timestamp. Provenance sidecars and the synthesis manifest (commit marker) live under `.kittify/charter/` — synthesis bookkeeping is kept separate from doctrine content so doctrine consumers are unaffected.
- Project-layer DRG writer: additive overlay at `.kittify/doctrine/graph.yaml` (the path the existing `_drg_helpers` project-layer loader already reads) that merges cleanly with the shipped graph via the existing `merge_layers()` semantics, with no-dangling-reference enforcement gated before any artifact is considered durably written.
- `spec-kitty charter resynthesize --topic <selector>` with structured-selector resolution (local kind+slug for synthesizable kinds → DRG URN → interview section label), bounded recomputation, and unambiguous structured errors on unresolvable/ambiguous topics.
- Extension of bundle validation so `spec-kitty charter bundle validate` recognises synthesized artifacts (under `.kittify/doctrine/`) and their provenance (under `.kittify/charter/`).
- Consumer wiring: extend the project-root candidate list inside `src/charter/compiler.py::_default_doctrine_service` and `src/charter/context.py::_build_doctrine_service` so `DoctrineService` discovers `.kittify/doctrine/` as a project layer in addition to the existing `src/doctrine` / `doctrine` candidates. `_drg_helpers` already reads the project graph from `.kittify/doctrine/graph.yaml`; no change is needed there.

### Non-Goals (explicitly out of scope)

- **Code-reading ingestion**: no static analysis, no AST walking, no repository crawl as synthesis input beyond what the interview already captures.
- **URL fetching / best-practice ingestion from the web**: no external knowledge retrieval.
- **Free-text topic rewriting**: `--topic` is structured only; loose natural-language topics are rejected.
- **Paradigms, procedures, toolguides, agent profiles**: synthesis of these artifact kinds is deferred; they remain shipped-layer-only in Phase 3.
- **WP3.3, WP3.4, WP3.5**: remain deferred unless an explicit dependency surfaces during `/spec-kitty.plan`, in which case the planning phase will pull them forward with justification.
- **Monorepo / cross-repo charter visibility** (ADR-8): out of scope for this mission.
- **Migration of existing pre-Phase-3 projects** (ADR-7): out of scope for this mission.
- **Reopening Phase 1 or Phase 2 design**: current bundle manifest v1.0.0, chokepoint, and charter-ownership invariants are fixed baseline unless a concrete blocker emerges in current code.
- **Live model calls in CI**: the fixture adapter must carry 100% of test executions.

## 3. User Scenarios & Acceptance

### Actors

- **Operator**: a developer configuring a project's charter and synthesizing project-local doctrine.
- **Downstream Agent**: any CLI-run agent that consumes `charter context --action <x>` output during `specify` / `plan` / `implement` / `review`.
- **Reviewer / Mission owner**: a human validating that synthesis produced legitimate artifacts before committing them.

### Primary Flows

**US-1 — First-time synthesis for a fresh project**
*Given* a project where `/spec-kitty.charter` has been completed (interview answers on disk, shipped charter bundle fresh),
*when* the operator runs `spec-kitty charter synthesize`,
*then* the pipeline produces project-local directives, tactics, and styleguides under `.kittify/doctrine/` (with filenames matching the existing repository globs), writes one provenance entry per artifact under `.kittify/charter/provenance/`, emits a project DRG layer at `.kittify/doctrine/graph.yaml` that merges cleanly with the shipped graph, writes the commit-marker manifest at `.kittify/charter/synthesis-manifest.yaml` last, and the next `charter context --action specify` invocation surfaces at least one project-specific item that was not present before synthesis.

**US-2 — Targeted resynthesis by DRG URN**
*Given* a project with a previously synthesized artifact set,
*when* the operator runs `spec-kitty charter resynthesize --topic directive:DIRECTIVE_003`,
*then* only artifacts whose provenance references that URN are regenerated, all other artifact content hashes remain byte-identical, and the merged DRG still validates.

**US-3 — Targeted resynthesis by artifact kind + slug**
*Given* a project with a previously synthesized artifact set that includes the project-local tactic `tactic:how-we-apply-directive-003`,
*when* the operator runs `spec-kitty charter resynthesize --topic tactic:how-we-apply-directive-003`,
*then* exactly that artifact is regenerated (the resolver's local-first rule for synthesizable kinds matches the project-layer artifact rather than any shipped DRG node), its provenance is updated (new `generated_at`, possibly new content hash), and the merged DRG re-validates.

**US-4 — Targeted resynthesis by interview section**
*Given* a project with a previously synthesized artifact set,
*when* the operator runs `spec-kitty charter resynthesize --topic testing-philosophy`,
*then* every artifact whose provenance records that section as a source input is regenerated, no orphan references are introduced, and artifacts unrelated to that section are untouched.

**US-5 — Dangling-reference guardrail**
*Given* a synthesis run whose generated output would introduce a DRG edge to a URN that does not exist in either the shipped layer or the in-progress project layer,
*when* the orchestration layer invokes validation before committing writes,
*then* the write transaction fails atomically, no files land under `.kittify/doctrine/` or `.kittify/charter/` (outside the preserved `.staging/<runid>.failed/` diagnostic directory), and the operator sees a structured error naming the dangling URN, the offending artifact, and the source reference that triggered it.

**US-6 — Ambiguous / unresolvable topic**
*Given* a `resynthesize --topic <selector>` invocation whose selector cannot be unambiguously resolved by the three-step order,
*when* the resolver runs,
*then* no files are written, no model is called, and the operator sees a structured error listing candidate interpretations (close DRG URNs, matching kind+slug pairs, matching interview sections).

**US-7 — Path-guard on shipped doctrine**
*Given* any code path inside the synthesizer,
*when* a write would target a location under `src/doctrine/`,
*then* the path guard raises a structured error before the filesystem is touched, and the test suite proves this cannot be bypassed.

**US-8 — Idempotent re-run**
*Given* a completed synthesis and unchanged inputs (interview answers, shipped doctrine, adapter identity),
*when* `spec-kitty charter synthesize` is run again with the fixture adapter,
*then* the provenance entries and the artifact content hashes are byte-identical to the previous run.

### Edge Cases

- EC-1: Empty or near-empty interview answers — synthesizer must still produce a valid (possibly minimal) project-local artifact set or refuse cleanly with a structured error; never leave a partial state.
- EC-2: Interview answers reference a selection URN that does not exist in the shipped DRG — synthesis must fail closed with a structured error before any artifact is written.
- EC-3: Adapter returns an artifact body that fails its shipped-layer Pydantic schema — orchestration rejects the artifact, fails closed, and records the rejection for operator diagnosis.
- EC-4: `resynthesize --topic <selector>` for a topic that resolves to zero existing artifacts — resolver returns a structured "no-op with diagnostic" result; no writes, no model call.
- EC-5: Interrupted synthesis run (process killed mid-write) — on next run, the bundle validator detects partial state and either repairs it (if safe) or presents a structured error directing the operator to rerun `synthesize`.
- EC-6: Project DRG overlay nodes or edges would collide with shipped nodes/edges (same URN or same edge triple) — additive-only semantics are enforced via the existing `merge_layers()` semantics; any collision fails closed before promote.
- EC-7: The same artifact slug is produced twice by the same run — orchestration rejects the run with a duplicate-slug error before any write.

## 4. Requirements

### 4.1 Functional Requirements

| ID | Requirement | Status |
|----|-------------|--------|
| FR-001 | The synthesizer SHALL accept as inputs the current charter interview answers, the shipped doctrine catalog, and the merged shipped+project DRG graph. | Accepted |
| FR-002 | The synthesizer SHALL produce, for Tranche 1, only artifacts of kind `directive`, `tactic`, and `styleguide`. | Accepted |
| FR-003 | The synthesizer SHALL expose a narrow provider-agnostic adapter interface for the generation step, such that the generated-artifact adapter and the fixture adapter are substitutable without changes to orchestration code. | Accepted |
| FR-004 | The fixture adapter SHALL be used for 100% of automated tests; no automated test SHALL require a live model call. | Accepted |
| FR-005 | Synthesized artifact content (directives, tactics, styleguides, project DRG graph) SHALL be written only under `.kittify/doctrine/`, using filenames that match the existing repository globs: `*.directive.yaml`, `*.tactic.yaml`, `*.styleguide.yaml`, plus `graph.yaml`. Synthesis bookkeeping (per-artifact provenance sidecars, commit-marker manifest, and ephemeral staging) SHALL be written only under `.kittify/charter/`. | Accepted |
| FR-006 | Every synthesized artifact SHALL have a provenance record containing: artifact URN, inputs hash, adapter id, adapter version, source references (interview section label and/or DRG URN(s)), and `generated_at` timestamp. | Accepted |
| FR-007 | The pipeline SHALL emit a project-layer DRG overlay at `.kittify/doctrine/graph.yaml` that is additive-only with respect to the shipped graph and that merges cleanly via the existing `merge_layers()` semantics. | Accepted |
| FR-008 | Before any synthesized artifact is considered durably written, the pipeline SHALL validate the merged (shipped + project) DRG and SHALL fail closed if any dangling reference, duplicate edge, or cycle-in-requires is detected. | Accepted |
| FR-009 | `src/charter/compiler.py::_default_doctrine_service` and `src/charter/context.py::_build_doctrine_service` SHALL extend their project-root candidate list so `.kittify/doctrine/` is recognised as a project layer for `DoctrineService` in addition to the existing `repo_root/src/doctrine` and `repo_root/doctrine` candidates. Discovery SHALL be conditional on the directory being present, so legacy projects (pre-synthesis) see no behaviour change. | Accepted |
| FR-010 | The CLI SHALL expose `spec-kitty charter synthesize` as the interview-driven full-synthesis entrypoint. | Accepted |
| FR-011 | The CLI SHALL expose `spec-kitty charter resynthesize --topic <selector>` as the bounded re-run entrypoint. | Accepted |
| FR-012 | The `--topic` selector resolver SHALL attempt resolution in this order, and only this order: (1) for a string `K:X` where `K` is a synthesizable artifact kind (`directive`, `tactic`, `styleguide`), first match against the project-local artifact set by `(kind, slug)`; (2) DRG URN against the merged shipped+project graph; (3) interview section label (only when the string contains no `:`). | Accepted |
| FR-013 | Unresolvable or ambiguous topic selectors SHALL produce a structured error enumerating candidates; the resolver SHALL NOT silently fall back to any partial match. | Accepted |
| FR-014 | The pipeline SHALL be idempotent: for identical inputs (interview answers, shipped doctrine, adapter id) the fixture adapter produces byte-identical artifact bodies and provenance. | Accepted |
| FR-015 | `spec-kitty charter bundle validate` SHALL be extended to verify that every synthesized artifact has a corresponding provenance entry and that every provenance entry references an existing artifact. | Accepted |
| FR-016 | The orchestration layer SHALL enforce a path guard that prevents any write targeting a location under `src/doctrine/`, and this guard SHALL be testable at the orchestration boundary. | Accepted |
| FR-017 | `resynthesize --topic <selector>` SHALL regenerate only the artifacts whose provenance references the resolved target, and SHALL leave all other artifact bodies and provenance entries byte-identical. | Accepted |
| FR-018 | After a successful synthesis, `charter context --action <specify\|plan\|implement\|review>` SHALL surface at least one project-specific directive, tactic, or styleguide that is not part of the shipped-layer-only output. | Accepted |
| FR-019 | The pipeline SHALL reject adapter outputs that fail shipped-layer Pydantic schema validation for the claimed artifact kind, with a structured error, before provenance or DRG writes occur. | Accepted |
| FR-020 | The pipeline SHALL never delete or mutate nodes or edges in the shipped DRG layer; the project layer is additive only. | Accepted |

### 4.2 Non-Functional Requirements

| ID | Requirement | Threshold | Status |
|----|-------------|-----------|--------|
| NFR-001 | Test coverage on synthesizer orchestration code (excluding the adapter's external call surface). | ≥ 90% line coverage, consistent with charter policy. | Accepted |
| NFR-002 | Full-synthesis wall-clock latency on a representative minimal interview (≤ 10 answered questions) using the fixture adapter. | < 30 seconds. | Accepted |
| NFR-003 | `resynthesize --topic` wall-clock latency for a single-target resolution using the fixture adapter. | < 15 seconds. | Accepted |
| NFR-004 | Time from detected validation failure to fail-closed return (no filesystem mutation) during synthesis. | < 5 seconds. | Accepted |
| NFR-005 | Shipped-layer Pydantic schema conformance of synthesized artifacts. | 100% of written artifacts. | Accepted |
| NFR-006 | Byte-reproducibility of provenance entries given identical (inputs, adapter id) tuples. | 100% of runs under the fixture adapter. | Accepted |
| NFR-007 | Static type-check conformance of all new modules. | `mypy --strict` passes with zero errors. | Accepted |
| NFR-008 | Writes outside `.kittify/doctrine/` (for content) and `.kittify/charter/` (for bookkeeping and staging) during any synthesis run. | 0 occurrences, verified by path-guard test. | Accepted |
| NFR-009 | Dangling-reference escapes into a committed project DRG layer. | 0 occurrences, verified by pre-commit validator. | Accepted |
| NFR-010 | Network calls from the test suite. | 0 occurrences; fixture adapter carries all tests. | Accepted |

### 4.3 Constraints

| ID | Constraint | Status |
|----|------------|--------|
| C-001 | Shipped doctrine under `src/doctrine/` remains read-only at runtime for all synthesizer code paths. | Accepted |
| C-002 | Synthesized artifact content lives only under `.kittify/doctrine/` (directories + filenames matching the existing repository globs); synthesis bookkeeping (provenance, manifest, staging) lives only under `.kittify/charter/`. No other locations are written. | Accepted |
| C-003 | No live network calls are permitted in the automated test suite; the LLM adapter must be swappable for a fixture adapter. | Accepted |
| C-004 | `--topic` accepts only structured selectors; free-text topics are rejected with a structured error. | Accepted |
| C-005 | Synthesis in this tranche covers only `directive`, `tactic`, and `styleguide` artifacts; `paradigm`, `procedure`, `toolguide`, and `agent_profile` remain shipped-layer-only. | Accepted |
| C-006 | Harness-owned inference remains outside spec-kitty. The CLI may validate and promote harness-authored artifacts, but it SHALL NOT embed a vendor-specific model client. | Accepted |
| C-007 | ADR-7 (existing project migration design) is out of scope for this mission. | Accepted |
| C-008 | ADR-8 (monorepo / cross-repo charter visibility) is out of scope for this mission. | Accepted |
| C-009 | The project DRG layer is additive only (per existing `merge_layers()` semantics); no deletions or silent replacements of shipped nodes/edges are permitted. | Accepted |
| C-010 | The bulk-edit occurrence-classification guardrail does not apply to this mission; it is net-new code and new seams, not a cross-file rename/rewrite of an existing identifier. | Accepted |
| C-011 | WP3.3, WP3.4, and WP3.5 remain deferred; `/spec-kitty.plan` may pull one forward only if current code surfaces a concrete dependency that cannot be deferred, with explicit justification. | Accepted |
| C-012 | Bundle manifest v1.0.0 tracked-vs-derived contract remains fixed; any extension to describe synthesized artifacts must preserve backwards-compatibility of existing validators. | Accepted |

## 5. Success Criteria

| ID | Criterion |
|----|-----------|
| SC-001 | An operator can complete end-to-end fresh-project synthesis (interview → `charter synthesize` → `charter bundle validate`) in under 2 minutes of hands-on time, excluding model latency. |
| SC-002 | 100% of synthesized artifacts validate against their shipped-layer schemas. |
| SC-003 | 100% of synthesized artifacts have a provenance entry referencing adapter id, adapter version, inputs hash, source refs, and `generated_at`. |
| SC-004 | 100% of merged (shipped + project) DRG graphs produced by the pipeline pass the existing no-dangling-reference, no-duplicate-edge, and no-cycle-in-requires validators. |
| SC-005 | After synthesis, `charter context --action <specify\|plan\|implement\|review>` surfaces at least one project-specific item not present in shipped-layer-only output. |
| SC-006 | For any `resynthesize --topic` invocation, at least 95% of unrelated artifact content hashes are byte-identical to the pre-run state. |
| SC-007 | 0% of synthesis runs write outside `.kittify/doctrine/` (content) or `.kittify/charter/` (bookkeeping), verified by path-guard test. |
| SC-008 | Operators encountering an ambiguous `--topic` selector receive a structured error listing candidate interpretations in under 2 seconds with no files touched. |
| SC-009 | A fresh operator, following quickstart documentation, can run a full synthesis cycle and explain what provenance entries mean within 15 minutes of first exposure. |

## 6. Key Entities

- **SynthesisRequest** — input envelope: trigger (fresh | resynthesize), adapter id, topic selector (if any), interview-answers snapshot, shipped-doctrine snapshot, DRG snapshot.
- **SynthesisTarget** — a single unit of synthesis: artifact kind (directive | tactic | styleguide), target slug, source references (interview section labels and/or DRG URNs).
- **SynthesisAdapter** — provider-agnostic interface: `generate(target, context) -> AdapterOutput`. Generated-artifact implementation for operator flows; fixture implementation for tests.
- **AdapterOutput** — artifact body + adapter metadata (adapter id, adapter version, inputs hash contribution).
- **SynthesisResult** — artifact body, provenance entry, validation status. Returned per-target before any filesystem write.
- **ProvenanceEntry** — record tied to a written artifact: artifact URN, inputs hash, adapter id, adapter version, source references, `generated_at`, content hash of the written body.
- **TopicSelector** — discriminated union: DRG URN | `<kind>:<slug>` | interview section label.
- **ProjectDRGOverlay** — additive DRG graph (nodes and edges) emitted by the synthesis run; must satisfy `merge_layers()` contract with the shipped graph.
- **SynthesisBundle** — filesystem view after a run: artifact files + provenance store + project DRG overlay, all under `.kittify/charter/`.

## 7. Assumptions

- A-1 — The existing `DRGGraph.merge_layers()` additive semantics are sufficient for the project layer; no new edge-removal semantics are required.
- A-2 — `DoctrineService` already accepts a `project_root` and sources artifacts by artifact-kind subdirectory; the only change required is extending the project-root candidate list in `compiler.py` / `context.py` to recognise `.kittify/doctrine/` (per FR-009).
- A-3 — The current charter interview already captures enough signal to drive directive, tactic, and styleguide synthesis; if `/spec-kitty.plan` discovers otherwise, scope additions will be surfaced explicitly and not absorbed silently.
- A-4 — The fixture adapter can be stored under `tests/charter/fixtures/synthesizer/` using a content-keyed layout that mirrors the adapter contract; the exact path is finalized in `/spec-kitty.plan`.
- A-5 — Synthesized artifact filenames follow the existing repository glob conventions: `<NNN>-<slug>.directive.yaml`, `<slug>.tactic.yaml`, `<slug>.styleguide.yaml`. Synthesized directive IDs use a distinct `PROJECT_<NNN>` numeric-prefix scheme (matches `Directive.id` regex `^[A-Z][A-Z0-9_-]*$`; disjoint from shipped `DIRECTIVE_<NNN>`). This scheme is the tranche-1 default and is not locked — if the WP3.2 model proves semantic IDs (e.g. `TEAM_TESTING_POLICY`) produce better provenance, the regex accepts them.
- A-6 — Bundle manifest v1.0.0 can be extended with optional synthesized-artifact metadata without breaking existing consumers; if that turns out to require a v1.1.0 bump, it will be called out in the plan phase and treated as an explicit contract change.
- A-7 — Operators running `resynthesize --topic` are comfortable with structured selectors; a natural-language on-ramp is not needed in this tranche.

## 8. Dependencies

- Harness-owned synthesis contract — generation remains the responsibility of the invoking LLM harness; spec-kitty consumes generated artifacts and provides validation, staging, and promotion.
- ADR-7 (existing 3.x project migration, #523) — out of scope here; flagged so its eventual design can re-use the Phase 3 bundle format without rework.
- ADR-8 (monorepo / cross-repo charter visibility, #522) — out of scope here; flagged so its design can assume the Phase 3 bundle format as a building block.
- Existing DRG validator (`src/doctrine/drg/validator.py`) — hard dependency; used as the gatekeeper for FR-008 / NFR-009.
- Existing `DoctrineService` project-layer support — hard dependency; activated by FR-009.
- Existing charter bundle manifest (v1.0.0, `src/charter/bundle.py`) — hard dependency; extended by FR-015.

## 9. Work Package Scope Anchor

This is a *scope* anchor, not an implementation plan. Concrete design — modules, class names, file layout, sequencing — is the job of `/spec-kitty.plan` and `/spec-kitty.tasks`.

| WP | Title | Scope summary |
|----|-------|---------------|
| WP3.1 | Synthesizer architecture skeleton + provider seam | Orchestration entrypoint; narrow adapter interface; fixture adapter; path guard; coverage floor. Must land first: WP3.2/3.6/3.7/3.8 all depend on its seams. |
| WP3.2 | Interview-driven synthesis path | Wiring from interview answers → target selection → adapter invocation → artifact assembly. Consumes WP3.1's seam; produces artifact bodies but does not yet persist. |
| WP3.6 | Project-local artifact storage + provenance writer | Filesystem layout under `.kittify/charter/`; provenance format and writer; idempotency guarantees. Consumes WP3.2's artifact bodies. |
| WP3.7 | Project DRG layer writer + no-dangling-ref enforcement | Additive DRG overlay emission; validation gate that runs before WP3.6's writes become durable; atomic-failure semantics. |
| WP3.8 | `spec-kitty charter resynthesize --topic <selector>` | Structured-selector resolver; bounded recomputation path; integration with WP3.1/3.6/3.7. |
| WP3.3 / WP3.4 / WP3.5 | Deferred | Stay out of this tranche. `/spec-kitty.plan` may pull one forward only with explicit justification rooted in current code. |

## 10. Validation Strategy

Validation is deliberately layered so that the LLM seam's non-determinism does not contaminate the rest of the test suite.

- **Synthesized artifact generation (WP3.1 / WP3.2)** — unit tests against the orchestration layer using the fixture adapter; shape/schema assertions; idempotency assertions under fixed inputs; golden fixtures for a small set of representative interview snapshots.
- **Provenance writing (WP3.6)** — assertions on provenance entry schema, presence of required fields, byte-reproducibility under the fixture adapter, round-trip read-back equality.
- **DRG integration (WP3.7)** — additive-merge invariant; no shipped-layer mutation; validator gate runs before persistence; synthetic DRG fixtures covering accept, reject-dangling, reject-duplicate, reject-cycle.
- **No-dangling-reference enforcement (WP3.7)** — dedicated negative tests proving that a deliberately introduced dangling URN causes atomic rollback with no partial state on disk.
- **Observable context differences (FR-018 / SC-005)** — end-to-end integration test that synthesizes, then invokes `charter context --action specify` and asserts the presence of at least one project-specific artifact in output.
- **Path guard (FR-016 / NFR-008)** — test harness attempts writes to every write-adjacent code path; any attempt to target `src/doctrine/` must raise the structured path-guard error before touching the filesystem.
- **Bundle validation (FR-015)** — `charter bundle validate` regression fixtures covering (a) valid post-synthesis bundle, (b) artifact without provenance, (c) provenance without artifact, (d) schema-invalid artifact.
- **Topic selector (FR-012 / FR-013 / SC-008)** — table-driven tests across all three resolution tiers plus the ambiguous / unresolvable / zero-match edge cases.
- **Performance envelopes (NFR-002 / NFR-003 / NFR-004)** — lightweight timing assertions using the fixture adapter; CI-tolerant thresholds.
- **Determinism (NFR-006 / FR-014)** — identical-inputs run produces byte-identical provenance and artifact hashes.

## 11. Risks and Sequencing Constraints

Risk detail belongs primarily to `/spec-kitty.plan`, but the specify phase records the headline risks that shape scope:

- **R-1: Seam leak** — if the adapter interface leaks generation concerns into orchestration (e.g., prompt shaping, retry policy), determinism erodes. Mitigation: WP3.1 defines the interface with no prompt-engineering surface; prompts live inside adapters.
- **R-2: DoctrineService wiring ripple** — switching charter compile/context to pass `project_root` may surface behavioral differences for projects that have never had a project layer. Mitigation: activation is gated on the presence of a synthesized artifact set; legacy projects see no change until their first `charter synthesize` run.
- **R-3: Bundle manifest drift** — extending bundle contents without a version bump risks silent breakage of `bundle validate`. Mitigation: any extension is additive and backwards-compatible; if not, the plan phase must call a v1.1.0 bump explicitly.
- **R-4: Provenance brittleness under adapter churn** — changing generated-artifact or fixture adapter semantics could invalidate provenance expectations. Mitigation: adapter id + adapter version are first-class provenance fields; invalidation is observable, not hidden.
- **R-5: Topic selector ambiguity escalation** — users may push back on structured-only selectors. Mitigation: structured error output enumerates candidates so the affordance is teachable; free-text is an explicit later-tranche decision, not a silent no.
- **R-6: harness-contract drift** — if spec-kitty and the invoking harness disagree about where generated artifacts live or how they are identified, operator runs fail late. Mitigation: C-006 freezes the no-internal-LLM rule and the generated-artifact adapter path.

Sequencing constraint (spec-level): WP3.1 must land before WP3.2/3.6/3.7/3.8 begin. WP3.6 and WP3.7 can proceed in parallel once WP3.2 establishes the artifact body contract. WP3.8 depends on WP3.6 and WP3.7 being durable enough to drive bounded recomputation. Likely file clusters (charter package, doctrine DRG package, CLI commands, bundle manifest) are a plan-phase concern.

## 12. Recommended Mission Shape

Realistic implementation scale for this tranche:

- 5 work packages (WP3.1 → WP3.2 → WP3.6 / WP3.7 → WP3.8), with WP3.6 / WP3.7 parallelisable after WP3.2.
- Scope spans `src/charter/`, `src/doctrine/drg/` (read-only of existing validators; no new validator logic), a new `src/charter/synthesizer/` subpackage (name is a plan-phase decision), new CLI surfaces under `spec-kitty charter`, and new test fixtures under `tests/charter/`.
- No migration of existing `.kittify/charter/` bundles; legacy projects are unaffected until they run `charter synthesize`.
- Expected review volume: moderate. WP3.1 carries the highest review cost (interface-shape decisions); WP3.8 carries the second-highest (selector semantics, structured error UX); WP3.2 / WP3.6 / WP3.7 are largely mechanical once the interface is right.

## 13. Review & Acceptance

The specification is ready for `/spec-kitty.plan` when:

- Requirements quality checklist passes (see `checklists/requirements.md`).
- No `[NEEDS CLARIFICATION]` markers remain.
- Scope, non-goals, and deferred WPs are unambiguous.
- Invariants (read-only shipped doctrine, no dangling refs, provenance mandatory, `.kittify/charter/`-only writes) are stated as testable requirements, not aspirations.
