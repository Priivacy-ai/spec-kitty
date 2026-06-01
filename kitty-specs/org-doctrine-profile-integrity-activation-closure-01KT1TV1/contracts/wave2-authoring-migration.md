# Contract: Wave 2 — DRG Authority & Bulk-Edit Migration

## C2.1 Fields rejected (hard cutover, FR-028, OQ-2-i)

- **Given** any artifact YAML (any of the 9 kinds) declaring `enhances:`, `overrides:`, or (for profiles) `specializes_from:`
  **When** loaded
  **Then** validation fails with a structured "relationship fields are authored in DRG fragments" error (the keys are no longer accepted; `extra="forbid"`).
- **Given** the model classes
  **Then** the relationship fields are removed from `Tactic`, `Styleguide`, `Paradigm`, `Procedure`, `AgentProfile`, and absent from `Directive`, `Toolguide`, mission step contract, mission type.

## C2.2 Relationships via DRG fragments + edges (FR-001, FR-003, FR-004)

- **Given** a fragment authoring `specializes_from`, `enhances`, or `overrides` edges for any kind (incl. directive, toolguide, mission step contract, mission type)
  **When** merged
  **Then** the edges validate from shipped/org/project fragments and appear in the merged DRG.
- **Given** the DRG documentation/fixtures (FR-004)
  **Then** they explain lineage vs delegation vs enhancement/override/replacement, with at least one profile-to-profile `specializes_from` fixture edge.

## C2.3 Lineage consumer migrated (FR-002)

- **Given** the agent-profile hierarchy resolver
  **When** computing parent/ancestors/cycle detection
  **Then** it resolves via doctrine-merged DRG traversal of `SPECIALIZES_FROM` edges (not the removed field); a lineage cycle is still detected and reported.

## C2.4 Augmentation single-source & parity (FR-030, FR-031, FR-032)

- **Given** the auto-emit set and validator augmentation set
  **Then** both derive from one shared constant; adding a kind is a one-line change (no two hand-synced tables).
- **Given** a fragment declaring `enhances`/`overrides` for a newly-covered kind (directive/toolguide/step-contract/mission-type)
  **Then** the validator applies the same intent-aware behavior as the original five: suppress the same-ID advisory when intent is declared, hard-error on unknown target, `intent_conflict` when both declared.
- **Given** mission-type augmentation
  **Then** it is handled explicitly (canonical-kind-universe expansion with contract-test sweep, or a documented separate path) — never silently dropped (FR-032).

## C2.5 Topology integrity (FR-029)

- **Given** an `enhances` overlay on a mission step contract or mission type
  **When** merged
  **Then** action-sequence ordering and step input/output contracts are preserved (no silent reordering/drop); `overrides` performs full replacement.

## C2.6 Migration zero-loss (NFR-007, bulk edit)

- **Given** the pre-migration set of field-authored relationships across built-in doctrine + shipped packs
  **When** migrated to DRG-fragment edges
  **Then** a count/identity diff shows every pre-existing relationship has exactly one corresponding merged DRG edge (I-A1); built-ins load with zero diagnostics (NFR-005).
- **Given** `occurrence_map.yaml`
  **Then** every one of the 8 occurrence categories has an explicit action and the `implement` bulk-edit gate passes for the field-retirement WPs.
