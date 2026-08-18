# Research Plan: Docling Graph for Spec Kitty Mission Artifacts

**Branch**: `research/docling-graph-kitty-specs` | **Date**: 2026-08-18 | **Spec**: [spec.md](spec.md)

## Summary

This mission uses a preregistered mixed-method case study to determine whether any Docling-based representation of `kitty-specs` artifacts is worth further investment. It separates representation, derivation, persistence, authority, lifecycle, aggregation, and egress decisions; compares current and deterministic native baselines with Docling structural and semantic candidates; and applies fail-closed fidelity, provenance, stability, privacy, and operational gates. Current artifacts are never mutated during probes. All authority postures remain counterfactual candidates until synthesis.

## Frozen Research Context

**Research Question**: Would any Docling-based representation create enough measurable traceability, impact-analysis, or discovery value to justify its costs, and which authority/adoption posture—if any—is supported?  
**Research Type**: Mixed-method empirical case study and primary-source review  
**Domain**: Spec-driven development artifacts, document models, structured extraction, and knowledge graphs  
**Time Frame**: Evidence available and measurements run on 2026-08-18  
**Resources Available**: Fresh Spec Kitty checkout, current upstream Docling Graph source, macOS arm64/Python 3.11, Git/GitHub, local static analysis, and disposable temporary environments. No approved remote inference or cross-platform runners.

**Frozen Inputs**:

- Spec Kitty baseline corpus: `Priivacy-ai/spec-kitty@cf0f7e3a7` (`origin/main` at mission start). This mission directory is excluded from corpus statistics and model inputs.
- Docling Graph source: `docling-project/docling-graph@19815e3147503f78a06e263255667e237830bab9`.
- Eligible corpus: files tracked at the Spec Kitty baseline under `kitty-specs/`; Markdown specimens may be joined to adjacent tracked JSON, JSONL, YAML, and CSV authorities for gold answers.
- Exclusions: untracked files, generated probe outputs, `.kittify` caches, worktrees, archives outside `kitty-specs`, vendored dependencies, and this mission's artifacts.
- Logical mission boundary: PRIMARY and COORD artifact kinds are identified through canonical placement/dossier code. A physical directory walk is not treated as complete lifecycle state.

## Preregistered Methodology

### Framework

Approach: comparative case study with a structured primary-source review, repository forensics, confirmatory conversion probes, manually reviewed gold truth, and dialectical synthesis. This is adapted from a systematic mapping study: search and exclusion rules are frozen, but the goal is engineering decision support rather than estimating a population effect.

Deviations from a full systematic review:

- The relevant technology is young and primary code/docs dominate the evidence base; peer-reviewed literature is contextual only.
- No production user study is conducted. Query value remains a maintainer hypothesis and cannot justify production adoption.
- Semantic extraction runs are conditional on an approved local backend. If unavailable, semantic-positive conclusions are prohibited and that proposition is marked unevaluated; structural candidates remain independently testable.

### Phase Sequence and Stop Rules

1. **Commit the methodology contract**: commit this plan and source revisions. Pre-spec observations remain exploratory and may not supply confirmatory outcomes.
2. **Build one sealed confirmatory bundle without running a candidate**: executable selector, exclusion list, corpus manifest, fixtures, complete atomic gold, preassigned criticality, rubrics, evaluator identities, candidate registry, baseline procedures, configs, and thresholds. Record every file's SHA-256 plus the bundle tree hash in `research/preregistration-manifest.json`.
3. **Independently approve the bundle**: two blinded reviewers annotate every scored atom from source artifacts, then a named adjudicator resolves disagreements. Reviewer attestations, disagreement rows, source blobs, and the approved-gold hash enter the bundle. Files exposed during exploratory conversion are excluded from confirmatory selection.
4. **Freeze and commit the bundle**: after this point, any changed input invalidates confirmatory results and requires a labelled new preregistration version. Candidate-facing imports, parses, conversions, and graph builds are prohibited before this commit.
5. **Register sources and consumers**: populate the source/evidence registers, contradiction register, authority-by-fact-class inventory, and consumer matrix.
6. **Establish baselines**: execute frozen B0/B1 procedures. B2 receives the same eight-hour engineering cap as any new Docling harness; B3 remains explicitly design-only. Run order is counterbalanced and timings use five clean repetitions.
7. **Run structural probes**: confirm byte equality and separately score normalized Markdown→DoclingDocument→Markdown construct fidelity, provenance, identity, storage, and lifecycle behavior.
8. **Run conditional semantic probes**: only with an approved local backend; repeat fixed document/model/schema/config runs and score atomic facts against approved gold.
9. **Assess operations and privacy**: dependency footprint, cold/warm runtime, storage amplification, offline behavior, data flow, consent, secret canaries, retention, and platform evidence.
10. **Synthesize dialectically**: assign `PASS|FAIL|UNKNOWN|N/A` to every applicable candidate gate, build the strongest counter-case for each load-bearing finding, and route back to gathering if evidence is insufficient.
11. **Review and publish**: independent adversarial review, citation/fidelity verification, hash-bound publication manifest, publication gate, and report.

