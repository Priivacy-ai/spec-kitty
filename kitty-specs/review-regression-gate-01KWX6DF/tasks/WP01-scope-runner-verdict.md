---
work_package_id: WP01
title: Scope-derivation + head-side runner + verdict engine
dependencies: []
requirement_refs:
- FR-002
- FR-003
- FR-005
- FR-006
tracker_refs: []
planning_base_branch: fix/review-regression-gate
merge_target_branch: fix/review-regression-gate
branch_strategy: Planning artifacts for this mission were generated on fix/review-regression-gate. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/review-regression-gate unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
agent: "claude"
shell_pid: "2145769"
history:
- 'Created by planner for #572/#1979/#2283 tasks phase'
agent_profile: python-pedro
authoritative_surface: src/specify_cli/review/
create_intent:
- src/specify_cli/review/pre_review_gate.py
- tests/architectural/test_pre_review_scope_singlesource.py
- tests/review/test_pre_review_gate_engine.py
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- src/specify_cli/review/pre_review_gate.py
- tests/architectural/test_pre_review_scope_singlesource.py
- tests/review/test_pre_review_gate_engine.py
role: implementer
tags: []
task_type: implement
---

# WP01 – Scope-derivation + head-side runner + verdict engine

## ⚡ Do This First: Load Agent Profile
`/ad-hoc-profile-load` → `python-pedro` (implementer, Sonnet-5). Read `spec.md` (FR-002/003/005/006, C-001/002/003) + `plan.md` (IC-01). **The scope derivation is the subtle part — read the Grounding section carefully.**

## Objective
Build `src/specify_cli/review/pre_review_gate.py`: given a WP's changed files, derive the affected test set, run it at head, and compute the **new-failure** verdict — reusing `review/baseline.py`'s JUnit parser + `diff_baseline` (the ONLY genuine reuse; the scoped runner is net-new).

## The scope derivation (T001 — read twice; two group shapes + a hard exclusion)
Study `tests/architectural/_gate_coverage.py`: `aggregate_filter_groups()` (`:866`), `_parse_filter_groups` (`:420`), `_COMPOSITE_ROUTING` (`:784-851`), `mapped_src_dirs` (`:902`). The dorny groups in `ci-quality.yml` have **two shapes**:
- **(a) per-shard groups** (`status`, `cli`, `merge`, `sync`, `review`, `lanes`, `dashboard`, `upgrade`, …) — their globs **already include `tests/**`**. Affected test scope = those test globs (filter to the changed files' group).
- **(b) composite groups** (`auth_audit_git`, `lifecycle`, `agent_surface`, `closeout`, `governance`, `platform`) — **src-only** globs, NO `tests/**`. Affected test scope = the census **`_COMPOSITE_ROUTING` cone_roots** for that dir (e.g. `git → tests/git`).
- **EXCLUDE the catch-all groups `core_misc`, `e2e`, `any_src`** — `core_misc` spans ~53 `tests/**` globs (~17min) and would defeat FR-005's bounded-cost goal. Verify: `status/emit.py` (a member of `status` AND `core_misc` AND `execution_context`) must resolve to the **`status`** shard, NOT `core_misc`.
- The derivation key is **"does the file's group carry `tests/**` globs"** — NOT "mapped vs unmapped tail" (that framing is wrong; the census worklist dirs are all composite-group members). Recall > precision applies to the focused/composite set only; never re-admit the excluded catch-alls.
- **An empty affected set NEVER = "verified clean" → always WARN** (a distinct `no_coverage` outcome, separate from a green `no_new_failures`): (a) a file only in a catch-all/excluded group → warn ("excluded scope — unverified"); (b) a composite dir whose census cone_roots are **EMPTY** (`doc_analysis`, `validators`, `task_utils`, `intake` — real src dirs, no test dir) → warn ("unmapped composite dir — unverified"). ⚠️ Do NOT report an empty run as clean — that reopens the mission's own silent-under-coverage anti-goal (SC-007).

## T002 — head-side scoped runner + new-failure verdict (FR-003)
- Invoke pytest on the derived test set at head (subprocess), emit JUnit, parse it with `baseline.py`'s existing parser → `current_failures`. Compute new-failures = `head_failures − base_failures` via `baseline.py`'s `diff_baseline` (which takes `current_failures` as input — that head-side production is what's net-new). ⚠️ `baseline.py` is REUSED unchanged (parser + `diff_baseline`); do NOT modify it.
- If the baseline is uncomputable (base ref missing) → **degrade to warn** (surface all as "unverified baseline"), never hard-block.

## T003 — FR-006 single-source invariant (`tests/architectural/test_pre_review_scope_singlesource.py`)
An arch test proving the derivation reads the **live authorities for BOTH shapes**: per-shard groups' `tests/**` globs from `aggregate_filter_groups()` AND composite groups' `_COMPOSITE_ROUTING` cone_roots; AND that the catch-all exclusion holds. It must FAIL if the derivation is fed a stale/hand-authored map, or if it consults only `aggregate_filter_groups()` (which would leave composite dirs with an empty test set — the silent-under-coverage the mission exists to prevent).

## DoD
- `pre_review_gate.py` derives per group shape + excludes catch-alls (`status/emit.py` → `status`, not `core_misc`; a `git/**` change → `tests/git` cone_roots).
- **Empty affected set → `no_coverage` WARN, never clean**: a `src/specify_cli/validators/**`-shaped change (empty-cone composite) warns "unmapped composite — unverified" (SC-007), NOT a clean pass — with a test asserting it.
- Head-side runner produces `current_failures`; verdict = new failures via `diff_baseline`; baseline-uncomputable → warn.
- FR-006 invariant green + genuinely bites (mutate the derivation → it reds).
- `baseline.py` untouched; `PWHEADLESS=1 uv run pytest tests/review/ tests/architectural/test_pre_review_scope_singlesource.py -q` green; `ruff` + `mypy --strict` clean; no new suppressions.

## Report back
The two-shape derivation (paste the per-shard vs composite branch + the catch-all exclusion); proof `status/emit.py` → `status` (not `core_misc`) + a composite dir → its cone_roots; the head-runner + `diff_baseline` reuse; the FR-006 invariant (mutation-proof); pytest counts; ruff+mypy; lane commit SHA. If the derivation can't cleanly separate the two shapes from the live authorities, STOP and report.

## Activity Log

- 2026-07-07T03:21:44Z – claude – shell_pid=2145769 – Assigned agent via action command
- 2026-07-07T04:08:15Z – claude – shell_pid=2145769 – Moved to for_review
- 2026-07-07T04:08:18Z – user – shell_pid=2145769 – Moved to approved
