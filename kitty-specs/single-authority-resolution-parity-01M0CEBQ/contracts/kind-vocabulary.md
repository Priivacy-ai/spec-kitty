# Contract — Derived Charter-Activatable Kind Vocabulary

**Home**: `src/doctrine/artifact_kinds.py` (beside `PROJECT_KIND_DIRS`) or a doctrine sibling
**Consumers**: `charter.activations`, `charter._activation_render`, `charter.context_renderers.template_include`
**Governs**: FR-004, FR-005, FR-006, C-003

## Public surface
```python
CHARTER_ACTIVATABLE_KINDS: frozenset[ArtifactKind]           # ArtifactKind − {TEMPLATE, ASSET} = 10 (incl ANTI_PATTERN)
CHARTER_ACTIVATABLE_SINGULAR_TO_PLURAL: dict[str, str]       # {k.value: k.plural}
CHARTER_ACTIVATABLE_PLURAL_TO_SINGULAR: dict[str, str]       # inverse
```

Derived (not restated): `CHARTER_ACTIVATABLE_KINDS = frozenset(ArtifactKind) - {ArtifactKind.TEMPLATE, ArtifactKind.ASSET}`. **Distinct** from `_NON_AUGMENTATION_ELIGIBLE_KINDS` (`{TEMPLATE, ASSET, ANTI_PATTERN}`) and from `CHARTER_KIND_TOKENS` (9 kinds) — both drop `anti_pattern`, which C-003/FR-005 keep.

## Collapse map (spec-named hand copies → derived)
| Site | Old | New | Behavior |
|------|-----|-----|----------|
| `activations._SINGULAR_TO_PLURAL_KIND` | 10-kind literal | `CHARTER_ACTIVATABLE_SINGULAR_TO_PLURAL` | **preserving** — current literal already == the derived 10 |
| `activations._PLURAL_TO_SINGULAR_KIND` | inverse comprehension | `CHARTER_ACTIVATABLE_PLURAL_TO_SINGULAR` | preserving |
| `_activation_render._singular_kind` inverse | 8-kind literal (DRIFTED) | `CHARTER_ACTIVATABLE_PLURAL_TO_SINGULAR` | **fixes drift** — gains `glossary_pack`, `anti_pattern` |
| `_activation_render._KIND_TO_PROPERTY` | 8-kind literal (DRIFTED) | derived `{plural: plural}` over activatable plurals | **fixes drift** — gains `glossary_packs` (real repo), `anti_patterns` (inert) |

### Non-goal (documented, out of scope)
`activations._ALLOWED_KINDS` is **not** collapsed. It is (a) a `frozenset`, not a plural↔singular **map** — the spec's duplicator list names only the maps above and `project_drg._KIND_TO_NODE_KIND`; (b) an 11-kind *validation* set (includes `templates`/`assets`, excludes `anti_patterns`) whose membership differs from the charter-activatable 10 on purpose, and whose sibling `charter.pack_context` mirror would ripple if changed; (c) outside the totality gate's dict scan regardless. Because `_SINGULAR_TO_PLURAL_KIND`'s membership is unchanged by the collapse, `normalize_artifact_kind` → `_ALLOWED_KINDS` validation is **byte-for-byte unchanged**. Reconciling `_ALLOWED_KINDS` is a candidate follow-up, not this mission (avoids C-004-style scope creep).

## Invariants (gate-enforced)
- **V1 round-trip**: `plural_to_singular[singular_to_plural[s]] == s` for all 10.
- **V2 (C-003)**: `ANTI_PATTERN ∈`; `TEMPLATE, ASSET ∉`. Exactly 10 kinds.
- **V3 (FR-004)**: no charter module declares a local plural↔singular kind dict; all import the authority. Enforced by the extended totality gate's string-keyed coverage.

## Behavioral consequences (the drift bug being fixed)
- `_singular_kind("glossary_packs")` → `"glossary_pack"` (was: `"glossary_packs"` — wrong selector token).
- `_infer_kind` scans `service.glossary_packs` (was: skipped — blind).
- `anti_patterns` present in property map is **inert-safe**: `_infer_kind` does `getattr(service, "anti_patterns", None)` → `None` → skip (no anti-pattern service repo). No crash.

## FR-006 selector recognition
`_render_doctrine_artifact_include.renderers` gains `glossary_pack` (renders via `service.glossary_packs`). `anti_pattern` is **recognized** (resolves to standard not-found), never "Unsupported --include selector kind". Every `CHARTER_ACTIVATABLE_KINDS` member is a recognized selector kind (S1).