Gathering stops only when every decision question has evidence saturation: at least one supporting and one challenging primary source where both exist, every known contradiction is resolved or marked outcome-blocking, and every required stratum is covered. The planning cap is 24 included primary sources and 8 explicit exclusions, but reaching it with an uncovered question, a load-bearing disputed exclusion, or known potentially overturning evidence forces `defer—unevaluated`; numeric caps never authorize publication. A second reviewer decides load-bearing exclusions. New candidate harnesses receive equal eight-hour implementation budgets; unsupported relations are reported, not backfilled after results are seen.

### Source Search Strategy

**Primary-source queries**:

- `site:github.com/docling-project/docling-graph markdown provenance graph conversion merge schema export`
- `site:docling-project.github.io/docling-graph markdown provenance graph fusion templates`
- Repository search for `kitty-specs`, `MissionArtifactKind`, `frontmatter`, `dossier`, `source-register.csv`, `body_upload`, `status.events`, and Markdown readers/writers.

**Inclusion Criteria**:

- Current upstream source/docs that directly define Docling Graph input, extraction, schema, graph, provenance, export, merge, dependency, or runtime behavior.
- Canonical Spec Kitty charter, ADR, glossary/context, code, tests, templates, and tracked artifacts that define authority, placement, identity, lifecycle, dossier, sync, or Markdown consumption.
- Reproducible observations with pinned input path/hash, command or script, and environment.
- Peer-reviewed or official Docling material only when it answers a decision question not already settled by source code.

**Exclusion Criteria**:

- Marketing summaries without inspectable implementation evidence.
- Unversioned third-party tutorials, opinion posts, generic GraphRAG claims, or unrelated PDF-to-Markdown benchmarks.
- Sources predating a contradictory current upstream contract unless retained as historical evidence.
- Any private data requiring remote transmission, credentials, or an unapproved inference provider.

Citation style: stable evidence IDs linked to APA-like source-register rows with URL/repository path, commit/version, access date, relevance, and status.

### Corpus Selection

The corpus census records tracked file counts, bytes, artifact roles, mission metadata/type where available, topology, era proxy, and Markdown syntax features. `research/select_corpus.py` is the sole selector. Before selection it freezes: feature-detection regexes, tracked-file eligibility, exploratory exclusions, stratum precedence, size quantiles over eligible byte sizes, maximum two sampled-stratum specimens per mission, and lexicographic SHA-256/path tie order. Preregistered query-source inclusions are exempt from that cap so every gold-source Markdown file receives its advertised span oracle; the manifest labels those non-population inclusions `query_fixture:*`. It chooses one negative/control specimen with no target syntax and at least 12 Markdown specimens so the published coverage matrix contains:

- roles: `spec.md`, `plan.md`, `tasks.md`, WP prompt/review-cycle, research/findings, and other contract/explanation;
- eras/types: legacy numeric mission, current ULID mission, software-dev, research/documentation where present;
- sizes: small, median-near, 90th-percentile-near, and large-but-runnable;
- topologies/acceptance: flat, coord-capable metadata, and accepted/not-accepted mission examples where available;
- syntax: YAML frontmatter, tables, fenced code, links/anchors, HTML comments, checkboxes, Unicode/diacritics, and cross-file identifiers.

