---
work_package_id: WP15
title: 'B-only meta routing: migration + audit + matrix; m_0_13_* deferral'
dependencies: []
requirement_refs:
- FR-005
- FR-006
tracker_refs: []
planning_base_branch: design/read-surface-ssot-closeout
merge_target_branch: design/read-surface-ssot-closeout
branch_strategy: Planning artifacts for this mission were generated on design/read-surface-ssot-closeout. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into design/read-surface-ssot-closeout unless the human explicitly redirects the landing branch.
subtasks:
- T043
- T044
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "3195824"
history:
- at: '2026-07-08T06:52:05+00:00'
  actor: planner
  action: created
agent_profile: python-pedro
authoritative_surface: src/specify_cli/
create_intent: []
execution_mode: code_change
owned_files:
- src/specify_cli/migration/backfill_identity.py
- src/specify_cli/migration/backfill_topology.py
- src/specify_cli/migration/mission_state.py
- src/specify_cli/migration/rebuild_state.py
- src/specify_cli/audit/classifiers/meta.py
- src/specify_cli/audit/detectors.py
- src/specify_cli/acceptance/matrix.py
- src/specify_cli/upgrade/migrations/m_0_13_0_research_csv_schema_check.py
- src/specify_cli/upgrade/migrations/m_0_13_5_add_commit_workflow_to_templates.py
- src/specify_cli/upgrade/migrations/m_0_13_8_target_branch.py
- src/specify_cli/upgrade/migrations/m_2_0_6_consistency_sweep.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Load `/ad-hoc-profile-load` for `python-pedro`. Read `spec.md` (FR-005, FR-006, Out of Scope),
`plan.md` (IC-05). **Append to `traces/*.md`.**

## Objective

Route the B-only meta reads in `migration/*` (non-`m_0_13_*`), `audit/*`, and `acceptance/matrix.py`.
**Defer ONLY `m_0_13_*` per-entry** (allow-list, rationale + filed issue) — no wholesale `migration/`
path-exclude.

## Context

- **In scope (route them):** `migration/backfill_identity.py`, `backfill_topology.py`,
  `mission_state.py`, `rebuild_state.py` — the spec's Out-of-Scope explicitly says these are
  #2100-in-scope (NOT blanket-deferred). Also `m_2_0_6_consistency_sweep.py`.
- **Deferred (`m_0_13_*` only):** the historical-fixture-sensitive migrations
  (`m_0_13_0_*`, `m_0_13_5_*`, `m_0_13_8_*`) — byte-exact risk. Do NOT route; instead each becomes an
  IC-06 allow-list entry (WP16) carrying a rationale AND a filed follow-up issue number (not a prose
  note, not a path-exclude). File the follow-up issue(s) and record the number(s).
- **`acceptance/matrix.py`** is the Thread-B leg of the acceptance package 3-way — file-granular
  ownership (accept.py=WP02, __init__.py=WP09, matrix.py=here).
- Per-site POST-#2091 contract (FR-005).

## Subtasks

### T043 — Route migration (non-m_0_13) + audit + matrix
Route `backfill_identity.py`, `backfill_topology.py`, `mission_state.py`, `rebuild_state.py`,
`m_2_0_6_consistency_sweep.py`, `audit/classifiers/meta.py`, `audit/detectors.py`,
`acceptance/matrix.py` meta reads onto `load_meta*` (post-#2091).

### T044 — m_0_13_* deferral (allow-list + issue)
For each `m_0_13_*` site: do NOT route. File a follow-up tracker issue (byte-exact migration risk),
and prepare the allow-list entry (`{key, rationale, issue}`) that WP16's gate will carry. Record the
issue number(s) in `traces/design-decisions.md`. **No `migration/` path-exclude.**

## Branch Strategy
Planning + merge target: `design/read-surface-ssot-closeout`. `spec-kitty agent action implement WP15 --agent <name>`.

## Definition of Done
- [ ] backfill_* / mission_state / rebuild_state / m_2_0_6 / audit / matrix routed (post-#2091).
- [ ] m_0_13_* deferred per-entry with rationale + FILED issue number (no path-exclude).
- [ ] acceptance/matrix.py file-granular; ruff/mypy clean; tracer updated.

## Reviewer guidance (opus)
Confirm backfill_*/mission_state/rebuild_state were ROUTED (not deferred). Confirm m_0_13_* deferrals
each carry a filed issue number. Verify no wholesale migration/ path-exclude.

## Activity Log

- 2026-07-08T08:39:51Z – claude:sonnet:python-pedro:implementer – shell_pid=3008345 – Assigned agent via action command
- 2026-07-08T08:58:50Z – claude:sonnet:python-pedro:implementer – shell_pid=3008345 – Ready for review: routed backfill_identity/backfill_topology/rebuild_state/audit-meta-classifier meta.json reads onto load_meta*; m_0_13_* deferred with filed follow-up issues #2477/#2478/#2479 for WP16 allow-list; 2252 tests pass, ruff+mypy clean.
- 2026-07-08T09:00:16Z – claude:opus:reviewer-renata:reviewer – shell_pid=3195824 – Started review via action command
- 2026-07-08T09:08:13Z – user – shell_pid=3195824 – Review passed: 6 migration/audit meta reads routed post-#2091 (backfill_identity x2, backfill_topology x2, rebuild_state via load_meta_or_empty, audit/classifiers/meta.py); lookalikes correctly excluded (mission_state already load_meta-compliant, detectors=JSONL-line parse, matrix=acceptance-matrix.json+existence-check, m_2_0_6 via load_feature_meta->load_meta); m_0_13_* deferred per-entry (0 commits) with filed OPEN issues #2477/#2478/#2479 on Priivacy-ai/spec-kitty, no path-exclude; error-detail text 'top-level JSON value must be an object' preserved via exc.__cause__ disambiguation (test_audit_classifiers L204 passes); 2086 passed/1 skipped, ruff+mypy clean
