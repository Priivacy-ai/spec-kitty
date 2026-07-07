---
work_package_id: WP08
title: '/tmp burn-down: empty baseline + flip ratchet to a self-consistent hard gate'
dependencies:
- WP01
- WP02
- WP03
- WP04
- WP05
- WP06
- WP07
requirement_refs:
- FR-003
- FR-004
- FR-005
- FR-006
- FR-007
tracker_refs: []
planning_base_branch: fix/tmp-literal-offender-burndown
merge_target_branch: fix/tmp-literal-offender-burndown
branch_strategy: Planning artifacts for this mission were generated on fix/tmp-literal-offender-burndown. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/tmp-literal-offender-burndown unless the human explicitly redirects the landing branch.
subtasks:
- T0801
- T0802
- T0803
- T0804
agent: "claude"
shell_pid: "1219471"
history:
- 'Created by planner for #1842 burn-down tasks phase'
agent_profile: python-pedro
authoritative_surface: tests/architectural/
create_intent: []
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- tests/architectural/test_no_tmp_paths_in_tests.py
- tests/architectural/tmp_ratchet_baseline.txt
role: implementer
tags: []
task_type: implement
---

# WP08 – /tmp burn-down: empty the baseline + flip the ratchet to a self-consistent hard gate

## ⚡ Do This First: Load Agent Profile
`/ad-hoc-profile-load` → `python-pedro` (implementer, Sonnet-5). Read `spec.md` (FR-003/004/006/007, C-003) + `plan.md` (Critical sequencing + WP08 row) + the precedent `tests/architectural/test_no_legacy_terminology.py` (fragment needle + `[forbidden]` docstring placeholder + `__file__` self-exclude).

## Objective (runs LAST — depends on WP01–07, all files already converted)
Empty `tmp_ratchet_baseline.txt` and turn `test_no_tmp_paths_in_tests.py` into a **self-consistent hard gate**: no literal `/tmp/` in any test file, the gate file included and genuinely literal-free.

## The self-reference trap (do not half-fix it)
The gate file has **14** literal `/tmp/` lines: the `_TMP_LITERAL` needle (~:73), the self-test payload (~:182), plus 12 in docstrings/comments (4,13,22,83,110,133,143,147,170) and assertion-message strings (157,158,185). Fragment-constructing only the needle keeps the gate's own pytest green (via `__file__` exclude) while SC-001's raw grep still matches the other 13 → **split-brain false-green**. Make the file GENUINELY literal-free.

## Changes
- **T0801 — empty the baseline + guard it**: remove every entry from `tmp_ratchet_baseline.txt` (all 99 lines; empty or header-only). By now WP01–07 converted all 97 + the stale `test_review.py` drops out. **Add a test asserting `_load_baseline()` is empty** (FR-003 guard) — a still-populated baseline yields 0 violations and passes every gate while silently re-grandfathering files; do not rest FR-003 on the DoD checkbox.
- **T0802 — literal-free gate file (all 14)**: string-fragment-construct the `_TMP_LITERAL` needle AND the self-test payload; **reword** the 9 docstring/comment + 3 assertion-message occurrences so `grep '/tmp/'` on this file returns 0. **ADD** a `Path(__file__).resolve()` self-exclude to `_collect_violations` (it does NOT exist today — the gate only avoids self-flagging via baseline membership, gone once emptied) as belt-and-suspenders (secondary; literal-freedom is primary).
- **T0803 — floor → positive self-test (via the REAL gate path)**: replace `test_baseline_is_non_empty_anti_vacuous` (`>50` floor) with a self-test that exercises `_collect_violations` on an EMPTY baseline. `_collect_violations` walks the repo `tests/` root, so a `tmp_path` offender is invisible — make the root/baseline **injectable** (add a `tests_root`/`baseline` param, cleanest) OR `monkeypatch` `_TESTS_ROOT` + `_REPO_ROOT` + `_BASELINE_FILE` to a seeded tmp dir. Assert `_collect_violations(<empty>)` returns **exactly** the synthetic (fragment-built `/tmp/`) offender AND `[]` after it's removed. **Do NOT** use `scan_file_for_tmp_literal` as the proof (bypasses the baseline-skip logic this replaces). Also assert the main gate reports **0** violations across `tests/`.
- **T0804 — FR-007 isolation-adoption check**: add a check that the burn-down did real isolation, not evasion — e.g. assert no test file contains `/dev/shm/`, `/scratch/`, or `/var/tmp/` literals (the substring-evasion vectors), and (optional) that the converted cat-A set references `tmp_path`. Keep it a genuine gate, not a comment.

## Red-first / DoD
- [ ] `grep -rn '/tmp/' tests/ --include='*.py'` → **0** (gate file included; NO `--exclude`).
- [ ] `tmp_ratchet_baseline.txt` empty; `_BASELINE_FLOOR`/`test_baseline_is_non_empty_anti_vacuous` gone.
- [ ] The positive self-test flags a synthetic offender (proven: temporarily point it at a clean dir → it must NOT flag → confirms non-vacuous); the main gate reports 0 violations.
- [ ] The evasion-vector check reds if a `/dev/shm/` literal is planted.
- [ ] `PWHEADLESS=1 uv run pytest tests/architectural/test_no_tmp_paths_in_tests.py -q` green; `ruff` + `mypy --strict` clean; no new suppressions.

## Commit
`git add tests/architectural/test_no_tmp_paths_in_tests.py tests/architectural/tmp_ratchet_baseline.txt && git commit -m "test(architectural): empty /tmp ratchet baseline + flip to self-consistent hard gate — closes #1842"`

## Report back
The literal-free proof (grep on the gate file = 0); the empty baseline; the positive self-test + its red-first evidence; the evasion-vector check; the full-suite `grep '/tmp/' tests/` = 0; pytest counts; ruff+mypy; lane commit SHA. If ANY convertible file still has `/tmp/` (a conversion WP missed one), STOP and report which — do NOT re-baseline it to force green (C-003).

## Activity Log

- 2026-07-06T23:52:32Z – claude – shell_pid=1219471 – Assigned agent via action command
