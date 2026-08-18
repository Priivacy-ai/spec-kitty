---
type: explanation
updated: 2026-08-18
audience: agentic-framework-core-team
---

# Should Spec Kitty turn `kitty-specs` Markdown into Docling graphs?

## Decision

No—not for existing missions, not as canonical storage, and not as a default dependency.

The attractive part of the idea is real: a graph could make cross-artifact impact, dependency, proof, and provenance questions directly queryable. [EV-001, EV-003, EV-026] But Docling Graph does not turn Markdown structure into those domain relations by itself. It first normalizes Markdown into a `DoclingDocument`; semantic graph value additionally requires an authored schema and an inference backend. [EV-001–EV-003] Safe Spec Kitty use additionally requires exact fact provenance, repository/mission identity, authority precedence, invalidation, consent, rollback, and consumer migration. [EV-004, EV-005, EV-008–EV-012]

The tested structural conversion is not safe as a replacement. Derived semantic/native graph options remain plausible but unevaluated. Current evidence therefore supports retaining Markdown and adjacent structured/event authorities, retaining the existing dossier/readers, rejecting default Docling integration, and doing no graph implementation yet. [EV-001–EV-012, EV-015–EV-026]

## What we would gain

| Gain | What it could mean for Spec Kitty | Evidence status |
|---|---|---|
| Typed entities and relationships | Requirements, WPs, decisions, evidence, and dependencies could become explicit query targets | Upstream capability; Spec Kitty utility `UNKNOWN` [EV-001, EV-003] |
| Cross-artifact traversal | Questions such as “what changes if this requirement moves?” could follow explicit edges rather than prose/file scans | Plausible; no fair candidate ran [EV-003, EV-010, EV-025, EV-026] |
| Interoperable exports | JSON, CSV, Cypher, HTML, and visualization surfaces could support external analysis | Upstream capability [EV-006] |
| Deterministic identity/merge | Declared identity fields can produce stable node IDs and deterministic graph merge behavior | Upstream capability; Spec Kitty namespace still required [EV-004] |
| Source grounding | Nodes can carry compact provenance views into source documents | Upstream capability; insufficient alone for exact critical-edge proof [EV-005] |
| Common document representation | Multiple document types can enter a shared normalized representation | Upstream capability; normalization is not domain semantics [EV-002] |

These are representation capabilities, not demonstrated user outcomes. The mission found no authorized user study, telemetry, or production utility evidence. [EV-024–EV-026]

## What we risk

| Risk | Evidence status |
|---|---|
| Loss of canonical Markdown bytes, constructs, and exact cited spans | Observed for tested structural round-trip [EV-015–EV-017] |
| Split authority across sources, models, graphs, generated views, and event writers | Contract gap [EV-008, EV-009, EV-012] |
| Wrong, collapsed, or unprovable semantic facts/edges | `UNKNOWN`; upstream grounding alone does not meet P0 [EV-004, EV-005, EV-023] |
| Sensitive body/credential egress or residue | Conversion behavior `UNKNOWN`; containment incompatibility observed [EV-011, EV-022] |
| Large default dependency/process footprint | Observed in bounded macOS environment [EV-019–EV-021] |
| Stale caches, identity collision, or unsafe fusion | Lifecycle untested and namespace contract absent [EV-004, EV-008, EV-025, EV-026] |
| Broken in-repo or external consumers | Broad local census; external residual `UNKNOWN` [EV-008–EV-012] |
| Building a graph that solves no valuable user job | `UNKNOWN`; baseline/utility benchmark invalid and no user study [EV-024–EV-026] |

The [full risk register](risk-register.md) maps these risks to exact candidate variants and required controls.

## What the experiments found

### Structural fidelity

The confirmatory corpus contained 37 selected repository files plus two golden fixtures. Each ran three times through Markdown → `DoclingDocument` → Markdown:

- 39 unique inputs; 117 total trials;
- zero conversion errors;
- zero byte-identical round-trips;
- stable repeated exports after the first conversion;
- both golden fixtures failed required construct preservation;
- 10 of 18 Markdown-applicable gold spans failed, eight passed, and two JSON-source atoms were not applicable. [EV-015–EV-017]

This is decisive against the tested default structural exporter as a byte/construct-preserving canonical replacement (`C7b`). [EV-015–EV-017] It does not prove that an optional graph is useless, that semantic facts were wrong, or that a custom greenfield renderer cannot exist.

### Corpus and authority shape

