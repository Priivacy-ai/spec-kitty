---
work_package_id: WP03
title: Coverage-scope reconciliation doc (research-first)
dependencies:
- WP02
requirement_refs:
- FR-003
- FR-004
tracker_refs: []
planning_base_branch: feat/sonar-qa-config-remediation
merge_target_branch: feat/sonar-qa-config-remediation
branch_strategy: Planning artifacts for this mission were generated on feat/sonar-qa-config-remediation. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/sonar-qa-config-remediation unless the human explicitly redirects the landing branch.
subtasks:
- T005
- T006
agent: "reviewer-renata"
shell_pid: "3199915"
history:
- Created for mission sonar-qa-config-remediation-01KWYCX7
agent_profile: curator-carla
authoritative_surface: docs/guides/
create_intent:
- docs/guides/coverage-signals.md
execution_mode: code_change
owned_files:
- docs/guides/coverage-signals.md
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile
Load your assigned profile (`curator-carla`) via `/ad-hoc-profile-load` before reading anything else.

## Objective
Determine whether SonarCloud's whole-repo `coverage` measures a **different file-set** than the internal `diff-coverage` gate, then document the reconciliation so a PR reviewer can tell an expected scope difference from a real regression (#2422). **FR-003, FR-004, C-002 (research-first).** Depends on WP02 (uses its tool).

## Context (grounded)
- Three things are colloquially "coverage": (1) internal `diff-coverage` gate (`.github/workflows/ci-quality.yml`, PR-only, `diff-cover` vs the union of `coverage-*.xml`, **per-PR-diff, critical-path-only, 90%**); (2) SonarCloud whole-repo `coverage` (~47%); (3) SonarCloud `new_coverage`.
- **Research-first (C-002)**: do NOT write a "scope alignment" code change unless a genuine `sources`/`exclusions` misconfiguration is found. A philosophy-only difference (whole-repo average vs per-PR-diff) is discharged by documentation.

## Guidance
**T005 — investigate (FR-003)**: using WP02's tool + the unauthenticated `GET /api/measures/component_tree?component=Priivacy-ai_spec-kitty&metricKeys=coverage`, enumerate the file set SonarCloud scores; compare against the internal gate's critical-path file list (read the `diff-cover` step config). Determine: do the **file sets** materially differ, or only the **threshold philosophy**? Record the evidence.
**T006 — document (FR-003/004)**: write `docs/guides/coverage-signals.md` — explain the three metrics, why they differ, and a short decision aid ("apparent discrepancy → is it a real regression or expected scope difference?"). State plainly which of file-set-vs-philosophy the investigation found. Reference it from where a PR reviewer meets the coverage signal (e.g. the testing/coverage guide index or the quality-gate context). If — and only if — a real `sources`/`exclusions` misconfig is found, note it + file a follow-up (do not fix Sonar config here unless trivial and in-scope).

## Definition of Done
- `docs/guides/coverage-signals.md` committed, accurate to the investigation, and discoverable (linked from the coverage/testing context).
- The note states whether file-sets or only philosophy differ, backed by evidence.
- No suppression/ratchet (NFR-002); terminology-guard clean (run `pytest tests/architectural/test_no_legacy_terminology.py`).

## Reviewer guidance
Confirm the doc's file-set-vs-philosophy claim matches the actual API evidence, that it's genuinely discoverable, and that no code "scope fix" was forced where docs are the honest answer (C-002).

## Activity Log

- 2026-07-07T15:02:11Z – curator-carla – shell_pid=3189427 – Assigned agent via action command
- 2026-07-07T15:12:10Z – curator-carla – shell_pid=3189427 – Coverage-signals reconciliation guide (FR-003/FR-004). Investigation: file-sets differ AND philosophy/baseline differ, but no sources/exclusions misconfig -> discharged by docs per C-002. Doc linked from Contributor guides index. Terminology guard clean.
- 2026-07-07T15:13:29Z – reviewer-renata – shell_pid=3199915 – Started review via action command
