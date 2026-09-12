# Issue matrix — doctrine-delivery-activation-01KYQVQK

Per FR-037 of the spec-kitty-mission-review skill Gate-4. One row per issue referenced in spec.md.

| Issue | Title | Verdict | Evidence ref |
|-------|-------|---------|--------------|
| #3070 | Delivery-rail forward API + A–E `suggests` edge families (parent slice) | verified-already-fixed | Parent slice MERGED to upstream/main before this fast-follow; this mission builds on the topology it authored |
| #3077 | Coverage tail for #3070 | verified-already-fixed | Coverage tail MERGED with the parent slice; no further work here |
| #3063 | A–E `suggests` edge families authored inert; profile channel must deliver them | fixed | Core vector: WP01 `PROFILE_CHANNEL_RELATIONS += SUGGESTS` + `when`-link delivery (`ac23cf97d`); companions/reconcile via WP02/WP03 before `done` |
| #3075 | Route + register DRGGraph emit sites + writer-discovery gate + Protocol typing (FR-010) | fixed | Writer half WP05 (`18d37c892`); Protocol-typing half WP04; both must land, then closes at merge (with #2977) |
| #3062 | Structured `DRGGraphSchemaError` UX + asset source-path fix (FR-011) | fixed | WP06 (`fe2c7dcfa`/`7d94c3c9b`/`1b2a2a42d`): both halves + twin verified; closes at merge |
| #2532 | Extract inline `context.py` helpers into `context_renderers/` (FR-012) | deferred-with-followup | WP04 extracts a slice (reference-pointer + delivery-table helpers); full de-god of the 3528-line module remains — follow-up tracked by #2532 (Refs, not Closes) |
| #3064 | Empty-charter/`default-charter.yml` asset, DIRECTIVE_044 always-on | deferred-with-followup | Out of scope per spec C-006 (separate mission); follow-up tracked by #3064 itself |

Valid `Verdict` values: `fixed`, `verified-already-fixed`, `deferred-with-followup`, `in-mission` (being fixed by a later WP in this mission; must reach a terminal verdict before mission `done`).
