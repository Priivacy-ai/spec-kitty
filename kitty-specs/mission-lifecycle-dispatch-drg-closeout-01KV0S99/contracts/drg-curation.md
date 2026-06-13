# Contract — DRG curation (workstream C, FR-008/009, NFR-003, C-003)

## Stale-reference repair (FR-008)

- `src/doctrine/styleguides/built-in/java-conventions.styleguide.yaml`: `references` entry
  `…/java-implementer.agent.yaml` (non-existent) → repaint to `…/java-jenny.agent.yaml`
  (real Java specialist profile; already `specializes_from implementer-ivan`).
- Sweep for other references of the **same class** (path/id/casing/retired-id pointing at a
  non-existent artifact); repair (repaint to a real target) or prune **the reference**
  (never the target artifact) with a per-fix one-line rationale.

## Orphan triage (FR-009, C-003) — wire-or-document, never bulk-delete

For each genuinely-orphaned **valid** doctrine artifact (no inbound/outbound edge):

1. **Prefer wiring** a real inbound edge when a natural referent exists (e.g., cite a
   refactoring tactic from the refactoring procedure / a coding directive).
2. **Else document** it as an accepted residual with a per-orphan rationale (in-mission),
   and file a curation follow-up ticket if the residual set is non-empty.
3. **Prune only** genuinely-retired artifacts (superseded/dead), each individually justified.
   Bulk deletion of valid-but-unreferenced doctrine is explicitly rejected (D-C2).

## Deterministic regen + regression pin (NFR-003)

- Regenerate via `spec-kitty doctrine regenerate-graph` (emit already deterministic: nodes
  sorted by URN, edges by `(source,target,relation)`, `generated_at="STATIC"`).
- `spec-kitty doctrine regenerate-graph --check` exits 0 iff the committed `graph.yaml`
  matches a fresh regen (freshness gate).
- Add a regression test pinning the reduced orphan count (`<= documented residual`) so it
  cannot silently grow; existing byte-identical-twice determinism test must stay green.

## Closure (#1863)

#1863 closes once: java-implementer (+ same-class) refs resolved; orphan count reduced to the
documented residual; residual rationale recorded (+ follow-up ticket if non-empty); regen
deterministic and freshness/orphan-count tests green.
