---
work_package_id: WP01
title: Stale Codex Docs Cleanup
dependencies: []
requirement_refs:
- FR-001
- FR-002
- FR-003
- FR-004
- FR-005
- FR-006
tracker_refs: []
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-agent-harness-install-audit-follow-through-01KT5YTQ
base_commit: 10d49722f492481e3be4b331aca8543cbb0bd06b
created_at: '2026-06-03T06:45:29.551011+00:00'
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
agent: "claude:sonnet:orchestrator:orchestrator"
shell_pid: "41631"
history:
- date: '2026-06-03'
  status: planned
agent_profile: curator-carla
authoritative_surface: docs/
execution_mode: code_change
owned_files:
- docs/explanation/ai-agent-architecture.md
- docs/how-to/upgrade-project.md
- docs/how-to/setup-codex-spec-kitty-launcher.md
- docs/reference/upgrade-lifecycle.md
- docs/reference/environment-variables.md
- docs/reference/supported-agents.md
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your assigned agent profile:

```
/ad-hoc-profile-load curator-carla
```

This profile governs your working style for this WP. Apply it throughout.

---

## Objective

Remove all active-guidance references to retired Codex install paths from 6 documentation files. Replace with the current canonical path (`.agents/skills/spec-kitty.<command>/SKILL.md`) and invocation syntax (`$spec-kitty.<command>`). Historical or planning documents are exempt.

This WP is governed by `occurrence_map.yaml` (bulk-edit gate, DIRECTIVE_035). The map is already validated. You must not edit files outside `owned_files`.

## Branch Strategy

- **Planning base**: `main`
- **Merge target**: `main`
- **Your workspace**: allocated by `spec-kitty agent action implement WP01 --agent claude`; the resolved worktree path comes from `lanes.json` — use that path, do not reconstruct it.

## Context

The 2026-06-03 harness audit found 7 docs files with stale Codex install guidance. Six are in scope for this WP (the seventh, `docs/development/3-2-information-architecture.md`, is a historical planning doc and is `do_not_change` per `occurrence_map.yaml`).

**Canonical replacements**:
| Stale | Canonical |
|-------|-----------|
| `.codex/prompts/` | `.agents/skills/spec-kitty.<command>/SKILL.md` |
| `.codex/skills/` | `.agents/skills/` |
| `CODEX_HOME=$(pwd)/.codex` | Remove guidance; Codex no longer needs `CODEX_HOME` for command skills |
| `$env:CODEX_HOME = Join-Path $RepoRoot ".codex"` | Remove or update to reflect new model |
| `@codex prompts:spec-kitty.*` | `$spec-kitty.<command>` |

**occurrence_map.yaml rules for this WP**:
- `filesystem_paths`: `manual_review` — each occurrence needs judgment (replace vs remove vs label historical)
- `user_facing_strings`: `manual_review` — active how-to/reference → update; historical → preserve with label
- Exception: `docs/development/**` → `do_not_change`

---

## Subtask T001 — Update `docs/explanation/ai-agent-architecture.md`

**Purpose**: Remove the stale `.codex/prompts/` table entry from the agent architecture reference.

**Steps**:
1. Open `docs/explanation/ai-agent-architecture.md` line 49.
2. Find the table row: `| GitHub Codex | .codex/prompts/ | Markdown |`
3. Update the path column to: `.agents/skills/spec-kitty.<command>/SKILL.md`
4. Verify surrounding rows remain accurate (do not edit unrelated rows).

**Validation**:
- [ ] `grep -n "\.codex/prompts/" docs/explanation/ai-agent-architecture.md` returns no results
- [ ] Table row for Codex now shows `.agents/skills/` path

---

## Subtask T002 — Update `docs/how-to/upgrade-project.md`

**Purpose**: Remove the stale `.codex/skills/` reference from the upgrade how-to.

**Steps**:
1. Open `docs/how-to/upgrade-project.md` line 55.
2. Find the text listing agent command directories including `.codex/skills/`.
3. Replace `.codex/skills/` with `.agents/skills/` in that list.
4. Verify the surrounding sentence remains grammatically correct and accurate.

**Validation**:
- [ ] `grep -n "\.codex/skills/" docs/how-to/upgrade-project.md` returns no results

---

## Subtask T003 — Update `docs/reference/upgrade-lifecycle.md`

**Purpose**: Remove the stale `.codex/skills/spec-kitty.*/` refresh target from the upgrade lifecycle reference.

**Steps**:
1. Open `docs/reference/upgrade-lifecycle.md` line 44.
2. Find the text listing refresh targets including `.codex/skills/spec-kitty.*/`.
3. Replace `.codex/skills/spec-kitty.*/` with `.agents/skills/spec-kitty.*/`.
4. Verify surrounding content remains accurate.

**Validation**:
- [ ] `grep -n "\.codex/skills/" docs/reference/upgrade-lifecycle.md` returns no results

