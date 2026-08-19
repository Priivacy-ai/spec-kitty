# Data Model & Seam→Home Map — Deliver Loaded Doctrine to the Agent (M4)

This mission changes render/delivery seams and one builder parameter; it does **not** change any doctrine domain model. The "entities" below are the delivery/render data structures and where each change lands.

## Entities (existing shapes — mostly unchanged)

### GlossaryPack / GlossaryTerm (unchanged)
- `GlossaryPack(id: str, provenance: str, terms: list[GlossaryTerm], description: str | None)`
- `GlossaryTerm(surface: str, definition: str, confidence: float, status: str, …)`
- **Render use (WP-A)**: the term-name surface list is `[t.surface for t in pack.terms]`; full definitions are **not** inlined — a `--include glossary-pack:<id>` fetch pointer covers them.

### ProcedureStep / TacticStep (unchanged shape, changed render)
- `ProcedureStep(title: str, description: str | None = None, …)` — `title` required, `description` optional.
- `TacticStep(title: str, description: str | None = None, …)`.
- **Render use (WP-A)**: today only `title` renders (`getattr(step, "title", …)` / `title or description`), so a present `description` is dropped. New render: emit the description as an additional sub-line when non-empty; byte-identical when absent.

### `_KindDelivery` delivery-table row (WP-A grows one row + closes the reason class)
- `_KindDelivery(slot: str | None, gate: _Gate)`; total over `NodeKind`.
- `GLOSSARY_PACK`: `None → "glossary_packs"`, gate stays `ACTIVATED`.
- `ANTI_PATTERN`: stays `None` but gains a stated-reason comment (the twin — closes the missing-reason class so no `None` row is unexplained).
- **Invariant (NFR-003)**: every `NodeKind` row present; every `slot=None` row carries a stated reason. `_empty_slot_map()` auto-derives an accumulator for the new `"glossary_packs"` slot.

### `_ActionDoctrineBundle` (WP-A adds one field)
- Existing: `directive_ids, tactic_ids, styleguide_ids, toolguide_ids, procedure_ids, asset_ids, service, …`.
- **Add**: `glossary_pack_ids: list[str]`, populated from `ids_by_slot.get("glossary_packs", ())` in `_load_action_doctrine_bundle`.

### `_ActionRenderRow` / `_ACTION_RENDER_ROWS` (WP-A adds glossary render)
- Generic rows carry `(heading, ids_attr, service_attr, title_attr, summary_attr, progressive_kind)`.
- Glossary needs a term-list body the generic `title_attr/summary_attr` cannot express → a dedicated glossary render branch/helper (`Terms: <surface>, …` names-only + fetch stanza), wired so `_render_action_doctrine_lines` emits it after the existing rows.

### Context JSON payload (WP-C promotes one array)
- `_ARRAY_BY_KIND`: add `"procedure": "procedures"` (was 4 kinds → 5).
- `context.py` payload build: move `procedure` from `extra_delivered` into `repos_by_kind`; `asset` stays in `extra_delivered` (reference-only).
- `context_contract.py`: `CONTEXT_SCHEMA_VERSION "1.0.0" → "1.1.0"`; add `"procedures"` to `CONTEXT_CONTRACT_TOP_LEVEL_KEYS`.
- **Invariant (C-005/NFR-003)**: version bump + ledger update land in the same change as the array promotion; the ledger totality guard reddens on any undeclared key.

### Doctrine-service builder overlay param (WP-B threads one param)
- `_build_doctrine_service(repo_root, *, org_roots=None, agent_profile_overlay_dir: Path | None = None)`.
- `_build_activation_aware_doctrine_service(repo_root, *, org_roots=None, agent_profile_overlay_dir=None)`.
- `build_activation_aware_doctrine_service(repo_root, *, agent_profile_overlay_dir=None)` (public — thin delegate).
- `doctrine.service.DoctrineService.__init__(..., agent_profile_overlay_dir: Path | None = None)`; `agent_profiles` property uses the override when set, else `self._project_dir("agent_profiles")`.
- **Invariant (NFR-002)**: unset → byte-identical kwargs/behaviour. **Invariant (C-006)**: only `_build_activation_aware_doctrine_service` constructs the wrapper; always wraps.

## Seam → Home map (file ownership by WP)

| Seam | File | WP | Change |
|------|------|----|--------|
| Delivery table row + reason class | `src/charter/context_renderers/delivery_table.py` | A | GLOSSARY_PACK → `"glossary_packs"` slot; ANTI_PATTERN stated reason |
| Action-bundle field | `src/charter/action_doctrine_bundle.py` | A | add `glossary_pack_ids`, populate from slot map |
| Glossary + step render | `src/charter/context_renderers/bootstrap_text.py`, `artifact_bodies.py` | A | glossary render row/helper; render step `description` |
| Profile inline step body | `src/charter/context_renderers/profile_sections.py` | A | render step `description`; document styleguide/toolguide pointer-only |
| Builder overlay param | `src/charter/doctrine_service_builder.py` | B | thread `agent_profile_overlay_dir` |
| Service overlay honour | `src/doctrine/service.py` | B | `agent_profiles` honours override |
| Projection migration | `src/specify_cli/tool_surface/profiles/projection.py` | B | build via factory + overlay; delete carve-out |
| Typed array map | `src/charter/progressive_disclosure.py` | C | `_ARRAY_BY_KIND["procedure"]` |
| Payload build | `src/charter/context.py` | C | procedure → `repos_by_kind` |
| Versioned contract | `src/charter/context_contract.py` | C | schema bump + ledger key |

No shared file appears in two WP rows → the three WPs are file-disjoint and parallel-safe.

## Guards (totality / parity — must stay green or redden intentionally)

- `tests/charter/test_action_bundle_delivery.py` — delivery-table slot/gate totality (WP-A extends).
- `tests/doctrine/drg/test_kind_mapping_totality.py`, `test_unknown_kind_fails_loudly.py` — NodeKind-keyed totality (WP-A: glossary row).
- `tests/charter/test_context_parity.py` — top-level JSON key ledger (WP-C: `procedures`).
- `tests/specify_cli/tool_surface/profiles/{test_projection,test_projection_collision_precedence,test_projection_org_visibility}.py` — the three carved-out project-overlay tests (WP-B un-carves).
