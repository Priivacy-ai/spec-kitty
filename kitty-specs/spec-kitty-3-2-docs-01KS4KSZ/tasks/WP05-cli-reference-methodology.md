---
work_package_id: WP05
title: CLI reference methodology recovery
dependencies: []
requirement_refs:
- FR-006
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T014
- T015
agent: "claude:opus-4-7:reviewer-renata:reviewer"
shell_pid: "40401"
history:
- actor: planner
  at: '2026-05-21T06:52:04Z'
  action: wp_authored
  notes: Initial authorship by tasks phase.
agent_profile: curator-carla
authoritative_surface: docs/development/
execution_mode: code_change
model: claude-opus-4-7
owned_files:
- docs/development/3-2-cli-reference-methodology.md
role: curator
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your agent profile:

```
/ad-hoc-profile-load curator-carla
```

## Objective

Recover the prior CLI reference methodology from git history and write the methodology note that justifies the 3.2 builder design. The note is the rationale anchor for WP06 (builder tool) and WP07 (rebuilt reference).

## Context

- Spec FR-006 requires this investigation.
- Commits to inspect:
  - `a14769e7a` Add command reference docs
  - `81b3d6c3e` docs: Update CLI reference with agent subcommands
  - `514106af2` docs(WP01): Add auth and sync CLI reference entries
  - `deee8d7f3` docs: refresh site for 1.0 release and current CLI
- Workspace audit already in [`cli-audit-3-2.md`](../../../cli-audit-3-2.md): 192 visible / 5 hidden / 2 deprecated; only 113/192 covered by current docs.
- Research R-001 already concluded the 3.2 builder is a small generator; this WP documents the evidence for that choice.

## Subtasks

### T014 — `git show` the four prior commits

For each commit, capture:
- The diff against `docs/reference/cli-commands.md` (or `docs/reference/agent-subcommands.md` where applicable).
- Whether the commit message describes hand authorship, generation, or test validation.
- Whether the commit added any script or test under `scripts/`, `tools/`, or `tests/` that touched the CLI reference.

Commands:

```bash
git show a14769e7a -- docs/reference/cli-commands.md
git show 81b3d6c3e -- docs/reference/cli-commands.md docs/reference/agent-subcommands.md
git show 514106af2 -- docs/reference
git show deee8d7f3 -- docs/reference docs/docfx.json docs/toc.yml
```

### T015 — Author `docs/development/3-2-cli-reference-methodology.md`

Structure the methodology note:

1. **Findings from prior commits** — one section per commit with the evidence captured in T014.
2. **Classification** — "hand-authored", "semi-generated", "generated", or "test-validated". The classification must cite specific lines or absence of scripts.
3. **Existing freshness checks** — does any test or hook validate the reference today? Cite if yes; record `none found` if no.
4. **Why the 3.2 builder is justified** — short rationale tying to `cli-audit-3-2.md` evidence (192 visible vs 113 covered).
5. **Builder design summary** — pointer to [`contracts/build_cli_reference.md`](../contracts/build_cli_reference.md). Do not re-document the contract; reference it.
6. **Decision-defer note** — the hybrid/generated/hand decision is `01KS4KTM69EG2KVX5MQ54FQ939`; this WP records that the methodology supports any of the three modes.

## Branch Strategy

- Planning base: `main`
- Merge target: `main`
- Lane: `B`. First WP in lane B; implement allocates `.worktrees/spec-kitty-3-2-docs-<mid8>-lane-b/`.

## Test Strategy

Reviewer gate only (doc-only WP).

## Definition of Done

- [ ] `docs/development/3-2-cli-reference-methodology.md` exists.
- [ ] Each of the four commits has its own section with evidence.
- [ ] Classification stated with citations.
- [ ] Pointer to `contracts/build_cli_reference.md` present.
- [ ] No files outside `owned_files` modified.

## Risks

- **Commit not present locally** — if `git show <sha>` fails, the implementer documents the failure and proceeds with what's available; do not silently invent history.
- **Methodology note drifts into builder design** — Mitigation: the contract is the design artifact; the methodology note is rationale.

## Reviewer Guidance

- Confirm every prior commit has a section.
- Confirm the classification is justified by quoted diffs, not assertion.
- Confirm the note does not re-document the builder contract (DRY).

## Implement command

```bash
spec-kitty agent action implement WP05 --agent claude
```

## Activity Log

- 2026-05-21T07:40:15Z – claude:opus-4-7:curator-carla:implementer – shell_pid=38224 – Started implementation via action command
- 2026-05-21T07:44:16Z – claude:opus-4-7:curator-carla:implementer – shell_pid=38224 – WP05 ready: methodology note with evidence from 4 prior commits, classification, freshness-check inventory.
- 2026-05-21T07:44:42Z – claude:opus-4-7:reviewer-renata:reviewer – shell_pid=40401 – Started review via action command
- 2026-05-21T07:45:35Z – claude:opus-4-7:reviewer-renata:reviewer – shell_pid=40401 – Renata review: pass. Methodology note covers all 4 prior commits with quoted evidence; classification=hand-authored; 1 anti-regression freshness check inventoried; decision-defer note in place.
