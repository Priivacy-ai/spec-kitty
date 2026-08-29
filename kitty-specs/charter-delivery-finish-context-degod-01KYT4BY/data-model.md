# Data Model & Structural Map

**Phase 1 output.** This mission is code-structural, not schema-bearing — the "entities" are runtime decision types, invariants, and the `context.py` seam→home map.

## Entities / value objects

### Empty-charter predicate (US1)
- **Composite boolean** over ALL charter-activatable dimensions. Inputs: `charter_activated_urns(repo_root)` (6 URN kinds) and `PackContext.from_config(repo_root)` fields `activated_agent_profiles`, `activated_mission_step_contracts`, `activated_glossary_packs` (each `frozenset|None`) + `org_roots`.
- **Invariant**: `is_empty ⇔ (urns == ∅) AND (activated_agent_profiles is None) AND (activated_mission_step_contracts is None) AND (activated_glossary_packs is None) AND (org_roots == ())`. Any activation on any dimension (even `[]`) or any org pack ⇒ not empty. `anti_pattern` is excluded (not charter-activatable).

### Empty-charter governance scoping (US1 / FR-010)
- On the `empty_charter_fallback` path, the dispatch governance block must suppress the project resolver-directive merge (`render_compact_view` otherwise merges `resolve_project_governance` directives, which catalog-fall-back to the full built-in `DIR-###` canon under an empty charter). **Invariant**: generic-agent dispatch `Directive IDs:` block is empty or exactly generic-agent's own cited directives — never the built-in canon.

### Generic-agent routing target (US1)
- Constant `GENERIC_AGENT_ID = "generic-agent"` — a shipped built-in profile (`src/doctrine/agent_profiles/built-in/generic-agent.agent.yaml`), resolved through the **ungated** built-in repo.
- **Invariant**: pinned only on the *no-profile-hint auto-route* path; the *action* is still derived from the request verb (CANONICAL_VERB_MAP). Explicit `--profile <x>` bypasses the fallback entirely.

### `RouterDecision` extension (US1)
- Existing `RouterDecision` (`invocation/router.py:161`) gains a new `confidence` Literal value `"generic_fallback"` (typed, mypy-strict clean). No structural field added to the router.

### `InvocationPayload.empty_charter_fallback` (US1)
- New `bool` slot on `InvocationPayload` (`executor.py:139-163`), serialized in `to_dict`. Drives the one-shot warning and the `--json` signal. **Footgun**: `__init__(**kwargs)` only sets provided keys and `to_dict` does `getattr(self, s, None)` — so thread `empty_charter_fallback=` at the single construction site always, and read via `getattr(payload, "empty_charter_fallback", False)` in `dispatch.py` (else legacy payloads emit `null`/`AttributeError`).

### Charter scaffold asset (US1)
- `AssetManifest` (`doctrine/assets/models.py`, frozen/extra-forbid): `id: common-charter-scaffold-minimal` (NOT "default-charter" — avoids collision with `charter/packs/default.yaml`), `mime: application/yaml`, `path: built-in/charter_scaffold_minimal.yml`, `title`. Resolve/copy-only; cross-reference comment to `packs/default.yaml` in both files.

### Fetch-stanza when-clause (US2)
- The normalized clause embedded at `fetch_stanza.py:133`. **Invariant**: for every rendered stanza, the line is grammatical AND matches `_WHEN_DOING_RE` (closed 6-verb set) AND `_FETCH_CMD_RE`.

## `context.py` seam → home map (US3)

Home key: `CR/<m>` = `src/charter/context_renderers/<m>.py`; `ch/<m>` = `src/charter/<m>.py`; **STAY** = orchestration surface. `(existing)` = consolidate into a module that already exists; `(new)` = new sibling.