---

## Subtask T004 — Update `docs/reference/environment-variables.md`

**Purpose**: Update the `CODEX_HOME` section. Codex command skills no longer require `CODEX_HOME` pointing to `.codex/`. The current install path is `.agents/skills/`.

**Steps**:
1. Open `docs/reference/environment-variables.md` and locate the `CODEX_HOME` section (around lines 241–282).
2. Assess what the section says:
   - If it prescribes `export CODEX_HOME="$(pwd)/.codex"` as active guidance: update to explain that `CODEX_HOME` is no longer required for Spec Kitty command skills (they live at `.agents/skills/spec-kitty.<command>/SKILL.md`). Retain the variable documentation if it still has other valid uses; mark it deprecated/legacy if it does not.
   - If the table row at line 282 lists `CODEX_HOME | Codex CLI prompt path | $(pwd)/.codex`: update the description to reflect the new canonical path or remove the row if the variable is no longer needed.
3. Do not remove the section entirely if `CODEX_HOME` is still relevant for other Codex prompt workflows — only correct the install path claim.

**Validation**:
- [ ] `grep -n "\.codex\"" docs/reference/environment-variables.md` returns no lines presenting `.codex` as an active install target
- [ ] Section accurately reflects current `CODEX_HOME` usage (or absence thereof)

---

## Subtask T005 — Update `docs/reference/supported-agents.md`

**Purpose**: Remove or correct the two `CODEX_HOME=$(pwd)/.codex` guidance blocks.

**Steps**:
1. Open `docs/reference/supported-agents.md`.
2. Locate lines 195–197 (first `CODEX_HOME` block) and lines 388–390 (second block).
3. For each block: same judgment as T004 — if it is prescribing `.codex` as the install target, update to reflect `.agents/skills/` or remove if entirely superseded.
4. Ensure Codex setup guidance in this file directs users to `.agents/skills/spec-kitty.<command>/SKILL.md` and `$spec-kitty.<command>` invocation.

**Validation**:
- [ ] `grep -n "CODEX_HOME.*\.codex" docs/reference/supported-agents.md` returns no results with `.codex` as the active install root

---

## Subtask T006 — Rework `docs/how-to/setup-codex-spec-kitty-launcher.md`

**Purpose**: This file explains the retired `.codex/` launcher model with `CODEX_HOME`. It is the most impacted file. Options in priority order:

**Option A (preferred)**: Rewrite the file to document the current model:
- Spec Kitty command skills for Codex live at `.agents/skills/spec-kitty.<command>/SKILL.md`
- Invocation: `$spec-kitty.<command>` (no `CODEX_HOME` required)
- Show a minimal working example of Codex finding and invoking a Spec Kitty skill

**Option B (acceptable if Option A is unclear)**: Replace file content with a redirect:
```markdown
# Setup Spec Kitty with Codex

Spec Kitty command skills are installed under `.agents/skills/spec-kitty.<command>/SKILL.md`.

For current setup instructions, see [docs/how-to/harnesses/codex.md](harnesses/codex.md).
```
Only use Option B if `docs/how-to/harnesses/codex.md` exists and covers the current model.

**Steps**:
1. Check whether `docs/how-to/harnesses/codex.md` exists and is current.
2. Apply Option A or Option B.
3. Verify zero remaining references to `.codex/` as an active install path in this file.

**Validation**:
- [ ] `grep -n "CODEX_HOME\|\.codex/prompts\|\.codex/skills" docs/how-to/setup-codex-spec-kitty-launcher.md` returns no lines presenting these as active install targets
- [ ] File accurately describes the current `.agents/skills/` model

---

## Post-edit Verification (required)

Run after completing all subtasks:

```bash
grep -rn "\.codex/prompts/\|\.codex/skills/\|CODEX_HOME.*\.codex" \
  docs/explanation/ docs/how-to/ docs/reference/ \
  --include="*.md"
```

**Expected**: Zero results (except inside `docs/development/` which is `do_not_change`).

If any results remain in active how-to or reference docs: fix them before marking this WP complete.

---

## Definition of Done

- [ ] All 6 owned files updated per `occurrence_map.yaml` rules
- [ ] Post-edit grep returns zero stale path occurrences in active docs
- [ ] `docs/development/3-2-information-architecture.md` is NOT modified
- [ ] No unrelated prose changed
- [ ] Changes pass `git diff` review: only targeted stale-path removals/replacements, no collateral edits

## Reviewer Guidance

Verify: run the post-edit grep command above. Any result in `docs/how-to/` or `docs/reference/` is a defect. Check `setup-codex-spec-kitty-launcher.md` specifically — it should describe the current `.agents/skills/` model, not the retired `.codex/` model. Confirm `docs/development/` files were NOT touched.

## Activity Log

- 2026-06-03T06:45:32Z – claude:sonnet:orchestrator:orchestrator – shell_pid=41631 – Assigned agent via action command
