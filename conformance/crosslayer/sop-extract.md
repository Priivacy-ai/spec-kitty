<!--
SOP policy extract (FR-007, OQ-6 option (b)).

This file is a bounded, verbatim subset of the repo-root AGENTS.md's
operating-policy sections — small enough to sit alongside a persona and a
skill in a composed context window without the small-model risk the full
file (35,933 bytes at this mission's base commit) would pose. AGENTS.md
itself is a shared, read-only input; neither this extract nor its drift
check ever modifies it.

Extraction rule (must match conformance/scripts/check-sop-extract-drift.sh
exactly, mechanical and re-run-able by that script, not a judgment call
re-made by hand): for each AGENTS.md heading listed below, in order, every
line from the heading (inclusive) through the line immediately before the
next line that is exactly "---" (AGENTS.md's own section-separator
convention) is extracted verbatim, excluding that "---" line itself.

Sections extracted (in AGENTS.md heading order):
  1. "## ⚠️ CRITICAL: Git Workflow — No Direct Pushes to origin/main"
  2. "## Branch Protection and CI"

Regenerate with: bash conformance/scripts/check-sop-extract-drift.sh --write
-->

## ⚠️ CRITICAL: Git Workflow — No Direct Pushes to origin/main

**All changes to origin/main MUST go through pull requests. Direct pushes are prohibited.**

- `spec-kitty merge` merges to **local main** only. It does NOT push to origin/main.
- After `spec-kitty merge`, if the user explicitly asks to share or publish: create a PR branch (`git checkout -b pr/<slug>`) and open a pull request (`gh pr create`). Do NOT do this automatically — wait for explicit user instruction.
- Never run `git push origin main` or equivalent. Use a PR branch and `gh pr create`.
- Distinguish **local main** (your checkout) vs **origin/main** (the remote); qualify which branch you mean (see the `primary`/`merge` footgun note under Terminology Canon).

**Why:** The workflow is predicated on pull requests for review, CI gating, and audit trail. Direct pushes to origin/main bypass all of these.

**Recovery:** If you accidentally push to origin/main, do NOT force-push (branch protection blocks it). Instead: create a `revert/<slug>` branch from origin/main, commit a revert, open a PR to merge it, then open the real mission PR.


## Branch Protection and CI

`main` has a **Protect Main Branch** CI workflow that enforces the no-direct-push policy. A "Protect Main Branch" failure on CI means code bypassed the PR workflow and must be addressed by revert + re-submit.

- `spec-kitty merge` merges lane branches into **local main** only — do NOT use `spec-kitty merge --push` or `git push origin main`.
- After `spec-kitty merge` completes locally, create a PR branch: `git checkout -b pr/<slug> && git push origin pr/<slug>` and open a PR with `gh pr create`.
- The only CI result relevant to code health is **CI Quality**. The protect-main failure indicates a workflow violation.

**Recovery if origin/main is accidentally pushed:** Do NOT force-push (branch protection blocks it). Create a `revert/<slug>` branch from origin/main, commit a single revert, open a PR to merge it, then open the real PR from the mission branch.

