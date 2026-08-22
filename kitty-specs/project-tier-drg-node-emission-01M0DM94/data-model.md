# Data Model — Project-Tier DRG Node Emission (M6)

## Entities

### Emittable project-tier kind set
- The **keys** of `charter.synthesizer.project_drg._KIND_TO_NODE_KIND` (post-change), an `ArtifactKind`-keyed partial:
  - `ArtifactKind.DIRECTIVE → NodeKind.DIRECTIVE`
  - `ArtifactKind.TACTIC → NodeKind.TACTIC`
  - `ArtifactKind.STYLEGUIDE → NodeKind.STYLEGUIDE`
  - `ArtifactKind.AGENT_PROFILE → NodeKind.AGENT_PROFILE`  *(new in M6)*
- Read via `_node_kind_for(kind: str) -> NodeKind | None`: `ArtifactKind(kind)` (catch `ValueError → None`) then `.get`. A kind not in the set → `None` → node skipped.
- **Explicitly excluded** (map absence is the contract, not an oversight): `asset` (#3037), `procedure`, `paradigm`, `toolguide`, `glossary_pack`, `mission_step_contract`, `template`, `anti_pattern`.

### Project agent_profile node
- **URN**: `agent_profile:<profile-id>` where `<profile-id>` is the `profile-id` field of the authored `*.agent.yaml`.
- **DRGNode**: `kind = NodeKind.AGENT_PROFILE`, `label = <profile display name or None>`, `provenance = "project"` (merge-time marker), `tags = []`.
- **Source**: `.kittify/doctrine/agent_profiles/*.agent.yaml` (recursive), discovered via the project-tier profile reader / mirror of the built-in walk.
- **Edges**: none authored by M6 (edge authoring is M5). Node must be valid without inbound edges.

## Invariants

| Inv | Statement | Enforcement |
|-----|-----------|-------------|
| INV-1 | A project profile URN must not collide with a built-in node URN | additive-only guard (reuse `emit_project_layer` FR-020/EC-6 pattern) → `ProjectDRGValidationError` |
| INV-2 | Each `agent_profile:<id>` appears at most once in the overlay | overlay-internal dedupe (`seen_urns`) |
| INV-3 | The map is `ArtifactKind`-keyed and total-or-exempt under the totality gate | `test_kind_mapping_totality.py` (`_EXEMPT_GET_PARTIALS` entry) |
| INV-4 | No `asset:*` project node emitted | emitter walks agent_profiles only; asset absent from the map |
| INV-5 | Emitted node lands in `.kittify/doctrine/graph.yaml` | flows through `persist → _promote_graph_overlay` |
| INV-6 | Malformed profile file fails loud (names the file) | fail-closed at walk/parse (NFR-002) |

## State transition (the fix, observable)

```
author .kittify/doctrine/agent_profiles/<name>.agent.yaml
   │  (loads + validates today — but no node)
   ▼
charter synthesize / activate  ──►  walk emitter builds agent_profile:<id> DRGNode
   ▼
merge into project overlay DRGGraph  ──►  persist (staging graph.yaml)
   ▼
_promote_graph_overlay  ──►  .kittify/doctrine/graph.yaml  (node now present: 0 → 1)
   ▼
load_validated_graph  ──►  cascade_activation_targets  (node reachable)
```
