---
work_package_id: WP07
title: '#2007 Focus A: command-contract-drift guard'
dependencies: []
requirement_refs:
- FR-011
- FR-012
- FR-013
tracker_refs: []
planning_base_branch: feat/naming-rider-3-2-1
merge_target_branch: feat/naming-rider-3-2-1
branch_strategy: Planning artifacts for this mission were generated on feat/naming-rider-3-2-1. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/naming-rider-3-2-1 unless the human explicitly redirects the landing branch.
subtasks:
- T025
- T026
- T027
- T028
- T029
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "1984006"
history:
- 2026-06-16 created (/spec-kitty.tasks)
agent_profile: python-pedro
authoritative_surface: src/doctrine/
create_intent: []
execution_mode: code_change
owned_files:
- src/doctrine/skills/spec-kitty-charter-doctrine/SKILL.md
- src/doctrine/skills/spec-kitty-mission-system/SKILL.md
- src/doctrine/missions/mission-steps/software-dev/plan/prompt.md
- tests/architectural/test_docs_cli_reference_parity.py
- scripts/docs/_typer_walker.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load python-pedro
```

Then read `spec.md` (FR-011/012/013), `plan.md` (IC-06), and
`docs/engineering_notes/3-2-0-training-bugs-2007/pedro-command-drift.md` (the exact drift inventory + guard
design). **CRITICAL: edit SOURCE templates only — `src/doctrine/...` — NEVER the generated agent copies
in `.claude/`, `.codex/`, etc. (they regenerate via `spec-kitty upgrade`).**

## Objective

Stop agents probing nonexistent CLI surfaces (#2007 Focus A): repoint the **15 drifted SOURCE references**,
add the **command-snippet CI guard**, and fix the worktree-repair hint + implement/review JSON contract
doc. Independent / parallel WP. A sibling of WP02's ratchet (architectural-consistency guard).

## Context — the verified drift (from `pedro-command-drift.md`)

12 HARD (nonexistent command) + 3 behavioral, in 3 SOURCE files. `doctrine list/show` do not exist; the
`doctrine` group only registers `fetch`/`new`/`regenerate-graph`/`validate`/`mission-type list`/`org`/`pack`.
`agent worktree repair` is not registered (real surface: `doctor workspaces --fix`). `agent action
implement/review` have no `--json`; top-level `implement` does (the internal-vs-canonical split).

## Subtasks

### T025 — Repoint the doctrine `list/show` refs (11 + 1)
In `src/doctrine/skills/spec-kitty-charter-doctrine/SKILL.md` (lines ~113-120, 348, 439-441, 444) and
`src/doctrine/skills/spec-kitty-mission-system/SKILL.md` (~320): replace `spec-kitty doctrine list --kind …`
/ `doctrine show <id>` with the real surfaces (`doctrine validate` / `mission-type list` / the programmatic
`DoctrineService` API the same skill already documents). Keep the guidance correct, not just syntactically
valid.

### T026 — Fix the 3 behavioral refs in `software-dev/plan/prompt.md`
- Line ~267: `agent context resolve` is missing the **required `--action`** — add `--action plan` (the
  other prompts pass it).
- Lines ~80/241: the prompt instructs `setup-plan --json` no-flag-first, which the resolver rejects with
  `PLAN_CONTEXT_UNRESOLVED` — change to require `--mission` (the resolver's actual contract). *(This is the
  exact drift that mis-steered this very mission's plan phase.)*

### T027 — Hint + contract-doc fixes (#13/#1890, #16/#1891)
- Repoint any `agent worktree repair` hint → `spec-kitty doctor workspaces --fix` (the real recovery
  surface). Grep SOURCE; if absent in SOURCE (per pedro it may only be in the installed build), record
  that finding and skip — do not invent.
- Document the implement/review JSON contract: state plainly that `agent action implement/review` is
  text-only and the top-level `implement --json` is internal — so agents don't pick the wrong surface.
  (Adding `--json` to the action surface is the read-path follow-on's job, NOT this WP.)

### T028 — The command-snippet CI guard
Generalize the existing docs-CLI reference-parity test (`tests/architectural/test_docs_cli_reference_parity.py`, its agent-profile-subcommand parity check) reusing
`scripts.docs._typer_walker.walk()`: extract `spec-kitty …` snippets from doctrine SOURCE prompts/skills/
docs and validate the command path against the registered Typer surface. **Path-level validation first**
(catches all 12 HARD hits). Emit finding codes: `unregistered-path`, `unknown-flag`, `internal-as-public`.
Allow-list as an empty module-level frozenset ratchet. Run in the existing docs-contract gate — **no new
CI job**. Document the limit: catches *snippet* drift, not *behavioral* drift (e.g. the setup-plan
contract — that needed the T026 prompt fix).

### T029 — Guard self-test + false-positive handling
Plant a nonexistent-command snippet → guard fails; clean tree → passes. Handle the documented
false-positive traps: placeholder tokens (`<mission>`, `…`) and valid bool auto-negation
(`--no-mark-loaded`). Don't flag the real `specify_cli.bulk_edit.*` / `specify_cli.mission_metadata`
imports.

## Branch Strategy
Base/merge target: `feat/naming-rider-3-2-1`. Worktree from `lanes.json`.

## Definition of Done
- [ ] The 15 SOURCE drift refs repointed to registered surfaces (SOURCE only; agent copies untouched).
- [ ] The plan-prompt behavioral refs fixed (`--action`, `--mission`).
- [ ] Command-snippet guard added, path-level, empty-frozenset ratchet, in the existing docs-contract gate.
- [ ] Guard self-test green; placeholder/auto-negation false-positives handled; clean tree passes.
- [ ] `ruff`/`mypy` clean on diff; complexity ≤ 15; no suppressions.

## Risks / reviewer guidance
- **Reviewer:** verify edits are in SOURCE (`src/doctrine/...`), NOT generated agent copies; verify the
  repointed commands actually exist in the Typer registry; verify the guard doesn't false-positive on
  placeholders.
- This WP touches doctrine SOURCE — the terminology guard + docs-contract gate apply; run
  `pytest tests/architectural/` before handoff.

## Activity Log

- 2026-06-16T12:22:04Z – claude:sonnet:python-pedro:implementer – shell_pid=1874599 – Assigned agent via action command
- 2026-06-16T12:50:48Z – claude:sonnet:python-pedro:implementer – shell_pid=1954928 – Assigned agent via action command
- 2026-06-16T13:02:19Z – claude:sonnet:python-pedro:implementer – shell_pid=1954928 – Repointed 15 SOURCE drift refs (SOURCE only; agent copies untouched): 12 HARD doctrine list/show → DoctrineService API + doctrine validate + mission-type list; 3 BEHAVIORAL plan-prompt fixes (--action plan, require --mission). Command-snippet guard added (test_docs_cli_reference_parity.py): path-level, empty frozenset ratchet, positional-arg false-positive handled, --no-mark-loaded auto-negation handled. Self-tests green (planted doctrine list fails; clean tree passes). Docs-contract + terminology gates green. ruff + mypy clean on diff (also fixed pre-existing _build_live_app -> object mypy issue). T027: worktree repair absent from SOURCE (confirmed per research doc); CLI Surface Contract section added to mission-system SKILL.md documenting text-only agent action implement/review vs internal implement --json.
- 2026-06-16T13:03:34Z – claude:opus:reviewer-renata:reviewer – shell_pid=1984006 – Started review via action command
- 2026-06-16T13:08:15Z – user – shell_pid=1984006 – Review passed: 12 doctrine refs + 3 behavioral refs repointed (SOURCE only, targets registered); CLI Surface Contract for #13/#16; command-snippet guard scans live Typer surface with real self-tests + empty-frozenset ratchet; false-positives handled; docs-contract + terminology gates green; ruff+mypy clean.
