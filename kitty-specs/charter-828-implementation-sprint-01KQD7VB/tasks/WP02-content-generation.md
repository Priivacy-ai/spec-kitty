---
work_package_id: WP02
title: Content Generation (WP02–WP08)
dependencies:
- WP01
requirement_refs:
- FR-003
- FR-007
- NFR-001
planning_base_branch: docs/charter-end-user-docs-828
merge_target_branch: docs/charter-end-user-docs-828
branch_strategy: Planning artifacts for this feature were generated on docs/charter-end-user-docs-828. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into docs/charter-end-user-docs-828 unless the human explicitly redirects the landing branch.
subtasks:
- T004
- T005
- T006
phase: Phase 2 - Content Generation
agent: "claude:sonnet:researcher-robbie:reviewer"
shell_pid: "90890"
history:
- at: '2026-04-29T18:44:20Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
authoritative_surface: docs/3x/
execution_mode: planning_artifact
owned_files:
- docs/3x/index.md
- docs/3x/charter-overview.md
- docs/3x/governance-files.md
- docs/tutorials/charter-governed-workflow.md
- docs/how-to/setup-governance.md
- docs/how-to/synthesize-doctrine.md
- docs/how-to/run-governed-mission.md
- docs/how-to/manage-glossary.md
- docs/how-to/use-retrospective-learning.md
- docs/how-to/troubleshoot-charter.md
- docs/explanation/charter-synthesis-drg.md
- docs/explanation/governed-profile-invocation.md
- docs/explanation/retrospective-learning-loop.md
- docs/explanation/documentation-mission.md
- docs/reference/charter-commands.md
- docs/reference/profile-invocation.md
- docs/reference/cli-commands.md
- docs/reference/retrospective-schema.md
- docs/migration/from-charter-2x.md
- docs/retrospective-learning-loop.md
tags: []
task_type: implement
---

# Work Package Prompt: WP02 — Content Generation (WP02–WP08)

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load the agent profile assigned to this work package:

```
/ad-hoc-profile-load researcher-robbie
```

This loads domain knowledge, tool preferences, and behavioral guidelines. Do not proceed until the profile confirms it has loaded.

## Objective

Drive source mission WP02–WP08 via repeated `spec-kitty next` calls to produce all 14 new and 5 updated documentation pages. Verify the complete page inventory. Grep for stale command names and TODO markers.

## Branch Strategy

- **Planning base branch**: `docs/charter-end-user-docs-828`
- **Merge target**: `docs/charter-end-user-docs-828`
- **Execution workspace**: allocated by `lanes.json`; do not guess the worktree path

## Context

Source WP02–WP08 can run in parallel within the source mission (they have no interdependencies after WP01). `spec-kitty next` will schedule them and their respective agents will execute them. This sprint WP monitors completion and verifies the aggregate output.

**Source WP mapping** (from `charter-end-user-docs-828-01KQCSYD`):

| Source WP | Content | Pages |
|---|---|---|
| WP02 | docs/3x/ Charter hub | 3 new pages |
| WP03 | End-to-end tutorial | 1 new page |
| WP04 | How-to: governance, synthesis, missions, glossary | 3 new + 2 updated |
| WP05 | How-to: retrospective + troubleshooting | 2 new pages |
| WP06 | Explanation pages + redirect stub | 3 new + 1 stub update |
| WP07 | Reference: CLI + profile invocation | 2 new + 1 updated |
| WP08 | Reference: schema + migration + doc-mission review | 2 new + 1 reviewed/updated |

**Corrected CLI command names** (C-004 — must appear in all generated pages):

| Correct | Wrong (do not use) |
|---|---|
| `charter synthesize` | `charter context` (for doctrine promotion) |
| `charter resynthesize` | (no wrong alternative — just check it exists) |
| `charter bundle validate` | `charter bundle` alone (incomplete) |
| `charter context --action <action>` | (correct, not synthesis) |
| `retrospect summary` | `retro summary` |
| `agent retrospect synthesize --json` | `retro synthesizer` |
| `charter sync` | (syncs charter.md to YAML configs; not SaaS push) |

## Subtask Guidance

### T004 — Execute Source WP02–WP08

Run `spec-kitty next` repeatedly until all 7 source WPs (WP02–WP08) show as `done`. Each call picks up the next ready WP.

```bash
# Run once per ready WP; spec-kitty next will pick the right one each time
uv run spec-kitty next \
  --agent researcher-robbie \
  --mission charter-end-user-docs-828-01KQCSYD
```

Check status after each run:

```bash
uv run spec-kitty agent tasks status \
  --mission charter-end-user-docs-828-01KQCSYD
```

Continue until WP02, WP03, WP04, WP05, WP06, WP07, WP08 are all `done`.

**If any WP fails or gets stuck**: Read the relevant WP prompt file at `kitty-specs/charter-end-user-docs-828-01KQCSYD/tasks/WP0N-*.md` and the failure details. Do not skip a WP — all 7 must complete before T005.

**If `spec-kitty next` surfaces a product bug** (per FR-007): Stop immediately. Do not attempt to fix the product code. Write a bug report to `kitty-specs/charter-828-implementation-sprint-01KQD7VB/bug-report.md` with:
- The failing command
- The exact error output
- Which doc page triggered it

