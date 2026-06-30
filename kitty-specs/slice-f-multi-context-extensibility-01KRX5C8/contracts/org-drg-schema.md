# Contract — Organisation-Tier DRG Fragment Schema

> Mission: `slice-f-multi-context-extensibility-01KRX5C8`
> Closes: FR-001, FR-003, FR-004, FR-005 | Companions: [charter-scope-resolution.md](charter-scope-resolution.md), [catalog-miss-cli-visibility.md](catalog-miss-cli-visibility.md), [contract-round-trip-frontmatter.md](contract-round-trip-frontmatter.md)
> Data model: [../data-model.md §2](../data-model.md#2-orgdrgfragment-fr-001), [../data-model.md §3](../data-model.md#3-orgdrgconflict-fr-004-fr-005)

The organisation-tier DRG fragment is one configured layer of doctrine-reference-graph state between shipped (`built-in`) and project (`.kittify/doctrine/graph.yaml`) layers. Slice F adds this tier so organisations can ship proprietary governance artefacts without forking the shipped graph.

---

## Input Contract

### Operator-facing surface — `.kittify/config.yaml`

The operator configures one or more org packs:

```yaml
# round-trip: skip: operator .kittify/config.yaml shape sketch (organisation_packs list), not a single Pydantic payload — the executable OrgDRGFragment examples are below
organisation_packs:
  - name: acme-compliance
    source: local_path
    path: ../acme-org-doctrine
  - name: acme-engineering
    source: local_path
    path: ../acme-engineering-doctrine
```

**This mission ships `source: local_path` only** (NEW-1 resolution). `url` and `package` sources are reserved and produce `NotImplementedError` with a descriptive message that links to the follow-up tracker.

### Pack-side layout

Each org pack on disk:

```
<pack-path>/
├── org-charter.yaml         # required (already supported by Mission B)
├── drg/
│   └── fragment.yaml        # NEW (this mission)
└── <kind>s/<id>.<kind>.yaml # any artefacts the fragment references
```

### `fragment.yaml` shape

```yaml
# pydantic_model: charter.drg.OrgDRGFragment
# expect: valid
pack_name: acme-compliance
source_kind: local_path
source_ref: ../acme-org-doctrine
layer_index: 1
provenance_marker: org
nodes:
  - id: sox-controls
    kind: directives
    title: "SOX Control Framework"
    body_path: directives/sox-controls.directive.yaml
edges:
  - source: sox-controls
    target: caveman-comments
    relation: refines
```

The `nodes` and `edges` shapes mirror `doctrine.drg.models.DRGNode` and `DRGEdge`.

### Invalid example — kind not in the 8-kind universe

```yaml
# pydantic_model: charter.drg.OrgDRGFragment
# expect: invalid
pack_name: acme-compliance
source_kind: local_path
source_ref: ../acme-org-doctrine
layer_index: 1
provenance_marker: org
nodes:
  - id: foo
    kind: not-a-real-kind        # ← C-009 violation
    title: "Bogus"
edges: []
```

Per C-009 the schema reuses Mission B's 8-kind plural-naming union semantics; unknown kinds raise `pydantic.ValidationError`. The FR-140 round-trip gate exercises this example via the frontmatter walker.

---

## Output Contract

### Loader output

`charter.drg.load_org_drg(repo_root: Path) -> list[OrgDRGFragment]` returns one fragment per configured pack in `.kittify/config.yaml` declaration order. Layer indices are assigned `1..N` matching declaration order.

### Merge output

`charter.drg.merge_three_layers(shipped, org_fragments, project) -> DRGGraph` produces a merged graph where every node and edge carries `source: built-in | org:<pack_name> | project`. The merge is order-stable (deterministic).

### Validator output

`spec-kitty charter lint` reports per-layer findings prefixed with the source name:

```
[built-in]    OK — 87 nodes, 142 edges
[org:acme-compliance]   OK — 12 nodes, 4 edges
[project]     warn: directive 'caveman-comments' selected but no body found
```

### Conflict output

`OrgDRGConflictError` carries one or more `OrgDRGConflict` records. The error message is operator-actionable and lists:

- Each conflict's `kind`, `target_id`, and `conflicting_layers`.
- The `resolution_applied`.
- The remediation hint (e.g. "remove the override from the org pack, OR escalate the shipped invariant change via a spec-kitty governance proposal").

---

## Failure modes

| Trigger | Exception | Operator message |
|---|---|---|
| Configured `local_path` does not exist on disk | `OrgPackMissingError` | "Org pack `<name>` configured at `<path>` not found. Either fetch the pack (`spec-kitty doctrine fetch --pack <name>`) or remove the entry from `.kittify/config.yaml`." (FR-004) |
| Pack's `drg/fragment.yaml` declares a node kind not in the 8-kind universe | `pydantic.ValidationError` | Per pydantic — names the field and the rejected value (C-009 binding) |
| Pack's fragment overrides a shipped invariant edge or node | `OrgDRGConflictError` with `resolution_applied="hard_fail"` | "Org pack `<name>` attempts to override shipped invariant `<target_id>`. Layer rule (Mission A): shipped invariants cannot be overridden by org packs. Remove the override or escalate the change upstream." (FR-005) |
| Pack's fragment imports across the layer boundary (e.g. body_path references `src/specify_cli/...`) | `OrgDRGConflictError` with `kind="layer_rule_violation"` | "Org pack `<name>` violates the layer rule. Doctrine artefacts cannot reference `src/specify_cli/`." (FR-005, C-001) |
| Pack uses `source_kind: url` or `package` in this mission | `NotImplementedError` | "Org pack source `url`/`package` is not yet implemented (tracker: <ticket>). Use `source: local_path` for now." (NEW-1) |

---

## Backward compatibility guarantee

- Repositories with **no `organisation_packs:` configuration** behave identically to today (NFR-001 binding). `load_org_drg(repo_root)` returns `[]`; `merge_three_layers` collapses to the existing two-layer merge.
- The 23 `test_wp_prompt_governance_contract.py` fixtures pass unchanged because none of them configure an org pack.
- The shipped-DRG layer's contents are not altered by this mission — only the loader is extended to thread an org layer between shipped and project.

---

## ATDD anchors

- `tests/integration/test_three_layer_drg_end_to_end.py` (Scenario 1 happy path; AC-1)
- `tests/charter/test_org_drg_loader.py` (unit; loader + merge + provenance)
- `tests/integration/test_org_pack_missing_path_hard_fails.py` (FR-004)
- `tests/charter/test_org_drg_cannot_override_shipped_invariants.py` (FR-005)
- `tests/contract/test_example_round_trip.py` (the `expect: valid` and `expect: invalid` examples above, exercised by the FR-140 walker)
