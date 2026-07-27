# Phase 0 Research: Doctrine Tension as First-Class DRG Edges

All `[NEEDS CLARIFICATION]` markers from spec.md were resolved before this mission
reached plan (D1/D2/D3, resolved by the operator via the squad-escalation path — see
`decisions/`). Two additional plan-phase decisions were resolved via the Decision
Moment Protocol during this planning session. No open clarifications remain
(`spec-kitty agent decision verify` returns `status: clean`).

## Decision: FR-015 downstream compatibility mechanism

- **Decision**: New `spec-kitty migrate` subcommand (module modeled on
  `src/specify_cli/migration/backfill_identity.py`, wired via
  `src/specify_cli/cli/commands/migrate_cmd.py`) that rewrites org-pack-authored
  `opposed_by` usages into `in_tension_with`/`rejects` edges. No deprecation window —
  the schema drops `opposed_by` from `additionalProperties: false` in the same release
  the migration ships in.
- **Rationale**: This repo already has an established one-shot-rewrite migration
  pattern (`backfill_identity.py` + `doctor identity` verification loop) for exactly
  this shape of problem: a schema/model change that could silently break org-pack
  consumers. Reusing it keeps the fix discoverable and consistent, and D1 only required
  *a* migration/deprecation path — it did not require carrying the legacy field forward.
- **Alternatives considered**:
  - *Deprecation window (warn for N releases before removal)*: rejected — prolongs the
    exact mis-encoding (D1's finding: extractor maps `opposed_by` to `replaces`,
    producing a nonsensical mutual cycle) that this mission exists to retire. A window
    would mean two representations of tension coexist for N releases.
  - *Diagnostic/warning only, no auto-rewrite*: rejected — pushes manual YAML editing
    onto every downstream consumer for a mechanically-derivable rewrite
    (`opposed_by` → `in_tension_with`, or → `rejects` for anti-pattern targets per D2);
    higher error surface than a tool doing it once.
- (Decision record: `01KY239G8EAZD7D1K37N5NM7NX`)

## Decision: bulk-edit classification (C-007)

- **Decision**: Mission runs under `change_mode: bulk_edit`; `occurrence_map.yaml`
  covers all 8 standard categories for the 21-site `opposed_by`/`Contradiction`
  removal.
- **Rationale**: C-007's own text frames `bulk_edit` as the default, exemption as the
  exception. Several of the 21 sites are semantic rewrites (FR-006/FR-007 migrate
  content to new edge types), not pure deletions, so the per-category
  guardrail (distinguishing `code_symbols`/`serialized_keys` needing `manual_review`
  from `tests_fixtures` safe to `rename`) is load-bearing, not boilerplate.
- **Alternatives considered**: *Exempt as pure-removal* — rejected, since a pure-removal
  exemption requires every site to be a straight deletion, which FR-006/FR-007
  contradict (content moves to new edges, it does not simply disappear).
- (Decision record: `01KY23N4RBCGWVGZ4QJFFFSJPH`)

## Domain research: symmetric, non-transitive relation storage

- **Decision**: Store `in_tension_with` as one canonical edge, source = the
  lexicographically-smaller URN (C-002); query both directions via the existing
  `DRGGraph.edges_from`/`edges_to` helpers (confirmed present — Assumption A3); the
  consistency-checker keys findings on the sorted URN pair for dedup.
- **Rationale**: Avoids a duplicate-edge bookkeeping problem (authoring both `A→B` and
  `B→A` would require keeping two edges in sync) and needs no new graph primitive.
- **Alternatives considered**: *Store both directions as separate edges* — rejected by
  C-002 directly: doubles authoring surface and reopens the divergent-reason drift
  problem named in the Edge Cases section (symmetric authoring drift).

## Domain research: cascade exclusion mechanism

- **Decision**: Omit `in_tension_with`/`reconciles_tension`/`rejects` from the cascade
  engine's `REFERENCE_RELATIONS` allowlist (exclusion by omission); guard with a
  regression test asserting they are absent (FR-013/C-003), since there is no
  "excluded relations" list to positively assert against.
- **Rationale**: The cascade engine's existing contract is pure-reachability off an
  allowlist with no per-kind special-casing (C-003). Adding a denylist would introduce
  a second list that must be kept in sync with the allowlist — a single-canonical-
  authority violation.
- **Alternatives considered**: *Explicit relation-kind check in the cascade engine*
  (`if relation in {IN_TENSION_WITH, ...}: skip`) — rejected: reintroduces per-kind
  logic the cascade engine's design deliberately avoids, and only the allowlist
  omission is testable as a true regression (a denylist could silently rot if a new
  relation is added later and nobody adds it to the denylist).

## Domain research: anti-pattern/smell node representation (D2 follow-through)

- **Decision** (already resolved as D2; researched here for the concrete wiring): new
  first-class `NodeKind.ANTI_PATTERN`/`SMELL`, threaded through `ArtifactKind`,
  `_SINGULAR_TO_PLURAL`, `_SINGULAR_TO_PER_KIND_FIELD`, the activation filter
  (`_node_is_activated`), and cascade `_kind_of` — plus a new `tags: list[str]` field on
  `DRGNode` (Pydantic v2's `extra='ignore'` default means an un-modelled key silently
  drops on load, so `tags` must be modelled explicitly for any marker to round-trip).
- **Rationale**: Confirmed by reading `src/doctrine/drg/models.py` — `DRGNode` has no
  `tags` field today; adding one is required, not optional, for D2's marker to survive
  a load/save round trip.
- **Alternatives considered**: *Tag on existing `paradigm`/`tactic` kind* — this is
  exactly what D2 rejected (an anti-pattern is not an active paradigm; conflating the
  two lets an anti-pattern get cascaded/activated as if it were a live rule).

## Codebase verification: unrelated `Contradiction` symbol

- **Finding**: `grep -rln "Contradiction"` returns 13 files, but only 4
  (`shared/models.py`, `directives/models.py`, `paradigms/models.py`,
  `tactics/models.py`) are the DRG-model `Contradiction` this mission removes. The
  remaining files (`charter_runtime/lint/checks/contradiction.py` and its two
  importers, plus its dedicated test) define an unrelated `ContradictionChecker` —
  a charter-lint text-contradiction check with no `opposed_by` occurrence and no
  relationship to the DRG model. This confirms NFR-002's explicit carve-out
  ("the dead-symbol gate scoped to that symbol, not the word 'Contradiction' which
  occurs unrelated elsewhere") is not hypothetical — the ambiguity is real in this
  codebase today. Recorded as `do_not_change` exceptions in `occurrence_map.yaml`.
