# Research Specification: Docling Graph for Spec Kitty Mission Artifacts

**Mission Branch**: `research/docling-graph-kitty-specs`  
**Created**: 2026-08-18  
**Status**: Scoped  
**Research Type**: Mixed-method empirical case study and primary-source review

## Research Question & Scope

**Primary Research Question**: Would any Docling-based representation of user `kitty-specs` artifacts create enough measurable traceability, impact-analysis, or discovery value to justify its fidelity, privacy, dependency, lifecycle, migration, and maintenance costs—and which authority and adoption posture, if any, is supported by the evidence?

**Falsifiable Proposition**: At least one Docling-based candidate materially improves correctness or operator time on preregistered cross-artifact queries over current workflows and a deterministic native Spec Kitty index, while meeting frozen fidelity, provenance, stability, privacy, and operational gates. The proposition is refuted if native approaches perform comparably, critical facts are lost or invented, results are unstable, provenance cannot resolve to original source locations, or costs exceed the preregistered thresholds.

**Sub-Questions**:

1. What distinct representations are actually available—source Markdown, DoclingDocument structure, template-validated Pydantic extraction, and NetworkX knowledge graph—and which user problem could each solve?
2. Which high-value queries are difficult with current Markdown, Mission Dossier metadata, JSON/YAML/JSONL authorities, and existing parsers?
3. How accurately, reproducibly, and traceably can Docling Graph recover requirements, work packages, dependencies, decisions, evidence, and lifecycle relationships from representative mission artifacts?
4. How does Docling-based semantic extraction compare with a deterministic projection built from canonical structured authorities and Markdown identifiers?
5. What are the install size, latency, storage, inference cost, cross-platform, offline, security, consent, and maintenance consequences?
6. Which adoption posture—reject, defer, optional experiment, derived sidecar, one-time export, or canonical replacement—is supported by the evidence?

**Scope**:

- **In Scope**: Current Docling Graph primary documentation and source; current Spec Kitty artifact/runtime/dossier/placement/sync seams; a stratified sample of tracked `kitty-specs` Markdown plus adjacent structured authorities; deterministic and Docling-oriented representation options; fidelity and round-trip probes; provenance, identity, graph-fusion, query-utility, dependency, privacy, lifecycle, and migration analysis; actionable recommendation and follow-up experiment design.
- **Out of Scope**: Implementing production graph support; changing the Doctrine Relationship Graph (DRG); replacing or mutating user Markdown; transmitting private repository content to a remote model; selecting a commercial inference provider; graph database procurement; broad documentation conversion outside `kitty-specs`; claiming user demand without user research.
- **Boundaries**: Evidence is collected against frozen repository commits and upstream sources available on 2026-08-18. Experiments MUST NOT mutate current canonical artifacts; all probe outputs remain disposable. Research MUST nevertheless evaluate Markdown-canonical, DoclingDocument-canonical, typed-semantic-model-canonical, graph-canonical, derived-sidecar, one-time-export, author-augmented-native, and no-change postures counterfactually. Any mission-content graph is a separate bounded context and MUST NOT reuse DRG identity, vocabulary, activation, or authority semantics.

**Expected Outcomes**:

- A reproducible source register, evidence log, corpus census, fidelity probe, dependency/operational assessment, option matrix, risk register, and decision-ready `findings.md`.
- A peer-review-ready report under `docs/research/docling-graph-kitty-specs/` answering what Spec Kitty would gain, what it would risk, and whether further investment is justified.
- A concrete recommendation with explicit kill criteria and, only if warranted, a bounded follow-up pilot design that preserves Markdown authority.

**Stakeholders and Audience**:

- Primary audience: Spec Kitty maintainers and architects deciding whether to fund a prototype.
- Secondary audience: Spec Kitty users whose mission artifacts, privacy, Git workflows, and offline experience would be affected.
- Accountable decision-maker: the human operator reviewing the pull request; this research does not authorize adoption or migration.
- Required review lenses: CLI/runtime maintainer, mission operator, privacy/security owner, and cross-platform/offline advocate. Without direct user research, utility conclusions remain maintainer hypotheses and cannot support production adoption.

**Constraints and Assumptions**:

