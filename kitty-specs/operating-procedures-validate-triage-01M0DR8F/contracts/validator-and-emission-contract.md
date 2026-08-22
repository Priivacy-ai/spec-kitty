# Contract: Operating-Procedures Validator & Edge Emission

**Mission**: operating-procedures-validate-triage-01M0DR8F

This mission exposes no HTTP/RPC surface. The contracts are the validator function,
the extractor emission behaviour, and the doctor diagnostic shape.

## C1 — `resolve_operating_procedure_entries` (pure validator)

**Location**: `src/doctrine/agent_profiles/operating_procedures.py` (new).

The validator operates on the raw `{profile_id: [entry, ...]}` seam rather than
`AgentProfile` objects, because every caller (the DRG extractor, `doctor doctrine`,
and the gate test) holds parsed YAML dicts, not model instances. `node_universe`
derives the procedure/kind sets from a DRG node collection (single authority — no
restated id list).

```python
def resolve_operating_procedure_entries(
    entries_by_profile: Mapping[str, Sequence[str]],
    procedure_urns: AbstractSet[str],
    urns_by_kind: Mapping[NodeKind, AbstractSet[str]] | None = None,
) -> list[UnresolvedOpProc]: ...

def node_universe(
    nodes: Iterable[DRGNode],
) -> tuple[frozenset[str], dict[NodeKind, frozenset[str]]]: ...
```

**Guarantees**:
- Returns one `UnresolvedOpProc` per (profile, entry) that does **not** resolve to a `procedure:` URN.
- `reason="wrong_kind"` with `resolved_kind` set when the entry matches a non-procedure node; else `reason="no_node"`.
- Empty list ⇔ every entry across `entries_by_profile` resolves to a procedure node.
- Deterministic order by `(profile_id, entry)`. Pure — no I/O, no fuzzy match.

**Given/When/Then**:
- Given a profile with `operating-procedures: [spike-timebox-policy]` and that procedure exists → When resolved → Then no record.
- Given `operating-procedures: [tdd-red-green-refactor]` (a tactic) → Then one record, `reason="wrong_kind"`, `resolved_kind="tactic"`.
- Given `operating-procedures: [code-review-checklist]` (no node) → Then one record, `reason="no_node"`.

## C2 — Empty-set gate (WP09 archetype)

**Location**: `tests/architectural/test_operating_procedures_resolve.py` (new).

**Assertion**: over the real built-in profiles + built-in procedure node set,
`resolve_operating_procedures(...) == []`. Non-vacuous: mutating one built-in profile
to add a fictional entry must red the gate (self-mutation check).

**Given/When/Then**:
- Given the shipped built-in doctrine → When the gate runs → Then the unresolved set is empty (exit green).
- Given a fictional entry injected into any built-in profile → Then the gate fails naming that (profile, entry).

## C3 — Extractor emission (data-drive, guarded)

**Location**: `src/doctrine/drg/migration/extractor.py::extract_artifact_edges` (agent-profile block).

**Behaviour**:
- For each built-in profile op-proc entry resolving to a procedure node → emit `agent_profile:<id> --requires--> procedure:<entry>`.
- Entry not resolving to a procedure node → emit nothing (guard).
- If any **built-in** entry is unresolved → raise (fail-closed; post-triage never fires).
- The two op-proc-sourced entries in `_CURATED_ARTIFACT_EDGES` are removed; their edges persist via this path.

**Given/When/Then**:
- Given a synthetic profile fixture with a resolvable op-proc procedure → When `extract_artifact_edges` runs → Then exactly one `requires` edge to that procedure.
- Given a synthetic profile whose op-proc entry is absent/non-procedure → Then no procedure edge for it, and (if built-in-scoped test) the build raises.
- Given the shipped built-in tree post-triage → Then 8 `agent_profile → procedure` edges (was 4): +4 net-new real refs, 2 re-derived pins, 2 prose pins.

## C4 — RECONCILE third edge

**Location**: `_CURATED_ARTIFACT_EDGES` (or equivalent) — `tactic:change-apply-smallest-viable-diff --suggests--> directive:RECONCILE_CHANGE_SCOPE_TENSIONS`.

**Given/When/Then**:
- Given the regenerated graph → Then all three trigger→RECONCILE edges exist and `assert_valid` passes.

## C5 — Doctor diagnostic shape

**Location**: `specify_cli/cli/commands/_doctrine_collect.py` (report augmentation via the cross-grain-check seam).

**Shape**: `doctor doctrine --json` carries a structured finding (e.g. `org_drg["operating_procedures_unresolved"]`,
a list of `{profile_id, entry, reason, resolved_kind}`) and, when non-empty on built-in, flips `healthy` to false.
Post-triage the built-in list is empty; the field is present-and-empty (discoverable, honest).

## C6 — Graph freshness

**Location**: committed `packs/built-in/*.graph.yaml` fragments.

**Assertion**: `spec-kitty doctrine regenerate-graph --check` exits 0 (committed graph == freshly generated).
The regenerated delta is exactly the +10 edges in research.md; `test_extractor_projection.py` count pins are updated to match.
