# Data Model: Operating-Procedures Validate, Triage, Data-Drive

**Date**: 2026-08-19 · **Mission**: operating-procedures-validate-triage-01M0DR8F

This is a doctrine/graph mission; the "data model" is the resolution relation and the
diagnostic value objects, not persisted storage.

## Entities & Value Objects

### `OperatingProcedureRef` (conceptual)
- **What**: one string entry in `AgentProfile.collaboration.operating_procedures`.
- **Fields**: `profile_id: str`, `entry: str` (the authored procedure id).
- **Source**: `doctrine/agent_profiles/profile.py:161`.

### `UnresolvedOpProc` (new value object)
- **What**: a diagnostic record for one op-proc entry that does not resolve to a real procedure node.
- **Fields**:
  - `profile_id: str` — the owning profile.
  - `entry: str` — the unresolvable id as authored.
  - `reason: Literal["no_node", "wrong_kind"]` — `no_node` (fictional) vs `wrong_kind` (resolves to a non-procedure node).
  - `resolved_kind: str | None` — for `wrong_kind`, the kind it actually resolved to (e.g. `"tactic"`); `None` for `no_node`.
- **Frozen dataclass**, mirroring `SkippedProfile` (`doctrine/agent_profiles/diagnostics.py`).
- **Ordering**: deterministic by `(profile_id, entry)` (NFR-002-style stable output).

### Procedure node universe
- **What**: the set of `procedure:` URNs in the built-in DRG.
- **Derivation**: `{n.urn for n in graph.nodes if n.kind is NodeKind.PROCEDURE}` — no restatement of the id list.
- A bare entry id `x` resolves iff `artifact_to_urn("procedure", x)` ∈ that set.

## Resolution relation (the validator)

```
resolve_operating_procedures(
    profiles: Iterable[AgentProfile],
    procedure_urns: AbstractSet[str],
    *,
    node_urns_by_kind: Mapping[NodeKind, AbstractSet[str]] | None = None,  # to classify wrong_kind
) -> list[UnresolvedOpProc]
```

- For each profile, for each `entry` in `collaboration.operating_procedures`:
  - `procedure:<entry>` ∈ `procedure_urns` → **resolved** (no record).
  - else if `<entry>` matches a node of another kind → `UnresolvedOpProc(reason="wrong_kind", resolved_kind=<kind>)`.
  - else → `UnresolvedOpProc(reason="no_node")`.
- Pure, total, deterministic. No fuzzy matching (NFR-003 fail-closed).
- Built-in unresolved set is **44** pre-triage, **0** post-triage.

## Edge emission (the extractor change)

For each built-in profile, for each op-proc `entry` that resolves to a procedure node:
```
DRGEdge(source=agent_profile:<profile_id>, target=procedure:<entry>, relation=REQUIRES)
```
- Guarded: emit only when `procedure:<entry>` is in the procedure node set (belt-and-suspenders for org/project tiers).
- Deduped by the existing `_add_edge` triple key (a procedure named by both op-proc and a surviving pin collapses to one edge).
- Fail-closed build raise: if any **built-in** op-proc entry is unresolved, `extract_artifact_edges` raises (post-triage this never fires).

## State / lifecycle

No runtime state. The lifecycle is build-time: parse profiles → resolve → (validate | emit) →
`assert_valid` → write committed `*.graph.yaml` fragments → freshness gate.

## Invariants

- **INV-1**: every built-in op-proc entry resolves to a procedure node (post-triage). Enforced by the empty-set gate + build raise.
- **INV-2**: no `agent_profile → procedure` edge exists whose target is not a procedure node (guard).
- **INV-3**: the two prose-sourced pins remain; the two op-proc-sourced pins are absent from `_CURATED_ARTIFACT_EDGES` yet their edges persist (data-driven).
- **INV-4**: `assert_valid` passes on the regenerated graph (zero dangling, no dup triple, no new cycle).
- **INV-5**: all three RECONCILE triggers have inbound edges.
