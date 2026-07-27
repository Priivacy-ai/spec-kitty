---
work_package_id: WP05
title: Allowlist reconciliation + grandfathered-legacy burndown
dependencies:
- WP18
requirement_refs:
- FR-002
- FR-004
- FR-016
- NFR-001
- NFR-002
tracker_refs:
- '2559'
- '2293'
planning_base_branch: feat/test-suite-friction-remediation
merge_target_branch: feat/test-suite-friction-remediation
branch_strategy: Planning artifacts for this mission were generated on feat/test-suite-friction-remediation. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/test-suite-friction-remediation unless the human explicitly redirects the landing branch.
subtasks:
- T019
- T020
- T021
- T022
- T023
agent: "claude:opus:reviewer-renata:reviewer"
history: []
agent_profile: python-pedro
authoritative_surface: tests/architectural/test_no_dead_symbols.py
create_intent: []
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- tests/architectural/test_no_dead_symbols.py
- tests/architectural/_baselines.yaml
role: implementer
tags: []
shell_pid: "3988808"
shell_pid_created_at: "1783977060.38"
---

## ⚡ Do This First: Load Agent Profile

`/ad-hoc-profile-load python-pedro` (role: implementer). Then read [spec.md](../spec.md) FR-002/FR-004 +
NFR-001, [plan.md](../plan.md) §IC-03, and [data-model.md](../data-model.md) E-02. This WP is the **sole
owner** of `test_no_dead_symbols.py` and lands **last** in the Lane-0 serial chain (rebases on WP01's gate
tooling + WP02's deletions + WP03/WP04's repointing).

## Objective

Reconcile the dead-code allowlist now that the gate (WP01) sees dynamic access and the delegates (WP02) are
gone: (1) remove the 4 `runtime_bridge` façade rows that were only present because the gate was blind; (2)
burn down the `category_b_grandfathered_legacy` subset that WP01 reclassifies as genuinely dead. The
allowlist count **decreases from baseline 193** but **MUST NOT reach 0** — live-by-dynamic-access and
load-bearing `doctrine.*` re-exports stay.

## Context

- Baseline allowlist count is **193** (not the historical 237 — see data-model E-02 / spec FR-004).
- The 4 façade rows to remove: `get_or_start_run`, `query_current_state`, `answer_decision_via_runtime`,
  `QueryModeValidationError` (FR-002).
- `category_b_grandfathered_legacy` holds a mix: genuinely-dead (removable), live-by-dynamic-access (keep),
  and load-bearing `doctrine.*` re-exports (keep). Only the genuinely-dead subset — proven dead by the WP01
  gate now that WP02 deleted the delegates — is removed.

## Subtask guidance

- **T019 — remove the 4 façade rows.** Delete the 4 `runtime_bridge` façade allowlist entries; the WP01
  gate now recognises them as live via dynamic access, so they pass reachability without a row (FR-002).
- **T020 — grandfathered burndown.** For each `category_b_grandfathered_legacy` entry, check the WP01 gate's
  classification: if the symbol is now genuinely dead (its delegate was deleted in WP02 and no live caller
  remains), remove the row AND confirm the symbol itself is gone (`git grep <symbol>` = 0). Keep every entry
  that is live-by-dynamic-access or a load-bearing `doctrine.*` re-export.
- **T021 — single baseline recount (both baselines — WP05 is the sole reconciler).** Update the dead-code
  allowlist count once, downward from 193 — it must strictly decrease and remain > 0 (over-deletion of a
  live `doctrine.*` re-export is the failure mode). Then reconcile the **second** baseline: the
  `category_b_grandfathered_legacy: 193` count in `tests/architectural/_baselines.yaml` (~L225, consumed by
  `test_ratchet_baselines.py`). Removing allowlist rows drops the observed count below 193 and reds that
  ratchet, so update `category_b_grandfathered_legacy` down from 193 to the post-burndown count. The count
  settles **here** — after WP02's src deletions and WP05's burndown — so WP05 is the single reconciler of
  `_baselines.yaml`; no other WP touches it.
- **T022 — non-fakeable DoD.** `.venv/bin/python -m pytest tests/architectural/test_no_dead_symbols.py -q`
  green; for every removed symbol, `git grep <symbol>` across `src` and `tests` returns 0.
- **T023 — gates + tracer.** `ruff`/`mypy` clean; append tracer catalog rows.

## Branch Strategy

Branches from WP04's tip — **last in the Lane-0 serial chain**; merges into
`feat/test-suite-friction-remediation`.

## Definition of Done (non-fakeable — NFR-002)

- [ ] The 4 `runtime_bridge` façade rows removed; they pass reachability as recognised-live (FR-002).
- [ ] The genuinely-dead `category_b_grandfathered_legacy` subset removed; live-by-dynamic-access and
      load-bearing `doctrine.*` re-exports **retained**.
- [ ] Allowlist baseline recount is a strict **decrease** from 193 and is **> 0** (FR-004).
- [ ] Update `category_b_grandfathered_legacy` in `tests/architectural/_baselines.yaml` down from 193 to the
      post-burndown count; `test_ratchet_baselines.py` green.
- [ ] Dead-code gate **green** on the real tree.
- [ ] For every removed symbol: `git grep <symbol>` = 0 across `src` and `tests` (deshim-delete evidence).
- [ ] `ruff` + `mypy` clean.
- [ ] **Tracer (FR-016):** append catalog rows for the dead-code/grandfathered ratchet (invariant-vs-shape,
      CaaCS churn, keep/consolidate/retire verdict) to `../tracer-design-decisions.md` + friction log.

## Risks

- **Over-deletion of a live `doctrine.*` re-export** — the count must decrease but not reach 0; each removal
  is gated on the WP01 gate proving deadness AND `git grep` = 0.
- **Racing the baseline** — exactly one recount; do not leave the baseline number and the actual row set
  disagreeing.

## Reviewer guidance

- Confirm the count strictly decreased from 193 and is > 0.
- Confirm every removed row corresponds to a symbol with `git grep` = 0, and no `doctrine.*` re-export was
  dropped.

## Activity Log

- 2026-07-13T21:30:41Z – claude – shell_pid=3988808 – Overlay wired into _imports_by_target + 4 façade rows removed ATOMICALLY (bc8b6bada); allowlist 317→313; gate 24/24 green. Grandfathered burndown: 0 removable (dangling=0/stale=0 mechanical audit; WP02 re-scoped to 0-delete so no dead material) — refused to fabricate decrease; FR-004 premise dissolved by re-seq. ruff/mypy clean. Force: lane planning/status-behind only.
- 2026-07-13T21:30:48Z – claude:opus:reviewer-renata:reviewer – shell_pid=3988808 – Review claim
- 2026-07-13T21:35:11Z – claude:opus:reviewer-renata:reviewer – shell_pid=3988808 – APPROVE (reviewer-renata/opus): atomic wire+remove (bc8b6bada, single commit); wiring load-bearing (4 façade names only reachable via next_cmd call-bound accessor invisible to static AST — un-wire would red); zero-grandfathered-burndown SOUND (traced Mission/Severity/AcceptanceMode live; WP18's 8 deletions non-eligible privates; dangling=0/stale=0); baseline honest (ratchet doesn't validate category_b key); allowlist 317→313; 27 passed. FR-004 burndown premise dissolved by re-seq — evidence-backed, not skipped.