- Use primary sources and reproducible local observations wherever possible; secondary sources may contextualize but cannot carry adoption claims.
- No credentials, private content, or mission documents may be sent to external inference services.
- Semantic extraction may run only through an approved local model/privacy boundary. Without successful pinned semantic runs against reviewed ground truth, permissible conclusions are `reject` or `defer—semantic value unevaluated`; the research MUST NOT recommend a Docling experiment, sidecar, or adoption.
- A graph is not proof of mission completeness or runtime state; canonical artifacts and events retain those roles.
- The in-repo CLI consumer census is mandatory. Out-of-tree SaaS, tracker, orchestrator, Go, hub, extension, automation, and user-script consumers are recorded as ecosystem residual risk unless separately evidenced; replacement confidence is insufficient while that residual remains.

## Research Methodology Outline

### Research Approach

- **Method**: Mixed methods—structured primary-source review, repository forensics, controlled conversion probes, deterministic-baseline design, and dialectical decision analysis.
- **Data Sources**: Version-pinned Docling Graph repository/docs; Docling primary docs/code where parsing behavior is relevant; Spec Kitty charter, ADRs, code, templates, and tracked mission corpus; reproducible local measurements.
- **Analysis Approach**: Evidence-tiered thematic synthesis plus a weighted option scorecard. Every load-bearing conclusion will be tested as a falsifiable proposition with the strongest counter-case from the same evidence base.

### Success Criteria

- Register and review at least 12 high-relevance primary sources, including upstream code/docs and local canonical Spec Kitty authorities; record exclusions and access dates.
- Characterize the full tracked artifact corpus and use a deterministic coverage matrix to select at least 12 specimens across artifact role, mission type/era, size, topology, and high-risk syntax; every required stratum and syntax feature MUST have explicit coverage.
- Define orthogonal option axes—authority, derivation engine, persisted form/location, refresh/invalidation lifecycle, aggregation scope, and inference/egress boundary—then enumerate and prune named candidates before scoring them.
- Commit a hash-addressed preregistration before probes: at least six user/job queries, owners, fixtures, gold answers, partial-credit rubric, atomic-fact provenance grade, three baselines, sampling rule, configurations, repeat count, weights, missing-data handling, numeric rejection/defer/pilot gates, and stop rules.
- Trace every factual claim and recommendation to stable evidence IDs; identify limitations, contradictory evidence, and at least one alternative interpretation for every major finding.
- Run bounded, profile-loaded adversarial reviews after scoping, methodology, gathering, synthesis, and before publication; incorporate or explicitly rebut every confirmed finding.
- Produce one artifact manifest naming the canonical role/path for evidence CSVs, corpus/query registries, probe harness and immutable outputs, consumer matrix, scorecard, risk register, adversarial reviews, findings, and publication report.

## Research Requirements

### Data Collection Requirements

- **DR-001**: Research MUST collect primary evidence from Docling Graph source/docs, Docling parser source/docs as needed, Spec Kitty canonical code/docs, and reproducible corpus measurements.
- **DR-002**: All reviewed sources, including exclusions, MUST be documented in `research/source-register.csv`.
- **DR-003**: Citations MUST use stable source IDs, version/commit context, URLs or repository paths, and access date 2026-08-18.
- **DR-004**: Empirical observations MUST include commands or scripts, input identifiers/hashes, outputs, and environmental limits sufficient for reproduction.
- **DR-005**: The corpus MUST be stratified by artifact role, mission era/type, size, and syntax features; convenient examples alone are insufficient.
- **DR-006**: Repository and upstream commits, eligible path/extensions, generated/current-mission exclusions, topology/lifecycle treatment, deterministic selection rule, and corpus hashes MUST be frozen before conversion probes.
- **DR-007**: Gathering stops when every preregistered decision question and corpus stratum has adequate evidence or the source cap in the plan is reached; additional leads become follow-ups rather than unbounded scope.

### Analysis Requirements

