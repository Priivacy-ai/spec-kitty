---
work_package_id: WP01
title: Provenance-comment normalization
dependencies: []
requirement_refs:
- FR-002
planning_base_branch: fix/frozen-baseline-toll-reduction
merge_target_branch: fix/frozen-baseline-toll-reduction
branch_strategy: Planning artifacts for this mission were generated on fix/frozen-baseline-toll-reduction. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/frozen-baseline-toll-reduction unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
history:
- at: '2026-08-18T12:40:00+00:00'
  actor: claude
  note: WP created by /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: tests/architectural/test_no_dead_symbols.py
create_intent: []
execution_mode: code_change
owned_files:
- tests/architectural/test_no_dead_symbols.py
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your assigned profile: run `/ad-hoc-profile-load python-pedro` (or `spec-kitty agent profile show python-pedro` + `spec-kitty charter context --action implement --json`). Apply its initialization, boundaries, directives, and tactics. You are an **implementer**: TDD/red-first, mypy `--strict` + zero new suppressions, complexity ≤ 15, tests for new behaviour.

## Objective

Give every **content-tier** entry in the dead-symbol allowlist a single canonical, machine-parseable `# module::Name` provenance comment. This is the fail-closed identity hint WP02's safe hash-refresh depends on — content-tier `SymbolKey`s are deliberately location-free (`module_path=None`), so the comment is the *only* discriminator between "same symbol, edited body" and "different symbol, same `bare_name`". This WP is a **comments-only** change: no `SymbolKey` values change, so `test_no_dead_symbols` stays green throughout.

## Context (verified against the tree)

- File: `tests/architectural/test_no_dead_symbols.py`. The allowlist is content-tier + collision-tier `SymbolKey` frozensets (**~365 entries as of the 2026-08-18 rebase; T001 re-derives — counts drift**, e.g. 354→365 and a new `register`×3 duplicate `bare_name` arrived from upstream).
- **Three live provenance-comment formats** (this is the whole reason WP01 exists):
  1. trailing `# module::Name` — ~176 entries (the canonical target).
  2. `# module`-only, **no** `::Name` — ~19 entries (reconstruct `::Name` from the entry's `bare_name`).
  3. comment on the **preceding** line, or absent — ~159 entries.
  Some carry parenthetical suffixes, e.g. `# charter.activation.activations::ALLOWED_MISSION_TYPES (body_hash refreshed …)`.
- **Do NOT** touch collision-tier entries' keys (they carry `module_path` in-key) — only their comments if needed for consistency.
- **Do NOT** change any `body_hash` / `bare_name` / `module_path` value. Comments only.

## Subtasks

### T001 — Audit + catalog the 3 formats
- Programmatically scan the content-tier frozensets and classify each entry's provenance comment into {trailing-`::Name`, trailing-`# mod`-only, preceding-line, absent}. Produce a short count summary (sanity-check against ~176 / ~19 / ~159).
- Identify the ~7 content-tier duplicate `bare_name`s (these are the entries whose *only* safe discriminator is the comment — they must end up with a correct `# module::Name`).
- **Validation**: the audit reproduces the format distribution; every duplicate `bare_name` is listed with its intended `module::Name`.

### T002 — Normalize to canonical trailing `# module::Name`
- Rewrite every content-tier entry to carry a single **trailing** `# module::Name` comment. For `# mod`-only entries, reconstruct `::Name` from the entry's `bare_name`. For preceding-line/absent, move/add the trailing comment (recover `module::Name` from the nearest existing provenance evidence; if a symbol's originating module genuinely cannot be determined, STOP and flag it rather than guess — a wrong module is worse than a missing one).
- Preserve any meaningful parenthetical suffix (or drop it if purely historical noise — reviewer's call).
- **Files**: `tests/architectural/test_no_dead_symbols.py` (comments only). **Validation**: no non-comment bytes change (diff is comment-only); every content-tier entry now matches a single canonical `# module::Name` regex.

### T003 — Parseable-comment assertion (defense in depth)
- Add a test asserting **every** content-tier allowlist entry carries a parseable trailing `# module::Name` provenance comment. This is the guard that keeps the WP02 helper's fail-closed hint from silently degrading to "refuse" as future entries are added.
- **Validation**: the new test passes now and would RED if any content-tier entry lacked a parseable comment.

### T004 — Green-check
- Run `PWHEADLESS=1 .venv/bin/python -m pytest tests/architectural/test_no_dead_symbols.py -q` — stays green (comments-only change cannot alter keys). ruff + mypy `--strict` clean on the touched file.

## Branch Strategy

Planning base and final merge target are both `fix/frozen-baseline-toll-reduction` (→ later a PR to `upstream`). Execution worktrees are allocated **per computed lane** from `lanes.json` (finalize-tasks computes them). Implement via `spec-kitty agent action implement WP01 --agent claude`. No cross-lane dependency; Lane 2 (`WP03`) runs in parallel.

## Definition of Done

- Every content-tier allowlist entry has a canonical trailing `# module::Name` comment (all 3 formats normalized).
- The parseable-comment assertion (T003) passes and is non-vacuous.
- `test_no_dead_symbols` green; diff is comments-only; ruff + mypy `--strict` clean.
- Any entry whose origin module was genuinely undeterminable is flagged for the reviewer, not guessed.

## Risks & Reviewer Guidance

- **Big mechanical diff** (~329 entries) — isolated here on purpose so review can check the normalization without algorithm noise. Reviewer: confirm the diff is comment-only (no key changes) and spot-check that the ~7 duplicate `bare_name`s got the correct `module::Name`.
- A wrong `module::Name` on a duplicate `bare_name` would mis-target WP02's refresh — verify those specifically.
