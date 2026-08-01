---
work_package_id: WP14
title: 'PLACEHOLDER: the sync half''s terminal state — remedy, or deferred-with-followup'
dependencies:
- WP06
requirement_refs:
- FR-010
planning_base_branch: feat/verification-trust-3115
merge_target_branch: feat/verification-trust-3115
branch_strategy: Planning artifacts for this mission were generated on feat/verification-trust-3115. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/verification-trust-3115 unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-verification-trust-3115-01KYVYWM
base_commit: d8d0ad7eff9ddeb14e154afd82450cf2dfd5472d
created_at: '2026-07-31T12:00:00+00:00'
subtasks:
- T044
- T045
history: []
authoritative_surface: tests/sync/tracker/
execution_mode: code_change
owned_files:
- tests/sync/tracker/test_saas_client.py
tags: []
tracker_refs: []
---

# WP14 — PLACEHOLDER: the sync half's terminal state

FR-010 bounds the sync-half investigation — **at most 6 agent-hours and at most 3 candidate mechanisms**
— so that bounded, finished work (`#3113`, the timeout gap, the whole CLI half) **is not held hostage to
an open-ended hunt**. This WP is that exit valve, and it has exactly two permitted terminal states.

## Why this WP exists now, before its outcome does

The friction record: ***"WPs created after planning have no lane, so two gates silently no-op."*** A WP
added later defaults to `lane-a`, which makes the **lane-staleness gate fire inapplicably** (advising a
rebase of somebody else's approved lane) and makes the **pre-review regression gate print
`no_coverage — skipping the gate cheaply` on work that received no gate at all**. **Pre-allocating the
lane entry is the whole fix.** Adding the WP after the investigation lands reproduces that friction
*knowingly*.

## Ownership is fixed at planning time, not at dispatch

Lane membership is computed **solely** from `owned_files` overlap
(`src/specify_cli/lanes/compute.py:1-11`), so a placeholder with **empty** ownership lands in its **own
singleton lane** — and outcome A would then write a file **another lane's worktree owns**. Declaring
`tests/sync/tracker/test_saas_client.py` now puts WP14 in the **same lane as WP06** (`lane-f`), which is
the only thing that makes outcome A a **within-lane transfer**.

## Definition of done — measurable evidence

**The only permitted terminal states for this leg are (a) or (b).**

### T044 — Outcome A: cause identified

- The remedy lands in the **declared** file, `tests/sync/tracker/test_saas_client.py`.
- It is supported by a **both-directions reproduction**: the count before and the count after, **both
  quoted with their assertion texts** (NFR-007) — *showing the call count moving*.
- **If the attribution names a thread-owning fixture in another file, that file is NOT taken over.**
  The remedy is expressed at the declared file and the other file's change is **raised as a successor**,
  because **ownership may not be invented after planning** — this is the whole point of the
  pre-allocation.
- On outcome A the pre-review gate **should run normally**. **If it prints `no_coverage`, that is a
  defect to investigate, not to absorb.**

### T045 — Outcome B: budget exhausted

- **The declared file is left untouched.** An owned file with **no diff is legal**, and it is what keeps
  the lane entry valid.
- The deliverable is the **successor issue**, filed against `Priivacy-ai/spec-kitty`, inheriting:
  - **WP04's inventory**, and
  - **the harness's negative result** — *which mechanisms were excluded and by what measurement*;
  plus the **`deferred-with-followup` verdict** and **the successor number recorded on `#3115`'s matrix
  row**.
- **Expected gate no-op, stated in advance.** Pre-allocating ownership closes only **one** of the two
  paths to `no_coverage — skipping the gate cheaply`: it fixes the **workspace-resolution** path
  (`tasks_move_task.py:937-962`), but **outcome B produces no diff**, so the **changed-file** path
  (`:965-980`) returns an empty tuple and the gate folds to `no_coverage` anyway. **The transition note
  must state that the printed line is expected** and **name the manual evidence standing in for it**:
  the **successor issue number**, **WP06's recorded floor** (F-a or F-b), and **the enumerated exclusion
  measurements**.

### The closure that is forbidden

> ***"Recorded as unproven" plus a green shard is NOT a permitted closure*** — that is the exact path
> that produced `578a659162`.

A green shard proves only that this run's dynamic worker assignment and this runner's terminal state
were benign. **A green shard may not close the sync half while the `sleep`-count cause is
unidentified** (FR-010's blocking exit clause).

### NFR-008 — every count line carries its collected count, on **both** outcomes

**Added post-tasks: WP14 was one of only two WPs in this mission carrying no collected-count
obligation** — and it is the WP whose sanctioned outcome produces no diff, which makes it the one most
exposed to a claim nothing measured.

- **Outcome A**: the both-directions reproduction quotes the count **before** and the count **after**,
  each **beside `tests/sync/tracker/test_saas_client.py`'s own collected count** at the commit under
  test, measured with `pytest --collect-only -q` on that single file. The remedy changes that file, so
  the collected count **may move**, and a move is **stated and reconciled**, never absorbed. The
  `sleep` call count moving is the finding; the collected count is what proves the two runs selected
  the same thing.
- **Outcome B**: the enumerated **exclusion measurements** each carry the **selection run, its
  collected count, and the observed outcome** — the same shape FR-010 already binds on WP06's floor.
  *An excluded mechanism with no collected count beside it is an argument from structure, not a
  measurement, and does not count against the budget of three.* An exclusion whose selection collected
  **zero** is no exclusion at all: `|| test $? -eq 5` is exactly how an empty collection reads as a
  result.
- **Both outcomes**: the transition note's manual evidence carries its input counts. **A gate, probe or
  harness that reports "nothing found" without saying how many inputs it processed passed vacuously**,
  and this WP is the mission's last chance to catch that on the sync half.

### Cross-cutting

**NFR-009**: state the commit every measurement was taken at and the lane's merge-base; merge the
mission branch into the worktree before the first measurement. **NFR-003**: output to a file, tail of
the file read; **an empty output file is no measurement**. **NFR-004**: never run `tests/sync` and
`tests/cli` sessions concurrently on one machine. **C-010**: a lane may not write `kitty-specs/` — the
successor issue number and the `deferred-with-followup` verdict are recorded in `issue-matrix.json` **by
the orchestrator on the mission branch**; this WP delivers the evidence and the issue.

## Interaction with WP13

WP13 is deliberately **not** blocked on WP14. WP14 owns `tests/sync/tracker/test_saas_client.py`, which
carries **node-id 13** (`TestRetryBehaviors::test_429_respects_retry_after`) in WP13's enumeration. If
WP14 lands **after** WP13's first pass, **WP13 re-quotes node-id 13's outcome at the merge commit**.
Coordinate the re-measurement; do not silently invalidate WP13's evidence.

## Files other agents hold

`tests/sync/tracker/test_saas_client.py` is **shared with WP06 by construction** — same lane, WP14
**after** WP06. `tests/sync/conftest.py` and `tests/sync/test_leak_guard_probe_3115.py` are **WP05's**;
`tests/sync/test_sync_consent_default_deny.py` is **WP09's**;
`docs/development/process-global-inventory-3115.md` is **WP04's** — this WP *inherits* the inventory into
the successor issue, it does not edit it. `scripts/mutants/attribute_sleep_count_3115.py` is **WP06's**.
`src/**` is nobody's.
