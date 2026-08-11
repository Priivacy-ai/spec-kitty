---
title: Doctrine
description: Doctrine layering, charter boundary, and artifact-selection planning — architecture reviews, gap analyses, and mission scope notes.
doc_status: draft
updated: '2026-07-26'
related:
- docs/plans/index.md
---
# Doctrine

Design and review artifacts for the doctrine layering system: charter/runtime
boundary audits, layered resolution design, org-doctrine-layer reviews, and
related mission scope notes.

- [Doctrine Usage Test (WP11 dogfood)](391-doctrine-usage-test.md)
- [Charter as Central Path Resolver — Gap Analysis](charter-path-resolution-gaps.md)
- [Pre-flight investigation — user-authored doctrine artifact selection](doctrine-artifact-selection-preflight.md)
- [Doctrine Inclusion Assessment](doctrine-inclusion-assessment.md)
- [Doctrine Migration: Architecture Alignment Review](doctrine-migration-architecture-review.md)
- [Layered Doctrine Resolution — Design Blueprint](layered-doctrine-resolution-design.md)
*Tiering: **AUTHORITY** docs are the only citable design/sequence statements; **RECORD** docs are superseded inputs and verdicts kept for provenance; **EVIDENCE** docs are raw squad reports and measurements.*

- [The Manifesto Tier — doctrine's missing primary-driver layer](manifesto-tier-primary-drivers.md) — RECORD; *superseded in part; read the verdict first*
- [Manifesto tier — verdict, corrections, and handover](manifesto-tier-verdict-and-handover.md) — RECORD
- **[FoundationalValues and Creed — canonical design](foundational-values-and-creed.md)** — **AUTHORITY**: the only doc citable as "the design"
- **[FoundationalValues/creed program — delivery sequence](manifesto-program-delivery-sequence.md)** — **AUTHORITY** for sequencing
- [Creed and FoundationalValues — design as proposed](creed-and-values-design-as-proposed.md) — RECORD; operator input + measured corpus grounding
- [Creed and FoundationalValues — hardened design](creed-and-values-design-hardened.md) — RECORD; four-lens hardening round
- [Squad reports + measurements](squad-reports/index.md) — EVIDENCE; raw lens reports, measurements, and the [final verification round](squad-reports/review-round-2026-07-26.md)
- [Mission B (proposed scope) — Charter-mediated doctrine selection](mission-b-proposed-scope.md)
- [Org Doctrine Layer — Post-Implementation Architecture Review](org-doctrine-layer-architecture-review.md)
- [Runtime → Charter → Doctrine — boundary audit and recommendations](runtime-charter-doctrine-boundary.md)
- [WP-Prompt Governance Contract — ATDD Findings](wp-prompt-governance-atdd-findings.md)
- [Test Quality — test slicing & mocking-boundary discipline](test_quality/index.md)
- [Next doctrine slice (preliminary research) — wheel cutover, mission-type relocation, public API surface](next-slice-wheel-mission-types-public-api-research.md) — RECORD; pre-spec research, gap-flags a missing tracker issue for the public-API thread
- [#3179 doctrine public API surface — scoping brief](3179-public-api-surface-scoping.md) — EVIDENCE; reach-through inventory, facade gap map, lazy-import ratchet design, SonarCloud read, and the OpenAPI-does-not-apply decision

## Programme realization (2026-07-26 operator ruling)

The FoundationalValues/creed programme captured by the two AUTHORITY docs above was specced as a
single mission — `kitty-specs/doctrine-canonical-structure-remediation-01KYEYSD/` — then **split by
operator ruling into five sequenced missions**. `01KYEYSD` is the **programme record**: it is
specced, then split, and does **not** itself implement (its `tasks/` carries no work packages).

| Mission | Slug | Delivers |
| --- | --- | --- |
| A | `doctrine-silence-guards-01KYFV7Q` | Guards + campsite band: I19 zero-producer lint, occurrence-map field-path granularity, the four-site silent-kind-drop closure (I2), I3b/I3c `extra="forbid"` + writers + round-trip, I3a schema-generation CI wiring, layout/enum ratchets, followable guidance, org→DRG bridge fix, `applies` hygiene |
| B1 | `drg-relation-impacts-vocabulary-01KYFV87` | `Relation.IMPACTS` + `is_symmetric`, retires `in_tension_with`, re-points `consistency_check.py`. Delivers ADR [`2026-07-26-3`](../../adr/3.x/2026-07-26-3-impacts-edge-subsumes-in-tension-with.md) |
| B2 | `drg-edge-migration-extractor-retirement-01KYFV8C` | All 774 edges become authored; extractor edge production retired |
| C | `test-quality-doctrine-series-01KYFV8H` | The original #2935 deliverable: paradigm, DIRECTIVE_047, procedure, anti-patterns, assets, DIRECTIVE_041 intent split, CLI/CI validator parity |
| D | `foundational-values-creed-band-01KYFV8N` | Reachable creed band: I5, I9, I6, I13, I8, I1a, I16, I4-WP01–03, I10 |

**Mandatory order: A → B1 → B2 → C; D gates on A only.** The order is load-bearing (C-009/C-010),
not preference. Full increment→mission mapping, the two measurements that amended the ranked list,
and the D-2/D-3 rulings are recorded in
[`manifesto-program-delivery-sequence.md` § 10](manifesto-program-delivery-sequence.md#10-realization-amendment-2026-07-26).

## See also

- [Plans home](../../index.md)
