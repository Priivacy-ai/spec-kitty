# Contract — DRG Writer-Registry Unification + Discovery Gate

**Owning concern**: IC-06 · **Requirements**: FR-010, NFR-005/006 · **Closes**: #3075, #2977 (iff all land).

## C1 — Single canonical document serializer

Every `src/` site that serializes a `DRGGraph` to a document dict (the five top-level keys
`schema_version`, `generated_at`, `generated_by`, `nodes`, `edges`) MUST delegate to
`graph_document_to_dict` (`src/doctrine/drg/migration/extractor.py:1424`). The three known sites MUST be
converted:
- `src/specify_cli/migration/rewrite_opposed_by.py:_write_graph` (#2977)
- `src/charter/activation/synthesizer/project_drg.py:_serialize_graph`
- `src/specify_cli/doctrine/pack_assembler.py` prune (~495-501) — currently bypasses the mapping funnel via
  raw `.model_dump()`, so it also MUST route node/edge dicts through `model_to_graph_dict` to restore
  `FIELDS_WITHHELD_FROM_GRAPH_OUTPUT` + omit-when-empty discipline.

## C2 — Registry membership

Each converted site is registered as a `DocumentWriter` member (`src/specify_cli/drg_writers/registry.py`)
so the existing member-iterating completeness test (`test_registry_completeness.py:199-220`) covers it.

## C3 — Discovery gate (non-vacuous, BOTH shapes)

A NEW gate MUST scan `src/` for graph-document emitters in BOTH shapes — (i) dict literals carrying
`schema_version`+`nodes`+`edges`, and (ii) `DRGGraph`→dict/YAML dumps via raw `.model_dump()` (the
`pack_assembler` shape) — and assert each callsite delegates to `graph_document_to_dict` and/or is a
registry member. The gate MUST be **non-vacuous**: the self-mutation **battery** injects an unregistered
**dict-literal** writer AND an unregistered **`.model_dump()`-shaped** writer, each proven to red
INDEPENDENTLY (a single dict-literal mutation leaves clause (ii) — the shape that motivated the gate —
unproven; memory: gate-unmask can't self-validate; prove the gate PARSES its authority, not literal-vs-
literal). **Bounded claim:** the gate closes the known literal + `.model_dump()` shapes + regressions of
them; graph-document construction via merge/comprehension/`**spread` remains uncovered → residual note.

## C4 — Protocol typing (fold-in)

Replace the `object`-typed repository surfaces (`progressive_disclosure.py:216`; `context.py:552,568,1520,
2526,2757,3375,3515-3518`) with an `ArtifactRepository` Protocol (`get(id)->T|None`,
`get_provenance(id)->str|None`) that the concrete repos already structurally satisfy via
`BaseDoctrineRepository`. The 12 `# type: ignore[attr-defined]` suppressions MUST be REMOVED (NFR-005 —
net-removal, no new suppressions), `mypy --strict` green.

## C5 — Closure

Close #3075 AND #2977 only if C1+C2+C3+C4 all land (C-007). Otherwise leave both open with a residual note
naming what remains.

## Acceptance (ATDD)

- **A1**: adding a hypothetical new top-level `DRGGraph` field, all three sites emit it (RED before C1).
- **A2**: the discovery-gate self-mutation **battery** reds independently for (a) an injected unregistered
  **dict-literal** writer and (b) an injected unregistered **`.model_dump()`-shaped** writer; each greens
  when it delegates to `graph_document_to_dict` (NFR-006, both clauses proven).
- **A3**: `mypy --strict` passes with the 12 `# type: ignore[attr-defined]` removed (NFR-005).
