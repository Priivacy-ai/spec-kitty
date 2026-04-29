---
work_package_id: WP04
title: Release Handoff and PR (WP10)
dependencies:
- WP03
requirement_refs:
- FR-005
- FR-006
- FR-007
planning_base_branch: docs/charter-end-user-docs-828
merge_target_branch: docs/charter-end-user-docs-828
branch_strategy: Planning artifacts for this feature were generated on docs/charter-end-user-docs-828. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into docs/charter-end-user-docs-828 unless the human explicitly redirects the landing branch.
subtasks:
- T010
- T011
- T012
phase: Phase 4 - Ship
agent: "claude:sonnet:researcher-robbie:implementer"
shell_pid: "91875"
history:
- at: '2026-04-29T18:44:20Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
authoritative_surface: kitty-specs/charter-end-user-docs-828-01KQCSYD/
execution_mode: planning_artifact
owned_files:
- kitty-specs/charter-end-user-docs-828-01KQCSYD/release-handoff.md
tags: []
task_type: implement
---

# Work Package Prompt: WP04 — Release Handoff and PR (WP10)

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load the agent profile assigned to this work package:

```
/ad-hoc-profile-load researcher-robbie
```

This loads domain knowledge, tool preferences, and behavioral guidelines. Do not proceed until the profile confirms it has loaded.

## Objective

Execute source mission WP10 (release handoff) via `spec-kitty next`. Verify `release-handoff.md` is complete. Confirm branch cleanliness and that PR #885 (`docs/charter-end-user-docs-828` → `main`) is ready for merge.

## Branch Strategy

- **Planning base branch**: `docs/charter-end-user-docs-828`
- **Merge target**: `docs/charter-end-user-docs-828`
- **Execution workspace**: allocated by `lanes.json`; do not guess the worktree path

## Context

Source WP10 produces the release handoff artifact and performs final hygiene checks. After WP10 completes, the branch must be clean, all success criteria from the spec must be verifiable, and PR #885 must be ready to merge.

**Required by spec success criteria (SC)**:
- SC1: All 14 new + 5 updated pages exist and are in toc.yml and docfx.json
- SC2: `uv run pytest tests/docs/ -q` passes
- SC3: `docs/docfx.json` includes `docs/3x/` and `docs/migration/`
- SC4: Zero TODO markers in current-facing pages
- SC5: Zero stale `2.x` references in non-migration pages
- SC6: All CLI flag content matches live `--help`
- SC7: Tutorial smoke-test + setup-governance smoke-test both pass
- SC8: `release-handoff.md` complete with all required sections
- SC9: Branch is clean and at least one commit ahead of `main`; PR #885 is ready to merge

## Subtask Guidance

### T010 — Execute Source Mission WP10

```bash
uv run spec-kitty next \
  --agent researcher-robbie \
  --mission charter-end-user-docs-828-01KQCSYD
```

Source WP10 (defined at `kitty-specs/charter-end-user-docs-828-01KQCSYD/tasks/WP10-release-handoff.md`) runs four subtasks:
- T042: Produce `release-handoff.md`
- T043: Update docs release notes / changelog (if maintained)
- T044: Final grep for stale text (`TODO`, `2.x`, `retro summary`, `charter context --dry-run`)
- T045: Verify branch is clean and ready for PR

If `spec-kitty next` errors, check source WP10 status:
```bash
uv run spec-kitty agent tasks status \
  --mission charter-end-user-docs-828-01KQCSYD
```

### T011 — Verify release-handoff.md

Read and verify the handoff document:

```bash
cat kitty-specs/charter-end-user-docs-828-01KQCSYD/release-handoff.md
```

The document must contain all required sections with real content (not placeholder text):

| Section | Required content |
|---|---|
| Pages added | List of all 14 new pages with file paths |
| Pages updated | List of all 5 updated pages |
| Snippets validated | List of commands smoke-tested with "pass" result |
| Tests run | pytest result with zero failures confirmed |
| Known limitations | Explicit statement (may be "none" if clean) |
| Follow-up issues | Links or descriptions of deferred items (may be "none") |

```bash
# Check for placeholder text — must be zero
grep -i 'TODO\|\[fill\]\|\[tbd\]\|placeholder' \
  kitty-specs/charter-end-user-docs-828-01KQCSYD/release-handoff.md
# Expected: zero matches

# Check for stale command greps per WP10/T044
grep -rn 'retro summary\|retro synthesizer\|charter context --dry-run' docs/ 2>/dev/null
# Expected: zero matches
```

If release-handoff.md has placeholder text, return source WP10 to the agent with specific gaps noted.

### T012 — Verify Branch Cleanliness and PR Readiness

Run the final branch and PR checks (SC9):

```bash
# Branch must be clean
git status --short

# Branch must be ahead of main
git log --oneline origin/main..HEAD | head -5
# Expected: at least one commit listed (the docs content commits)

# Verify PR #885 exists and targets main
gh pr view 885 --json state,headRefName,baseRefName,title 2>/dev/null
# Expected: state=OPEN, headRefName=docs/charter-end-user-docs-828, baseRefName=main
```

**If branch has uncommitted changes**: investigate and commit or discard as appropriate. No changes should be uncommitted after source WP10.

**If PR #885 is not open or targets wrong branch**: surface to the user — do not force-push or create a new PR without explicit instruction.

**Final success criteria verification**:

```bash
# SC1: all pages registered in docfx.json
grep -c '"3x"' docs/docfx.json && grep -c '"migration"' docs/docfx.json

# SC2: pytest
uv run pytest tests/docs/ -q 2>&1 | tail -5

# SC4: zero TODO in current-facing pages
grep -rn 'TODO' docs/3x/ docs/tutorials/ docs/how-to/ docs/explanation/ docs/reference/ docs/migration/ 2>/dev/null | grep -v toc.yml | wc -l
# Expected: 0

# SC5: zero stale 2.x in non-migration pages
grep -rn '\b2\.x\b' docs/3x/ docs/tutorials/ docs/how-to/ docs/explanation/ docs/reference/ 2>/dev/null | wc -l
# Expected: 0
```

Report each SC result. If any SC fails, fix the underlying gap before declaring WP04 complete.

## Definition of Done

- [ ] `spec-kitty next` executed source WP10 without errors (T010)
- [ ] `release-handoff.md` exists with all required sections filled (T011)
- [ ] Zero placeholder text in `release-handoff.md` (T011)
- [ ] Zero stale command refs in docs/ confirmed by final grep (T011)
- [ ] `git status --short` shows clean working tree (T012)
- [ ] Branch is at least one commit ahead of `main` (T012)
- [ ] PR #885 is open and targets `main` (T012)
- [ ] `uv run pytest tests/docs/ -q` passes (T012/SC2)
- [ ] Zero TODO markers in current-facing pages (T012/SC4)
- [ ] Zero stale `2.x` refs in non-migration pages (T012/SC5)
- [ ] All 9 success criteria verified (T012)

## Risks

- PR #885 may need a push to include new commits from the sprint — run `git push origin docs/charter-end-user-docs-828` if the PR is behind
- `pytest tests/docs/` may not yet exist (no test suite for docs) — if the path doesn't exist, note "no tests/docs/ suite found" in the release-handoff.md and report to the user
- `release-handoff.md` may have placeholder sections if WP10 agent skipped guidance — review every section for real content, not scaffold prose

## Activity Log

- 2026-04-29T19:27:04Z – claude:sonnet:researcher-robbie:implementer – shell_pid=91875 – Started implementation via action command