### T005 — Verify Page Count and CLI Flag Accuracy

After all 7 source WPs complete, verify the complete page inventory:

```bash
# New pages — all must exist
for f in \
  docs/3x/index.md \
  docs/3x/charter-overview.md \
  docs/3x/governance-files.md \
  docs/tutorials/charter-governed-workflow.md \
  docs/how-to/synthesize-doctrine.md \
  docs/how-to/run-governed-mission.md \
  docs/how-to/use-retrospective-learning.md \
  docs/how-to/troubleshoot-charter.md \
  docs/explanation/charter-synthesis-drg.md \
  docs/explanation/governed-profile-invocation.md \
  docs/explanation/retrospective-learning-loop.md \
  docs/reference/charter-commands.md \
  docs/reference/profile-invocation.md \
  docs/reference/retrospective-schema.md \
  docs/migration/from-charter-2x.md; do
  test -f "$f" && echo "✅ $f" || echo "❌ MISSING: $f"
done

# Updated pages — must exist and show Charter-era content
for f in \
  docs/how-to/setup-governance.md \
  docs/how-to/manage-glossary.md \
  docs/reference/cli-commands.md \
  docs/explanation/documentation-mission.md \
  docs/retrospective-learning-loop.md; do
  test -f "$f" && echo "✅ $f" || echo "❌ MISSING: $f"
done
```

**Zero ❌ results required** (FR-003: all 14 new + 5 updated pages must exist).

**CLI spot-check** (NFR-001 — verify against live --help before proceeding to T006):

```bash
# Capture live subcommand list
uv run spec-kitty charter --help 2>&1 | grep -E '^\s+(interview|generate|synthesize|resynthesize|status|sync|lint|bundle)'

# Confirm charter-commands.md has synthesize section
grep -l 'charter synthesize' docs/reference/charter-commands.md && echo "synthesize section ✅" || echo "missing synthesize ❌"

# Confirm resynthesize section exists
grep -l 'resynthesize' docs/reference/charter-commands.md && echo "resynthesize section ✅" || echo "missing resynthesize ❌"

# Confirm retrospect not retro
grep -rn 'retro summary\|retro synthesizer' docs/ && echo "❌ stale retro refs found" || echo "no stale retro refs ✅"
```

### T006 — Grep for Stale Command Names and TODO Markers

Run all stale-content checks across the generated pages (FR-005 precondition, NFR-001):

```bash
# TODO markers — must be zero in current-facing pages
grep -rn 'TODO' \
  docs/3x/ docs/tutorials/ docs/how-to/ \
  docs/explanation/ docs/reference/ docs/migration/ \
  docs/retrospective-learning-loop.md \
  2>/dev/null | grep -v 'toc.yml' | grep -v '.pyc'
# Expected: zero matches

# Stale synthesis command
grep -rn 'charter context --dry-run\|charter context --apply' docs/ 2>/dev/null
# Expected: zero matches (charter context --action <action> is correct; charter synthesize is for doctrine)

# Stale retro commands
grep -rn '\bretro summary\b\|\bretro synthesizer\b' docs/ 2>/dev/null
# Expected: zero matches

# Stale 2.x references in non-migration pages
grep -rn '\b2\.x\b' \
  docs/3x/ docs/tutorials/ docs/how-to/ \
  docs/explanation/ docs/reference/ \
  2>/dev/null
# Expected: zero matches (2.x references belong only in docs/migration/ and docs/2x/)
```

If any match is found, fix it in the relevant page before proceeding to WP03.

## Definition of Done

- [ ] All 7 source WPs (WP02–WP08) show `done` in `spec-kitty agent tasks status` (T004)
- [ ] All 14 new pages exist on the branch (T005)
- [ ] All 5 updated pages exist and have Charter-era content (T005)
- [ ] `charter-commands.md` has both `charter synthesize` and `charter resynthesize` sections (T005)
- [ ] Zero stale `retro summary`/`retro synthesizer` refs in docs/ (T005, T006)
- [ ] Zero TODO markers in current-facing pages (T006)
- [ ] Zero stale `charter context --dry-run/--apply` patterns (T006)
- [ ] Zero stale `2.x` refs in non-migration pages (T006)
- [ ] No product bug triggered; if triggered, bug-report.md written and WP stopped (FR-007)

## Risks

- `spec-kitty next` may produce incomplete pages if an agent skips steps — verify each page has real content, not stubs
- CLI spot-check may reveal a flag name discrepancy — stop and investigate (NFR-001 is a hard gate)
- `charter resynthesize` may not exist in 3.2.0a5 — if `--help` returns "No such command", document that in charter-commands.md and update the relevant how-to page

## Activity Log

- 2026-04-29T19:07:44Z – claude:sonnet:researcher-robbie:implementer – shell_pid=86978 – Started implementation via action command
- 2026-04-29T19:21:32Z – claude:sonnet:researcher-robbie:implementer – shell_pid=86978 – Content generation complete: 14 new + 5 updated pages, stale checks passed, CLI verified
- 2026-04-29T19:22:07Z – claude:sonnet:researcher-robbie:reviewer – shell_pid=90890 – Started review via action command
