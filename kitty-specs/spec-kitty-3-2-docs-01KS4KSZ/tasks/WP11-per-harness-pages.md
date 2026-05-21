---
work_package_id: WP11
title: Per-harness setup-and-usage pages
dependencies:
- WP10
requirement_refs:
- FR-016
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T033
- T034
agent: "claude:opus-4-7:reviewer-renata:reviewer"
shell_pid: "5759"
history:
- actor: planner
  at: '2026-05-21T06:52:04Z'
  action: wp_authored
  notes: Initial authorship by tasks phase.
agent_profile: researcher-robbie
authoritative_surface: docs/how-to/harnesses/
execution_mode: code_change
model: claude-opus-4-7
owned_files:
- docs/how-to/harnesses/**
role: researcher
tags: []
---

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load researcher-robbie
```

## Objective

Author one user-facing setup-and-usage page per harness classified `partial` or higher in WP10's support matrix. Each page maps the harness's canonical mechanism to Spec Kitty's installed surface and cites the harness's current external docs.

## Context

- FR-016, NFR-004.
- Sources: WP10 support matrix and research method doc; `CLAUDE.md` agent tables.
- Plan default: pages exist only for harnesses ≥ partial. Likely set: claude-code, codex, opencode, cursor, gemini, qwen, amazon-q, copilot, augment, roo, kilocode, kiro, windsurf (and conditionally pi-tui, vibe, letta-code).

## Subtasks

### T033 — Author per-harness pages

For each in-scope harness, create `docs/how-to/harnesses/<key>.md` with:

- **Title** — `Use Spec Kitty in <Harness Name>`.
- **Prerequisites** — install Spec Kitty CLI (link to install how-to from WP12), open a project that has been `spec-kitty init`'d for this harness.
- **Where Spec Kitty installs files** — list directories from WP10 inventory.
- **Canonical invocation** — show how the user invokes a Spec Kitty command in this harness (slash command syntax, skill invocation, workflow trigger).
- **Worked example** — a short example running `/spec-kitty.specify "a tiny feature"` or equivalent.
- **Troubleshooting** — at least two common issues (e.g., commands not showing, profile not loading) and resolutions.
- **Where to learn more about the harness itself** — cite the external doc URL from WP10.

### T034 — Citation pass

- For each page, ensure at least one external citation appears in the page body or footer.
- Include the access date (matches WP10 doc).
- WP13's freshness check rule `LEAK-MISSING-CITATION` will validate at publication.

## Branch Strategy

- Planning base: `main`
- Merge target: `main`
- Lane: `D`. Reuses the lane-D worktree.

## Test Strategy

- Reviewer gate; spot-check 3 random pages for citation presence and worked-example accuracy.
- Optional: implementer runs the WP13 freshness check (once that ships) to confirm citation coverage.

## Definition of Done

- [ ] One `.md` page exists for every harness ≥ partial per WP10 matrix.
- [ ] Each page cites at least one current external doc URL.
- [ ] Each page lists the on-disk surfaces from WP10 inventory.
- [ ] No files outside `owned_files` modified.

## Risks

- **Harness slash-command syntax differs across versions** — Mitigation: cite the harness's own docs as authoritative; note the date the syntax was confirmed.
- **Worked example breaks on user's machine** — Mitigation: use the minimal `/spec-kitty.specify "..."` invocation that does not require SaaS access.

## Reviewer Guidance

- Confirm one page per harness ≥ partial.
- Confirm citation coverage.
- Confirm the worked example actually matches the host's invocation syntax.

## Implement command

```bash
spec-kitty agent action implement WP11 --agent claude
```

## Activity Log

- 2026-05-21T08:52:52Z – claude:opus-4-7:researcher-robbie:researcher – shell_pid=3704 – Started implementation via action command
- 2026-05-21T08:57:21Z – claude:opus-4-7:researcher-robbie:researcher – shell_pid=3704 – WP11 ready: 14 harness pages with prereqs/install/invocation/example/troubleshooting/citations.
- 2026-05-21T08:57:41Z – claude:opus-4-7:reviewer-renata:reviewer – shell_pid=5759 – Started review via action command
- 2026-05-21T08:58:47Z – claude:opus-4-7:reviewer-renata:reviewer – shell_pid=5759 – Renata review: pass. 14 harness pages with consistent structure; 13 external citations + 1 partial-tier disclosure (pi-tui); paths match WP10 inventory.