One specimen may cover multiple features, but each role/era/type/size/topology/lifecycle stratum gets an independently selected row; the sample expands if any row is empty. Query fixtures are transparently frozen maintainer scenarios, not a random population sample; they are protected against hard-coding by source-literal bans, five frozen metamorphic ID/path mutations, and post-implementation code review. This limitation prevents population-effect or end-user-demand claims. No confirmatory specimen may have been used in exploratory conversion.

Gold truth annotates requirement/story/constraint IDs, WPs, dependencies, owned files, decisions, sources, evidence, lifecycle facts, and exact source spans. Criticality is frozen before predictions: requirement/dependency/authority/approval/provenance facts are critical; inferred themes are non-critical. Two reviewers independently annotate every scored atom while blinded to candidate output. A named adjudicator resolves all disagreements; agreement, resolution, reviewer identity, attestation, and gold/source hashes are published. Neither missing agreement nor an unadjudicated row may enter a score.

### Frozen Query Registry

The canonical registry is `research/query-registry.yaml`; its content hash is recorded before confirmatory probes. Each row includes owner/job, fixture mission(s), expected atomic answer, partial-credit rules, required provenance grade, baseline procedure, evaluator, and value status (`observed` or `hypothesized`).

| ID | Critical | Owner/job | Question | Required evidence |
|---|---|---|---|---|
| Q1 | yes | Mission operator / audit trace | Which requirement or acceptance criterion maps through a WP to its approved proof? | Exact paths/spans for every hop |
| Q2 | yes | Planner / sequencing | What prerequisite and blocker path prevents a selected WP from advancing? | Canonical dependency and status facts |
| Q3 | yes | Maintainer / impact analysis | Which files, contracts, and tests are implicated by a selected requirement? | Authored ownership plus qualified inference |
| Q4 | yes | Reviewer / rationale | Which decisions and research sources support or oppose a selected concern? | Exact decision/evidence citations |
| Q5 | yes | Runtime maintainer / consistency | Where do Markdown, metadata, status events, and acceptance artifacts contradict? | Source-specific conflicting facts |
| Q6 | no | Architect / portfolio discovery | Which cross-mission concepts or dependencies may overlap without collapsing mission-local IDs? | Namespaced identity and non-merge proof |

These are maintainer-designed technical tasks, not validated end-user demand. No production-adoption conclusion may treat them as user research.

### Comparable Baselines

- **B0 Current workflow**: `rg`, Git, existing CLI/dashboard outputs, and manual source opening.
- **B1 Existing structured readers**: Mission Dossier/index/hash plus canonical JSON/YAML/JSONL/frontmatter parsers; no new graph.
- **B2 Deterministic projection**: disposable research index over mission/artifact identity, explicit IDs, dependencies, references, ownership, decisions, sources, and lifecycle facts. No LLM inference.
- **B3 Author-augmented native**: design-only estimate for adding typed IDs/links to existing canonical formats and deriving B2; authoring burden is scored separately.

All executed baselines use identical corpus, query fixtures, gold answers, hardware, clean/warm cache definitions, and scoring. `research/baseline-procedures.yaml` freezes commands, five trials, counterbalanced order, evaluator training, timing boundaries (prompt shown to final cited answer), allowed corrections, and cold/warm preparation. Record build/update time, atomic correctness, provenance, p50/p95 latency, human correction time, stale-result behavior, storage, and maintenance surface. B2 and each new Docling harness receive an eight-hour cap; sensitivity is reported at two and eight hours. B3 is not timed or compared as an empirical winner.

### Executable Probe Contracts

