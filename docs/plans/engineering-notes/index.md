---
title: Engineering notes
description: 'Internal engineering notes for Spec Kitty: runtime and state overhaul, surface-resolution clusters, triage logs, architectural reviews, and reflections.'
doc_status: draft
updated: '2026-06-27'
related:
- docs/plans/engineering-notes/architectural-review/README.md
- docs/plans/engineering-notes/finding/README.md
- docs/plans/engineering-notes/reflections/README.md
- docs/plans/engineering-notes/runtime_and_state_overhaul/README.md
- docs/plans/engineering-notes/triage/README.md
- docs/plans/index.md
---
# Engineering notes

Internal engineering material organized into topic clusters. These notes capture
in-flight design work, investigations, and triage; they are working artifacts for
maintainers rather than end-user documentation.

## Clusters

- [Runtime and state overhaul](runtime_and_state_overhaul/README.md) — unifying mission execution context and state.
- [Triage](triage/README.md) — investigation and triage logs.
- [Architectural review](architectural-review/README.md) — design reviews and findings.
- [Findings](finding/README.md) — recorded engineering findings.
- [Reflections](reflections/README.md) — retrospective engineering reflections.
- [Test-suite parallelization — CI shard topology status](testing-parallel-ci-topology-status.md) — point-in-time mission-status snapshot of the CI shard-topology re-flip, carved out of the durable `testing-parallel.md` how-to.

Additional clusters cover infra/logic separation (`2173-infra-logic-separation/`),
surface-resolution work (`3-2-3-surface-resolution-cluster/`), naming/identity SSOT
(`naming-identity-ssot-strangler/`), transient mission-scoped classifications
([mission notes](mission-notes/index.md)), and a preserved historical mission closeout
([01KSMG8Y — Pre-Doctrine Test Stabilization](01KSMG8Y-closeout/index.md)).

## Field reports

Maintainer-facing narratives of a full run under the doctrine — process, operator decisions,
and where the charter/ADRs/guides changed the outcome:

- [Doctrine-driven P0 remediation, end to end (2026-07-18)](2026-07-18-doctrine-driven-p0-remediation-field-report.md) — remediating the merge-core P0 pair #2709/#2711 and fast-follow #2786; what the adversarial-squad cadence and the red-main / tracker-hygiene / seam docs actually bought.

## Closing reports

One-time mission closeout records — final checks, disposition tables, and follow-up issue filings
for a completed mission:

- [Docs IA & Onboarding Overhaul — Terminology Sweep & Closing Report](terminology-sweep-report.md) — WP10's closing record for mission `docs-ia-onboarding-overhaul-01KY02JB`: the mission-wide terminology/glossary sweep, NFR-005 Divio frontmatter coverage check, and follow-up issue filing.

## Pre-spec research

Durable records of profile-loaded pre-spec research squads, captured so a parked mission can
resume without re-running the squad:

- [DRG completeness (#2843 / #2847) — pre-spec research squad findings](drg-completeness-2843-research.md) — convergent 4-lens findings on the #2833 residue: relation-description parity, the activation-gate latent bug, and the anti-pattern corpus promotion split.
## Docs governance

Docs-wide structural baselines and concern audits — the durable record of where each doc kind
belongs and what has drifted, replacing the retired anti-sprawl ratchet:

- [Common-Docs section audit (docs-wide structural concern baseline)](common-docs-section-audit.md) — post-#2851 concern-bucket audit of every `docs/` section (excl. `development/` + `guides/`): misfiled files, redistribution tally, follow-up ticket proposals under #2314 bucket C, and the taxonomy recommendation for #2302.

## Design notes

Durable design investigations that inform a convention or a future mission:

- [Agent knowledge: canonical homes](agent-knowledge-canonical-homes.md) — where rules (charter), practices (doctrine), reference (Common Docs), and learned facts (`.kittify/memory/`) belong; how to stop a per-agent memory duplicating the repo.
- [Coord-branch bookkeeping: read/write split-brain root-cause](coord-splitbrain-rootcause.md) — #2841 drift is unenforced write-placement (writers pick their own dir), not a broken partition contract; the single placement-port seam that makes wrong-partition writes unrepresentable at commit.
- [Coordination-branch trust & reconciliation model — mission scope](coord-trust-mission-scope.md) — the pre-spec scope for the coord-trust friction-remediation mission: Gap-1 staleness, Symptom-B gate exemption, and why reconciliation is a minimized fail-loud residual, not the centerpiece.

## See also

- [Documentation home](../index.md)
- [Development notes](../../development/index.md)
