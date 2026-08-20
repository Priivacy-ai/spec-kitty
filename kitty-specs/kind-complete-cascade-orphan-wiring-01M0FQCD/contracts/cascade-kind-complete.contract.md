# Contract: Kind-Complete Cascade + Orphan Wiring

Behavioral contract for the cascade engine and the orphan ledger. Every clause
is a testable assertion; the WPs must land a red-first test for the starred
(★) clauses before the fix.

## Cascade traversal (IC-01)

- **C-CAS-1 ★**: For each **governance-bearing** built-in `mission_type` URN
  (`documentation`, `research`, `software-dev`), `cascade_activation_targets(
  graph, urn, CascadeScope.all())` returns a non-empty `activated` mapping.
  (Baseline: all four return empty.) `mission_type:plan` is the documented
  exception — its actions scope no governance (only `instantiates→template`), so
  it correctly returns empty; a dedicated test pins this with rationale. The
  #2829 traversal dead-end is closed for all four; plan simply has no governance
  authored to reach.
- **C-CAS-2**: The activated mapping for `mission_type:documentation` contains the
  governance kinds reachable through its actions' `scope` edges (at least
  `directive`, `tactic`, `styleguide`).
- **C-CAS-3 ★**: No `template` or `asset` id appears in `activated` or in
  `referenced_but_not_cascaded(...).skipped`, for any source — including sources
  whose closure reaches templates/assets.
- **C-CAS-4**: No `action:` node (nor any non-`ArtifactKind` node) is ever emitted
  as a `ReferencedArtifact` / activation target.
- **C-CAS-5**: The candidate filter is `kind in CHARTER_ACTIVATABLE_KINDS`, read
  from `doctrine.artifact_kinds` — not a re-declared literal (assert by identity/
  membership against the imported set; a self-mutation guard proves a
  hypothetical non-excluded kind flows through while `template`/`asset` never do).
- **C-CAS-6**: Excluded relations stay unfollowed — a graph with only an
  `in_tension_with` / `rejects` / `delegates_to` / `specializes_from` / `enhances`
  / `overrides` / `replaces` / `applies` / `vocabulary` edge from the source
  yields an empty cascade.
- **C-CAS-7**: `deactivation_plan` remains shared-reference-safe under the widened
  followed set — a candidate reachable (via the widened set) from another active
  source is skipped (never deactivated), and the referencing source is named.

## Orphan wiring (IC-02)

- **C-ORP-1 ★**: In the pure extractor graph, each of
  `styleguide:given-when-then-authoring`, `toolguide:gherkin`, `toolguide:sonar`,
  `styleguide:quadruple-a-test-format` has ≥1 inbound edge (baseline: 0 inbound
  in the pure graph → present in `_ACTIVATED_BUT_ORPHANED`).
- **C-ORP-2**: Each promoted edge is `directive:<DIR> --suggests--> <target>`,
  identical (source, target, relation, when, reason) to the removed overlay edge;
  the shipped `(source, target, relation)` edge set is unchanged.
- **C-ORP-3 ★**: `styleguide:deployable-skill-authoring` is recorded in the
  direct-activation-only disposition with a rationale and removed from the
  "must-shrink" `_ACTIVATED_BUT_ORPHANED` debt set.
- **C-ORP-4**: `spec-kitty doctrine regenerate-graph --check` passes (committed
  fragments fresh); the in-process byte-identity guard stays green.
- **C-ORP-5**: Directive `references` entries round-trip `reason` (symmetric with
  `when`); an existing directive ref without `reason` is unchanged.
- **C-ORP-6**: The golden re-ledger is applied exactly once — `_ACTIVATED_BUT_
  ORPHANED` −5, `_ORPHANS_RESOLVED_BY_OVERLAY` −4, reachability pins unchanged;
  every moved value is traced to a single edge/relation cause in the ledger
  comments + the wiring-table doc.

## Cross-cutting

- **C-X-1**: `src/charter/cascade.py` imports only `doctrine.*` (never
  `specify_cli`).
- **C-X-2**: All new/changed code passes `ruff` and `mypy --strict` with zero
  suppressions.
