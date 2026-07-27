# Research: Glossary Pack Doctrine Kind (Mission A)

Distilled from the pre-spec research squad (2026-07-21): `glossary-research/01-doctrine-glossary-kind.md`
and `glossary-research/00-consolidated-pre-spec-brief.md`. Grounding: ADR
`docs/adr/3.x/2026-07-21-1-glossary-first-order-doctrine-artefact.md`, issue #1418.

## Decision: `GLOSSARY_PACK` is a first-order, charter-activatable ArtifactKind

- **Decision**: Add `GLOSSARY_PACK` to `ArtifactKind` (`src/doctrine/artifact_kinds.py`) as an
  8th-universe charter-activatable kind, copying the `directive` kind's wiring. Keep it OUT of
  `_NON_AUGMENTATION_ELIGIBLE_KINDS` (`{template, asset}`).
- **Rationale**: #1418 designs the pack as activatable (per-ID via `PackContext.activated_glossary_packs`)
  and DRG-addressable. `directive` is the closest existing template (charter-activatable, glob-loaded
  from a package dir). `asset` is the wrong template — it is loose-contract, non-activatable, and its
  DRG node discards `path`/`mime`.
- **Alternatives considered**: (a) model it like `asset` — rejected, loses activation + resolution;
  (b) keep it a runtime-only seed — rejected, that is exactly the drift #1418/#2727 remove.

## Decision: URN is `glossary_pack:` (underscore), not `glossary-pack:`

- **Decision**: The DRG URN prefix is `glossary_pack` (underscore).
- **Rationale**: `src/doctrine/drg/models.py` (URN regex ~line 19 + the `prefix == kind.value`
  assertion ~lines 117-121) requires the URN prefix to equal the enum `.value`. #1418's prose writes
  the hyphenated `glossary-pack:` everywhere, which would fail that assertion. The hyphen is valid ONLY
  as the operator token (`from_operator_token`).
- **Alternatives considered**: hyphenated URN — rejected, breaks the DRG contract. Guarded by an
  explicit NFR-001 regression asserting hyphen-rejected / underscore-accepted.

## Decision: new `src/doctrine/glossaries/` package; repository inherits `BaseDoctrineRepository`

- **Decision**: A ~30-line `GlossaryPackRepository(BaseDoctrineRepository)` loads
  `*.glossary-pack.yaml` from `src/doctrine/glossaries/builtin/`, exposed as `DoctrineService.glossaries`.
- **Rationale**: `BaseDoctrineRepository` already provides glob loading, provenance, and node
  construction for the other kinds; the pack repo inherits nearly everything. Built-in assets live in
  the package (like other built-in doctrine), NOT under `.kittify/glossaries/` (the retiring seed home).
- **Alternatives considered**: reuse the runtime `glossary.store`/`scope` loaders — rejected, that
  couples the new kind to the dying runtime (C-002).

## Decision: three mirrored kind-lists move in lockstep

- **Decision**: Add `GLOSSARY_PACK` to `pack_context._BUILTIN_ARTIFACT_KINDS`,
  `activations._ALLOWED_KINDS`, and `org_pack_loader._ORG_DRG_CANONICAL_KINDS` together, and add the
  `activated_glossary_packs` field + reader.
- **Rationale**: A drift-guard forces these three lists to agree; touching one without the others fails
  the guard. This is the load-bearing architectural gate for the kind (DIRECTIVE_043 non-vacuity).
- **Alternatives considered**: none — the drift-guard is authoritative.

## Decision: charter activation/cascade is data-driven; only two `charter/drg.py` map entries needed

- **Decision**: Add the kind to the two maps in `src/charter/drg.py`; cascade/kind_vocabulary/
  `YAML_KEY_MAP` are derived and mostly free. The built-in pack is charter-activated by default
  (operator decision, 2026-07-21).
- **Rationale**: Research found the charter filter is already data-driven, so #1418's proposed
  hand-written `elif` per-kind branch is obsolete. Cascade is generic (follows DRG `requires`/`suggests`
  edges).
- **Alternatives considered**: per-kind special-casing — rejected as obsolete/anti-canonical.

## Decision: extractor must emit the node AND a `*.graph.yaml` fragment must ship (silent-invisibility guard)

- **Decision**: Add the kind to the extractor `_KIND_MAP` and ship
  `spec-kitty-core.graph.yaml`; add a non-vacuous "resolves as a loaded node" test.
- **Rationale**: `loader.py` (~lines 100-146) only surfaces packs to charter resolution if the extractor
  emits them and a graph fragment ships. Without the guard, a built-in pack loads from disk but is
  invisible to charter resolution — a silent failure. The guard must FAIL when emission or the fragment
  is removed (fakeable-failure pattern), not merely assert file presence.
- **Alternatives considered**: rely on load-from-disk only — rejected, silent-invisibility trap.

## What already exists vs greenfield

- **Exists (term half):** `NodeKind.GLOSSARY` / `GLOSSARY_SCOPE` runtime term-node stubs,
  `Relation.VOCABULARY`, the runtime `glossary:<hash>` DRG bridge (`src/doctrine/drg/models.py:45`,
  `src/doctrine/styleguides/models.py:46`). These are the runtime *term* nodes — NOT the *pack* kind.
- **Greenfield (pack half):** `ArtifactKind.GLOSSARY_PACK`, `NodeKind.GLOSSARY_PACK`,
  `src/doctrine/glossaries/`, the built-in pack, the graph fragment, the activation field — all new.

## Key file:line index (from lens 1)

| Surface | Anchor | Change |
|---------|--------|--------|
| `src/doctrine/artifact_kinds.py` | `ArtifactKind` (82-91), `_NON_AUGMENTATION_ELIGIBLE_KINDS` (178-190), `CHARTER_KIND_TOKENS` | add member/plural/glob; stay out of exclusion set |
| `src/doctrine/drg/models.py` | URN regex ~19, `prefix==kind.value` ~117-121, `NodeKind` ~45 | `NodeKind.GLOSSARY_PACK`; underscore URN |
| `src/doctrine/glossaries/` | — | NEW package (models, repository, builtin assets) |
| `src/doctrine/service.py` | `DoctrineService` | `.glossaries` accessor |
| `src/charter/pack_context.py` | `_BUILTIN_ARTIFACT_KINDS`, `activated_*` | add kind + `activated_glossary_packs` |
| `src/charter/activations.py` | `_ALLOWED_KINDS` | add kind |
| `src/charter/org_pack_loader.py` | `_ORG_DRG_CANONICAL_KINDS` | add kind |
| `src/charter/drg.py` | kind maps | two entries |
| `src/charter/kind_vocabulary.py` | `from_operator_token`, `YAML_KEY_MAP` | derived token |
| doctrine `loader.py` / extractor | `_KIND_MAP` ~100-146 | emit glossary-pack nodes |

## Open risks carried into design

1. **Ticket contradiction with #2727** — #1418 keeps runtime `src/glossary/` and seeds into it; this
   mission drops that ACL (C-002) and leaves the runtime for Mission C. Design must not couple to it.
2. **Silent-invisibility** — mitigated by the NFR-003 non-vacuous guard.
3. **Migration fidelity** — 104 terms must round-trip field-for-field (NFR-002); the seed stays the
   source of record for the casing gate until Mission B/C.
