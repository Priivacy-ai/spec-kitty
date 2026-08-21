# Contracts: Retire the Doctrine Term

**Mission**: retire-doctrine-term-01M0JMK9 · **Phase 1 output** of `/spec-kitty.plan`

This mission's "API contracts" are **artifact schemas**: the formats its deliverables must follow so that (a) implementation WPs execute rather than re-decide, and (b) downstream stack missions can consume the artifacts mechanically.

| Contract | Governs artifact | Consumed by |
|----------|------------------|-------------|
| [adr-content-contract.md](./adr-content-contract.md) | The new ADR in `docs/adr/3.x/` (IC-01) | M1 (executes the canon line + FR-011 glossary decisions), all stack missions (scope boundary, compatibility policy) |
| [inventory-schema.md](./inventory-schema.md) | `inventory.md` (IC-02) | M1–M6 (work lists, re-baselining), SC-002 verification |
| [stacked-plan-schema.md](./stacked-plan-schema.md) | `stacked-plan.md` (IC-04) | Program execution (mission-by-mission), SC-003/SC-004 verification |

**Shared rules**:
1. **Stable identifiers are the interface.** Downstream missions cite OC-## IDs and mission slugs — never prose descriptions. Renaming a class's description is allowed; reusing an ID for different occurrences is not (OC-I2).
2. **Evidence before conclusion.** Every count in any artifact traces to the mechanical audit procedure (NFR-001); no hand-tallied numbers.
3. **No new decisions downstream.** Anything a stack mission would need to decide is either fixed in these artifacts or explicitly marked `OPEN` with an owner — and M1 must have zero `OPEN` items (FR-010).
