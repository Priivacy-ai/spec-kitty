# Risk register

Status vocabulary: `OBSERVED`, `UNKNOWN`, `CONTRACT_GAP`, or `NOT_APPLICABLE`. `UNKNOWN` is never treated as safety.

| ID | Risk | Severity | Evidence state | Affected options | Evidence | Required control |
|---|---|---:|---|---|---|---|
| R-01 | Canonical Markdown bytes and constructs are lost during Docling round-trip | Critical | `OBSERVED` | C3a, C3b, C6a, C7b default exporter | EV-015–EV-017 | Keep source artifacts canonical; reject required-fidelity dispositions |
| R-02 | Competing source, semantic-model, graph, and generated-view writers create split authority | Critical | `CONTRACT_GAP` | C7b, C8b, C9b, P5 | EV-008, EV-009, EV-012 | One mutation owner, transactional cutover, immutable rollback, complete consumer migration |
| R-03 | Inferred properties or edges lack exact fact-level source spans | High | `CONTRACT_GAP` | C4, C5b, C6b, C8g, C8b | EV-005 | Independently resolve every critical fact and edge to tracked path, blob, and exact bytes |
| R-04 | Semantic extraction invents, merges, or omits critical mission facts | Critical | `UNKNOWN` | C4, C5b, C6b, C8g, C8b | EV-023 | Approved pinned local backend plus blinded gold precision/recall and zero-hallucination gates |
| R-05 | Conversion or model runtime leaks or retains sensitive bodies/credentials | Critical | Containment incompatibility `OBSERVED`; conversion behavior `UNKNOWN` | C3a, C3b, C4, C5b, C6a, C6b, C7g, C7b, C8g, C8b | EV-011, EV-022, EV-023 | Consent boundary, runnable confinement, network proof, canary cleanup, exception/SIGTERM tests |
| R-06 | Default dependency footprint slows or destabilizes the CLI | High | `OBSERVED` for isolated environment/process footprint | C3a, C3b, C4, C7g, C7b if default-integrated | EV-007, EV-019–EV-021 | Reject default dependency; only separately scored optional/out-of-process design could reopen |
| R-07 | Derived graph serves stale data after edits, renames, deletion, branch switch, or failed refresh | High | `UNKNOWN` | C3b, C4, C5a, C5b, P2 | EV-025, EV-026 | Hash-bound state machine, atomic stale refusal, delete/restore/branch/schema failure probes |
| R-08 | Mission-local IDs collide across missions or repositories during fusion | Critical | `CONTRACT_GAP` | C5a, C5b, C9g, C9b, P3 | EV-004, EV-008 | Namespace repository + mission + artifact + local ID; preserve contradictions; forbid unproved merge |
| R-09 | In-repo or external readers break on new filenames, bytes, frontmatter, APIs, or paths | Critical | `OBSERVED` in-repo breadth; external residual `UNKNOWN` | C7b, C8b, C9b | EV-008, EV-009, EV-012 | Producer/reader/writer migration matrix, compatibility views, ecosystem study, rollback rehearsal |
| R-10 | Generated graph/JSON harms Git diff, merge, blame, search, or sparse checkout | High | `UNKNOWN` for custom renderers; C7b default-export byte change `OBSERVED` | C7b, C8b, C9b, P2 | EV-015, EV-016 | Representative Git workflow experiments; keep caches untracked and disposable |
| R-11 | Stored derived representation materially amplifies repository/cache size | Medium | `OBSERVED` supplementary 9.2869× DoclingDocument JSON | C3b, C7g, C7b | EV-018 | Measure representative lifecycle/storage cost; cache quotas and deletion; never commit by default |
| R-12 | The graph solves no sufficiently valuable user job | High | `UNKNOWN` | C2, C3a, C3b, C4, C5a, C5b, C6a, C6b, C7g, C7b, C8g, C8b, C9g, C9b, P1, P2, P3, P4, P5 | EV-024–EV-026 | User-demand study before implementation; fair generic query benchmark afterward |
| R-13 | Platform behavior differs on Linux or Windows | High | `UNKNOWN` | C2, C3a, C3b, C4, C5a, C5b, C6a, C6b, C7g, C7b, C8g, C8b, C9g, C9b, P2, P3 | EV-007, EV-019 | Frozen Linux/macOS/Windows matrix before any production claim |
| R-14 | Cache/model/dependency cleanup is incomplete | Medium | `UNKNOWN` | C3b, C4, C5b, C7g, C7b, C8g, C8b | EV-019–EV-023 | Measure uninstall disk/cache/model residue and recovery rather than package-name residue only |

No risk is accepted for production by this mission.
