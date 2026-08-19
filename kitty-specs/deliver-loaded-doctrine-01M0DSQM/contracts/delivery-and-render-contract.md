# Contract — Action-Bundle Delivery Table & Render (WP-A)

## C-A1 Delivery-table totality with stated reasons
- Every `NodeKind` member has exactly one `_KindDelivery(slot, gate)` row in `_ACTION_BUNDLE_DELIVERY_BY_KIND`.
- Every row with `slot is None` carries a stated reason (inline comment naming why it is not delivered).
- After this mission: `GLOSSARY_PACK.slot == "glossary_packs"` (gate `ACTIVATED`); `ANTI_PATTERN.slot is None` **with** a stated reason. Zero `None` rows lack a reason.
- Guard: `tests/charter/test_action_bundle_delivery.py`, `tests/doctrine/drg/test_kind_mapping_totality.py` redden on any omission.

## C-A2 Glossary delivery + render (names-only + pointer)
- A glossary pack whose URN reaches `_classify_artifact_urns` is bucketed into the `"glossary_packs"` slot and surfaced as `_ActionDoctrineBundle.glossary_pack_ids`.
- The render emits, per delivered pack: the pack id/heading, its term **surfaces** (names) as a surface list, and a `--include glossary-pack:<id>` fetch pointer.
- The render MUST NOT inline any term `definition` (NFR-001). A pack with N terms adds ≈N short surface strings, never N definitions.
- Empty/absent glossary delivery → no glossary block (byte-identical to today).

## C-A3 Step description renders
- For a `ProcedureStep`/`TacticStep` with non-empty `description`, every render path (action-doctrine bundle body via `artifact_bodies`; profile-channel inline body via `profile_sections.format_inline_named_body`) emits the `description` in addition to the required `title`.
- `description` empty/whitespace/absent → title-only output byte-identical to pre-mission.

## C-A4 Styleguide/toolguide pointer-only ratified
- `render_profile_styleguides` / `render_profile_toolguides` keep `body_fn=None` (fetch stanza only).
- The pointer-only choice is documented as intentional (stated reason on the renderer + schema/doc note), not an unlabeled no-op. No runtime/behaviour change.
