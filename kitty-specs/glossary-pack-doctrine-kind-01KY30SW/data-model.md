# Data Model: Glossary Pack Doctrine Kind (Mission A)

> **Naming (squad M4):** plural == dir == accessor == `glossary_packs`. Package
> `src/doctrine/glossary_packs/`, accessor `DoctrineService.glossary_packs`, built-in dir
> `glossary_packs/built-in/` (hyphen), activation key `activated_glossary_packs`. The enum
> **value** (and URN prefix) is singular `glossary_pack`.

## Aggregate: GlossaryPack

The aggregate root. Distributed as one `*.glossary-pack.yaml` file; loaded by
`GlossaryPackRepository`; addressable as a DRG node.

| Field | Type | Notes |
|-------|------|-------|
| `id` | str (slug) | Pack identity, e.g. `spec-kitty-core`. Unique within provenance tier. |
| `provenance` | enum | `built-in` \| `org` \| `project` (Mission A ships `built-in` only). |
| `terms` | list[GlossaryTerm] | Non-empty; term `surface` values unique within the pack. |
| `description` | str? | Optional human description. |

- **DRG node**: `NodeKind.GLOSSARY_PACK`, URN `glossary_pack:<id>` (underscore — invariant).
- **Activation**: recorded per-id in `PackContext.activated_glossary_packs`; the built-in
  `spec-kitty-core` pack is activated by default (see default-on mechanism below).
- **Invariant**: a pack with any invalid term is invalid as a whole (doctor reports it unhealthy).

## Entity: GlossaryTerm

Carries **every field the seed carries** so migration is provably zero-loss (squad CRITICAL — the
seed has `see_also`/`introduced_in_mission`/`synonyms_to_avoid` beyond the obvious four).

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `surface` | str | yes | Canonical term surface, e.g. `work package`. Unique within pack. |
| `definition` | str | yes | Canonical definition. |
| `confidence` | **float** | yes | Seed values are floats (0.6/0.75/0.9/0.95/1.0). NOT enum/str. |
| `status` | str | yes | Migrated from seed. |
| `see_also` | list[str] \| None | no | Present on ≥1 seed term. Default `None`. |
| `introduced_in_mission` | str \| None | no | Present on ≥2 seed terms. Default `None`. |
| `synonyms_to_avoid` | list[str] \| None | no | Populated on 3 seed terms. Default `None`. Carried; unwired in A. |
| `aliases` | list[str] \| None | no | **New for Mission B**, present + round-trips in A. Default `None`. |
| `banned_synonyms` | list[str] \| None | no | **New for Mission B**, present + round-trips in A. Default `None`. |

- **Validation**: `surface`, `definition`, `confidence`, `status` required; duplicate `surface`
  within a pack → load error (needs a synthetic fixture — the real seed has no dups).
- **Optional-list default**: `None` (matches the runtime `TermSense` model), not `[]`. Tested.
- **Forward-compat (C-004)**: `aliases`/`banned_synonyms` round-trip unchanged so Mission B needs no
  schema revision. No gate consumes any enforcement field in Mission A.

## Enum extension: ArtifactKind.GLOSSARY_PACK

- New member `GLOSSARY_PACK = "glossary_pack"`; `_PLURALS["glossary_pack"] = "glossary_packs"`;
  `_PATTERNS` entry.
- **MUST NOT** be in `_NON_AUGMENTATION_ELIGIBLE_KINDS` (`{template, asset}`) — it is
  charter-activatable (C-001). Operator token `glossary-pack` (hyphen) → `glossary_pack` via
  `from_operator_token` (enum-derived — free). `CHARTER_KIND_TOKENS` + `YAML_KEY_MAP` derive.

## DRG node kind: NodeKind.GLOSSARY_PACK

- New `NodeKind.GLOSSARY_PACK = "glossary_pack"`; comment-fenced away from the retiring runtime
  `GLOSSARY`/`GLOSSARY_SCOPE` term nodes (Mission C deletes those, keeps this).
- URN `glossary_pack:<id>`; the URN regex + `prefix == kind.value` assertion reject the hyphenated
  form (NFR-001).

## Activation ledger field: activated_glossary_packs

- New field + `_read_activated_glossary_packs` reader on `PackContext`, wired into
  `from_config`/`from_activation`. Lists activated pack ids. The `test_packcontext_has_all_ten_
  activated_fields` count test goes 10 → 11.

## Default-on mechanism (named — squad F2)

Active-by-default rides three things together, NOT a `config.yaml` entry or a DRG edge:
1. the **three-state `None` default** for `activated_kinds`,
2. **`_BUILTIN_ARTIFACT_KINDS` membership** (`"glossary_packs"`), and
3. the **root graph fragment** `src/doctrine/glossary_pack.graph.yaml`.

The lockstep drift-guard must be **extended to bind `_BUILTIN_ARTIFACT_KINDS`** (today it binds only
`_ALLOWED_KINDS ↔ _ORG_DRG_CANONICAL_KINDS`); otherwise omitting the built-in list silently disables
default-on with a green suite.

## The three (four) per-kind maps to update in lockstep

| Surface | File | Key form |
|---------|------|----------|
| `_ALLOWED_KINDS` | `src/charter/activations.py` | plural `"glossary_packs"` |
| `_BUILTIN_ARTIFACT_KINDS` | `src/charter/pack_context.py` | plural `"glossary_packs"` (default-on) |
| `_ORG_DRG_KIND_ALIASES` → `_ORG_DRG_CANONICAL_KINDS` | `src/doctrine/drg/org_pack_loader.py` | alias dict, plural |
| `_SINGULAR_TO_PLURAL_KIND` | `src/charter/activations.py` | `{"glossary_pack":"glossary_packs"}` |
| `_CLI_KIND_TO_DRG_SINGULAR` | `src/charter/consistency_check.py` | `{"glossary-pack":"glossary_pack"}` |

## Relationships

```
ArtifactKind.GLOSSARY_PACK ──classifies──> GlossaryPack (aggregate)
GlossaryPack ──contains──> GlossaryTerm[* ]
GlossaryPack ──is──> DRG node (NodeKind.GLOSSARY_PACK, urn glossary_pack:<id>)
PackContext.activated_glossary_packs ──activates──> GlossaryPack (by id)
DoctrineService.glossary_packs ──loads──> GlossaryPack[* ]  (via GlossaryPackRepository)
```

## State / lifecycle

Packs are static doctrine assets — no runtime mutation. Lifecycle is load → (optionally) activate →
resolve as DRG node. No state machine. (Contrast: the retired runtime glossary had a dynamic
observe/extract/resolve pipeline — explicitly NOT reintroduced here.)
