---
work_package_id: WP01
title: Pre-Flight and Foundation
dependencies: []
requirement_refs:
- FR-001
- FR-002
- NFR-002
planning_base_branch: docs/charter-end-user-docs-828
merge_target_branch: docs/charter-end-user-docs-828
branch_strategy: Planning artifacts for this feature were generated on docs/charter-end-user-docs-828. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into docs/charter-end-user-docs-828 unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
phase: Phase 1 - Foundation
agent: "claude:sonnet:researcher-robbie:reviewer"
shell_pid: "86606"
history:
- at: '2026-04-29T18:44:20Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
authoritative_surface: docs/
execution_mode: planning_artifact
owned_files:
- kitty-specs/charter-end-user-docs-828-01KQCSYD/gap-analysis.md
- docs/toc.yml
- docs/docfx.json
- docs/2x/index.md
- docs/3x/toc.yml
- docs/tutorials/toc.yml
- docs/how-to/toc.yml
- docs/explanation/toc.yml
- docs/reference/toc.yml
- docs/migration/toc.yml
tags: []
task_type: implement
---

# Work Package Prompt: WP01 — Pre-Flight and Foundation

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load the agent profile assigned to this work package:

```
/ad-hoc-profile-load researcher-robbie
```

This loads domain knowledge, tool preferences, and behavioral guidelines. Do not proceed until the profile confirms it has loaded.

## Objective

Run all pre-flight checks and execute source mission WP01 (gap analysis + navigation architecture) via `spec-kitty next`. Verify all WP01 deliverables are in place before any content WPs begin.

## Branch Strategy

- **Planning base branch**: `docs/charter-end-user-docs-828`
- **Merge target**: `docs/charter-end-user-docs-828`
- **Execution workspace**: allocated by `lanes.json`; do not guess the worktree path

## Context

This sprint mission drives `charter-end-user-docs-828-01KQCSYD` via repeated `spec-kitty next` calls. WP01 of the source mission establishes all navigation infrastructure that content WPs (WP02–WP08) depend on. Nothing in the content phase can begin until WP01 is verified complete.

**Critical constraints from spec**:
- All invocations: `uv run spec-kitty` (not ambient `spec-kitty`)
- Hosted auth/tracker commands: prefix `SPEC_KITTY_ENABLE_SAAS_SYNC=1`
- Working directory: `/Users/robert/spec-kitty-dev/spec-kitty-20260429-161241-ycLfiR/spec-kitty`
- No product code changes — stop and report if docs validation surfaces a product bug

## Subtask Guidance

### T001 — Run Pre-Flight Checks

Run all four checks in order. All must pass before any WP execution begins (FR-001).

```bash
# 1. Confirm branch and clean state
git status --short --branch

# 2. Pull tracking branch (origin/docs/charter-end-user-docs-828) with fast-forward only
#    Note: NOT "git pull --ff-only origin main" — the feature branch is ahead of main
git pull --ff-only

# 3. Verify CLI version is 3.2.0a5 or later
uv run spec-kitty --version

# 4. Check source mission prerequisites
uv run spec-kitty agent mission check-prerequisites \
  --mission charter-end-user-docs-828-01KQCSYD --json

# 5. Verify PR #885 is open (Assumption in spec)
gh pr view 885 --json state,headRefName,baseRefName
```

**Pass criteria**:
- `git status` shows branch `docs/charter-end-user-docs-828`, working tree clean
- `git pull --ff-only` succeeds (pulls tracking branch; not main)
- `spec-kitty --version` prints `3.2.0a5` or later
- `check-prerequisites` returns `"valid": true` with zero errors
- PR #885: `state=OPEN`, `headRefName=docs/charter-end-user-docs-828`, `baseRefName=main`

**If any check fails**: Stop, report the failure, do not proceed to T002.

### T002 — Execute Source Mission WP01

Run `spec-kitty next` for the source mission. It will pick up WP01 (the next ready work package).

```bash
uv run spec-kitty next \
  --agent researcher-robbie \
  --mission charter-end-user-docs-828-01KQCSYD
```

Source WP01 is defined at:
`kitty-specs/charter-end-user-docs-828-01KQCSYD/tasks/WP01-gap-analysis-and-navigation-architecture.md`

