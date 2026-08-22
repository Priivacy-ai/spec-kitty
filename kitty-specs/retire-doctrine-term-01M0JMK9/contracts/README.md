# Contracts: Retire the Doctrine Term

**Mission**: retire-doctrine-term-01M0JMK9 · **Phase 1 output** of `/spec-kitty.plan`

This mission's "API contracts" are **artifact schemas**: the formats its deliverables must follow so that (a) implementation WPs execute rather than re-decide, and (b) downstream stack missions can consume the artifacts mechanically.

| Contract | Governs artifact | Consumed by |
|----------|------------------|-------------|
| [adr-content-contract.md](./adr-content-contract.md) | The new ADR in `docs/adr/3.x/` (IC-01) | M1 (executes the canon line + FR-011 glossary decisions), all stack missions (scope boundary, compatibility policy) |
| [inventory-schema.md](./inventory-schema.md) | `inventory.md` + supporting per-hit `inventory-hits.tsv` (IC-02) | M1–M6 (work lists, occurrence maps, fingerprint shrink), SC-002 verification |
| [operator-surface-map-schema.md](./operator-surface-map-schema.md) | M2's frozen command, serialized/API, supported-Python-API, and public distribution/wheel mapping contract | M2–M6 execution and exclusion checks |
| [stacked-plan-schema.md](./stacked-plan-schema.md) | `stacked-plan.md` (IC-04) | Program execution (mission-by-mission), SC-003/SC-004 verification |

**Shared rules**:
1. **Stable identifiers are the interface.** Downstream missions cite OC-## IDs and mission slugs — never prose descriptions. Renaming a class's description is allowed; reusing an ID for different occurrences is forbidden by `data-model.md` §3.
2. **Evidence before conclusion.** Every count derives from one-row-per-hit manifest evidence over pinned content and pathname audits; examples never substitute for classification.
3. **No unresolved cross-wave inputs.** M1 has zero local questions. Later questions must be named, bounded, owned, and unable to affect ordering or another mission's inputs.
4. **Single assignment owner.** Inventory defines hits/classes and plans non-owning CR candidates; `stacked-plan.md` alone assigns each OC-## to one M1–M5 primary owner and each CR to one M1–M4 introduction plus M6 removal. Every funded source OC owner must equal the CR introduction wave; mixed-owner rows split before approval.