- **AR-001**: Findings MUST keep representation layer separate from authority/adoption posture. Candidates MUST include current workflow, existing dossier/structured parsers, best-effort deterministic native projection, author-augmented native model plus deterministic projection, DoclingDocument archive, Docling semantic projection, layered hybrid, three distinct canonical replacement forms, one-time export, and no change.
- **AR-002**: Methodology MUST be clearly documented and reproducible, with preregistered inclusion/exclusion rules and decision thresholds.
- **AR-003**: Limitations, threats to validity, source conflicts, and missing semantic-extraction evidence MUST be explicit.
- **AR-004**: Claimed benefits MUST map to named user queries and outperform current/native baselines; “files become graphs” is not a benefit by itself.
- **AR-005**: Critical facts MUST preserve canonical mission/project identity, artifact kind, source path/hash, original line or byte span, authored-versus-inferred status, schema/config identity, and confidence.
- **AR-006**: Remote model extraction requires separate, explicit project-scoped egress consent; existing hosted-sync consent MUST NOT be treated as authorization.
- **AR-007**: The deterministic baseline MUST be a disposable, effort-capped research harness over named canonical inputs and relations; unsupported relations are recorded rather than expanding into product implementation.
- **AR-008**: A machine-derived producer/reader/writer/authority matrix MUST cover filenames, frontmatter/headings/IDs, artifact placement and commit routing, expected-artifact manifests, prompts, dossier/index/hash/drift, review/accept/merge/retrospective, sync/consent/history, dashboard/doctor/upgrade, recursive scans, and Git diff/merge/blame/search behavior.
- **AR-009**: Privacy analysis MUST trace conversion/model endpoints, local retention, caches, traces, graph/provenance exports, embedded source text and paths, permissions, Git inclusion, hosted sync/body upload, deletion, crash cleanup, and prompt-injection/secret-canary behavior.
- **AR-010**: Operational evidence MUST measure or explicitly mark untested clean-install/import/conversion, disk, memory, latency, offline, model-download, dependency/SBOM/license/vulnerability, and uninstall behavior for Linux, macOS, and Windows; untested platforms reduce confidence and bar adoption.

### Quality Requirements

- **QR-001**: All factual claims MUST be supported by cited evidence; unsourced statements MUST be labelled hypotheses.
- **QR-002**: Confidence levels MUST be assigned to findings in `research/evidence-log.csv` and propagated without inflation into conclusions.
- **QR-003**: Alternative interpretations MUST be considered and consequential disagreement adjudicated from source evidence or a focused second opinion.
- **QR-004**: Replacement is rejected if any source construct required by Spec Kitty fails byte/structural round-trip or if any current Markdown consumer lacks a credible migration path.
- **QR-005**: Any positive adoption recommendation MUST include deterministic invalidation, namespaced identity, no self-indexing cycle, rollback, explicit graph-domain terminology, privacy defaults, and cross-platform isolation.
- **QR-006**: Provenance MUST be scored per atomic attribute and edge as exact-original-span, approximate/chunk, document-scope, unresolved, fabricated, or incorrectly attributed. Critical requirements, decisions, dependencies, and evidence links require exact original path + content hash + line/byte span.
- **QR-007**: Semantic candidates MUST use a pinned backend/model/schema/config and independently reviewed node/attribute/edge ground truth; repeat runs and shuffled input order MUST measure identity, property, edge, provenance, fusion, and export drift.
- **QR-008**: Replacement is a bounded falsification track during this mission: the first critical round-trip loss closes byte-preserving replacement, while other canonical-model forms retain separate scores. A full ecosystem migration design is follow-up work, not a condition for completing this research.

## Key Concepts & Terminology

- **Canonical mission artifact**: Human-authored or machine-authoritative Spec Kitty source whose existing file/event contract determines mission meaning or lifecycle.
- **DoclingDocument**: Docling's structured document model produced from an input document; distinct from a semantic knowledge graph and not presumed byte-round-trippable.
- **Docling-derived mission knowledge projection**: A disposable, non-authoritative graph generated from canonical mission artifacts. It MUST NOT be called a DRG.
- **Deterministic native index**: A graph/index derived without LLM inference from existing Spec Kitty JSON/YAML/JSONL authorities, artifact manifests, dossier metadata, and explicit Markdown identifiers.
- **Authored edge**: A relationship explicitly present in a canonical source; distinct from an inferred edge proposed by a model.
- **Projection provenance**: Metadata linking a generated fact to immutable project/mission/artifact identity and an exact or qualified source location; it is not mission authority.
- **DRG**: Spec Kitty's Doctrine Relationship Graph. This term remains reserved for doctrine and is outside the proposed projection's bounded context.

## Evidence Tracking Guidance

- Log every reviewed source in `research/source-register.csv` with citation, URL or repository path, access date, relevance, status, version/commit, and exclusion reason where applicable.
- Capture each key finding in `research/evidence-log.csv` with a stable evidence ID, source ID, method, confidence, limitations, and notes.
- Reference evidence IDs from `findings.md`, the publication report, option scorecard, and risk register so the full decision trail is auditable.
