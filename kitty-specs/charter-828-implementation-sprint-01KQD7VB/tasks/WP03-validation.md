---
work_package_id: WP03
title: Validation Pass (WP09)
dependencies:
- WP02
requirement_refs:
- FR-004
- FR-007
- NFR-003
planning_base_branch: docs/charter-end-user-docs-828
merge_target_branch: docs/charter-end-user-docs-828
branch_strategy: Planning artifacts for this feature were generated on docs/charter-end-user-docs-828. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into docs/charter-end-user-docs-828 unless the human explicitly redirects the landing branch.
subtasks:
- T007
- T008
- T009
phase: Phase 3 - Quality Gate
agent: "claude:sonnet:researcher-robbie:reviewer"
shell_pid: "91691"
history:
- at: '2026-04-29T18:44:20Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
authoritative_surface: kitty-specs/charter-end-user-docs-828-01KQCSYD/checklists/
execution_mode: planning_artifact
owned_files:
- kitty-specs/charter-end-user-docs-828-01KQCSYD/checklists/validation-report.md
tags: []
task_type: implement
---

# Work Package Prompt: WP03 — Validation Pass (WP09)

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load the agent profile assigned to this work package:

```
/ad-hoc-profile-load researcher-robbie
```

This loads domain knowledge, tool preferences, and behavioral guidelines. Do not proceed until the profile confirms it has loaded.

## Objective

Execute source mission WP09 (validation pass) via `spec-kitty next`. Review the resulting `validation-report.md` for completeness and evidence coverage. Triage any validation failures — stop and report product bugs immediately per FR-007.

## Branch Strategy

- **Planning base branch**: `docs/charter-end-user-docs-828`
- **Merge target**: `docs/charter-end-user-docs-828`
- **Execution workspace**: allocated by `lanes.json`; do not guess the worktree path

## Context

Source WP09 runs six validation checks:
1. `uv run pytest tests/docs/ -q` (zero failures)
2. toc.yml reachability check + TODO grep
3. CLI flags in `charter-commands.md` matched against live `--help`
4. Documentation mission phases matched against `mission-runtime.yaml`
5. Tutorial smoke-test in a fresh temp repo (NFR-002)
6. Produces `checklists/validation-report.md` with evidence for each check

The validation report is a required deliverable (FR-004) and must accompany the docs PR.

**Product-bug escalation rule (FR-007)**: If any validation step surfaces a failure that is a bug in spec-kitty product code (not a docs error), stop immediately. Write a bug report to `kitty-specs/charter-828-implementation-sprint-01KQD7VB/bug-report.md` with the exact error, the failing command, and which check triggered it. Do NOT attempt to patch product code.

## Subtask Guidance

### T007 — Execute Source Mission WP09

```bash
uv run spec-kitty next \
  --agent researcher-robbie \
  --mission charter-end-user-docs-828-01KQCSYD
```

WP09 is the next ready WP after WP02–WP08 complete. It will run all six validation subtasks (T036–T041 of the source mission).

**Monitor for**:
- pytest failures → docs fix, not product fix
- CLI flag mismatch (NFR-001 gate) → update the relevant reference page to match live `--help`
- Phase mismatch with `mission-runtime.yaml` (NFR-003) → update `documentation-mission.md`
- Smoke-test failure → isolate to docs error vs. product bug; stop on product bug

**If WP09 surfaces a docs error (not a product bug)**: Fix the specific page and re-run source WP09 validation (the source WP09 prompt specifies how to iterate).

**If WP09 surfaces a product bug**: Stop. Write `bug-report.md` per FR-007. Do NOT continue to WP04.

### T008 — Review validation-report.md

After `spec-kitty next` completes WP09, read the validation report:

```bash
cat kitty-specs/charter-end-user-docs-828-01KQCSYD/checklists/validation-report.md
```

Verify it contains evidence for all six required checks:

| Check | Required in report | Status |
|---|---|---|
| pytest result | Zero failures, command output or log reference | — |
| toc.yml reachability | All new pages reachable, grep zero TODO results | — |
| CLI flag accuracy | `--help` output excerpts or diff confirming match | — |
| Phase accuracy | Phase names from `mission-runtime.yaml` confirmed | — |
| Tutorial smoke-test | Temp dir path, commands run, cleanup confirmed | — |
| setup-governance smoke-test | Temp dir path, commands run, cleanup confirmed | — |

**If any section is missing evidence**: Return the source mission WP09 to the agent with a specific note about what evidence is missing. Do not proceed to WP04 with an incomplete report.

### T009 — Triage Validation Failures

After reviewing the report, classify any failures:

**Docs errors** (fix and continue):
- Missing page registered in toc.yml → add toc entry, no code change
- Stale TODO marker → delete or fill the placeholder
- CLI flag in docs differs from `--help` → update docs to match live output
- Phase name in docs differs from `mission-runtime.yaml` → update docs

**Product bugs** (stop and report):
- `uv run spec-kitty charter synthesize --help` crashes or returns unexpected error
- `uv run spec-kitty retrospect summary` fails with unexpected exit code
- pytest tests/docs/ fails on infrastructure (not docs content)
- Smoke-test tutorial commands produce errors unrelated to the tutorial text itself

For any product bug: write `kitty-specs/charter-828-implementation-sprint-01KQD7VB/bug-report.md` with:

```markdown
# Bug Report: [one-line summary]

**Triggered during**: WP09 validation — [which check]
**Command**: `uv run spec-kitty ...`
**Error output**:
```
[exact output]
```
**Expected**: [what should happen]
**Classification**: Product bug — docs fix not applicable
```

## Definition of Done

- [ ] `spec-kitty next` executed source WP09 without stopping on a product bug (T007)
- [ ] `checklists/validation-report.md` exists and has evidence for all six checks (T008)
- [ ] pytest `tests/docs/ -q` result is zero failures (per report) (T008)
- [ ] All new pages reachable from toc.yml (per report) (T008)
- [ ] CLI flags in `charter-commands.md` match live `--help` (per report) (T008)
- [ ] Doc mission phases match `mission-runtime.yaml` (per report) (T008)
- [ ] Tutorial smoke-test completed in isolated temp dir, no repo pollution (per report) (T008)
- [ ] All docs errors found in validation were fixed before WP09 completed (T009)
- [ ] If product bugs found: `bug-report.md` written and sprint halted (T009)

## Risks

- Smoke-test may leave temp files in the source repo if the cleanup step was skipped by the source WP09 agent — run `git status --short` after WP09 and clean up any untracked temp files
- CLI flag mismatch may be systemic (multiple pages) — scan all reference pages with `grep -rn` before declaring fixed
- Product bug boundary is sometimes ambiguous — when in doubt, write a bug report and surface to the user for judgment

## Activity Log

- 2026-04-29T19:23:14Z – claude:sonnet:researcher-robbie:implementer – shell_pid=91142 – Started implementation via action command
- 2026-04-29T19:26:26Z – claude:sonnet:researcher-robbie:implementer – shell_pid=91142 – Validation pass complete, report at kitty-specs/charter-end-user-docs-828-01KQCSYD/checklists/validation-report.md
- 2026-04-29T19:26:41Z – claude:sonnet:researcher-robbie:reviewer – shell_pid=91691 – Started review via action command
