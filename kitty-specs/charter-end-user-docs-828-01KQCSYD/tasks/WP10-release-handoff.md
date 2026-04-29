---
work_package_id: WP10
title: Release Handoff
dependencies:
- WP09
requirement_refs:
- FR-015
planning_base_branch: docs/charter-end-user-docs-828
merge_target_branch: docs/charter-end-user-docs-828
branch_strategy: Planning artifacts for this feature were generated on docs/charter-end-user-docs-828. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into docs/charter-end-user-docs-828 unless the human explicitly redirects the landing branch.
subtasks:
- T042
- T043
- T044
- T045
agent: curator-carla
history:
- date: '2026-04-29'
  author: spec-kitty.tasks
  note: Initial WP generated
authoritative_surface: kitty-specs/charter-end-user-docs-828-01KQCSYD/
execution_mode: planning_artifact
owned_files:
- kitty-specs/charter-end-user-docs-828-01KQCSYD/release-handoff.md
tags: []
---

# WP10 — Release Handoff

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load the agent profile assigned to this work package:

```
/ad-hoc-profile-load curator-carla
```

This loads domain knowledge, tool preferences, and behavioral guidelines for documentation writing. Do not proceed until the profile confirms it has loaded.

## Objective

Produce the release handoff artifact and finalize the branch for PR. This is the last WP — it can only run after WP09 passes all validation checks.

## Branch Strategy

- **Planning base branch**: `docs/charter-end-user-docs-828`
- **Merge target**: `main`
- **Execution workspace**: allocated by `lanes.json` at `spec-kitty agent action implement WP10 --agent <name>`; do not guess the worktree path

## Context

Read `kitty-specs/charter-end-user-docs-828-01KQCSYD/checklists/validation-report.md` before starting. The release handoff depends on the validation report being complete and all checks passing.

Read `plan.md` Section "Release Handoff Template" for the required artifact structure.

## Subtask Guidance

### T042 — Produce release-handoff.md

**File**: `kitty-specs/charter-end-user-docs-828-01KQCSYD/release-handoff.md`

Produce the release handoff artifact. Use the template from `plan.md` "Release Handoff Template" section. Fill every field from the actual work done.

**Required sections**:

```markdown
# Release Handoff: Charter End-User Docs Parity (#828)

**Date**: [date]
**Branch**: docs/charter-end-user-docs-828
**Mission**: charter-end-user-docs-828-01KQCSYD

## Pages Added

| Path | Title | FR Coverage |
|---|---|---|
| docs/3x/index.md | Charter Era (3.x) — Current Docs | FR-003 |
| docs/3x/charter-overview.md | How Charter Works: Synthesis, DRG, and the Bundle | FR-003, FR-006 |
| docs/3x/governance-files.md | Authoritative vs Generated Governance Files | FR-003 |
| docs/tutorials/charter-governed-workflow.md | Tutorial: Governed Charter Workflow End-to-End | FR-017 |
| docs/how-to/synthesize-doctrine.md | How to Synthesize and Maintain Doctrine | FR-005 |
| docs/how-to/run-governed-mission.md | How to Run a Governed Mission | FR-008 |
| docs/how-to/use-retrospective-learning.md | How to Use the Retrospective Learning Loop | FR-010 |
| docs/how-to/troubleshoot-charter.md | Troubleshooting Charter Failures | FR-014 |
| docs/explanation/charter-synthesis-drg.md | Understanding Charter: Synthesis, DRG, and Governed Context | FR-003, FR-006 |
| docs/explanation/governed-profile-invocation.md | Understanding Governed Profile Invocation | FR-007 |
| docs/explanation/retrospective-learning-loop.md | Understanding the Retrospective Learning Loop | FR-010 |
| docs/reference/charter-commands.md | Charter CLI Reference | FR-012 |
| docs/reference/profile-invocation.md | Profile Invocation Reference | FR-007 |
| docs/reference/retrospective-schema.md | Retrospective Schema and Events Reference | FR-010 |
| docs/migration/from-charter-2x.md | Migrating from 2.x / Early 3.x | FR-013 |

## Pages Updated

| Path | Nature of Change | FR Coverage |
|---|---|---|
| docs/toc.yml | Added 3x/ entry; relabeled 2x/ as Archive | FR-002 |
| docs/2x/index.md | Added archive notice with forward pointer | FR-016 |
| docs/how-to/setup-governance.md | Added Charter synthesis/bundle flow; removed 2.x prereq | FR-004 |
| docs/how-to/manage-glossary.md | Added Charter runtime integration section | FR-011 |
| docs/reference/cli-commands.md | Added Charter-era section with cross-links | FR-012 |
| docs/explanation/documentation-mission.md | Updated phases to match mission-runtime.yaml (if stale) | FR-009 |
| docs/retrospective-learning-loop.md | Converted to redirect stub | — |
| docs/3x/toc.yml | Created (new file) | FR-002 |
| docs/tutorials/toc.yml | Added charter-governed-workflow entry | FR-002 |
| docs/how-to/toc.yml | Added 4 new how-to entries | FR-002 |
| docs/explanation/toc.yml | Added 3 new explanation entries | FR-002 |
| docs/reference/toc.yml | Added 3 new reference entries | FR-002 |
| docs/migration/toc.yml | Created with from-charter-2x entry | FR-002 |

## Command Snippets Validated

| Command | Outcome |
|---|---|
| `uv run spec-kitty charter interview --help` | [actual outcome] |
| `uv run spec-kitty charter generate --help` | [actual outcome] |
| `uv run spec-kitty charter synthesize --help` | [actual outcome] |
| `uv run spec-kitty charter resynthesize --help` | [actual outcome or "not available"] |
| `uv run spec-kitty charter status --help` | [actual outcome] |
| `uv run spec-kitty charter sync --help` | [actual outcome] |
| `uv run spec-kitty charter lint --help` | [actual outcome] |
| `uv run spec-kitty charter bundle --help` | [actual outcome or "not available"] |
| `uv run spec-kitty next --help` | [actual outcome] |
| `uv run spec-kitty retrospect summary --help` | [actual outcome] |
| `uv run spec-kitty agent retrospect synthesize --help` | [actual outcome] |
| Tutorial smoke-test (temp repo) | [pass/fail + notes] |
| `docs/how-to/setup-governance.md` smoke-test (temp repo) | [pass/fail + notes] |

## Docs Tests Run

| Test file | Result |
|---|---|
| tests/docs/test_architecture_docs_consistency.py | [pass/fail] |
| tests/docs/test_readme_canonical_path.py | [pass/fail] |
| tests/docs/test_versioned_docs_integrity.py | [pass/fail] |

## Known Limitations Accepted

| Limitation | Status | Issue / Notes |
|---|---|---|
| Compact-context mode truncates large DRG contexts | Documented in troubleshoot-charter.md and charter-synthesis-drg.md | Issue #787 (check open/closed) |
| [Any other limitations found during implementation] | | |

## Follow-Up Docs Issues

[List any documentation gaps not addressed by this PR, with suggested issue titles. If none, write "None."]

## Gap Analysis

Full coverage matrix: `kitty-specs/charter-end-user-docs-828-01KQCSYD/gap-analysis.md`

All P0 and P1 gaps addressed. See gap-analysis.md for full matrix.
```

