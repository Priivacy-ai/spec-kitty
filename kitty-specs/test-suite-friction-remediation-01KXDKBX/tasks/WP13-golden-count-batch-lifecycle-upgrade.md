---
work_package_id: WP13
title: Golden-count conversion batch 2 — lifecycle & upgrade
dependencies:
- WP11
requirement_refs:
- FR-014
- FR-016
- NFR-002
tracker_refs:
- '2076'
planning_base_branch: feat/test-suite-friction-remediation
merge_target_branch: feat/test-suite-friction-remediation
branch_strategy: Planning artifacts for this mission were generated on feat/test-suite-friction-remediation. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/test-suite-friction-remediation unless the human explicitly redirects the landing branch.
subtasks:
- T060
- T061
- T062
- T063
- T064
agent: "claude:sonnet:python-pedro:implementer"
history: []
agent_profile: python-pedro
authoritative_surface: tests/upgrade/
create_intent: []
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- tests/upgrade/**
- tests/dossier/**
- tests/lanes/**
- tests/migration/**
- tests/migrate/**
- tests/post_merge/**
- tests/merge/**
- tests/coordination/**
- tests/review/**
role: implementer
tags: []
shell_pid: "3237943"
shell_pid_created_at: "1783958502.54"
---

## ⚡ Do This First: Load Agent Profile

`/ad-hoc-profile-load python-pedro` (role: implementer). Then read [spec.md](../spec.md) FR-014,
[plan.md](../plan.md) §IC-14, WP07 (the exemplar), and **WP11's `../golden-count-inventory.md`** (the
directory-partitioned convert-set — your file/line set comes from there).

## Objective

Burn down the golden-count `convert`-set in `tests/upgrade/**`, `tests/dossier/**`, `tests/lanes/**`,
`tests/migration/**`, `tests/migrate/**`, `tests/post_merge/**`, `tests/merge/**`, `tests/coordination/**`,
`tests/review/**` (~262 candidate `len==int` sites before classification). Convert each `convert`-classified
assertion to a set/frozenset-equality; leave `keep`-classified sites untouched (annotate them).

## Context

- These directories are **disjoint** from every other WP's owned files. `tests/review` (not `tests/reviews`)
  is owned here; `tests/reviews` has no convert candidates and is not owned by this batch.
- The exact convert-set for these dirs is defined by WP11's inventory.

## Subtask guidance

- **T060 — pull the slice.** Extract the `convert` rows for the owned directories from
  `../golden-count-inventory.md`.
- **T061 — convert.** Replace `len(<collection>) == N` with the real set/frozenset/dict-equality contract
  (WP07 exemplar shape). Annotate genuine-cardinality `keep` sites with
  `# golden-count: cardinality-is-contract` instead of converting.
- **T062 — decrement the baseline.** Reduce the `convert`-set baseline by this batch's converted count
  (strictly decreases; never regrows).
- **T063 — suites + guard green.**
  `.venv/bin/python -m pytest tests/upgrade tests/dossier tests/lanes tests/migration tests/migrate tests/post_merge tests/merge tests/coordination tests/review tests/architectural/test_golden_count_ban.py -q`.
- **T064 — gates + tracer.** `ruff`/`mypy` clean; append tracer rows.

## Branch Strategy

Lane C batch. Branches from WP11's tip; merges into `feat/test-suite-friction-remediation`. Parallel with
WP12/WP14 (directory-disjoint).

## Definition of Done (non-fakeable — NFR-002)

- [ ] Every `convert`-classified site in the owned dirs converted (or annotated `keep`).
- [ ] The `convert`-set baseline strictly decreased by this batch's count; never regrows.
- [ ] Owned-dir suites + `test_golden_count_ban.py` green.
- [ ] No file outside the owned directories was edited.
- [ ] `ruff` + `mypy` clean.
- [ ] **Tracer (FR-016):** append a catalog row for this batch's conversions + friction log.

## Risks

- **Converting a genuine cardinality assertion** — trust WP11's `keep` classification.
- **`tests/review` vs `tests/reviews`** — own only `tests/review/**`.

## Reviewer guidance

- Confirm the baseline decrement matches the conversion count and the guard is green.
- Confirm no drift outside the owned directories.

## Activity Log

- 2026-07-13T16:02:05Z – claude:sonnet:python-pedro:implementer – shell_pid=3237943 – Assigned agent via action command
