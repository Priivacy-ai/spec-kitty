---
work_package_id: WP03
title: Write-in-home placement + analysis-report re-home
dependencies: []
requirement_refs:
- FR-001
- FR-003
planning_base_branch: remediation/coord-trust-2841
merge_target_branch: remediation/coord-trust-2841
branch_strategy: Planning artifacts for this mission were generated on remediation/coord-trust-2841. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into remediation/coord-trust-2841 unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-coord-commit-integrity-01KY5JS8
base_commit: ebf28500d886561480e1d9375c1372ff8ba46b40
created_at: '2026-07-22T20:59:24.476770+00:00'
subtasks:
- T009
- T010
- T011
history:
- at: '2026-07-22T19:33:57Z'
  actor: claude
  event: created
agent_profile: python-pedro
authoritative_surface: src/mission_runtime/
create_intent:
- tests/coordination/test_analysis_report_rehome.py
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- src/mission_runtime/artifacts.py
- src/specify_cli/review/cycle.py
- src/specify_cli/cli/commands/agent/mission_record_analysis.py
- src/specify_cli/coordination/commit_router.py
- src/specify_cli/post_merge/review_artifact_consistency.py
- tests/coordination/test_commit_router.py
- tests/architectural/test_write_surface_placement_guard.py
- tests/coordination/test_analysis_report_rehome.py
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load python-pedro
```

(Or read `src/doctrine/agent_profiles/built-in/python-pedro.agent.yaml`.) Adopt its directives/tactics; state which you applied. **This WP has three landmines the post-plan squad flagged — read the whole prompt before editing.**

## Objective

Retire wrong-partition authorship and the second-copy residue; re-home `ANALYSIS_REPORT` COORD→PRIMARY. Read
`research.md` (Decision C + the ⚠ Precision note), `data-model.md` (partition table + the KEEP-the-classifier
note), `contracts/commit-path-contract.md`. **The re-home is a mis-classification correction, not a contract
redesign — the ONE frozenset move only.**

## Branch Strategy

Planning base + merge target **`remediation/coord-trust-2841`** (coord). Lane b (parallel with lane-a). Worktree per lane.

## ⚠️ Three landmines (do NOT step on these)

1. **KEEP `_COORD_RESIDUE_FILENAMES["analysis-report.md"]`.** It is the file→kind *classifier* consumed by
   `kind_for_mission_file`, NOT a residue-only entry. Deleting it makes `kind_for_mission_file("analysis-report.md")→None`
   → mis-routes via the unrecognized-path fallback. The re-home is the frozenset membership move ONLY; the ~9
   residue delegators + `is_primary_artifact_kind` flip atomically from it. (Optional: rename
   `_COORD_RESIDUE_FILENAMES`→`_MISSION_FILENAME_KINDS` to kill the naming-lie.)
2. **INVERT the coord-pinning tests — do NOT run-to-green.** `tests/coordination/test_commit_router.py:502`
   asserts `"…ANALYSIS_REPORT… STILL routes to coordination (C-001)"` — a #2463 flip-test landmine. Assert the
   NEW PRIMARY truth. For tests that merely use ANALYSIS_REPORT as the coord-kind *exemplar*
   (`test_wp05_mission_coordination_routing.py:96`, `test_protected_primary_spec_commit.py:205/368/414`), SWAP the
   exemplar to `ACCEPTANCE_MATRIX`/`ISSUE_MATRIX` — don't delete the coverage.
3. **Update the #2198 arch-gate.** `tests/architectural/test_write_surface_placement_guard.py`
   `PARTITION_RATIONALE[ANALYSIS_REPORT]` pins `("COORD", …, …)` + an anti-mutant expected-ref assertion —
   flip partition + rationale text + the expected ref, or CI reds.

## Subtasks

### T009 — FR-001 review-cycle write-in-home (ALL write sites)

`review-cycle-N.md` is `WORK_PACKAGE_TASK` → PRIMARY, but `review/cycle.py:~272` (`create_rejected_review_cycle`)
writes it via kind-blind `candidate_feature_dir_for_mission` → the coord husk. **The placement decision lives
ONLY in `cycle.py:272` — the move-task `--review-feedback-file` path (#2697) merely CALLS
`create_rejected_review_cycle` (`tasks_move_task.py:1325`, WP02-owned) and passes no pre-resolved dir (paula
verified). So extracting ONE `_review_cycle_wp_dir(root,slug,wp_slug)` in `cycle.py` and pointing it at the
PRIMARY-home resolver fixes BOTH the direct site and the move-task caller from ONE edit in your own file — do
NOT reach into `tasks_move_task.py`.** Also VERIFY `post_merge/review_artifact_consistency.py`'s
caller-supplied `feature_dir` resolves PRIMARY post-fix (#2275/#2646 — the merge gate must read where the write
now lands; edit it if it reads COORD). Converge the read seam (`cycle.py:~193`) + write seam on the one
resolver. Contingent-close #2646/#2697/#2275 only if each repro retests green.

**OWN the review-cycle-PRIMARY e2e assertion (moved from WP01, renata+paula):** add to a WP03 test — assert
via committed refs on a real-git coord fixture that `review-cycle-N.md` exists at `git show <primary_ref>:tasks/<wp>/…`
and is ABSENT at `git show <coord_ref>:…`. There must be NO mission-introduced `xfail` for this at merge.

### T010 — FR-003 analysis-report re-home + residue drop (narrow)

- `mission_runtime/artifacts.py`: move `ANALYSIS_REPORT` from `_PLACEMENT_ARTIFACT_KINDS` to
  `_PRIMARY_ARTIFACT_KINDS` — **this one frozenset move ONLY**. KEEP the `_COORD_RESIDUE_FILENAMES` entry
  (landmine 1). Confirm `assert_partition_invariant` stays green (disjoint-and-total).
- `mission_record_analysis.py`: analysis-report now writes to its PRIMARY home; DROP the best-effort coord
  copy (the `contextlib.suppress(Exception)` block ~:324) and rewrite the now-false comment ~:336-340 (it
  asserts the opposite). Campsite: dedup the 5 `if json_output: … else console.print` error branches + narrow
  the two blanket `suppress(Exception)` to concrete exceptions + log.
- `coordination/commit_router.py`: drop ONLY the analysis-report path of the `shutil.copy2` at `:700-705`.
  KEEP the `.worktrees` bypass (`:691-699`) and the status-skip (`:688`). Acceptance-matrix + issue-matrix STAY
  COORD (they write-in-coord-home via the bypass — do NOT move them). Add a regression enumerating every
  `commit_for_mission` coord-kind caller proving write-in-coord-home BEFORE the copy is removed (else "silently
  copied" → "silently missing").

### T011 — mandatory co-changes + reader verification

- Update the #2198 arch-gate `PARTITION_RATIONALE[ANALYSIS_REPORT]` (landmine 3).
- INVERT the coord-pinning tests (landmine 2) — **the count is ~12-15, NOT ~8 (pedro): `ANALYSIS_REPORT`
  appears in 18 test files.** Invert EVERY test that asserts its partition/routing (incl. the unlisted
  `test_analysis_report.py`, `test_record_analysis_placement.py`, `test_mission_record_analysis.py`,
  `test_kind_for_artifact.py`, `test_partition_authority_characterization.py`, …). These are WP03's by the
  re-home (no other WP owns them); add any not pre-listed to your scope with a one-line rationale — do NOT
  silently exceed, but do NOT leave a coord-asserting test un-inverted either. **Non-fakeable (renata):** each
  inverted test must assert the PRIMARY/target ref POSITIVELY and be red-against-pre-move / green-after —
  direction pinned by content, not by "green" (running `test_commit_router.py`'s
  `test_coord_kind_under_coord_topology_still_routes_to_coord` to green would REVERSE the re-home). Each
  exemplar-swapped test must still reference a coord kind (`ACCEPTANCE_MATRIX`/`ISSUE_MATRIX`) and preserve its
  assertion count — deletion of coord-routing coverage is a review failure.
- New `tests/coordination/test_analysis_report_rehome.py`: assert `kind_for_mission_file("analysis-report.md")`
  resolves to **`ANALYSIS_REPORT` specifically** (not merely non-`None` — reference the PUBLIC classifier, not
  the private `_COORD_RESIDUE_FILENAMES` symbol, so it survives the optional rename) AND
  `is_primary_artifact_kind(ANALYSIS_REPORT)` True (the pair catches both classifier-deletion and mis-move);
  `assert_partition_invariant` green. **Committed-ref proof (renata — config-only does NOT satisfy):** on the
  real-git coord fixture, `git show <primary_ref>:…/analysis-report.md` succeeds AND `git show <coord_ref>:…/analysis-report.md`
  fails (absent) — proving no coord copy via committed trees, not a config assertion.
- Verify the 3 direct-path readers (`retrospective/generator.py`, `dossier/indexer.py`, `sync/body_upload.py`)
  receive the PRIMARY dir post-re-home (read + confirm; fix if any is handed COORD).

## Definition of Done

- [ ] `ANALYSIS_REPORT` is PRIMARY (frozenset move only); `_COORD_RESIDUE_FILENAMES["analysis-report.md"]` KEPT; `assert_partition_invariant` green.
- [ ] Review-cycle writes land PRIMARY from EVERY write site; the merge-gate reader resolves PRIMARY; `_review_cycle_wp_dir` unifies read+write.
- [ ] Residue `copy2` dropped for analysis-report ONLY (`:700-705`); bypass + status-skip kept; acceptance/issue-matrix stay COORD; coord-kind-caller regression added.
- [ ] #2198 arch-gate updated; ALL (~12-15) coord-pinning tests INVERTED (positive PRIMARY-ref assert, red-before/green-after, coord-kind coverage preserved — never run-to-green); stale comment rewritten; 3 direct-path readers verified PRIMARY.
- [ ] Review-cycle-PRIMARY placement proven via committed refs on the real-git fixture (moved from WP01); NO mission-introduced `xfail` remains at merge; analysis-report PRIMARY/absent-on-coord proven via `git show`, not config.
- [ ] `uv run --extra test ruff check` + `mypy` clean; complexity ≤15 (keep `record_analysis:206` under 15 via the error-branch dedup).
- [ ] Full `uv run --extra test pytest tests/coordination tests/architectural/test_write_surface_placement_guard.py -q` green.

## Reviewer guidance

Verify (highest scrutiny): the `_COORD_RESIDUE_FILENAMES` entry is KEPT; the inverted tests assert the PRIMARY
truth (NOT reversed toward coord — the flip-test landmine); the copy-drop is scoped to `:700-705` only;
acceptance/issue-matrix are untouched; `assert_partition_invariant` green; the merge-gate reader change is present.

## Risks

- Running the coord-pinning tests to green REVERSES the re-home (#2463 landmine) — invert deliberately.
- Deleting the classifier entry mis-routes analysis-report — keep it.
- Over-broad copy-drop turns "silently copied" into "silently missing" for other coord kinds — narrow + regression-first.
