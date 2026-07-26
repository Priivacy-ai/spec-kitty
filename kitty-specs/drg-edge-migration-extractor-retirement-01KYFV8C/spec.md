# Mission Specification: DRG Edge Migration and Extractor Retirement

**Created**: 2026-07-26
**Status**: ⏸ **NOT YET SPECCED — deliberately.** Scope sketch only.
**Programme**: Mission **B2** of five — see the programme record [`doctrine-canonical-structure-remediation-01KYEYSD`](../doctrine-canonical-structure-remediation-01KYEYSD/spec.md).
**Order**: Third. Blocked by **A** and **B1**. Blocks **C**.
**Change mode**: `bulk_edit` — carries [`occurrence_map.yaml`](occurrence_map.yaml) (DIRECTIVE_035).

## Why this is a sketch and not a specification

**Operator guidance, 2026-07-26:** do not over-specify or plan any mission after phase A. Missions run
**one at a time**, each specced and planned only after the previous phase is finalized.

This mission is the most sensitive to that rule. Its entire proof chain — committed baseline →
structured diff → in-process ablation → completion gate — is built against a tree that A and B1 both
change materially. A closes the silent-drop sites `aliases` would fall through and extends the
occurrence-map schema this mission's guardrail depends on; B1 changes the relation vocabulary the
migration writes. Speccing the proof now would pin it to a tree that will not exist.

**Nothing is lost by waiting.** The measured scope, the traps, and the concern map live in the
programme record's [`spec.md`](../doctrine-canonical-structure-remediation-01KYEYSD/spec.md) and
[`plan.md`](../doctrine-canonical-structure-remediation-01KYEYSD/plan.md).

## Scope sketch

Make **all 774 DRG edges authored** and retire every mechanism that re-derives them. The extractor
becomes a node minter plus validator; node discovery stays derived.

- Committed pre-migration SHA-256 baseline manifest **before any artefact YAML is edited**, plus an in-process ablation harness.
- `<kind>.edges.yaml` authored tier as the localized source of truth; the aggregate `*.graph.yaml` becomes a self-declaring, content-hashed **generated cache** with freshness enforced in CI.
- Collapse the duplicated profile→directive field; lift the 219 reference labels onto 102 artefacts as `aliases`.
- Migrate the 559 MIGRATE-class entries across 169 files; author the 215 structural edges.
- Absorb and **delete** both Python edge registries and the calibrator; retire all extractor edge production.
- Gate the relationship-free invariant; preserve the 68 rationales and 219 labels; human review of the 55 hardcoded-`suggests` relations.

**Measured scope** (re-derive with `PYTHONPATH=src python scripts/doctrine/inline_reference_inventory.py`
— hand counts were wrong twice): 559 MIGRATE / 188 GOVERNANCE / 14 RAW across 171 files; 169 MIGRATE
files. Estimated 11–14 agent-days, ~365–390 files.

## Carried constraints — do not lose these when speccing

- **Never sweep `directive-references` (68).** Zero DRG edges, but it is the **seed set for the entire charter governance closure**. Deleting it empties every profile-routed prompt while fragments, golden counts and a zero-entries gate all stay green.
- **`tactic-references` (29) is classified MIGRATE but has a production render path** (`charter/context.py` `_render_profile_tactics`). **Re-adjudicate before migrating.**
- **Relation inference keys on SOURCE kind, not reference `type`** — keying on ref type mis-types **118 of 372** structured entries.
- **The overlay merge overwrites on `(source, target, relation)`**, so a half-done migration passes a diff-style proof. Completion must be asserted by the inventory gate, never by the diff alone.
- **The proof cannot be byte-identity** — preserving the rationales and labels breaks it by design, and a byte proof would pressure the migrator into deleting authored content to pass.
- **The ablation must be in-process**, over a tree copy: as a git sequence it is unachievable, because the extractor must be alive as the migration oracle while the ablation needs it deleted.
- **NFR-010 asserts at the production seams** (`charter/context.py` closure + the two inline render paths), **not** `resolve_governance_for_profile`, which has no production caller.
- **The profile-field collapse is not behaviour-neutral.** `python-pedro` carries `034` in `directive-references` only, producing no edge today. Evidence says omission at birth, not intent — accept as a single enumerated ledgered deviation.
- **The raw-material exemption is enumerated, not computed.** Two gaming shapes already exist in the tree: an artefact's markdown payload, and a mission-tier template with an empty glob.
- **`scope` (157) is the seed of every context resolution** — leaving it derived leaves the load-bearing relation outside the authority.
- **Re-author `occurrence_map.yaml` at field granularity** against A's schema extension before implementing. The current map is honest at file granularity but cannot separate the 188 GOVERNANCE and 14 RAW entries, because all 17 GOVERNANCE files and 5 of 7 RAW files also carry MIGRATE entries.
