# Implementation Plan: TeamSpace Mission-State History Repair Coordination

**Branch**: `fix/teamspace-mission-state-closeout-guards` | **Date**: 2026-05-11 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `kitty-specs/teamspace-mission-state-repair-coordination-01KRB8AC/spec.md`

## Summary

This plan coordinates running the `spec-kitty doctor mission-state` pipeline
(audit → fix → dry-run) across three active repos (`spec-kitty`,
`spec-kitty-saas`, `spec-kitty-events`), produces a standalone repair commit
per repo on a `repair/teamspace-mission-state-history` branch, and closes
`spec-kitty#979` with evidence.

## Technical Context

**Language/Version**: Python 3.11 (spec-kitty CLI, uv-managed)
**Primary Dependencies**: spec-kitty-cli v3.2.0rc4, spec-kitty-events==5.0.0, gh CLI, git
**Storage**: Git repositories — `kitty-specs/` history rows, `.kittify/migrations/mission-state/` manifests
**Testing**: CLI command output validation (JSON reports), manifest review, zero-blocker assertion
**Target Platform**: macOS darwin (local dev machine) with SPEC_KITTY_ENABLE_SAAS_SYNC=1 for SaaS-touching commands
**Project Type**: Operational runbook — no new source code; all work is CLI execution + Git operations
**Performance Goals**: Audit completes in < 5 minutes per repo; repair is idempotent
**Constraints**: No random IDs in repair output; no `git add -A`; C-001 clean working tree before `--fix`; PR #1017 confirmed merged

## Charter Check

Charter directives in scope:
- **DIRECTIVE_003** (Decision Documentation): All repair decisions (scope, quarantine handling, manifest review) must be documented in PR bodies and issue comments.
- **DIRECTIVE_010** (Specification Fidelity): WP outputs must satisfy the acceptance criteria from start-here.md and spec.md exactly — no shortcutting the dry-run or manifest review steps.

No charter violations anticipated. The mission produces only Git artifacts (manifest files, repair commits, PR descriptions) and shell command outputs. No new source code is written.

## Project Structure

### Documentation (this mission)

```
kitty-specs/teamspace-mission-state-repair-coordination-01KRB8AC/
├── plan.md              # This file
├── research.md          # Phase 0 — command reference and repair scope decisions
├── data-model.md        # Phase 1 — audit JSON schema and manifest format
├── contracts/           # Phase 1 — command contracts and acceptance gates
├── quickstart.md        # Phase 1 — operator quick-reference
└── tasks.md             # Phase 2 output (spec-kitty.tasks)
```

### Repair artifacts (produced per target repo)

```
<repo-root>/
├── .kittify/migrations/mission-state/    # manifest written by --fix
└── kitty-specs/                          # status rows repaired in-place

../spec-kitty.before.audit.json           # baseline audit report
../spec-kitty.after.audit.json            # post-repair audit report
../spec-kitty.dry-run.json               # dry-run envelope validation

# Same pattern for spec-kitty-saas and spec-kitty-events
```

## Phase 0: Research

Findings consolidated in `research.md`.

### Scope decisions

1. **Repos in scope**: `spec-kitty`, `spec-kitty-saas`, `spec-kitty-events`.
   `spec-kitty-runtime` evaluated after Mission 2 baseline audit; included only
   if `missions_with_teamspace_blockers > 0`.

2. **Target branch per repo**: `main` — repair PR merges into `main` via
   `repair/teamspace-mission-state-history`.

3. **SPEC_KITTY_ENABLE_SAAS_SYNC=1** is required for `--teamspace-dry-run`
   on this machine.

4. **PR #1017** confirmed merged 2026-05-11T09:40:29Z — gate cleared.

5. **spec-kitty-events==5.0.0** is the required contract package. The installed
   CLI validates envelopes against this version at dry-run time.

### Command reference (per repo)

```bash
# WP02: Baseline audit
git checkout main && git pull --ff-only origin main
SPEC_KITTY_ENABLE_SAAS_SYNC=1 spec-kitty doctor mission-state --audit --json \
  > ../<repo>.before.audit.json

# WP03: Deterministic repair
SPEC_KITTY_ENABLE_SAAS_SYNC=1 spec-kitty doctor mission-state --fix

# WP04: Post-repair validation
SPEC_KITTY_ENABLE_SAAS_SYNC=1 spec-kitty doctor mission-state --audit --json \
  > ../<repo>.after.audit.json
SPEC_KITTY_ENABLE_SAAS_SYNC=1 spec-kitty doctor mission-state --teamspace-dry-run --json \
  > ../<repo>.dry-run.json

# WP05: Commit
git add .kittify/migrations/mission-state/ kitty-specs/
git commit -m "repair: TeamSpace mission-state history — deterministic repair manifest"
gh pr create --base main --title "repair: TeamSpace mission-state history" \
  --body "..."
```

## Phase 1: Design & Contracts

### Data model

Detailed in `data-model.md`.

### Contracts

Detailed in `contracts/`.

### Quickstart

Detailed in `quickstart.md`.

## Work Package Breakdown (preview — authoritative in tasks.md)

| WP | Title | Scope |
|----|-------|-------|
| WP01 | Repair scope confirmation and freeze coordination | Confirm repos, branches, verify PR #1017 merged, note freeze window |
| WP02 | Baseline audits across all selected repos | Run `--audit --json` in each repo; record blocker counts |
| WP03 | Run deterministic repair | Run `--fix` in each repo; review manifests |
| WP04 | Post-repair dry-run validation | Run `--audit` + `--teamspace-dry-run` in each repo; assert zero blockers |
| WP05 | Create repair branches and PRs | One branch + PR per repo; PR body includes evidence from WP02–WP04 |
| WP06 | Closeout: re-audit and issue closure | Re-run audits from fresh clones; comment on #979 and #920; close #979 |
