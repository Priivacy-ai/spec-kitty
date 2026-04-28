---
work_package_id: WP09
title: PR Creation & Issue Hygiene
dependencies:
- WP08
requirement_refs:
- FR-014
planning_base_branch: fix/charter-e2e-827-tranche-2
merge_target_branch: fix/charter-e2e-827-tranche-2
branch_strategy: Planning artifacts for this feature were generated on fix/charter-e2e-827-tranche-2. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/charter-e2e-827-tranche-2 unless the human explicitly redirects the landing branch.
subtasks:
- T041
- T042
- T043
- T044
agent: "claude:sonnet:curator-carla:curator"
shell_pid: "28017"
history:
- at: '2026-04-28T09:36:40Z'
  actor: spec-kitty.tasks
  event: created
agent_profile: curator-carla
authoritative_surface: kitty-specs/charter-e2e-hardening-tranche-2-01KQ9NVQ/notes/
execution_mode: planning_artifact
mission_slug: charter-e2e-hardening-tranche-2-01KQ9NVQ
model: claude-sonnet-4-6
owned_files:
- kitty-specs/charter-e2e-hardening-tranche-2-01KQ9NVQ/notes/pr-body.md
role: curator
tags: []
---

## ⚡ Do This First: Load Agent Profile

Run `/ad-hoc-profile-load curator-carla` before reading further.

## Objective

Open the upstream PR with proper closes/partial-closes, update `#827`, and comment on partially fixed issues with what remains. Confirm the regenerated agent skill copies (from WP06) appear in the PR diff.

Satisfies: `FR-014`, `C-004`, `C-005`.

## Context

- **Spec FR-014**: PR declares closes/partial-closes for `#839`–`#844`, mentions verified `#336`, includes before/after E2E strictness, verification commands, and `#827` follow-up scope.
- **Brief**: `start-here.md` "PR Expectations" and "After PR creation" sections.
- **Upstream**: `Priivacy-ai/spec-kitty`, base branch `main` at `daaee895`.
- **Source branch**: `fix/charter-e2e-827-tranche-2`.

## Branch Strategy

- Mission planning/base branch: `fix/charter-e2e-827-tranche-2`
- Mission merge target (internal): `fix/charter-e2e-827-tranche-2`
- **Upstream PR target**: `Priivacy-ai/spec-kitty:main` (this is the GitHub-side action this WP performs).

## Subtasks

### T041 — Open PR with proper closes/partial-closes and verification log

**Purpose**: Create the upstream PR following the spec's "PR Expectations" requirements.

**Steps**:
1. Confirm WP08 is merged on `fix/charter-e2e-827-tranche-2` and the branch is pushed to origin.
2. Run all verification commands locally (NFR-001..005) and capture output.
3. Author the PR body in `kitty-specs/<mission>/notes/pr-body.md` (this WP owns this file). Body must include:
   - **Summary** (1–3 bullets).
   - **Closes**: `#839`, `#840`, `#841`, `#842`, `#843`, `#844`.
   - **Verifies fix**: `#336` (closed by PR `#803`; this PR locks regression-free behavior in the strict E2E).
   - **Before/after** statement on E2E strictness (the six bypasses removed).
   - **Verification commands and results** (paste output of narrow gate, targeted gates, ruff, mypy strict, determinism check).
   - **Remaining `#827` follow-up scope** (likely cross-repo E2E and docs coverage; deferred issues `#845`–`#848`).
   - **Note**: explicit statement that no external E2E repo was required for this tranche because PR #838's test lives in the product repo.
4. Create the PR:
   ```bash
   gh pr create \
     --repo Priivacy-ai/spec-kitty \
     --base main \
     --head fix/charter-e2e-827-tranche-2 \
     --title "Charter E2E Hardening Tranche 2 — strict regression gate (#827 #839 #840 #841 #842 #843 #844)" \
     --body "$(cat kitty-specs/charter-e2e-hardening-tranche-2-01KQ9NVQ/notes/pr-body.md)"
   ```
