# Research Log: Docling Graph for `kitty-specs`

## Frozen inputs

- Spec Kitty: `cf0f7e3a7db149f8b73006f9bca8bb97df880704`
- Docling Graph: `19815e3147503f78a06e263255667e237830bab9` (`1.9.1`)
- Preregistration commit: `e6fcdb4ba96f8e3da0a2d4b22595ada602290232`
- Preregistration tree: `15bb54c3989210ec095123d520f5c4a2a327bace9d40fc6bcadcd8190e73cf33`

## Gathering ledger

| Stream | Evidence | Status |
|---|---|---|
| Primary-source review | 24 included sources; 8 explicit contradictions | Complete |
| Authority/consumer census | 15 fact classes; 22 in-repo contexts, one bounded Git contract, and one external residual | Complete for known local surfaces; ecosystem residual `UNKNOWN` |
| Corpus census | 10,161 files / 95,403,203 bytes / 385 missions | Complete at frozen revision |
| Markdown → `DoclingDocument` → Markdown round-trip | 39 unique inputs × 3 repetitions | Complete; lifecycle, fusion, invalidation, rollback, and graph-query behavior `UNKNOWN` |
| Operations | Clean Python 3.11 environment; five import/version trials | Complete for bounded macOS footprint |
| Privacy | Normal, exception, and SIGTERM launch attempts under sandbox | Containment compatibility `FAIL`; conversion/egress/residue/cleanup behavior `UNKNOWN` because candidate never started |
| Semantic extraction | Approved pinned local generative backend | `UNKNOWN`: unavailable; no remote egress and no post-hoc download |
| User utility | Production user study | `UNKNOWN`: not performed |
| Cross-platform | Linux and Windows execution | `UNKNOWN`: not performed |

## Integrity notes

- Exploratory inputs were excluded from confirmatory selection.
- Publication-safe normalized outputs are hash-bound to commands, environments, and the sealed inputs by per-probe execution manifests. Pre-normalization hashes and replacement categories are retained in `redaction-manifest.json`. No canonical user artifact was converted in place.
- Structural failures support loss findings. Structural count equality is never treated as proof of semantic or lossless fidelity.
- Privacy failure means the preregistered containment contract was not runnable. Empty residue is non-evidence; no leakage or cleanup claim follows.
- B0/B1 outputs replay sealed annotations and are not baseline performance evidence. The sealed v1 B2/C5a API cannot support a fair blinded implementation, so material utility remains `UNKNOWN`.
- The research mission contract checks a root `source-register.csv` while its own instructions designate `research/source-register.csv`. The root file is a byte-identical compatibility projection; the nested file remains the authored register and equality is gate-verified.
