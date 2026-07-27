# Decision Moment `01KY1XHDJC35VFFFHH5S10G2Y7`

- **Mission:** `doctrine-tension-edges-01KY1WPC`
- **Origin flow:** `specify`
- **Slot key:** `specify.model.anti-pattern-node-kind`
- **Input key:** `anti_pattern_node_kind`
- **Status:** `resolved`
- **Created:** `2026-07-21T08:44:05.580286+00:00`
- **Resolved:** `2026-07-21T09:04:56.370500+00:00`
- **Opened by:** `cli`
- **Other answer:** `false`

## Question

Anti-pattern/smell targets of rejects edges: introduce a new NodeKind (e.g. anti_pattern/smell) that ripples through ArtifactKind + activation filter, or keep them as kind:paradigm/tactic nodes carrying an anti-pattern tag?

## Options

- new-nodekind-anti-pattern
- keep-existing-kind-plus-tag

## Final answer

Introduce a new first-class NodeKind (anti_pattern/smell); wire ArtifactKind, _SINGULAR_TO_PLURAL, the activation filter, and schemas accordingly. Anti-pattern targets are no longer kind:paradigm/tactic phantoms.

## Rationale

_(none)_

## Change log

- `2026-07-21T08:44:05.580286+00:00` — opened
- `2026-07-21T09:04:56.370500+00:00` — resolved (final_answer="Introduce a new first-class NodeKind (anti_pattern/smell); wire ArtifactKind, _SINGULAR_TO_PLURAL, the activation filter, and schemas accordingly. Anti-pattern targets are no longer kind:paradigm/tactic phantoms.")
