---
work_package_id: WP09
title: Validation Pass
dependencies:
- WP02
- WP03
- WP04
- WP05
- WP06
- WP07
- WP08
requirement_refs:
- FR-001
- FR-002
- FR-003
- FR-004
- FR-005
- FR-006
- FR-007
- FR-008
- FR-009
- FR-010
- FR-011
- FR-012
- FR-013
- FR-014
- FR-015
- FR-016
- FR-017
planning_base_branch: docs/charter-end-user-docs-828
merge_target_branch: docs/charter-end-user-docs-828
branch_strategy: Planning artifacts for this feature were generated on docs/charter-end-user-docs-828. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into docs/charter-end-user-docs-828 unless the human explicitly redirects the landing branch.
subtasks:
- T036
- T037
- T038
- T039
- T040
- T041
agent: reviewer-renata
history:
- date: '2026-04-29'
  author: spec-kitty.tasks
  note: Initial WP generated
authoritative_surface: kitty-specs/charter-end-user-docs-828-01KQCSYD/checklists/
execution_mode: planning_artifact
owned_files:
- kitty-specs/charter-end-user-docs-828-01KQCSYD/checklists/validation-report.md
tags: []
---

# WP09 — Validation Pass

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load the agent profile assigned to this work package:

```
/ad-hoc-profile-load reviewer-renata
```

This loads domain knowledge, tool preferences, and behavioral guidelines for documentation review and validation. Do not proceed until the profile confirms it has loaded.

## Objective

Run all docs validation checks across every page produced by WP02–WP08. Produce `validation-report.md` with evidence of each check. This WP is P0 — the PR cannot be opened until all checks pass.

This WP depends on all content WPs (WP02–WP08) being complete.

## Branch Strategy

- **Planning base branch**: `docs/charter-end-user-docs-828`
- **Merge target**: `main`
- **Execution workspace**: allocated by `lanes.json` at `spec-kitty agent action implement WP09 --agent <name>`; do not guess the worktree path

## Context

### What "Pass" Means

Every check below must produce a zero-error result. If a check fails:
1. Identify the specific page/line causing the failure
2. Fix it (or flag the owning WP as needing a fix)
3. Re-run the check until it passes
4. Record the fix in `validation-report.md`

Do not mark WP09 complete until all checks pass.

### Pages to Validate

All pages produced or updated by WP02–WP08:
- `docs/3x/index.md`, `docs/3x/charter-overview.md`, `docs/3x/governance-files.md`
- `docs/tutorials/charter-governed-workflow.md`
- `docs/how-to/setup-governance.md`, `synthesize-doctrine.md`, `run-governed-mission.md`, `use-retrospective-learning.md`, `troubleshoot-charter.md`, `manage-glossary.md`
- `docs/explanation/charter-synthesis-drg.md`, `governed-profile-invocation.md`, `retrospective-learning-loop.md`
- `docs/retrospective-learning-loop.md` (redirect stub)
- `docs/reference/charter-commands.md`, `cli-commands.md`, `profile-invocation.md`, `retrospective-schema.md`
- `docs/migration/from-charter-2x.md`
- `docs/explanation/documentation-mission.md`
- `docs/2x/index.md`
- All toc.yml files updated by WP01

## Subtask Guidance

### T036 — Run uv run pytest tests/docs/ -q

```bash
cd /path/to/spec-kitty/repo  # run from repo root
uv run pytest tests/docs/ -q
```

**Required result**: Zero failures.

If failures occur:
- `test_architecture_docs_consistency.py`: likely a new page not registered in a test expectation
- `test_versioned_docs_integrity.py`: likely a toc.yml reference to a non-existent file
- `test_readme_canonical_path.py`: likely a broken canonical path reference

Fix each failure by reading the test output, identifying the root cause, and fixing the page or toc.yml.

Record in validation-report.md:
- Command run
- Exit code
- Number of tests passing
- Any failures and their fixes

### T037 — Check all new/changed pages reachable from toc.yml; grep for TODO markers

**Part 1: toc.yml reachability**

For each new page, verify it appears in its section's toc.yml:

```bash
# Check each new page has a toc entry
grep 'charter-governed-workflow' docs/tutorials/toc.yml
grep 'synthesize-doctrine\|run-governed-mission\|use-retrospective-learning\|troubleshoot-charter' docs/how-to/toc.yml
grep 'charter-synthesis-drg\|governed-profile-invocation\|retrospective-learning-loop' docs/explanation/toc.yml
grep 'charter-commands\|profile-invocation\|retrospective-schema' docs/reference/toc.yml
grep 'from-charter-2x' docs/migration/toc.yml
grep '3x' docs/toc.yml
```

All must return a match. If any is missing, the owning WP (WP01) produced an incomplete toc.

**Part 2: TODO markers**

```bash
grep -r 'TODO' docs/3x/ docs/tutorials/charter-governed-workflow.md \
  docs/how-to/synthesize-doctrine.md docs/how-to/run-governed-mission.md \
  docs/how-to/use-retrospective-learning.md docs/how-to/troubleshoot-charter.md \
  docs/explanation/charter-synthesis-drg.md docs/explanation/governed-profile-invocation.md \
  docs/explanation/retrospective-learning-loop.md \
  docs/reference/charter-commands.md docs/reference/profile-invocation.md \
  docs/reference/retrospective-schema.md docs/migration/from-charter-2x.md
```

