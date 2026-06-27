---
work_package_id: WP04
title: Re-section docs/development + docs/engineering_notes per-file durable-vs-ephemeral (FR-012/#2054)
dependencies:
- WP03
requirement_refs:
- FR-001
- FR-012
tracker_refs: []
planning_base_branch: docs/2165-mission-b-structural-move
merge_target_branch: docs/2165-mission-b-structural-move
branch_strategy: Planning artifacts for this mission were generated on docs/2165-mission-b-structural-move. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into docs/2165-mission-b-structural-move unless the human explicitly redirects the landing branch.
subtasks:
- T021
- T022
- T023
- T024
- T025
- T026
agent: "claude:opus:reviewer-renata:reviewer"
history: []
agent_profile: python-pedro
authoritative_surface: docs/development
create_intent: []
execution_mode: code_change
owned_files:
- docs/development/*.md
- docs/development/**/*.md
- docs/engineering_notes/**
- docs/operations/**
- docs/guides/**
- docs/configuration/**
role: implementer
tags: []
shell_pid: "1491686"
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your agent profile: run `/ad-hoc-profile-load python-pedro` (or read `src/doctrine/agent_profiles/built-in/python-pedro.agent.yaml` and adopt it). State which directives apply, then proceed.

## Objective

Re-section the **existing `docs/development/` and `docs/engineering_notes/` subdirectories** (they have been `docs/` subdirs since January, not parallel roots) into the 13-section structure via a **per-file durable-vs-ephemeral classification** — **not** one mechanical directory move. This is IC-03b, which resolves the #2054 / FR-012 drift (the `docs/development/` durable-vs-ephemeral mixing). The **page-inventory `docs/development/3-2-page-inventory.yaml` STAYS PUT** (operator directive).

## Context

The plan (IC-03) and `occurrence_map.yaml` (`moves:` `docs/development` → `docs/operations`, `inventory_stays_put`) are explicit: each page is classified individually —
- **durable** dev/ops references → `docs/operations/` (or `guides/` / `configuration/` per Mission A's reconciliation ADR);
- **ephemeral** tracking/sprint docs → `docs/plans/` (distil-then-retire, `doc_status: draft|active`).

`/tasks` must enumerate the classification, not move the dir wholesale. The **EXCEPTION** is `docs/development/3-2-page-inventory.yaml` — a tooling artifact that stays at its path; the 4 lockfile constants (`inventory_lockfile.py` / `check_docs_freshness.py` / `version_leakage_check.py` / `_inventory.py`) are UNCHANGED. (`docs/plans/` itself is WP03-owned; this WP appends ephemeral pages into it — flag the overlap to the orchestrator: the two WPs write disjoint files under `docs/plans/`, sequenced WP03→WP04.)

## Requirement refs (hints for the orchestrator's map-requirements)

FR-001 (re-section the existing `docs/` subdirs into the 13-section structure), FR-012 (fold #2054: resolve the `docs/development/` durable-vs-ephemeral mixing + add to the issue-matrix + `Closes #2054`).

## Subtasks

### T021 — Enumerate + classify every `docs/development/` page
Produce a per-file classification table for every page under `docs/development/` (excluding the inventory yaml): each page → `{durable: operations|guides|configuration}` or `{ephemeral: plans}`.

**Apply these explicit decision rules (not bare judgment) so the classification is reproducible + auditable:**
- **Ephemeral → `plans/`** if the filename or content contains any of: `sprint`, `session`, `WP##`/`wp-`, `mission-<slug>`, a date-stamp tied to one effort, "status update", "tracking", "handoff", "scratch", or it narrates a one-time investigation / decision-in-progress.
- **Durable** if it is a runbook / deployment / on-call / incident procedure (**operations**), a how-to / tutorial / contributor workflow that outlives any one mission (**guides**), or a settings / env-var / toolchain / config reference (**configuration**).
- **Tie-breaker:** "would this page still be correct and useful two missions from now?" — yes → durable, no → ephemeral.

Record, per page, the **rule that fired** (not just the bucket) in the WP activity log / a scratch note, so the reviewer audits the *reason*.

### T022 — Classify `docs/engineering_notes/`
`docs/engineering_notes/` is investigations/traces → predominantly `docs/plans/` (distil-then-retire). Per `occurrence_map.yaml` `moves:` (`docs/engineering_notes` → `docs/plans`), re-section into `plans/` with `doc_status: draft|active`. Where a note carries a durable finding, flag it for the distil-then-retire lifecycle (the distillation itself is later; here just classify + place).

### T023 — Move durable pages → operations/guides/configuration
Relocate each page classified durable in T021 to its target section. Ensure each destination section carries an `index.md`. Keep the moves represented in `occurrence_map.yaml` `moves:` (or flag any new pair the map doesn't cover as an IC-01 gap — do not improvise outside the reviewed map).

### T024 — Move ephemeral pages → `docs/plans/`
Relocate the ephemeral pages into `docs/plans/` with the distil-then-retire `doc_status`. Coordinate with WP03 (which created `docs/plans/` and moved the `architecture/`-rooted plans) — write only the `docs/development`/`engineering_notes`-sourced files; do not touch WP03's plans content.

### T025 — Assert the inventory file STAYED PUT
Confirm `docs/development/3-2-page-inventory.yaml` is still at its original path and the 4 lockfile constants are unchanged. Add a regression guard (a tiny test or an assertion in the existing freshness test) that the inventory path is stable, so a future re-section can't silently move it.

### T026 — Verify the re-section + suite green
Confirm `docs/development/` now holds only durable dev pages that legitimately stay (and the inventory yaml); no ephemeral/tracking docs remain mis-filed. Run the terminology guard + `ruff` on any touched script. Record the #2054 resolution note for the issue-matrix (the orchestrator runs map-requirements; FR-012 wants `Closes #2054` on the PR).

## Surfaces & Loci

| Surface | Classification rule | Target |
|---------|---------------------|--------|
| `docs/development/**` (excl. inventory yaml) | durable dev/ops reference | `docs/operations/` (or `guides/`/`configuration/` per A's ADR) |
| `docs/development/**` (excl. inventory yaml) | ephemeral tracking/sprint | `docs/plans/` (distil-then-retire) |
| `docs/engineering_notes/**` | investigations/traces | `docs/plans/` (per `moves:`) |
| `docs/development/3-2-page-inventory.yaml` | tooling artifact | **STAYS PUT** (operator directive) |

Unchanged constants (operator directive): `inventory_lockfile.py`, `check_docs_freshness.py`, `version_leakage_check.py`, `_inventory.py`.

## Requirement → Subtask Traceability

| Requirement | Subtasks |
|-------------|----------|
| FR-001 (re-section existing `docs/` subdirs into 13-section) | T021, T022, T023, T024 |
| FR-012 (fold #2054: durable-vs-ephemeral + issue-matrix + `Closes #2054`) | T021, T025, T026 |

## Branch Strategy

Planning + final merge target: `docs/2165-mission-b-structural-move`. Depends on WP03 (the gating move). Parallel-eligible with WP05 (disjoint surfaces).

## Definition of Done

- [ ] Every `docs/development/` + `docs/engineering_notes/` page is **per-file classified** (durable→operations/guides/configuration; ephemeral→plans) — the classification table is auditable.
- [ ] `docs/development/3-2-page-inventory.yaml` **stayed put**; the 4 lockfile constants unchanged; a guard asserts the path is stable.
- [ ] #2054 drift resolved (no durable-vs-ephemeral mixing in `docs/development/`); recorded for the issue-matrix / `Closes #2054`.
- [ ] **Redirect/back-compat in place so no reference breaks**: every re-section move is represented in `occurrence_map.yaml` `moves:` (WP07 emits stubs); each destination section has `index.md`.
- [ ] Terminology guard + `ruff` clean.

## Risks & Reviewer Guidance

- **Wholesale dir move** is the failure mode FR-012 exists to prevent — reviewer must check the classification is per-file, not `mv docs/development docs/operations`.
- **Moving the inventory yaml** re-opens the freshness self-block — verify it stayed put (T025's guard).
- Overlap with WP03 under `docs/plans/`: confirm WP04 only added `development`/`engineering_notes`-sourced pages; no collision with WP03's `architecture/`-rooted plans.

## Activity Log

- (populated at implement time)
- 2026-06-27T13:37:41Z – claude:opus:python-pedro:implementer – shell_pid=1421969 – Assigned agent via action command
- 2026-06-27T14:18:35Z – claude:opus:python-pedro:implementer – shell_pid=1421969 – re-section: 2 ops/5 guides/2 config/34 ephemeral→plans + engineering_notes subtree (121 renames), auditable rule-fired table, inventory stayed put + regression guard, terminology/ruff/mypy clean
- 2026-06-27T14:18:49Z – claude:opus:reviewer-renata:reviewer – shell_pid=1491686 – Started review via action command
- 2026-06-27T14:23:23Z – user – shell_pid=1491686 – Review passed: per-file classification sound (spot-checked 9: ssh-deploy-keys/identity-boundary-ci-gate->operations, testing-flakiness->guides, yaml-libraries/linting-cutoff-policy->configuration + 4 tie-breakers), 4 tie-breakers RATIFIED ephemeral->plans (version-taxonomy mission-tied w/ SSOT in data-model, ci-coverage-gate branch-tied, model-first dated/PR-tied, quality_check_structure narrates one-time change while durable linting-cutoff-policy correctly split to configuration), 121 renames all R100 byte-preserved (0 delete+recreate), inventory STAYED PUT + guard green (5 passed) + 4 lockfile modules untouched, engineering_notes->plans/engineering-notes disjoint from WP03, no WP03-plans collision, terminology guard green, ruff clean, #2054 resolution recorded for issue-matrix
