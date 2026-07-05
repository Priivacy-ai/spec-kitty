---
work_package_id: WP06
title: 'Closeout: ratchet baseline refresh (orphan=0, no test disappears) + issue-matrix terminal verdicts + #1931 rollup + closeout comments'
dependencies:
- WP04
- WP05
requirement_refs:
- NFR-007
- C-006
tracker_refs:
- '#1931'
- '#2378'
- '#1933'
- '#2383'
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-ci-topology-shrink-01KWQAVX
base_commit: aa998ede7e31927286e78e7819757e03c2f2c604
created_at: '2026-07-04T21:00:00+00:00'
subtasks:
- T015
phase: Phase 6 - Closeout
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "1233198"
history:
- at: '2026-07-04T21:00:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: tests/architectural/_gate_coverage_baseline.json
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- tests/architectural/_gate_coverage_baseline.json
- docs/changelog/CHANGELOG.md
- tests/architectural/test_ci_quality_path_filters.py
- tests/architectural/test_ci_architectural_gate_coverage.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP06 – Closeout

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter (or any user-defined profile), and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`

---

## ⚠️ IMPORTANT: Review Feedback

Check the `review_ref` field in the event log before starting; address all feedback.

---

## Objectives & Success Criteria

Close the mission: refresh the ratchet baseline (`orphan_test_count` stays 0 and no previously-collected test disappears — `total_tests` legitimately RISES by the newly-added gated tests), set every issue-matrix verdict to a terminal value, post closeout comments, and the #1931 rollup. Run the full NFR-007 invariant sweep on the merged tree to confirm all 8 #2368 invariants + the new relations are green.

## Subtasks & Detailed Guidance

### Subtask T015 – Baseline refresh + issue-matrix + closeout comments
- **Baseline refresh**: `uv run python -m tests.architectural._gate_coverage --update-baseline`. The correct anchor is **`orphan_test_count` stays 0** (every new test is gated) AND **no previously-collected test disappears** — NOT total-equality. This mission ADDS test files (WP02's 8 new invariants + WP05's 1 coverage-ownership test), so `total_tests` legitimately RISES by exactly the count of newly-added gated test cases (across those 8 WP02 files + the 1 WP05 file). The machine ratchet (`test_gate_coverage.py`) fails on new **orphan files**, not on total inequality. A **DROP** in `total_tests` (a previously-collected test vanished) or any new **orphan** IS the regression — investigate before committing. `duplicate_test_count` may shift with the same-tier consolidation — record the delta.
- **Coordinate-note**: #2072 also re-keys `_gate_coverage_baseline.json`. Flag this shared-file coordinate in the closeout comment so a later agent does not clobber our refresh.
- **Issue-matrix terminal verdicts** (`issue-matrix.md`): **NOTE — this file lives under `kitty-specs/` and is therefore NOT an `owned_files` entry** (the finalize/lanes guard rejects `kitty-specs/*` paths as owned code files). The verdict-flip is a **planning-artifact / coordination-branch edit**, not an owned-code-file change — editing it is expected and causes no ownership violation. Set #2378 → `fixed` (shard-side split landed), #1933 → `fixed` (group-side shrink; cite the #1933-intent statement from WP05's C-006 decision), #2383 → `fixed` (arch un-blind landed), #1931 → `fixed` (rollup, terminal at closeout). The context/substrate rows (#2368/#2370/#2379) and out-of-scope rows (#2283/#2077/#2071) already carry terminal verdicts from planning — confirm they are unchanged. Zero `unknown`/`in-mission` rows may remain.
- **Closeout comments**: post on #2378 (shard-side split, PR link), #1933 (group-side shrink + the intent statement + intact escape hatches/nightly over-cover), #2383 (arch un-blind), and the #1931 rollup. Use `unset GITHUB_TOKEN` if `gh` hits a scope error (keyring token).
- **CHANGELOG**: append the mission entry to `docs/changelog/CHANGELOG.md` (root `CHANGELOG.md` is a symlink → this file — edit the target).

## Campsite cleaning (standing rule; ride the WP's normal review)

Data + docs files — keep JSON schema-consistent and the CHANGELOG entry in the existing format. No scope creep to the workflow/test files (owned by WP03/WP04/WP05).

## Definition of Done (non-fakeable — every anchor is a green test or a terminal record)

- **`_gate_coverage_baseline.json` refreshed with `orphan_test_count`=0 (all new tests gated) and NO previously-collected test dropped**, asserted by the orphan ratchet (`test_gate_coverage.py`) staying green on the merged tree — recorded run output. `total_tests` RISES by exactly the count of newly-added gated test cases (8 new WP02 files + 1 new WP05 file) — a rise is expected and correct; a DROP or a new orphan is the regression.
- **NFR-007 sweep GREEN**: all 8 #2368 invariants + NFR-002/003/005 + C-005 green on the merged tree (`PWHEADLESS=1 uv run pytest tests/architectural/ -q`) — recorded output.
- **`issue-matrix.md` has zero non-terminal rows** — every verdict is `fixed`/`verified-already-fixed`/`deferred-with-followup`.
- Closeout comments posted (links recorded); #1931 rollup terminal; #2072 shared-baseline coordinate flagged.
- CHANGELOG entry appended via the symlink target.

## Risks / Reviewer Guidance

- A baseline rekey that introduces a new orphan file, or that DROPS a previously-collected test, masks a real regression → assert `orphan_test_count`=0 and no-test-disappears as the DoD anchor (a `total_tests` RISE from the newly-added gated tests is expected, NOT a regression).
- #2072 concurrently rekeys the same baseline → the closeout comment must flag the coordinate.
- Reviewer confirms no non-terminal issue-matrix row remains (mission cannot reach `done` otherwise).

## Activity Log

> Append at the END, chronological. Format: `- YYYY-MM-DDTHH:MM:SSZ – agent_id – <action>`

- 2026-07-04T21:00:00Z – system – Prompt created.
- 2026-07-05T01:40:38Z – claude:opus:python-pedro:implementer – shell_pid=1179639 – Assigned agent via action command
- 2026-07-05T02:05:00Z – claude:opus:python-pedro:implementer – Baseline refreshed (`uv run --extra test python -m tests.architectural._gate_coverage --update-baseline`): total_tests 28573→28709 (+136 RISE, expected from WP02's 8 invariants + WP05's ownership test; NO drop); orphan_test_count 0→0; duplicate_test_count 3550→707 (−2843, same-tier consolidation from WP03 filter grouping); orphan_files []→[]. Orphan ratchet `test_gate_coverage.py` GREEN (18 passed).
- 2026-07-05T02:05:00Z – claude:opus:python-pedro:implementer – Issue-matrix terminal verdicts set (#2378/#1933/#2383/#1931 → `fixed`; substrate #2368/#2370/#2379 and out-of-scope #2283/#2077/#2071 unchanged). Zero non-terminal rows (only the legend line mentions `in-mission`). CHANGELOG mission entry appended to docs/changelog/CHANGELOG.md (♻️ Changed, [Unreleased] 3.2.4). Closeout comments DRAFTED (NOT posted — mission unmerged, operator merges) at kitty-specs/ci-topology-shrink-01KWQAVX/closeout-comments-draft.md, incl. #2072 shared-baseline coordinate + the 2 WP05 post-merge backfill obligations.
- 2026-07-05T02:05:00Z – claude:opus:python-pedro:implementer – ⛔ CLOSEOUT BLOCKED — NFR-007 full `tests/architectural/` sweep RED (9 failed / 714 passed / 4 skipped, 379s). Adjudicated against cross-base control (mission base aa998ede7; origin/main e67f0ab7 is an ANCESTOR of the base, so base is fresh): (A) 4× test_tid251_enforcement.py = ENVIRONMENTAL (ruff absent from `test` extra) — 9 pass with `--extra test --extra lint`; green on CI. (B) 1× test_no_dead_modules.py = foreign-merge artifact (m_3_2_4 allowlist entry removed by model-discipline-dispatch-binding-01KWPW36/#2370 edit while lane keeps the module; origin/main has BOTH absent → passes) — resolves on merge-to-main. (C) ⛔ 4× ci-quality sibling contract tests (test_ci_quality_path_filters.py ×3 + test_ci_architectural_gate_coverage.py ×1) = GENUINE mission gap: WP03 rewrote ci-quality.yml (de-serialized arch pole, resharded core-misc) but the pre-existing sibling tests still assert the OLD topology ('architectural' as core-misc shard [superseded by WP02's test_arch_pole_deserialized.py]; literal `--ignore=tests/e2e` now in matrix.ignore_args; core_misc!="true" short-circuit guard). NOT in any WP's owned_files (WP03 owns only ci-quality.yml) nor any campsite list; per-WP review never ran the full arch suite. Pass on old-topology base, WILL red on origin/main post-merge. Fix is WP03-scope (WP06 must not edit WP03-owned test files): update/delete the 4 superseded assertions, re-run full sweep green, then re-refresh _gate_coverage_baseline.json. HOLDING WP06 for_review — did NOT mark T015 done, did NOT move to for_review, did NOT post GitHub comments. WP06-owned deliverables (baseline + CHANGELOG) committed; issue-matrix + closeout draft on coordination branch.
- 2026-07-05T02:08:06Z – claude:opus:python-pedro:implementer – shell_pid=1179639 – BLOCKED: NFR-007 full tests/architectural/ sweep RED (9 failed/714 passed). Adjudicated: 4x TID251 environmental (ruff not in test extra; green with --extra lint); 1x no_dead_modules foreign-merge m_3_2_4 artifact (origin/main has module+entry both absent -> resolves on merge-to-main); 4x GENUINE ci-quality sibling contract tests (test_ci_quality_path_filters.py x3 + test_ci_architectural_gate_coverage.py x1) assert OLD topology WP03 replaced (arch pole de-serialization + core-misc reshard) and were never updated. These 2 files are NOT in any WP owned_files (WP03 owns only ci-quality.yml) nor any campsite list -> undiscovered gap; superseded by WP02 test_arch_pole_deserialized.py. Fix is WP03-scope (WP06 must not edit WP03 test files): update/delete 4 stale assertions, re-run full sweep green, re-refresh baseline. WP06-owned deliverables (baseline+CHANGELOG) committed 407f1caf8; issue-matrix terminal + closeout draft written. HELD: T015 not marked done, WP06 not moved to for_review, no GitHub comments posted.
- 2026-07-05T04:00:00Z – claude:opus:python-pedro:implementer – CLOSEOUT UNBLOCKED — the 2 sibling ci-topology contract test files (test_ci_quality_path_filters.py, test_ci_architectural_gate_coverage.py) were folded into WP06 owned_files for this remediation; re-pinned the 4 stale assertions to the WP03 de-serialized/sharded topology (BEHAVIORAL INTENT preserved, no vacuous weakening, DIR-041):
  - **#1 test_core_misc_integration_is_sharded_and_parallelized** — RE-PINNED: dropped `architectural` from the expected `integration-tests-core-misc` shard set → now `{integration, specify-cli-heavy, specify-cli-rest, auth-audit-git, misc}` (matches new matrix); added an assertion that the extracted `architectural` shard still exists in the always-on `arch-adversarial` pole so "arch still runs" keeps biting.
  - **#2 test_core_misc_excludes_e2e_and_cross_cutting_suites** — RE-PINNED: WP03 moved the `--ignore=tests/e2e`/`--ignore=tests/cross_cutting` literals out of the fast run step into `matrix.ignore_args`; assertion now pins the run step interpolates `${{ matrix.ignore_args }}` AND the fast `core-misc` shard's `ignore_args` carries both ignores (e2e/cross_cutting still excluded from core-misc fast runs — intent intact at the new structural location).
  - **#3 test_execution_context_only_core_misc_runs_focused_parity_gate → renamed test_execution_context_parity_ratchet_runs_unconditionally** — RE-PINNED: WP03 removed the exec-context short-circuit block from `integration-tests-core-misc`; the CWD parity ratchet (`tests/architectural/test_execution_context_parity.py`, `architectural`+`git_repo` markers) now runs in the always-on `arch-adversarial` pole. Assertion pins pole is `if: always()`, its `architectural` shard collects `tests/architectural`, the parity file exists there, and the pole's marker positively selects it → ratchet runs unconditionally (stronger than the old conditional path; parity guarantee NOT dropped).
  - **#4 test_status_change_sets_core_misc_bypasses_short_circuit → renamed test_arch_suite_runs_unconditionally_cannot_be_masked** — RE-PINNED (old `core_misc != "true"` short-circuit mechanism SUPERSEDED by WP03's always-on pole): assertion now pins `arch-adversarial.if == "always()"`, gate carries NO `needs.changes.outputs` filter reference, and the pole declares no `needs` edge → no status/path change can mask the arch suite (raw-YAML lens; complements — does not duplicate — WP02's parse-model invariants `test_arch_unblind_matrix.py::test_no_src_dir_is_architecturally_blind` [0 arch-blind dirs] and `test_arch_pole_deserialized.py` [de-serialized]). Not deleted-as-superseded because this raw-YAML `if: always()` + no-filter-gate assertion is a distinct guard from the WP02 parse-model matrix.
  - **Full NFR-007 sweep** (`PWHEADLESS=1 uv run --extra test --extra lint pytest tests/architectural/ -q`): **1 failed / 722 passed / 4 skipped**. The ONLY red is `test_no_dead_modules.py::test_no_new_dead_modules_under_src` flagging `specify_cli.upgrade.migrations.m_3_2_4_derived_views_gitignore_backfill` — confirmed STALE-BASE artifact (module present in lane HEAD, `git cat-file -e origin/main:…` → DELETED on origin/main); resolves on the pre-merge rebase; NOT touched in-lane. Everything else GREEN (TID251 env-class passes with `--extra lint`).
  - **Baseline re-refresh** (`python -m tests.architectural._gate_coverage --update-baseline`): NO-OP — already current from 407f1caf8. total_tests 28709 (unchanged; re-pins were renames, no net case count delta), orphan_test_count 0 (unchanged), duplicate_test_count 707 (unchanged). Orphan ratchet `test_gate_coverage.py` GREEN (18 passed). #2072 concurrently re-keys this same baseline — shared-file coordinate.
  - ruff + mypy on the 2 edited files: clean (`All checks passed!` / `Success: no issues found in 2 source files`). Committing 2 test files (+ baseline no-op) and moving WP06 → for_review.
- 2026-07-05T02:33:43Z – claude:opus:python-pedro:implementer – shell_pid=1179639 – Closeout: baseline refreshed (orphan=0), NFR-007 sweep green except m_3_2_4 stale-base artifact (resolves on rebase); 4 stale ci-topology contract tests re-pinned to new topology; issue-matrix terminal; CHANGELOG appended
- 2026-07-05T02:34:58Z – claude:opus:reviewer-renata:reviewer – shell_pid=1233198 – Started review via action command
- 2026-07-05T02:45:46Z – user – shell_pid=1233198 – Review passed: 4 stale contract tests faithfully re-pinned (parity ratchet + arch-unconditional preserved, still bite); NFR-007 sweep green except m_3_2_4 stale-base artifact (resolves on rebase); baseline orphan=0; issue-matrix terminal; closeout drafted for merge