At the frozen Spec Kitty revision, the tracked population contained 385 missions, 10,161 files, and 95,403,203 bytes. The 7,199 Markdown files coexist with 1,734 JSON, 402 JSONL, and 402 YAML/YML files. Markdown also carries dense tables, checkboxes, fences, comments, links, and identifiers. [EV-013, EV-014]

More importantly, a logical mission is not a recursive Markdown directory. Facts are split intentionally across PRIMARY/COORD placement, authored frontmatter, JSON metadata, event-sourced lifecycle/verdict state, review artifacts, acceptance proof, dossier snapshots, and hosted-consent boundaries. The consumer census found 22 in-repo contexts, one bounded Git/human contract, and one unbounded external residual. [EV-008–EV-012]

### Storage and operating cost

A supplementary measurement serialized 571,855 source bytes into 5,310,769 bytes of compact `DoclingDocument` JSON: 9.2869× aggregate and 9.109× median amplification. It was not a preregistered threshold test. [EV-018]

On macOS 15.7.7 arm64, an isolated Python 3.11 environment added 1,205,293,056 bytes and 122 distributions. First import took 54.35 seconds with 743,227,392 bytes peak RSS. Four later imports took 6.88–7.14 seconds with about 696 MB median peak RSS. The environment snapshot found no dated known vulnerability, but that is only a point-in-time result. [EV-019–EV-021]

These numbers reject adding Docling Graph as a default in-process Spec Kitty dependency under the frozen ≥100 MiB gate. [EV-019, EV-020] They do not measure a separately designed optional service, actual Spec Kitty integration, cold-network download, shared cache/model size, Linux/Windows behavior, or complete uninstall cleanup. [EV-019–EV-023]

### Semantic quality and privacy

No approved pinned local generative backend was available. The installed Ollama model was embedding-only. No remote provider was authorized and no model was downloaded after preregistration. Semantic node/edge correctness, exact identity, critical provenance, repeatability, and query value remain `UNKNOWN`. [EV-023]

The privacy harness attempted normal, exception, and SIGTERM paths. Its strict filesystem policy blocked a dependency writing `/dev/null` during import, before conversion or canary handling. Containment compatibility therefore failed. Conversion-time network behavior, leakage, residue, cleanup, exception handling, and SIGTERM handling remain `UNKNOWN`; empty residue is non-evidence. [EV-022]

### Utility comparison

The planned B0/B1 outputs copied sealed gold annotations; they did not execute manual or existing-reader workflows and are explicitly `NOT_EVIDENCE`. The sealed B2/C5a candidate contract withheld identifiers that its exact expected output required, so a blinded implementation could not be scored fairly. Material utility for every new graph posture remains `UNKNOWN`. [EV-024, EV-025]

## Options and disposition

The [full scorecard](option-scorecard.csv) evaluates 21 preregistered candidates. Frozen rules allow a weighted score only after every applicable mandatory gate passes. None did.

| Disposition | Candidates | Meaning |
|---|---|---|
| Retain controls | C0, C1 | Keep current authorities and existing dossier/readers [EV-010, EV-024] |
| Reject | C3a, C3b, C6a, C7b | Observed structural fidelity failure; C3 also fails default-footprint posture [EV-015, EV-016, EV-019] |
| Defer—unevaluated | C2, C4, C5a, C5b, C6b, C7g, C8g, C8b, C9g, C9b, P2 | At least one required gate is `UNKNOWN`; no adoption claim [EV-008, EV-012, EV-022–EV-026] |
| Prune/reject | P1, P3, P4, P5 | Consent [EV-011, EV-023], identity/fusion [EV-004, EV-008], bounded-context [EV-028], or single-authority [EV-008, EV-009, EV-012] contract violation |

The distinction matters: C8b/C9b are not proven impossible; their renderers, cutovers, and migrations were never executed. They are deferred, not falsified. [EV-008, EV-012, EV-025] The answer is still “do not convert now,” because `UNKNOWN` forces defer under the frozen decision rules. [EV-029]

## Dialectical conclusion

### Canonical graph: strongest case and rebuttal

The strongest case is a single typed API with explicit relationships, validation, traversal, and multiple readable/exportable views. A purpose-built greenfield model might make impact questions first-class. [EV-001, EV-003, EV-006]

For existing `kitty-specs`, the rebuttal is stronger: default Docling export loses required bytes/constructs; mission facts have deliberate separate authorities/writers; complete in-repo and external migration is unproven; no transactional cutover, compatible renderer, or rollback passed. C7b is rejected. C8b/C9b remain unfit for adoption because their mandatory evidence is missing. [EV-008, EV-009, EV-012, EV-015–EV-017]