| Seam cluster | Home | New/existing | Render? | Notes |
|---|---|---|---|---|
| Public orchestrators (`build_charter_context`, `_include`, `_json`, `CharterContextResult`, `BOOTSTRAP_ACTIONS`) | **STAY** | — | y | thin after delegation; ≤500 LOC ceiling |
| Catalog diagnosis (`_diagnose_catalog_miss`, `_available_catalog_ids`) | `CR/catalog_diagnosis.py` | new (leaf) | n | **cycle symbol**; deps `charter.activation._catalog_miss` only |
| Token budget (`_enforce_token_budget`, `_budget_estimate`, `_PROFILE_INLINE_BODY_LIMIT_CHARS`) | `CR/token_budget.py` | existing | y/n | **cycle symbols**; consolidate |
| Fetch stanza (`_render_fetch_stanza`) | `CR/fetch_stanza.py` | existing | y | **cycle symbol**; fold thin wrapper; US2 fix lands here |
| Artifact-body formatting (9× `_format_inline_*`, `_format_full_artifact_payload_body`, `_format_profile_directive_code`, `_jsonable_artifact_value`) | `CR/artifact_bodies.py` | new | y/n | pure transforms |
| charter.md parsing (`_extract_policy_summary`, `_find_section_start`) | `ch/charter_md_parsing.py` | new | n | pure |
| Reference loading (`_load_references`) | `CR/reference_pointers.py` | existing | n | consolidate |
| Context state (`_ContextStateBundle`, `_load_state`, `_write_state`, `_mark_action_loaded`, `_prepare_context_state`) | `ch/context_state.py` | new | n | local file I/O |
| Template include (6× `_render_*_include`, `_default_missions_root`) | `CR/template_include.py` | new | y | backs `_include` orchestrator |
| Selection rendering (11× `_render_selected_*`, `_render_selection_block`, `_SELECTED_*_HEADER`, `_provenance_suffix`, `_extend_named_artifact_lines`, source-map) | `CR/selection_block.py` | new | y | large render-pure |
| Activation (`_load/_read/_union_activations`, `_render_activation_block`) | `CR/activation_block.py` | new | y/n | cohesive around ActivationEntry |
| Compact governance (`_render_compact_governance`, `_compact_section_block`, `_render_compact_from_bundle`) | `CR/compact_governance.py` | new | y | dispatch governance path |
| Bootstrap assembly (`_render_bootstrap_text`, `_render_action_doctrine_lines`, headers, `_ActionRenderRow`) | `CR/bootstrap_text.py` | new | y | |
| JSON builder (`build_charter_context_json` privates, `_DirectiveLike`, `_project_*`) | `ch/context_json.py` | new | n | |
| Org-pack discovery (`_enumerate_org_pack_paths`, `_load_doctrine_selection`, …) | `ch/org_pack_discovery.py` | new | n | service-touching |
| Action-doctrine bundle (`_load_action_doctrine_bundle`, `_resolve_action_bundle`, `_ActionDoctrineBundle`) | `ch/action_doctrine_bundle.py` | new | n | service glue |
| Profile-cited render (`_render_profile_directives/_tactics/_sections`, header tpls) | `CR/profile_sections.py` | existing | y | consolidate (render half) |
| **Profile resolution + caches** (`_default_agent_profile_repository`, `_reset_agent_profile_cache`, `_activation_aware_profile_map`, `_resolve_agent_profile_record`, `_load_agent_profile`, module globals) | `ch/profile_resolution.py` | new | n | **LAST**; FR-009 anchor |
| **Doctrine-service builder** (`_build_doctrine_service`, `_build_activation_aware_doctrine_service`) | `ch/doctrine_service_builder.py` | new | n | **LAST**; US1-frozen region (~L1550-1566) |

**Seam refinements vs the spec's 12 candidates**: "token budget" and "reference loading" are *consolidations* (existing homes), not new seams; "profile resolution" **splits** into render (`profile_sections`) + resolution/caches (`profile_resolution`); "doctrine-service builder" is broken out as its own US1-frozen seam.

## Invariants preserved across the mission

1. **Output parity** — `build_charter_context` / `_include` / `_json` byte-identical on the non-trivial corpus (token-budget substitution + catalog-miss + first-load inputs).
2. **Layer rule** — no `specify_cli` import anywhere under `src/charter/`.
3. **`__all__`** — every `src/charter/` module (incl. new seams) declares `__all__`; every export has a caller.
4. **Import acyclicity** — the `profile_sections` cycle is dissolved, no new cycle introduced.
5. **FR-009 surface** — every private symbol imported from `charter.activation.context` by tests stays importable (re-export shim).
