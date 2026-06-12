---
work_package_id: WP01
title: Issue Hygiene and Follow-Up Umbrella
dependencies: []
requirement_refs:
- FR-011
tracker_refs: []
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
agent: "claude:fable-5:reviewer-renata:reviewer"
shell_pid: "85716"
history:
- '2026-06-12: created by /spec-kitty.tasks'
agent_profile: curator-carla
authoritative_surface: docs/development/
execution_mode: planning_artifact
owned_files:
- docs/development/3-2-coord-merge-issue-hygiene-log.md
role: curator
tags: []
---

# WP01 — Issue Hygiene and Follow-Up Umbrella

## ⚡ Do This First: Load Agent Profile

Before reading further, load your assigned profile:

```
/ad-hoc-profile-load curator-carla
```

Adopt its initialization declaration, boundaries, and governance scope for this WP. You are curating tracker state, not writing production code.

## Objective

Make the GitHub tracker reflect code reality for the 13-issue Coordination & Merge cluster (FR-011): close the seven issues whose defects are already fixed at HEAD, re-scope the four partially-fixed issues to their residuals, file ONE follow-up architecture umbrella under epic #1666, and record every action in a committed hygiene log.

## Context

A Debbie/Paula validation pass (2026-06-12) proved most of the cluster was drained by PR #1850 (commit `8544012fa`), rc41 (`c5a10ce56`), rc42 (`9c8bff06f`), and PR #1719. Validation comments with file:line evidence were already posted to all 13 issues — your job is the disposition, not re-analysis. Authoritative disposition table: `kitty-specs/coordination-merge-stabilization-01KTXRVR/validation/cluster-validation-brief.md` §2 (in-scope/exclusions) and research.md R8.

Repo: `Priivacy-ai/spec-kitty`. Use `gh`. If `gh` hits scope errors: `unset GITHUB_TOKEN` first (keyring token has full repo scope).

## Subtasks

### T001 — Close the seven fixed issues

For each, post a short closing comment citing the landed fix (the validation comment on the issue already carries the detailed evidence — reference it), then close:

| Issue | Close citation |
|---|---|
| #1770 | PR #1793 (`c5a10ce56`, FR-035/FR-037 tempdir bake) + PR #1850 accept anchor |
| #1789 | PR #1850 WP11/WP12 (`8544012fa`): git-op guard, write-free dashboard materialize, scoped reaper |
| #1816 | PR #1850 WP06 unified CommitTarget/FLATTENED classification |
| #1771 | PR #1850 WP08 (FR-006 canonical tracked path; `test_record_committable_1771.py`) |
| #1571 | PR #1719 push-gated sync preflight; superseded by #1706 |
| #1784 | duplicate of #1777; core fixed by PR #1850 `resolve_placement_only`; P3 crumbs carried in mission 01KTXRVR WP02/WP03 |
| #1735 | core fixed by PR #1850 WP08; residuals carried in mission 01KTXRVR WP05 **and** listed in the T003 umbrella — cite BOTH in the closing comment so tracking survives if WP05 is ever deferred (analysis finding U2) |

Closing comment shape: one sentence "Fixed at HEAD by <citation>; validation evidence in the 2026-06-12 cluster-validation comment above. Residuals (if any) tracked in mission coordination-merge-stabilization-01KTXRVR <WP>." Use `gh issue close <n> --comment "..."`.

### T002 — Re-scope the four partially-fixed issues

For #1814, #1736, #1833, #1861: edit title (prefix `residual:` or equivalent) and prepend a body section "## Re-scoped 2026-06-12" stating what landed (with commit), what remains, and which mission WP carries it:

- **#1814** → residual: finalize staging leaves `lanes.json`/`tasks/*` residue on primary (mission WP02/T008). Status-file deadlock fixed by #1850 WP06.
- **#1736** → residual: `_make_merge_env` extraction, narrow `status_transition.py:399` except, mixed-timestamp ratchet (mission WP03/T015-T017). Bugs A/B/C fixed (`a5f30616e`/`c5a10ce56`/`8544012fa`).
- **#1833** → residual: husk fall-through guards + doctor check (mission WP04). F-001 naming trigger fixed in #1850.
- **#1861** → residual: Part 1 validate-only guard (mission WP02/T006). Part 2 already resolved by `SafeCommitHeadMismatch` (`8e79b3f6d`) — record explicitly (AC-C3).

