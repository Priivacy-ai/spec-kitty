# Contract — Name↔URN Template Resolution (two lanes)

**Requirement**: FR-010, C-004. The filesystem↔URN duality is a **compatibility contract**, not one seam.

## Lane 1 — resolve-by-name (unchanged, the creation path)
`resolve_configured_template(artifact_kind)` → `template_set[artifact_kind]` → **filename** → `resolve_template(name)` → 5-tier filesystem precedence (`.kittify/overrides/templates/` > legacy > global-mission > global > package). The `template_file` filename is the override key.

## Lane 2 — resolve-by-URN (new, graph-addressed)
`template_catalog.resolve_template_by_id("template:<mission>/<name>")` → splits `<mission>/<name>` → delegates to the **same** Stage-2 `resolve_template`. Uses the mission-qualified URN form.

## Invariants
- **Equivalence**: for an authored template, by-URN and by-name resolve to the same file (US3.2).
- **Override-wins on both lanes**: a `.kittify/overrides/templates/<file>` override wins for the URN lane too (US3.3) — because both terminate in the same 5-tier `resolve_template`.
- **Do NOT collapse**: the two lanes key on different identities (semantic `artifact_kind` vs mission-qualified URN); collapsing turns the name-keyed override chain into dead code.
- **Scope bound (FR-010)**: add the lane + equivalence test only; do NOT re-wire the name-based creation path.
- **Fence (C-002)**: the new URN code must never reference the scalar `template_set` surfaces (`resolution.template_set`, `MissionTypeProfile.template_set`, `doctrine.template_set`).