- **Enumeration/selection**: `git ls-tree -r -z --long cf0f7e3a7 -- kitty-specs` supplies tracked bytes and paths. Role classifiers are frozen basename/glob tables; mission era is legacy numeric vs current ULID regex; topology/type and mission acceptance come only from `meta.json`, while WP lifecycle facts come only from canonical status events. Missing metadata is `unknown`, never inferred. Size strata use nearest-rank order over `(bytes, content_sha256, path)`: rank `ceil(p*n)` for p=0.5/0.9; "large-but-runnable" is largest eligible file at most 2 MiB. Other strata use `(content_sha256, path)`. The selector greedily fills independently ordered strata, enforces two files per mission, then expands until all available rows are filled. Exact paths/Git blobs/content SHA-256 hashes are output, not hand-picked.
- **Round trip**: pinned `research/probe_roundtrip.py` calls Docling `DocumentConverter().convert(path).document.export_to_markdown()` in the pinned source environment. It first runs isolated golden micro-fixtures, then selected corpus files. Raw input/output hashes establish byte equality; a separate frozen construct oracle reports structural survival. Output normalization is prohibited for the byte track.
- **Answers**: all procedures emit `query_id,fixture_id,atom_type,subject,predicate,object,source_path,source_blob,start_byte,end_byte,status`. Exact-set atom matching supplies correctness; partial credit is allowed only for registry-enumerated compound answers. Candidate implementations may not contain registered mission/path/local-ID literals and must pass five frozen metamorphic renames before original-fixture scoring.
- **Stability**: permutations and seeds are literal rows in `research/probe-procedures.yaml`; concurrency is one, temperature is zero where supported, decoding/model/runtime/device are pinned, failures count as failed trials, and only `converted_at` is excluded from canonical comparison.
- **Lifecycle**: disposable copies run edit, rename, delete, restore, branch switch, schema change, model/config change, forced regeneration failure, rollback, and cleanup. Each row fixes expected cache key, invalidation deadline (next read must refuse stale state), atomicity, derived diff, and residue.
- **Operations**: `research/probe_operations.sh` creates a fresh environment and captures install wall time/disk, package inventory/SBOM, dated license/vulnerability snapshots, import/cold/warm/RSS trials, offline behavior, uninstall, and residual files. Cache and model bytes are included. Linux x86_64 and Windows x86_64 registry rows begin `UNTESTED`; upstream claims cannot change them to observed.
- **Privacy**: `research/probe_privacy.sh` applies the loopback/canary/residue contract above and records endpoint and filesystem observations. It never transmits repository content remotely.

### Candidate Option Lattice

`research/candidate-registry.csv` instantiates each named candidate with exactly one value or explicit `N/A` for every normalized axis. It also records admissibility predicate, prune/scope rationale, fact classes affected, migration/rollback contract, and evidence status. The axes are:

1. **Representation**: current source formats; DoclingDocument; typed semantic records; property graph; explicitly enumerated composite.
2. **Fact-level authority and mutation owner**: current per-fact-class authority; derived/no writer; Docling writer; semantic-model writer; graph writer.
3. **Transform**: existing reader; deterministic native; author-augmented deterministic; Docling structural; schema extraction; ordered hybrid.
4. **Persistence/location**: ephemeral memory; hidden content-addressed local cache; committed sidecar; hosted store; one-time export; canonical local store.
5. **Lifecycle**: explicit disposable; on-demand hash cache; transactional incremental; CI; background; write-through canonical.
6. **Aggregation/fusion**: artifact; logical mission; repository; cross-repository.
7. **Inference backend**: none; pinned local; remote provider.
8. **Egress/retention/consent**: none; local retained; remote separate opt-in; remote default.

Named registry rows:

- C0 current/manual, no new representation;
- C1 current authorities plus existing dossier/structured readers;
- C2 current authorities plus author-augmented deterministic projection;
- C3 current authorities plus structural DoclingDocument ephemeral/cache projection;
- C4 current authorities plus pinned-local Docling semantic cache;
- C5a current authorities plus deterministic graph core;
- C5b C5a plus optional pinned-local semantic enrichment, scored separately from its core;
- C6a one-time structural DoclingDocument export;
- C6b one-time semantic graph export;
- C7g/C7b greenfield and brownfield-cutover canonical DoclingDocument with generated Markdown/graph views;
- C8g/C8b greenfield and brownfield-cutover canonical typed semantic model with Markdown/graph views;
- C9g/C9b greenfield and brownfield-cutover canonical graph with generated Markdown view.

Brownfield C7b–C9b remain explicit requested conversion candidates, not pre-rejected. They can pass only with one-way transactional cutover, immutable pre-cutover source preservation, sole writer, rollback, and complete consumer migration; failure of any contract rejects them. Greenfield C7g–C9g are scored separately. Other explicitly pruned cells remain in the registry: remote-default, DRG namespace reuse, bidirectional editing, unconsented hosted projections, and cross-repository fusion without authorization/identity/contradiction rules.

