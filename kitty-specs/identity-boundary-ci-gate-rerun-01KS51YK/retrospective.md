# Retrospective — identity-boundary-ci-gate-rerun-01KS51YK

**Date**: 2026-05-21
**Mission**: Identity-Boundary CI Gate (Rerun)
**Tracker**: [`Priivacy-ai/spec-kitty#1247`](https://github.com/Priivacy-ai/spec-kitty/issues/1247)
**Prior attempt**: closed PRs spec-kitty#1252, saas#261, events#35 (ceremony bypass)

## Outcome

- Three open PRs returned to orchestrator:
  - `Priivacy-ai/spec-kitty` #1267
  - `Priivacy-ai/spec-kitty-events` #36
  - `Priivacy-ai/spec-kitty-saas` #264
- Mission directory pushed to `Priivacy-ai/spec-kitty:mission/identity-boundary-ci-gate-rerun` (planning branch).
- Verdict: mission-review = PASS WITH NOTES; intent-vs-outcome = matched.
- Operating-rule violations: zero.
- Canonical main pollution: none observed (all 3 sibling repos' local main unchanged).

## What went well

- **Formal ceremony invoked end-to-end.** Every required skill (`/spec-kitty.specify`, `/spec-kitty.plan`, `/spec-kitty.tasks`, `/spec-kitty.analyze`, `ad-hoc-profile-load reviewer-renata`, `/spec-kitty-mission-review`) was actually invoked rather than synthesized inline. This was the explicit asymmetric improvement vs. the prior attempt.
- **Planning-branch mitigation worked.** Switching the canonical spec-kitty repo to `mission/identity-boundary-ci-gate-rerun` BEFORE invoking `spec-kitty agent mission create` kept all planning commits off local `main`. Verified with `git log main --oneline -1` returning the same hash as before the run.
- **R-005 (sibling-PR collision recheck at PR-open time) caught a real risk class.** No collisions occurred, but the pre-flight check was the right discipline.
- **One Renata iteration was enough.** Renata returned 5 findings (3 LOW edits applied immediately, 1 N/A per brief, 1 procedural to Phase 9). No re-run required.
- **Lane parallelism.** finalize-tasks computed lanes a/b/c/planning; the runtime claimed each WP's lane workspace cleanly. The fact that WP02/WP03 were cross-repo (worktrees outside the lane workspace) required a `--force` on `move-task`; documented as runtime-vs-cross-repo divergence in the WP body and reflected in mission-review I1.

## What was bumpy

- **Cross-repo WPs and the runtime's worktree allocator.** The runtime creates `.worktrees/<mission>-lane-{a,b,c}/` inside the spec-kitty repo, but WP02 and WP03 land in sibling repos. The lane workspaces were correctly created but unused; the actual implementation worktrees (`spec-kitty-events.wt-canary-gate-rerun/`, `spec-kitty-saas.wt-canary-gate-rerun/`) were created manually. This works but feels like the runtime isn't fully aware of the multi-repo case. The brief's PR target frontmatter (events/saas main) was overwritten by the runtime normalizer back to the planning-branch target; mitigated via body-text `branch_strategy` clarification (Renata R-003).
- **`move-task --force` required for cross-repo WPs.** The runtime's cleanliness pre-flight checks the in-repo lane workspace, which was untouched for WP02/WP03. `--force` is the right escape hatch for cross-repo cases but felt like skipping a safety check; documented inline in each move-task `--note`.
- **Planning workflows are not idempotent against the empty-template scaffold.** `setup-plan` returned `phase_complete=false, plan_substantive=false` until I overwrote the plan.md template with real Technical Context content. That's correct gating but the failure mode was a CLI block on a freshly-scaffolded file with no human cue. Likely a CLI doc improvement opportunity.

## What would I do differently next time

- **Set up the planning branch on the canonical repo BEFORE the first CLI call.** The branch-context CLI reports `current_branch: main` when the canonical repo is on main, even when the agent's worktree is on a lane branch. That's by design (planning happens at canonical level), but it's a sharp edge. Pre-creating the planning branch is the mitigation. The mission brief should call this out as Phase 0.5.
- **For cross-repo missions, document the dual-worktree pattern explicitly.** The runtime creates a lane workspace inside the spec-kitty repo; the implementer also needs a worktree inside each sibling repo. Both are necessary; neither replaces the other. The brief implied this but it's worth a doctrine pack.
- **Renata's R-005 (recheck sibling PRs at PR-open) should be a CLI guard, not a manual procedural check.** A `spec-kitty agent action open-pr` wrapper that re-lists open PRs in the target repo and warns on filename collisions would be cheap and high-value.

## Drift hazards surfaced (for `#1198` consideration)

- **The "PR target divergence" pattern in cross-repo WP frontmatter.** The runtime's `merge_target_branch` field is the in-mission state-machine target (always the planning branch). The actual PR target is whatever the implementer pushed to. Frontmatter `branch_strategy` body text is the canonical narrative; readers of frontmatter alone can be misled. Not a defect (this mission), but a category that may recur for any cross-repo workflow.
- **Empty `owned_files` glob warnings during finalize-tasks.** When a WP's owned files don't exist yet on the canonical repo (which is the case for any WP that creates new files), finalize-tasks emits "matches zero files" warnings. They're warnings not errors, but they're noise that could mask real ownership-conflict warnings.

## Closing artifact pointer (this file)

This retrospective is committed on `mission/identity-boundary-ci-gate-rerun`
in the spec-kitty repo at
`kitty-specs/identity-boundary-ci-gate-rerun-01KS51YK/retrospective.md`.

The canonical YAML retrospective at
`.kittify/missions/01KS51YKDSHF73EBDMFSFH3RMP/retrospective.yaml` will be
authored at merge time by the runtime terminus, NOT now (the brief says DO
NOT MERGE; the YAML is for post-merge). Mission-review.md documents the
follow-up: `spec-kitty retrospect create --mission identity-boundary-ci-gate-rerun-01KS51YK`
at orchestrator-merge time if the automatic capture fails.
