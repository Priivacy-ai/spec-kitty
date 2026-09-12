# Contract — Graph Writer Registry

**Requirements**: FR-001, FR-002 · **Criteria**: SC-004, SC-009 · **Constraints**: C-001, C-006, C-010

**Revised 2026-07-28** after the post-plan squad proved the single-Protocol form unbuildable.

## Contract

Every site that persists `DRGNode` / `DRGEdge` / `DRGGraph` state is a **registry member**. The
completeness tests iterate the registry; they carry no hand-written list of writers.

The registry has **three shapes**, because the five members are three different kinds of thing.

```python
# Hosted in src/specify_cli/ — the top layer. See "Hosting" below.

class MappingWriter(Protocol):
    name: str
    def node_to_mapping(self, node: DRGNode) -> dict[str, object]: ...
    def edge_to_mapping(self, edge: DRGEdge) -> dict[str, object]: ...

class DocumentWriter(Protocol):
    name: str
    def document_to_mapping(self, graph: DRGGraph) -> dict[str, object]: ...

class ModelBridge(Protocol):
    name: str
    def bridge(self, fragment_edge: object, /, **ctx: object) -> DRGEdge | None: ...
```

| Member | Shape | Note |
|---|---|---|
| `extractor._node_to_dict` / `_edge_to_dict` | `MappingWriter` | The derived reference implementation |
| `rewrite_opposed_by._node_to_dict` / `_edge_to_dict` | `MappingWriter` | **Already guarded** — needs membership, not a new test |
| `project_drg._serialize_graph` | `MappingWriter` **after extraction** | Currently `(DRGGraph) -> str` with the dicts built inline in two loops. Extracting them into `_node_to_dict`/`_edge_to_dict` is a **prerequisite task**, not a registry join |
| `_dump_graph_document` | `DocumentWriter` | Owns the five document-level keys; delegates node/edge to the extractor pair. This is also what makes W-4 meaningful |
| `_bridge_org_edge_to_drg_edge` | `ModelBridge` | **Constructs** a `DRGEdge` from an org-fragment edge. Its input is not a `DRGEdge` and its output is not a mapping — its defect is model→model field coverage, not serialization |

### Obligations

| # | Obligation |
|---|---|
| W-1 | For every `MappingWriter` and a **fully-populated** instance: `set(w.edge_to_mapping(e)) == set(DRGEdge.model_fields) - _FIELDS_WITHHELD_FROM_GRAPH_OUTPUT`. Same for nodes. |
| W-1a | **Empty values are the hole W-1 alone does not close.** `_render_for_yaml` returns `None` for `None` *and for an empty list*, and `_model_to_dict` drops the key — so a novel `impacts: str \| None = None` or `impacts: list[str] = []` field is dropped by **both** derived writers today, while `is_symmetric: bool = False` survives. A separate obligation must state the empty-value rule (emit-with-empty, or a declared second withholding rule). Without it the gate is vacuous for exactly the field shape B1 is likely to add. |
| W-2 | For every `DocumentWriter`: emitted keys equal `set(DRGGraph.model_fields)` less any declared withholding. |
| W-3 | For every `ModelBridge`: every `DRGEdge` / `DRGNode` field the fragment schema can express is set on the minted model. |
| W-4 | `DRGGraph` declares `model_config = ConfigDict(extra="forbid")`, matching `DRGNode` and `DRGEdge`. **This is a consumer-facing read-path break** — an org-pack graph document with an unknown top-level key goes from silently-accepted to a hard load failure. It needs a typed error and a named diagnostic, and it should not ride the lane that lands first and alone. |
| W-5 | Failures name the **member** and the **missing field**, never a bare count mismatch. |

### Hosting

The registry lives in **`src/specify_cli/`**, the top layer.

A `Final[tuple[...]]` in `doctrine` naming charter and specify_cli members reds
`tests/architectural/test_layer_rules.py:282` and `:293`; `charter` reds `:311`. Only the top layer can
statically hold all five members.

`src/charter/drg.py` **already exists** (532 lines, 24-entry `__all__`) and
`rewrite_opposed_by.py:97` already imports `DRGEdge, DRGGraph, DRGNode, NodeKind, Relation` through
it. No facade is created; the derived helper is added to an existing export surface.

**Import-time self-registration is the wrong escape.** It makes membership depend on import order,
which re-opens the exact "a writer that never joins is invisible" gap this contract concedes below.

### Acceptance test shape (SC-004, SC-009)

The mutation is the **fixture**, not a manual edit (C-006). Verified buildable: `DRGNode`/`DRGEdge`
are **not frozen** (only `extra="forbid"`), attribute injection and extra kwargs are both rejected, so
**subclassing is the only route** — and `DRGGraph` does not re-validate or coerce, so a mutated
node/edge survives into a graph and reaches the document writer.

```python
def test_every_mapping_writer_preserves_an_unknown_field():
    edge = _EdgeWithNovelField(...)          # subclass; every field populated (W-1)
    for writer in MAPPING_WRITERS:
        emitted = set(writer.edge_to_mapping(edge))
        assert emitted == _expected_keys(), f"{writer.name} dropped {_expected_keys() - emitted}"
```

B1 extends this test rather than re-deriving it.

### Known gap, recorded

A writer that **never joins** the registry is invisible to it. The compensating control — an AST gate
failing on dict-literal construction whose keys are a subset of `model_fields`, outside the derived
helper — is deferred and **currently has no owner or issue number**, which the plan flags as needing a
home. Note that the repository already runs precisely this mechanism for kind maps
(`tests/doctrine/drg/test_kind_mapping_totality.py`) with an audited exemption list and tests proving
the exemption does real work — so the reason originally given for rejecting it is refuted by prior art
in this same repo.

### Non-obligations

- The registry does not change *when* writers run, or the shape of the files they produce beyond field
  completeness.
