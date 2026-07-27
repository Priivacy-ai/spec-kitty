# Mission Retrospective: coordination-merge-stabilization-01KTXRVR (mission 131)

**Date**: 2026-06-12 | **Facilitator**: claude:fable-5 (orchestrator) with operator Robert Douglass
**Status**: committed retrospective record. The gitignored `.kittify/missions/01KTXRVR2HPMKGMH20K18JZ1SA/retrospective.yaml` exists locally but is uncommittable (failure H.27, #1771 residual) and its generator found zero findings — this document and [workflow-failures-log.md](workflow-failures-log.md) (28 itemized failures with evidence) are the retrospective corpus.

## Mission outcome

Shipped as PR #1879 (squash `3f2af08f0` on origin/main): 5 WPs, 27 subtasks, 13/13 FRs test-covered, zero review rejection cycles, post-merge mission review verdict FAIL on 7 mechanical items remediated by a follow-up agent before merge. The mission fixed #1826 (the 3.2.0 release blocker), #1861 Part 1, and the residuals of #1833/#1814/#1736/#1735 — and in doing so, dogfooded the very workflow it was stabilizing, surfacing 28 live workflow failures.

## The one structural finding

**Split-brain between write and read surfaces under coordination topology.** Transitions and planning artifacts write to the coordination branch (PR #1850's placement resolver — which held perfectly all session), but nearly every gate, reader, and dashboard reads the primary checkout: the `is_committed` entry gate, `check-prerequisites`, the dashboard (#1572), `record-analysis`'s dirty check, and accept's git_dirty snapshot. This single asymmetry caused failures 1, 2, 5, 6, 9, 13, 24, 25 of the log and forced ~10 manual `git merge --ff-only` syncs (the "ff-merge treadmill" — the largest workflow tax observed). The read-side strangler is the core of umbrella **#1878**.

## Failures by phase (summary — full evidence in workflow-failures-log.md)

- **Planning**: coord-blind `is_committed` gate; setup-plan auto-commit falling back to protected main; lifecycle emission requiring the `SPEC_KITTY_ALLOW_PROTECTED_BRANCH_COMMITS=1` hatch; the canonical specify prompt prescribing a `safe-commit` invocation that cannot work on protected main (items 1–5).
- **Tasks/analyze**: split-surface anchoring between commands; `record-analysis` refusing on ANY unrelated untracked file (hit 3×, including spec-kitty's own scaffolds and daemon-rematerialized files); staleness gate re-firing on analyze's own recommended commits (items 6–12).
- **Implement/review**: stale dashboard; `spec-kitty next` returning an unusable query stub; missing `issue-matrix.md` scaffold forcing mid-review authoring; per-lane manual rebases as status commits advanced the mission branch (#771 family); `owned_files` accepting nonexistent paths (items 13–17).
- **Accept**: structurally self-defeating — mutates artifacts, then fails its own `git_dirty` snapshot; can never return ok under coordination topology; once regressed WP frontmatter; matrix scaffolded with placeholders and no CLI surface to record verdicts (items 18–20).
- **Merge**: mid8 selector not resolved (identity-contract violation); coordination worktree not cleaned (mission-branch delete fails); stale-assertion false positive on message-content assertions; 27 duplicate `.worktrees/<coord>/` paths leaked into the index (items 21–23, 28).
- **Post-merge**: terminus retrospective not generated despite the always-on directive; explicit `retrospect create` writes to the gitignored path; findings generator returned zero findings for a 28-failure mission (items 26–27).

## What worked (keep)

- The 9-lane status model, per-WP review prompts with correct diff bases, lane isolation, and the safe-commit backstop behaved exactly as designed — no inconsistent commit ever landed.
- PR #1850's placement resolver: zero #1784-class failures in any path that routes through it.
- Red-test-first per WP and independent adversarial review caught real issues (including this mission's own remediation list) with zero rejection-cycle churn.
- Parallel lane execution (4 code lanes + planning lane) with completion-driven review scheduling worked end-to-end.

## Meta-lesson

The gates are individually correct but compositionally hostile: each tool's own writes (accept's matrix, mission create's scaffolds, record-analysis's report, daemon materialization) become the next gate's blocker. The design principle for #1878: **a gate must never fail on state that spec-kitty itself wrote in the same workflow.**

## Disposition of findings

- Fresh evidence cross-posted to **#1878** (umbrella: coordination placement/identity strangler) and **#1771** (gitignored retrospect path) on 2026-06-12.
- Post-merge verification of which items are already fixed at `3f2af08f0` is recorded as a comment trail on #1878 (and in the session record); items confirmed fixed by this mission itself: #7 (validate-only checkout switch), #16's worst case (#1826 backstop aborts), husk fall-through misattribution, finalize residue deadlock subset.
- Everything else is tracked: #1878 (read-surface strangler, accept redesign, merge cleanup, mid8 resolver), #1572 (dashboard), #771 (lane staleness), #1764 (staleness gate), #1623 (doctor split).
