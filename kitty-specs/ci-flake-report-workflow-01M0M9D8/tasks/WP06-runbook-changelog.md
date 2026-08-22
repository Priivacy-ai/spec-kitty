---
work_package_id: WP06
title: 'Runbook + changelog: draft/ready contract and green-before-RFR'
dependencies:
- WP04
- WP05
requirement_refs:
- FR-013
- C-001
planning_base_branch: qa/test-hardening
merge_target_branch: qa/test-hardening
branch_strategy: Planning artifacts for this mission were generated on qa/test-hardening. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into qa/test-hardening unless the human explicitly redirects the landing branch.
subtasks:
- T021
- T022
- T023
history: []
agent_profile: curator-carla
authoritative_surface: docs/development/
create_intent:
- docs/development/ci-draft-ready.md
execution_mode: code_change
owned_files:
- docs/development/ci-draft-ready.md
- CONTRIBUTING.md
- CHANGELOG.md
tags: []
tracker_refs: []
---

# WP06 — Runbook + changelog

**Capability B** · profile: curator-carla · deps: WP04, WP05 · refs: FR-013, C-001

## Objective

Document the draft/ready CI contract for contributors and agents, and record the mission in the changelog. (C-001 forbids wiring the flake-report *findings* into docs — this WP documents the CI *contract*, which is allowed.)

## Subtasks

- **T021 — Runbook (`docs/development/ci-draft-ready.md`).** Explain: draft = fail-fast (canceller stops the chain on first failure → quick iteration); ready = full **relevant** signal (diff-relevant chains run to completion; untouched domains stay path-filtered out); red-first re-run; and the rule: **monitor a draft run until all jobs conclude `success` before flipping to ready-for-review** (a red draft run is inherently partial by design). Note the merge-gate is preserved in both modes.
- **T022 — CONTRIBUTING pointer.** Add a short "Draft vs ready CI" subsection (or link) in `CONTRIBUTING.md` pointing agents/contributors to the runbook and the green-before-RFR rule (SC-006 discoverability).
- **T023 — CHANGELOG.** Add an entry for the mission (flake-report workflow + draft/ready CI mode + red-first). Follow the repo changelog format.

## Done when

Runbook exists and states the contract + green-before-RFR rule; CONTRIBUTING points to it; CHANGELOG entry added; terminology guard (`test_no_legacy_terminology.py`) green for the prose.
