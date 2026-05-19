# Implementation Plan: Investigate canary follow-ups #1142 and #1141

**Branch**: `main` | **Date**: 2026-05-19 | **Spec**: [spec.md](./spec.md)
**Mission ID**: `01KS02TVCYPQXQ9DX1Z39SXZ6K`
**Mission slug**: `investigate-canary-followups-1142-1141-01KS02TV`

## Summary

Honor two operator commitments carried over from the `unblock-sync-identity-boundary-canary-01KRZJ07` Gate 3 mission exception: investigate canary issue **#1142** (scenarios 1+2 `FORBIDDEN_KEY` block, 7-day window, ranked hypotheses H1→H2→H3) and canary issue **#1141** (scenario 4 lifecycle rollback contract, 14-day window, ranked H4→H3→H2→H1). Deliverables are evidence-backed GitHub issue comments plus a `mission-exception.md` `## Follow-up` update on the focused-PR branch — **not** spec-kitty source-code changes. If a hypothesis surfaces a real code defect, a separate 1-WP follow-up mission is opened.

Approach: cheapest-first hypothesis testing per the order recorded in each issue body. The mission's own commits to `main` are limited to spec/plan/tasks artifacts and the removal of `NEXT-AGENT-HANDOFF.md`.

## Technical Context

**Language/Version**: Python 3.11+ (host) — investigation does not commit code unless a follow-up mission is opened
**Primary Dependencies**: `spec-kitty` CLI (this repo), `gh` CLI (GitHub interactions), `pytest` (canary scenario re-runs), `pip` + `venv` (clean canary install per #1142 H1)
**Storage**: Filesystem only — markdown artifact at `kitty-specs/unblock-sync-identity-boundary-canary-01KRZJ07/mission-exception.md` (on focused-PR branch) plus GitHub issue comments
**Testing**: Re-uses `Priivacy-ai/spec-kitty-end-to-end-testing` pytest suite (scenarios 1, 2, 4). No new tests authored by this mission.
**Target Platform**: macOS / Linux operator workstation with Python 3.11+, network access to GitHub, and `gh` authenticated against `Priivacy-ai/spec-kitty`
**Project Type**: single (investigation/runbook within spec-kitty repo)
**Performance Goals**: NFR-004 — #1142 H1 repro completes (`pip install` + `pytest` scenarios 1+2) in ≤ 15 minutes wall-clock
**Constraints**: NFR-001 / NFR-002 — #1142 substantive comment by **2026-05-26**; #1141 by **2026-06-02**. NFR-003 — each comment must be reproducible by a reviewer in ≤ 15 minutes from the comment alone.
**Scale/Scope**: 2 GitHub issues, 1 cross-branch markdown edit, 1 mission-local handoff cleanup; estimated ≤ 1 operator-day total wall-clock if H1 confirms on #1142 and H4 explains #1141.

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Charter context (`spec-kitty charter context --action plan`) returned `software-dev-default` template set, languages=`python`, tools=`git, mypy, pytest, ruff, spec-kitty`, 13 directives (DIR-001…DIR-013) in scope.

Relevant directives for an investigation mission with cross-branch artifact rules:

| Directive area | Relevance | Plan compliance |
|---|---|---|
| Branch Strategy (3.x) | Mission lives on `main`; `mission-exception.md` update lives on `kitty/pr/unblock-sync-identity-boundary-canary-01KRZJ07-to-main` | Plan explicitly partitions writes by branch — see Project Structure → Cross-branch artifacts. No write to `mission-exception.md` from `main`. |
| Pre-existing Failure Reporting | If H1 confirms on #1142, the operator trap (stale canary venv) is a pre-existing operator-process failure, not a regression | Plan records this as a *closing fix-pattern comment*, not as a new issue file. |
| Tracker Ticket Assignment | Each WP carries the GitHub issue link in its description | Tasks-phase will set per-WP `external_ref` to `#1142` / `#1141`. |
| Identifier Safety Rules | No identifier renames in this mission (not a bulk-edit). `meta.json` `change_mode` stays at default. | No `occurrence_map.yaml` required. |
| ATDD-First Discipline (C-011) | Acceptance test = "issue comment satisfies NFR-003 reproducibility" + "scenarios re-run with documented outcome" | Each WP's Definition of Done references NFR-003 verbatim. |
| Burn-down Policy (HiC §5a.2 / C-004) | Mission inherits an exception-pack ratchet from parent mission | Plan does NOT add new ratchet entries; it consumes one operator-commitment row from `mission-exception.md`. |

**Gate result**: PASS. No charter violations require Complexity Tracking entries.

**Charter file status**: `.kittify/charter/charter.md` is referenced by the doctrine service via `software-dev-default`; loaded compact context, `references_count=0` (no on-demand pulls needed for this plan).

## Project Structure

### Documentation (this feature)

```
kitty-specs/investigate-canary-followups-1142-1141-01KS02TV/
├── spec.md                                       # committed (specify phase)
├── plan.md                                       # this file (plan phase)
├── meta.json                                     # mission identity (committed by `mission create`)
├── status.events.jsonl                           # canonical event log
├── research/                                     # phase 0 artifacts
├── research.md                                   # phase 0 consolidated findings
├── data-model.md                                 # phase 1 — investigation outcome record shape
├── quickstart.md                                 # phase 1 — operator runbook
├── contracts/
│   ├── issue-comment-shape.md                    # required shape for the #1142/#1141 comments
│   └── follow-up-update-shape.md                 # required shape for the mission-exception.md update
├── checklists/
│   └── requirements.md                           # spec-quality checklist (already green)
└── tasks/                                        # populated by /spec-kitty.tasks
```

### Cross-branch artifacts (not in this mission's worktree on `main`)

```
kitty-specs/unblock-sync-identity-boundary-canary-01KRZJ07/
└── mission-exception.md                          # `## Follow-up` updated on branch
                                                  # `kitty/pr/unblock-sync-identity-boundary-canary-01KRZJ07-to-main`
                                                  # (or successor if PR #1143 merges first)
```

GitHub-side artifacts (no local file representation):

```
github.com/Priivacy-ai/spec-kitty/issues/1142    # substantive comment + (conditional) close
github.com/Priivacy-ai/spec-kitty/issues/1141    # substantive comment with A/B/C recommendation
```

### Source Code (repository root)

```
src/specify_cli/                                  # READ-ONLY in this mission
├── status/lifecycle_events.py                    # walked by #1142 H2 against WP01 predicate
├── status/store.py                               # compared by #1141 H2 against canary expectation
├── invocation/propagator.py                      # walked by #1142 H2
├── dossier/                                      # walked by #1142 H2
├── next/_internal_runtime/engine.py              # walked by #1142 H2
├── retrospective/events.py                       # walked by #1142 H2
└── cli/commands/agent/tasks.py                   # inspected by #1141 H1 (recent backward-transition changes)
```

External canary repo (read-only checkout into `/tmp/canary-clean/...` for #1142 H1):

```
Priivacy-ai/spec-kitty-end-to-end-testing/
└── tests/identity_boundary/
    ├── test_scenario_1_*.py                      # re-run by #1142 H1
    ├── test_scenario_2_*.py                      # re-run by #1142 H1
    └── test_scenario_4_review_rejection_contract.py  # read by #1141 H4/H3/H2
```

**Structure Decision**: Single-project, investigation-only. No `src/` writes from this mission; the only file edits are this feature's own kitty-specs artifacts (on `main`) and one cross-branch markdown edit on the focused-PR branch. No new module layout, no new dependencies, no test scaffolding — the canary repo's existing pytest tree is the testing surface.

## Phase Plan

### Phase 0 — Research

Outputs: `research.md`, optional rows under `research/`.

Research tasks are scoped to the questions the mission already knows are unresolved, not generic technology trade-offs:

1. **Pin the parent-mission exception state** — quote the exact `## Follow-up` row from `mission-exception.md` on the focused-PR branch so the WP02/WP01 ATDD checks have an unambiguous reference string to update.
2. **Cite the canonical hypothesis bodies** — fetch and snapshot the current text of #1142 and #1141 issue bodies (since they are authoritative on hypothesis numbering and `mission-review.md` already cross-refs them).
3. **WP01 predicate restatement** — record the canonical predicate `aggregate_type == "Mission"` AND `event_type` non-empty, with a literal pointer to the source line in `src/specify_cli/...` that defines it, so #1142 H2 has one reference to walk emitters against.
4. **Cross-branch update mechanics** — document the exact sequence (`git fetch`, `git checkout`, edit, `git commit`, `git push`) and the conditional branch (i.e., if PR #1143 has merged before the operator gets to FR-007, the edit lands on `main` via a fresh PR off `main` rather than the focused-PR branch).

No technology comparisons are needed — the stack is fixed by the parent mission.

### Phase 1 — Design & Contracts

Outputs: `data-model.md`, `contracts/issue-comment-shape.md`, `contracts/follow-up-update-shape.md`, `quickstart.md`.

**Data model** is light: one "Investigation Outcome" record per issue, capturing hypothesis-tested, evidence-URI(s), conclusion, and downstream-action.

**Contracts** are markdown shape contracts, not OpenAPI:
- `issue-comment-shape.md` — required headings/fields in the comment that satisfies NFR-003 (Hypothesis, Commands, Evidence, Conclusion).
- `follow-up-update-shape.md` — the diff shape for `mission-exception.md` `## Follow-up`: how a deferred commitment row is rewritten to a resolved row, including the link back to the issue comment.

**Quickstart** is the operator runbook — a copy-paste-able sequence that produces the H1 evidence file used in the #1142 issue comment.

## Risks & Mitigations

| Risk | Likelihood | Mitigation |
|---|---|---|
| `gh` CLI lacks `repo` scope on org repo | Medium | Per CLAUDE.md: `unset GITHUB_TOKEN && gh auth status` to fall back to keyring token; documented in quickstart. |
| PR #1143 merges before FR-007 lands | Low | Plan explicitly conditionalizes the write target — `mission-exception.md` lives on `main` post-merge; quickstart documents both paths. |
| H1 false positive on #1142 | Medium | NFR-003 evidence rule + spec's "repro twice" guidance; the comment must include both pip install log and pytest log. |
| Operator workstation pollutes existing canary venv | Low | H1 procedure uses a fresh `/tmp/canary-clean/` scratch dir; no reuse of any existing canary venv. |
| Repo state drifted from handoff snapshot | Medium | FR-008 mandates the four pre-flight checks (clean tree, `0 0` divergence, `HEAD == f51745df0`, focused-PR branch present) before any repro runs. |
| Window expires without conclusion | Medium | Mission permits a "what has been ruled out so far" comment inside the window; that satisfies NFR-001/NFR-002 even when investigation continues. |

## Complexity Tracking

*No Charter Check violations — table intentionally empty.*

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| (none) | — | — |
