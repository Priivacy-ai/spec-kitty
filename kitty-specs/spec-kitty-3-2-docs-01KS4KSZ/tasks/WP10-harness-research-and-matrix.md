---
work_package_id: WP10
title: Harness research method + support matrix
dependencies: []
requirement_refs:
- FR-014
- FR-015
- NFR-004
- NFR-007
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T029
- T030
- T031
- T032
agent: "claude:opus-4-7:researcher-robbie:researcher"
shell_pid: "263"
history:
- actor: planner
  at: '2026-05-21T06:52:04Z'
  action: wp_authored
  notes: Initial authorship by tasks phase.
agent_profile: researcher-robbie
authoritative_surface: docs/development/
execution_mode: code_change
model: claude-opus-4-7
owned_files:
- docs/development/3-2-harness-research-method.md
- docs/reference/supported-harnesses.md
role: researcher
tags: []
---

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load researcher-robbie
```

## Objective

Author the harness research method document and populate the 5-tier support matrix for 16 candidate harnesses. Every harness gets a tier and at least one external-doc citation when tier ≥ supported.

## Context

- FR-014, FR-015, NFR-004, NFR-007.
- Candidate harnesses from `start-here.md` §"Supported Harness Research" plus `CLAUDE.md` §"Supported AI Agents".
- Plan default for decision `01KS4KTS4V300M9MMTS1AJEGXY`: matrix-first; promote per-harness pages based on evidence.
- `HarnessEntry` shape from [`data-model.md`](../data-model.md) §"HarnessEntry".

## Subtasks

### T029 — Author research method doc

Create `docs/development/3-2-harness-research-method.md` covering:

1. **Subject list** — 16 candidate harnesses (Claude Code, Codex, OpenCode, Cursor, Gemini, Pi TUI, Qwen, Amazon Q, GitHub Copilot, Augment/Auggie, Roo, Kilo Code, Kiro, Windsurf, Vibe, Letta Code).
2. **Inventory step** — list the host's installed surface (e.g., `.claude/commands/`, `.codex/...`, `.cursor/commands/`); cross-reference `CLAUDE.md` table.
3. **Canonical mechanism step** — slash command / prompt / workflow / skill / command file / config.
4. **Citation step** — at least one current public doc URL per harness (tier ≥ supported).
5. **Classification criteria** — explicit rules for each of the 5 tiers (`first_class` / `supported` / `partial` / `experimental` / `archived`).
6. **Promotion rule** — when does a harness move from `partial` to `supported` or `first_class`.

### T030 — Inventory generated files per harness

For each candidate harness, list the on-disk files Spec Kitty installs:

- e.g., for Claude Code: `.claude/commands/spec-kitty.*.md`.
- e.g., for Codex: `.agents/skills/spec-kitty.*/SKILL.md`.
- e.g., for Vibe: `.agents/skills/spec-kitty.*/SKILL.md` (shared with Codex per CLAUDE.md).
- Cross-reference the actual on-disk state (use `find .` or `git ls-files` against the listed directories).

Record results inside the research method doc as a table or per-harness section.

### T031 — Verify external citations

For each harness, find at least one current public-doc URL:

- Prefer the harness's primary documentation page.
- Avoid blog posts unless they are the only public source.
- Record citation along with the date the page was accessed.
- Flag harnesses where citation is not findable; classify those at `partial` or lower.

### T032 — Populate the support matrix

Create `docs/reference/supported-harnesses.md` with:

- One row per harness using the `HarnessEntry` columns.
- Tiers per the classification criteria from T029.
- At least one external citation per row at tier ≥ supported.
- A short legend explaining each tier (1–2 lines each).

## Branch Strategy

- Planning base: `main`
- Merge target: `main`
- Lane: `D`. First WP in lane D; allocates `.worktrees/spec-kitty-3-2-docs-<mid8>-lane-d/`.

## Test Strategy

- Reviewer gate.
- Schema validation: every row has a non-empty `name`, `key`, `repo_directory`, `mechanism`, `support_tier`; rows at tier ≥ supported have non-empty `external_doc_citations`.

## Definition of Done

- [ ] Research method doc covers all 16 candidate harnesses.
- [ ] Support matrix renders as one page with the 5-tier legend.
- [ ] Every row passes the schema rules in `data-model.md`.
- [ ] No files outside `owned_files` modified.

## Risks

- **External docs change between research and publish** — Mitigation: cite with access date; freshness check rule for citations is part of WP13.
- **Vibe / Letta Code uncertain status** — Mitigation: classify at `experimental` or `archived` with explicit notes; no page promotion.

## Reviewer Guidance

- Cross-check inventory against `find . -maxdepth 2 -type d -name '.[a-z]*'`.
- Confirm every tier ≥ supported has citations.
- Confirm Vibe is correctly noted as shared-skill with Codex per CLAUDE.md.

## Implement command

```bash
spec-kitty agent action implement WP10 --agent claude
```

## Activity Log

- 2026-05-21T08:47:42Z – claude:opus-4-7:researcher-robbie:researcher – shell_pid=263 – Started implementation via action command
