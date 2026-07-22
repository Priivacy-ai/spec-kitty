# Contract: Activation gate (canonical-URN matching)

**Owner**: `charter/drg.py` — `_node_is_activated`, `filter_graph_by_activation`
**Requirements**: FR-001, FR-002, C-002, C-004, NFR-001, NFR-002

## Obligation

For a per-kind activation set `S` on `PackContext` (holding config **stems**), a graph node of
that kind with canonical id `A` survives the per-ID gate iff `A ∈ resolve_stems_to_canonical(S)`,
where resolution reuses `charter.kind_vocabulary.resolve_artifact_urn` with roots sourced from the
`PackContext`. The gate signature is unchanged.

## Behavioral cases

| `activated_<kind>` | Node canonical id | Expected |
|--------------------|-------------------|----------|
| `None` (default-allow) | any | **kept** (byte-identical to merge-base) |
| populated, stem resolves to this node's canonical id | matching | **kept** (RED on merge-base — the bug — GREEN after fix) |
| populated, does not include this node's canonical id | non-matching | **excluded** |
| populated with a raw canonical-id (not a stem) | — | **not a supported input** (require-canonical, C-002); do not add a tolerate-both branch |
| populated with an unresolvable stem | — | **skip that stem** (catch `UnknownArtifactIdError`, `continue`) and let `_check_unknown_references` report it — matching the two sibling resolution sites `consistency_check.py:734-735` and `:902-903`. The gate MUST NOT raise: `filter_graph_by_activation` is consumed by five callers including `_check_graph_kind_parity`, whose contract is fail-closed-**report** (`consistency_check.py:811-812`), never crash. |

## Implementation notes (binding on the WP)

- **Batch resolution once per filter call.** `_node_is_activated` is invoked once per node (`drg.py:351`) and `resolve_artifact_urn` does filesystem I/O (`rglob`). Resolving per-node is O(nodes×stems×fs-walk) and pushes `_node_is_activated` past the ≤15 complexity ceiling. Instead, `filter_graph_by_activation` builds a `dict[kind, frozenset[canonical_urn] | None]` **once** (lift `_build_tension_active_urns` from the deleted tension-scan almost verbatim — `consistency_check.py:932-956`), and `_node_is_activated` takes that pre-resolved map and stays a pure membership check. The **public gate signature is unchanged** (only the internal helper's).
- **Compare on full URN.** `resolve_artifact_urn` returns a full URN (`"directive:DIRECTIVE_001"`), while Step 3 today compares the bare `artifact_id`. Resolve activated stems to full URNs and membership-test against `node.urn` (as the tension-scan does at `consistency_check.py:929`).
- **One doctrine-root source.** Source `doctrine_root` from `resolve_doctrine_root()` (`charter.catalog`) — the SAME source the surviving compiler `references.yaml` projection uses — NOT `pack_context.pack_roots[0]` (a naive `__file__` join that can disagree in installed/wheel layouts and reintroduce the silent-drop class). `org_roots` = `pack_context.pack_roots[1:]`. Add a test pinning gate-doctrine-root == projection-doctrine-root. Prefer lifting `org_roots`/`doctrine_root` to a named `PackContext` accessor so the gate does not become a third open-coded copy of the `pack_roots[1:]` slice (compiler `:144`, tension-scan `:940` are the existing two).

## Attribution proof (NFR-001)

The characterization test must pair: (a) a stem-form populated list → **RED on merge-base**; (b) a
control whose entry already equals the canonical id → **GREEN on merge-base**. The GREEN control
isolates the cause as stem≠canonical, not an incidental populated-list error. Run against the real
built-in corpus (and this repo's populated `.kittify/config.yaml`), never a hermetic `id==stem` fixture.

## Consumer observables (NFR-002)

Each of the five callers gets a before/after test asserting a **named observable**, not a smoke test:
`executor.py:182`, `reference_resolver.py:67`, `compiler.py:1037` closure,
`consistency_check.py::_check_drg_cross_kind_refs` (`:424`), `context.py:928`. `None`-path
byte-identical to merge-base; populated-path emits the corrected per-ID result.

## What this contract does NOT change

The compiler `references.yaml` projection (`_resolve_config_activated_ids`, `compiler.py:88`) — it
already resolves stems correctly and is a catalog projection, not a graph filter (C-001). It stays.