Every persisted candidate has a lifecycle state machine covering create/read, content edit, rename, delete/restore, branch/worktree divergence, schema/model/config upgrade, failed regeneration, stale-read refusal, garbage collection, export/cache deletion, and version compatibility. Aggregated candidates must preserve `repository_uuid + mission_id + artifact identity + local ID`, permission intersection, contradictory facts as distinct sourced claims, provenance through fusion, and a non-merge rule unless entity equivalence is explicitly proven. Missing legacy identity is namespaced by repository remote/path hash and marked provisional; it is never silently merged.

## Frozen Decision Rules

### Mandatory Rejection Gates

- Byte-preserving replacement: exact SHA-256 equality of input and exported UTF-8 bytes is required for a byte-preserving claim. BOM, LF/CRLF, trailing spaces, ordering, escaping, comments, and all other bytes count. Normalized structural fidelity is a separate track and cannot rescue byte inequality.
- Structural fidelity: a frozen golden suite covers frontmatter, HTML comments, checkboxes, nested lists, tables, links/anchors, fence language/indentation, raw HTML, Unicode/diacritics/NFC-NFD, BOM, LF/CRLF, trailing spaces, repeated text, and source spans. Each construct has an exact oracle; any loss closes candidates requiring that construct.
- Critical semantic facts: zero invented, incorrectly attributed, or cross-mission-collapsed critical requirement, dependency, decision, or acceptance-evidence facts.
- Provenance: 100% of critical atomic attributes/edges resolve through an independently tested chunk→original mapping to tracked path + blob hash + exact original UTF-8 bytes. Native enriched-chunk character offsets or node-only grounding receive at most P1/P2; relationships without an independently resolved source span fail P0.
- Privacy: zero outbound transmission without separate explicit project-scoped consent; zero credential/canary retention in logs, caches, graph/provenance exports, or crash residue.
- Identity/fusion: zero bare mission-local ID collisions; outputs namespace `repository_uuid + mission_id + artifact identity + local ID`. Fixtures include two repositories/missions with `FR-001`, case/punctuation variants, and NFC/NFD diacritics under all merge input orders.
- Authority: probes never mutate canonical artifacts. A counterfactual replacement must prove one-way transactional cutover, immutable source preservation, one mutation owner, rollback, and complete consumer migration; live dual authority, DRG namespace reuse, or hidden mission-state override rejects it.

### Semantic Quality Gates

These gates apply only to C4, C5b, C6b, and other semantic candidates. They do not reject structural C3/C6a or deterministic C5a:

- at least one approved local backend with pinned model, schema, configuration, and input hashes;
- independently reviewed gold truth;
- micro and macro precision/recall/F1 at least 0.95 for nodes, atomic properties, and edges, and at least 0.90 for every preregistered non-empty class; zero-support classes are `N/A`, never perfect;
- critical-edge recall 1.00 and critical hallucination rate 0;
- node identity exact match 1.00, critical properties/edges P0 provenance 1.00, and canonical export node/property/edge multiset Jaccard at least 0.99;
- five clean repetitions plus frozen order permutations with model artifact/revision, serving runtime, quantization/device, seed, decoding, one worker, and failure semantics pinned; after excluding only preregistered volatile timestamps, critical answers are identical and every node/property/edge/provenance/export metric changes by at most 0.01;
- exact/approximate/document/unresolved/fabricated/incorrect provenance reported separately.

If these runs cannot execute, semantic candidates are `UNKNOWN` and `defer—semantic value unevaluated`; structural/deterministic candidates retain their own dispositions.

### Utility and Operational Gates

