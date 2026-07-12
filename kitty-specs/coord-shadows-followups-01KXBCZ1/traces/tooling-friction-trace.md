# Tooling-Friction Trace — coord-shadows-followups

Witnessed spec-kitty friction during this mission. Entry format:
`[date][phase] SYMPTOM — anchor — disposition (fixed PR#/ticket#/workaround/open)`

Seed → append-during-implement → assess-at-close. Tracked under #2095.

## Seed (planning)

- `[2026-07-12][specify]` `mission create` produced `topology: coord` + a coordination branch even WITHOUT `--pr-bound` on a non-primary branch — anchor `core/mission_creation.py` default `coord` — workaround: flattened canonically (remove `coordination_branch` key + `flattened:true`, delete empty coord branch, delete stale `topology`, re-run `migrate backfill-topology --mission` → `single_branch`). OPEN question for #2160: should a fork/feature-branch mission default to coord? (This mission's whole theme is reducing coord-husk friction.)
- `[2026-07-12][plan]` `setup-plan` scaffolds `plan.md` then immediately returns `blocked` until substantive — the exact scaffold→block dance tracked as #2566 (EXCLUDED from this mission, but witnessed here first-hand) — disposition: expected, #2566 owns it.

## Append (implement)

- `[2026-07-12][implement]` `agent action implement WP01` initially BLOCKED: `analysis_report_required` — the implement gate needs `analysis-report.md` (from `/spec-kitty.analyze`) which the spec→plan→tasks flow does not auto-produce. Anchor: `agent action implement` gate. Disposition: workaround — authored + recorded the analysis report via `agent mission record-analysis`; the recorder parsed verdict as `unknown` (severity keywords in prose outside table cells) but implement accepted it. Minor: the analyze step isn't surfaced as a required step in the tasks→implement handoff.
- `[2026-07-12][implement]` `move-task WP03 --to for_review` runs a SYNCHRONOUS scoped pre-review-gate pytest (`tests/architectural/test_execution_context_parity.py tests/cli tests/specify_cli/cli`, multi-minute) that reads as a hang — the documented #2573 friction, witnessed first-hand. Anchor: `_mt_run_pre_review_gate`. Disposition: OPEN, tracked #2573 (not in this mission's scope; C-004 fences WP03 away from that function). Backgrounded it and continued.
- `[2026-07-12][implement]` Lane worktree testing: bare `pytest`/`python` in a lane worktree imports the PRIMARY checkout's editable install, not the lane's edits; `uv run` inside the lane builds a lane-local venv pointing at lane src (correct). Anchor: `.worktrees/<slug>-lane-*`. Disposition: workaround (instructed all implementers to use `uv run`); consistent with [[project_lane_bare_python_imports_primary]].
- `[2026-07-12][review]` `move-task --to approved` blocked twice on the issue-matrix gate: (a) `issue-matrix.md` auto-scaffolds every referenced issue with verdict `unknown` and requires manual fill before ANY WP can be approved (a mission-level artifact gating the FIRST per-WP approval); (b) a `deferred-with-followup` row is rejected unless its evidence_ref contains a `#NNN` / `Follow-up:` handle. Anchor: acceptance/approve gate + `issue-matrix.md`. Disposition: workaround (filled verdicts + added follow-up handles). Friction: the first WP approval is gated on a whole-mission artifact.
- `[2026-07-12][review]` `move-task --to approved` also blocked on "Commit these files before moving to approved" for uncommitted `kitty-specs/` planning artifacts (tracer/matrix edits) even though they are not the WP's code. Anchor: approve pre-flight clean-tree check. Disposition: workaround (committed kitty-specs). Friction: mission-level doc edits during implement re-block per-WP approvals.
- `[2026-07-12][review]` pre-review-gate returned `unverified_baseline — baseline uncomputable — surfacing all current failures as unverified` (parallel lanes + dirty tree → no clean baseline). Anchor: `_mt_run_pre_review_gate` baseline computation. Disposition: advisory, non-blocking (per [[feedback_coverage_is_indicative]]); moved to for_review anyway. Related #2573.

## Assess (close)

<!-- fill at mission close: which frictions recurred, which are worth escalating -->