### Optional Docling semantic sidecar: strongest case and rebuttal

The strongest case is a local disposable cache that leaves source authority untouched while offering schema-directed queries and export/visualization. Failure could degrade to current sources. [EV-001, EV-003, EV-006]

The rebuttal is a stack of unknowns: no semantic candidate, no exact edge-provenance proof, no valid utility comparison, no lifecycle test, no complete privacy run, and no cross-platform evidence. The large observed environment/process footprint makes default integration unattractive, though a separately specified optional/out-of-process posture was not tested. [EV-005, EV-019, EV-022–EV-025]

### Deterministic native projection: strongest case and rebuttal

The lowest-authority-disruption hypothesis is a native graph derived from filenames, frontmatter, IDs, event logs, placement rules, and dossier hashes. It could target exact Q1–Q6 joins without LLM inference or Docling normalization. [EV-008–EV-010, EV-026]

It is not a winner: no fair candidate ran, users did not validate the jobs, and authoring, freshness, identity, permission, contradiction, and maintenance costs remain unmeasured. It deserves at most separate user-demand-first research—not implementation or a pilot. [EV-024–EV-026]

## Recommendation

1. Keep Markdown, JSON/YAML, and event logs as their current canonical authorities. [EV-008, EV-009, EV-012, EV-015–EV-017]
2. Keep the Mission Dossier as the current content-addressed index/cache seam. [EV-010]
3. Do not add Docling Graph to the default CLI dependency surface. [EV-019, EV-020]
4. Do not commit or host graph sidecars by default. [EV-011, EV-018, EV-022]
5. Do not begin a native graph implementation on this evidence. [EV-024–EV-026]
6. If user research validates a high-value cross-artifact job, preregister a new source-preserving cache study with a fair generic interface. [EV-025, EV-026]

Any future study must prove exact critical property/edge provenance [EV-005]; namespace repository, mission, artifact, and local IDs [EV-004, EV-008]; preserve contradictory sourced claims and refuse stale reads [EV-008, EV-025]; cover edit/rename/delete/restore/branch/worktree/schema/failure lifecycle [EV-025, EV-026]; pass viable privacy confinement [EV-011, EV-022]; and test Linux/macOS/Windows [EV-007, EV-019]. See the [risk register](risk-register.md).

## Limitations

- One frozen Spec Kitty revision and one pinned Docling Graph revision (`1.9.1`) were studied.
- Structural probes executed Docling conversion/export, not Docling Graph semantic extraction.
- Operations were bounded to macOS arm64 with a warm uv cache.
- No local generative model, Linux/Windows run, production integration, external-consumer census, or user-demand study existed.
- Supplementary storage was observational.
- Current-reader/native material utility was not validly benchmarked.

Those limitations narrow the conclusion. They do not weaken the observed rejection of default structural brownfield replacement.

## Reproducibility and sources

- [Findings and dialectical analysis](../../../kitty-specs/docling-graph-kitty-specs-01M0A0FG/findings.md)
- [Evidence log](../../../kitty-specs/docling-graph-kitty-specs-01M0A0FG/research/evidence-log.csv)
- [Source register](../../../kitty-specs/docling-graph-kitty-specs-01M0A0FG/research/source-register.csv)
- [Results summary](data/results-summary.json)
- [Preregistered plan](../../../kitty-specs/docling-graph-kitty-specs-01M0A0FG/plan.md)
- [Candidate scorecard](option-scorecard.csv)
- [Risk register](risk-register.md)

Primary upstream anchors: [Docling Graph v1.9.1 package contract](https://github.com/docling-project/docling-graph/blob/19815e3147503f78a06e263255667e237830bab9/pyproject.toml), [input formats](https://github.com/docling-project/docling-graph/blob/19815e3147503f78a06e263255667e237830bab9/docs/fundamentals/pipeline-configuration/input-formats.md), [schema templates](https://github.com/docling-project/docling-graph/blob/19815e3147503f78a06e263255667e237830bab9/docs/fundamentals/schema-definition/template-basics.md), [relationships](https://github.com/docling-project/docling-graph/blob/19815e3147503f78a06e263255667e237830bab9/docs/fundamentals/schema-definition/relationships.md), [provenance source](https://github.com/docling-project/docling-graph/tree/19815e3147503f78a06e263255667e237830bab9/docling_graph/core/provenance), and [exports](https://github.com/docling-project/docling-graph/blob/19815e3147503f78a06e263255667e237830bab9/docs/fundamentals/pipeline-configuration/export-configuration.md).