- Every candidate emits the same canonical answer-row schema. Material utility requires: aggregate and every critical-query correctness non-inferior to the best native baseline; wins on at least four of six queries; paired correctness improvement of at least 20 percentage points with a non-negative 95% paired-bootstrap lower bound (10,000 resamples, seed `20260818`); and required citations. Five single-researcher timing trials are exploratory additional evidence only; even a 2× speedup cannot substitute for correctness.
- Default dependency integration is rejected when clean isolated install adds at least 100 MiB, downloads a model or contacts a network, or any of `spec-kitty --version`, `spec-kitty next --help`, and a frozen local status query exceeds 2.0 seconds p95 over five cold and five warm runs. Record disk delta including caches/models, peak RSS, import time, SBOM, licenses, dated vulnerability scan, offline run, uninstall, and residue. Optional/out-of-process candidates are scored separately.
- A committed sidecar is rejected if a frozen one-line edit/rename/delete/restore/branch-switch/config/schema scenario changes more than five derived files or 50 derived lines, varies across five runs, indexes itself, enters hosted upload without separate consent, returns stale data on the next read, or cannot atomically refuse/rollback a failed refresh.
- Untested Linux or Windows behavior, unavailable local semantic extraction, or unresolved ecosystem consumers forces `defer` for production adoption even if a narrower macOS structural probe passes.

### Scoring

Every applicable gate is `PASS|FAIL|UNKNOWN|N/A` with evidence IDs. `FAIL` rejects that disposition; `UNKNOWN` forces `defer/unevaluated` and cannot be called surviving. Only all-`PASS` candidates receive two independent 0–5 ratings for query utility (25%), fidelity/provenance (20%), determinism/lifecycle (15%), privacy/security (15%), operational footprint/cross-platform (10%), Git/human ergonomics (10%), and implementation/maintenance burden (5%), with adjudication and ±20% weight sensitivity.

Shared anchors: 0 = absent/catastrophic; 1 = major deficit; 2 = below best native baseline; 3 = parity with manageable costs; 4 = preregistered material improvement; 5 = improvement materially beyond threshold with no meaningful new cost. Disposition mapping: any gate `FAIL` = reject; any gate `UNKNOWN` = defer; all structural gates pass and score 3.0–3.49 = bounded structural experiment; all applicable gates pass, utility passes, and score at least 3.5 = bounded pilot; score at least 4.0 plus Linux/macOS/Windows evidence, ecosystem compatibility, and validated user demand = production candidate. This mission has no user study, so it cannot recommend production adoption.

## Provenance and Privacy Model

Atomic-fact provenance grades:

- **P0 exact**: original tracked path + Git blob/content hash + exact original span. Byte offsets are zero-based, half-open indexes over raw bytes; line numbers are one-based inclusive over original newline bytes. An automated resolver must reproduce the cited bytes exactly.
- **P1 approximate**: original path/hash + normalized chunk span;
- **P2 document**: original path/hash only;
- **P3 unresolved**: source document known, supporting content unresolved;
- **P4 fabricated/misattributed**: unsupported or wrong source.

Critical authored facts require P0. Non-critical inferred themes may use P1 only when visibly labelled inferred and never drive a gate. P2/P3 cannot answer preregistered queries; P4 triggers rejection.

The mapping oracle explicitly tests repeated strings, UTF-8 multibyte text, NFC/NFD, CRLF, and transformed/enriched chunks. If original bytes cannot be resolved unambiguously, grade P1 or worse. Edge provenance is tested independently of node provenance.

The data-flow review covers Docling conversion, model endpoint, local model retention, caches, debug traces, source/chunk text embedded in provenance, graph exports, file paths, permissions, Git staging, dossier indexing, hosted body upload, retention/deletion, crash cleanup, prompt injection, malicious markup/links, and synthetic secret canaries. Hosted-sync consent is not inference/conversion consent. Privacy probes enforce loopback-only networking; unset then poison remote provider/endpoint variables; place unique canaries in content, path, and a task-scoped environment variable; snapshot declared temp/cache roots and modes; scan raw, base64, URL, and JSON-escaped variants; and repeat after a forced exception and SIGTERM. Any undeclared endpoint, world-readable residue, or canary after declared cleanup is a failure.

## Consumer and Authority Census

