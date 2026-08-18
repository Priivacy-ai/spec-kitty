# Findings: should `kitty-specs` become Docling graphs?

## Decision

No. Do not convert or replace existing `kitty-specs` Markdown with `DoclingDocument`, typed semantic records, or a canonical graph. Do not add Docling Graph as a default Spec Kitty dependency. The proposed blanket conversion is not worth its demonstrated fidelity and footprint costs, and the graph-utility proposition remains unevaluated. [EV-008, EV-009, EV-012, EV-015, EV-016, EV-019, EV-024, EV-025]

Retain current source formats and the existing dossier/readers (`C0`/`C1`). A deterministic native projection (`C5a`) is only the lowest-authority-disruption hypothesis for separate user-demand-first research. It is not an evidence-ranked winner and is not ready for an implementation pilot. [EV-010, EV-024–EV-026]

## What a graph could add

Docling Graph offers real technical capabilities. [EV-001–EV-006]

- schema-defined entities, properties, and relationships in a directed graph [EV-001, EV-003];
- deterministic identity and merge behavior for explicitly declared identity fields [EV-004];
- traversal across relations that prose and file-level indexes do not directly answer [EV-003, EV-010];
- document/graph exports for JSON, CSV, Cypher, HTML, and visualization workflows [EV-006];
- node-level provenance views and a common representation across supported document inputs [EV-002, EV-005].

Those gains do not arise from “turn Markdown into a graph” alone. Markdown first becomes a normalized `DoclingDocument`; a semantic graph additionally needs an authored Pydantic schema and an inference backend. Cross-mission safety additionally needs Spec Kitty namespaces, fact-level provenance, authority rules, and lifecycle machinery. [EV-001–EV-005, EV-008, EV-009]

## Confirmed costs and failures

- Across 39 inputs and three repetitions, zero of 117 Markdown → `DoclingDocument` → Markdown outputs matched source bytes. Conversion itself did not error and repeated outputs were stable. [EV-015]
- Both golden fixtures lost required constructs. Of 18 Markdown-applicable gold spans, 10 failed and eight passed; two JSON-source atoms were not applicable. This rejects the tested structural/canonical replacement, not every possible derived graph. [EV-016, EV-017]
- The frozen corpus is a mixed logical mission model: 7,199 Markdown files coexist with JSON, JSONL, and YAML authorities. A directory of `.md` files is neither the whole mission nor a safe state authority. [EV-008, EV-013, EV-014]
- Supplementary compact `DoclingDocument` JSON occupied 5,310,769 bytes for 571,855 source bytes: 9.2869× aggregate amplification. This was observational, not a preregistered threshold. [EV-018]
- The isolated macOS arm64 environment added 1,205,293,056 bytes and 122 distributions. First import took 54.35 seconds and ~743 MB peak RSS; four later imports took 6.88–7.14 seconds and ~696 MB median peak RSS. These measurements are bounded process/environment evidence, not Spec Kitty integration timings. [EV-019, EV-020]

## What remains unknown

- No approved local generative model was available. Semantic fact, edge, identity, provenance, stability, and graph-query quality were not tested. [EV-023]
- Strict confinement blocked a dependency's `/dev/null` write before conversion. Containment compatibility failed; conversion-time egress, leakage, residue, cleanup, exception, and SIGTERM behavior remain `UNKNOWN`. [EV-022]
- The sealed B2/C5a candidate API could not fairly support its exact hidden identifier contract. B0/B1 merely replayed sealed annotations and are not baseline performance evidence. Material graph utility therefore remains `UNKNOWN`. [EV-024, EV-025]
- User demand, production workflow value, Linux/Windows behavior, complete cache lifecycle, model/cache footprint, full uninstall cleanup, and external-consumer compatibility were not measured. [EV-007, EV-012, EV-019, EV-023–EV-026]

## Dialectical cases

### Strongest case for canonical conversion

A graph-native authority could offer one typed API, explicit relationships, validation, traversal, and multiple generated views. For greenfield content, a purpose-built canonical model could reduce repeated parsing and make impact queries first-class. [EV-001, EV-003, EV-006]

The counter-case wins for existing `kitty-specs`: observed Docling round-trip loss crosses byte, frontmatter, comment, table, fence, whitespace, and source-span contracts; mission facts deliberately live under multiple writers and event authorities; 22 in-repo contexts plus one bounded Git contract and an external residual require migration analysis; no custom renderer, transactional cutover, or rollback was proven. Greenfield C7g/C8g/C9g remain unevaluated rather than disproven, but they do not answer the requested brownfield conversion. [EV-008, EV-009, EV-012, EV-015–EV-017]

### Strongest case for an optional Docling semantic sidecar

A disposable local graph could preserve Markdown authority while adding schema-directed Q1–Q6 traversal, exports, and visualization. Semantic failure could degrade to current sources rather than corrupt them. [EV-001, EV-003, EV-006, EV-026]

The counter-case is missing evidence, not a claim of impossibility: no approved model ran; upstream node grounding does not meet the mission's exact critical-edge provenance gate by itself; dependency footprint exceeds the default-integration threshold; privacy behavior, freshness, invalidation, branch behavior, and user value are unknown. Current evidence cannot justify integration. [EV-005, EV-019, EV-022–EV-025]

### Strongest case for a deterministic native projection

Existing filenames, frontmatter, IDs, event logs, placement rules, and dossier hashes could feed a source-preserving graph without an LLM or Docling normalization. This minimizes authority disruption and can target exact impact/proof queries. [EV-008–EV-010, EV-026]

The counter-case is that no fair candidate ran, no users validated those jobs, and typed-link authoring, invalidation, identity, permissions, and maintenance burden were not measured. The next step is separate research, not implementation. [EV-024–EV-026]

## Candidate disposition

- Retain controls: `C0`, `C1`.
- Reject under frozen gates: `C3a`, `C3b`, `C6a`, `C7b`.
- Defer as unevaluated: `C2`, `C4`, `C5a`, `C5b`, `C6b`, `C7g`, `C8g`, `C8b`, `C9g`, `C9b`, `P2`.
- Prune/reject by authority, consent, or identity contract: `P1`, `P3`, `P4`, `P5`.

No candidate qualified for weighted scoring because every adoption candidate had at least one `FAIL` or `UNKNOWN` mandatory gate. [EV-015–EV-026, EV-029]

## Revisit conditions

Only reopen derived-graph investment after all of these are independently preregistered:

1. Users validate concrete cross-artifact jobs that current dossier/readers cannot satisfy.
2. A generic candidate interface permits fair blinded native and Docling comparisons.
3. Markdown, structured files, and event logs remain canonical; the graph is local, disposable, hash-bound, and stale-read refusing.
4. Every critical property and edge resolves to tracked path, blob hash, and exact original bytes.
5. Identity, permissions, contradictions, rename/delete/restore, branch/worktree, upgrade, failure, and garbage-collection behavior pass.
6. Privacy runs complete under a viable confinement policy with network and residue proof.
7. Optional footprint and Linux/macOS/Windows behavior meet their own gates.

Until then, “actual graph” is an appealing representation idea without demonstrated Spec Kitty user value.
