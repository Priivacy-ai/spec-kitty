---
work_package_id: WP14
title: Golden-count conversion batch 3 — cli/auth/tasks & long tail
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
- T065
- T066
- T067
- T068
- T069
agent: "claude:sonnet:python-pedro:implementer"
history: []
agent_profile: python-pedro
authoritative_surface: tests/tasks/
create_intent: []
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- tests/audit/**
- tests/auth/**
- tests/tasks/**
- tests/missions/**
- tests/cross_cutting/**
- tests/docs/**
- tests/cli/**
- tests/doctor/**
- tests/core/**
- tests/characterization/**
- tests/kernel/**
- tests/policy/**
- tests/delivery/**
- tests/research/**
- tests/git_ops/**
- tests/event_journal/**
- tests/dashboard/**
- tests/context/**
- tests/ci/**
- tests/paths/**
- tests/init/**
- tests/e2e/**
- tests/cross_branch/**
- tests/concurrency/**
- tests/release/**
- tests/readiness/**
- tests/proof/**
- tests/mission_metadata/**
- tests/calibration/**
role: implementer
tags: []
shell_pid: "3237943"
shell_pid_created_at: "1783958502.54"
---

## ⚡ Do This First: Load Agent Profile

`/ad-hoc-profile-load python-pedro` (role: implementer). Then read [spec.md](../spec.md) FR-014,
[plan.md](../plan.md) §IC-14, WP07 (the exemplar), and **WP11's `../golden-count-inventory.md`** (the
directory-partitioned convert-set).

## Objective

Burn down the golden-count `convert`-set across the remaining clean directories (the long tail — ~250
candidate `len==int` sites before classification). Convert each `convert`-classified assertion to a
set/frozenset-equality; annotate `keep`-classified sites.

## Context — owned directories (all disjoint from every other WP)

`tests/audit`, `tests/auth`, `tests/tasks`, `tests/missions`, `tests/cross_cutting`, `tests/docs`,
`tests/cli`, `tests/doctor`, `tests/core`, `tests/characterization`, `tests/kernel`, `tests/policy`,
`tests/delivery`, `tests/research`, `tests/git_ops`, `tests/event_journal`, `tests/dashboard`,
`tests/context`, `tests/ci`, `tests/paths`, `tests/init`, `tests/e2e`, `tests/cross_branch`,
`tests/concurrency`, `tests/release`, `tests/readiness`, `tests/proof`, `tests/mission_metadata`,
`tests/calibration`.

**Boundary notes:** `tests/dashboard/**` is owned here (the `test_api_handler.py` twin is in the SEPARATE
`tests/test_dashboard/` dir, owned by WP08 — not this batch). `tests/cli/**` (not `tests/cli_gate`) is
owned. Many of these dirs have only 1–4 convert candidates; the exact set comes from WP11's inventory.

## Subtask guidance

- **T065 — pull the slice.** Extract the `convert` rows for the owned directories from
  `../golden-count-inventory.md`.
- **T066 — convert.** Replace `len(<collection>) == N` with the real set/frozenset/dict-equality contract
  (WP07 exemplar). Annotate genuine-cardinality `keep` sites with `# golden-count: cardinality-is-contract`.
- **T067 — decrement the baseline.** Reduce the `convert`-set baseline by this batch's converted count
  (strictly decreases; never regrows).
- **T068 — suites + guard green.** Run the owned-dir suites + `test_golden_count_ban.py` (`-n auto` is fine;
  the long tail is broad). Verify green.
- **T069 — gates + tracer.** `ruff`/`mypy` clean; append tracer rows.

## Branch Strategy

Lane C batch. Branches from WP11's tip; merges into `feat/test-suite-friction-remediation`. Parallel with
WP12/WP13 (directory-disjoint).

## Definition of Done (non-fakeable — NFR-002)

- [ ] Every `convert`-classified site in the owned dirs converted (or annotated `keep`).
- [ ] The `convert`-set baseline strictly decreased by this batch's count; never regrows.
- [ ] Owned-dir suites + `test_golden_count_ban.py` green.
- [ ] No file outside the owned directories was edited (esp. NOT `tests/test_dashboard/**`).
- [ ] `ruff` + `mypy` clean.
- [ ] **Tracer (FR-016):** append a catalog row for this batch's conversions + friction log.

## Risks

- **`tests/dashboard` vs `tests/test_dashboard`** — own only `tests/dashboard/**`; the api_handler twin is
  WP08's.
- **Broad surface, small per-dir counts** — the inventory keeps it bounded; do not scan-and-convert beyond
  the convert-set.

## Reviewer guidance

- Confirm the baseline decrement matches the conversion count and the guard is green.
- Confirm no edit landed in `tests/test_dashboard/**` or any non-owned directory.

## Activity Log

- 2026-07-13T16:02:18Z – claude:sonnet:python-pedro:implementer – shell_pid=3237943 – Assigned agent via action command