Zero results required.

Also check:
```bash
grep -r 'TODO: register in docs nav' docs/
```
Zero results required.

### T038 — Verify CLI flags in charter-commands.md match current --help

Re-run each charter subcommand `--help` and compare against `docs/reference/charter-commands.md`:

```bash
uv run spec-kitty charter interview --help
uv run spec-kitty charter generate --help
uv run spec-kitty charter context --help
uv run spec-kitty charter status --help
uv run spec-kitty charter sync --help
uv run spec-kitty charter lint --help
uv run spec-kitty charter bundle --help
```

For each subcommand:
- Every flag in `charter-commands.md` must appear in `--help` output
- No flag in `charter-commands.md` that doesn't appear in `--help`
- Descriptions should match (minor paraphrasing acceptable; invented flags are not)

Record any discrepancies and fix `charter-commands.md` before marking this check passed.

### T039 — Verify documentation mission phases in changed pages match mission-runtime.yaml

```bash
# Find mission-runtime.yaml
find src/ -name 'mission-runtime.yaml' 2>/dev/null

# Read it
cat src/specify_cli/missions/documentation/mission-runtime.yaml
```

Cross-check `docs/explanation/documentation-mission.md` against the phases in `mission-runtime.yaml`. Every phase name in the doc must match the YAML exactly. If WP08 missed a stale phase, fix it now.

Record the phase list from mission-runtime.yaml in the validation report as evidence.

### T040 — Execute tutorial smoke-test from fresh temp repo

Run the `docs/tutorials/charter-governed-workflow.md` tutorial from a fresh temp directory and verify no source-repo pollution:

```bash
TMPDIR=$(mktemp -d)
ORIGINAL_DIR=$(pwd)
cd "$TMPDIR"
git init -q

# Execute each step in the tutorial in sequence
# For interactive steps (charter interview), use --non-interactive if available or document manually
# For steps requiring SaaS sync: SPEC_KITTY_ENABLE_SAAS_SYNC=1

cd "$ORIGINAL_DIR"

# Verify no pollution in source repo
git status  # should show no unexpected changes
git diff --stat HEAD  # should be clean

rm -rf "$TMPDIR"
```

**Required result**: All tutorial steps complete without error (or errors are documented in the tutorial as expected), AND the spec-kitty source repo is clean after the smoke test.

If a tutorial step fails in the smoke test:
- Check if the tutorial step accurately describes what the command does
- Fix the tutorial page if the step description is wrong
- If the command itself has a bug, note it in the validation report and flag for follow-up

### T041 — Write validation-report.md with evidence

**File**: `kitty-specs/charter-end-user-docs-828-01KQCSYD/checklists/validation-report.md`

Produce a comprehensive report. Template:

```markdown
# Validation Report: Charter End-User Docs Parity (#828)

**Date**: [date]
**Branch**: docs/charter-end-user-docs-828
**Validator**: WP09 agent (reviewer-renata)

## T036: pytest docs suite

- **Command**: `uv run pytest tests/docs/ -q`
- **Result**: [pass/fail]
- **Tests run**: [N]
- **Tests passed**: [N]
- **Tests failed**: 0
- **Fixes applied**: [list any fixes, or "none"]

## T037: toc.yml reachability + TODO markers

- **Pages checked**: [list pages]
- **All pages in toc.yml**: [yes/no — list any misses]
- **TODO markers found**: 0
- **Fixes applied**: [list any, or "none"]

## T038: CLI flags vs --help

- **Subcommands verified**: charter interview, generate, context, status, sync, lint, bundle
- **Discrepancies found**: [list any, or "none"]
- **Fixes applied**: [list any, or "none"]

## T039: Documentation mission phases

- **mission-runtime.yaml phases**: [list phases]
- **documentation-mission.md phases**: [list phases]
- **Match**: [yes/no]
- **Fixes applied**: [list any, or "none"]

## T040: Tutorial smoke-test

- **Tutorial**: docs/tutorials/charter-governed-workflow.md
- **Smoke-test repo**: temp dir (cleaned after test)
- **Source-repo pollution**: none
- **Steps passed**: [list which steps ran cleanly]
- **Steps that require SaaS or interactive**: [list and note]
- **Result**: [pass/fail]

## Summary

All validation checks: [PASS / FAIL with list of failures]

Ready for PR: [yes/no]
```

## Definition of Done

- [ ] `uv run pytest tests/docs/ -q` → zero failures
- [ ] All new/changed pages verified in toc.yml
- [ ] `grep -r 'TODO' [all new pages]` → zero results
- [ ] `grep -r 'TODO: register in docs nav' docs/` → zero results
- [ ] CLI flags in `charter-commands.md` verified against live `--help`
- [ ] Documentation mission phases verified against `mission-runtime.yaml`
- [ ] Tutorial smoke-test completed with no source-repo pollution
- [ ] `kitty-specs/charter-end-user-docs-828-01KQCSYD/checklists/validation-report.md` written with evidence for each check
- [ ] All checks PASS (no outstanding failures)