The matrix at `research/consumer-matrix.csv` is machine-seeded and manually reviewed. Required categories: artifact producers; human/agent prompt readers; filename and frontmatter/headings/ID parsers; `MissionArtifactKind` placement/commit routing; expected-artifact manifests; runtime guards/events; dossier/index/hash/drift/API/dashboard; review/accept/merge/retrospective; sync allowlists/consent/history; upgrade/migration/doctor; recursive scans; Git diff/merge/blame/search/sparse-worktree behavior. Each row names reader/writer, contract, physical/logical surface, candidate-specific replacement/sidecar impact, migration/rollback effect, and evidence source.

`research/authority-inventory.csv` separately inventories authored prose, frontmatter identity, `meta.json`, runtime events/status, review verdicts, acceptance proof, dossier/index state, and derived exports. Each fact class names canonical source, permitted writer, conflict winner, mutation transaction, lifecycle owner, and candidate-specific migration/rollback. Whole-mission "authority" is never treated as a single switch.

Out-of-tree SaaS, tracker, orchestrator, Go, hub, extension, automation, and user-script consumers remain explicit ecosystem residual risk unless directly evidenced. This mission may conclusively assess in-repo CLI compatibility; it may not claim ecosystem-safe replacement.

## Artifact Manifest

| Role | Canonical path | Notes |
|---|---|---|
| Research contract | `kitty-specs/docling-graph-kitty-specs-01M0A0FG/spec.md` | Locked scope |
| Methodology/preregistration | `kitty-specs/docling-graph-kitty-specs-01M0A0FG/plan.md` | This document |
| Source register | `kitty-specs/docling-graph-kitty-specs-01M0A0FG/research/source-register.csv` | Every reviewed source/exclusion |
| Evidence log | `kitty-specs/docling-graph-kitty-specs-01M0A0FG/research/evidence-log.csv` | Stable evidence IDs |
| Sealed preregistration | `kitty-specs/docling-graph-kitty-specs-01M0A0FG/research/preregistration-manifest.json` | SHA-256/tree hash of every confirmatory input |
| Query registry | `kitty-specs/docling-graph-kitty-specs-01M0A0FG/research/query-registry.yaml` | Frozen before probes |
| Candidate registry | `kitty-specs/docling-graph-kitty-specs-01M0A0FG/research/candidate-registry.csv` | Instantiated/pruned lattice cells |
| Baseline procedures | `kitty-specs/docling-graph-kitty-specs-01M0A0FG/research/baseline-procedures.yaml` | Commands, timing, order, budgets |
| Selector | `kitty-specs/docling-graph-kitty-specs-01M0A0FG/research/select_corpus.py` | Sole executable sampling rule |
| Corpus manifest | `kitty-specs/docling-graph-kitty-specs-01M0A0FG/research/corpus-manifest.csv` | Paths, hashes, strata, syntax |
| Golden fixtures and truth | `kitty-specs/docling-graph-kitty-specs-01M0A0FG/research/fixtures/` | Inputs, atoms, reviews, adjudication |
| Consumer matrix | `kitty-specs/docling-graph-kitty-specs-01M0A0FG/research/consumer-matrix.csv` | Readers/writers/authority |
| Authority inventory | `kitty-specs/docling-graph-kitty-specs-01M0A0FG/research/authority-inventory.csv` | Fact-level authority/mutation/lifecycle |
| Contradiction register | `kitty-specs/docling-graph-kitty-specs-01M0A0FG/research/contradictions.csv` | Supporting/challenging evidence disposition |
| Probe method/results | `docs/research/docling-graph-kitty-specs/data/` | Reproducible scripts and immutable outputs |
| Option scorecard | `docs/research/docling-graph-kitty-specs/option-scorecard.csv` | Gate outcomes + weighted scores |
| Risk register | `docs/research/docling-graph-kitty-specs/risk-register.md` | Likelihood/impact/mitigation |
| Decision findings | `kitty-specs/docling-graph-kitty-specs-01M0A0FG/findings.md` | Runtime synthesis artifact |
| Publication report | `docs/research/docling-graph-kitty-specs/report.md` | Human-facing canonical publication |
| Runtime publication pointer | `kitty-specs/docling-graph-kitty-specs-01M0A0FG/report.md` | Short fidelity-checked pointer/abstract, not a duplicate report |
| Publication manifest | `docs/research/docling-graph-kitty-specs/publication-manifest.json` | Hash-binds report, inputs, results, and pointers |
| Review evidence | `kitty-specs/docling-graph-kitty-specs-01M0A0FG/research/adversarial-reviews.md` | Point-cut findings and dispositions |
| Process tracers | `kitty-specs/docling-graph-kitty-specs-01M0A0FG/traces/` | Approach, decisions, tooling friction |

