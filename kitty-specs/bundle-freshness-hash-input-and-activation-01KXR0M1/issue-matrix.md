# Issue matrix — bundle-freshness-hash-input-and-activation-01KXR0M1

Per FR-037 of the spec-kitty-mission-review skill Gate-4. One row per issue referenced in spec.md.

| Issue | Title | Verdict | Evidence ref |
|-------|-------|---------|--------------|
| #2758 | synthesized_drg freshness: missing bundle file (references.yaml) → permanent-stale | fixed | `references.yaml` removed from `BUNDLE_CONTENT_HASH_FILES` (commit `42291c84b`); regression `test_computer.py::test_synthesized_drg_not_stale_when_references_yaml_missing` + `test_activation_freshness.py` US1 |
| #2759 | Freshness blind spot: activation not reflected in the bundle-content signal | fixed | directive-activation digest via shared `resolve_synthesis_graph_directives` (commits `3d22b8a2a`,`42291c84b`); collision-free JSON encoding (`5ef1bd8c8`); `test_activation_freshness.py` US2 (directive→stale; paradigm/tactic→fresh boundary) |
| #2732 | fix synthesized_drg stuck-stale via content-identity freshness | verified-already-fixed | base PR this mission is stacked on; extends (does not re-implement) its `bundle_content_hash` mechanism — swaps `references.yaml`→directive digest |
| #2577 | absent `activated_directives` → `[]` for the graph consumer | verified-already-fixed | the shared helper mirrors the #2577 rule exactly; `test_config_sourced_derivation.py` + `test_synthesize_path_parity.py` prove behavior-preservation |
| #2724 | #2721 S-C: template_set graph-back exemplars | deferred-with-followup | orthogonal epic slice (Stijn); this mission touches `activate`/`deactivate` not at all, so no collision. Sibling #2760 also deferred pending #2721 built-in-DRG cutover |

Valid `Verdict` values: `fixed`, `verified-already-fixed`, `deferred-with-followup`, `in-mission` (being fixed by a later WP in this mission; must reach a terminal verdict before mission `done`).