**WP01 source deliverables** (from source mission T001–T005):
- `kitty-specs/charter-end-user-docs-828-01KQCSYD/gap-analysis.md` — Divio coverage matrix
- `docs/toc.yml` — updated: add `3x/`, relabel `2x/` as Archive
- `docs/3x/toc.yml` — created
- `docs/tutorials/toc.yml`, `docs/how-to/toc.yml`, `docs/explanation/toc.yml`, `docs/reference/toc.yml`, `docs/migration/toc.yml` — updated/created
- `docs/2x/index.md` — archive notice + forward pointer to `docs/3x/`
- `docs/docfx.json` — updated to include `docs/3x/` and `docs/migration/` (NFR: DocFX must include these dirs)

If `spec-kitty next` returns no ready WP or a blocking error, investigate and resolve before continuing.

### T003 — Verify WP01 Deliverables

After `spec-kitty next` completes, verify each deliverable:

```bash
# Gap analysis created
test -f kitty-specs/charter-end-user-docs-828-01KQCSYD/gap-analysis.md && echo "gap-analysis.md ✅" || echo "MISSING ❌"

# Navigation files
test -f docs/3x/toc.yml && echo "docs/3x/toc.yml ✅" || echo "MISSING ❌"
grep -q '3x' docs/toc.yml && echo "docs/toc.yml has 3x ✅" || echo "docs/toc.yml missing 3x ❌"
grep -qi 'archive\|2x' docs/toc.yml && echo "docs/toc.yml has 2x archive label ✅" || echo "docs/toc.yml missing archive label ❌"

# docfx.json includes new directories
grep -q '"3x"' docs/docfx.json && echo "docfx.json has 3x ✅" || echo "docfx.json missing 3x ❌"
grep -q '"migration"' docs/docfx.json && echo "docfx.json has migration ✅" || echo "docfx.json missing migration ❌"

# docfx.json is valid JSON
python3 -c "import json; json.load(open('docs/docfx.json')); print('docfx.json valid JSON ✅')"

# Section toc.yml files exist
for d in tutorials how-to explanation reference migration; do
  test -f "docs/$d/toc.yml" && echo "docs/$d/toc.yml ✅" || echo "docs/$d/toc.yml MISSING ❌"
done

# Archive notice
grep -qi 'archive\|2\.x.*no longer' docs/2x/index.md && echo "docs/2x/index.md has archive notice ✅" || echo "docs/2x/index.md missing archive notice ❌"
```

**Zero ❌ results required.** If any check fails, re-run the source WP01 or fix the specific gap before marking WP01 complete.

## Definition of Done

- [ ] All four pre-flight checks passed (T001)
- [ ] `spec-kitty next` completed source WP01 without errors (T002)
- [ ] `gap-analysis.md` exists with Divio coverage matrix (T003)
- [ ] `docs/toc.yml` has `3x/` entry and `2x/` labeled Archive (T003)
- [ ] `docs/3x/toc.yml` exists (T003)
- [ ] All five section `toc.yml` files exist (tutorials/, how-to/, explanation/, reference/, migration/) (T003)
- [ ] `docs/2x/index.md` has archive notice (T003)
- [ ] `docs/docfx.json` includes `docs/3x/` and `docs/migration/`; valid JSON (T003)
- [ ] Zero uncommitted changes from any smoke commands (NFR-002)

## Risks

- `git pull --ff-only` fails if local branch has diverged from origin — resolve before continuing
- Source WP01 may not be "ready" if source mission status is unexpected — check `spec-kitty agent tasks status --mission charter-end-user-docs-828-01KQCSYD`
- `docs/docfx.json` update may have been skipped by WP01 agent — verify explicitly in T003

## Activity Log

- 2026-04-29T18:58:01Z – claude:sonnet:researcher-robbie:implementer – shell_pid=83167 – Started implementation via action command
- 2026-04-29T19:06:12Z – claude:sonnet:researcher-robbie:implementer – shell_pid=83167 – Pre-flight checks passed, source WP01 executed, all deliverables verified
- 2026-04-29T19:06:54Z – claude:sonnet:researcher-robbie:reviewer – shell_pid=86606 – Started review via action command
- 2026-04-29T19:07:38Z – claude:sonnet:researcher-robbie:reviewer – shell_pid=86606 – Review passed: all deliverables verified — gap-analysis.md with Divio matrix, docs/toc.yml updated (3x entry + Archive label), docs/3x/toc.yml created, all 5 section toc.yml files updated, docfx.json includes 3x and migration, docs/2x/index.md has archive notice. 375 tests pass.
- 2026-04-29T19:31:38Z – claude:sonnet:researcher-robbie:reviewer – shell_pid=86606 – Planning artifact — all work committed directly to docs/charter-end-user-docs-828. No separate lane branch.