Raw probe outputs are content-addressed inputs to evidence rows. A generated publication manifest hashes every input/output, binds each evidence row to raw-result hashes, and records the report Git blob and commit. The runtime pointer is generated from that manifest and includes the report hash. Publication verification fails on drift. The report is the sole long-form publication; the pointer does not restate findings.

## Methodology Decisions

| Decision | Choice | Alternatives | Rationale / trade-off |
|---|---|---|---|
| M-01 | Freeze commits and preregister before confirmatory probes | Adapt while probing | Prevents post-hoc thresholds; exploratory pre-spec observations must be rerun or labelled exploratory |
| M-02 | Mixed-method case study | Pure literature review; full product experiment | Source code and real artifacts answer feasibility; user demand remains intentionally unresolved |
| M-03 | Three native baselines | Compare only with Markdown/`rg` | Avoids attributing ontology/index value uniquely to Docling |
| M-04 | Atomic-fact provenance | Node-level grounding | A grounded identifier cannot validate an invented attribute/edge |
| M-05 | Local-only semantic inference | Remote provider | No approved egress/retention boundary; reduced model choice is accepted |
| M-06 | Mandatory gates before weighted score | Score every option | Safety/fidelity failures cannot be averaged away by convenience |
| M-07 | Bounded in-repo census + ecosystem residual | Claim all consumers; clone all repos | Achievable and honest; replacement confidence remains insufficient |
| M-08 | Publication outside `kitty-specs` with runtime pointer | Duplicate full report | Follows research deliverable separation while avoiding dual long-form authority |
| M-09 | Two-stage freeze ending in one sealed bundle | Plan-only freeze | Corpus/gold/configs must be fixed before candidate exposure; bundle changes invalidate results |
| M-10 | Structural and semantic dispositions separated | One Docling verdict | Structural parsing does not require inference; missing local inference cannot manufacture a structural rejection |
| M-11 | Fact-class authority + instantiated candidate registry | Whole-system authority labels | Makes invalid brownfield cells, ownership, migration, and rollback auditable |
| M-12 | Exact answer-row and byte/span oracles | Narrative evaluator judgement | Removes candidate-specific interpretations and ambiguous provenance/fidelity grades |

## Quality Gates

### Before Gathering

- [x] Research question, boundaries, and counterfactual authority postures are explicit.
- [x] Source revisions, inclusion/exclusion criteria, normalized option axes, query set, baseline contracts, thresholds, weights, missing-data rules, and saturation rules are specified.
- [x] Artifact roles and publication authority are declared.
- [x] Post-methodology adversarial review findings are incorporated or explicitly rebutted.
- [ ] This plan is committed and its Git blob hash recorded in `research/query-registry.yaml`.
- [ ] Sealed preregistration bundle exists, has two-reviewer/adjudicator attestations, is hash-addressed and committed, and no confirmatory candidate has run.

### Before Synthesis

- [ ] Source/evidence registers validate and minimum runtime source events exist.
- [ ] Corpus/query/consumer manifests satisfy required coverage.
- [ ] Exploratory evidence is distinguished from confirmatory reruns.
- [ ] Mandatory gates and missing semantic/cross-platform evidence are reported without imputation.
- [ ] Post-gathering adversarial review findings are incorporated.

### Before Publication

- [ ] Every claim maps to evidence IDs and registered sources.
- [ ] Findings contain counter-cases, alternatives, limitations, and threats to validity.
- [ ] Report, scorecard, risk register, and runtime pointer agree.
- [ ] Independent publication review and `publication_approved` event are recorded.

## Known Workflow Gap

`spec-kitty plan` currently rejects the canonical research spec because its generic substantive gate requires software-development `FR-###` rows. The gap is recorded in [issue #3546](https://github.com/Priivacy-ai/spec-kitty/issues/3546). This research-native methodology step uses the canonical research plan template and runtime action; no fake FR rows were added.
