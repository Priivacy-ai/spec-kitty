---
work_package_id: WP12
title: Golden-count conversion batch 1 — doctrine & charter
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
- T055
- T056
- T057
- T058
- T059
agent: "claude:sonnet:python-pedro:implementer"
history: []
agent_profile: python-pedro
authoritative_surface: tests/charter/
create_intent: []
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- tests/charter/**
- tests/doctrine/**
- tests/doctrine_synthesizer/**
- tests/glossary/**
role: implementer
tags: []
shell_pid: "3237943"
shell_pid_created_at: "1783958502.54"
---

## ⚡ Do This First: Load Agent Profile

`/ad-hoc-profile-load python-pedro` (role: implementer). Then read [spec.md](../spec.md) FR-014,
[plan.md](../plan.md) §IC-14, WP07 (the exemplar conversion), and **WP11's `../golden-count-inventory.md`**
(the directory-partitioned convert-set — your exact file/line set comes from there, not from a fresh scan).

## Objective

Burn down the golden-count `convert`-set in this batch's owned directories: `tests/charter/**`,
`tests/doctrine/**`, `tests/doctrine_synthesizer/**`, `tests/glossary/**` (~261 candidate `len==int` sites
before classification). Convert each `convert`-classified assertion to a set/frozenset-equality that
expresses the real contract; leave `keep`-classified (cardinality-is-contract) sites untouched.

## Context

- These directories are **disjoint** from every other WP's owned files (verified during planning). No
  Lane-0/A/B file lives here.
- The exact convert-set for these dirs is defined by WP11's inventory. If WP11 flagged a convert-site inside
  a dir owned by another WP, it is NOT in scope here.

## Subtask guidance

- **T055 — pull the slice.** From `../golden-count-inventory.md`, extract the `convert` rows for
  `tests/charter/**`, `tests/doctrine/**`, `tests/doctrine_synthesizer/**`, `tests/glossary/**`.
- **T056 — convert.** For each, replace `len(<collection>) == N` with the set/frozenset/dict-equality that
  is the real contract (following WP07's exemplar shape). For genuine cardinality assertions the inventory
  marked `keep`, add the `# golden-count: cardinality-is-contract` annotation instead of converting.
- **T057 — decrement the baseline.** Reduce the `convert`-set baseline by the number converted in this
  batch. The baseline must **strictly decrease** and never regrow.
- **T058 — suites + guard green.** Run the owned-dir suites + the recurrence guard:
  `.venv/bin/python -m pytest tests/charter tests/doctrine tests/doctrine_synthesizer tests/glossary tests/architectural/test_golden_count_ban.py -q`.
- **T059 — gates + tracer.** `ruff`/`mypy` clean; append tracer rows.

## Branch Strategy

Lane C batch. Branches from WP11's tip (inventory dependency); merges into
`feat/test-suite-friction-remediation`. Parallel with WP13/WP14 (directory-disjoint).

## Definition of Done (non-fakeable — NFR-002)

- [ ] Every `convert`-classified site in the owned dirs converted to a set/frozenset/dict-equality (or
      annotated `keep`).
- [ ] The `convert`-set baseline strictly decreased by this batch's count; never regrows.
- [ ] Owned-dir suites + `test_golden_count_ban.py` green.
- [ ] No file outside the owned directories was edited.
- [ ] `ruff` + `mypy` clean.
- [ ] **Tracer (FR-016):** append a catalog row for the golden-count conversions in this batch + friction log.

## Risks

- **Converting a genuine cardinality assertion** — trust WP11's `keep` classification; annotate rather than
  convert those.
- **Drift outside owned dirs** — the convert-set is bounded to these four directories.

## Reviewer guidance

- Spot-check a few conversions against WP07's exemplar shape.
- Confirm the baseline decrement matches the number of conversions and the guard is green.

## Activity Log

- 2026-07-13T16:01:51Z – claude:sonnet:python-pedro:implementer – shell_pid=3237943 – Assigned agent via action command