Use `gh issue edit <n> --title ... --body ...` (fetch current body first; prepend, don't destroy).

### T003 — File the follow-up umbrella under epic #1666

One new issue titled approximately "Umbrella: complete the coordination placement/identity strangler (post-3.2.0)". Body lists the C-001 deferred non-goals from spec.md / paula-analysis.md follow-up section: resolver strangler completion (`gate.py`, `agent_retrospect.py`, implement.py C-004 fallback — note WP05 of this mission resolves the first two; scope accordingly), single ref-advance helper rollout beyond the merge pipeline, worktree-naming allocator unification, is-a-worktree type invariant, AC10 lint expansion, `_ensure_branch_checked_out` shim retirement, #1827 crash-between-record-and-commit edge, #1784 P3 polish not carried by WP02. Include explicit **Non-goals** (no topology redesign, no safe-commit semantics change) and link epic #1666 + this mission. Label per repo conventions; assign nobody.

**Additionally (analysis finding I2)** — include a "Fresh evidence, 2026-06-12 planning session" section recording three further live instances of the #1784/Class A family observed first-hand while planning this very mission:

1. **Coord-unaware setup-plan entry gate**: `is_committed()` (`src/specify_cli/missions/_substantive.py:214-239`) checks only the primary checkout's HEAD; a spec.md committed on the coordination branch is reported uncommitted, blocking `setup-plan` until the operator manually fast-forwards local main.
2. **setup-plan auto-commit fallback divergence**: the plan auto-commit path inside `setup-plan` refused with the protected-main error even though direct invocation of `_planning_commit_worktree` + `_resolve_planning_placement` routes correctly to the coordination worktree — some call path inside setup-plan bypasses or falls back around the #1784 catch-22 fix.
3. **Lifecycle event emission targets protected main**: the phase-event emission during `setup-plan` attempted a safe_commit against the primary main checkout and only succeeded under `SPEC_KITTY_ALLOW_PROTECTED_BRANCH_COMMITS=1`.

Also observed (same session, adjacent classes): `record-analysis` refuses on ANY untracked primary-checkout file (the #1814 mechanism, confirmed live), and `mission create` leaves a `tasks/.gitkeep` scaffold that later trips dirty-tree gates. Cite `kitty-specs/coordination-merge-stabilization-01KTXRVR/analysis-report.md` finding I2.

### T004 — Hygiene log artifact

Write `docs/development/3-2-coord-merge-issue-hygiene-log.md`: a table of every action (issue, action taken, citation, URL, timestamp) plus the umbrella issue URL. Commit it via the coordination worktree:

```bash
cd .worktrees/coordination-merge-stabilization-01KTXRVR-coord
# copy the file in, then:
spec-kitty safe-commit --to-branch kitty/mission-coordination-merge-stabilization-01KTXRVR \
  --message "WP01: issue hygiene log" docs/development/3-2-coord-merge-issue-hygiene-log.md
```

## Definition of Done

- [ ] 7 issues closed, each with citation comment (T001)
- [ ] 4 issues re-titled/re-scoped with residual sections (T002)
- [ ] Umbrella issue filed under epic #1666 with non-goals (T003)
- [ ] issue-hygiene-log.md committed; every action has a URL (T004)
- [ ] Zero code changes in this WP

## Risks & Reviewer Guidance

- **Wrong citation = future triage confusion.** Reviewer: spot-check 3 closures against `git log` for the cited SHAs.
- Do NOT close #1826 or modify its scope — it is fixed by WP03 of this mission, not by hygiene.
- Reviewer: verify the umbrella issue does not duplicate an existing open architecture issue under #1666 before approving.

## Activity Log

- 2026-06-12T11:57:31Z – claude:fable-5:curator-carla:curator – shell_pid=83127 – Started implementation via action command
- 2026-06-12T12:03:03Z – claude:fable-5:curator-carla:curator – shell_pid=83127 – Hygiene complete: 7 closed, 4 re-scoped, umbrella #1878 filed, log committed (7714776)
- 2026-06-12T12:03:41Z – claude:fable-5:reviewer-renata:reviewer – shell_pid=85716 – Started review via action command
