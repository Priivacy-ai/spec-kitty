---
work_package_id: WP01
title: Surface-resolution audit (read-only inventory)
dependencies: []
requirement_refs:
- FR-003
tracker_refs: []
planning_base_branch: feat/single-mission-surface-resolver
merge_target_branch: feat/single-mission-surface-resolver
branch_strategy: Planning artifacts for this mission were generated on feat/single-mission-surface-resolver. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/single-mission-surface-resolver unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "1517028"
history:
- at: '2026-06-19T17:06:54Z'
  actor: claude
  note: WP authored from plan IC-02 (FR-003).
agent_profile: python-pedro
authoritative_surface: tests/architectural/surface_resolution_audit/
create_intent:
- tests/architectural/surface_resolution_audit/audit.py
- tests/architectural/surface_resolution_audit/RULESET.md
- tests/architectural/surface_resolution_audit/inventory.md
- tests/architectural/surface_resolution_audit/audited-surfaces.md
execution_mode: code_change
model: claude-sonnet-4-6
owned_files:
- tests/architectural/surface_resolution_audit/**
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Load your assigned profile: read `src/doctrine/agent_profiles/built-in/python-pedro.agent.yaml` and adopt it; acknowledge its initialization declaration.

## Objective

Repoint the merged 01KVFTFV audit AST walker (`tests/architectural/untrusted_path_audit/audit.py`) to enumerate every **mission-surface-resolution** callsite in `src/specify_cli` + `src/mission_runtime`, classifying each `routed-through-resolver` / `topology-blind-by-design` / `raw-bypass`. Read-only — no `src/` changes. This inventory scopes WP06 (collapse), WP07 (shim migration), and WP08 (guard). (IC-02; FR-003)

## Context

- The mission collapses the coord-vs-primary **selection** resolvers to one canonical owner (`coordination/surface_resolver.resolve_status_surface_with_anchor`).
- Reuse the 01KVFTFV walker machinery (C-001): same AST approach, one-hop aliasing, recorded ruleset, self-asserting tripwire.
- Resolution entry points (the "routed-through-resolver" set): `missions/_read_path_resolver.py` (`resolve_mission_read_path`, `primary_feature_dir_for_mission`, `candidate_feature_dir_for_mission`), `coordination/surface_resolver.py`, `status/aggregate.py` (`_resolve_read_dir`, `_find_meta_path`), `mission_runtime/resolution.py`, and `coordination/status_transition.py` coord predicates (#1900).

## Subtasks

### T001 — Repoint the walker to surface resolution
- Adapt the audit script into `tests/architectural/surface_resolution_audit/audit.py`. Seed-set: callsites that produce a **mission-surface directory** from a handle/slug. Sink predicate: a `repo_root|root / KITTY_SPECS_DIR / <slug>`-style join OR a call to a known resolver. Follow one-hop aliasing. Record the seed-set + predicate in `RULESET.md` with a "known false-negative classes" section.

### T002 — Classify each callsite
- `routed-through-resolver` — goes through the canonical resolver or a blessed delegator (cite it).
- `topology-blind-by-design` — deliberately primary-only (e.g. meta.json reads) — legitimate, not a desync. NAME why.
- `raw-bypass` — composes the path itself, bypassing the resolver. These are FR-001 targets.
- Do NOT flag the `WorktreeTopology`/`classify_worktree_topology`/`read_worktree_registry` machinery (correct git-registry authority — out of scope).

### T003 — Emit inventory + self-assert
- Write `inventory.md` (table: `file:line | handle source | sink | disposition | rationale`). `audit.py` self-asserts count consistency + **known-candidate presence**: every known resolver file (`_read_path_resolver.py`, `surface_resolver.py`, `aggregate.py`, `status_transition.py`, `mission_runtime/resolution.py`, `feature_dir_resolver.py`) appears. Exit non-zero if any is missing. `python tests/architectural/surface_resolution_audit/audit.py` → exit 0.

### T004 — Audited-surface list for WP08
- Produce `audited-surfaces.md` — the stable list WP08's guard anchors on (the routed-through-resolver + raw-bypass surfaces).

## Branch Strategy

Planning/base + merge target: `feat/single-mission-surface-resolver` (→ main via PR; flattened). Execution worktree per `lanes.json` lane at implement time.

## Definition of Done

- [ ] `audit.py` + `RULESET.md` committed under `tests/architectural/surface_resolution_audit/`; re-run reproduces the inventory.
- [ ] Every callsite has one disposition with rationale; known resolver files all present (machine-asserted).
- [ ] `topology-blind-by-design` rows justified; `WorktreeTopology` machinery not flagged.
- [ ] `audited-surfaces.md` produced for WP08.
- [ ] No `src/` modified; ruff + mypy clean on the audit tooling.

## Risks / Reviewer guidance
- **Risk**: misclassifying a legitimate primary-only read as raw-bypass. The disposition must name the source provenance.
- **Reviewer**: re-run the audit; spot-check 3 dispositions; confirm all known resolver files are in the inventory.

## Activity Log

- 2026-06-19T17:31:05Z – claude:sonnet:python-pedro:implementer – shell_pid=1484277 – Assigned agent via action command
- 2026-06-19T17:44:21Z – claude:sonnet:python-pedro:implementer – shell_pid=1484277 – Audit module ready for review
- 2026-06-19T17:47:10Z – claude:sonnet:python-pedro:implementer – shell_pid=1484277 – Audit complete on lane-a (811c40414); lane kitty-specs aligned to mission branch
- 2026-06-19T17:47:19Z – claude:opus:reviewer-renata:reviewer – shell_pid=1517028 – Started review via action command
- 2026-06-19T17:52:21Z – user – shell_pid=1517028 – reviewer-renata APPROVED on merits: tripwire bites (3 mutations verified), 5 dispositions spot-checked vs source, primary_feature_dir correctly topology-blind, ruff+mypy clean. Issue-matrix verdicts now resolved.