Fill every `[actual outcome]` and `[pass/fail]` cell with real data from the implementation.

### T043 — Update docs release notes or changelog if maintained

Check whether the repo maintains a docs changelog:

```bash
ls CHANGELOG.md docs/CHANGELOG.md docs/release-notes/ 2>/dev/null
```

If a changelog exists:
- Add an entry for this PR: "Charter-era documentation parity — 14 new pages, 5 updated, full navigation architecture for docs/3x/ hub"
- Follow the existing format

If no changelog exists, skip this subtask and note "no docs changelog maintained" in release-handoff.md.

### T044 — Final grep for stale text across all changed files

```bash
# Check for TODO markers
grep -r 'TODO' docs/3x/ docs/tutorials/charter-governed-workflow.md \
  docs/how-to/synthesize-doctrine.md docs/how-to/run-governed-mission.md \
  docs/how-to/use-retrospective-learning.md docs/how-to/troubleshoot-charter.md \
  docs/explanation/charter-synthesis-drg.md docs/explanation/governed-profile-invocation.md \
  docs/explanation/retrospective-learning-loop.md \
  docs/reference/charter-commands.md docs/reference/profile-invocation.md \
  docs/reference/retrospective-schema.md docs/migration/from-charter-2x.md

# Check for stale "2.x" references in current-facing pages (3x/ hub pages, tutorials, how-to, explanation, reference, migration)
grep -r '2\.x' docs/3x/ docs/tutorials/charter-governed-workflow.md \
  docs/how-to/synthesize-doctrine.md docs/how-to/run-governed-mission.md \
  docs/how-to/use-retrospective-learning.md docs/how-to/troubleshoot-charter.md \
  docs/explanation/charter-synthesis-drg.md docs/explanation/governed-profile-invocation.md \
  docs/explanation/retrospective-learning-loop.md \
  docs/reference/charter-commands.md docs/reference/profile-invocation.md \
  docs/reference/retrospective-schema.md

# Note: migration/from-charter-2x.md deliberately contains "2.x" text — that is correct
```

**Required result**:
- `grep -r 'TODO'` → zero results
- `grep -r '2\.x'` in current-facing pages → zero results (except migration page, which is expected)

Also run a final stale-command check:
```bash
# Check for stale retro command surface
grep -r 'retro summary\|retro synthesizer\|spec-kitty retro' \
  docs/3x/ docs/tutorials/ docs/how-to/ docs/explanation/ docs/reference/ docs/migration/

# Check for stale charter context as synthesis verb
grep -r 'charter context --dry-run\|charter context.*apply' \
  docs/3x/ docs/tutorials/ docs/how-to/ docs/explanation/ docs/reference/
```

Both greps must return zero results.

If any stale text found: fix the page, then re-run the grep.

### T045 — Verify branch is clean and ready for PR

```bash
git status
git diff --stat HEAD
```

**Required result**: Working tree is clean, no uncommitted changes.

If there are uncommitted changes:
- Stage and commit them to `docs/charter-end-user-docs-828`
- Do not leave the branch dirty

Verify the branch is ahead of main (has commits to PR):
```bash
git log main..HEAD --oneline | head -10
```

There should be at least one commit. Record the branch state and top commit in the release handoff.

## Definition of Done

- [ ] `release-handoff.md` produced with all sections filled (pages added, pages updated, snippets validated, tests run, known limitations, follow-up issues)
- [ ] Changelog updated if one exists (or noted as absent)
- [ ] Final grep: zero `TODO` markers in all new/changed current-facing pages
- [ ] Final grep: zero stale `2.x` references in current-facing pages (migration page exempt)
- [ ] `git status` → clean working tree
- [ ] `git log main..HEAD --oneline` → at least one commit
- [ ] `uv run pytest tests/docs/ -q` → zero failures (final confirmation)
