# Tracer: Approach — dossier-guard-reexport-analyze-cleanup

Seeded at planning (plan phase). Append during implementation; assess at close per the
`mission-tracer-files` procedure (charter Standing Order #3).

## Scope

Four already-diagnosed, disjoint defects in spec-kitty's own tooling, folded into one mission
because two of them (SK-63's path-relativization half, #3678's commit-subject fix) share the exact
same call path (`mission_record_analysis.py` → `analysis_report.py`) and the other two (#3676's
guard-widening, #3677's re-export trim) are each small, self-contained, one-file fixes with no
interaction with anything else in the set. See `spec.md`'s Clarifications/Decision-Record for the
binding scope boundary (D1–D3) — this tracer records how the plan phase approached turning that
already-settled scope into a sequenced set of implementation concerns, not a re-derivation of the
scope itself.

## Plan-authoring approach

1. Read the charter (`.kittify/charter/charter.md`), `AGENTS.md`, and `CONTRIBUTING.md` in full
   before touching plan.md, per the charter's own "Load the Project Charter First" rule and this
   mission's explicit instruction to read them in that order.
2. Read `spec.md` in its entirety, with particular attention to the Clarifications/Decision-Record
   section — it is binding and takes precedence over any ambiguity in the FR/AC tables. All four
   operator decisions (D1–D3), the two charter-clause resolutions (§486's corrected precedence,
   §106), and all four Grounding Corrections were re-read before writing a single line of plan
   content, so the plan restates rather than re-derives them.
3. Independently re-verified every file:line citation carried into this plan against the live
   checkout (this session, on `fix/dossier-guard-reexport-analyze-cleanup-3676`) rather than
   trusting either the mission brief or spec.md's own citations blindly — per the charter's "Use
   Canonical Sources, Never Improvise" rule and this repo's own established re-verification
   discipline (see the `up-mission-type-seam-01KZY1JB` mission's tracer-approach.md for the same
   practice on a prior mission). Specifically checked directly against the live files: the guard's
   docstring (lines 1–42) and `_call_target_name` (lines 92–96) in
   `tests/architectural/test_dossier_emitter_positional_guard.py`; the `from .events import (...)`
   block and `__all__` list (27 entries, lines 27–40 and 50–78) in
   `src/specify_cli/dossier/__init__.py`; the `commit_for_mission(...)` call and its `message=`
   f-string (line 365) in `mission_record_analysis.py`; `_artifact_hash_entry`, `_charter_path`,
   `collect_input_artifact_hashes` (lines 179–226), `write_analysis_report`'s
   `collect_input_artifact_hashes` call (line 412), and `check_analysis_report_current` (line 458,
   its own `collect_input_artifact_hashes` call at line 515) in `analysis_report.py`;
   `_require_current_analysis_report` (line 950) in `cli/commands/agent/workflow.py`; all five
   `hashes["charter"]["path"]` / `input_artifacts["charter"]["path"]` assertion sites across
   `test_analysis_report.py` (lines 238, 260) and `test_analysis_report_charter_yaml_staleness.py`
   (lines 52, 94, 137); the commitlint `ignores` regex and `type-enum`/`type-case`/`type-empty`/
   `subject-empty` rules in `commitlint.config.cjs`; and the CI gate set in
   `.github/workflows/ci-quality.yml` (the `lint` job's per-step `[ENFORCED]`/`[INFO]` labels, the
   `sonarcloud` job's `if: always() && (github.event_name == 'schedule' || ... 'workflow_dispatch')`
   condition, the `kernel-tests`/`mission-loader-coverage` job names, and the `uv-lock-check` job).
   Every citation held exactly as the operator's pre-verified ground truth stated it — no drift
   found (contrast with the `up-mission-type-seam-01KZY1JB` mission, where re-verification did
   surface two off-by-a-line citations; this mission's ground truth was supplied already
   re-verified and re-checking confirmed it, rather than correcting it).
4. Ran `spec-kitty plan --mission dossier-guard-reexport-analyze-cleanup-01M0NHRT --json`
   non-interactively (explicit `--mission` flag, no prompt observed) to scaffold `plan.md` from the
   canonical software-dev template rather than hand-authoring the file's structure. The command
   emitted the same sync/telemetry warnings already recorded as F-01 in
   `tracer-tooling-friction.md` (`project sync store is locked`, `Explicit-context event capture
   failed: live payload writes require the project_only layout`) — non-fatal, `result: "success"`,
   the same known SK-65 signature, no new tracer entry warranted (fourth sighting, same as F-01's
   third).
5. Because spec.md's Decision Record already settles every question this plan needs (no genuine
   open architecture/tech-stack question exists for a four-file bugfix set against an already-fully
   specified target), no `[NEEDS CLARIFICATION]` marker was opened and the Decision Moment Protocol
   (mint/resolve/defer a decision per question) was not exercised — there was no question to open a
   decision for. This is stated explicitly in plan.md's Summary section rather than left implicit.
6. Skipped Phase 0 (`research.md`) and Phase 1 design artifacts (`data-model.md`, `contracts/`,
   `quickstart.md`) for the same reason: zero `[NEEDS CLARIFICATION]` markers to resolve, zero new
   entities (the three touched data shapes — `PositionalCallViolation`,
   `AnalysisReportResult.input_artifacts`, `specify_cli.dossier.__all__` — are all pre-existing per
   spec.md's Key Entities section; this mission changes field *semantics*, not shape), and zero new
   API/contract surface. plan.md states this disposition explicitly under "Phase 0/1 artifacts"
   rather than generating placeholder files or silently omitting the topic.
7. Structured the plan's Implementation Concern Map as three ICs mapped 1:1 to the mission's own
   three independently-diagnosed GitHub issues (#3676 → IC-01, #3677 → IC-02, #3678+SK-63 → IC-03)
   rather than one IC per file, because the file-level grouping already matches the issue-level
   grouping exactly (each issue's fix lives in a disjoint file set from the other two issues' fixes)
   — a finer-grained IC split would not have added planning value. Recorded each IC's
   sequencing/depends-on as "none" against the other two ICs (verified: no shared file, no shared
   call path across ICs) but noted the *internal* coupling within IC-03 between FR-007's
   implementation and its five dependent test-assertion updates, since those cannot be sequenced
   apart from each other.
8. Verified the open-PR-overlap claim independently rather than trusting the pre-supplied summary
   as final: re-ran `gh pr list` and cross-checked file overlap for the one PR (#3672) flagged as
   touching a shared file, confirming it is this mission's own stacked base (per spec.md D2) and
   not a concurrent lane.
9. Every requirement in the plan is written with the RED-before-GREEN, non-raising-contract-first,
   and no-silent-fallback framing threaded through explicitly (§591 ATDD-First sequencing section,
   the NFR-002 test-strategy row, the Revert Discipline section) rather than left as an implicit
   assumption a reviewer would have to reconstruct.

## What the plan deliberately did not re-litigate

- Branch/target topology (`single_branch`, stacked on PR #3672) — fixed at scaffold time per spec.md
  D2; the plan's Branch Contract section restates the resolved values from the `setup-plan --json`
  payload rather than re-deciding anything.
- The #3678 fix-direction (conforming commit subject vs. `commitlint.config.cjs` ignore-list
  widening) — already resolved in spec.md's Grounding Correction 4 in favor of the conforming-
  subject approach; the plan cites that resolution rather than re-weighing the two options.
- The `charter` entry's `canonical_root`-vs-`repo_root` relativization root — already resolved in
  spec.md's Grounding Correction 3 (the #1823 cross-root behavior must be preserved); the plan's
  IC-03 risk note restates this as an implementation caution, not a fresh design choice.