5. If `gh` fails with "Missing required token scopes", per CLAUDE.md unset `GITHUB_TOKEN` and retry: `unset GITHUB_TOKEN && gh pr create ...`.
6. Capture the resulting PR URL for T042/T043.

**Files**: `kitty-specs/charter-e2e-hardening-tranche-2-01KQ9NVQ/notes/pr-body.md` (new).

### T042 — Comment on `#827` with PR URL and remaining-tranche recommendation

**Purpose**: Keep the epic accurate per spec C-005.

**Steps**:
1. Compose a comment that includes:
   - PR URL.
   - Brief summary of what shipped (six product fixes, strict E2E).
   - **Remaining tranche recommendation**: e.g., cross-repo E2E coverage, plain-English suite expansion, dossier ergonomics (`#845`), specify/plan auto-commit (`#846`), status-event reducer (`#847`), uv.lock pin drift (`#848`).
2. Post via `gh issue comment 827 --repo Priivacy-ai/spec-kitty --body "..."` (use HEREDOC for formatting).

### T043 — Comment precisely on any partially fixed issue

**Purpose**: Per spec C-005, partially fixed issues get a comment stating exactly what remains.

**Steps**:
1. For each issue that this PR closes only partially (most likely none if all six product fixes ship cleanly; possibly one if WP01 surfaced a deviation that escalated scope), post a precise comment via `gh issue comment <num> --repo Priivacy-ai/spec-kitty --body "..."`.
2. State in the comment: which FR/aspect was fixed, which is deferred, and the deferral reason.

### T044 — Cross-check generated agent skill copies appear in PR diff

**Purpose**: Per spec C-005, ensure WP06 T028's regenerated copies are part of the PR.

**Steps**:
1. Run `gh pr diff <PR_NUMBER> --repo Priivacy-ai/spec-kitty | grep -E '\.claude/|\.amazonq/|\.gemini/|\.cursor/|\.qwen/|\.opencode/|\.windsurf/|\.kilocode/|\.augment/|\.roo/|\.kiro/|\.agent/|\.github/prompts/|\.agents/skills/'`.
2. Confirm the runtime-next skill copies are in the diff with the workaround text removed.
3. If any copy is missing, return to WP06 T028 (re-run the migration); do **not** hand-edit copies.

## Test Strategy

- This WP is GitHub-side hygiene. No new code/test changes.
- Verification: PR exists, comments posted, copies in diff.

## Definition of Done

- [ ] PR open at `Priivacy-ai/spec-kitty:main` from `fix/charter-e2e-827-tranche-2`.
- [ ] PR body declares closes for `#839`–`#844`, mentions `#336`, includes before/after E2E strictness, verification log, and `#827` follow-up scope.
- [ ] `#827` has a comment with PR URL and remaining-tranche recommendation.
- [ ] Any partially fixed issue has a precise remaining-scope comment.
- [ ] Skill copies appear in PR diff with workaround text removed.
- [ ] Owned files only (the pr-body.md note).

## Risks

- **`gh` auth scope**: `GITHUB_TOKEN` may have limited scopes for organization repos. **Mitigation**: per CLAUDE.md, unset `GITHUB_TOKEN` and use keyring auth.
- **Missing skill copies in diff**: WP06 T028 may have failed silently. **Mitigation**: T044 catches this and routes back to WP06.
- **Verification command output too long for PR body**: trim to "exit 0" summaries with grep'd failure markers if any.

## Reviewer Guidance

- Confirm PR title and body match spec FR-014.
- Confirm all six issues are referenced as closes (or partial close with comment).
- Confirm `#827` comment is present and clearly identifies remaining scope.
- Confirm skill-copy refresh appears in the PR diff.

## Implementation command

```bash
spec-kitty agent action implement WP09 --agent <your-agent-key>
```

## Activity Log

- 2026-04-28T13:52:43Z – claude:sonnet:curator-carla:curator – shell_pid=28017 – Started implementation via action command
