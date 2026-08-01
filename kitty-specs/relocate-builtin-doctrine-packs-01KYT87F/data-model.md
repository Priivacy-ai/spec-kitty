# Data Model: Relocate Built-In Doctrine to packs/built-in (Phase 1)

This mission moves data and repoints resolution; the "entities" are the resolution/verification
constructs, not new domain objects.

## PackRoot (resolution)

- **tier**: `"built-in" | "org" | "project"` — the doctrine layer.
- **path**: absolute filesystem path to the tier's content root.
- **origin**: `env | editable | installed` — which D-1 branch resolved it (for diagnostics/tests).
- **Invariant**: `resolve_pack_root("built-in").is_relative_to(<packs>/built-in)`; never resolves
  inside `src/doctrine/` post-move (FR-009). Fail-closed: unresolved → `PackRootNotFound`, never a
  fallback tree.

## ContentInventoryEntry (FR-002 / occurrence_map.yaml)

- **path**: source tree/reader.
- **category**: one of the 8 bulk-edit categories.
- **action**: `MOVE | STAY | REPOINT | KEEP | UPDATE | ADD`.
- **to**: destination under `packs/built-in/` (MOVE only).
- **rationale**: why (esp. STAY: code-coupling / non-tiered).
- **Invariant**: every `files("doctrine*")` reader and every literal `src/doctrine/...` path has
  exactly one entry (0 unclassified — SC-004).

## GraphIdentityFixture (NFR-001) — full-model projection

- **nodes**: `sorted((node.urn, node.label, tuple(sorted(node.tags))) for node in graph.nodes)`.
- **edges**: `sorted((e.source, e.relation, e.target, e.when, e.reason) for e in graph.edges)`.
- **captured_at**: pre-move commit ref (baseline anchor), captured in IC-01 **before** the move.
- **Invariant**: post-move `nodes` and `edges` projections **equal** the fixture. Bare URN/triple sets
  are insufficient — `when` gates delivery and could be silently dropped by a regen while triples stay
  identical. Cardinality 324/892 is a derived smoke check only.

## OverlayPrecedenceCase (FR-008)

- Synthetic org + project fragments overriding a known built-in URN.
- **Assertions**: tier override wins `built-in < org < project`; `_tag_source` tags a moved built-in
  URN as `built-in` (origin tier, not the new path); no built-in edge dropped when an overlay adds
  edges on the same URN.

## PackagingArtifactManifest (NFR-002)

- **wheel_paths** / **sdist_paths**: relative paths under `packs/built-in/` in each built artifact.
- **Invariant**: each equals the pre-move file manifest (set-equality, not `≥`); clean-venv install
  imports + resolves built-in with 0 missing-file errors.
