---
title: Investigations
description: Scope and compatibility investigations — issue analyses, schema-generation research, and mission review reports.
doc_status: draft
updated: '2026-08-30'
related:
- docs/plans/index.md
---
# Investigations

Standalone investigation and scope-assessment artifacts: issue analyses,
compatibility matrices, model-first schema research, and mission review
reports.

## Live investigations

Open designs and unshipped scope still worth consulting:

- [Issue #797: Events and Tracker Fork Census](issue-797-events-tracker-fork-census.md) —
  read-only ancestry, PyPI-source, and publication-workflow evidence for D6; recommends
  events 8.2.0 and tracker 0.5.2, and records the missing public tracker repository.
- [Write-path topology: ambient-location root cause and remediation options](write-path-topology-root-cause.md) —
  dialectic-squad-corroborated root cause for the #3129 defect class (14 issues); scoped
  remediation options for a future mission; rejects the batch-reparent/new-P0-epic action.
- [Review-artifact integrity (#3044): the topology-seam connection is historical, the open gap is a missing writer](review-artifact-write-integrity-3044.md) —
  dialectic-squad-corroborated finding that #2275's lane/coord read-side split is already fixed in
  code; the live gap in #3044's cluster is a missing approved-verdict writer plus a content-provenance
  validation gap, not a topology-seam extension.
- [Issue #1040 — ADRs as First-Class Primitive: Scope Inclusion Assessment](issue-1040-scope-assessment.md) —
  scope-inclusion assessment for #1040 (issue still **OPEN**; not yet shipped).
- [WP & Op Schema Model](wp-op-schema-model.md)
- [WP & Op Schema Model — Related Open Tracker Tickets](wp-op-schema-related-tickets.md)
- [WP Prompt & Ops Debrief — Model / Schema Proposal](wp-op-schema-proposal.md)
- [RFC #2497 — External Observability Endpoints: Squad Assessment](2497-external-observability-endpoints-assessment.md)

## Retired (shipped) records

The designs below shipped; the pages are retained as historical snapshots
(`doc_status: deprecated`, content preserved) and should not be consulted for
current behavior:

- [Mission-type step-model unification](mission-type-step-model-unification.md) —
  **retired**; shipped via ADR `2026-07-16-2` (#2658) + mission `templates-as-config-01KXMS1G`.
- [Mission Review Report: windows-compatibility-hardening-01KP5R6K](2026-04-14-windows-compatibility-hardening-mission-review.md) —
  **retired**; mission squash-merged as `89bab26e5`.
- [Mission-Next Compatibility Matrix](mission-next-compatibility.md) —
  **retired**; superseded by `shared-package-boundary-cutover-01KQ22DS` (ADR `2026-04-25-1`).
- [Model-First Schema Generation](model-first-schema-generation.md) —
  **retired**; shipped as the `scripts/generate_schemas.py` pipeline.
- [Scoping brief — #2684 task-move / runtime-state cluster](2684-task-move-cluster-scoping.md) —
  **retired**; shipped via ADR `2026-07-19-1` + mission `wp-runtime-state-eviction-01KXWN13`.
- [Feature spec — evict runtime-mutable WP state (#2684)](2684-task-move-cluster-spec.md) —
  **retired**; shipped via ADR `2026-07-19-1` + mission `wp-runtime-state-eviction-01KXWN13`.
- [WP Runtime-State Eviction — Prerequisite Mission Scope](wp-runtime-state-eviction-scope.md) —
  **retired**; shipped via ADR `2026-07-19-1` + mission `wp-runtime-state-eviction-01KXWN13`.
- [Issue #1111 Analysis — Branch Alignment Report](issue-1111-analysis.md) —
  **retired**; Epic #1111 closed COMPLETED (2026-06-02).
- [Fast-Follow Spec: Implement-Loop Friction Quick-Wins](loop-friction-fastfollow-spec.md) —
  **retired**; #2581 closed COMPLETED, shipped via mission `loop-reliability-ci-red-burndown-01KXWWD6`.

## See also

- [Plans home](../../index.md)
