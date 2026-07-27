# Mission Specification: Investigate canary follow-ups #1142 and #1141

**Mission ID**: `01KS02TVCYPQXQ9DX1Z39SXZ6K`
**Mission slug**: `investigate-canary-followups-1142-1141-01KS02TV`
**Mission type**: `software-dev`
**Target branch**: `main`
**Created**: 2026-05-19

## Purpose

**TLDR**: Honor the 7- and 14-day operator commitments to investigate canary follow-ups #1142 and #1141.

**Context**: Mission `unblock-sync-identity-boundary-canary-01KRZJ07` deferred NFR-003 ("canary scenarios 1, 2, 4 turn green on a re-run against the rc bump") via a Gate 3 mission exception. The exception was accepted on the condition that two open canary issues are investigated inside operator-committed windows:

- `#1142` — Canary scenarios 1+2 hit `TeamSpace FORBIDDEN_KEY` block even though the WP01 fix verifies clean in direct repro (**7-day window**).
- `#1141` — Canary scenario 4 tests lifecycle rollback emission contract not covered by mission spec (**14-day window**).

The operator commitments are recorded in `kitty-specs/unblock-sync-identity-boundary-canary-01KRZJ07/mission-exception.md` (`## Follow-up` section) and `mission-review.md` (`## Open items`). Those files live on the focused-PR branch `kitty/pr/unblock-sync-identity-boundary-canary-01KRZJ07-to-main` (PR #1143) — they are not on `origin/main` yet.

This mission delivers those investigations end-to-end: cheapest-first hypothesis tests, evidence-backed comments on each issue, and an updated `## Follow-up` section.

## User Scenarios & Testing

### Primary scenario — #1142 investigation (7-day window)

1. Operator opens issue #1142 and reads the three ranked hypotheses (H1 stale canary venv → H2 missing lifecycle row → H3 spec-kitty regression).
2. Operator executes H1 first: provisions a clean canary venv in a scratch directory, clones `Priivacy-ai/spec-kitty-end-to-end-testing`, installs the spec-kitty CLI from the focused-PR working tree as a non-editable build, and runs only scenarios 1 and 2.
3. If H1 turns the scenarios green, operator closes #1142 with a fix-pattern comment that names "rebuild the canary venv between runs; do not `pip install --force-reinstall --no-deps` into a prior venv" as the trap.
4. If H1 is still red, operator advances to H2: walks each lifecycle event emitter (`src/specify_cli/status/lifecycle_events.py`, `src/specify_cli/invocation/propagator.py`, `src/specify_cli/dossier/`, `src/specify_cli/next/_internal_runtime/engine.py`, `src/specify_cli/retrospective/events.py`) and verifies every emitted row satisfies the WP01 predicate (`aggregate_type == "Mission"` AND `event_type` non-empty). If a non-conforming emitter is found, operator opens a 1-WP follow-up mission to extend the predicate and links it from #1142.

### Primary scenario — #1141 investigation (14-day window)

1. Operator reads scenario-4 source `tests/identity_boundary/test_scenario_4_review_rejection_contract.py` end-to-end.
2. Operator executes hypotheses in the order **H4 (fixture state error) → H3 (sequencing race) → H2 (canary drift) → H1 (CLI regression)**, because each check is cheaper than the next.
3. H4: confirm the fixture actually reaches `in_review` (not `for_review`).
4. H3: inspect the peek-the-queue assertion (canary line 543) for a race against the `move-task` write.
5. H2: compare expected `WPStatusChanged` payload shape against current spec-kitty emission in `src/specify_cli/status/lifecycle_events.py` and `src/specify_cli/status/store.py`.
6. H1: if H4/H3/H2 all rule out, walk `git log --oneline -- src/specify_cli/status/store.py src/specify_cli/cli/commands/agent/tasks.py` for recent backward-transition row emission changes.
7. Operator records the conclusion on #1141 with one of three recommendations: (A) new mission, (B) patch canary, (C) already a small fix.

### Edge cases

- **Repo not in expected starting state**: Before any investigation, operator verifies `git status` is clean, `git rev-list --left-right --count main...origin/main` is `0 0`, local `HEAD` on `main` is `f51745df0`, and the focused-PR branch is still present. If any check fails, operator stops and resolves drift before running hypothesis repros.
- **H1 false positive on #1142**: Operator captures the full pip install log alongside the pytest log so that "stale install" can be proved vs. "happens to pass once" — H1 is only confirmed when a fresh venv reproduces green twice in a row.
- **Investigation finishes inside window but produces a code patch**: Patch must land via its own mission/PR, not this mission. This mission's deliverable is the investigation outcome (issue comment + exception follow-up update), not the patch.
- **Window expires without conclusion**: Operator must still post a status comment on the issue inside the window stating what has been ruled out and what is outstanding, and update `mission-exception.md` `## Follow-up` accordingly.

## Functional Requirements

| ID | Description | Status |
|---|---|---|
| FR-001 | Operator MUST execute the #1142 H1 clean-venv repro (fresh canary venv, non-editable spec-kitty install, scenarios 1+2 only) before any other #1142 hypothesis. | proposed |
| FR-002 | Operator MUST post a comment on #1142 inside the 7-day window stating: hypothesis tested, result, evidence (log excerpts), and conclusion. | proposed |
| FR-003 | If #1142 H1 turns scenarios 1+2 green, operator MUST close #1142 with a fix-pattern comment naming "rebuild the canary venv between runs" as the operator trap. | proposed |
| FR-004 | If #1142 H1 is still red, operator MUST execute H2 and inspect each named lifecycle emitter against the WP01 predicate; any non-conforming emitter triggers a linked 1-WP follow-up mission. | proposed |
| FR-005 | Operator MUST execute #1141 hypotheses in order H4 → H3 → H2 → H1 and stop at the first hypothesis that explains the failure. | proposed |
| FR-006 | Operator MUST post a comment on #1141 inside the 14-day window stating: hypothesis tested, result, evidence, conclusion, and one of the recommendations A/B/C from the issue body. | proposed |
| FR-007 | Operator MUST update `kitty-specs/unblock-sync-identity-boundary-canary-01KRZJ07/mission-exception.md` `## Follow-up` section on the focused-PR branch `kitty/pr/unblock-sync-identity-boundary-canary-01KRZJ07-to-main` with the outcome for each issue. | proposed |
| FR-008 | Before any hypothesis repro, operator MUST verify the starting repo state matches the snapshot recorded in this spec's Edge Cases (clean tree, `0 0` divergence, `HEAD == f51745df0`, focused-PR branch present). | proposed |
| FR-009 | Once `spec.md` is committed, operator MUST remove `NEXT-AGENT-HANDOFF.md` from the working tree (it is untracked-by-design and superseded by this spec). | proposed |
| FR-010 | If an investigation reveals a code change is required, the change MUST be delivered via a separate mission or PR — this mission's deliverable is investigation outcome only. | proposed |

## Non-Functional Requirements

| ID | Description | Measurable threshold | Status |
|---|---|---|---|
| NFR-001 | #1142 investigation latency. | First substantive comment on #1142 posted **≤ 7 days** from this mission's creation date (2026-05-19), i.e. **by 2026-05-26**. | proposed |
| NFR-002 | #1141 investigation latency. | First substantive comment on #1141 posted **≤ 14 days** from this mission's creation date (2026-05-19), i.e. **by 2026-06-02**. | proposed |
| NFR-003 | Evidence completeness on each issue comment. | Comment contains, at minimum: (a) the hypothesis label tested, (b) the exact commands run, (c) a log excerpt or file/line reference, (d) a yes/no conclusion. Reviewer can reproduce within 15 minutes from the comment alone. | proposed |
| NFR-004 | H1 repro cost on #1142. | Clean-venv repro completes (pip install + pytest scenarios 1+2) in **≤ 15 minutes** of wall-clock time on the operator workstation. | proposed |

## Constraints

| ID | Description | Status |
|---|---|---|
| C-001 | The focused-PR branch `kitty/pr/unblock-sync-identity-boundary-canary-01KRZJ07-to-main` is the only place `mission-exception.md` lives; updates to its `## Follow-up` section MUST land on that branch (or a successor PR branch), not on `main`. | proposed |
| C-002 | Out of scope: PR #1143 review/merge, PR #1154 review/merge, tool-issues #1145–#1153, and pre-existing-failure issues #1134/#1135. Side context only. | proposed |
| C-003 | This mission MUST NOT pre-commit to landing a code patch. If hypotheses converge on a clean-install fix-pattern (no code change), that is an acceptable terminal state for #1142. | proposed |
| C-004 | Hypothesis order is fixed: #1142 = H1 → H2 → H3; #1141 = H4 → H3 → H2 → H1. Cheapest-first discipline is non-negotiable. | proposed |
| C-005 | `NEXT-AGENT-HANDOFF.md` MUST NOT be committed to `origin/main`; it is removed (FR-009), not tracked. | proposed |

## Success Criteria

- **SC-001**: Issue #1142 has a substantive comment with hypothesis-tested, evidence, and conclusion posted by 2026-05-26.
- **SC-002**: Issue #1141 has a substantive comment with hypothesis-tested, evidence, conclusion, and a recommendation (A/B/C) posted by 2026-06-02.
- **SC-003**: `mission-exception.md` `## Follow-up` section on the focused-PR branch reflects the outcome of both investigations.
- **SC-004**: If #1142 resolves via H1, the closing comment explicitly names the operator trap so a future canary run does not repeat it.
- **SC-005**: `NEXT-AGENT-HANDOFF.md` is no longer present in the working tree once the mission spec is committed.

## Key Entities

- **Issue #1142** — Canary scenarios 1+2 FORBIDDEN_KEY block (7-day window, three ranked hypotheses).
- **Issue #1141** — Canary scenario 4 rollback contract drift (14-day window, four ranked hypotheses).
- **mission-exception.md (`## Follow-up`)** — Authoritative record of operator commitments; lives on focused-PR branch.
- **Focused-PR branch** `kitty/pr/unblock-sync-identity-boundary-canary-01KRZJ07-to-main` — Where the mission docs and the canary evidence currently sit; not yet on `origin/main`.
- **Canary repo** `Priivacy-ai/spec-kitty-end-to-end-testing` — Source of the failing scenarios; H1 repro provisions a clean venv against this repo.
- **WP01 predicate** — `aggregate_type == "Mission"` AND `event_type` non-empty; the lifecycle-row contract H2 of #1142 walks every emitter against.

## Domain Language

- **H1 / H2 / H3 / H4** — Hypothesis labels as numbered in the GitHub issue bodies. Do not renumber.
- **Operator trap** — A repeatable mistake an operator can make that produces a false-failure signal (e.g., reusing a stale canary venv). Recording the trap is the deliverable when H1 closes #1142.
- **Substantive comment** — An issue comment that satisfies NFR-003 (hypothesis label, exact commands, evidence, yes/no conclusion).
- **Fix-pattern** — Documented procedure that prevents a recurrence; for canary issues, this is operator-facing, not code-facing.

## Assumptions

- The starting repo state matches the snapshot in NEXT-AGENT-HANDOFF.md: `git status` clean (modulo the handoff doc itself), `main...origin/main = 0 0`, `HEAD = f51745df0`. The mission verifies this in FR-008 before any repro runs.
- Issue #1142 and #1141 bodies remain authoritative on hypothesis content; this spec does not re-state hypothesis details inline beyond what the procedures require.
- The focused-PR branch (#1143) is not yet merged when this mission begins; if it merges first, the `## Follow-up` update lands on `main` via that PR's history rather than a fresh PR.
- The investigation may produce no code patch at all (H1 confirm path on #1142). That outcome is success, not punt.

## Out of Scope

- PR #1143 (focused-PR for the parent mission's code) review and merge.
- PR #1154 (charter: "Run only the affected test packages") review and merge.
- Spec-kitty tool issues #1145 through #1153 (orchestrator-filed during the parent mission).
- Pre-existing-failure issues #1134 and #1135.
- Any code patch arising from an investigation (delivered via a separate mission/PR per FR-010 and C-003).
